from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from .models import StaffProfile
from .permissions import can_teach, teaching_users

@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class TeachingPermissionsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("demo-admin", password="Fictional123!")
        self.staff = User.objects.create_user("demo-staff", password="Fictional123!")
        self.teacher = User.objects.create_user("demo-teacher", password="Fictional123!")
        self.teacher.groups.add(Group.objects.get(name="Teacher"))
        self.profile = StaffProfile.objects.create(user=self.staff, teaching_enabled=True)
    def test_independent_access_and_admin_boundary(self):
        self.assertTrue(can_teach(self.teacher))
        self.assertTrue(can_teach(self.staff))
        self.assertFalse(can_teach(self.admin))
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get("/teacher/timetable/").status_code, 200)
        self.assertEqual(self.client.get("/manage/").status_code, 403)
        StaffProfile.objects.create(user=self.admin, teaching_enabled=True)
        self.assertTrue(can_teach(self.admin))
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/teacher/timetable/").status_code, 200)
        self.assertEqual(self.client.get("/manage/").status_code, 200)
        self.assertIn(self.admin, teaching_users())
    def test_explicit_denial_and_deactivation(self):
        p = StaffProfile.objects.create(user=self.teacher, teaching_enabled=False)
        self.assertFalse(can_teach(self.teacher))
        self.assertNotIn(self.teacher, teaching_users())
        self.staff.is_active = False
        self.staff.save(update_fields=["is_active"])
        self.assertFalse(can_teach(self.staff))
