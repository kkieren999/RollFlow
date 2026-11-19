import csv
import io
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q, Count
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from .models import SchoolClass, ClassEnrolment, Room, SchoolPeriod, TimetableSlot, SecurityEvent
from .staff_views import administrator, page
from .timetable_forms import ClassForm, EnrolmentForm, EndEnrolmentForm, RoomForm, PeriodForm, SlotForm, TimetableImportForm, teachers

def event(request, action, subject):
    SecurityEvent.objects.create(actor=request.user,event=action,subject=str(subject)[:150])

def active_slots():
    return TimetableSlot.objects.filter(active=True,school_class__active=True,room__active=True,teacher__is_active=True,teacher__is_staff=False,teacher__is_superuser=False,teacher__groups__name="Teacher").select_related("school_class","teacher","room","period").distinct()

@administrator
@require_http_methods(["GET"])
def classes(request):
    q = request.GET.get("q","").strip()[:150]
    year = request.GET.get("year","")
    records = SchoolClass.objects.select_related("teacher").annotate(roster_count=Count("enrolments",filter=Q(enrolments__end_date__isnull=True))).order_by("code")
    if q:
        records = records.filter(Q(code__icontains=q)|Q(name__icontains=q)|Q(subject__icontains=q)|Q(teacher__username__icontains=q))
    if year in [str(x) for x in range(7,13)]:
        records = records.filter(year_level=int(year))
    return page(request,"classes",class_page=Paginator(records,50).get_page(request.GET.get("page")),q=q,year=year,years=range(7,13))

@administrator
@require_http_methods(["GET","POST"])
def class_edit(request,pk=None):
    record = get_object_or_404(SchoolClass,pk=pk) if pk is not None else None
    form = ClassForm(request.POST if request.method=="POST" else None,instance=record)
    if request.method=="POST" and form.is_valid():
        try:
            with transaction.atomic():
                saved = form.save()
                event(request,"class_updated" if pk else "class_created",saved.code)
            messages.success(request,"Class saved. Existing timetable slots retain their assigned teacher.")
            return redirect("management-class-detail",pk=saved.pk)
        except IntegrityError:
            form.add_error(None,"Duplicate class code.")
    return page(request,"classes",editor_form=form,editor_title="Edit class" if pk else "Add class",cancel_url="management-class-directory")

def class_context(request,record,form=None):
    return page(request,"classes",class_record=record,enrolments=record.enrolments.select_related("student").order_by("-start_date","student__last_name"),slots=record.slots.select_related("teacher","room","period"),enrolment_form=form or EnrolmentForm(school_class=record,initial={"start_date":timezone.localdate()}),today=timezone.localdate())

@administrator
@require_http_methods(["GET"])
def class_detail(request,pk):
    return class_context(request,get_object_or_404(SchoolClass,pk=pk))

@administrator
@require_POST
def enrol(request,pk):
    with transaction.atomic():
        record = get_object_or_404(SchoolClass.objects.select_for_update(),pk=pk)
        form = EnrolmentForm(request.POST,school_class=record)
        if form.is_valid():
            try:
                with transaction.atomic():
                    enrolment = form.save(commit=False)
                    enrolment.school_class = record
                    enrolment.save()
                    event(request,"class_enrolment_added",record.code+" / "+enrolment.student.student_id)
                messages.success(request,"Student enrolled.")
                return redirect("management-class-detail",pk=pk)
            except IntegrityError:
                form.add_error(None,"An open enrolment already exists.")
    return class_context(request,record,form)

@administrator
@require_POST
def end_enrolment(request,pk):
    form=EndEnrolmentForm(request.POST)
    with transaction.atomic():
        enrolment=get_object_or_404(ClassEnrolment.objects.select_for_update(),pk=pk)
        if enrolment.end_date is not None or not form.is_valid() or form.cleaned_data["end_date"]<enrolment.start_date:
            return HttpResponseBadRequest("Enter a valid last enrolled date for an open enrolment.")
        enrolment.end_date=form.cleaned_data["end_date"]
        enrolment.save(update_fields=["end_date"])
        event(request,"class_enrolment_ended",enrolment.school_class.code+" / "+enrolment.student.student_id)
    messages.success(request,"Enrolment ended; history retained.")
    return redirect("management-class-detail",pk=enrolment.school_class_id)

@administrator
@require_http_methods(["GET"])
def timetable(request):
    teacher=request.GET.get("teacher","")
    weekday=request.GET.get("day","")
    slots=TimetableSlot.objects.select_related("school_class","teacher","room","period")
    if teacher.isdigit():
        slots=slots.filter(teacher_id=int(teacher))
    if weekday in ["1","2","3","4","5"]:
        slots=slots.filter(weekday=int(weekday))
    return page(request,"timetable",slots=slots,rooms=Room.objects.order_by("code"),periods=SchoolPeriod.objects.all(),teacher_options=teachers(),teacher_filter=teacher,day_filter=weekday,days=TimetableSlot._meta.get_field("weekday").choices,import_form=TimetableImportForm())

def save_editor(request,form_class,model,pk,title,section="timetable",initial=None):
    record=get_object_or_404(model,pk=pk) if pk else None
    form=form_class(request.POST if request.method=="POST" else None,instance=record,initial=initial)
    if request.method=="POST" and form.is_valid():
        try:
            with transaction.atomic():
                saved=form.save()
                event(request,model.__name__.lower()+("_updated" if pk else "_created"),getattr(saved,"code",str(saved.pk)))
            messages.success(request,title+" saved.")
            return redirect("management-timetable")
        except IntegrityError:
            form.add_error(None,"Conflicting or duplicate record. Reload and try again.")
    return page(request,section,editor_form=form,editor_title=title,cancel_url="management-timetable")

@administrator
@require_http_methods(["GET","POST"])
def room_edit(request,pk=None):
    return save_editor(request,RoomForm,Room,pk,"Room")

@administrator
@require_http_methods(["GET","POST"])
def period_edit(request,pk=None):
    return save_editor(request,PeriodForm,SchoolPeriod,pk,"Period")

@administrator
@require_http_methods(["GET","POST"])
def slot_edit(request,pk=None):
    initial={}
    if request.GET.get("class","").isdigit():
        record=get_object_or_404(SchoolClass,pk=int(request.GET["class"]))
        initial={"school_class":record.pk,"teacher":record.teacher_id,"active":True}
    return save_editor(request,SlotForm,TimetableSlot,pk,"Timetable slot",initial=initial)

@administrator
@require_POST
def slot_cancel(request,pk):
    with transaction.atomic():
        slot=get_object_or_404(TimetableSlot.objects.select_for_update(),pk=pk)
        slot.active=False
        slot.save(update_fields=["active"])
        event(request,"timetable_slot_archived",str(slot.pk))
    messages.success(request,"Slot archived.")
    return redirect("management-timetable")

HEADER=["class_code","teacher_username","room_code","weekday","period_code"]

@administrator
@require_http_methods(["GET"])
def csv_template(request):
    response=HttpResponse(",".join(HEADER)+"\nDEMO101,sampleteacher,M01,1,1\n",content_type="text/csv; charset=utf-8")
    response["Content-Disposition"]='attachment; filename="rollflow-timetable-template.csv"'
    return response

@administrator
@require_POST
def import_timetable(request):
    form=TimetableImportForm(request.POST,request.FILES)
    if form.is_valid():
        try:
            upload=form.cleaned_data["csv"]
            if upload.size>250000:
                raise ValidationError("File must be below 250 KB.")
            reader=csv.DictReader(io.StringIO(upload.read().decode("utf-8-sig")),strict=True)
            if reader.fieldnames!=HEADER:
                raise ValidationError("Use the exact five-column header.")
            with transaction.atomic():
                count=0
                for number,row in enumerate(reader,2):
                    if number>501 or None in row or any(v is None for v in row.values()):
                        raise ValidationError(f"Invalid or excess row {number}.")
                    r={k:v.strip() for k,v in row.items()}
                    try:
                        klass=SchoolClass.objects.get(code__iexact=r["class_code"],active=True)
                        teacher=teachers().get(username__iexact=r["teacher_username"])
                        room=Room.objects.get(code__iexact=r["room_code"],active=True)
                        period=SchoolPeriod.objects.get(code__iexact=r["period_code"])
                    except (SchoolClass.DoesNotExist,Room.DoesNotExist,SchoolPeriod.DoesNotExist,User.DoesNotExist) as exc:
                        raise ValidationError(f"Unknown or inactive reference on row {number}.") from exc
                    slot_form=SlotForm({"school_class":klass.pk,"teacher":teacher.pk,"room":room.pk,"weekday":r["weekday"],"period":period.pk,"active":"on"})
                    if not slot_form.is_valid():
                        raise ValidationError(f"Invalid or conflicting timetable row {number}: "+", ".join(slot_form.errors.keys()))
                    slot=slot_form.save()
                    event(request,"timetable_slot_imported",str(slot.pk))
                    count+=1
                if not count:
                    raise ValidationError("No timetable entries.")
            messages.success(request,f"Imported {count} slots.")
            return redirect("management-timetable")
        except (ValidationError,UnicodeError,csv.Error,IntegrityError) as error:
            form.add_error("csv","Import rejected because of conflicting or invalid records." if isinstance(error, IntegrityError) else str(error))
    return page(request,"timetable",import_error_form=form)
