from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import SecurityEvent, AccessAudit, StaffAccessGrant


@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True, SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class AdministrationExperienceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("fictional-admin")
        self.staff = User.objects.create_user("fictional-staff")
        self.inactive = User.objects.create_user("fictional-inactive", is_active=False)
        self.routes = ("admin-system-centre", "admin-account-review",
                       "admin-audit-review", "admin-system-settings")

    def test_admin_only_and_read_only(self):
        for name in self.routes:
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)
        StaffAccessGrant.objects.create(user=self.staff, role="Principal", scope="school",
            capabilities=["students"], granted_by=self.admin)
        self.client.force_login(self.staff)
        for name in self.routes:
            self.assertEqual(self.client.get(reverse(name)).status_code, 403)
            self.assertEqual(self.client.post(reverse(name)).status_code, 403)
        self.client.force_login(self.admin)
        for name in self.routes:
            response = self.client.get(reverse(name))
            self.assertContains(response, 'data-rf-shell="protected"', count=1)
            self.assertIn("no-store", response["Cache-Control"])
            self.assertEqual(self.client.post(reverse(name)).status_code, 405)

    def test_overview_and_empty_readiness(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("admin-system-centre")), "Review priorities")
        res = self.client.get(reverse("admin-system-settings"))
        self.assertContains(res, "No active publication")
        self.assertContains(res, "Production blocked")
        self.assertContains(res, "Open launch gates (10)")
        self.assertContains(res, "Backup status is not verified")

    def test_account_filter_and_no_mutations(self):
        self.client.force_login(self.admin)
        res = self.client.get(reverse("admin-account-review"), {"status":"inactive","q":"fictional"})
        self.assertContains(res, "fictional-inactive")
        self.assertNotContains(res, "fictional-staff")
        self.assertContains(res, reverse("security-effective", args=[self.inactive.pk]))
        self.assertFalse(User.objects.get(pk=self.inactive.pk).is_active)

    def test_audit_filter_pagination_and_escape(self):
        self.client.force_login(self.admin)
        SecurityEvent.objects.bulk_create([SecurityEvent(actor=self.admin,event="fixture",subject="<script>fake</script>") for _ in range(51)])
        SecurityEvent.objects.create(actor=self.admin,event="other",subject="unmatched")
        AccessAudit.objects.create(actor=self.admin,target=self.staff,action="fixture_access")
        url = reverse("admin-audit-review")
        res = self.client.get(url, {"source":"security","q":"fixture"})
        self.assertContains(res, "51 matching events")
        self.assertContains(res, "&lt;script&gt;fake&lt;/script&gt;")
        self.assertNotContains(res, "unmatched")
        self.assertContains(res, "Page 1 of 2")
        self.assertContains(self.client.get(url, {"source":"security","q":"fixture","page":2}), "Page 2 of 2")
        res = self.client.get(url, {"source":"access","q":"fixture_access"})
        self.assertContains(res, "fixture_access")
        self.assertNotContains(res, "fake&lt;/script&gt;")

    @override_settings(ROLLFLOW_PROTECTED_WORKSPACE=False)
    def test_unprotected_mode_not_enabled(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("admin-system-centre")).status_code, 404)
