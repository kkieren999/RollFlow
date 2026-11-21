"""OneSchool EQID/Class_Name matching against existing, authorised records.

No teachers, periods, rooms or Student records are created from this export.
Class codes must already exist in a currently published OneSchool timetable
or an active, administrator-created SchoolClass. Unmatched pairs are skipped
only after explicit, counts-specific administrator confirmation.
"""
import hashlib

from .models import (
    ImportedTimetableDay, OneSchoolClassMembership,
    SchoolClass, Student,
)


def known_class_codes():
    classes = set(SchoolClass.objects.filter(active=True).values_list("code", flat=True))
    # Only the current published timetable, never old draft or archived versions.
    published = ImportedTimetableDay.objects.filter(version__status="published").only("allocations")
    for record in published.iterator():
        for item in record.allocations:
            if isinstance(item, dict):
                code = item.get("code", "")
                if isinstance(code, str) and code.strip():
                    classes.add(code)
    return {code.strip().upper() for code in classes}


def preview_links(pairs):
    """Resolve current identities and class codes without altering data."""
    student_keys = {eqid for eqid, _ in pairs}
    students = {}
    for student in Student.objects.filter(student_id__in=student_keys).only(
        "pk", "student_id", "status"
    ):
        key = student.student_id.strip().upper()
        if key in students:
            raise ValueError("Ambiguous duplicate student identifiers require review.")
        students[key] = student
    # Account for legacy lower-case student IDs in the directory.
    if len(students) != len(student_keys):
        for student in Student.objects.exclude(student_id__in=student_keys).only(
            "pk", "student_id", "status"
        ):
            key = student.student_id.strip().upper()
            if key not in student_keys:
                continue
            if key in students:
                raise ValueError("Ambiguous case-insensitive EQIDs require administrator review.")
            students[key] = student

    classes = known_class_codes()
    unmatched_students = set()
    inactive_students = set()
    unmatched_classes = set()
    matched = []
    matched_examples = []
    witness = hashlib.sha256()
    for eqid, code in pairs:
        student = students.get(eqid)
        # The digest records what was matched, not personal identifiers in
        # OneSchoolArchiveBatch.summary.
        is_class = code in classes
        is_active = student is not None and student.status == Student.Status.ACTIVE
        witness.update((eqid + "\0" + code + "\0" +
                        (str(student.pk) if student else "-") + "\0" +
                        (student.status if student else "-") + "\0" +
                        str(int(is_class)) + "\n").encode("utf-8"))
        if student is None:
            unmatched_students.add(eqid)
        elif not is_active:
            inactive_students.add(eqid)
        if not is_class:
            unmatched_classes.add(code)
        if is_active and is_class:
            matched.append((student.pk, code))
            # Ephemeral administrator-only preview, never saved in summary/logs.
            if len(matched_examples) < 15:
                matched_examples.append({"eqid": student.student_id, "class_code": code})
    return {
        "matched": matched,
        "matched_examples": matched_examples,
        "matched_count": len(matched),
        "unmatched_student_count": len(unmatched_students),
        "inactive_student_count": len(inactive_students),
        "unmatched_class_count": len(unmatched_classes),
        "unmatched_class_examples": sorted(unmatched_classes)[:12],
        "skipped_count": len(pairs) - len(matched),
        "preview_signature": witness.hexdigest(),
    }


def apply_links(matched, batch):
    """Add only missing pairs; never remove or replace prior class allocations.

    A unique index keeps the same pair idempotent, including on later imports.
    This model does not grant staff permission to view student records.
    """
    student_ids = {sid for sid, _ in matched}
    codes = {code for _, code in matched}
    existing = set(OneSchoolClassMembership.objects.filter(
        student_id__in=student_ids, class_code__in=codes
    ).values_list("student_id", "class_code"))
    new_pairs = [(sid, code) for sid, code in matched if (sid, code) not in existing]
    OneSchoolClassMembership.objects.bulk_create(
        [OneSchoolClassMembership(student_id=sid, class_code=code, source_batch=batch)
         for sid, code in new_pairs], batch_size=200
    )
    return {"created": len(new_pairs), "already_present": len(matched) - len(new_pairs)}
