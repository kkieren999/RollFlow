"""Protected archive -> verified structured preview helpers, admin only."""
import hashlib

from .models import OneSchoolArchiveBatch
from .oneschool_alignment import parse_alignment_batch
from .oneschool_staff_pdf import parse_staff_pdf
from .oneschool_storage import read_encrypted


def read_batch_sources(batch):
    if batch.source_purged_at:
        raise ValueError("Original sources have been purged; cannot apply this import.")
    files = []
    for item in batch.files.all():
        raw = read_encrypted(item.storage_token)
        if hashlib.sha256(raw).hexdigest() != item.sha256:
            raise ValueError("Archived OneSchool file checksum mismatch.")
        files.append((item.original_name, raw))
    if not files:
        raise ValueError("No original source files in this batch.")
    return files


def alignment_preview(batch):
    if batch.kind != OneSchoolArchiveBatch.Kind.TT_ALIGNMENT:
        raise ValueError("This is not a line-alignment upload.")
    files = read_batch_sources(batch)
    rows, summary = parse_alignment_batch(files)
    summary["examples"] = [
        {k: row[k] for k in ("class_code", "weekday", "period", "staff_code", "room_code")}
        for row in rows[:12]
    ]
    return rows, summary


def staff_pdf_preview(batch):
    if batch.kind != OneSchoolArchiveBatch.Kind.STAFF_PDF:
        raise ValueError("This is not a staff timetable PDF upload.")
    files = read_batch_sources(batch)
    if len(files) != 1 or not files[0][0].lower().endswith(".pdf"):
        raise ValueError("Choose one whole-staff timetable PDF at a time for structured evidence.")
    raw = files[0][1]
    rows, summary = parse_staff_pdf(raw)
    summary["source_signature"] = hashlib.sha256(raw).hexdigest()
    summary["examples"] = [
        {k: row[k] for k in ("staff_code", "class_code", "subject_name", "line_number")}
        for row in rows[:12]
    ]
    return rows, summary
