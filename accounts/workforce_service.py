"""Operational overlays on a reviewed dated timetable; no source mutations."""
from django.contrib.auth.models import User
from django.utils import timezone
from .models import WorkforceEntry, WorkforceNotice, ReliefAttendanceAssignment, AttendanceRoll, StudentMovement
from .security_service import eligible_account
from .permissions import can_teach
from .school_access import grants_for
from .connected_school import personal_codes, visible_slots


def authority(user):
    return eligible_account(user) and (user.is_staff and user.is_superuser or any(
        g.scope=="school" and "workforce_monitor" in g.capabilities for g in grants_for(user)))


def self_allowed(user):
    return eligible_account(user) and bool(user.is_staff and user.is_superuser or can_teach(user) or grants_for(user))


def entries(pub,day,kind=None):
    qs=WorkforceEntry.objects.filter(publication=pub,day=day,cancelled_at__isnull=True)
    return qs.filter(kind=kind) if kind else qs


def closed(pub,day):
    return bool(pub and entries(pub,day,"closure").exists())


def absent(pub,day,user):
    return bool(pub and entries(pub,day,"absence").filter(staff=user).exists())


def duty_conflict(pub,day,user,start,end):
    return entries(pub,day,"duty").filter(staff=user,start__lt=end,end__gt=start).exists()


def effective_room(pub,day,row):
    change=entries(pub,day,"room").filter(class_code=row["code"],period=str(row["period"]),start=row["start"]).first()
    return change.location if change else row.get("room","")


def raw_busy(pub,day,user,start,end):
    """Conservative: original published allocations count even when covered."""
    codes=personal_codes(pub,user)
    return any(r.get("staff") in codes and r.get("start","")<end and start<r.get("end","")
        for r in visible_slots(pub,day)) or ReliefAttendanceAssignment.objects.filter(
        publication=pub,lesson_date=day,relief_teacher=user,cancelled_at__isnull=True,start__lt=end,end__gt=start).exists() or duty_conflict(pub,day,user,start,end)


def lesson_has_records(day,row):
    return AttendanceRoll.objects.filter(lesson_date=day,class_code=row["code"],start__lt=row["end"],end__gt=row["start"]).exists() or StudentMovement.objects.filter(
        lesson_date=day,class_code=row["code"],start__lt=row["end"],end__gt=row["start"]).exists()


def notify(pub,day,ids,message):
    for recipient in User.objects.filter(pk__in=set(ids),is_active=True):
        if self_allowed(recipient):
            WorkforceNotice.objects.create(recipient=recipient,publication=pub,day=day,message=message[:240])


def lesson_people(pub,day,row):
    binding=pub.snapshot.get("bindings",{}).get(row.get("staff"),{})
    ids=[binding.get("user")]
    ids.extend(ReliefAttendanceAssignment.objects.filter(publication=pub,lesson_date=day,class_code=row["code"],
        period=str(row["period"]),start=row["start"],cancelled_at__isnull=True).values_list("relief_teacher_id",flat=True))
    return [pk for pk in ids if pk]


def coverage(pub,day):
    from .attendance import lesson_valid,lesson_key
    if not pub or closed(pub,day):
        return []
    absences=set(entries(pub,day,"absence").values_list("staff_id",flat=True))
    relief={(a.class_code,a.period,a.start):a for a in ReliefAttendanceAssignment.objects.filter(publication=pub,
        lesson_date=day,cancelled_at__isnull=True).select_related("relief_teacher","regular_teacher")}
    bindings=pub.snapshot.get("bindings",{})
    rows=[]
    for r in visible_slots(pub,day):
        if not lesson_valid(r):
            continue
        regular=bindings.get(r.get("staff"),{}).get("user")
        if regular not in absences:
            continue
        a=relief.get(lesson_key(r))
        covered=bool(a and a.expires_at>timezone.now() and a.regular_teacher_id==regular and a.end==r["end"]
            and a.relief_teacher_id not in absences and personal_codes(pub,a.relief_teacher))
        rows.append(dict(code=r["code"],period=r["period"],start=r["start"],end=r["end"],
            room=effective_room(pub,day,r),covered=covered,relief=a.relief_teacher.username if covered else ""))
    return rows
