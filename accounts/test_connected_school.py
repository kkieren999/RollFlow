"""Synthetic regression coverage for the connected school publication."""
import hashlib
import io
import tempfile
from datetime import timedelta
from pathlib import Path

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings, Client
from django.utils import timezone
from openpyxl import Workbook

from .connected_school import DAYS, current, parse_calendar
from .models import (
    ConnectedSchoolPublication, ConnectedStaffMapping, StaffProfile, Student,
    OneSchoolArchiveBatch, OneSchoolArchivedFile, OneSchoolLineAllocation,
    OneSchoolStaffClassReference, OneSchoolClassMembership,
)
from .oneschool_storage import save_encrypted, read_encrypted


def fictional_students():
    wb = Workbook()
    ws = wb.active
    ws.title = "Data"
    ws.append(["Fictional school"])
    ws.append(["Dynamic Student List"])
    ws.append([])
    ws.append(["Selected Criteria: Enrolment Status: Active"])
    ws.append(["Student Name", "EQ ID", "Roll Class", "Year"])
    ws.append(["Example, Learner", "000FAKE01", "7A", "07"])
    ws.append(["Practice, Pupil", "000FAKE02", "7B", "07"])
    buf = io.BytesIO()
    wb.save(buf)
    wb.close()
    return buf.getvalue()


def times():
    return "\n".join(
        f"{day},{period},{start},{end}"
        for day in DAYS
        for period, (start, end) in enumerate(
            [("09:00","10:00"), ("10:10","11:10"), ("12:00","13:00"), ("13:30","14:30")], 1
        )
    )


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class ConnectedSchoolTests(TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        flags = override_settings(ROLLFLOW_ARCHIVE_STATE_DIR=Path(temp.name))
        flags.enable()
        self.addCleanup(flags.disable)
        self.admin = User.objects.create_superuser("fake-admin", password="Fictional-123!password")
        self.a = User.objects.create_user("fake-teacher-a", password="Fictional-123!password")
        self.b = User.objects.create_user("fake-teacher-b", password="Fictional-123!password")
        for teacher in (self.a, self.b):
            teacher.groups.add(Group.objects.get(name="Teacher"))
        self.a_profile = StaffProfile.objects.create(user=self.a, staff_id="ID-A", timetable_link_verified=True)
        self.b_profile = StaffProfile.objects.create(user=self.b, staff_id="ID-B", timetable_link_verified=True)
        self.student = Student.objects.create(student_id="000FAKE01", first_name="Learner",
                                              last_name="Example", year_level=7, home_group="7A")
        self.other = Student.objects.create(student_id="000FAKE02", first_name="Pupil",
                                            last_name="Practice", year_level=7, home_group="7B")
        self.sm = self.batch("students")
        self.archive(self.sm, "fictional.xlsx", fictional_students())
        self.lines = self.batch("tt_alignment", {"lines": list(range(1,8)), "timetable_version_id": "123456"})
        self.pdf = self.batch("staff_pdf", {"timetable_version_id":"123456"})
        self.members = self.batch("class_members")
        self.archive(self.members, "fictional.csv", b"EQID,Class_Name\n000FAKE01,DEMO07A\n000FAKE02,DEMO07B\n000MISSING,DEMO07A\n")
        for student, code, staff in [(self.student,"DEMO07A","CODEA"),(self.other,"DEMO07B","CODEB")]:
            OneSchoolLineAllocation.objects.create(batch=self.lines, line_number=1, year_level=7,
                weekday=1, period=1, class_code=code, staff_code=staff, room_code="R01")
            OneSchoolStaffClassReference.objects.create(batch=self.pdf, staff_code=staff,
                class_code=code, subject_name="Fictional class", line_number=1)
            OneSchoolClassMembership.objects.create(student=student, class_code=code, source_batch=self.members)
        # Old additive membership omitted from current CSV must not leak into publication.
        OneSchoolClassMembership.objects.create(student=self.other, class_code="DEMO07A", source_batch=self.members)
        OneSchoolStaffClassReference.objects.create(batch=self.pdf, staff_code="CODEA",
            class_code="LEGENDONLY", subject_name="Home group")
        self.today = timezone.localdate()
        self.monday = self.today - timedelta(days=self.today.weekday())
        self.data = {"name":"Fictional term", "starts":self.monday.isoformat(),
                     "ends":(self.monday+timedelta(days=30)).isoformat(),
                     "times":times(), "closures":(self.monday+timedelta(days=7)).isoformat()}
        self.client.force_login(self.admin)

    def batch(self, kind, summary=None):
        return OneSchoolArchiveBatch.objects.create(kind=kind, label="Fictional source",
             created_by=self.admin, status="applied", applied_at=timezone.now(), summary={"applied":summary or {}})

    def archive(self, batch, name, raw):
        return OneSchoolArchivedFile.objects.create(batch=batch, original_name=name,
            storage_token=save_encrypted(raw), sha256=hashlib.sha256(raw).hexdigest(),
            size=len(raw), format="."+name.rsplit(".",1)[1])

    def verify(self, profile, code):
        return self.client.post("/manage/connected/mapping/", {"action":"verify","staff_code":code,
                 "profile":profile.pk,"confirm":"yes"})

    def review(self):
        response = self.client.post("/manage/connected/", {**self.data,"action":"review"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["preview"], response.context["form"].errors)
        return response.context["preview"]

    def publish(self):
        preview = self.review()
        response = self.client.post("/manage/connected/", {**self.data, "action":"publish",
             "digest":preview["digest"], "confirm":"yes"})
        self.assertEqual(response.status_code,302)
        return current()

    def test_review_publish_preserves_imports_and_limits_rosters(self):
        self.assertEqual(self.verify(self.a_profile,"CODEA").status_code,302)
        self.assertEqual(self.verify(self.b_profile,"CODEB").status_code,302)
        p = self.review()
        self.assertEqual(p["stats"]["classes"],3)
        self.assertEqual(p["stats"]["memberships"],2)
        self.assertEqual(p["stats"]["skipped_pairs"],1)
        self.assertIsNone(current())
        p = self.publish()
        self.assertEqual(OneSchoolArchiveBatch.objects.count(),4)
        self.assertEqual(OneSchoolClassMembership.objects.count(),3)
        original = read_encrypted(self.sm.files.get().storage_token)
        self.assertEqual(hashlib.sha256(original).hexdigest(), self.sm.files.get().sha256)
        self.assertRedirects(self.client.get("/manage/classes/"),"/manage/connected/classes/",fetch_redirect_response=False)
        self.assertContains(self.client.get("/manage/connected/classes/"),"LEGENDONLY")
        self.assertContains(self.client.get("/manage/connected/roster/DEMO07A/"),"Learner")
        self.assertNotContains(self.client.get("/manage/connected/roster/DEMO07A/"),"Pupil")
        self.assertContains(self.client.get("/manage/master/?date="+self.monday.isoformat(), follow=True),"School master timetable")
        self.client.force_login(self.a)
        self.assertRedirects(self.client.get("/teacher/"),"/teacher/timetable/",fetch_redirect_response=False)
        day=self.client.get("/teacher/timetable/?date="+self.monday.isoformat()+"&staff_id=ID-B")
        self.assertContains(day,"DEMO07A")
        self.assertNotContains(day,"DEMO07B")
        self.assertNotContains(day,"CODEB")
        self.assertContains(self.client.get("/teacher/week/?date="+self.monday.isoformat()),"DEMO07A")
        self.assertContains(self.client.get("/teacher/roster/DEMO07A/"),"Learner")
        self.assertNotContains(self.client.get("/teacher/roster/DEMO07A/"),"000FAKE01")
        for path in ("/teacher/roster/DEMO07B/","/teacher/roster/LEGENDONLY/","/manage/connected/","/manage/connected/master/"):
            self.assertEqual(self.client.get(path).status_code,403)
        self.assertRedirects(self.client.get("/teacher/master/"),"/teacher/timetable/",fetch_redirect_response=False)
        holiday=self.client.get("/teacher/week/?date="+(self.monday+timedelta(days=7)).isoformat())
        self.assertNotContains(holiday,"DEMO07A")

    def test_new_mapping_not_active_until_republish_and_revoked_immediately(self):
        self.publish()
        self.verify(self.a_profile,"CODEA")
        self.client.force_login(self.a)
        self.assertEqual(self.client.get("/teacher/roster/DEMO07A/").status_code,403)
        self.client.force_login(self.admin)
        self.publish()
        self.assertEqual(ConnectedSchoolPublication.objects.filter(active=True).count(),1)
        self.assertEqual(ConnectedSchoolPublication.objects.count(),2)
        self.client.force_login(self.a)
        self.assertEqual(self.client.get("/teacher/roster/DEMO07A/").status_code,200)
        self.a_profile.timetable_link_verified=False
        self.a_profile.save(update_fields=["timetable_link_verified"])
        self.assertEqual(self.client.get("/teacher/roster/DEMO07A/").status_code,403)

    def test_stale_review_and_version_mismatch_are_rejected(self):
        preview=self.review()
        self.verify(self.a_profile,"CODEA")
        response=self.client.post("/manage/connected/",{**self.data,"action":"publish","digest":preview["digest"],"confirm":"yes"})
        self.assertContains(response,"Review again")
        self.assertIsNone(current())
        self.pdf.summary={"applied":{"timetable_version_id":"999999"}}
        self.pdf.save(update_fields=["summary"])
        response=self.client.post("/manage/connected/",{**self.data,"action":"review"})
        self.assertContains(response,"same timetable version")
        self.assertIsNone(current())

    def test_invalid_and_unverified_mapping_attempts(self):
        self.b_profile.timetable_link_verified=False
        self.b_profile.save(update_fields=["timetable_link_verified"])
        self.verify(self.b_profile,"CODEB")
        self.verify(self.a_profile,"UNOBSERVED")
        self.assertFalse(ConnectedStaffMapping.objects.exists())
        self.verify(self.a_profile,"CODEA")
        self.client.post("/manage/connected/mapping/",{"action":"revoke","staff_code":"CODEA","confirm":"yes"})
        self.assertFalse(ConnectedStaffMapping.objects.exists())
        self.client.force_login(self.a)
        self.assertEqual(self.verify(self.a_profile,"CODEA").status_code,403)
        secure=Client(enforce_csrf_checks=True)
        secure.force_login(self.admin)
        self.assertEqual(secure.post("/manage/connected/",{**self.data,"action":"review"}).status_code,403)

    def test_invalid_lesson_times_and_inactive_students(self):
        invalid=times().replace("Monday,2,10:10,11:10","Monday,2,09:10,10:10")
        with self.assertRaisesRegex(ValueError,"overlap"):
            parse_calendar(self.monday,self.monday+timedelta(days=30),invalid,"")
        self.verify(self.a_profile,"CODEA")
        self.publish()
        self.student.status=Student.Status.INACTIVE
        self.student.save(update_fields=["status"])
        self.client.force_login(self.a)
        self.assertNotContains(self.client.get("/teacher/roster/DEMO07A/"),"Learner")
        self.student.status=Student.Status.ACTIVE
        self.student.student_id="CHANGED-ID"
        self.student.save(update_fields=["status","student_id"])
        self.assertNotContains(self.client.get("/teacher/roster/DEMO07A/"),"Learner")
