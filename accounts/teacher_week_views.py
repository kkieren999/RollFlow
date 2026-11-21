"""Read-only, date-specific teacher week from the published OneSchool snapshot."""
from datetime import date
from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from .models import ImportedTimetableDay
from .oneschool_views import MIN_DAY, MAX_DAY, current_version, shift_date, coverage_message
from .teacher_schedule import staff_identity, assigned_rows
from .views import role_for


@never_cache
@require_GET
def week(request):
    role = role_for(request.user)
    if role is None:
        return redirect("teacher-login")
    if role != "teacher":
        return HttpResponseForbidden("Teacher access required.")

    from .connected_school import current
    if current():
        from .connected_views import teacher_schedule
        return teacher_schedule(request, week=True)
    version = current_version()
    if version is None:
        return render(request, "live_timetable_pending.html")

    today = timezone.localdate()
    fallback = today
    if not version.days.filter(date=today).exists():
        next_day = version.days.filter(date__gte=today).first() or version.days.last()
        if next_day:
            fallback = next_day.date

    try:
        anchor = date.fromisoformat(request.GET.get("date", fallback.isoformat()))
        if anchor < MIN_DAY or anchor > MAX_DAY:
            raise ValueError("Outside supported range")
    except (ValueError, TypeError):
        anchor = fallback

    monday = shift_date(anchor, -anchor.weekday())
    dates = [shift_date(monday, day) for day in range(5)]
    staff_id, link_message = staff_identity(request.user)
    # Only read a bounded work week from the current *published* version.
    # Archived/draft versions cannot be requested through this endpoint.
    records = ImportedTimetableDay.objects.filter(version=version, date__in=dates)
    days_by_date = {record.date: record for record in records}
    week_days = []
    for day in dates:
        record = days_by_date.get(day)
        rows = assigned_rows(record.allocations, staff_id) if record else []
        # Explicit projection prevents exposing any other staff/room directory,
        # staff identifiers or raw JSON from the imported snapshot.
        lessons = [
            {key: row[key] for key in ("code", "subject", "year", "period", "start", "end", "room")}
            for row in rows
        ]
        lessons.sort(key=lambda x: (x["start"], x["end"], x["period"], x["code"]))
        week_days.append({
            "date": day, "iso": day.isoformat(),
            "published": record is not None, "lessons": lessons,
        })

    return render(request, "teacher_week.html", {
        "version": version,
        "week_days": week_days,
        "week_start": monday,
        "prev_week": shift_date(monday, -7).isoformat(),
        "next_week": shift_date(monday, 7).isoformat(),
        "today_url": today.isoformat(),
        "first_url": version.summary["first_date"],
        "link_message": link_message,
        "coverage_warning": coverage_message(version, today),
        "live_timetable": settings.ROLLFLOW_LIVE_TIMETABLE,
        "lesson_count": sum(len(day["lessons"]) for day in week_days),
    })
