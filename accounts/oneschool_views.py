from collections import Counter
from datetime import date, timedelta
from django import forms
from django.contrib import messages
from django.db import transaction, IntegrityError
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST
from .models import ImportedTimetable, ImportedTimetableDay, SecurityEvent
from .staff_views import administrator, page
from .views import role_for
from .oneschool_csv import parse, HEADER, MAX_BYTES

class ImportForm(forms.Form):
    name=forms.CharField(label="Draft name",max_length=100)
    csv=forms.FileField(label="OneSchool timetable CSV")
    fictional=forms.BooleanField(label="I confirm this file contains only fictional or approved de-identified development data.")

@administrator
@require_http_methods(["GET","POST"])
def centre(request):
    form=ImportForm(request.POST if request.method=="POST" else None,request.FILES if request.method=="POST" else None)
    if request.method=="POST" and form.is_valid():
        upload=form.cleaned_data["csv"]
        try:
            if upload.size>MAX_BYTES:
                raise ValueError("Choose a CSV up to 20 MB.")
            days,summary,digest=parse(upload.read(MAX_BYTES+1))
            with transaction.atomic():
                version,created=ImportedTimetable.objects.get_or_create(digest=digest,defaults={"name":form.cleaned_data["name"],"summary":summary,"created_by":request.user})
                if created:
                    ImportedTimetableDay.objects.bulk_create([ImportedTimetableDay(version=version,date=day,allocations=rows) for day,rows in days.items()],batch_size=100)
                    SecurityEvent.objects.create(actor=request.user,event="timetable_import_draft",subject=str(version.pk))
            messages.success(request,"Draft created." if created else "Identical import already exists. No duplicate version created.")
            return redirect("oneschool-review",pk=version.pk)
        except ValueError as exc:
            form.add_error("csv",str(exc))
        except IntegrityError:
            form.add_error("csv","A concurrent import conflicted. Please retry.")
    return page(request,"oneschool",import_form=form,versions=ImportedTimetable.objects.all()[:50])

@administrator
@require_http_methods(["GET"])
def review(request,pk):
    version=get_object_or_404(ImportedTimetable,pk=pk)
    first=version.days.first()
    return page(request,"oneschool",review_version=version,example_rows=(first.allocations[:15] if first else []),published=ImportedTimetable.objects.filter(status="published").first())

@administrator
@require_POST
def publish(request,pk):
    if request.POST.get("ack")!="yes":
        messages.error(request,"Review the date range and acknowledge warnings before publishing.")
        return redirect("oneschool-review",pk=pk)
    try:
        with transaction.atomic():
            # Serialize publication against existing versions. The conditional unique constraint is the final guard.
            versions=list(ImportedTimetable.objects.select_for_update().order_by("pk"))
            version=next((v for v in versions if v.pk==pk),None)
            if version is None:
                return HttpResponseBadRequest("Unknown version.")
            if version.status=="published":
                return redirect("oneschool-review",pk=pk)
            ImportedTimetable.objects.filter(status="published").update(status="archived")
            version.status="published";version.published_at=timezone.now()
            version.save(update_fields=["status","published_at"])
            SecurityEvent.objects.create(actor=request.user,event="timetable_import_publish",subject=str(version.pk))
    except IntegrityError:
        messages.error(request,"Another publication occurred. Review the current version and retry.")
    else:
        messages.success(request,"Timetable published. Earlier versions are retained.")
    return redirect("oneschool-review",pk=pk)

@administrator
@require_http_methods(["GET"])
def sample(request):
    text=",".join(HEADER)+"\nDEMO071A,Mathematics,07,Mon,23/11/2026,PERIOD 1,08:50,10:00,DEMO01,,DEMOA,Example,Teacher,M01,Sample room\nDEMO071A,Mathematics,07,Tue,24/11/2026,PERIOD 1,09:00,10:10,DEMO02,,DEMOB,Example,Teacher,M02,Sample room\n"
    response=HttpResponse(text,content_type="text/csv; charset=utf-8")
    response["Content-Disposition"]='attachment; filename="fictional-oneschool-timetable.csv"'
    return response

def current_version():
    return ImportedTimetable.objects.filter(status="published").first()

@never_cache
@require_http_methods(["GET"])
def dated(request, personal=False,admin_only=False):
    role=role_for(request.user)
    if role is None:
        return redirect("teacher-login")
    if role not in ("teacher","admin") or (personal and role!="teacher") or (admin_only and role!="admin"):
        return HttpResponseForbidden("Staff access required.")
    version=current_version()
    if not version:
        return redirect("teacher-timetable" if personal else ("management-master" if role=="admin" else "teacher-master"))
    requested=request.GET.get("date",timezone.localdate().isoformat())
    try:
        day=date.fromisoformat(requested)
    except ValueError:
        day=timezone.localdate()
    record=version.days.filter(date=day).first()
    all_rows=record.allocations if record else []
    profile=getattr(request.user,"staff_profile",None)
    staff_id=profile.staff_id if personal and profile else None
    rows=[r for r in all_rows if not personal or bool(staff_id) and r["staff_id"]==staff_id]
    query=request.GET.get("q","").strip()[:150]
    year=request.GET.get("year","")
    if year not in [str(y) for y in range(7,13)]:
        year=""
    filtered=[r for r in rows if (not year or str(r["year"])==year) and query.casefold() in " ".join(str(r[k]) for k in ("code","subject","staff_code","room","period")).casefold()]
    periods=sorted({(r["start"],r["end"],r["period"]) for r in all_rows})
    groups=[]
    for y in range(7,13):
        if year and year!=str(y):
            continue
        cells=[]
        for p in periods:
            cells.append([r for r in filtered if r["year"]==y and (r["start"],r["end"],r["period"])==p])
        groups.append({"year":y,"cells":cells})
    monday=day-timedelta(days=day.weekday())
    tabs=[{"date":(monday+timedelta(days=i)).isoformat(),"label":["Monday","Tuesday","Wednesday","Thursday","Friday"][i]} for i in range(5)]
    context=dict(version=version,selected_date=day.isoformat(),day=day,tabs=tabs,periods=periods,groups=groups,rows=filtered,query=query,year=year,years=range(7,13),personal=personal,unlinked=personal and not staff_id,record_exists=record is not None,admin=role=="admin")
    if role=="admin":
        return page(request,"master",dated_import=True,**context)
    return render(request,"imported_teacher.html",context)
