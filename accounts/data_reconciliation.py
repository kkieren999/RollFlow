"""Read-only publication comparisons and conservative data-readiness checks."""
from collections import Counter, defaultdict
from .models import OneSchoolArchiveBatch, ImportedTimetable, AttendanceRoll


def latest_batches():
    return {kind: OneSchoolArchiveBatch.objects.filter(kind=kind,status="applied")
            .order_by("-applied_at","-pk").first() for kind in ("students","class_members")}


def source_issues(publication):
    """Check current applied sources without reading private files during every teacher request."""
    if not publication or publication.snapshot.get("source") != "dated":
        return ["A dated publication is required."]
    sources = publication.source_batches
    # Legacy/test snapshots may not have source provenance; do not invent it.
    # Newly generated dated snapshots always declare a dated_timetable source.
    if not sources or "dated_timetable" not in sources:
        return ["Publication has no reviewed source provenance."]
    issues = []
    if not ImportedTimetable.objects.filter(pk=sources.get("dated_timetable"),status="published").exists():
        issues.append("The published timetable version changed.")
    for kind,batch in latest_batches().items():
        if not batch or batch.source_purged_at or batch.pk != sources.get(kind):
            issues.append("Review and republish the " + ("student directory" if kind=="students" else "class membership") + " source.")
    return issues


def compare_publications(previous, candidate):
    old = previous.snapshot if previous else {}
    old_classes = {c["code"]: c for c in old.get("classes", [])}
    new_classes = {c["code"]: c for c in candidate.get("classes", [])}
    def members(classes):
        return {(code, pk) for code,c in classes.items() for pk in c.get("students", [])}
    def slots(snapshot):
        return Counter((s.get("date"),s.get("day"),s.get("code"),str(s.get("period")),
                        s.get("start"),s.get("end"),s.get("staff"),s.get("room")) for s in snapshot.get("slots", []))
    a,b=members(old_classes),members(new_classes)
    x,y=slots(old),slots(candidate)
    old_bindings,new_bindings=old.get("bindings",{}),candidate.get("bindings",{})
    return {
        "classes_added":len(new_classes.keys()-old_classes.keys()),
        "classes_removed":len(old_classes.keys()-new_classes.keys()),
        "membership_added":len(b-a), "membership_removed":len(a-b),
        "allocations_added":sum((y-x).values()), "allocations_removed":sum((x-y).values()),
        "bindings_changed":sum(old_bindings.get(k)!=new_bindings.get(k) for k in old_bindings.keys()|new_bindings.keys()),
        "prior_rolls":AttendanceRoll.objects.filter(publication=previous).count() if previous else 0,
    }


def diagnostics(snapshot):
    """Non-inferred facts: duplicate/overlap warnings, empty class roster counts."""
    rows=snapshot.get("slots",[])
    keys=Counter((s.get("date"),s.get("code"),str(s.get("period")),s.get("start")) for s in rows)
    groups=defaultdict(list)
    for s in rows:
        for field in ("staff","code"):
            if s.get(field):
                groups[(s.get("date"),field,s[field])].append(s)
    overlaps=0
    for group in groups.values():
        latest=""
        for s in sorted(group,key=lambda row:(row.get("start",""),row.get("end",""))):
            if s.get("start","")<latest:
                overlaps+=1
            latest=max(latest,s.get("end",""))
    return {"duplicate_lesson_keys":sum(n>1 for n in keys.values()),
            "overlap_warnings":overlaps,
            "empty_rosters":sum(not c.get("students") for c in snapshot.get("classes",[])),
            "missing_staff":len(snapshot.get("stats",{}).get("unmapped_codes",[])),
            "skipped_pairs":snapshot.get("stats",{}).get("skipped_pairs",0)}
