"""Operational overlays on a reviewed dated timetable; no source mutations."""
from django.contrib.auth.models import User
from django.utils import timezone
from .models import WorkforceEntry, WorkforceNotice, ReliefAttendanceAssignment, AttendanceRoll, StudentMovement, StaffProfile
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
    profile=StaffProfile.objects.filter(user=user).first()
    # A known raw staff identifier without verified binding is a conflict, not free time.
    if profile and profile.staff_id:
        codes=codes|{profile.staff_id.strip().upper()}
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
    from .attendance import lesson_valid,lesson_key,publication_ready,own_lessons
    if not publication_ready(pub) or closed(pub,day):
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
            and a.relief_teacher_id not in absences and any(lesson_key(x)==lesson_key(r) and x.get("relief")
                for x in own_lessons(pub,a.relief_teacher,day)))
        rows.append(dict(code=r["code"],period=r["period"],start=r["start"],end=r["end"],
            room=effective_room(pub,day,r),covered=covered,relief=a.relief_teacher.username if covered else ""))
    return rows


def relief_candidates(pub,day,row):
    """Read-only conservative eligibility preview for one exact reviewed lesson.

    The existing locked assignment endpoint remains authoritative. No private
    absence reasons or guesses about staff availability are returned.
    """
    from .attendance import publication_ready,own_lessons,lesson_key,roster_for,AttendanceUnavailable
    from .connected_school import date_is_school_day
    from .security_service import eligible_account
    if not publication_ready(pub) or not date_is_school_day(pub,day) or closed(pub,day):
        return [],"Review a current published school day."
    key=lesson_key(row)
    binding=pub.snapshot.get("bindings",{}).get(row.get("staff"),{})
    regular=User.objects.filter(pk=binding.get("user")).first()
    if not regular or not any(lesson_key(r)==key for r in own_lessons(pub,regular,day,ignore_absence=True)):
        return [],"Original allocation is not uniquely verified or already covered."
    if lesson_has_records(day,row) or ReliefAttendanceAssignment.objects.filter(publication=pub,
        lesson_date=day,class_code=key[0],period=key[1],start=key[2],cancelled_at__isnull=True).exists():
        return [],"Existing roll, movement or assignment requires review."
    try:roster_for(pub,row["code"],day)
    except AttendanceUnavailable:return [],"Roster is not ready."
    result=[]
    for p in StaffProfile.objects.filter(timetable_link_verified=True,user__is_active=True).select_related("user").order_by("user__username"):
        u=p.user
        if u.pk==regular.pk or not eligible_account(u) or not personal_codes(pub,u):
            continue
        if absent(pub,day,u) or raw_busy(pub,day,u,row["start"],row["end"]):
            continue
        result.append({"pk":u.pk,"name":u.get_full_name() or u.username})
    return result,"No recorded conflicts in this reviewed timetable; verify suitability before assigning."
