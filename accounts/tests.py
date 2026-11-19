from django.contrib.auth.models import Group, User
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from .models import SecurityEvent

@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class AuthenticationTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user("testteacher", password="Fictional-test-password-42")
        self.teacher.groups.add(Group.objects.get(name="Teacher"))
        self.admin = User.objects.create_superuser("testadmin", password="Fictional-admin-password-42")
    def test_unauthenticated_teacher_redirect(self):
        self.assertRedirects(self.client.get("/teacher/"), "/")
    def test_teacher_login_and_identity(self):
        response = self.client.post("/", {"username": "testteacher", "password": "Fictional-test-password-42"})
        self.assertRedirects(response, "/teacher/")
        self.assertContains(self.client.get("/teacher/"), "rollflow-server-identity")
        self.assertEqual(SecurityEvent.objects.filter(event="login").count(), 1)
    def test_admin_portal_separation(self):
        self.assertEqual(self.client.post("/admin-login/", {"username": "testteacher", "password": "Fictional-test-password-42"}).status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.client.force_login(self.teacher)
        self.assertRedirects(self.client.get("/admin/"), "/admin/login/?next=/admin/", fetch_redirect_response=False)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/teacher/").status_code, 403)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
    def test_weak_public_demo_credentials_not_valid(self):
        response = self.client.post("/", {"username": "teacher", "password": "teacher"})
        self.assertContains(response, "Incorrect username or password")
        self.assertNotIn("_auth_user_id", self.client.session)
    def test_logout_post_only(self):
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertRedirects(self.client.post("/logout/"), "/")
        self.assertNotIn("_auth_user_id", self.client.session)
    def test_csrf(self):
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post("/", {"username": "testteacher", "password": "Fictional-test-password-42"}).status_code, 403)
    def test_disabled_teacher(self):
        self.teacher.is_active = False
        self.teacher.save()
        self.assertContains(self.client.post("/", {"username": "testteacher", "password": "Fictional-test-password-42"}), "Incorrect username or password")
    def test_login_throttled(self):
        for _ in range(10):
            self.assertEqual(self.client.post("/", {"username": "testteacher", "password": "wrong"}).status_code, 200)
        self.assertEqual(self.client.post("/", {"username": "testteacher", "password": "wrong"}).status_code, 429)


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class StaffManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("testadmin", password="Fictional-admin-password-42")
        self.teacher = User.objects.create_user("testteacher", password="Fictional-teacher-password-42")
        self.teacher.groups.add(Group.objects.get(name="Teacher"))
        self.client.force_login(self.admin)
    def details(self, **extra):
        return {"staff_id": "STF003", "username": "newteacher", "first_name": "Fictional", "last_name": "Example", "faculty": "Maths", "campus": "Test", "role": "teacher", "active": "on", "password": "Strong-example-passphrase-92", "password_confirm": "Strong-example-passphrase-92", **extra}
    def test_portal_role_and_redirect(self):
        self.client.logout()
        self.assertRedirects(self.client.get("/manage/"), "/admin-login/")
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get("/manage/staff/").status_code, 403)
        self.client.logout()
        self.assertRedirects(self.client.post("/admin-login/", {"username":"testadmin","password":"Fictional-admin-password-42"}), "/manage/")
    def test_create_staff_and_hash_password(self):
        self.assertRedirects(self.client.post("/manage/staff/add/", self.details()), "/manage/staff/")
        user = User.objects.get(username="newteacher")
        self.assertTrue(user.check_password("Strong-example-passphrase-92"))
        self.assertTrue(user.groups.filter(name="Teacher").exists())
        self.assertEqual(user.staff_profile.staff_id, "STF003")
        self.assertEqual(SecurityEvent.objects.filter(event="staff_created", subject="newteacher").count(), 1)
    def test_duplicate_and_weak_passwords(self):
        self.assertEqual(self.client.post("/manage/staff/add/", self.details(username="TESTTEACHER")).status_code, 200)
        self.assertEqual(self.client.post("/manage/staff/add/", self.details(password="teacher", password_confirm="teacher")).status_code, 200)
        self.assertFalse(User.objects.filter(username="newteacher").exists())
    def test_disable_and_self_protection(self):
        self.assertEqual(self.client.post(f"/manage/staff/{self.admin.pk}/status/", {"active":"0"}).status_code, 403)
        self.assertRedirects(self.client.post(f"/manage/staff/{self.teacher.pk}/status/", {"active":"0"}), "/manage/staff/")
        self.teacher.refresh_from_db()
        self.assertFalse(self.teacher.is_active)
    def test_password_reset(self):
        self.assertRedirects(self.client.post(f"/manage/staff/{self.teacher.pk}/reset/", {"password":"New-fictional-passphrase-82","password_confirm":"New-fictional-passphrase-82"}), "/manage/staff/")
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password("New-fictional-passphrase-82"))
    def test_csv_import_and_activation_guard(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        data = b"staff_id,username,first_name,last_name,faculty,campus\nSTF999,csvteacher,Sample,Teacher,Maths,Test\n"
        self.assertRedirects(self.client.post("/manage/staff/import/", {"csv": SimpleUploadedFile("staff.csv", data)}), "/manage/staff/")
        user = User.objects.get(username="csvteacher")
        self.assertFalse(user.is_active)
        self.assertFalse(user.has_usable_password())
        self.client.post(f"/manage/staff/{user.pk}/status/", {"active":"1"})
        user.refresh_from_db()
        self.assertFalse(user.is_active)
    def test_import_atomic_on_duplicate(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        data = b"staff_id,username,first_name,last_name,faculty,campus\nSTF991,freshstaff,Sample,Teacher,Maths,Test\nSTF992,testteacher,Sample,Teacher,Maths,Test\n"
        self.assertEqual(self.client.post("/manage/staff/import/", {"csv": SimpleUploadedFile("staff.csv", data)}).status_code, 200)
        self.assertFalse(User.objects.filter(username="freshstaff").exists())
    def test_mutations_require_csrf(self):
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.admin)
        self.assertEqual(c.post(f"/manage/staff/{self.teacher.pk}/status/", {"active":"0"}).status_code, 403)
