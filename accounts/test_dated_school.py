"""Synthetic dated publication regressions; never load school exports in CI."""
import hashlib
import tempfile
from datetime import timedelta
from pathlib import Path
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from .connected_school import current, visible_slots, personal_codes
from .dated_school import build_dated_candidate
from .models import (StaffProfile, Student, ImportedTimetable, ImportedTimetableDay,
    OneSchoolArchiveBatch, OneSchoolArchivedFile, OneSchoolClassMembership)
from .oneschool_csv import HEADER, parse
from .oneschool_storage import save_encrypted
from .test_connected_school import fictional_students

@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class DatedSchoolTests(TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        flags = override_settings(ROLLFLOW_ARCHIVE_STATE_DIR=Path(temp.name))
        flags.enable()
        self.addCleanup(flags.disable)
        self.admin = User.objects.create_superuser("dated-admin", password="Fictional123!")
        self.a = User.objects.create_user("dated-a", password="Fictional123!")
        self.b = User.objects.create_user("dated-b", password="Fictional123!")
        self.profile = StaffProfile.objects.create(user=self.a, staff_id="ID-A", teaching_enabled=True, timetable_link_verified=True)
        StaffProfile.objects.create(user=self.b, staff_id="ID-B", teaching_enabled=True, timetable_link_verified=True)
        today = timezone.localdate()
        self.monday = today - timedelta(days=today.weekday())
        self.other_day = self.monday + timedelta(days=7)
        def csv_row(day, code, staff, period, start, end):
            return ",".join([code, "Fictional subject", "07", day.strftime("%a"), day.strftime("%d/%m/%Y"),
                period, start, end, staff, "", staff, "Ignored", "Name", "ROOM", "Fictional room"])
        raw = ("\n".join([",".join(HEADER),
            csv_row(self.monday, "DEMO07A", "ID-A", "Care class", "08:35", "08:50"),
            csv_row(self.monday, "DEMO07B", "ID-B", "PERIOD 1", "09:00", "10:10"),
            csv_row(self.other_day, "DEMO07A", "ID-C", "PERIOD 2", "10:15", "11:25")])+"\n").encode()
        days, summary, digest = parse(raw)
        self.version = ImportedTimetable.objects.create(name="Fictional dated feed", status="published",
            summary=summary, digest=digest, created_by=self.admin, published_at=timezone.now())
        ImportedTimetableDay.objects.bulk_create([ImportedTimetableDay(version=self.version, date=day, allocations=rows)
            for day, rows in days.items()])
        self.student = Student.objects.create(student_id="000FAKE01", first_name="Learner", last_name="Example", year_level=7)
        self.other = Student.objects.create(student_id="000FAKE02", first_name="Pupil", last_name="Practice", year_level=7)
        self.client.force_login(self.admin)
    def source(self, kind, filename, raw):
        batch = OneSchoolArchiveBatch.objects.create(kind=kind, label="Fictional", created_by=self.admin,
            status="applied", applied_at=timezone.now())
        OneSchoolArchivedFile.objects.create(batch=batch, original_name=filename, storage_token=save_encrypted(raw),
            sha256=hashlib.sha256(raw).hexdigest(), size=len(raw), format="."+filename.rsplit(".",1)[1])
        return batch
    def rosters(self):
        self.source("students", "fictional.xlsx", fictional_students())
        batch = self.source("class_members", "fictional.csv", b"EQID,Class_Name\n000FAKE01,DEMO07A\n000FAKE02,DEMO07B\n")
        OneSchoolClassMembership.objects.create(student=self.student, class_code="DEMO07A", source_batch=batch)
        OneSchoolClassMembership.objects.create(student=self.other, class_code="DEMO07B", source_batch=batch)
        OneSchoolClassMembership.objects.create(student=self.other, class_code="DEMO07A", source_batch=batch)
    def preview(self):
        response = self.client.get("/manage/connected/dated/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context["preview"], response.context["error"])
        return response.context["preview"]
    def publish(self):
        p = self.preview()
        response = self.client.post("/manage/connected/dated/", {"action":"publish", "digest":p["digest"], "confirm":"yes"})
        self.assertEqual(response.status_code, 302)
        return current()
    def test_timetable_only_and_missing_staff(self):
        p = self.preview()
        self.assertFalse(p["stats"]["rosters_ready"])
        self.assertEqual(p["stats"]["staff"], 3)
        self.assertEqual(p["stats"]["missing_profiles"], ["ID-C"])
        self.assertEqual(self.client.post("/manage/connected/dated/", {"action":"prepare","digest":p["digest"],"confirm":"yes"}).status_code, 302)
        pending = User.objects.get(username="oneschool-id-c")
        self.assertFalse(pending.is_active)
        self.assertFalse(pending.has_usable_password())
        self.assertFalse(pending.staff_profile.teaching_enabled)
        self.assertFalse(pending.staff_profile.timetable_link_verified)
        # Old approval invalid after identity inventory changes.
        self.assertContains(self.client.post("/manage/connected/dated/", {"action":"publish","digest":p["digest"],"confirm":"yes"}), "Review")
        self.assertIsNone(current())
        publication = self.publish()
        self.assertEqual(publication.snapshot["stats"]["memberships"], 0)
        self.assertEqual(publication.snapshot["stats"]["classes"], 2)
    def test_actual_dates_allocations_and_roster_scope(self):
        self.rosters()
        publication = self.publish()
        self.assertTrue(publication.snapshot["stats"]["rosters_ready"])
        self.assertEqual(publication.snapshot["stats"]["memberships"], 2)
        self.assertEqual(publication.snapshot["timetable_version"], self.version.pk)
        self.assertEqual(personal_codes(publication, self.a), {"ID-A"})
        self.assertEqual(visible_slots(publication, self.monday, {"ID-A"})[0]["period_label"], "Care class")
        self.assertEqual(visible_slots(publication, self.monday+timedelta(days=1)), [])
        self.assertEqual(visible_slots(publication, self.other_day, {"ID-A"}), [])
        self.client.force_login(self.a)
        path = "/teacher/roster/DEMO07A/?date="+self.monday.isoformat()
        self.assertContains(self.client.get(path), "Learner")
        self.assertNotContains(self.client.get(path), "Pupil")
        self.assertEqual(self.client.get("/teacher/roster/DEMO07A/?date="+self.other_day.isoformat()).status_code,403)
        self.assertEqual(self.client.get("/teacher/roster/DEMO07B/?date="+self.monday.isoformat()).status_code,403)
        self.assertEqual(self.client.get("/manage/connected/dated/").status_code,403)
        self.profile.teaching_enabled = False
        self.profile.save(update_fields=["teaching_enabled"])
        self.assertEqual(personal_codes(publication, self.a), set())
    def test_new_import_does_not_silently_replace_connected_publication(self):
        publication = self.publish()
        self.version.status = "archived"
        self.version.save(update_fields=["status"])
        self.assertEqual(current().pk, publication.pk)
        self.assertEqual(len(visible_slots(current(), self.monday)),2)
