"""Read-only cross-module links and scoped projections, never access grants."""
from urllib.parse import urlencode
from django.urls import reverse
from django.utils import timezone
from .attendance import (own_lessons, roster_for, roll_for, roll_matches,
                         AttendanceUnavailable, lesson_key)
from .movement_service import visible, identity_matches
from .models import AttendanceRevision, AttendanceRoll


def lesson_links(row, now=None):
    """The destination endpoints recheck authority and the exact current lesson."""
    now = now or timezone.localtime()
    params = urlencode(dict(zip(("code", "period", "start"), lesson_key(row))))
    def url(name):
        return reverse(name) + "?" + params
    return {"roll": url("live-roll"), "classroom": url("classroom-tools"),
            "movement": url("movement-issue") if row["start"] <= now.strftime("%H:%M") < row["end"] else "",
            "schedule": reverse("live-day"), "class": reverse("teacher-class-detail", kwargs={"code": row["code"]})}


def student_workflow(pub, user, record, today=None):
    """A student profile only joins records already authorised by their own module.

    No other teacher's marks, inferred attendance or historical roster authority.
    """
    today = today or timezone.localdate()
    student = record["student"]
    classes = {c["code"] for c in record["classes"]}
    lessons = []
    for row in own_lessons(pub, user, today):
        if row["code"] not in classes:
            continue
        try:
            roster = roster_for(pub, row["code"], today)
        except AttendanceUnavailable:
            continue
        if student.pk not in {s.pk for s in roster}:
            continue
        roll = roll_for(today, row)
        status = "Not recorded"
        mark = ""
        links = lesson_links(row)
        overlap = AttendanceRoll.objects.filter(lesson_date=today, class_code=row["code"],
                    start__lt=row["end"], end__gt=row["start"]).exclude(pk=roll.pk if roll else None).exists()
        if overlap:
            status = "Review required"
            links = {}
        elif roll:
            if not roll_matches(roll, pub, row, user, roster):
                status = "Review required"
                links = {}
            elif not roll.submitted_at:
                status = "Draft — not certified"
            else:
                revision = AttendanceRevision.objects.filter(roll=roll, revision=roll.revision).first()
                if (revision and revision.marks == roll.marks and set(roll.marks) == set(map(str, roll.roster))
                        and all(v in ("P", "A", "L") for v in roll.marks.values())
                        and ((revision.action == "submit" and revision.actor_id == roll.teacher_id)
                             or (revision.action == "correct" and revision.reason))):
                    status = "Submitted"
                    mark = {"P":"Present", "A":"Absent", "L":"Late"}.get(roll.marks.get(str(student.pk)), "")
                else:
                    status = "Review required"
                    links = {}
        lessons.append({"code": row["code"], "period": row["period"], "start": row["start"],
                        "end": row["end"], "room": row.get("room", ""), "relief": bool(row.get("relief")),
                        "status": status, "mark": mark, "links": links})
    # Bound the preview. Older or non-visible records are not fetched or inferred.
    candidates = visible(user).filter(student_id=student.pk, lesson_date=today).order_by("-departed_at", "-pk")[:21]
    movements = []
    for m in candidates:
        if identity_matches(m):
            movements.append({"state": m.get_state_display(), "destination": m.destination_name,
                              "departure": m.departed_at, "period": m.period,
                              "url": reverse("movement-detail", kwargs={"pk": m.pk})})
    return {"day": today, "lessons": sorted(lessons, key=lambda x:(x["start"], x["code"])),
            "movements": movements[:20],
            "movement_url": reverse("movement-board") + "?" + urlencode({"student": student.pk, "date": today.isoformat()})}
