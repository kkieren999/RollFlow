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

    def test_published_year_scope_excludes_mixed_and_other_years(self):
        from datetime import date
        from .models import ConnectedSchoolPublication
        from .school_access import published_rows
        day = date(2026, 11, 23)
        pub = ConnectedSchoolPublication.objects.create(
            name="Fictional term", starts=day, ends=day, published_by=self.admin, digest="a"*64,
            snapshot={"source": "dated", "calendar": {"dates": [day.isoformat()]},
                      "classes": [{"code":"Y7", "name":"Year seven", "years":[7], "students":[111]},
                                  {"code":"Y8", "name":"Year eight", "years":[8], "students":[222]},
                                  {"code":"MIX", "name":"Mixed", "years":[7,8], "students":[333]}],
                      "slots": [{"date":day.isoformat(), "code":code, "staff":"PRIVATECODE", "period":"P1", "room":"FAKE"}
                                for code in ("Y7","Y8","MIX")], "bindings": {}})
        self.add("Head of Year", "year", "7", ["published_classes", "published_timetable"])
        grants = grants_for(self.staff)
        rows = published_rows(pub, grants, "published_classes", day)
        self.assertEqual([r["code"] for r in rows], ["Y7"])
        self.assertNotIn("students", rows[0])
        self.client.force_login(self.staff)
        res = self.client.get("/workspace/published_timetable/", {"date": day.isoformat()})
        self.assertContains(res, "Y7")
        self.assertNotContains(res, "Y8")
        self.assertNotContains(res, "MIX")
        self.assertNotContains(res, "PRIVATECODE")

    def test_published_faculty_scope_requires_current_verified_binding(self):
        from datetime import date
        from .models import ConnectedSchoolPublication
        from .school_access import published_rows
        teacher = self.staff.staff_profile
        teacher.staff_id = "FAKE01"
        teacher.timetable_link_verified = True
        teacher.teaching_enabled = True
        teacher.save()
        day = date(2026, 11, 23)
        pub = ConnectedSchoolPublication.objects.create(
            name="Fictional term", starts=day, ends=day, published_by=self.admin, digest="b"*64,
            snapshot={"source": "dated", "calendar": {"dates": [day.isoformat()]},
                      "classes": [{"code":"ENG", "name":"English", "years":[7]},
                                  {"code":"SCI", "name":"Science", "years":[7]}],
                      "slots": [{"date":day.isoformat(), "code":"ENG", "staff":"FAKE01", "period":"P1"},
                                {"date":day.isoformat(), "code":"SCI", "staff":"UNVERIFIED", "period":"P1"}],
                      "bindings": {"FAKE01":{"profile":teacher.pk,"user":self.staff.pk,"staff_id":"FAKE01"}}})
        self.add("Head of Department", "faculty", "English", ["published_timetable"])
        self.assertEqual([r["code"] for r in published_rows(pub, grants_for(self.staff), "published_timetable", day)], ["ENG"])
        teacher.timetable_link_verified = False
        teacher.save()
        self.assertEqual(published_rows(pub, grants_for(self.staff), "published_timetable", day), [])
