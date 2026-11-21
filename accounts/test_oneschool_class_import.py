"""Synthetic-only tests for OneSchool ExportStudentClass EQID/Class_Name CSV."""
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from .models import (
    Student, SchoolClass, ImportedTimetable, ImportedTimetableDay,
    OneSchoolArchiveBatch, OneSchoolClassMembership, SecurityEvent,
)
from .oneschool_class_csv import parse_student_classes


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class OneSchoolClassImportTests(TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        local = override_settings(ROLLFLOW_ARCHIVE_STATE_DIR=Path(temporary.name))
        local.enable()
        self.addCleanup(local.disable)

        self.admin = User.objects.create_superuser("class-admin", password="Fictional-password-234")
        self.teacher = User.objects.create_user("class-teacher", password="Fictional-password-235")
        self.client.force_login(self.admin)
        self.student = Student.objects.create(
            student_id="000DEMO01", first_name="Fictional", last_name="Learner",
            year_level=8, home_group="8B", status=Student.Status.ACTIVE,
        )
        self.inactive = Student.objects.create(
            student_id="000DEMO02", first_name="Fake", last_name="Inactive",
            year_level=9, home_group="9A", status=Student.Status.INACTIVE,
        )
        SchoolClass.objects.create(
            code="MATH08A", name="Fictional Maths", subject="Mathematics",
            year_level=8, teacher=self.teacher, active=True
        )
        self.version = ImportedTimetable.objects.create(
            name="Fictional Term", digest="c" * 64, status="published",
            summary={"first_date": "2026-11-23", "last_date": "2026-11-23"},
            created_by=self.admin,
        )
        ImportedTimetableDay.objects.create(
            version=self.version,
            date="2026-11-23",
            allocations=[{"code": "ENG08B", "staff_id": "FAKESTAFF", "start": "08:50"}],
        )

    def csv(self, rows=None, header=b"EQID,Class_Name\n"):
        if rows is None:
            rows = [
                ("000DEMO01", "MATH08A"),
                ("000DEMO01", "ENG08B"),
            ]
        return header + "".join(f"{a},{b}\n" for a, b in rows).encode("utf-8")

    def upload(self, rows=None, raw=None):
        source = self.csv(rows) if raw is None else raw
        return self.client.post("/manage/oneschool/documents/", {
            "kind": "class_members", "label": "Fictional ExportStudentClass",
            "acknowledge": "on",
            "files": [SimpleUploadedFile("ExportStudentClass-fictional.csv", source)],
        })

    def batch_and_preview(self):
        batch = OneSchoolArchiveBatch.objects.order_by("-pk").first()
        response = self.client.get(f"/manage/oneschool/documents/{batch.pk}/")
        self.assertEqual(response.status_code, 200)
        return batch, response.context["class_preview"]

    def apply(self, batch, preview, *, skip=False):
        data = {"confirm_apply": "yes", "preview_signature": preview["preview_signature"]}
        if skip:
            data["skip_unmatched"] = "yes"
        return self.client.post(f"/manage/oneschool/documents/{batch.pk}/apply-classes/", data)

    def test_staging_preview_no_changes_and_leading_zero_eqids(self):
        response = self.upload()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(OneSchoolClassMembership.objects.count(), 0)
        batch, preview = self.batch_and_preview()
        self.assertEqual(batch.summary["unique_pairs"], 2)
        self.assertEqual(preview["matched_count"], 2)
        self.assertEqual(preview["skipped_count"], 0)
        self.assertEqual(preview["matched_examples"][0], {"eqid": "000DEMO01", "class_code": "MATH08A"})
        self.assertContains(self.client.get(f"/manage/oneschool/documents/{batch.pk}/"), "Review student-to-class matches")
        self.assertEqual(batch.kind, "class_members")
        self.assertEqual(batch.files.count(), 1)
        self.assertEqual(list(parse_student_classes(self.csv())[0])[0][0], "000DEMO01")

    def test_apply_creates_matched_links_without_creating_classes_or_teachers(self):
        self.upload()
        batch, preview = self.batch_and_preview()
        self.assertEqual(self.client.post(
            f"/manage/oneschool/documents/{batch.pk}/apply-classes/", {}
        ).status_code, 400)
        self.assertEqual(self.apply(batch, preview).status_code, 302)
        self.assertEqual(OneSchoolClassMembership.objects.count(), 2)
        self.assertEqual(set(OneSchoolClassMembership.objects.values_list("class_code", flat=True)),
                         {"MATH08A", "ENG08B"})
        self.assertEqual(SchoolClass.objects.count(), 1)
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(Student.objects.count(), 2)
        self.assertEqual(self.student.class_enrolments.count(), 0)
        batch.refresh_from_db()
        self.assertEqual(batch.status, "applied")
        self.assertEqual(batch.summary["applied"]["created"], 2)
        self.assertTrue(batch.summary["subject_student_enrolment"])
        self.assertTrue(SecurityEvent.objects.filter(
            event="oneschool_classes_applied", subject=str(batch.pk)
        ).exists())
        self.assertEqual(self.apply(batch, preview).status_code, 400)

        page = self.client.get("/manage/oneschool/class-memberships/")
        self.assertContains(page, "MATH08A")
        self.assertContains(page, "ENG08B")
        person = self.client.get("/manage/oneschool/class-memberships/?class=MATH08A")
        self.assertContains(person, "000DEMO01")
        self.assertContains(person, "Fictional")

    def test_unknown_students_inactive_and_unknown_classes_are_skipped_only_when_acknowledged(self):
        self.upload(rows=[
            ("000DEMO01", "MATH08A"),
            ("000MISSING", "MATH08A"),
            ("000DEMO02", "ENG08B"),
            ("000DEMO01", "UNKNOWNC"),
        ])
        batch, preview = self.batch_and_preview()
        self.assertEqual(preview["matched_count"], 1)
        self.assertEqual(preview["skipped_count"], 3)
        self.assertEqual(preview["unmatched_student_count"], 1)
        self.assertEqual(preview["inactive_student_count"], 1)
        self.assertEqual(preview["unmatched_class_count"], 1)
        self.assertEqual(preview["unmatched_class_examples"], ["UNKNOWNC"])
        self.assertEqual(self.apply(batch, preview).status_code, 302)
        self.assertEqual(OneSchoolClassMembership.objects.count(), 0)
        batch.refresh_from_db()
        self.assertEqual(batch.status, "staged")
        self.assertEqual(self.apply(batch, preview, skip=True).status_code, 302)
        self.assertEqual(OneSchoolClassMembership.objects.count(), 1)
        batch.refresh_from_db()
        self.assertEqual(batch.summary["applied"]["skipped"], 3)
        self.assertEqual(batch.summary["applied"]["created"], 1)
        self.assertFalse(OneSchoolClassMembership.objects.filter(class_code="UNKNOWNC").exists())

    def test_second_import_is_idempotent_and_never_deletes_existing_links(self):
        self.upload()
        first, report = self.batch_and_preview()
        self.apply(first, report)
        self.upload(rows=[("000DEMO01", "MATH08A")])
        second, report = self.batch_and_preview()
        self.assertEqual(self.apply(second, report).status_code, 302)
        second.refresh_from_db()
        self.assertEqual(second.summary["applied"]["created"], 0)
        self.assertEqual(second.summary["applied"]["already_present"], 1)
        self.assertEqual(OneSchoolClassMembership.objects.count(), 2)

    def test_preview_changes_are_rejected_without_writes(self):
        self.upload()
        batch, preview = self.batch_and_preview()
        self.student.status = Student.Status.INACTIVE
        self.student.save(update_fields=["status"])
        response = self.apply(batch, preview)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(OneSchoolClassMembership.objects.count(), 0)
        batch.refresh_from_db()
        self.assertEqual(batch.status, "staged")
        self.student.status = Student.Status.ACTIVE
        self.student.save(update_fields=["status"])
        self.version.status = "archived"
        self.version.save(update_fields=["status"])
        batch, report = self.batch_and_preview()
        self.assertEqual(report["matched_count"], 1)
        self.assertEqual(report["unmatched_class_examples"], ["ENG08B"])

    def test_duplicate_rows_and_normalized_case(self):
        pairs, stats = parse_student_classes(b"\xef\xbb\xbfEQID,Class_Name\r\n"
                                            b"000demo01,math08a\r\n000DEMO01,MATH08A\r\n")
        self.assertEqual(pairs, [("000DEMO01", "MATH08A")])
        self.assertEqual(stats["duplicate_rows"], 1)
        self.assertEqual(stats["source_rows"], 2)

    def test_invalid_file_structures_never_archive(self):
        cases = [
            b"EqId,Class Name\n000DEMO01,MATH08A\n",
            b"EQID,Class_Name,Extra\n000DEMO01,MATH08A,One\n",
            b"EQID,Class_Name\n000DEMO01\n",
            b"EQID,Class_Name\n,ENG08B\n",
            b"EQID,Class_Name\n000DEMO01,=HYPERLINK\n",
            b"EQID,Class_Name\n000DEMO01,\"bad\"extra\n",
            b"EQID,Class_Name\n",
        ]
        for csv in cases:
            with self.subTest(csv=csv[:35]):
                self.assertEqual(self.upload(raw=csv).status_code, 200)
                self.assertFalse(OneSchoolArchiveBatch.objects.exists())

    def test_unknown_class_without_manual_or_published_timetable_does_not_link(self):
        SchoolClass.objects.filter(code="MATH08A").update(active=False)
        self.version.status = "archived"
        self.version.save(update_fields=["status"])
        self.upload()
        batch, report = self.batch_and_preview()
        self.assertEqual(report["matched_count"], 0)
        self.assertEqual(report["skipped_count"], 2)
        self.assertEqual(self.apply(batch, report, skip=True).status_code, 302)
        self.assertEqual(OneSchoolClassMembership.objects.count(), 0)

    def test_admin_only_and_csrf_for_preview_apply_and_rosters(self):
        self.upload()
        batch, preview = self.batch_and_preview()
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get("/manage/oneschool/class-memberships/").status_code, 403)
        self.assertEqual(self.client.get(f"/manage/oneschool/documents/{batch.pk}/").status_code, 403)
        self.assertEqual(self.apply(batch, preview).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get("/manage/oneschool/class-memberships/").status_code, 302)
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.admin)
        self.assertEqual(secure.post(
            f"/manage/oneschool/documents/{batch.pk}/apply-classes/",
            {"confirm_apply": "yes", "preview_signature": preview["preview_signature"]},
        ).status_code, 403)
