"""Protected movement passes: classroom departure, reception, release and return."""
from datetime import timedelta,date
from django import forms
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction,IntegrityError
from django.http import HttpResponseForbidden,HttpResponseBadRequest
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET,require_http_methods,require_POST
from .attendance import own_lessons,lesson_key,roster_for,AttendanceUnavailable
from .attendance_admin_views import lock_sources
from .connected_school import current
from .models import MovementDestination,StudentMovement,StaffAccessGrant,StaffProfile,Student
from .movement_service import authority,may_access,visible,identity_matches,actions_for,record,transition,CLOSE_REASONS
from .security_service import eligible_account,lock_administrator,audit
from .staff_views import administrator
from .permissions import can_teach
from .live_views import page, shell


def current_lesson(pub,user,day,key,now):
    if not pub or day!=now.date():
        return None
    return next((r for r in own_lessons(pub,user,day) if lesson_key(r)==key and r["start"]<=now.strftime("%H:%M")<r["end"]),None)


def student_label(m):
    if not identity_matches(m):
        return "Identity changed — administrator review"
    return f"{m.student.preferred_name or m.student.first_name} {m.student.last_name}"


def projection(m,user,now):
    return {"pk":m.pk,"student":student_label(m),"class_code":m.class_code,"destination":m.destination_name,
        "origin":m.origin_room,"state":m.get_state_display(),"departure":m.departed_at,"due":m.due_at,
        "overdue":not m.closed_at and m.due_at<=now,"revision":m.revision,
        "actions":actions_for(user,m),"closed":m.closed_at}


@never_cache
@require_GET
def board(request):
    if not request.user.is_authenticated:
        return redirect("teacher-login")
    if not may_access(request.user):
        return HttpResponseForbidden("Movement access required.")
    now=timezone.now()
    qs=visible(request.user)
    try:
        day=date.fromisoformat(request.GET.get("date") or timezone.localdate().isoformat())
        if day>timezone.localdate():
            raise ValueError()
    except ValueError:
        return HttpResponseBadRequest("Choose a valid current or historical date.")
    # Open passes carry over across midnight; never silently close at bell time.
    active=qs.filter(closed_at__isnull=True).order_by("due_at","pk")
    history=qs.filter(lesson_date=day,closed_at__isnull=False).order_by("-closed_at","-pk")
    active_page=Paginator(active,50).get_page(request.GET.get("open_page"))
    history_page=Paginator(history,50).get_page(request.GET.get("page"))
    return page(request,"movement_board.html",day=day,open_count=active.count(),
        overdue_count=active.filter(due_at__lte=now).count(),active_page=active_page,history_page=history_page,
        open_rows=[projection(m,request.user,now) for m in active_page],
        closed_rows=[projection(m,request.user,now) for m in history_page],
        closure_reasons=CLOSE_REASONS)


@never_cache
@require_http_methods(["GET","POST"])
def issue(request):
    if not request.user.is_authenticated:
        return redirect("teacher-login")
    if not eligible_account(request.user) or not can_teach(request.user):
        return HttpResponseForbidden("Verified teaching access required.")
    key=tuple(request.GET.get(k,"") for k in ("code","period","start"))
    if not all(key):
        return HttpResponseBadRequest("Select a current lesson from My day.")
    try:
        with transaction.atomic():
            if request.method=="POST":
                actor=User.objects.select_for_update().get(pk=request.user.pk)
                lock_sources()
                list(StaffProfile.objects.select_for_update().filter(user=actor))
            else:
                actor=request.user
            if not eligible_account(actor) or not can_teach(actor):
                return HttpResponseForbidden("Teaching access revoked.")
            now=timezone.localtime()
            day=now.date()
            pub=current()
            row=current_lesson(pub,actor,day,key,now)
            if not row:
                return HttpResponseForbidden("Only your current verified lesson can issue a pass.")
            students=roster_for(pub,row["code"],day,lock=request.method=="POST")
            if request.method=="POST":
                if request.POST.get("publication")!=str(pub.pk) or request.POST.get("confirm")!="yes":
                    return HttpResponseBadRequest("Review the current publication and confirm departure.")
                student=next((s for s in students if str(s.pk)==request.POST.get("student")),None)
                if not student:
                    return HttpResponseForbidden("Student is not in the verified roster.")
                dest=MovementDestination.objects.select_for_update().filter(pk=request.POST.get("destination") if request.POST.get("destination","").isascii() and request.POST.get("destination","").isdecimal() and len(request.POST.get("destination",""))<=18 else None,active=True).first()
                if not dest:
                    return HttpResponseBadRequest("Choose an active destination.")
                if StudentMovement.objects.filter(student=student,closed_at__isnull=True).exists():
                    raise ValueError("This student already has an open movement. Contact the authorised staff member.")
                m=StudentMovement.objects.create(publication=pub,student=student,issuer=actor,destination=dest,
                    destination_name=dest.name,requires_reception=dest.requires_reception,lesson_date=day,
                    class_code=key[0],period=key[1],start=key[2],end=row["end"],origin_room=row.get("room","")[:100],
                    departed_at=now,due_at=now+timedelta(minutes=dest.expected_minutes))
                record(m,actor,"issue")
                return redirect("movement-detail",pk=m.pk)
            destinations=MovementDestination.objects.filter(active=True).order_by("name")
            return page(request,"movement_issue.html",row=row,students=students,destinations=destinations,publication=pub)
    except (AttendanceUnavailable,ValueError,IntegrityError) as exc:
        return render(request,"live_conflict.html",{**shell(request.user),
            "error":str(exc) if isinstance(exc,ValueError) else "Concurrent movement already exists. Review again."},status=409)


@never_cache
@require_GET
def detail(request,pk):
    if not request.user.is_authenticated:
        return redirect("teacher-login")
    if not may_access(request.user):
        return HttpResponseForbidden("Movement access required.")
    m=get_object_or_404(visible(request.user),pk=pk)
    return page(request,"movement_detail.html",movement=projection(m,request.user,timezone.now()),
        events=m.events.select_related("actor").order_by("revision"),closure_reasons=CLOSE_REASONS)


@never_cache
@require_POST
def change(request,pk):
    if not request.user.is_authenticated:
        return redirect("teacher-login")
    try:
        with transaction.atomic():
            actor=User.objects.select_for_update().get(pk=request.user.pk)
            # Recheck grants after locking their rows, so revocation is serialised.
            list(StaffAccessGrant.objects.select_for_update().filter(user=actor).order_by("pk"))
            if not may_access(actor):
                return HttpResponseForbidden("Movement access revoked.")
            # Student identity changes and the event must not race.
            candidate=get_object_or_404(visible(actor),pk=pk)
            list(Student.objects.select_for_update().filter(pk=candidate.student_id))
            m=get_object_or_404(visible(actor).select_for_update(of=("self",)),pk=pk)
            transition(m,actor,request.POST.get("action"),request.POST.get("revision",""),request.POST.get("reason",""))
    except PermissionError:
        return HttpResponseForbidden("Movement transition not authorised.")
    except ValueError as exc:
        return render(request,"movement_conflict.html",{**shell(request.user),"error":str(exc)},status=409)
    return redirect("movement-detail",pk=pk)


class DestinationForm(forms.Form):
    name=forms.CharField(max_length=80)
    expected_minutes=forms.IntegerField(min_value=1,max_value=180,initial=10)
    requires_reception=forms.BooleanField(required=False,help_text="Staff at the destination must confirm arrival and release.")
    def clean_name(self):
        name=self.cleaned_data["name"]
        if MovementDestination.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError("Use a new destination name; archive obsolete destinations.")
        return name


@administrator
@require_http_methods(["GET","POST"])
def destinations(request):
    form=DestinationForm(request.POST if request.method=="POST" and request.POST.get("action")=="create" else None)
    if request.method=="POST":
        try:
            with transaction.atomic():
                if not lock_administrator(request.user):
                    return HttpResponseForbidden("Administrator access revoked.")
                action=request.POST.get("action")
                if action=="create" and form.is_valid():
                    if MovementDestination.objects.filter(name__iexact=form.cleaned_data["name"]).exists():
                        raise ValueError("Destination name already exists.")
                    d=MovementDestination.objects.create(**form.cleaned_data,created_by=request.user)
                    audit(request.user,"movement_destination_created",after={"destination":d.pk,"minutes":d.expected_minutes,"reception":d.requires_reception})
                    return redirect("movement-destinations")
                if action=="archive":
                    d=get_object_or_404(MovementDestination.objects.select_for_update(),pk=request.POST.get("destination"))
                    if d.active:
                        d.active=False
                        d.save(update_fields=["active"])
                        audit(request.user,"movement_destination_archived",after={"destination":d.pk})
                    return redirect("movement-destinations")
                if action!="create":
                    return HttpResponseBadRequest("Unknown action.")
        except (ValueError,IntegrityError):
            form.add_error(None,"Destination configuration changed; review again.")
    return render(request,"movement_destinations.html",{"form":form,"destinations":MovementDestination.objects.order_by("name")})
