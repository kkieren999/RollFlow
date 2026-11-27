"""Review a complete dated OneSchool export as the authoritative school publication.

No inferred lessons, guessed identities, or automatic activation. Student rosters
come only from the chosen approved student and membership originals.
"""
import hashlib
import json
from collections import defaultdict

from .connected_school import canonical, eligible_profile, source_file
from .models import ImportedTimetable, OneSchoolArchiveBatch, OneSchoolClassMembership, StaffProfile, Student
from .oneschool_documents import parse_students
from .oneschool_class_csv import parse_student_classes

def published_version():
    return ImportedTimetable.objects.filter(status=ImportedTimetable.Status.PUBLISHED).first()

def build_dated_candidate(version):
    if version is None or version.status != ImportedTimetable.Status.PUBLISHED:
        raise ValueError("Publish the full dated OneSchool timetable CSV first.")
    batches = {}
    for kind in ("students", "class_members"):
        batch = OneSchoolArchiveBatch.objects.filter(kind=kind, status="applied").order_by("-applied_at", "-pk").first()
        if batch is not None:
            batches[kind] = batch
    roster_ready = len(batches) == 2
    classes = {}
    slots = []
    dates = []
    staff = set()
    rooms = set()
    for day in version.days.iterator():
        iso = day.date.isoformat()
        dates.append(iso)
        for row in day.allocations:
            code = canonical(row["code"])
            staff_id = canonical(row["staff_id"])
            if not code:
                raise ValueError("A published allocation has no class code.")
            record = classes.setdefault(code, {"code": code, "name": row["subject"], "years": [], "students": []})
            if row["year"] not in record["years"]:
                record["years"].append(row["year"])
            slots.append({"code": code, "date": iso, "day": day.date.isoweekday(),
                          "period": row["period"], "start": row["start"], "end": row["end"],
                          "staff": staff_id, "staff_code": row["staff_code"], "room": row["room"],
                          "name": row["subject"]})
            if staff_id:
                staff.add(staff_id)
            if row["room"]:
                rooms.add(row["room"])
    if not slots:
        raise ValueError("The published CSV has no lesson allocations.")
    students, pairs = [], []
    if roster_ready:
        students, _ = parse_students(source_file(batches["students"]))
        pairs, _ = parse_student_classes(source_file(batches["class_members"]))
    source_ids = {canonical(row["student_id"]) for row in students}
    student_index = {}
    for student in Student.objects.only("pk", "student_id", "status"):
        key = canonical(student.student_id)
        if key not in source_ids:
            continue
        if key in student_index:
            raise ValueError("Ambiguous student identifiers require review.")
        student_index[key] = student
    approved = {(pk, canonical(code)) for pk, code in OneSchoolClassMembership.objects.values_list("student_id", "class_code")}
    identity = {}
    skipped = 0
    for eqid, code in pairs:
        student = student_index.get(canonical(eqid))
        code = canonical(code)
        if (not student or student.status != Student.Status.ACTIVE or code not in classes
                or (student.pk, code) not in approved):
            skipped += 1
            continue
        classes[code]["students"].append(student.pk)
        identity[str(student.pk)] = canonical(student.student_id)
    for record in classes.values():
        record["students"] = sorted(set(record["students"]))
        record["years"].sort()
    bindings = {}
    known = defaultdict(list)
    for profile in StaffProfile.objects.select_related("user"):
        key = canonical(profile.staff_id)
        if key in staff:
            known[key].append(profile)
    for key, profiles in known.items():
        if len(profiles) == 1 and eligible_profile(profiles[0]):
            profile = profiles[0]
            bindings[key] = {"profile": profile.pk, "user": profile.user_id, "staff_id": key}
    stats = {"classes": len(classes), "slots": len(slots), "days": len(dates), "staff": len(staff),
             "rooms": len(rooms), "memberships": sum(len(c["students"]) for c in classes.values()),
             "skipped_pairs": skipped, "rosters_ready": roster_ready,
             "missing_roster_sources": sorted({"students", "class_members"} - set(batches)),
             "unmapped_codes": sorted(staff - set(bindings)),
             "missing_profiles": sorted(staff - set(known)),
             "unassigned_slots": sum(not s["staff"] for s in slots),
             "legend_only": 0, "verified_mappings": len(bindings)}
    snapshot = {"source": "dated", "data_validation": 1, "timetable_version": version.pk,
                "calendar": {"dates": dates, "closed": [], "times": {}},
                "classes": sorted(classes.values(), key=lambda c:c["code"]),
                "slots": slots, "bindings": bindings, "stats": stats, "student_identity": identity}
    sources = {kind: batch.pk for kind, batch in batches.items()}
    sources["dated_timetable"] = version.pk
    value = {"name": version.name, "sources": sources, "snapshot": snapshot}
    digest = hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
                                       separators=(",", ":")).encode()).hexdigest()
    return sources, snapshot, digest
