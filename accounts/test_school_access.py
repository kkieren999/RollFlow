from django.contrib.auth.models import User
from django.test import TestCase, override_settings, Client
from .models import StaffAccessGrant, StaffProfile, Student
from .school_access import grants_for, scoped_rows


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class SchoolAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin-fictional", password="Fictional-admin-42!")
        self.staff = User.objects.create_user("leader-fictional", password="Fictional-leader-42!")
        self.other = User.objects.create_user("outside-fictional")
        StaffProfile.objects.create(user=self.staff, faculty="English")
        StaffProfile.objects.create(user=self.other, faculty="Science")
        self.seven = Student.objects.create(student_id="S7", first_name="YearSeven", last_name="Example", year_level=7)
        self.eight = Student.objects.create(student_id="S8", first_name="YearEight", last_name="Example", year_level=8)
        self.grant = self.add("Head of Year", "year", "7", ["students"])

    def add(self, role, scope, value, caps):
        return StaffAccessGrant.objects.create(user=self.staff, role=role, scope=scope, scope_value=value, capabilities=caps, granted_by=self.admin)

    def test_unified_login_and_scoped_student_view(self):
        response = self.client.post("/", {"username": self.staff.username, "password": "Fictional-leader-42!"})
        self.assertRedirects(response, "/workspace/")
        response = self.client.get("/workspace/students/")
        self.assertContains(response, "YearSeven")
        self.assertNotContains(response, "YearEight")
        self.assertEqual(self.client.get("/workspace/staff/").status_code, 403)
        self.assertEqual(self.client.get("/manage/students/").status_code, 403)
        self.assertEqual(self.client.get("/manage/access/").status_code, 403)
        self.assertEqual(self.client.get("/teacher/").status_code, 302)

    def test_multiple_roles_do_not_borrow_scope(self):
        self.add("Head of Department", "faculty", "English", ["staff"])
        grants = grants_for(self.staff)
        self.assertEqual(list(scoped_rows(grants, "students").values_list("pk", flat=True)), [self.seven.pk])
        self.assertEqual(list(scoped_rows(grants, "staff").values_list("user_id", flat=True)), [self.staff.pk])

    def test_invalid_grant_and_revocation_fail_closed(self):
        self.add("Invalid", "faculty", "English", ["students"])
        self.client.force_login(self.staff)
        self.grant.delete()
        self.assertEqual(self.client.get("/workspace/students/").status_code, 403)

    def test_admin_grant_revoke_and_validation(self):
        self.client.force_login(self.admin)
        payload = {"action": "grant", "user": self.staff.pk, "role": "Head of Department", "scope": "school", "capabilities": ["staff"]}
        self.assertEqual(self.client.post("/manage/access/", payload).status_code, 200)
        self.assertEqual(StaffAccessGrant.objects.count(), 1)
        payload.update(scope="faculty", scope_value="English")
        self.assertRedirects(self.client.post("/manage/access/", payload), "/manage/access/")
        grant = StaffAccessGrant.objects.get(scope="faculty")
        self.assertRedirects(self.client.post("/manage/access/", {"action": "revoke", "grant_id": grant.pk}), "/manage/access/")
        self.assertFalse(StaffAccessGrant.objects.filter(pk=grant.pk).exists())

    def test_admin_login_and_csrf(self):
        self.assertRedirects(self.client.post("/", {"username": self.admin.username, "password": "Fictional-admin-42!"}), "/manage/")
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.admin)
        self.assertEqual(c.post("/manage/access/", {"action": "revoke", "grant_id": self.grant.pk}).status_code, 403)

    def test_deactivated_account(self):
        self.client.force_login(self.staff)
        self.staff.is_active = False
        self.staff.save()
        self.assertEqual(grants_for(self.staff), [])
        self.assertEqual(self.client.get("/workspace/students/").status_code, 302)
