from datetime import timedelta
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.utils.html import json_script
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST
from django.middleware.csrf import get_token
from .models import LoginWindow, SecurityEvent
from .permissions import can_teach

def role_for(user):
    from .security_service import eligible_account
    if not eligible_account(user):
        return None
    if user.is_staff and user.is_superuser:
        return "admin"
    if can_teach(user):
        return "teacher"
    return None

def portal_allowed(user, mode):
    if mode == "admin":
        return role_for(user) == "admin"
    if mode == "unified":
        from .school_access import has_workspace
        from .live_views import eligible
        return eligible(user) and (role_for(user) is not None or has_workspace(user))
    return can_teach(user)


def portal_destination(user, mode):
    if mode == "admin":
        return "management-dashboard"
    if mode == "unified":
        if settings.ROLLFLOW_PROTECTED_WORKSPACE:
            return "live-home"
        from .school_access import has_workspace
        if has_workspace(user):
            return "school-workspace"
        if role_for(user) == "admin":
            return "management-dashboard"
    return "teacher"

def limit_key(request, username):
    return salted_hmac("rollflow-login", request.META.get("REMOTE_ADDR", "") + "|" + username.casefold(), algorithm="sha256").hexdigest()

def consume_attempt(key):
    now = timezone.now()
    with transaction.atomic():
        row, _ = LoginWindow.objects.select_for_update().get_or_create(key=key, defaults={"started_at": now})
        if now - row.started_at >= timedelta(minutes=15):
            row.count, row.started_at = 0, now
        if row.count >= 10:
            return False
        row.count += 1
        row.save(update_fields=["count", "started_at"])
    return True

@never_cache
@require_http_methods(["GET", "POST"])
def portal_login(request, mode="unified"):
    if request.method == "GET" and portal_allowed(request.user, mode):
        return redirect(portal_destination(request.user, mode))
    error = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()[:150]
        password = request.POST.get("password", "")[:1024]
        key = limit_key(request, username)
        ip_key = limit_key(request, "__all_usernames__")
        if not consume_attempt(ip_key) or not consume_attempt(key):
            return render(request, "login.html", {"live_timetable": settings.ROLLFLOW_LIVE_TIMETABLE, "mode": mode, "error": "Too many attempts. Try again in 15 minutes."}, status=429)
        user = authenticate(request, username=username, password=password)
        if user is not None and portal_allowed(user, mode):
            login(request, user)
            LoginWindow.objects.filter(key=key).delete()
            SecurityEvent.objects.create(actor=user, event="login", subject=mode)
            return redirect(portal_destination(user, mode))
        error = "Incorrect username or password for this portal."
    return render(request, "login.html", {"live_timetable": settings.ROLLFLOW_LIVE_TIMETABLE, "mode": mode, "error": error})

@never_cache
@require_http_methods(["GET"])
def teacher(request):
    role = role_for(request.user)
    if role is None:
        return redirect("teacher-login")
    if not can_teach(request.user):
        return HttpResponseForbidden("Teaching permission is required.")
    if settings.ROLLFLOW_PROTECTED_WORKSPACE:
        return redirect("live-day")
    from .connected_school import current
    if current() or settings.ROLLFLOW_LIVE_TIMETABLE:
        return redirect("teacher-timetable")
    user = request.user
    profile = getattr(user, "staff_profile", None)
    identity = {
        "id": user.pk,
        "username": user.get_username(),
        "name": user.get_full_name() or user.get_username(),
        "faculty": profile.faculty if profile else "",
        "campus": profile.campus if profile else "",
        "logout": "/logout/",
        "csrf": get_token(request),
    }
    html = (settings.BASE_DIR / "index.html").read_text(encoding="utf-8")
    marker = "<!-- ROLLFLOW_SERVER_BOOTSTRAP -->"
    if html.count(marker) != 1:
        return HttpResponse("Teacher portal integration is not configured.", status=503)
    html = html.replace(marker, str(json_script(identity, "rollflow-server-identity")), 1)
    return HttpResponse(html, content_type="text/html; charset=utf-8")

@never_cache
@require_POST
def sign_out(request):
    if request.user.is_authenticated:
        SecurityEvent.objects.create(actor=request.user, event="logout")
    logout(request)
    return redirect("teacher-login")


@never_cache
@require_http_methods(["GET"])
def teacher_timetable(request):
    role = role_for(request.user)
    if role is None:
        return redirect("teacher-login")
    if not can_teach(request.user):
        return HttpResponseForbidden("Teacher access required.")
    from .connected_school import current
    if current():
        from .connected_views import teacher_schedule
        return teacher_schedule(request)
    from .oneschool_views import current_version, dated
    if current_version():
        return dated(request, personal=True)
    if settings.ROLLFLOW_LIVE_TIMETABLE:
        return render(request, "live_timetable_pending.html")
    from .timetable_views import active_slots
    from .models import TimetableSlot
    slots = list(active_slots().filter(teacher=request.user))
    schedule = [(label, [slot for slot in slots if slot.weekday == day]) for day, label in TimetableSlot._meta.get_field("weekday").choices]
    return render(request, "teacher_timetable.html", {"schedule": schedule})
