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
