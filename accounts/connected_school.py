"""Connected school projection. No inferred identity, no live roll writing.

A publication is reviewed against a specific four-source set. The weekly
line exports are recurring planning data, not a daily OneSchool feed.
The staff PDF provides class descriptions, not extra scheduled lessons.
"""
import csv
import hashlib
import io
import json
import re
from datetime import date, time, timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    ConnectedSchoolPublication, ConnectedStaffMapping, OneSchoolArchiveBatch,
    OneSchoolClassMembership, OneSchoolLineAllocation, OneSchoolStaffClassReference,
    StaffProfile, Student,
)
from .oneschool_documents import parse_students
from .oneschool_class_csv import parse_student_classes
from .oneschool_source_review import read_batch_sources
from .permissions import can_teach

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")


def current():
    return ConnectedSchoolPublication.objects.filter(active=True).first()


def source_set():
    """Find the latest approved set, excluding stale/mismatched PDF versions."""
    batches = {}
    for kind in ("students", "tt_alignment", "staff_pdf", "class_members"):
        b = OneSchoolArchiveBatch.objects.filter(kind=kind, status="applied").order_by("-applied_at", "-pk").first()
        if b is None:
            raise ValueError("Apply all four OneSchool report types before publishing: missing " + kind)
        batches[kind] = b
    lines = batches["tt_alignment"].summary.get("applied", {})
    pdf = batches["staff_pdf"].summary.get("applied", {})
    if (not lines.get("timetable_version_id") or
            str(lines["timetable_version_id"]) != str(pdf.get("timetable_version_id"))):
        raise ValueError("The latest approved line exports and staff PDF must have the same timetable version.")
    if sorted(lines.get("lines", [])) != list(range(1, 8)):
        raise ValueError("Apply the complete seven-line timetable first.")
    return batches


def source_file(batch):
    originals = read_batch_sources(batch)
    if len(originals) != 1:
        raise ValueError("Expected one original source file in this applied import.")
    return originals[0][1]


def canonical(value):
    return (value or "").strip().upper()


def eligible_profile(profile):
    if not profile or not can_teach(profile.user) or not profile.timetable_link_verified:
        return False
    key = canonical(profile.staff_id)
    return bool(key and StaffProfile.objects.filter(staff_id__iexact=key).count() == 1)


def mapping_valid(mapping):
    return eligible_profile(mapping.profile) and canonical(mapping.profile.staff_id) == mapping.verified_staff_id


def observed_codes(batches):
    return {canonical(x) for x in OneSchoolLineAllocation.objects.filter(
        batch=batches["tt_alignment"]
    ).values_list("staff_code", flat=True) if canonical(x)} | {
        canonical(x) for x in OneSchoolStaffClassReference.objects.filter(
            batch=batches["staff_pdf"]
        ).values_list("staff_code", flat=True) if canonical(x)
    }


def parse_calendar(starts, ends, times, closures):
    if starts.year < 2000 or ends.year > 2100 or not 0 <= (ends - starts).days <= 180:
        raise ValueError("Choose a valid school term of no more than 181 calendar days (2000–2100).")
    schedule = {}
    reader = csv.reader(io.StringIO(times), strict=True)
    try:
        for row in reader:
            if not row or not any(x.strip() for x in row):
                continue
            if len(row) != 4:
                raise ValueError("Lesson times need Day,Period,Start,End on each line.")
            day, period, start, end = (x.strip() for x in row)
            if day not in DAYS or period not in ("1", "2", "3", "4"):
                raise ValueError("Use Monday–Friday and period numbers 1–4.")
            if not re.fullmatch(r"\d{2}:\d{2}", start) or not re.fullmatch(r"\d{2}:\d{2}", end):
                raise ValueError("Enter lesson times in 24-hour HH:MM format.")
            s, e = time.fromisoformat(start), time.fromisoformat(end)
            key = f"{DAYS.index(day)+1}:{period}"
            if key in schedule or e <= s:
                raise ValueError("Duplicate lesson time or end before start.")
            schedule[key] = [start, end]
    except csv.Error:
        raise ValueError("Invalid lesson-time CSV.") from None
    for day in range(1, 6):
        previous = ""
        for period in range(1, 5):
            key = f"{day}:{period}"
            if key not in schedule:
                raise ValueError("Enter all four period times for each weekday.")
            s, e = schedule[key]
            if s < previous:
                raise ValueError("Lesson times overlap or are out of period order.")
            previous = e
    closed = set()
    for line in closures.splitlines():
        if not line.strip():
            continue
        value = date.fromisoformat(line.strip())
        if not starts <= value <= ends:
            raise ValueError("Closure dates must be within the term.")
        closed.add(value.isoformat())
    return {"times": schedule, "closed": sorted(closed)}


def build_candidate(name, starts, ends, times, closures):
    calendar = parse_calendar(starts, ends, times, closures)
    batches = source_set()
    student_rows, _ = parse_students(source_file(batches["students"]))
    pairs, _ = parse_student_classes(source_file(batches["class_members"]))
    active_source_ids = {canonical(row["student_id"]) for row in student_rows}
    student_index = {}
    for student in Student.objects.only("pk", "student_id", "status"):
        key = canonical(student.student_id)
        if key not in active_source_ids:
            continue
        if key in student_index:
            raise ValueError("Ambiguous student identifiers in the existing directory.")
        student_index[key] = student
    classes = {}
    slots = []
    for row in OneSchoolLineAllocation.objects.filter(batch=batches["tt_alignment"]).order_by("weekday", "period", "class_code", "pk"):
        code = canonical(row.class_code)
        if not code or not 1 <= row.weekday <= 5 or not 1 <= row.period <= 4:
            raise ValueError("The approved timetable contains an invalid day or period.")
        classes.setdefault(code, {"code": code, "name": code, "years": [], "students": []})
        if row.year_level not in classes[code]["years"]:
            classes[code]["years"].append(row.year_level)
        slots.append({"code": code, "day": row.weekday, "period": row.period,
                      "staff": canonical(row.staff_code), "room": row.room_code})
    if not slots:
        raise ValueError("The approved seven-line batch has no class slots.")
    # PDF catalogue records can include roll classes without dated lesson slots.
    names = {}
    for row in OneSchoolStaffClassReference.objects.filter(batch=batches["staff_pdf"]).order_by("class_code", "pk"):
        code = canonical(row.class_code)
        classes.setdefault(code, {"code": code, "name": code, "years": [], "students": []})
        if row.subject_name:
            names.setdefault(code, set()).add(row.subject_name)
    for code, values in names.items():
        if len(values) == 1:
            classes[code]["name"] = next(iter(values))
    # Only pairs actually found in the chosen original CSV AND previously
    # accepted membership records qualify. Never union historic CSV rosters.
    approved = {(pk, canonical(code)) for pk, code in
                OneSchoolClassMembership.objects.values_list("student_id", "class_code")}
    unmatched = 0
    student_identity = {}
    for eqid, code in pairs:
        stu = student_index.get(canonical(eqid))
        code = canonical(code)
        if (not stu or stu.status != Student.Status.ACTIVE or code not in classes
                or (stu.pk, code) not in approved):
            unmatched += 1
            continue
        classes[code]["students"].append(stu.pk)
        student_identity[str(stu.pk)] = canonical(stu.student_id)
    for cls in classes.values():
        cls["students"] = sorted(set(cls["students"]))
        cls["years"].sort()
    allowed_codes = observed_codes(batches)
    bindings = {}
    for mapping in ConnectedStaffMapping.objects.select_related("profile__user").order_by("staff_code"):
        if mapping.staff_code in allowed_codes and mapping_valid(mapping):
            bindings[mapping.staff_code] = {
                "profile": mapping.profile_id, "user": mapping.profile.user_id,
                "staff_id": mapping.verified_staff_id,
                "verification": mapping.verified_at.isoformat(),
            }
    missing_codes = sorted({row["staff"] for row in slots if row["staff"] and row["staff"] not in bindings})
    stats = {"classes": len(classes), "slots": len(slots),
             "memberships": sum(len(c["students"]) for c in classes.values()),
             "skipped_pairs": unmatched, "unmapped_codes": missing_codes,
             "unassigned_slots": sum(not s["staff"] for s in slots),
             "legend_only": len(set(classes) - {s["code"] for s in slots}),
             "verified_mappings": len(bindings)}
    source_ids = {k: v.pk for k, v in batches.items()}
    snapshot = {"calendar": calendar, "classes": sorted(classes.values(), key=lambda x:x["code"]),
                "slots": slots, "bindings": bindings, "stats": stats,
                "student_identity": student_identity}
    value = {"name": name, "starts": starts.isoformat(), "ends": ends.isoformat(),
             "sources": source_ids, "snapshot": snapshot}
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                       separators=(",", ":")).encode()).hexdigest()
    return source_ids, snapshot, digest


def personal_codes(publication, user):
    """Verify current role, mapping and original published attestation every request."""
    if not can_teach(user):
        return set()
    if publication.snapshot.get("source") == "dated":
        profile = StaffProfile.objects.filter(user=user).first()
        if not eligible_profile(profile):
            return set()
        key = canonical(profile.staff_id)
        expected = publication.snapshot["bindings"].get(key)
        actual = {"profile": profile.pk, "user": user.pk, "staff_id": key}
        return {key} if expected == actual else set()
    mapping = ConnectedStaffMapping.objects.select_related("profile__user").filter(profile__user=user).first()
    if not mapping or not mapping_valid(mapping):
        return set()
    expected = publication.snapshot["bindings"].get(mapping.staff_code)
    actual = {"profile": mapping.profile_id, "user": user.pk,
              "staff_id": mapping.verified_staff_id,
              "verification": mapping.verified_at.isoformat()}
    return {mapping.staff_code} if expected == actual else set()


def date_is_school_day(publication, day):
    if publication.snapshot.get("source") == "dated":
        return (publication.starts <= day <= publication.ends
                and day.isoformat() in publication.snapshot["calendar"]["dates"])
    return (publication.starts <= day <= publication.ends and day.weekday() < 5
            and day.isoformat() not in publication.snapshot["calendar"]["closed"])


def selected_day(publication, requested):
    try:
        day = date.fromisoformat(requested or "")
        if publication.starts <= day <= publication.ends:
            return day
    except (ValueError, TypeError):
        pass
    return max(publication.starts, min(publication.ends, timezone.localdate()))


def visible_slots(publication, day, codes=None):
    if not date_is_school_day(publication, day):
        return []
    if publication.snapshot.get("source") == "dated":
        return [dict(s, period_label=s["period"]) for s in publication.snapshot["slots"]
                if s["date"] == day.isoformat() and (codes is None or s["staff"] in codes)]
    return [dict(s, period_label=f"P{s['period']}", start=publication.snapshot["calendar"]["times"][f"{s['day']}:{s['period']}"][0],
                 end=publication.snapshot["calendar"]["times"][f"{s['day']}:{s['period']}"][1])
            for s in publication.snapshot["slots"]
            if s["day"] == day.isoweekday() and (codes is None or s["staff"] in codes)]
