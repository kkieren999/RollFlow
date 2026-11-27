"""RC2.5: protected administrator navigation and read-only operational review.

All changes to school data, permissions and operations use existing authorised
transactional workflows. No delegated rights, direct system commands or secrets.
"""
from django.conf import settings
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q, Exists, OuterRef
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .staff_views import administrator
from .attendance import publication_ready
from .connected_school import current
from .data_reconciliation import source_issues
from .models import (AccessAudit, ConnectedSchoolPublication, ImportedTimetable,
                     MovementDestination, OneSchoolArchiveBatch, PendingTeacherSetup,
                     RoleTemplate, SecurityEvent, StaffAccessGrant, StaffProfile,
                     Student, SchoolClass, Room, SchoolPeriod)
from .permissions import teaching_users
from rollflow.release_policy import VERSION, OPEN_GATES


def link(label, name, description, **kwargs):
    return {"label": label, "url": reverse(name, kwargs=kwargs or None), "description": description}


def counts():
    users = User.objects.all()
    return [
        ("Staff accounts", users.count()),
        ("Active accounts", users.filter(is_active=True).count()),
        ("Inactive accounts", users.filter(is_active=False).count()),
        ("Pending teacher verification", PendingTeacherSetup.objects.filter(activated_at__isnull=True).count()),
        ("Teaching accounts", teaching_users().count()),
        ("Active administrator accounts", users.filter(is_active=True, is_staff=True, is_superuser=True).count()),
        ("Active students", Student.objects.filter(status=Student.Status.ACTIVE).count()),
        ("Manual active classes", SchoolClass.objects.filter(active=True).count()),
    ]


def account_rows(request):
    now = timezone.now()
    qs = User.objects.select_related("staff_profile").annotate(
        pending=Exists(PendingTeacherSetup.objects.filter(user_id=OuterRef("pk"), activated_at__isnull=True)),
        recorded_grant=Exists(StaffAccessGrant.objects.filter(user_id=OuterRef("pk"))),
    )
    q = request.GET.get("q", "").strip()[:150]
    status = request.GET.get("status", "all")
    filters = {
        "all": Q(), "active": Q(is_active=True, pending=False),
        "inactive": Q(is_active=False), "pending": Q(pending=True),
        "admin": Q(is_staff=True, is_superuser=True, is_active=True, pending=False),
        "unverified": Q(is_active=True, pending=False) & ~Q(staff_profile__timetable_link_verified=True),
        "granted": Q(recorded_grant=True),
    }
    if status not in filters:
        status = "all"
    qs = qs.filter(filters[status])
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) |
                       Q(last_name__icontains=q) | Q(staff_profile__staff_id__icontains=q))
    rows = Paginator(qs.order_by("username", "pk"), 25).get_page(request.GET.get("page"))
    return {"rows": rows, "q": q, "status": status, "now": now,
            "statuses": [("all", "All accounts"), ("active", "Active, not pending"),
                         ("inactive", "Inactive"), ("pending", "Pending verification"),
                         ("admin", "Active administrators"), ("unverified", "No verified timetable ID"),
                         ("granted", "Has recorded grant (not necessarily effective)")]}


def audit_rows(request):
    q = request.GET.get("q", "").strip()[:150]
    source = request.GET.get("source", "security")
    if source not in ("security", "access"):
        source = "security"
    if source == "access":
        qs = AccessAudit.objects.select_related("actor", "target")
        if q:
            qs = qs.filter(Q(action__icontains=q) | Q(actor__username__icontains=q) |
                           Q(target__username__icontains=q))
    else:
        qs = SecurityEvent.objects.select_related("actor")
        if q:
            qs = qs.filter(Q(event__icontains=q) | Q(actor__username__icontains=q) |
                           Q(subject__icontains=q))
    return {"rows": Paginator(qs.order_by("-created_at", "-pk"), 50).get_page(request.GET.get("page")),
            "q": q, "source": source}


@administrator
@require_GET
def centre(request, section="overview"):
    if not settings.ROLLFLOW_PROTECTED_WORKSPACE:
        raise Http404
    if section not in ("overview", "accounts", "audit", "settings"):
        raise Http404
    context = {"section": section, "version": VERSION}
    if section == "accounts":
        context.update(account_rows(request))
    elif section == "audit":
        context.update(audit_rows(request))
    else:
        pub = current()
        today = timezone.localdate()
        issues = source_issues(pub)
        ready = publication_ready(pub)
        context.update(publication=pub, issues=issues, ready=ready,
                       in_coverage=bool(pub and pub.starts <= today <= pub.ends),
                       version_count=ConnectedSchoolPublication.objects.count(),
                       import_count=OneSchoolArchiveBatch.objects.filter(status="staged").count(),
                       draft_count=ImportedTimetable.objects.filter(status="draft").count(),
                       destinations=MovementDestination.objects.filter(active=True).count(),
                       rooms=Room.objects.count(), periods=SchoolPeriod.objects.count(),
                       gates=OPEN_GATES)
        if section == "overview":
            context["stats"] = counts()
            context["groups"] = [
                ("School directories", [
                    link("Staff directory", "management-section", "Create, edit, reset and deactivate staff using existing review controls.", section="staff"),
                    link("Student directory", "management-student-directory", "Review enrolments, student profiles and approved imports."),
                    link("Class directory", "management-class-directory", "Manage manual class records and dated enrolments."),
                    link("Timetable management", "management-timetable", "Manage manual lessons, rooms and periods."),
                    link("Master timetable", "management-master", "Inspect published or manual allocations.")]),
                ("Accounts and security", [
                    link("Account review", "admin-account-review", "Find inactive, pending and unverified accounts; inspect effective access."),
                    link("Roles & permissions", "school-access-manage", "Explicit scoped grants and revocation."),
                    link("Role templates", "security-templates", "Review and archive capability bundles."),
                    link("Audit & activity", "admin-audit-review", "Search and page through security and access events.")]),
                ("OneSchool and reconciliation", [
                    link("Document imports", "oneschool-documents", "Review uploaded sources before applying them."),
                    link("Timetable imports", "oneschool-centre", "Review timetable versions and publish approved sources."),
                    link("School data centre", "school-data-overview", "Source diagnostics, publication history and guarded restore."),
                    link("Dated school publication", "connected-dated", "Review and publish the exact dated snapshot."),
                    link("Attendance reconciliation", "school-data-transfers", "Review eligible submitted rolls for approved transfer."),
                    link("Automated setup", "automated-school-setup", "Review pending imported teacher identities.")]),
                ("Operations and system", [
                    link("Attendance overview", "live-monitor", "Review central roll completion."),
                    link("Student movements", "movement-board", "Review movement register."),
                    link("Movement destinations", "movement-destinations", "Configure authorised service destinations."),
                    link("Workforce allocations", "workforce-board", "Review relief, supervision and approved operational changes."),
                    link("System settings & readiness", "admin-system-settings", "Inspect mode, source readiness, configuration links and recovery boundaries.")]),
            ]
    return render(request, "admin_experience.html", context)
