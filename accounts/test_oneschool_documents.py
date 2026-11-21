"""Fictional-only security, archive and Excel import regression coverage."""
import io
import os
from pathlib import Path
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from openpyxl import Workbook
from pypdf import PdfWriter

from .models import OneSchoolArchiveBatch, OneSchoolArchivedFile, SecurityEvent, Student
from .oneschool_storage import read_encrypted


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class OneSchoolDocumentTests(TestCase):
    def setUp(self):
        state = tempfile.TemporaryDirectory()
        self.addCleanup(state.cleanup)
        self.state = Path(state.name)
        flags = override_settings(ROLLFLOW_ARCHIVE_STATE_DIR=self.state)
        flags.enable()
        self.addCleanup(flags.disable)

        self.admin = User.objects.create_superuser(
            "archive_admin", password="Fictional-archive-password-99"
        )
        self.teacher = User.objects.create_user(
            "archive_teacher", password="Fictional-teacher-password-91"
        )
        self.teacher.groups.add(Group.objects.get(name="Teacher"))
        self.client.force_login(self.admin)

    def xlsx(self, rows=None, bad_header=False):
        wb = Workbook()
        ws = wb.active
        ws.title = "Data"
        ws.append(["Fictional State High"])
        ws.append(["Dynamic Student List Report"])
        ws.append([])
        ws.append(["Selected Criteria: Enrolment Status: Active"])
        ws.append(["Student Name", "EQ ID", "Roll Class", "Year"] if not bad_header
                  else ["Wrong header", "EQ ID", "Roll Class", "Year"])
        for row in rows if rows is not None else [
            ("Example, Learner", "E00001", "7A", "07"),
            ("Practice, Pupil", "E00002", "8B", "08"),
        ]:
            ws.append(row)
        data = io.BytesIO()
        wb.save(data)
        wb.close()
        return data.getvalue()

    def upload(self, kind="students", sources=None, **extras):
        if sources is None:
            sources = [("SM110_DynamicStudentList.xlsx", self.xlsx())]
        files = [SimpleUploadedFile(name, raw) for name, raw in sources]
        data = {
            "kind": kind,
            "label": "Fictional test report",
            "acknowledge": "on",
            "files": files,
        }
        data.update(extras)
        return self.client.post("/manage/oneschool/documents/", data)

    def test_selection_guide_and_login_protection(self):
        self.assertContains(self.client.get("/manage/oneschool/documents/"), "TTLineAlignmentExport")
        self.assertContains(self.client.get("/manage/oneschool/documents/"), "multiple files at once")
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get("/manage/oneschool/documents/").status_code, 403)
        self.assertEqual(self.client.post("/manage/oneschool/documents/").status_code, 403)
        self.client.logout()
        self.assertRedirects(self.client.get("/manage/oneschool/documents/"), "/admin-login/")

    def test_sm110_stage_does_not_change_directory(self):
        resp = self.upload()
        self.assertEqual(resp.status_code, 302)
        batch = OneSchoolArchiveBatch.objects.get()
        self.assertEqual(batch.kind, "students")
        self.assertEqual(batch.status, "staged")
        self.assertEqual(batch.summary["student_count"], 2)
        self.assertEqual(batch.summary["home_group_count"], 2)
        self.assertEqual(Student.objects.count(), 0)
        page = self.client.get(f"/manage/oneschool/documents/{batch.pk}/")
        self.assertContains(page, "Approve the student directory changes")
        self.assertNotContains(page, "Practice, Pupil")

    def test_stored_source_is_encrypted_and_admin_only(self):
        source = self.xlsx()
        self.upload(sources=[("SM110.xlsx", source)])
        file = OneSchoolArchivedFile.objects.get()
        stored = self.state / "oneschool-imports" / (file.storage_token + ".rfenc")
        self.assertTrue(stored.exists())
        self.assertNotIn(b"Practice, Pupil", stored.read_bytes())
        self.assertEqual(read_encrypted(file.storage_token), source)
        if os.name != "nt":
            self.assertEqual(stored.stat().st_mode & 0o077, 0)
            self.assertEqual((self.state / "oneschool-import.key").stat().st_mode & 0o077, 0)
        response = self.client.get(f"/manage/oneschool/documents/file/{file.pk}/download/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, source)
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("no-store", response["Cache-Control"])
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(f"/manage/oneschool/documents/file/{file.pk}/download/").status_code, 403)

    def test_missing_archive_key_does_not_get_replaced_automatically(self):
        self.upload()
        item = OneSchoolArchivedFile.objects.get()
        key = self.state / "oneschool-import.key"
        old = self.state / "oneschool-import.key.backup"
        key.rename(old)
        from .oneschool_storage import read_encrypted
        with self.assertRaises(ValueError):
            read_encrypted(item.storage_token)
        self.assertFalse(key.exists())
        old.rename(key)
        self.assertTrue(read_encrypted(item.storage_token).startswith(b"PK"))

    def test_approved_sm110_upsert_preserves_status_and_subject_membership(self):
        old = Student.objects.create(
            student_id="E00001", first_name="Former", last_name="Name",
            year_level=9, home_group="9C", status=Student.Status.INACTIVE,
        )
        self.upload()
        batch = OneSchoolArchiveBatch.objects.get()
        self.assertEqual(self.client.get(f"/manage/oneschool/documents/{batch.pk}/apply/").status_code, 405)
        self.assertEqual(self.client.post(f"/manage/oneschool/documents/{batch.pk}/apply/").status_code, 400)
        apply = self.client.post(
            f"/manage/oneschool/documents/{batch.pk}/apply/", {"confirm_apply": "yes"}
        )
        self.assertEqual(apply.status_code, 302)
        old.refresh_from_db()
        self.assertEqual(old.first_name, "Learner")
        self.assertEqual(old.last_name, "Example")
        self.assertEqual(old.year_level, 7)
        self.assertEqual(old.status, Student.Status.INACTIVE)
        self.assertEqual(Student.objects.count(), 2)
        self.assertEqual(Student.objects.get(student_id="E00002").home_group, "8B")
        batch.refresh_from_db()
        self.assertEqual(batch.status, "applied")
        self.assertEqual(batch.summary["applied"], {
            "created": 1, "updated": 1, "unchanged": 0,
        })
        self.assertEqual(
            self.client.post(f"/manage/oneschool/documents/{batch.pk}/apply/",
                             {"confirm_apply": "yes"}).status_code, 400
        )
        self.assertTrue(
            SecurityEvent.objects.filter(event="oneschool_students_applied", subject=str(batch.pk)).exists()
        )

    def test_sm110_missing_dimension_metadata_is_validated_safely(self):
        from .test_oneschool_real_formats import without_excel_dimensions
        source = without_excel_dimensions(self.xlsx())
        response = self.upload(sources=[("SM110_DynamicStudentList.xlsx", source)])
        self.assertEqual(response.status_code, 302)
        batch = OneSchoolArchiveBatch.objects.get()
        self.assertEqual(batch.status, "staged")
        self.assertEqual(batch.summary["student_count"], 2)
        self.assertEqual(Student.objects.count(), 0)

    def test_invalid_header_and_duplicate_id_are_atomic(self):
        for raw in [
            self.xlsx(bad_header=True),
            self.xlsx(rows=[
                ("Example, One", "E00001", "7A", "07"),
                ("Example, Two", "E00001", "7A", "07"),
            ]),
        ]:
            with self.subTest(testcase=len(raw)):
                self.assertEqual(self.upload(sources=[("SM110.xlsx", raw)]).status_code, 200)
                self.assertEqual(OneSchoolArchiveBatch.objects.count(), 0)
                self.assertEqual(OneSchoolArchivedFile.objects.count(), 0)

    def test_inactive_report_criteria_rejected(self):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(self.xlsx()))
        wb["Data"]["A4"] = "Selected Criteria: Enrolment Status: Inactive"
        stream = io.BytesIO()
        wb.save(stream)
        wb.close()
        self.assertEqual(self.upload(sources=[("SM110.xlsx", stream.getvalue())]).status_code, 200)
        self.assertEqual(OneSchoolArchiveBatch.objects.count(), 0)

    def test_tt_line_accepts_several_parts_without_assigned_classes(self):
        wb = self.xlsx()
        csv = b"Line,Class,Period\nL1,DEMO071A,P1\n"
        response = self.upload(
            kind="tt_alignment",
            sources=[("TTLineAlignmentExport-A.csv", csv),
                     ("TTLineAlignmentExport-B.xlsx", wb)],
        )
        self.assertEqual(response.status_code, 302)
        batch = OneSchoolArchiveBatch.objects.get()
        self.assertEqual(batch.summary["file_count"], 2)
        self.assertFalse(batch.summary["automatic_teacher_assignment"])
        self.assertEqual(batch.status, "staged")
        self.assertEqual(batch.files.count(), 2)
        self.assertEqual(Student.objects.count(), 0)
        self.assertEqual(self.client.post(
            f"/manage/oneschool/documents/{batch.pk}/apply/", {"confirm_apply": "yes"}
        ).status_code, 400)

    def test_staff_pdf_can_be_archived_without_guessing_staff_identity(self):
        pdf = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)
        writer.write(pdf)
        response = self.upload(
            kind="staff_pdf", sources=[("whole-staff.pdf", pdf.getvalue())]
        )
        self.assertEqual(response.status_code, 302)
        batch = OneSchoolArchiveBatch.objects.get()
        self.assertEqual(batch.summary["files"][0]["pages"], 1)
        self.assertFalse(batch.summary["automatic_teacher_assignment"])
        self.assertContains(
            self.client.get(f"/manage/oneschool/documents/{batch.pk}/"),
            "Stored for review, not applied.",
        )

    def test_reject_duplicate_parts_and_invalid_extensions(self):
        raw = b"Line,Class\nA,B\n"
        self.assertEqual(self.upload(
            kind="tt_alignment", sources=[("one.csv", raw), ("two.csv", raw)]
        ).status_code, 200)
        self.assertEqual(OneSchoolArchiveBatch.objects.count(), 0)
        self.assertEqual(self.upload(
            kind="tt_alignment", sources=[("malware.exe", raw)]
        ).status_code, 200)
        self.assertEqual(OneSchoolArchiveBatch.objects.count(), 0)
        self.assertEqual(self.upload(
            kind="staff_pdf", sources=[("fake.pdf", b"not pdf")]
        ).status_code, 200)
        self.assertEqual(OneSchoolArchiveBatch.objects.count(), 0)

    def test_purge_sources_but_keep_audit_and_students(self):
        self.upload()
        batch = OneSchoolArchiveBatch.objects.get()
        file = OneSchoolArchivedFile.objects.get()
        path = self.state / "oneschool-imports" / (file.storage_token + ".rfenc")
        self.assertEqual(self.client.post(
            f"/manage/oneschool/documents/{batch.pk}/purge/",
            {"confirm_purge": "wrong"},
        ).status_code, 400)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.post(
                f"/manage/oneschool/documents/{batch.pk}/purge/",
                {"confirm_purge": "DELETE SOURCES"},
            ).status_code, 302)
        self.assertFalse(path.exists())
        batch.refresh_from_db()
        self.assertIsNotNone(batch.source_purged_at)
        # In Django TestCase, on_commit executes only through captureOnCommitCallbacks.
        self.assertEqual(self.client.get(
            f"/manage/oneschool/documents/file/{file.pk}/download/"
        ).status_code, 404)
        self.assertEqual(self.client.post(
            f"/manage/oneschool/documents/{batch.pk}/apply/",
            {"confirm_apply": "yes"},
        ).status_code, 400)
        self.assertTrue(SecurityEvent.objects.filter(
            event="oneschool_sources_purged", subject=str(batch.pk)
        ).exists())

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.admin)
        self.assertEqual(client.post("/manage/oneschool/documents/").status_code, 403)
        self.upload()
        batch = OneSchoolArchiveBatch.objects.get()
        self.assertEqual(client.post(
            f"/manage/oneschool/documents/{batch.pk}/purge/",
            {"confirm_purge": "DELETE SOURCES"},
        ).status_code, 403)
