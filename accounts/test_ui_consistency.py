"""Fictional regression tests for every visible admin tab and teacher timetable shell.

UI-only changes must not weaken server permission boundaries or alter
published allocation data. No real school exports or staff identifiers.
"""
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.template.loader import get_template
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .models import ConnectedSchoolPublication, ConnectedStaffMapping, StaffProfile, Student


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class SharedInterfaceTests(TestCase):
    ADMIN_TABS = (
        "/manage/", "/manage/staff/", "/manage/students/", "/manage/classes/",
        "/manage/timetable/", "/manage/master/", "/manage/relief/",
        "/manage/attendance/", "/manage/movements/", "/manage/notices/",
        "/manage/reports/", "/manage/roles/", "/manage/data/",
        "/manage/oneschool/", "/manage/audit/", "/manage/settings/",
    )
    ADMIN_EXTERNAL = (
        "/manage/oneschool/documents/",
        "/manage/oneschool/class-memberships/",
        "/manage/oneschool/timetable-evidence/",
        "/manage/connected/", "/manage/connected/setup/",
    )

    def setUp(self):
        self.admin = User.objects.create_superuser(
            "fictional-admin-ui", password="Fictional-long-secret-123!"
        )
        self.teacher = User.objects.create_user(
            "fictional-teacher-ui", password="Fictional-long-secret-123!"
        )
        self.teacher.groups.add(Group.objects.get(name="Teacher"))
        self.profile = StaffProfile.objects.create(
            user=self.teacher, staff_id="FAKE-ID-01", timetable_link_verified=True
        )
        self.client.force_login(self.admin)

    def assert_interface(self, path, heading=None):
        res = self.client.get(path)
        self.assertEqual(res.status_code, 200, (path, res.status_code))
        html = res.content.decode()
        self.assertIn("--rf-green", html, path)
        self.assertIn("Skip to main content", html, path)
        self.assertIn('id="main-content"', html, path)
        self.assertIn('action="/logout/"', html, path)
        if heading:
            self.assertIn(heading, html, path)
        return html

    def test_all_admin_tabs_and_import_pages_share_navigation_and_design(self):
        for path in self.ADMIN_TABS + self.ADMIN_EXTERNAL:
            with self.subTest(route=path):
                html = self.assert_interface(path)
                self.assertIn("ADMINISTRATION PORTAL", html)
                self.assertNotIn("href=\"/teacher/roster/", html)
        html = self.assert_interface("/manage/connected/setup/", "Automated School Setup")
        self.assertIn('href="/manage/connected/"', html)
        html = self.assert_interface("/manage/oneschool/documents/", "OneSchool Import Centre")
        self.assertIn('href="/manage/"', html)

    def publish_fictional(self):
        now = timezone.localdate()
        mapping = ConnectedStaffMapping.objects.create(
            staff_code="FABC", profile=self.profile,
            verified_staff_id="FAKE-ID-01", verified_by=self.admin
        )
        bindings = {
            "FABC": {
                "profile": self.profile.pk, "user": self.teacher.pk,
                "staff_id": "FAKE-ID-01",
                "verification": mapping.verified_at.isoformat(),
            }
        }
        source = {"calendar": {
            "times": {f"{day}:{period}": ["09:00","10:00"]
                      for day in range(1, 6) for period in range(1, 5)},
            "closed": []},
            "classes": [{"code":"FICT7A","name":"Fictional class","years":[7],"students":[]}],
            "slots": [{"code":"FICT7A","day":now.weekday()+1 if now.weekday()<5 else 1,
                       "period":1,"staff":"FABC","room":"FAKE-R1"}],
            "bindings":bindings, "student_identity": {},
            "stats": {"classes":1,"slots":1,"memberships":0,"skipped_pairs":0,
                      "verified_mappings":1,"unmapped_codes":[],"unassigned_slots":0,
                      "legend_only":0},
        }
        ConnectedSchoolPublication.objects.create(
            name="Fictional term", starts=now-timedelta(days=21),
            ends=now+timedelta(days=21), snapshot=source,
            source_batches={}, digest="a"*64, published_by=self.admin,
        )

    def test_connected_admin_class_master_and_roster_have_the_same_shell(self):
        self.publish_fictional()
        for path in ("/manage/connected/", "/manage/connected/classes/",
                     "/manage/connected/master/", "/manage/connected/roster/FICT7A/"):
            with self.subTest(route=path):
                html = self.assert_interface(path)
                self.assertIn("ADMINISTRATION PORTAL", html)
                self.assertIn('href="/manage/connected/setup/"', html)

    def test_published_teacher_pages_share_nav_without_admin_links_or_other_staff(self):
        self.publish_fictional()
        self.client.force_login(self.teacher)
        for path in ("/teacher/timetable/", "/teacher/week/", "/teacher/roster/FICT7A/"):
            with self.subTest(route=path):
                html = self.assert_interface(path)
                self.assertIn("TEACHER PORTAL", html)
                self.assertIn('href="/teacher/week/"', html)
                self.assertIn('href="/teacher/timetable/"', html)
                self.assertNotIn('href="/manage/', html)
                self.assertNotIn("FAKE-ID-01", html)
        for path in ("/manage/staff/", "/manage/connected/", "/manage/connected/setup/",
                     "/manage/oneschool/documents/", "/manage/connected/master/"):
            with self.subTest(denied=path):
                self.assertEqual(self.client.get(path).status_code, 403)
        self.assertEqual(self.client.get("/teacher/master/").status_code, 302)

    def test_unpublished_legacy_teacher_demo_keeps_server_bootstrap(self):
        self.client.force_login(self.teacher)
        res = self.client.get("/teacher/")
        self.assertEqual(res.status_code, 200)
        html = res.content.decode()
        self.assertIn("Skip to teacher portal", html)
        self.assertIn("TEACHER PORTAL", html)
        self.assertIn('id="rollflow-server-identity"', html)
        self.assertNotIn("href=\"/manage/", html)

    def test_offline_teacher_demo_has_example_one_movement_dashboard(self):
        """The Windows bundle packages index.html for the offline fallback teacher UI.

        These are fictional browser-local movements, not the published school
        timetable's authenticated database records.
        """
        html = (settings.BASE_DIR / "index.html").read_text(encoding="utf-8")
        for marker in (
            "function rfMovementEntriesForDate()",
            'class="rf-movements-hero"',
            'class="rf-movement-stats"',
            'id="movementStudentSearch"',
            'id="movementDestination"',
            'id="movementIssueButton"',
            'id="rfMovementView"',
            'data-action="returnMovement"',
            "rfMovementExample1Style",
            "date!==brisbaneToday()",
            "function rfMakeVariedMovementSamples()",
            "rfIsOldAutoSample",
            "rf-fictional-2026-",
            "Fictional sample · ",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, html)
        for removed_section in (
            "DAILY SERVICE USAGE", "STUDENTS USING EACH SERVICE",
            "VISITS TO EACH SERVICE",
        ):
            self.assertNotIn(removed_section, html)
        # The previous blanket-generated set of 6–10 visits per fictional
        # student must never return, especially in new Windows bundles.
        self.assertNotIn("people.flatMap((person,index)=>Array.from({length:6+index%5}", html)
        self.assertEqual(html.count("function movementRows()"), 1)
        self.assertEqual(html.count("function movementsPage()"), 1)

    def test_login_and_templates_compile_with_shared_components(self):
        anon = Client()
        for path in ("/", "/admin-login/"):
            res = anon.get(path)
            self.assertEqual(res.status_code, 200)
            html = res.content.decode()
            self.assertIn("--rf-green", html)
            self.assertIn("Skip to sign in", html)
            self.assertIn('id="login-main"', html)
        for template in (
            "ui_system.html", "ui_header.html", "staff_portal.html",
            "connected_school.html", "automated_setup.html", "teacher_week.html",
            "teacher_timetable.html", "teacher_master.html", "imported_teacher.html",
            "live_timetable_pending.html", "oneschool_documents.html",
            "oneschool_class_rosters.html", "oneschool_schedule_review.html",
            "login.html",
        ):
            with self.subTest(template=template):
                get_template(template)
        html = (settings.BASE_DIR / "index.html").read_text(encoding="utf-8")
        self.assertEqual(html.count("<!-- ROLLFLOW_SERVER_BOOTSTRAP -->"), 1)
        self.assertIn("--green:#147f38", html)
