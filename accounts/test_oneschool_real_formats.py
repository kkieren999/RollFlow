"""Fictional reproductions of observed OneSchool TTLine and staff PDF layouts.

Do not commit authentic school exports, names or EQIDs to this repository.
"""
import io
import tempfile
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from openpyxl import Workbook
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from .models import (
    OneSchoolArchiveBatch, OneSchoolLineAllocation, OneSchoolStaffClassReference,
    OneSchoolClassMembership, Student, SecurityEvent,
)
from .oneschool_alignment import parse_alignment_file, parse_alignment_batch
from .oneschool_staff_pdf import parse_staff_pdf
from .oneschool_class_service import known_class_codes


HEADINGS = [
    ["Monday - PERIOD 3", "Tuesday - PERIOD 1", "Thursday - PERIOD 4"],
    ["Tuesday - PERIOD 4", "Wednesday - PERIOD 2", "Friday - PERIOD 3"],
    ["Wednesday - PERIOD 3", "Thursday - PERIOD 1", "Friday - PERIOD 4"],
    ["Wednesday - PERIOD 1", "Thursday - PERIOD 3", "Friday - PERIOD 2"],
    ["Monday - PERIOD 2", "Tuesday - PERIOD 3", "Thursday - PERIOD 2"],
    ["Monday - PERIOD 1", "Wednesday - PERIOD 4", "Friday - PERIOD 1"],
    ["Tuesday - PERIOD 2"],
]


def fictional_line(line_num, version=186054, offline=False):
    wb = Workbook()
    sheet = wb.active
    sheet.title = "Sheet1"
    headings = HEADINGS[line_num - 1]
    for index, heading in enumerate(headings):
        col = 3 * index + 1
        sheet.cell(1, col, heading)
        for off, label in enumerate(["Class", "Teacher", "Room"]):
            sheet.cell(2, col+off, label)
    sheet.cell(3, 1, f"Year 7 - Line {line_num}")
    for index, _ in enumerate(headings):
        col = 3 * index + 1
        sheet.cell(4, col, f"DEMO07{line_num}")
        if line_num != 1:
            sheet.cell(4, col+1, f"FAKE{line_num}")
        sheet.cell(4, col+2, f"R{line_num:02}")
    if offline:
        sheet.cell(5, 1, "Year 7 - OFFLINE")
    crit = wb.create_sheet("ReportCriteria")
    for i, (key, value) in enumerate([
        ("Report Criteria", None), ("User", "Fictional school test"),
        ("Record Count", len(headings)),
        ("TimetableVersionId", version), ("LineNr", line_num),
        ("YrLvlCd", "0"), ("Generated", "Fictional"),
        ("Report", "TTLineAlignmentExport"), ("Version", "1.0"),
    ], start=1):
        crit.cell(i, 1, key)
        if value is not None:
            crit.cell(i, 2, value)
    raw = io.BytesIO()
    wb.save(raw)
    wb.close()
    return raw.getvalue()


def fictional_staff_pdf(version=186054, empty_legend=False):
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})
    })
    parts = ["FAKETE", "-", "Test", "Fictional"]
    if not empty_legend:
        parts += ["Legend:", "Class Code", "Class Name", "Line",
                  "DEMO071", "Fictional English", "Line 1",
                  "HOMEROOM07", "Roll Class", "Line"]
    parts += [f"TTStaffTimetable-V5.36-2149-{version}-"]
    stream = DecodedStreamObject()
    stream.set_data(("BT /F1 12 Tf 45 790 Td 14 TL " +
                     " ".join(f"({item}) Tj T*" for item in parts) +
                     " ET").encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    file = io.BytesIO()
    writer.write(file)
    return file.getvalue()


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class ActualOneSchoolLayoutTests(TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        settings = override_settings(ROLLFLOW_ARCHIVE_STATE_DIR=Path(temp.name))
        settings.enable()
        self.addCleanup(settings.disable)
        self.admin = User.objects.create_superuser(
            "report-admin", password="Fictional-source-test-password-43"
        )
        self.client.force_login(self.admin)

    def stage(self, kind, sources):
        return self.client.post("/manage/oneschool/documents/", {
            "kind": kind, "label": "Fictional timetable version",
            "acknowledge": "on",
            "files": [SimpleUploadedFile(name, raw) for name, raw in sources],
        })

    def seven_lines(self, version=186054):
        return [(f"TTLineAlignmentExport-{n}.xlsx", fictional_line(n,version)) for n in range(1,8)]

    def test_parsers_accept_full_seven_line_layout(self):
        rows = []
        for line in range(1,8):
            data, meta = parse_alignment_file(fictional_line(line,offline=(line==2)))
            self.assertEqual(meta["line_number"], line)
            self.assertEqual(meta["allocations"], len(HEADINGS[line-1]))
            self.assertEqual(meta["timetable_version_id"], "186054")
            rows.extend(data)
        self.assertEqual(len(rows), 19)
        self.assertEqual(sum(not row["staff_code"] for row in rows), 3)

    def test_seven_files_preview_approval_and_local_database(self):
        self.assertEqual(self.stage("tt_alignment", self.seven_lines()).status_code, 302)
        batch = OneSchoolArchiveBatch.objects.get()
        self.assertEqual(batch.status, "staged")
        review = self.client.get(f"/manage/oneschool/documents/{batch.pk}/")
        self.assertEqual(review.status_code, 200)
        preview = review.context["alignment_review"]
        self.assertTrue(preview["complete"])
        self.assertEqual(preview["allocation_count"], 19)
        self.assertEqual(preview["distinct_classes"], 7)
        self.assertEqual(OneSchoolLineAllocation.objects.count(), 0)
        self.assertEqual(self.client.post(
            f"/manage/oneschool/documents/{batch.pk}/apply-alignment/",
            {"confirm_apply": "yes", "source_signature": "wrong"},
        ).status_code, 302)
        self.assertEqual(OneSchoolLineAllocation.objects.count(), 0)
        self.assertEqual(self.client.post(
            f"/manage/oneschool/documents/{batch.pk}/apply-alignment/",
            {"confirm_apply": "yes", "source_signature": preview["source_signature"]},
        ).status_code, 302)
        self.assertEqual(OneSchoolLineAllocation.objects.count(), 19)
        self.assertTrue(OneSchoolLineAllocation.objects.filter(staff_code="").exists())
        batch.refresh_from_db()
        self.assertEqual(batch.status, "applied")
        self.assertEqual(batch.summary["applied"]["classes"], 7)
        self.assertIn("DEMO071", known_class_codes())
        self.assertEqual(self.client.post(
            f"/manage/oneschool/documents/{batch.pk}/apply-alignment/",
            {"confirm_apply": "yes", "source_signature": preview["source_signature"]},
        ).status_code, 400)
        self.assertTrue(SecurityEvent.objects.filter(
            event="oneschool_alignment_applied", subject=str(batch.pk)
        ).exists())

    def test_missing_line_is_visible_but_not_applied(self):
        self.assertEqual(self.stage("tt_alignment", self.seven_lines()[:-1]).status_code, 302)
        batch = OneSchoolArchiveBatch.objects.get()
        response = self.client.get(f"/manage/oneschool/documents/{batch.pk}/")
        self.assertContains(response, "Missing TTLine numbers")
        preview = response.context["alignment_review"]
        self.assertEqual(preview["missing_lines"], [7])
        self.client.post(f"/manage/oneschool/documents/{batch.pk}/apply-alignment/",
                         {"confirm_apply": "yes", "source_signature": preview["source_signature"]})
        self.assertEqual(OneSchoolLineAllocation.objects.count(), 0)

    def test_inconsistent_version_and_repeated_line_rejected(self):
        files = self.seven_lines()
        mismatch = files[:-1] + [("mismatched.xlsx", fictional_line(7,version=999999))]
        with self.assertRaisesRegex(ValueError,"same OneSchool timetable version"):
            parse_alignment_batch(mismatch)
        repeated = files[:-1] + [("repeated.xlsx", fictional_line(6))]
        with self.assertRaisesRegex(ValueError,"more than one file"):
            parse_alignment_batch(repeated)

    def test_pdf_legend_parser_and_review_no_login_permission(self):
        raw = fictional_staff_pdf()
        records, meta = parse_staff_pdf(raw)
        self.assertEqual(meta["staff_codes"], 1)
        self.assertEqual(meta["staff_class_references"], 2)
        self.assertEqual(meta["timetable_version_id"], "186054")
        self.assertEqual(records[0]["staff_code"], "FAKETE")
        self.assertEqual(self.stage("staff_pdf", [("fictional-staff.pdf", raw)]).status_code, 302)
        batch = OneSchoolArchiveBatch.objects.get()
        page = self.client.get(f"/manage/oneschool/documents/{batch.pk}/")
        preview = page.context["staff_review"]
        self.assertEqual(preview["distinct_classes"], 2)
        self.assertEqual(OneSchoolStaffClassReference.objects.count(), 0)
        self.client.post(f"/manage/oneschool/documents/{batch.pk}/apply-staff-evidence/",
                         {"confirm_apply": "yes", "source_signature": preview["source_signature"]})
        self.assertEqual(OneSchoolStaffClassReference.objects.count(), 2)
        self.assertIn("HOMEROOM07", known_class_codes())
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(hasattr(self.admin, "staff_profile"))
        self.assertEqual(batch.files.count(), 1)

    def test_staff_pdf_without_legend_fails_closed_but_preserves_source(self):
        raw = fictional_staff_pdf(empty_legend=True)
        self.assertEqual(self.stage("staff_pdf", [("fictional.pdf", raw)]).status_code, 302)
        batch = OneSchoolArchiveBatch.objects.get()
        self.assertEqual(batch.status, "staged")
        review = self.client.get(f"/manage/oneschool/documents/{batch.pk}/")
        self.assertContains(review, "No class legend entries")
        self.assertFalse(OneSchoolStaffClassReference.objects.exists())

    def test_student_class_can_match_pdf_home_group_and_line_classes(self):
        self.stage("tt_alignment", self.seven_lines())
        align = OneSchoolArchiveBatch.objects.get()
        ar = self.client.get(f"/manage/oneschool/documents/{align.pk}/").context["alignment_review"]
        self.client.post(f"/manage/oneschool/documents/{align.pk}/apply-alignment/",
                         {"confirm_apply":"yes","source_signature":ar["source_signature"]})
        self.stage("staff_pdf", [("staff.pdf", fictional_staff_pdf())])
        pdf = OneSchoolArchiveBatch.objects.order_by("-pk").first()
        pr = self.client.get(f"/manage/oneschool/documents/{pdf.pk}/").context["staff_review"]
        self.client.post(f"/manage/oneschool/documents/{pdf.pk}/apply-staff-evidence/",
                         {"confirm_apply":"yes","source_signature":pr["source_signature"]})
        Student.objects.create(student_id="000DEMO", first_name="Test",last_name="Student",
                               year_level=7,home_group="HOMEROOM07")
        raw=b"EQID,Class_Name\r\n000DEMO,DEMO071\r\n000DEMO,HOMEROOM07\r\n"
        self.stage("class_members",[("ExportStudentClass.csv",raw)])
        b=OneSchoolArchiveBatch.objects.order_by("-pk").first()
        response=self.client.get(f"/manage/oneschool/documents/{b.pk}/")
        cp=response.context["class_preview"]
        self.assertEqual(cp["matched_count"],2)
        self.client.post(f"/manage/oneschool/documents/{b.pk}/apply-classes/",
                         {"confirm_apply":"yes","preview_signature":cp["preview_signature"]})
        self.assertEqual(OneSchoolClassMembership.objects.count(),2)

    def test_no_cross_version_pdf_class_catalogue(self):
        self.stage("tt_alignment", self.seven_lines())
        batch=OneSchoolArchiveBatch.objects.get()
        preview=self.client.get(f"/manage/oneschool/documents/{batch.pk}/").context["alignment_review"]
        self.client.post(f"/manage/oneschool/documents/{batch.pk}/apply-alignment/",
                         {"confirm_apply":"yes","source_signature":preview["source_signature"]})
        self.stage("staff_pdf",[("old.pdf",fictional_staff_pdf(version=999999))])
        pdf=OneSchoolArchiveBatch.objects.order_by("-pk").first()
        pr=self.client.get(f"/manage/oneschool/documents/{pdf.pk}/").context["staff_review"]
        self.client.post(f"/manage/oneschool/documents/{pdf.pk}/apply-staff-evidence/",
                         {"confirm_apply":"yes","source_signature":pr["source_signature"]})
        self.assertNotIn("HOMEROOM07",known_class_codes())

    def test_teacher_cannot_review_or_approve_structured_reports(self):
        self.stage("tt_alignment", self.seven_lines())
        batch=OneSchoolArchiveBatch.objects.get()
        teacher=User.objects.create_user("fake-teacher", password="Fictional-password-57")
        self.client.force_login(teacher)
        self.assertEqual(self.client.get(f"/manage/oneschool/documents/{batch.pk}/").status_code,403)
        self.assertEqual(self.client.post(f"/manage/oneschool/documents/{batch.pk}/apply-alignment/",
                                          {"confirm_apply":"yes"}).status_code,403)
        self.assertEqual(self.client.post(f"/manage/oneschool/documents/{batch.pk}/apply-staff-evidence/",
                                          {"confirm_apply":"yes"}).status_code,403)
