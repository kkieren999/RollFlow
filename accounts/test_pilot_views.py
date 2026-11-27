from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import StaffAccessGrant, AccessAudit, SecurityEvent


@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True,SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False)
class PilotViewTests(TestCase):
    def test_admin_only_read_only_and_no_assessment(self):
        admin=User.objects.create_superuser("fictional-pilot-admin")
        staff=User.objects.create_user("fictional-pilot-staff")
        StaffAccessGrant.objects.create(user=staff,role="Principal",scope="school",
                                       capabilities=["students"],granted_by=admin)
        url=reverse("admin-pilot-readiness")
        self.assertEqual(self.client.get(url).status_code,302)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.client.post(url,{"approved":"yes"}).status_code,403)
        self.assertNotContains(self.client.get("/live/"),url)
        self.client.force_login(admin)
        before=(AccessAudit.objects.count(),SecurityEvent.objects.count())
        response=self.client.get(url,{"approved":"yes"})
        self.assertContains(response,"Production blocked")
        self.assertContains(response,"Rehearsal scenarios (12)")
        self.assertContains(response,"Open production gates (10)")
        self.assertContains(response,"not assessed",count=12)
        self.assertIn("no-store",response["Cache-Control"])
        self.assertEqual(self.client.post(url,{"approved":"yes"}).status_code,405)
        self.assertEqual((AccessAudit.objects.count(),SecurityEvent.objects.count()),before)
        with self.settings(ROLLFLOW_PROTECTED_WORKSPACE=False):
            self.assertEqual(self.client.get(url).status_code,404)
