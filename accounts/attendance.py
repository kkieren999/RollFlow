"""First protected attendance workflow: reviewed dated publication, today's own lessons."""
from collections import Counter
import re
from django.conf import settings
from datetime import time
from django.utils import timezone
from .connected_school import canonical, personal_codes, visible_slots
from .models import AttendanceRoll, ImportedTimetable, Student, ReliefAttendanceAssignment
from .school_access import grants_for


MARKS = (("P", "Present"), ("A", "Absent"), ("L", "Late"))


class AttendanceUnavailable(ValueError):
    pass


def can_monitor(user):
    return bool(user.is_authenticated and user.is_active and (
        (user.is_staff and user.is_superuser) or any(
            g.scope == "school" and "attendance_monitor" in g.capabilities
            for g in grants_for(user))))


def publication_ready(pub):
    if not pub or pub.snapshot.get("source") != "dated":
        return False
    from .data_reconciliation import source_issues
    if (settings.ROLLFLOW_SCHOOL_MODE or pub.snapshot.get("data_validation") == 1 or pub.source_batches) and source_issues(pub):
        return False
    stats = pub.snapshot.get("stats", {})
    return (stats.get("rosters_ready") is True and stats.get("skipped_pairs") == 0
            and ImportedTimetable.objects.filter(pk=pub.snapshot.get("timetable_version"),
                status=ImportedTimetable.Status.PUBLISHED).exists())


def lesson_key(row):
    return (row["code"], str(row["period"]), row["start"])


def non_instructional(row):
    return bool(re.search(r"\b(lunch|recess|break|interval|playground duty|supervision)\b", str(row.get("period","")), re.I))


def lesson_valid(row):
    try:
        code, period, start = lesson_key(row)
        end = row["end"]
        if non_instructional(row):
            return False
        return (0 < len(code) <= 30 and 0 < len(period) <= 50 and len(start) == len(end) == 5
                and time.fromisoformat(start) < time.fromisoformat(end))
    except (KeyError, TypeError, ValueError):
        return False


def lesson_started(day,row,now=None):
    now = now or timezone.localtime()
    return day < now.date() or (day == now.date() and now.strftime("%H:%M") >= row["start"])


def active_relief(pub, day):
    return {(a.class_code,a.period,a.start):a for a in ReliefAttendanceAssignment.objects.filter(
        publication=pub,lesson_date=day,cancelled_at__isnull=True,expires_at__gt=timezone.now()
    ).select_related("relief_teacher","regular_teacher")}


def own_lessons(pub, user, day, ignore_absence=False):
    from .workforce_service import closed, absent, effective_room
    if not publication_ready(pub) or closed(pub,day) or (not ignore_absence and absent(pub,day,user)):
        return []
    all_slots = [r for r in visible_slots(pub, day) if lesson_valid(r)]
    counts = Counter(lesson_key(r) for r in all_slots)
    codes = personal_codes(pub, user)
    relief = active_relief(pub,day)
    result=[]
    for r in all_slots:
        key=lesson_key(r)
        assignment=relief.get(key)
        if assignment:
            # Recheck both identities and the original binding, not just the
            # assignee. An invalidated original allocation must fail closed.
            if (assignment.relief_teacher_id!=user.pk or assignment.end!=r["end"] or not codes
                    or r.get("staff") not in personal_codes(pub,assignment.regular_teacher)):
                continue
            from .workforce_service import duty_conflict
            if duty_conflict(pub,day,user,r["start"],r["end"]):
                continue
        elif r.get("staff") not in codes:
            continue
        if counts[key]!=1 or any(other is not r and (other.get("staff")==r.get("staff") or other["code"]==r["code"])
                 and other["start"]<r["end"] and r["start"]<other["end"] for other in all_slots):
            continue
        result.append(dict(r, relief=bool(assignment), room=effective_room(pub,day,r)))
    return result


def roster_for(pub, code, day, lock=False):
    records = [c for c in pub.snapshot.get("classes", []) if c.get("code") == code]
    if len(records) != 1:
        raise AttendanceUnavailable("Class roster needs administrator review.")
    ids = records[0].get("students", [])
    identity = pub.snapshot.get("student_identity", {})
    if not ids or len(ids) != len(set(ids)):
        raise AttendanceUnavailable("No complete reviewed roster is available.")
    qs = Student.objects.filter(pk__in=ids)
    if lock:
        qs = qs.select_for_update()
    students = list(qs.order_by("pk"))
    if len(students) != len(ids):
        raise AttendanceUnavailable("Roster changed; review and republish.")
    for student in students:
        if (canonical(student.student_id) != identity.get(str(student.pk))
                or student.status != Student.Status.ACTIVE
                or (student.enrolled_on and student.enrolled_on > day)
                or (student.left_on and student.left_on < day)):
            raise AttendanceUnavailable("Student identity or enrolment changed; review and republish.")
    # Freeze only IDs, never names or EQIDs in the attendance revision.
    return sorted(students, key=lambda s:(s.last_name.casefold(), s.first_name.casefold(), s.pk))


def roll_for(day, row, lock=False):
    qs = AttendanceRoll.objects
    if lock:
        qs = qs.select_for_update()
    code, period, start = lesson_key(row)
    return qs.filter(lesson_date=day, class_code=code, period=period, start=start).first()


def roll_matches(roll, pub, row, user, students):
    return (roll.publication_id == pub.pk and roll.teacher_id == user.pk
            and roll.end == row["end"] and roll.roster == sorted(s.pk for s in students))


def status_label(roll, pub):
    if not roll:
        return "Not started"
    if not pub or roll.publication_id != pub.pk:
        return "Publication changed — review required"
    return "Submitted" if roll.submitted_at else "Draft"
