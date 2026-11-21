"""Bounded parsers for OneSchool files. No real export content enters logs.

Only the observed SM110 format is eligible for database updates. PDF and
TTLineAlignmentExport formats are securely staged as source material for
admin review; their class/staff mapping is NOT guessed from unseen schemas.
"""
import csv
import hashlib
import io
import re
from collections import Counter
from pathlib import PureWindowsPath
from zipfile import BadZipFile, ZipFile

from openpyxl import load_workbook
from pypdf import PdfReader
from .oneschool_class_csv import parse_student_classes


MAX_FILE_SIZE = 12 * 1024 * 1024
MAX_BATCH_SIZE = 48 * 1024 * 1024
MAX_FILES = 12
MAX_WORKBOOK_UNCOMPRESSED = 45 * 1024 * 1024
MAX_STUDENTS = 2500
STUDENT_HEADER = ["Student Name", "EQ ID", "Roll Class", "Year"]
ALLOWED = {
    "students": {".xlsx"},
    "staff_pdf": {".pdf"},
    "tt_alignment": {".csv", ".xlsx", ".pdf"},
    "class_members": {".csv"},
}


def file_name(name):
    value = PureWindowsPath(str(name).replace("/", "\\")).name
    if not value or len(value) > 180 or any(ord(ch) < 32 for ch in value):
        raise ValueError("Invalid file name.")
    return value


def validate_zip(raw):
    if not raw.startswith(b"PK\x03\x04"):
        raise ValueError("Not a valid XLSX workbook.")
    try:
        with ZipFile(io.BytesIO(raw)) as archive:
            infos = archive.infolist()
            if len(infos) > 1000 or sum(x.file_size for x in infos) > MAX_WORKBOOK_UNCOMPRESSED:
                raise ValueError("XLSX workbook expands beyond the safe import size.")
            if not archive.testzip() is None:
                raise ValueError("XLSX workbook failed integrity checks.")
    except (BadZipFile, OSError):
        raise ValueError("The XLSX workbook is invalid.") from None


def workbook_from_bytes(raw):
    validate_zip(raw)
    try:
        # Never run macros, external references or formulas.
        return load_workbook(io.BytesIO(raw), read_only=True, data_only=True, keep_links=False)
    except (OSError, ValueError, KeyError, BadZipFile):
        raise ValueError("Unable to read the XLSX workbook.") from None


def parse_students(raw):
    """Read the observed OneSchool SM110 workbook, retaining leading-zero IDs."""
    wb = workbook_from_bytes(raw)
    try:
        if "Data" not in wb.sheetnames:
            raise ValueError("Expected the SM110 'Data' worksheet.")
        ws = wb["Data"]
        if ws.max_row > MAX_STUDENTS + 30 or ws.max_column > 30:
            raise ValueError("Unexpected student list size or columns.")
        criteria = str(ws["A4"].value or "")
        if not re.search(r"enrolment\s+status\s*:\s*active\b", criteria, re.I):
            raise ValueError("SM110 must be exported with Enrolment Status: Active selected.")
        headers = [str(cell or "").strip() for cell in
                   next(ws.iter_rows(min_row=5, max_row=5, max_col=4, values_only=True))]
        if headers != STUDENT_HEADER:
            raise ValueError("Expected the exact SM110 columns: Student Name, EQ ID, Roll Class, Year.")
        students, ids, years, groups = [], set(), Counter(), set()
        for line, values in enumerate(ws.iter_rows(min_row=6, min_col=1, max_col=4, values_only=True), 6):
            if all(v is None or str(v).strip() == "" for v in values):
                continue
            name, sid, group, year = [str(v).strip() if v is not None else "" for v in values]
            if "," not in name:
                raise ValueError(f"Row {line}: expected 'Surname, Given names' in Student Name.")
            last, first = [part.strip() for part in name.split(",", 1)]
            sid = sid.upper()
            group = group.upper()
            if not first or not last or len(first) > 100 or len(last) > 100:
                raise ValueError(f"Row {line}: invalid student name.")
            if not re.fullmatch(r"[A-Z0-9_-]{1,40}", sid) or sid in ids:
                raise ValueError(f"Row {line}: missing, invalid or repeated EQ ID.")
            if len(group) > 30 or any(ord(ch) < 32 for ch in group):
                raise ValueError(f"Row {line}: invalid roll class.")
            if year not in ("07", "08", "09", "10", "11", "12", "7", "8", "9"):
                raise ValueError(f"Row {line}: year must be 7–12.")
            ids.add(sid)
            years[int(year)] += 1
            if group:
                groups.add(group)
            students.append(dict(student_id=sid, first_name=first, last_name=last,
                                 year_level=int(year), home_group=group))
            if len(students) > MAX_STUDENTS:
                raise ValueError("Too many students in the SM110 workbook.")
        if not students:
            raise ValueError("The SM110 student list contains no students.")
        return students, {
            "student_count": len(students), "home_group_count": len(groups),
            "years": {str(k): v for k, v in sorted(years.items())},
            "format": "SM110 Dynamic Student List",
            "scope": "Student directory and home groups only; no subject enrolment",
        }
    finally:
        wb.close()


def inspect_pdf(raw):
    if not raw.startswith(b"%PDF-"):
        raise ValueError("The PDF file signature is invalid.")
    try:
        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted:
            raise ValueError("Password-protected PDFs cannot be archived yet.")
        n = len(reader.pages)
        if n == 0 or n > 200:
            raise ValueError("Use a PDF with 1–200 pages.")
        # Extract tiny samples only to distinguish text layer from scanned pages.
        text_pages = 0
        for page in reader.pages:
            if (page.extract_text() or "").strip():
                text_pages += 1
        return {"pages": n, "text_pages": text_pages, "scanned_pages": n - text_pages}
    except ValueError:
        raise
    except Exception:
        raise ValueError("Unable to safely read the PDF.") from None


def inspect_file(kind, name, raw):
    """Metadata-only inspection for formats not yet safe to apply."""
    name = file_name(name)
    suffix = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
    if kind not in ALLOWED or suffix not in ALLOWED[kind]:
        raise ValueError("This file type does not match the selected OneSchool export.")
    if not raw or len(raw) > MAX_FILE_SIZE:
        raise ValueError("Each export must contain data and be no larger than 12 MB.")
    common = {"name": name, "extension": suffix, "size": len(raw),
              "sha256": hashlib.sha256(raw).hexdigest()}
    if kind == "students":
        students, summary = parse_students(raw)
        return common, summary
    if kind == "class_members":
        pairs, summary = parse_student_classes(raw)
        return common, summary
    if suffix == ".pdf":
        return common, inspect_pdf(raw)
    if suffix == ".xlsx":
        wb = workbook_from_bytes(raw)
        try:
            return common, {"worksheets": len(wb.sheetnames)}
        finally:
            wb.close()
    if suffix == ".csv":
        try:
            text = raw.decode("utf-8-sig")
            reader = csv.reader(io.StringIO(text, newline=""), strict=True)
            count = 0
            for record in reader:
                if record:
                    count += 1
                if count > 150000:
                    raise ValueError("CSV exceeds the maximum number of rows.")
            if count < 2:
                raise ValueError("CSV must have a header and at least one data row.")
            return common, {"csv_rows_including_header": count}
        except (UnicodeError, csv.Error):
            raise ValueError("CSV must be valid UTF-8.") from None
    raise ValueError("Unsupported file format.")
