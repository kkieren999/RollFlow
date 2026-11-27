"""Classroom tools and explicitly assigned student support; protected endpoints."""
from datetime import timedelta
from .student_experience import follow_up_date
from django.contrib.auth.models import User
from django.db import transaction,IntegrityError
from django.http import HttpResponseBadRequest,HttpResponseForbidden,Http404
from django.shortcuts import redirect,render,get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET,require_http_methods,require_POST
from django.core.paginator import Paginator
from urllib.parse import urlencode
from .attendance import AttendanceUnavailable,publication_ready
from .attendance_admin_views import lock_sources
from .connected_school import current
from .models import ClassroomPlan,ClassroomObservation,SupportTask,SupportReferral,StaffAccessGrant,Student,StaffProfile
from .classroom_support import (OBSERVATIONS,TASKS,REFERRALS,has_cap,coordinator,board_allowed,lesson_context,
    accessible,permitted,actions,student_matches)
from .security_service import audit,eligible_account
from .permissions import can_teach
from .live_views import page,shell,roster_token


def key_from(request):
    return tuple(request.GET.get(k,"") for k in ("code","period","start"))


def class_url(key):
    return reverse("classroom-tools")+"?"+urlencode(dict(zip(("code","period","start"),key)))


def conflict(request,error):
    return render(request,"live_conflict.html",{**shell(request.user),"error":error},status=409)


def recipients(cap):
    # Explicit capability, never title. No student information on this picker.
    ids=StaffAccessGrant.objects.filter(scope="school").values_list("user_id",flat=True).distinct()
    return [u for u in User.objects.filter(pk__in=ids,is_active=True).order_by("username") if has_cap(u,cap)]


@never_cache
@require_http_methods(["GET","POST"])
def classroom(request):
    if not request.user.is_authenticated:
        return redirect("teacher-login")
    if not eligible_account(request.user) or not can_teach(request.user):
        return HttpResponseForbidden("Teaching access required.")
    if request.GET.get('date') and request.GET['date']!=timezone.localdate().isoformat():
        return HttpResponseBadRequest('Classroom actions require today’s verified lesson.')
    key=key_from(request)
    if not all(key):return HttpResponseBadRequest("Select a verified lesson.")
    try:
        with transaction.atomic():
            actor=request.user
            if request.method=="POST":
                # Lock actor and any selected recipient in deterministic order before source rows.
                ids=[actor.pk]
                raw=request.POST.get("recipient","")
                if raw.isascii() and raw.isdecimal() and len(raw)<=18:
                    ids.append(int(raw))
                locked={u.pk:u for u in User.objects.select_for_update(no_key=True).filter(pk__in=ids).order_by("pk")}
                actor=locked[actor.pk]
                list(StaffAccessGrant.objects.select_for_update().filter(user_id__in=ids).order_by('pk'))
                lock_sources()
                list(StaffProfile.objects.select_for_update().filter(user=actor))
            pub=current()
            day=timezone.localdate()
            row,students=lesson_context(pub,actor,key,day,lock=request.method=="POST")
            if not row:
                return HttpResponseForbidden("No verified allocation for this lesson.")
            regular=not row.get("relief")
            plan=ClassroomPlan.objects.filter(publication=pub,teacher=actor,class_code=key[0]).first() if regular else None
            if request.method=="POST":
                if not regular:
                    return HttpResponseForbidden("Temporary relief does not confer lasting classroom or support authority.")
                if request.POST.get("publication")!=str(pub.pk) or request.POST.get("roster_token")!=roster_token(students):
                    raise ValueError("Publication or roster changed. Reload.")
                action=request.POST.get("action")
                if action=="seating":
                    expected=str(plan.revision if plan else 0)
                    if request.POST.get("revision")!=expected:
                        raise ValueError("Seating plan changed. Reload before saving.")
                    fields={"seat_"+str(s.pk):str(s.pk) for s in students}
                    if {k for k in request.POST if k.startswith("seat_")}!=set(fields) or any(len(request.POST.getlist(k))!=1 for k in fields):
                        return HttpResponseBadRequest("Invalid seating roster.")
                    seats={}
                    for field,pk in fields.items():
                        value=request.POST[field]
                        if value:
                            if not value.isascii() or not value.isdecimal() or len(value)>3 or not 1<=int(value)<=200:
                                return HttpResponseBadRequest("Seat number must be between 1 and 200.")
                            seats[pk]=int(value)
                    if len(set(seats.values()))!=len(seats):
                        raise ValueError("Each seat can have only one student.")
                    if plan:
                        plan.seats=seats
                        plan.revision+=1
                        plan.save()
                    else:
                        plan=ClassroomPlan.objects.create(publication=pub,teacher=actor,class_code=key[0],seats=seats)
                    audit(actor,"classroom_seating_saved",after={"plan":plan.pk,"revision":plan.revision})
                elif action in ("observe","task","referral"):
                    student=next((s for s in students if str(s.pk)==request.POST.get("student")),None)
                    if not student:return HttpResponseForbidden("Student is outside your verified roster.")
                    category=request.POST.get("category","")
                    if action=="observe":
                        if category not in dict(OBSERVATIONS):return HttpResponseBadRequest("Invalid observation category.")
                        item=ClassroomObservation.objects.create(publication=pub,teacher=actor,student=student,
                            class_code=key[0],lesson_date=day,category=category)
                    elif action=="task":
                        if category not in dict(TASKS):return HttpResponseBadRequest("Invalid learning task.")
                        recipient=locked.get(int(raw)) if raw.isascii() and raw.isdecimal() and len(raw)<=18 else None
                        if not recipient or not has_cap(recipient,"support_task"):
                            return HttpResponseForbidden("Recipient lacks explicit learning task permission.")
                        item=SupportTask.objects.create(publication=pub,student=student,class_code=key[0],requested_by=actor,
                            assigned_to=recipient,category=category,due_on=follow_up_date(request.POST.get("due"),day))
                    else:
                        if category not in dict(REFERRALS):return HttpResponseBadRequest("Invalid educational referral.")
                        item=SupportReferral.objects.create(publication=pub,student=student,class_code=key[0],requested_by=actor,
                            category=category,follow_up_on=follow_up_date(request.POST.get("due"),day))
                    audit(actor,"classroom_"+action,after={"record":item.pk,**({"due":(item.due_on if action=="task" else item.follow_up_on).isoformat()} if action in ("task","referral") else {})})
                elif action=="withdraw_observation":
                    item=get_object_or_404(ClassroomObservation.objects.select_for_update(),pk=request.POST.get("observation"),
                        publication=pub,teacher=actor,class_code=key[0],student_id__in=[s.pk for s in students],withdrawn_at__isnull=True)
                    item.withdrawn_at=timezone.now()
                    item.save(update_fields=["withdrawn_at"])
                    audit(actor,"classroom_observation_withdrawn",after={"record":item.pk})
                else:return HttpResponseBadRequest("Unknown classroom action.")
                return redirect(class_url(key))
            seats=plan.seats if plan else {}
            roster=[{"pk":s.pk,"name":f"{s.last_name}, {s.preferred_name or s.first_name}","seat":seats.get(str(s.pk),"")} for s in students]
            observations=ClassroomObservation.objects.filter(publication=pub,teacher=actor,class_code=key[0],
                student_id__in=[s.pk for s in students],withdrawn_at__isnull=True).select_related("student").order_by("-created_at")[:50] if regular else []
            occupied=sorted((s for s in roster if s['seat']),key=lambda s:s['seat'])
            return page(request,"classroom_tools.html",row=row,regular=regular,roster=roster,plan=plan,occupied=occupied,
                publication=pub,roster_token=roster_token(students),observations=observations,
                observation_choices=OBSERVATIONS,task_choices=TASKS,referral_choices=REFERRALS,
                today=day,default_due=day+timedelta(days=7),max_due=day+timedelta(days=90),
                recipients=recipients("support_task") if regular else [])
    except (ValueError,AttendanceUnavailable,IntegrityError) as exc:
        return conflict(request,str(exc) if isinstance(exc,ValueError) else "Concurrent change. Reload.")


def project(record,user,pub,kind):
    return {"pk":record.pk,"kind":kind,"student":f"{record.student.preferred_name or record.student.first_name} {record.student.last_name}",
        "class_code":record.class_code,"category":dict(TASKS if kind=="task" else REFERRALS).get(record.category,record.category),
        "state":record.state,"revision":record.revision,"due":record.due_on if kind=="task" else record.follow_up_on,
        "requester":record.requested_by.username,"recipient":record.assigned_to.username if record.assigned_to else "Unassigned",
        "actions":actions(record,user,pub),"overdue":not record.closed_at and (record.due_on if kind=="task" else record.follow_up_on)<timezone.localdate()}


@never_cache
@require_GET
def board(request):
    if not request.user.is_authenticated:return redirect("teacher-login")
    if not board_allowed(request.user):return HttpResponseForbidden("Assigned educational support access required.")
    pub=current()
    rows=[]
    view=request.GET.get("view","all")
    if view not in ("all","tasks","referrals","followups","closed"):
        return HttpResponseBadRequest("Unknown support view.")
    for model,kind in ((SupportTask,"task"),(SupportReferral,"referral")):
        for record in accessible(request.user,model,pub).order_by("-created_at","-pk"):
            if permitted(record,request.user,pub):
                rows.append(project(record,request.user,pub,kind))
    counts={"tasks":sum(r["kind"]=="task" for r in rows),"referrals":sum(r["kind"]=="referral" for r in rows),"followups":sum(r["overdue"] for r in rows),"closed":sum(r["state"] in ("closed","withdrawn","completed","cancelled") for r in rows)}
    rows=[r for r in rows if view=="all" or (view=="tasks" and r["kind"]=="task") or (view=="referrals" and r["kind"]=="referral") or (view=="followups" and r["overdue"]) or (view=="closed" and r["state"] in ("closed","withdrawn","completed","cancelled"))]
    rows.sort(key=lambda r:(not r["overdue"],r["due"],r["kind"],r["pk"]))
    today=timezone.localdate()
    return page(request,"support_board.html",rows=Paginator(rows,50).get_page(request.GET.get("page")),view=view,counts=counts,today=today,max_due=today+timedelta(days=90),
        support_coordinator=coordinator(request.user),reviewers=recipients("support_referral") if coordinator(request.user) else [])


@never_cache
@require_POST
def change(request,kind,pk):
    if not request.user.is_authenticated:return redirect("teacher-login")
    model={"task":SupportTask,"referral":SupportReferral}.get(kind)
    if not model:raise Http404()
    try:
        with transaction.atomic():
            ids=[request.user.pk]
            raw=request.POST.get("recipient","")
            if raw.isascii() and raw.isdecimal() and len(raw)<=18:ids.append(int(raw))
            users={u.pk:u for u in User.objects.select_for_update(no_key=True).filter(pk__in=ids).order_by("pk")}
            actor=users[request.user.pk]
            list(StaffAccessGrant.objects.select_for_update().filter(user_id__in=ids).order_by("pk"))
            if not board_allowed(actor):return HttpResponseForbidden("Support access revoked.")
            lock_sources()
            pub=current()
            candidate=get_object_or_404(accessible(actor,model,pub),pk=pk)
            list(Student.objects.select_for_update().filter(pk=candidate.student_id))
            record=get_object_or_404(accessible(actor,model,pub).select_for_update(of=("self",)),pk=pk)
            if not permitted(record,actor,pub):raise Http404()
            if request.POST.get("revision")!=str(record.revision):raise ValueError("Support record changed. Refresh.")
            action=request.POST.get("action")
            if action not in dict(actions(record,actor,pub)):return HttpResponseForbidden("Support action not authorised.")
            old=record.state
            if action=="reschedule":
                if not request.POST.get("due"):return HttpResponseBadRequest("Choose a follow-up date.")
                field="due_on" if kind=="task" else "follow_up_on"
                prior=getattr(record,field)
                due=follow_up_date(request.POST["due"])
                if due==prior:raise ValueError("Choose a different follow-up date.")
                setattr(record,field,due)
                record.revision+=1
                record.save(update_fields=[field,"revision"])
                audit(actor,"support_reschedule",after={"kind":kind,"record":record.pk,"revision":record.revision,"prior_due":prior.isoformat(),"due":due.isoformat()})
                return redirect("support-board")
            if action=="assign":
                recipient=users.get(int(raw)) if raw.isascii() and raw.isdecimal() and len(raw)<=18 else None
                if not recipient or not has_cap(recipient,"support_referral"):
                    return HttpResponseForbidden("Reviewer lacks explicit referral permission.")
                record.assigned_to=recipient
            record.state={"assign":"assigned","review":"reviewed","close":"closed","withdraw":"withdrawn",
                "accept":"accepted","complete":"completed","cancel":"cancelled"}[action]
            record.revision+=1
            if record.state in ("closed","withdrawn","completed","cancelled"):record.closed_at=timezone.now()
            record.save()
            audit(actor,"support_"+action,after={"kind":kind,"record":record.pk,"revision":record.revision,"prior_state":old,"state":record.state})
    except (ValueError,IntegrityError) as exc:return conflict(request,str(exc) if isinstance(exc,ValueError) else 'Concurrent support change. Reload.')
    return redirect("support-board")
