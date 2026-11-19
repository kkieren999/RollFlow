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

def role_for(user):
    if not user.is_authenticated or not user.is_active:
        return None
    if user.is_staff and user.is_superuser:
        return "admin"
    if not user.is_staff and user.groups.filter(name="Teacher").exists():
        return "teacher"
    return None

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
def portal_login(request, mode="teacher"):
    if request.method == "GET" and role_for(request.user) == mode:
        return redirect("management-dashboard" if mode == "admin" else "teacher")
    error = ""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()[:150]
        password = request.POST.get("password", "")[:1024]
        key = limit_key(request, username)
        ip_key = limit_key(request, "__all_usernames__")
        if not consume_attempt(ip_key) or not consume_attempt(key):
            return render(request, "login.html", {"mode": mode, "error": "Too many attempts. Try again in 15 minutes."}, status=429)
        user = authenticate(request, username=username, password=password)
        if user is not None and role_for(user) == mode:
            login(request, user)
            LoginWindow.objects.filter(key=key).delete()
            SecurityEvent.objects.create(actor=user, event="login", subject=mode)
            return redirect("management-dashboard" if mode == "admin" else "teacher")
        error = "Incorrect username or password for this portal."
    return render(request, "login.html", {"mode": mode, "error": error})

@never_cache
@require_http_methods(["GET"])
def teacher(request):
    role = role_for(request.user)
    if role is None:
        return redirect("teacher-login")
    if role != "teacher":
        return HttpResponseForbidden("Use a teacher account to open the Teacher Portal.")
    if settings.ROLLFLOW_LIVE_TIMETABLE:
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
    if role != "teacher":
        return HttpResponseForbidden("Teacher access required.")
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
