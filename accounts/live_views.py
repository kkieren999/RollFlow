"""Authenticated application shell and transactional attendance endpoints."""
from collections import Counter
from django.utils.crypto import salted_hmac
from urllib.parse import urlencode
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods
from .attendance import (MARKS, AttendanceUnavailable, can_monitor, publication_ready,
                         own_lessons, lesson_key, lesson_valid, roster_for, roll_for,
                         roll_matches, status_label, lesson_started)
from .connected_school import current, visible_slots
from .models import (AttendanceRoll, AttendanceRevision, ConnectedSchoolPublication,
                     StaffProfile, SecurityEvent, PendingTeacherSetup, ImportedTimetable)
from .permissions import can_teach
from .school_access import grants_for, visible_modules


def eligible(user):
    return (user.is_authenticated and user.is_active and not
            PendingTeacherSetup.objects.filter(user=user, activated_at__isnull=True).exists())


def shell(user):
    grants = grants_for(user)
    modules = visible_modules(grants)
    modules.pop("attendance_monitor", None)
    from .movement_service import may_access
    from .classroom_support import board_allowed
    from .reporting import available
    reports=available(user,grants)
    modules={k:v for k,v in modules.items() if not k.startswith(("report_","export_"))}
    from .workforce_service import self_allowed, authority
    return {"report_access":bool(reports),"support_access":board_allowed(user),"workforce_self":self_allowed(user),"workforce_monitor":authority(user),"movements":may_access(user), "teaching": can_teach(user), "monitor": can_monitor(user),
            "admin_access": user.is_staff and user.is_superuser,
            "modules": modules, "grants": grants}


def page(request, template, *, _presentation_shell=None, **context):
    from django.conf import settings
    if settings.ROLLFLOW_PROTECTED_WORKSPACE and template in ("live_roll.html", "classroom_tools.html", "movement_issue.html") and context.get("row"):
        from .workflow_integration import lesson_links
        context["lesson_links"] = lesson_links(context["row"])
        context["lesson_active"] = {"live_roll.html":"roll", "classroom_tools.html":"classroom", "movement_issue.html":"movement"}[template]
    # Share the freshly computed presentation snapshot with the context processor
    # only during this render. Never use it for endpoint authorization or writes.
    ctx = shell(request.user) if _presentation_shell is None else _presentation_shell
    request._rf_render_shell = ctx
    try:
        return render(request, template, {**ctx, **context})
    finally:
        del request._rf_render_shell


@never_cache
@require_GET
def home(request):
    if not request.user.is_authenticated:
        return redirect("teacher-login")
    if not eligible(request.user):
        return HttpResponseForbidden("Account not authorised.")
    ctx = shell(request.user)
    if not (ctx["teaching"] or ctx["monitor"] or ctx["admin_access"] or ctx["modules"] or ctx["report_access"]):
        return HttpResponseForbidden("No assigned workspace.")
    pub = current()
    from django.conf import settings
    from .leadership_experience import dashboard, operational_summary
    leadership=dashboard(request.user) if settings.ROLLFLOW_PROTECTED_WORKSPACE and ctx["report_access"] else None
    operations=operational_summary(request.user,pub) if settings.ROLLFLOW_PROTECTED_WORKSPACE else []
    return page(request, "live_home.html", _presentation_shell=ctx, ready=publication_ready(pub),leadership=leadership,operations=operations)


def roster_token(students):
    return salted_hmac("attendance-roster-v1", ",".join(str(s.pk) for s in sorted(students, key=lambda s:s.pk)), algorithm="sha256").hexdigest()


def lesson_url(row):
    code, period, start = lesson_key(row)
    return reverse("live-roll") + "?" + urlencode({"code": code, "period": period, "start": start})


@never_cache
@require_GET
def my_day(request):
    if not request.user.is_authenticated:
        return redirect("teacher-login")
    if not eligible(request.user) or not can_teach(request.user):
        return HttpResponseForbidden("Teaching access required.")
    from django.conf import settings
    if settings.ROLLFLOW_PROTECTED_WORKSPACE:
        from .teacher_experience_views import schedule
        return schedule(request)
    pub, day = current(), timezone.localdate()
    rows = own_lessons(pub, request.user, day)
    lessons = [dict(row, url=lesson_url(row), status=status_label(roll_for(day,row), pub))
               for row in rows]
    from .workforce_service import closed, absent
    return page(request, "live_day.html", lessons=lessons, day=day, ready=publication_ready(pub), day_closed=closed(pub,day), unavailable=absent(pub,day,request.user))


@never_cache
@require_http_methods(["GET", "POST"])
def mark_roll(request):
    if not request.user.is_authenticated:
        return redirect("teacher-login")
    if not eligible(request.user) or not can_teach(request.user):
        return HttpResponseForbidden("Teaching access required.")
    day = timezone.localdate()
    if request.GET.get("date") and request.GET["date"] != day.isoformat():
        return HttpResponseBadRequest("Attendance is only editable for today’s verified allocation.")
    key = tuple(request.GET.get(k, "") for k in ("code", "period", "start"))
    if not all(key):
        return HttpResponseBadRequest("Select a lesson from My day.")
    try:
        with transaction.atomic():
            if request.method == "POST":
                # Serialise writes against other attendance submissions and current publication changes.
                actor = User.objects.select_for_update().get(pk=request.user.pk)
                list(ImportedTimetable.objects.select_for_update().order_by("pk"))
                from .models import OneSchoolArchiveBatch
                list(OneSchoolArchiveBatch.objects.select_for_update().order_by("pk"))
                pub = ConnectedSchoolPublication.objects.select_for_update().filter(active=True).first()
                list(StaffProfile.objects.select_for_update().filter(user=actor))
            else:
                pub, actor = current(), request.user
            if not eligible(actor) or not can_teach(actor):
                return HttpResponseForbidden("Teaching access required.")
            row = next((r for r in own_lessons(pub, actor, day) if lesson_key(r) == key), None)
            if row is None:
                return HttpResponseForbidden("No current verified allocation for this lesson.")
            students = roster_for(pub, row["code"], day, lock=request.method == "POST")
            roll = roll_for(day, row, lock=request.method == "POST")
            if AttendanceRoll.objects.filter(lesson_date=day, class_code=row["code"]).exclude(pk=roll.pk if roll else None).filter(start__lt=row["end"], end__gt=row["start"]).exists():
                raise AttendanceUnavailable("A different overlapping roll exists. Administrator reconciliation required.")
            if roll and not roll_matches(roll, pub, row, actor, students):
                raise AttendanceUnavailable("Existing roll differs from current publication or roster. Administrator reconciliation required.")
            error = ""
            if request.method == "POST":
                if roll and roll.submitted_at:
                    raise AttendanceUnavailable("Submitted rolls are locked. Request an administrator correction.")
                expected = str(roll.revision if roll else 0)
                if (request.POST.get("roster_token") != roster_token(students) or request.POST.get("revision") != expected or request.POST.get("publication") != str(pub.pk)
                        or request.POST.get("day") != day.isoformat()):
                    raise AttendanceUnavailable("This page is stale. Reload before saving.")
                action = request.POST.get("action")
                if action not in ("draft", "submit"):
                    return HttpResponseBadRequest("Choose save draft or submit.")
                if action == "submit" and not lesson_started(day,row):
                    raise AttendanceUnavailable("Attendance cannot be submitted before the lesson starts.")
                fields = {"mark_" + str(s.pk): str(s.pk) for s in students}
                actual = {k for k in request.POST if k.startswith("mark_")}
                if actual != set(fields) or any(len(request.POST.getlist(k)) != 1 for k in fields):
                    return HttpResponseBadRequest("The roster changed or an invalid student was supplied.")
                marks = {sid: request.POST[k] for k,sid in fields.items()}
                allowed = {k for k,_ in MARKS}
                if any(m not in allowed | {""} for m in marks.values()):
                    return HttpResponseBadRequest("Invalid attendance status.")
                if action == "submit" and (not all(marks.values()) or request.POST.get("certify") != "yes"):
                    error = "Mark every student and confirm the certification before submission."
                else:
                    if roll is None:
                        roll = AttendanceRoll(publication=pub, lesson_date=day, class_code=row["code"],
                            period=str(row["period"]), start=row["start"], end=row["end"], teacher=actor,
                            roster=sorted(s.pk for s in students))
                    else:
                        roll.revision += 1
                    roll.marks = marks
                    if action == "submit":
                        roll.submitted_at = timezone.now()
                    roll.save()
                    AttendanceRevision.objects.create(roll=roll, revision=roll.revision,
                        actor=actor, action=action, marks=marks)
                    SecurityEvent.objects.create(actor=actor, event="attendance_" + action, subject=str(roll.pk))
                    return redirect(lesson_url(row))
            else:
                marks = roll.marks if roll else {}
            student_rows = [{"name": s.preferred_name or s.first_name, "last":s.last_name,
                             "pk":s.pk, "mark":marks.get(str(s.pk),"")} for s in students]
            return page(request, "live_roll.html", row=row, day=day, publication_id=pub.pk, roll=roll,
                        students=student_rows, choices=MARKS, error=error, roster_token=roster_token(students), started=lesson_started(day,row))
    except AttendanceUnavailable as exc:
        return render(
            request, "live_conflict.html", {**shell(request.user), "error":str(exc)}, status=409)
    except IntegrityError:
        return render(request, "live_conflict.html", {**shell(request.user),
            "error":"Another request changed the roll. Reload and retry."}, status=409)


@never_cache
@require_GET
def monitor(request):
    if not request.user.is_authenticated:
        return redirect("teacher-login")
    if not eligible(request.user) or not can_monitor(request.user):
        return HttpResponseForbidden("Attendance monitoring permission required.")
    from datetime import date
    from .attendance_operations import daily_status
    try:
        day=date.fromisoformat(request.GET.get("date") or timezone.localdate().isoformat())
    except ValueError:
        return HttpResponseBadRequest("Choose a valid date.")
    pub=current()
    rows,summary=daily_status(pub,day)
    from .workforce_service import closed
    return page(request,"live_monitor.html",rows=rows,summary=summary,day=day,ready=publication_ready(pub),day_closed=closed(pub,day))
