"""Minimal educational support; permission is independent of job title."""
from django.db.models import Q
from django.utils import timezone
from .attendance import own_lessons,lesson_key,roster_for,AttendanceUnavailable,publication_ready
from .connected_school import canonical,current
from .models import SupportTask,SupportReferral,StaffAccessGrant
from .school_access import grants_for
from .security_service import eligible_account
from .permissions import can_teach

OBSERVATIONS=(("engaged","Engaged in learning"),("participated","Participated in learning"),
              ("practice","Additional practice helpful"),("check_understanding","Check understanding"),
              ("extension","Extension opportunity"),("follow_up","Teacher follow-up needed"))
TASKS=(("practice","Guided practice"),("check_understanding","Check understanding"),
       ("materials","Prepare learning materials"),("organisation","Learning organisation"),
       ("extension","Extension activity"))
REFERRALS=(("learning_review","Learning support review"),("extension_review","Extension review"),
           ("classroom_strategy","Classroom strategy review"),("follow_up","Educational follow-up"))


def has_cap(user,cap):
    return eligible_account(user) and any(g.scope=="school" and cap in g.capabilities for g in grants_for(user))


def coordinator(user):
    return has_cap(user,"support_coordinator")


def board_allowed(user):
    return eligible_account(user) and (can_teach(user) or coordinator(user) or has_cap(user,"support_task") or has_cap(user,"support_referral"))


def lesson_context(pub,user,key,day,lock=False):
    if not eligible_account(user) or not can_teach(user):
        return None,[]
    row=next((r for r in own_lessons(pub,user,day) if lesson_key(r)==key),None)
    if not row:
        return None,[]
    return row,roster_for(pub,row["code"],day,lock=lock)


def regular_class(pub,user,code,day):
    return any(r["code"]==code and not r.get("relief") for r in own_lessons(pub,user,day))


def student_matches(record,pub):
    today=timezone.localdate()
    return bool(pub and record.publication_id==pub.pk and record.student.status=="active"
        and (not record.student.enrolled_on or record.student.enrolled_on<=today)
        and (not record.student.left_on or record.student.left_on>=today)
        and pub.snapshot.get("student_identity",{}).get(str(record.student_id))==canonical(record.student.student_id)
        and canonical(record.student.student_id)
        and any(c.get("code")==record.class_code and record.student_id in c.get("students",[]) for c in pub.snapshot.get("classes",[])))


def requester_current(record,user,pub):
    return record.requested_by_id==user.pk and student_matches(record,pub) and regular_class(pub,user,record.class_code,timezone.localdate())


def accessible(user,model,pub):
    qs=model.objects.filter(publication=pub).select_related("student","requested_by","assigned_to","publication")
    if not board_allowed(user) or not pub or not publication_ready(pub):
        return qs.none()
    if coordinator(user):
        return qs
    cap="support_task" if model==SupportTask else "support_referral"
    q=Q(pk__in=[])
    if has_cap(user,cap):
        q|=Q(assigned_to=user)
    if can_teach(user):
        q|=Q(requested_by=user,class_code__in={r["code"] for r in own_lessons(pub,user,timezone.localdate()) if not r.get("relief")})
    return qs.filter(q)


def permitted(record,user,pub):
    if not student_matches(record,pub):
        return False
    cap="support_task" if isinstance(record,SupportTask) else "support_referral"
    return coordinator(user) or requester_current(record,user,pub) or (record.assigned_to_id==user.pk and has_cap(user,cap))


def actions(record,user,pub):
    if not permitted(record,user,pub) or record.closed_at:
        return []
    if isinstance(record,SupportTask):
        result=[]
        if record.assigned_to_id==user.pk and has_cap(user,"support_task"):
            if record.state=="pending":result.append(("accept","Accept task"))
            if record.state=="accepted":result.append(("complete","Complete task"))
        if coordinator(user) or requester_current(record,user,pub):
            result.append(("cancel","Cancel task"))
        return result
    result=[]
    if coordinator(user) and record.state in ("pending","assigned","reviewed"):
        result.append(("assign","Assign / reassign reviewer"))
    if record.state=="assigned" and record.assigned_to_id==user.pk and has_cap(user,"support_referral"):
        result.append(("review","Record educational review"))
    if record.state=="reviewed" and (coordinator(user) or (record.assigned_to_id==user.pk and has_cap(user,"support_referral"))):
        result.append(("close","Close reviewed referral"))
    if coordinator(user) or (record.state=="pending" and requester_current(record,user,pub)):
        result.append(("withdraw","Withdraw referral"))
    return result
