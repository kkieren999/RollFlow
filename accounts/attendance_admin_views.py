"""Audited correction and exact relief allocation management."""
from datetime import datetime, time, date
from django import forms
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from django.http import HttpResponseBadRequest,HttpResponseForbidden
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .staff_views import administrator
from .security_service import lock_administrator,audit,eligible_account
from .attendance import MARKS,lesson_key,lesson_valid,publication_ready,own_lessons,roster_for
from .attendance_operations import frozen_students
from .connected_school import current,visible_slots,personal_codes
from .models import (AttendanceRoll,AttendanceRevision,ImportedTimetable,ConnectedSchoolPublication,
    OneSchoolArchiveBatch,ReliefAttendanceAssignment,StaffProfile,SecurityEvent)


def lock_sources():
    list(ImportedTimetable.objects.select_for_update().order_by("pk"))
    list(OneSchoolArchiveBatch.objects.select_for_update().order_by("pk"))
    list(ConnectedSchoolPublication.objects.select_for_update().order_by("pk"))


@administrator
@require_http_methods(["GET","POST"])
def correct(request,pk):
    roll=get_object_or_404(AttendanceRoll.objects.select_related("publication"),pk=pk)
    error=""
    students=[]
    try:
        with transaction.atomic():
            if request.method=="POST":
                if not lock_administrator(request.user):
                    return HttpResponseForbidden("Administrator access revoked.")
                lock_sources()
                roll=get_object_or_404(AttendanceRoll.objects.select_related("publication"),pk=pk)
            students=frozen_students(roll,lock=request.method=="POST")
            if request.method=="POST":
                locked=AttendanceRoll.objects.select_for_update().get(pk=pk)
                if locked.revision!=roll.revision or request.POST.get("revision")!=str(roll.revision):
                    raise ValueError("A newer revision exists. Reload and review.")
                reason=request.POST.get("reason","").strip()
                if not 8<=len(reason)<=500 or request.POST.get("confirm")!="yes":
                    raise ValueError("Enter a correction reason (8–500 characters) and confirm.")
                fields={"mark_"+str(s.pk):str(s.pk) for s in students}
                if {k for k in request.POST if k.startswith("mark_")}!=set(fields) or any(len(request.POST.getlist(k))!=1 for k in fields):
                    return HttpResponseBadRequest("Invalid roster.")
                marks={sid:request.POST[k] for k,sid in fields.items()}
                if any(v not in dict(MARKS) for v in marks.values()):
                    return HttpResponseBadRequest("Invalid mark.")
                if marks==roll.marks:
                    raise ValueError("No marks changed.")
                prior=roll.revision
                roll.revision+=1
                roll.marks=marks
                roll.save(update_fields=["revision","marks","updated_at"])
                AttendanceRevision.objects.create(roll=roll,revision=roll.revision,actor=request.user,action="correct",marks=marks,reason=reason)
                audit(request.user,"attendance_corrected",after={"roll":roll.pk,"prior_revision":prior,"revision":roll.revision})
                SecurityEvent.objects.create(actor=request.user,event="attendance_corrected",subject=str(roll.pk))
                messages.success(request,"Correction saved. The original revision is preserved; reconcile the new revision separately.")
                return redirect("attendance-correct",pk=pk)
    except ValueError as exc:
        error=str(exc)
    rows=[{"pk":s.pk,"name":s.preferred_name or s.first_name,"last":s.last_name,"mark":roll.marks.get(str(s.pk),"")} for s in students]
    return render(request,"attendance_correct.html",{"roll":roll,"students":rows,"choices":MARKS,
        "error":error,"history":roll.history.select_related("actor").order_by("-revision")})


class ReliefForm(forms.Form):
    lesson=forms.ChoiceField(choices=[])
    teacher=forms.ModelChoiceField(queryset=User.objects.none())
    def __init__(self,*args,pub=None,day=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.rows={}
        if pub and publication_ready(pub):
            for r in visible_slots(pub,day):
                if lesson_valid(r):
                    key="|".join(lesson_key(r))
                    if key in self.rows:
                        self.rows[key]=None
                    else:
                        self.rows[key]=r
        self.fields["lesson"].choices=[(k,f'{r["start"]} · {r["code"]} · {r["period"]}') for k,r in self.rows.items() if r]
        self.fields["teacher"].queryset=User.objects.filter(is_active=True,staff_profile__timetable_link_verified=True).order_by("username")


@administrator
@require_http_methods(["GET","POST"])
def relief(request):
    pub=current()
    day=timezone.localdate()
    form=ReliefForm(request.POST if request.method=="POST" and request.POST.get("action")=="assign" else None,pub=pub,day=day)
    error=""
    if request.method=="POST":
        try:
            with transaction.atomic():
                if not lock_administrator(request.user):
                    return HttpResponseForbidden("Administrator access revoked.")
                # Lock user before sources to match roll writes.
                if request.POST.get("action")=="assign" and form.is_valid():
                    teacher=User.objects.select_for_update().get(pk=form.cleaned_data["teacher"].pk)
                    lock_sources()
                    active=current()
                    if not pub or not active or active.pk!=pub.pk or request.POST.get("publication")!=str(pub.pk) or not publication_ready(active):
                        raise ValueError("Publication changed; review again.")
                    row=form.rows[form.cleaned_data["lesson"]]
                    key=lesson_key(row)
                    binding=active.snapshot.get("bindings",{}).get(row.get("staff"),{})
                    regular=User.objects.filter(pk=binding.get("user")).first()
                    if not regular or teacher.pk==regular.pk or not personal_codes(active,teacher):
                        raise ValueError("Choose a different, verified teaching account.")
                    if not any(lesson_key(r)==key for r in own_lessons(active,regular,day)):
                        raise ValueError("Original lesson is not an unambiguous verified allocation.")
                    roster_for(active,row["code"],day,lock=True)
                    if AttendanceRoll.objects.filter(lesson_date=day,class_code=row["code"],start__lt=row["end"],end__gt=row["start"]).exists():
                        raise ValueError("A roll already exists. No automatic ownership transfer is allowed.")
                    if ReliefAttendanceAssignment.objects.filter(publication=active,lesson_date=day,class_code=key[0],period=key[1],start=key[2],cancelled_at__isnull=True).exists():
                        raise ValueError("An assignment already exists; review or cancel it first.")
                    if any(r["start"]<row["end"] and row["start"]<r["end"] for r in own_lessons(active,teacher,day)):
                        raise ValueError("The relief teacher already has an overlapping lesson.")
                    if ReliefAttendanceAssignment.objects.filter(publication=active,lesson_date=day,relief_teacher=teacher,
                         cancelled_at__isnull=True,start__lt=row["end"],end__gt=row["start"]).exists():
                        raise ValueError("An overlapping relief assignment exists.")
                    expiry=timezone.make_aware(datetime.combine(day,time(23,59,59)))
                    a=ReliefAttendanceAssignment.objects.create(publication=active,lesson_date=day,class_code=key[0],period=key[1],start=key[2],end=row["end"],
                        regular_teacher=regular,relief_teacher=teacher,created_by=request.user,expires_at=expiry)
                    audit(request.user,"relief_lesson_assigned",teacher,after={"assignment":a.pk,"publication":active.pk,"regular_teacher":regular.pk})
                    return redirect("attendance-relief")
                if request.POST.get("action")=="cancel":
                    lock_sources()
                    a=get_object_or_404(ReliefAttendanceAssignment.objects.select_for_update(),pk=request.POST.get("assignment"))
                    if a.cancelled_at or a.lesson_date!=day or not pub or a.publication_id!=pub.pk:
                        raise ValueError("Assignment is not current.")
                    if AttendanceRoll.objects.filter(lesson_date=a.lesson_date,class_code=a.class_code,start__lt=a.end,end__gt=a.start).exists():
                        raise ValueError("A roll exists; assignment cannot be cancelled automatically.")
                    a.cancelled_at=timezone.now()
                    a.save(update_fields=["cancelled_at"])
                    audit(request.user,"relief_lesson_cancelled",a.relief_teacher,after={"assignment":a.pk})
                    return redirect("attendance-relief")
                if request.POST.get("action")!="assign":
                    return HttpResponseBadRequest("Unknown action.")
        except (ValueError,IntegrityError) as exc:
            error=str(exc) if isinstance(exc,ValueError) else "Concurrent assignment changed; review again."
    assignments=ReliefAttendanceAssignment.objects.filter(lesson_date=day).select_related("regular_teacher","relief_teacher").order_by("start","pk")
    return render(request,"attendance_relief.html",{"form":form,"publication":pub,"day":day,"assignments":assignments,"error":error})
