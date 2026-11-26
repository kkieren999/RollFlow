"""Daily exception-aware attendance status and frozen-roll verification."""
from collections import Counter
from django.utils import timezone
from .attendance import lesson_valid, lesson_key, publication_ready, roster_for, AttendanceUnavailable, active_relief
from .connected_school import visible_slots, personal_codes, canonical
from .models import AttendanceRoll, AttendanceRevision, Student, StaffProfile


def frozen_students(roll, lock=False):
    """Verify the original publication and latest immutable revision, not a new roster."""
    if not roll.submitted_at or not roll.roster or len(set(roll.roster))!=len(roll.roster):
        raise ValueError("Only a complete submitted roll may be corrected.")
    if set(roll.marks)!=set(map(str,roll.roster)) or any(v not in ("P","A","L") for v in roll.marks.values()):
        raise ValueError("The submitted marks are incomplete.")
    latest=AttendanceRevision.objects.filter(roll=roll,revision=roll.revision).first()
    if not latest or latest.action not in ("submit","correct") or latest.marks!=roll.marks:
        raise ValueError("Revision history does not match the recorded roll.")
    if latest.action=="submit" and latest.actor_id!=roll.teacher_id:
        raise ValueError("Original submission actor does not match.")
    if latest.action=="correct" and not latest.reason:
        raise ValueError("Correction reason is missing.")
    pub=roll.publication
    classes=[c for c in pub.snapshot.get("classes",[]) if c.get("code")==roll.class_code]
    if len(classes)!=1 or set(classes[0].get("students",[]))!=set(roll.roster):
        raise ValueError("The frozen roster differs from the original publication.")
    qs=Student.objects.filter(pk__in=roll.roster).order_by("pk")
    if lock:
        qs=qs.select_for_update()
    students=list(qs)
    identities=pub.snapshot.get("student_identity",{})
    if len(students)!=len(roll.roster) or any(not identities.get(str(s.pk)) or identities[str(s.pk)]!=canonical(s.student_id) for s in students):
        raise ValueError("Student identity changed. Review required.")
    return students


def daily_status(pub,day,now=None):
    now=now or timezone.localtime()
    ready=publication_ready(pub)
    source=visible_slots(pub,day) if pub and pub.snapshot.get("source")=="dated" else []
    slots=[r for r in source if lesson_valid(r)]
    keys=Counter(lesson_key(r) for r in slots)
    rolls={(r.class_code,r.period,r.start):r for r in AttendanceRoll.objects.filter(lesson_date=day)
           .select_related("publication").prefetch_related("transfer_reviews")}
    bindings=pub.snapshot.get("bindings",{}) if pub else {}
    profiles={p.user_id:p for p in StaffProfile.objects.filter(user_id__in=[b.get("user") for b in bindings.values() if isinstance(b,dict)]).select_related("user")}
    verified=set()
    for p in profiles.values():
        verified.update(personal_codes(pub,p.user))
    relief=active_relief(pub,day) if pub else {}
    seen=set()
    rows=[]
    summary=Counter()
    def add(key,state,roll=None,expected=True):
        summary[state]+=1
        counts=Counter(roll.marks.values()) if roll and roll.submitted_at and state=="Submitted" else {}
        reconcile="—"
        if counts:
            reconcile="Manually reconciled" if any(x.revision==roll.revision and x.reconciled_at for x in roll.transfer_reviews.all()) else "Review required"
        rows.append(dict(code=key[0],period=key[1],start=key[2],status=state,
            present=counts.get("P","—"),absent=counts.get("A","—"),late=counts.get("L","—"),
            reconciliation=reconcile,roll_id=roll.pk if roll else None,
            submitted=bool(roll and roll.submitted_at),expected=expected))
    for row in sorted(slots,key=lambda r:(r["start"],r["code"])):
        key=lesson_key(row)
        if key in seen:
            continue
        seen.add(key)
        roll=rolls.get(key)
        overlapping=any(other is not row and (other.get("staff")==row.get("staff") or other["code"]==row["code"])
            and other["start"]<row["end"] and row["start"]<other["end"] for other in slots)
        if keys[key]!=1 or overlapping:
            state="Ambiguous allocation — review required"
        elif roll and roll.publication_id!=pub.pk:
            state="Publication changed — review required"
        elif roll and roll.submitted_at:
            try:
                frozen_students(roll)
                state="Submitted"
            except ValueError:
                state="Submitted data conflict — review required"
        elif not ready:
            state="Source not ready — review required"
        elif row.get("staff") not in verified:
            state="Unverified allocation — review required"
        elif key in relief and not personal_codes(pub,relief[key].relief_teacher):
            state="Relief identity — review required"
        else:
            try:
                roster_for(pub,row["code"],day)
                overdue=day<now.date() or (day==now.date() and now.strftime("%H:%M")>=row["end"])
                state=("Overdue draft" if roll else "Overdue — Not started") if overdue else ("Draft" if roll else "Not started")
            except AttendanceUnavailable:
                state="Roster not ready — review required"
        add(key,state,roll)
    for key,roll in rolls.items():
        if key not in seen:
            add(key,"No current allocation — review required",roll,False)
    # The count is scheduled unique valid lesson keys, never just existing roll rows.
    return rows,{"expected":len(seen),"submitted":summary["Submitted"],
        "outstanding":len(seen)-summary["Submitted"],"overdue":summary["Overdue draft"]+summary["Overdue — Not started"],
        "exceptions":sum(n for label,n in summary.items() if "review required" in label),
        "excluded":len(source)-len(slots),
        "reconciled":sum(r["reconciliation"]=="Manually reconciled" for r in rows)}
