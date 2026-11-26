"""Fail-closed scoped grants, independent of existing teacher and administrator rights."""
from django.db.models import Q
from .models import StaffAccessGrant, StaffProfile, Student, SchoolClass, TimetableSlot

ROLES = (
    "Principal", "Deputy Principal", "Head of Department", "Head of Year",
    "Teacher", "Relief Teacher", "Teacher Aide", "Administration Officer",
    "Student Services", "Attendance Officer", "Guidance Officer", "Custom",
)
CAPABILITIES = {
    "staff": "Staff directory",
    "students": "Student directory",
    "classes": "Manual class directory",
    "timetable": "Manual timetable",
}
SCOPES = {
    "school": set(CAPABILITIES),
    "faculty": {"staff", "classes", "timetable"},
    "year": {"students", "classes", "timetable"},
}
YEARS = {str(y) for y in range(7, 13)}


def valid_scope(scope, value):
    return ((scope == "school" and value == "") or
            (scope == "faculty" and isinstance(value, str) and bool(value.strip()) and value == value.strip()) or
            (scope == "year" and value in YEARS))


def valid_grant(grant):
    caps = grant.capabilities
    return (valid_scope(grant.scope, grant.scope_value) and isinstance(caps, list)
            and bool(caps) and all(isinstance(c, str) and c in SCOPES[grant.scope] for c in caps))


def grants_for(user):
    if not user.is_authenticated or not user.is_active:
        return []
    # Pending imported accounts are not authorised staff identities.
    from .models import PendingTeacherSetup
    if PendingTeacherSetup.objects.filter(user=user, activated_at__isnull=True).exists():
        return []
    return [g for g in StaffAccessGrant.objects.filter(user=user).order_by("pk") if valid_grant(g)]


def has_workspace(user):
    return bool(grants_for(user))


def visible_modules(grants):
    return {code: label for code, label in CAPABILITIES.items()
            if any(code in g.capabilities for g in grants)}


def scoped_rows(grants, module):
    """Union only grants for this specific module; no cross-grant scope borrowing."""
    querysets = {
        "staff": StaffProfile.objects.filter(user__is_active=True).select_related("user").order_by("user__last_name", "user__first_name", "pk"),
        "students": Student.objects.filter(status=Student.Status.ACTIVE).order_by("last_name", "first_name", "pk"),
        "classes": SchoolClass.objects.filter(active=True).select_related("teacher").order_by("code", "pk"),
        "timetable": TimetableSlot.objects.filter(active=True, school_class__active=True).select_related("school_class", "teacher", "room", "period").order_by("weekday", "period__start_time", "pk"),
    }
    qs = querysets[module]
    condition = Q(pk__in=[])
    for g in grants:
        if not valid_grant(g) or module not in g.capabilities:
            continue
        if g.scope == "school":
            return qs
        if g.scope == "faculty":
            # Faculty refers to the assigned staff member, not inferred subject ownership.
            field = "faculty__iexact" if module == "staff" else "teacher__staff_profile__faculty__iexact"
            condition |= Q(**{field: g.scope_value})
        if g.scope == "year":
            field = "school_class__year_level" if module == "timetable" else "year_level"
            condition |= Q(**{field: int(g.scope_value)})
    return qs.filter(condition)
