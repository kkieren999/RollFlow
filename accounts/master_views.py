"""Read-only whole-school recurring timetable; development data only."""
from collections import Counter
import re
from django.shortcuts import redirect, render
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .models import SchoolPeriod, Room, TimetableSlot
from .timetable_forms import teachers
from .timetable_views import active_slots
from .staff_views import page
from .views import role_for

DAYS = [(str(value), label) for value, label in TimetableSlot._meta.get_field("weekday").choices]

def break_period(period):
    return bool(re.search(r"\b(break|recess|lunch|interval)\b", period.label + " " + period.code, re.I))

def context(request):
    default = str(min(timezone.localdate().isoweekday(), 5))
    day = request.GET.get("day", default)
    if day not in dict(DAYS):
        day = default
    query = request.GET.get("q", "").strip()[:150]
    year = request.GET.get("year", "")
    if year not in [str(y) for y in range(7, 13)]:
        year = ""
    hide = request.GET.get("breaks") == "hide"
    periods = list(SchoolPeriod.objects.filter(active=True).order_by("start_time"))
    slots = list(active_slots().filter(weekday=int(day)))
    staff_count = teachers().count()
    room_count = Room.objects.filter(active=True).count()
    visible = [p for p in periods if not hide or not break_period(p)]
    stats = {}
    for p in visible:
        entries = [s for s in slots if s.period_id == p.pk]
        staff = Counter(s.teacher_id for s in entries)
        rooms = Counter(s.room_id for s in entries)
        stats[p.pk] = dict(staff_clashes=sum(n > 1 for n in staff.values()),
            room_clashes=sum(n > 1 for n in rooms.values()),
            free_staff=max(0, staff_count - len(staff)), free_rooms=max(0, room_count - len(rooms)),
            staff=staff, rooms=rooms)
    visible_ids = {p.pk for p in visible}
    def matches(s):
        text = " ".join([s.school_class.code, s.school_class.name, s.school_class.subject,
                        s.teacher.username, s.teacher.get_full_name(), s.room.code, f"Year {s.school_class.year_level}"])
        return s.period_id in visible_ids and (not year or str(s.school_class.year_level) == year) and query.casefold() in text.casefold()
    filtered = [s for s in slots if matches(s)]
    groups = []
    for y in range(7, 13):
        if year and str(y) != year:
            continue
        group = [s for s in filtered if s.school_class.year_level == y]
        cells = []
        for p in visible:
            stat = stats[p.pk]
            entries = [dict(slot=s, clash=stat["staff"][s.teacher_id] > 1 or stat["rooms"][s.room_id] > 1)
                       for s in sorted(group, key=lambda x: x.school_class.code) if s.period_id == p.pk]
            cells.append(dict(entries=entries, is_break=break_period(p)))
        groups.append(dict(year=y, count=len(group), cells=cells))
    selected = next((s for s in filtered if str(s.pk) == request.GET.get("slot", "")), None)
    return dict(master_days=DAYS, master_day=day, master_day_label=dict(DAYS)[day], master_query=query,
                master_year=year, master_years=range(7, 13), master_hide=hide, master_periods=visible,
                master_groups=groups, master_stats=[stats[p.pk] for p in visible], master_columns=len(visible)+1,
                master_selected=selected, master_count=len(filtered), master_total=len(slots),
                master_staff_count=staff_count, master_room_count=room_count)

@never_cache
@require_http_methods(["GET"])
def master(request, admin_only=False):
    role = role_for(request.user)
    if role is None:
        return redirect("teacher-login")
    if role not in ("teacher", "admin") or (admin_only and role != "admin"):
        return HttpResponseForbidden("Staff access required.")
    data = context(request)
    if role == "admin":
        return page(request, "master", master_admin=True, **data)
    return render(request, "teacher_master.html", data)
