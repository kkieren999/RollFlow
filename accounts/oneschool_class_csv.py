"""Validated OneSchool ExportStudentClass two-column CSV import.

Only confirmed EQID/Class_Name pairs are allowed. Preserve EQID text,
including leading zeros. Never accept unknown extra columns, malformed
quotes or potentially executable spreadsheet cell values.
"""
import csv
import io
import re

from .oneschool_csv import validate_quoting

HEADER = ["EQID", "Class_Name"]
MAX_ROWS = 75000
STUDENT_RE = re.compile(r"[A-Z0-9_-]{1,40}\Z")
CLASS_RE = re.compile(r"[A-Z0-9_-]{1,30}\Z")


def parse_student_classes(raw):
    if not raw or len(raw) > 12 * 1024 * 1024:
        raise ValueError("Choose an ExportStudentClass CSV no larger than 12 MB.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError:
        raise ValueError("Save the OneSchool export as UTF-8 CSV.") from None
    if "\x00" in text:
        raise ValueError("Invalid binary content in class export.")
    validate_quoting(text)
    try:
        reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
        if reader.fieldnames != HEADER:
            raise ValueError("Expected the exact two columns: EQID,Class_Name.")
        pairs, seen, students, codes = [], set(), set(), set()
        source_rows = duplicates = 0
        for line, row in enumerate(reader, start=2):
            if row and all(v is not None and not v.strip() for v in row.values()):
                continue
            source_rows += 1
            if source_rows > MAX_ROWS:
                raise ValueError("Too many rows in class export (limit 75,000).")
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Row {line}: expected exactly two columns.")
            eqid = row["EQID"].strip().upper()
            code = row["Class_Name"].strip().upper()
            if not STUDENT_RE.fullmatch(eqid):
                raise ValueError(f"Row {line}: invalid EQID.")
            if not CLASS_RE.fullmatch(code):
                raise ValueError(f"Row {line}: invalid Class_Name.")
            pair = (eqid, code)
            if pair in seen:
                duplicates += 1
                continue
            seen.add(pair)
            pairs.append(pair)
            students.add(eqid)
            codes.add(code)
    except csv.Error:
        raise ValueError("Malformed OneSchool student class CSV.") from None
    if not pairs:
        raise ValueError("No student/class pairs found.")
    return pairs, {
        "source_rows": source_rows,
        "unique_pairs": len(pairs),
        "student_count": len(students),
        "class_count": len(codes),
        "duplicate_rows": duplicates,
        "format": "ExportStudentClass",
        "scope": "Student-to-class links only. Existing teacher assignments are unchanged.",
    }
