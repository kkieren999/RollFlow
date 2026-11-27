import csv
import io
from functools import wraps
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST
from .models import SecurityEvent, StaffProfile, Student, SchoolClass, TimetableSlot
from .staff_forms import StaffForm, ResetPasswordForm, StaffImportForm
from .views import role_for
from .permissions import can_teach, teaching_users
from .security_service import audit, account_state, lock_administrator, revoke_account_grants

NAVIGATION = (
    ("SCHOOL MANAGEMENT", (("dashboard", "Dashboard"), ("staff", "Staff Management"), ("students", "Student Management"), ("classes", "Class Management"), ("timetable", "Timetable Management"), ("master", "Master Timetable"), ("relief", "Relief & Supervision"))),
    ("OPERATIONS", (("attendance", "Attendance Monitoring"), ("movements", "Student Movements"), ("notices", "School Notices"), ("reports", "Reports"))),
    ("SYSTEM", (("roles", "Roles & Permissions"), ("data", "Data Management"), ("oneschool", "OneSchool Timetable CSV"), ("audit", "Audit Logs"), ("settings", "School Settings"))),
)
TITLES = dict(item for _, items in NAVIGATION for item in items)

def administrator(view):
    @wraps(view)
    @never_cache
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("admin-login")
        if role_for(request.user) != "admin":
            return HttpResponseForbidden("Administrator access required.")
        return view(request, *args, **kwargs)
    return wrapped

def page(request, section, **context):
    navigation=NAVIGATION
    if settings.ROLLFLOW_LIVE_TIMETABLE:
        available={"dashboard","staff","students","classes","timetable","master","data","oneschool","audit","roles"}
        navigation=tuple((group,tuple(item for item in items if item[0] in available)) for group,items in NAVIGATION)
        navigation=tuple((group,items) for group,items in navigation if items)
    from .school_access import has_workspace
    return render(request, "staff_portal.html", {"has_staff_workspace": has_workspace(request.user), "can_access_teaching": can_teach(request.user), "section": section, "title": TITLES[section], "navigation": navigation, "live_timetable": settings.ROLLFLOW_LIVE_TIMETABLE, **context})

def revoke_sessions(user):
    # Development implementation: database sessions only.
    for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
        if str(session.get_decoded().get("_auth_user_id")) == str(user.pk):
            session.delete()

def log(request, event, target):
    SecurityEvent.objects.create(actor=request.user, event=event, subject=target.username)

def set_role(user, role):
    user.is_staff = role == "admin"
    user.is_superuser = role == "admin"
    user.save()
    # V3.1 deliberately exposes only the two roles. Remove stale group grants.
    user.groups.clear()
    user.user_permissions.clear()
    if role == "teacher":
        user.groups.add(Group.objects.get(name="Teacher"))

@administrator
@require_http_methods(["GET"])
def dashboard(request):
    users = User.objects.all()
    from .oneschool_views import current_version, coverage_message
    from .connected_school import current as connected_current, visible_slots
    connected=connected_current()
    version=current_version()
    imported_stats=[]
    if version:
        a=version.summary
        current=version.days.filter(date=timezone.localdate()).first()
        rows=current.allocations if current else []
        imported_stats=[("Imported allocations",a.get("lessons",0)),("Imported classes",a.get("classes",0)),("Imported staff IDs",a.get("staff",0)),("Imported rooms",a.get("rooms",0)),("Imported school days",a.get("days",0)),("Today’s allocations",len(rows)),("Today’s classes",len({r["code"] for r in rows}))]
    if connected:
        today_rows = visible_slots(connected, timezone.localdate())
        # Count the retained snapshot itself. Older publications and synthetic
        # fixtures may omit summary keys; do not report a fabricated zero.
        snapshot=connected.snapshot
        classes,slots,bindings=(snapshot.get(k) for k in ("classes","slots","bindings"))
        valid_classes=isinstance(classes,list) and all(isinstance(c,dict) for c in classes)
        imported_stats = [
            ("Published classes",len(classes) if valid_classes else "Unavailable"),
            ("Published lesson allocations",len(slots) if isinstance(slots,list) else "Unavailable"),
            ("Published student-class links",sum(len(c["students"]) for c in classes)
             if valid_classes and all(isinstance(c.get("students"),list) for c in classes) else "Unavailable"),
            ("Verified mappings at publication",len(bindings) if isinstance(bindings,dict) else "Unavailable"),
            ("Today’s allocations",len(today_rows)),
            ("Today’s classes",len({row["code"] for row in today_rows}))]
    return page(request, "dashboard", connected_publication=connected, published_import=version, coverage_warning=coverage_message(version,timezone.localdate()) if version else "", imported_stats=imported_stats, stats=[
        ("Staff accounts", users.count()),
        ("Active staff", users.filter(is_active=True).count()),
        ("Teachers", teaching_users().count()),
        ("Administrators", users.filter(is_staff=True, is_superuser=True).count()),
        ("Enrolled students", Student.objects.filter(status=Student.Status.ACTIVE).count()),
        ("Student records", Student.objects.count()),
        ("Manual active classes", SchoolClass.objects.filter(active=True).count()),
        ("Manual active timetable slots", TimetableSlot.objects.filter(active=True).count()),
    ], events=SecurityEvent.objects.select_related("actor").all()[:6])

@administrator
@require_http_methods(["GET"])
def section(request, section):
    if section == "dashboard":
        return redirect("management-dashboard")
    if section == "roles":
        return redirect("school-access-manage")
    if section == "relief" and settings.ROLLFLOW_PROTECTED_WORKSPACE:
        return redirect("workforce-board")
    if section == "movements" and settings.ROLLFLOW_PROTECTED_WORKSPACE:
        return redirect("movement-board")
    if section not in TITLES:
        return HttpResponseBadRequest("Unknown section.")
    if section == "students":
        return redirect("management-student-directory")
    if section == "classes":
        return redirect("management-class-directory")
    if section == "timetable":
        return redirect("management-timetable")
    if section == "master":
        return redirect("management-master")
    if section == "oneschool":
        return redirect("oneschool-centre")
    if section == "staff":
        q = request.GET.get("q", "").strip()[:150]
        status = request.GET.get("status", "all")
        users = User.objects.select_related("staff_profile").order_by("last_name", "first_name", "username")
        if q:
            users = users.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) |
                Q(staff_profile__staff_id__icontains=q) | Q(staff_profile__faculty__icontains=q))
        if status == "active":
            users = users.filter(is_active=True)
        elif status == "inactive":
            users = users.filter(is_active=False)
        elif status == "teacher":
            users = users.filter(pk__in=teaching_users().values("pk"))
        elif status == "admin":
            users = users.filter(is_staff=True, is_superuser=True)
        from django.core.paginator import Paginator
        sort=request.GET.get("sort","name")
        orders={"name":("last_name","first_name"),"username":("username",),"faculty":("staff_profile__faculty",),"status":("is_active",)}
        sort=sort if sort in orders else "name"
        direction="desc" if request.GET.get("dir")=="desc" else "asc"
        users=users.order_by(*[("-" if direction=="desc" else "")+f for f in orders[sort]],"pk")
        return page(request, section, staff_page=Paginator(users, 50).get_page(request.GET.get("page")), q=q, status=status, sort=sort, direction=direction)
    if section == "audit":
        return page(request, section, events=SecurityEvent.objects.select_related("actor").all()[:200])
    if section == "data":
        return page(request, section, import_form=StaffImportForm())
    return page(request, section)

@administrator
@require_http_methods(["GET", "POST"])
def staff_edit(request, pk=None):
    target = get_object_or_404(User, pk=pk) if pk is not None else None
    from .models import PendingTeacherSetup
    if target and PendingTeacherSetup.objects.filter(user=target, activated_at__isnull=True).exists():
        messages.error(request, "Complete pending teacher verification in Automated School Setup. Use password reset separately.")
        return redirect("automated-school-setup")
    form = StaffForm(request.POST if request.method == "POST" else None, target=target, actor=request.user)
    if request.method == "POST" and form.is_valid():
        c = form.cleaned_data
        try:
            with transaction.atomic():
                if not lock_administrator(request.user):
                    return HttpResponseForbidden("Administrator access revoked.")
                before = {}
                if target:
                    user = User.objects.select_for_update().get(pk=target.pk)
                    before = account_state(user)
                    if user.pk == request.user.pk and (c["role"] != "admin" or not c["active"]):
                        return HttpResponseForbidden("Cannot remove your own administrator access.")
                    old_role = (user.is_staff, user.is_superuser)
                    old_active = user.is_active
                    user.first_name, user.last_name = c["first_name"], c["last_name"]
                    user.is_active = c["active"]
                else:
                    user = User(username=c["username"], first_name=c["first_name"], last_name=c["last_name"], is_active=c["active"])
                    user.set_password(c["password"])
                set_role(user, c["role"])
                existing_profile = StaffProfile.objects.select_for_update().filter(user=user).first()
                previous_id = (existing_profile.staff_id or "").upper() if existing_profile else ""
                # A changed ID loses its old verification unless the administrator
                # explicitly attests to the *new* ID on this submission.
                link_verified = bool(c["staff_id"]) and (
                    c["verify_timetable_link"] or (
                        existing_profile is not None
                        and existing_profile.timetable_link_verified
                        and previous_id == c["staff_id"]
                    )
                )
                permission = c.get("teaching_permission")
                teaching_enabled = {"allow": True, "deny": False, "default": None}.get(
                    permission, existing_profile.teaching_enabled if existing_profile else None)
                StaffProfile.objects.update_or_create(user=user, defaults={
                    "teaching_enabled": teaching_enabled,
                    "staff_id": c["staff_id"], "faculty": c["faculty"], "campus": c["campus"],
                    "class_codes": c["class_codes"], "timetable_link_verified": link_verified,
                })
                if existing_profile and (previous_id != c["staff_id"] or not link_verified or not can_teach(user) or not user.is_active):
                    from .models import ConnectedStaffMapping
                    if ConnectedStaffMapping.objects.filter(profile=existing_profile).delete()[0]:
                        SecurityEvent.objects.create(actor=request.user, event="connected_mapping_revoked", subject=user.username)
                if link_verified != bool(existing_profile and existing_profile.timetable_link_verified) or (
                    c["staff_id"] and previous_id != c["staff_id"] and link_verified
                ):
                    SecurityEvent.objects.create(
                        actor=request.user,
                        event="staff_link_verified" if link_verified else "staff_link_revoked",
                        subject=user.username,
                    )
                if target and user.pk != request.user.pk and (old_active != user.is_active or old_role != (user.is_staff, user.is_superuser)):
                    revoke_sessions(user)
                if teaching_enabled != (existing_profile.teaching_enabled if existing_profile else None):
                    SecurityEvent.objects.create(actor=request.user, event="teaching_permission_changed", subject=user.username)
                if not user.is_active:
                    revoke_account_grants(request.user, user)
                audit(request.user, "account_updated" if target else "account_created", user, before=before, after=account_state(user))
                log(request, "staff_updated" if target else "staff_created", user)
            messages.success(request, "Staff details saved.")
            return redirect("management-section", section="staff")
        except IntegrityError:
            form.add_error(None, "A staff ID or username is already in use.")
    return page(request, "staff", form=form, target=target, editor=True)

@administrator
@require_http_methods(["GET", "POST"])
def staff_reset(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        return HttpResponseForbidden("Change your own password using the administrator account settings.")
    form = ResetPasswordForm(request.POST if request.method == "POST" else None, target=target)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            if not lock_administrator(request.user):
                return HttpResponseForbidden("Administrator access revoked.")
            target = User.objects.select_for_update().get(pk=pk)
            target.set_password(form.cleaned_data["password"])
            target.save(update_fields=["password"])
            revoke_sessions(target)
            audit(request.user, "password_reset", target)
            log(request, "password_reset", target)
        messages.success(request, "Password reset. Existing sessions have been revoked. Share credentials only through an approved channel.")
        return redirect("management-section", section="staff")
    return page(request, "staff", form=form, target=target, editor=True, reset=True)

@administrator
@require_POST
def staff_status(request, pk):
    with transaction.atomic():
        if not lock_administrator(request.user):
            return HttpResponseForbidden("Administrator access revoked.")
        target = get_object_or_404(User.objects.select_for_update(), pk=pk)
        before = account_state(target)
        if target.pk == request.user.pk:
            return HttpResponseForbidden("You cannot deactivate your own administrator account.")
        value = request.POST.get("active")
        if value not in ("0", "1"):
            return HttpResponseBadRequest("Invalid status.")
        from .models import PendingTeacherSetup
        if value == "1" and PendingTeacherSetup.objects.filter(user=target, activated_at__isnull=True).exists():
            messages.error(request, "Activate pending teacher accounts through Automated School Setup.")
            return redirect("automated-school-setup")
        if value == "1" and not target.has_usable_password():
            messages.error(request, "Reset this imported account's password before activating it.")
            return redirect("management-section", section="staff")
        target.is_active = value == "1"
        target.save(update_fields=["is_active"])
        if not target.is_active:
            from .models import ConnectedStaffMapping
            if ConnectedStaffMapping.objects.filter(profile__user=target).delete()[0]:
                SecurityEvent.objects.create(actor=request.user, event="connected_mapping_revoked", subject=target.username)
        if not target.is_active:
            revoke_account_grants(request.user, target)
        revoke_sessions(target)
        audit(request.user, "account_status_changed", target, before=before, after=account_state(target))
        log(request, "account_activated" if target.is_active else "account_deactivated", target)
    messages.success(request, "Account status updated.")
    return redirect("management-section", section="staff")

CSV_HEADER = ["staff_id", "username", "first_name", "last_name", "faculty", "campus"]

def parse_staff_csv(upload):
    if upload.size > 200000:
        raise ValidationError("Choose a CSV below 200 KB.")
    try:
        raw = upload.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(raw), strict=True)
        if reader.fieldnames != CSV_HEADER:
            raise ValidationError("Use the exact six-column header shown below.")
        rows, ids, names = [], set(), set()
        for line, row in enumerate(reader, 2):
            if line > 201:
                raise ValidationError("Import at most 200 rows at once.")
            if None in row or any(value is None for value in row.values()):
                raise ValidationError(f"Incorrect columns on row {line}.")
            values = {key: val.strip() for key, val in row.items()}
            values["username"] = values["username"].lower()
            values["staff_id"] = values["staff_id"].upper()
            if not all(values[k] for k in CSV_HEADER[:4]) or len(values["staff_id"]) > 40 or len(values["username"]) > 150 or any(len(values[k]) > 100 for k in CSV_HEADER[2:]):
                raise ValidationError(f"Invalid field length or blank required field on row {line}.")
            User.username_validator(values["username"])
            name, staff_id = values["username"], values["staff_id"]
            if name in names or staff_id in ids or User.objects.filter(username__iexact=name).exists() or StaffProfile.objects.filter(staff_id__iexact=staff_id).exists():
                raise ValidationError(f"Duplicate username or staff ID on row {line}.")
            names.add(name); ids.add(staff_id); rows.append(values)
        if not rows:
            raise ValidationError("The CSV contains no staff records.")
        return rows
    except (UnicodeError, csv.Error) as error:
        raise ValidationError("Use a valid UTF-8 CSV file.") from error

@administrator
@require_POST
def staff_import(request):
    form = StaffImportForm(request.POST, request.FILES)
    if form.is_valid():
        try:
            with transaction.atomic():
                rows = parse_staff_csv(form.cleaned_data["csv"])
                teacher_group = Group.objects.get(name="Teacher")
                for row in rows:
                    user = User(username=row["username"], first_name=row["first_name"], last_name=row["last_name"], is_active=False)
                    user.set_unusable_password()
                    user.save()
                    user.groups.add(teacher_group)
                    StaffProfile.objects.create(user=user, staff_id=row["staff_id"], faculty=row["faculty"], campus=row["campus"])
                    log(request, "staff_imported", user)
            messages.success(request, f"Imported {len(rows)} inactive teachers. Reset passwords before activation.")
            return redirect("management-section", section="staff")
        except ValidationError as err:
            form.add_error("csv", err)
        except IntegrityError:
            form.add_error("csv", "Duplicate details detected. No staff were imported.")
    return page(request, "data", import_form=form)
