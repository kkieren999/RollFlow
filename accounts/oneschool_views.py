from collections import Counter
from datetime import date, timedelta
MIN_DAY=date(1900,1,1)
MAX_DAY=date(2099,12,31)

def shift_date(day,days):
    return min(MAX_DAY,max(MIN_DAY,day+timedelta(days=days)))

def coverage_message(version,today):
    value=today.isoformat()
    if value>version.summary["last_date"]:
        return "Published timetable has expired. Import a timetable covering today."
    if value<version.summary["first_date"]:
        return "Published timetable starts in the future."
    return ""
from django import forms
from django.conf import settings
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
from .teacher_schedule import staff_identity, assigned_rows

class ImportForm(forms.Form):
    name=forms.CharField(label="Timetable version name",max_length=100)
    csv=forms.FileField(label="OneSchool timetable CSV")
    fictional=forms.BooleanField(label="I confirm this file contains only fictional or approved de-identified development data.")

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if settings.ROLLFLOW_LIVE_TIMETABLE:
            self.fields["fictional"].label="I am authorised to import and publish this OneSchool export in the school-hosted installation."

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
            publish_now=settings.ROLLFLOW_LIVE_TIMETABLE or request.POST.get("publish_now")=="yes"
            if publish_now and not settings.ROLLFLOW_LIVE_TIMETABLE:
                raise ValueError("Direct publication is available only in approved live timetable mode.")
            if publish_now and request.POST.get("replace_ack")!="yes":
                raise ValueError("Confirm that this import replaces the entire published timetable.")
            with transaction.atomic():
                if publish_now:
                    list(ImportedTimetable.objects.select_for_update().order_by("pk"))
                version,created=ImportedTimetable.objects.get_or_create(digest=digest,defaults={"name":form.cleaned_data["name"],"summary":summary,"created_by":request.user})
                if created:
                    ImportedTimetableDay.objects.bulk_create([ImportedTimetableDay(version=version,date=day,allocations=rows) for day,rows in days.items()],batch_size=100)
                    SecurityEvent.objects.create(actor=request.user,event="timetable_import_draft",subject=str(version.pk))
                if publish_now and version.status!="published":
                    ImportedTimetable.objects.filter(status="published").update(status="archived")
                    version.status="published"
                    version.published_at=timezone.now()
                    version.save(update_fields=["status","published_at"])
                    SecurityEvent.objects.create(actor=request.user,event="timetable_import_publish",subject=str(version.pk))
            messages.success(request,"Timetable imported and published." if publish_now else ("Draft created." if created else "Identical import already exists. No duplicate version created."))
            return redirect("oneschool-review",pk=version.pk)
        except ValueError as exc:
            form.add_error("csv",str(exc))
        except IntegrityError:
            form.add_error("csv","A concurrent import conflicted. Please retry.")
    return page(request,"oneschool",import_form=form,live_timetable=settings.ROLLFLOW_LIVE_TIMETABLE,versions=ImportedTimetable.objects.all()[:50])

@administrator
@require_http_methods(["GET"])
def review(request,pk):
    version=get_object_or_404(ImportedTimetable,pk=pk)
    first=version.days.first()
    return page(request,"oneschool",live_timetable=settings.ROLLFLOW_LIVE_TIMETABLE,review_version=version,example_rows=(first.allocations[:15] if first else []),published=ImportedTimetable.objects.filter(status="published").first())

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
    if settings.ROLLFLOW_LIVE_TIMETABLE:
        return HttpResponseForbidden("Sample exports are not available in the operational installation.")
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
    today=timezone.localdate()
    fallback=today.isoformat()
    if not version.days.filter(date=today).exists():
        next_day=version.days.filter(date__gte=today).first() or version.days.last()
        if next_day:
            fallback=next_day.date.isoformat()
    requested=request.GET.get("date",fallback)
    try:
        day=date.fromisoformat(requested)
        if not MIN_DAY<=day<=MAX_DAY:
            raise ValueError("Date outside supported range")
    except ValueError:
        day=timezone.localdate()
    record=version.days.filter(date=day).first()
    all_rows=record.allocations if record else []
    staff_id, link_message = staff_identity(request.user) if personal else (None, "")
    rows=assigned_rows(all_rows, staff_id) if personal else all_rows
    query=request.GET.get("q","").strip()[:150]
    year=request.GET.get("year","")
    years=sorted({r["year"] for r in rows})
    if year not in [str(y) for y in years]:
        year=""
    staff=request.GET.get("staff","").strip().upper()[:250] if not personal else ""
    staff_key=request.GET.get("staff_id","").strip().upper()[:250] if not personal else ""
    room=request.GET.get("room","").strip()[:250]
    highlight=request.GET.get("highlight")=="1" and not personal
    hide=request.GET.get("breaks")=="hide"
    import re
    from urllib.parse import urlencode
    periods=sorted({(r["start"],r["end"],r["period"]) for r in rows if not hide or not re.search(r"\b(break|recess|lunch|interval)\b",r["period"],re.I)})
    visible=set(periods)
    def matches(r):
        return ((not year or str(r["year"])==year) and (not staff or r["staff_code"].upper()==staff) and (not staff_key or r["staff_id"].upper()==staff_key) and (not room or r["room"]==room) and query.casefold() in " ".join(str(r[k]) for k in ("code","subject","staff_code","room","period")).casefold())
    filtered=[r for r in rows if (r["start"],r["end"],r["period"]) in visible and matches(r)]
    shown=[dict(r,match=matches(r)) for r in rows if (r["start"],r["end"],r["period"]) in visible and (highlight or matches(r))]
    current_time=timezone.localtime().strftime("%H:%M")
    is_today=day==today
    def params(**kwargs):
        base={"date":day.isoformat(),"q":query,"year":year,"staff":staff,"staff_id":staff_key,"room":room,"breaks":"hide" if hide else "","highlight":"1" if highlight else ""}
        base.update(kwargs)
        return "?"+urlencode({k:v for k,v in base.items() if v})
    for r in shown:
        r["staff_url"]=params(staff="" if r["staff_id"] else r["staff_code"],staff_id=r["staff_id"],room="",q="",year="",highlight="")
        r["room_url"]=params(room=r["room"],staff="",staff_id="",q="",year="",highlight="")
        r["current"]=is_today and r["start"]<=current_time<r["end"]
    groups=[]
    period_headers=[dict(start=p[0],end=p[1],label=p[2],current=is_today and p[0]<=current_time<p[1]) for p in periods]
    for y in years:
        if not highlight and year and year!=str(y):
            continue
        cells=[]
        for p,h in zip(periods,period_headers):
            cells.append(dict(current=h["current"],entries=[r for r in shown if r["year"]==y and (r["start"],r["end"],r["period"])==p]))
        groups.append({"year":y,"cells":cells})
    monday=shift_date(day,-day.weekday())
    tabs=[{"date":shift_date(monday,i).isoformat(),"label":["Monday","Tuesday","Wednesday","Thursday","Friday"][i],"url":params(date=shift_date(monday,i).isoformat())} for i in range(5)]
    current_periods=[p for p in period_headers if p["current"]]
    next_period=next((p for p in period_headers if is_today and p["start"]>current_time),None)
    context=dict(live_timetable=settings.ROLLFLOW_LIVE_TIMETABLE,version=version,selected_date=day.isoformat(),day=day,tabs=tabs,periods=period_headers,groups=groups,rows=shown if personal else filtered,query=query,year=year,years=years,hide=hide,personal=personal,unlinked=personal and not staff_id,link_message=link_message,record_exists=record is not None,admin=role=="admin",staff=staff,room=room,highlight=highlight,has_filter=bool(query or year or staff or staff_key or room),staff_key=staff_key,visible_count=sum(1 for r in rows if (r["start"],r["end"],r["period"]) in visible),coverage_warning=coverage_message(version,today),staff_choices=sorted({r["staff_code"] for r in rows if r["staff_code"]}|({staff} if staff else set())),room_choices=sorted({r["room"] for r in rows if r["room"]}|({room} if room else set())),today_url=params(date=today.isoformat()),prev_url=params(date=shift_date(day,-7).isoformat()),next_url=params(date=shift_date(day,7).isoformat()),first_url=params(date=version.summary["first_date"]),clear_url=params(q="",year="",staff="",staff_id="",room=""),break_url=params(breaks="" if hide else "hide"),highlight_url=params(highlight="" if highlight else "1"),is_today=is_today,current_periods=current_periods,next_period=next_period)
    if role=="admin":
        return page(request,"master",dated_import=True,**context)
    return render(request,"imported_teacher.html",context)
