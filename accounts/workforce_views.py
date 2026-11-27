"""Admin-approved workforce changes and private staff inbox."""
from datetime import date, timedelta
from django import forms
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render,redirect,get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET,require_http_methods,require_POST
from .attendance import lesson_valid,lesson_key,publication_ready
from .attendance_admin_views import lock_sources
from .connected_school import current,visible_slots,date_is_school_day
from .models import WorkforceEntry,WorkforceNotice,ReliefAttendanceAssignment,AttendanceRoll,StudentMovement,StaffProfile
from .security_service import lock_administrator,audit
from .workforce_service import authority,self_allowed,entries,closed,absent,raw_busy,effective_room,lesson_has_records,notify,lesson_people,coverage
from .live_views import page


def selected_date(request):
    value=request.GET.get("date") or timezone.localdate().isoformat()
    day=date.fromisoformat(value)
    today=timezone.localdate()
    if not today-timedelta(days=365)<=day<=today+timedelta(days=180):
        raise ValueError("Choose a date within the planning range.")
    return day


def planning_day(pub,day):
    return pub and pub.active and pub.snapshot.get("source")=="dated" and publication_ready(pub) and date_is_school_day(pub,day) and day>=timezone.localdate()


class EntryForm(forms.Form):
    kind=forms.ChoiceField(choices=WorkforceEntry.Kind.choices)
    staff=forms.ModelChoiceField(queryset=User.objects.none(),required=False)
    lesson=forms.ChoiceField(choices=[],required=False)
    start=forms.TimeField(required=False,widget=forms.TimeInput(attrs={"type":"time"}))
    end=forms.TimeField(required=False,widget=forms.TimeInput(attrs={"type":"time"}))
    location=forms.CharField(max_length=100,required=False,help_text="Duty location or exact published room name; no medical or personal details.")
    confirm=forms.BooleanField()
    def __init__(self,*args,pub=None,day=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.rows={}
        if pub and day:
            for r in visible_slots(pub,day):
                if lesson_valid(r):
                    k="|".join(lesson_key(r))
                    self.rows[k]=None if k in self.rows else r
        self.fields["lesson"].choices=[("","Select lesson for room change")]+[(k,f'{r["start"]} · {r["code"]} · {r["period"]}') for k,r in self.rows.items() if r]
        self.fields["staff"].queryset=User.objects.filter(is_active=True).order_by("username")


def link(day):
    return reverse("workforce-board")+"?date="+day.isoformat()


def can_write(user):
    return bool(user.is_staff and user.is_superuser)


def check_no_day_records(day):
    if AttendanceRoll.objects.filter(lesson_date=day).exists() or StudentMovement.objects.filter(lesson_date=day).exists():
        raise ValueError("Recorded attendance or movements exist; an automatic day closure is not allowed.")


def create_entry(actor,pub,day,c,rows):
    kind=c["kind"]
    staff=c.get("staff")
    data={"publication":pub,"day":day,"kind":kind,"created_by":actor}
    people=[]
    if kind=="closure":
        if staff or c.get("lesson") or c.get("start") or c.get("end") or c.get("location"):
            raise ValueError("A day closure does not accept staff, lesson, time or location.")
        check_no_day_records(day)
        if entries(pub,day).exists() or ReliefAttendanceAssignment.objects.filter(publication=pub,lesson_date=day,cancelled_at__isnull=True).exists():
            raise ValueError("Cancel existing operational allocations before closing the day.")
        people=[b.get("user") for b in pub.snapshot.get("bindings",{}).values() if isinstance(b,dict) and b.get("user")]
    else:
        if closed(pub,day):
            raise ValueError("The selected school day is closed.")
        if kind in ("absence","duty"):
            if not staff or not self_allowed(staff):
                raise ValueError("Select an eligible staff account with existing workspace access.")
            data["staff"]=staff
            people=[staff.pk]
        if kind=="absence":
            if c.get("lesson") or c.get("start") or c.get("end") or c.get("location"):
                raise ValueError("Full-day unavailability needs only the staff account.")
            if AttendanceRoll.objects.filter(lesson_date=day,teacher=staff).exists() or StudentMovement.objects.filter(lesson_date=day,issuer=staff).exists():
                raise ValueError("Staff already has attendance or movement records for this day.")
            if entries(pub,day,"duty").filter(staff=staff).exists() or ReliefAttendanceAssignment.objects.filter(publication=pub,lesson_date=day,relief_teacher=staff,cancelled_at__isnull=True).exists():
                raise ValueError("Resolve existing cover or duty assignments before recording unavailability.")
        if kind=="duty":
            start,end=c.get("start"),c.get("end")
            if not start or not end or start>=end or not c.get("location") or c.get("lesson"):
                raise ValueError("Choose a duty location and valid start/end times, without a lesson.")
            start,end=start.strftime("%H:%M"),end.strftime("%H:%M")
            if start>=end or absent(pub,day,staff) or raw_busy(pub,day,staff,start,end):
                raise ValueError("Staff is unavailable or already has an overlapping allocation.")
            data.update(start=start,end=end,location=c["location"])
        if kind=="room":
            row=rows.get(c.get("lesson"))
            if staff or c.get("start") or c.get("end") or not row or not c.get("location"):
                raise ValueError("Select only a lesson and replacement room.")
            room=c["location"]
            if room not in {r.get("room") for r in pub.snapshot.get("slots",[]) if r.get("room")}:
                raise ValueError("Select an exact room from the reviewed timetable.")
            if room==effective_room(pub,day,row) or lesson_has_records(day,row):
                raise ValueError("Room unchanged or existing roll/movement requires manual review.")
            if any(lesson_key(r)!=lesson_key(row) and r.get("start","")<row["end"] and row["start"]<r.get("end","")
                   and effective_room(pub,day,r)==room for r in visible_slots(pub,day)):
                raise ValueError("Replacement room already has an overlapping allocation.")
            code,period,start=lesson_key(row)
            data.update(class_code=code,period=period,start=start,end=row["end"],location=room)
            people=lesson_people(pub,day,row)
    entry=WorkforceEntry.objects.create(**data)
    audit(actor,"workforce_created",staff,after={"entry":entry.pk,"kind":kind,"publication":pub.pk,"day":day.isoformat()})
    notify(pub,day,people,f"Approved {entry.get_kind_display()} for {day.isoformat()}. Review your workforce schedule.")
    return entry


def cancel_entry(actor,pub,day,pk):
    entry=get_object_or_404(entries(pub,day).select_for_update(),pk=pk)
    people=[entry.staff_id] if entry.staff_id else []
    if entry.kind=="absence" and ReliefAttendanceAssignment.objects.filter(publication=pub,lesson_date=day,
        regular_teacher_id=entry.staff_id,cancelled_at__isnull=True).exists():
        raise ValueError("Resolve existing relief cover before cancelling the absence.")
    if entry.kind=="room":
        row={"code":entry.class_code,"period":entry.period,"start":entry.start,"end":entry.end}
        if lesson_has_records(day,row):
            raise ValueError("Existing roll or movement prevents automatic room restoration.")
        original=next((r for r in visible_slots(pub,day) if lesson_key(r)==lesson_key(row)),None)
        if not original:
            raise ValueError("Original allocation changed; review required.")
        original_room=original.get("room","")
        if original_room and any(lesson_key(r)!=lesson_key(row) and r.get("start","")<entry.end and entry.start<r.get("end","") and effective_room(pub,day,r)==original_room for r in visible_slots(pub,day)):
            raise ValueError("Original room now conflicts with another allocation.")
        people=lesson_people(pub,day,original)
    if entry.kind=="closure":
        check_no_day_records(day)
        people=[b.get("user") for b in pub.snapshot.get("bindings",{}).values() if isinstance(b,dict) and b.get("user")]
    entry.cancelled_at=timezone.now()
    entry.save(update_fields=["cancelled_at"])
    audit(actor,"workforce_cancelled",entry.staff,after={"entry":entry.pk,"kind":entry.kind})
    notify(pub,day,people,f"Cancelled {entry.get_kind_display()} for {day.isoformat()}. Review your workforce schedule.")


@never_cache
@require_http_methods(["GET","POST"])
def board(request):
    if not request.user.is_authenticated:
        return redirect("teacher-login")
    if not authority(request.user):
        return HttpResponseForbidden("Workforce monitoring access required.")
    try:
        day=selected_date(request)
    except ValueError:
        return HttpResponseBadRequest("Invalid planning date.")
    pub=current()
    form=EntryForm(request.POST if request.method=="POST" and request.POST.get("action")=="create" else None,pub=pub,day=day)
    error=""
    if request.method=="POST":
        if not can_write(request.user):
            return HttpResponseForbidden("Administrator approval required.")
        try:
            with transaction.atomic():
                if not lock_administrator(request.user):
                    return HttpResponseForbidden("Administrator access revoked.")
                action=request.POST.get("action")
                valid=action=="create" and form.is_valid()
                if valid and form.cleaned_data.get("staff"):
                    # User before sources matches attendance and movement writers.
                    staff=User.objects.select_for_update().get(pk=form.cleaned_data["staff"].pk)
                    form.cleaned_data["staff"]=staff
                lock_sources()
                active=current()
                if not pub or not active or active.pk!=pub.pk or request.POST.get("publication")!=str(pub.pk) or not planning_day(active,day):
                    raise ValueError("Current reviewed publication or planning day changed.")
                if valid:
                    if form.cleaned_data["kind"]=="room" and form.cleaned_data.get("lesson") not in form.rows:
                        raise ValueError("Review the current lesson.")
                    create_entry(request.user,active,day,form.cleaned_data,form.rows)
                    return redirect(link(day))
                if action=="cancel":
                    if request.POST.get("confirm")!="yes":
                        return HttpResponseBadRequest("Confirm cancellation.")
                    cancel_entry(request.user,active,day,request.POST.get("entry"))
                    return redirect(link(day))
                if action!="create":
                    return HttpResponseBadRequest("Unknown workforce action.")
        except (ValueError,IntegrityError) as exc:
            error=str(exc) if isinstance(exc,ValueError) else "Conflicting workforce change. Reload and review."
    qs=WorkforceEntry.objects.filter(day=day).select_related("staff","publication","created_by").order_by("kind","start","pk")
    rows=coverage(pub,day)
    cover=ReliefAttendanceAssignment.objects.filter(lesson_date=day).select_related("regular_teacher","relief_teacher","publication").order_by("start","pk")
    return page(request,"workforce_board.html",pub=pub,day=day,form=form,error=error,
        writable=can_write(request.user) and planning_day(pub,day),entries=Paginator(qs,50).get_page(request.GET.get("page")),
        coverage=rows,uncovered=sum(not r["covered"] for r in rows),cover=cover,day_closed=closed(pub,day))


@never_cache
@require_GET
def mine(request):
    if not request.user.is_authenticated:
        return redirect("teacher-login")
    if not self_allowed(request.user):
        return HttpResponseForbidden("Staff workspace access required.")
    try:
        day=selected_date(request)
    except ValueError:
        return HttpResponseBadRequest("Invalid planning date.")
    pub=current()
    qs=entries(pub,day).filter(staff=request.user) if pub else WorkforceEntry.objects.none()
    cover=ReliefAttendanceAssignment.objects.filter(publication=pub,lesson_date=day,relief_teacher=request.user,
        cancelled_at__isnull=True,expires_at__gt=timezone.now()) if pub else ReliefAttendanceAssignment.objects.none()
    notices=WorkforceNotice.objects.filter(recipient=request.user).select_related("publication").order_by("-created_at","-pk")
    return page(request,"workforce_mine.html",pub=pub,day=day,entries=qs,cover=cover,
        day_closed=closed(pub,day),notices=Paginator(notices,30).get_page(request.GET.get("page")))


@never_cache
@require_POST
def acknowledge(request,pk):
    if not request.user.is_authenticated:
        return redirect("teacher-login")
    with transaction.atomic():
        user=User.objects.select_for_update().get(pk=request.user.pk)
        if not self_allowed(user):
            return HttpResponseForbidden("Staff workspace access required.")
        n=get_object_or_404(WorkforceNotice.objects.select_for_update(),pk=pk,recipient=user)
        if not n.acknowledged_at:
            n.acknowledged_at=timezone.now()
            n.save(update_fields=["acknowledged_at"])
            audit(user,"workforce_notice_acknowledged",after={"notice":n.pk})
    return redirect("workforce-mine")
