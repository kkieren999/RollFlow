"""Protected teacher screens. All new routes are read-only."""
from datetime import timedelta
from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden,HttpResponseBadRequest,Http404
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from .connected_school import current,canonical
from .live_views import page
from .teacher_experience import (allowed,bounded_day,shift,personal_schedule,directory_classes,student_projection)


def deny(request):
    if not request.user.is_authenticated:return redirect("teacher-login")
    if not settings.ROLLFLOW_PROTECTED_WORKSPACE or not allowed(request.user):
        return HttpResponseForbidden("Verified teaching access required.")
    return None


def dates(request):
    today=timezone.localdate()
    return today,bounded_day(request.GET.get("date"),today)


@never_cache
@require_GET
def schedule(request,mode="day"):
    rejected=deny(request)
    if rejected:return rejected
    try:today,day=dates(request)
    except (ValueError,TypeError):return HttpResponseBadRequest("Choose a valid school date.")
    pub=current()
    week=mode=="week"
    master=mode=="master"
    if week:
        monday=shift(day,-day.weekday())
        days=[personal_schedule(pub,request.user,shift(monday,i),today) for i in range(5)]
    else:days=[personal_schedule(pub,request.user,day,today)]
    return page(request,"teacher_experience_schedule.html",selected=day,today=today,days=days,week=week,master=master,
                prev=shift(day,-7 if week else -1),next=shift(day,7 if week else 1),
                publication=pub,ready=days[0]["ready"],day_closed=days[0]["day_closed"],
                unavailable=days[0]["unavailable"],lessons=days[0]["lessons"])


@never_cache
@require_GET
def classes(request):
    rejected=deny(request)
    if rejected:return rejected
    data=directory_classes(current(),request.user)
    q=request.GET.get("q","").strip()[:100]
    year=request.GET.get("year","")
    if year and year not in {"7","8","9","10","11","12"}:return HttpResponseBadRequest("Choose a valid year level.")
    rows=[r for r in data.values() if (not q or q.casefold() in (r["code"]+" "+r["name"]).casefold())
          and (not year or int(year) in r["years"])]
    rows.sort(key=lambda r:r["code"])
    return page(request,"teacher_experience_classes.html",rows=Paginator(rows,30).get_page(request.GET.get("page")),q=q,year=year,years=range(7,13))


@never_cache
@require_GET
def class_detail(request,code):
    rejected=deny(request)
    if rejected:return rejected
    pub=current()
    record=directory_classes(pub,request.user).get(canonical(code))
    if not record:raise Http404("Class not within your verified teaching scope.")
    day=personal_schedule(pub,request.user,timezone.localdate())
    lessons=[r for r in day["lessons"] if r["code"]==record["code"]]
    students=Paginator(record["students"],50).get_page(request.GET.get("page"))
    return page(request,"teacher_experience_class.html",record=record,students=students,lessons=lessons)


@never_cache
@require_GET
def students(request):
    rejected=deny(request)
    if rejected:return rejected
    data=student_projection(directory_classes(current(),request.user))
    q=request.GET.get("q","").strip()[:100]
    year=request.GET.get("year","")
    if year and year not in {"7","8","9","10","11","12"}:return HttpResponseBadRequest("Choose a valid year level.")
    rows=[r for r in data.values() if (not q or q.casefold() in " ".join((r["student"].first_name,r["student"].preferred_name,r["student"].last_name)).casefold())
          and (not year or r["student"].year_level==int(year))]
    rows.sort(key=lambda r:(r["student"].last_name.casefold(),r["student"].first_name.casefold(),r["student"].pk))
    return page(request,"teacher_experience_students.html",rows=Paginator(rows,30).get_page(request.GET.get("page")),q=q,year=year,years=range(7,13))


@never_cache
@require_GET
def student_detail(request,pk):
    rejected=deny(request)
    if rejected:return rejected
    record=student_projection(directory_classes(current(),request.user)).get(pk)
    if not record:raise Http404("Student not within your verified teaching scope.")
    return page(request,"teacher_experience_student.html",record=record)
