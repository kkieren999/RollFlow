"""Fail-closed scoped grants, independent of existing teacher and administrator rights."""
from django.db.models import Q
from django.utils import timezone
from .models import StaffAccessGrant, StaffProfile, Student, SchoolClass, TimetableSlot

ROLES = (
    "Principal", "Deputy Principal", "Head of Department", "Head of Year",
    "Teacher", "Relief Teacher", "Teacher Aide", "Administration Officer",
    "Student Services", "Attendance Officer", "Guidance Officer", "Business Manager",
    "Learning Support Teacher", "Custom",
)
CAPABILITIES = {
    "staff": "Staff directory",
    "students": "Student directory",
    "classes": "Manual class directory",
    "timetable": "Manual timetable",
    "published_classes": "Published OneSchool classes",
    "published_timetable": "Published OneSchool timetable",
    "attendance_monitor": "School-wide attendance monitoring (summary only)",
}
SCOPES = {
    "school": set(CAPABILITIES),
    "faculty": {"staff", "classes", "timetable", "published_classes", "published_timetable"},
    "year": {"students", "classes", "timetable", "published_classes", "published_timetable"},
    "class": {"published_classes", "published_timetable"},
}
YEARS = {str(y) for y in range(7, 13)}


def valid_scope(scope, value):
    return isinstance(value, str) and ((scope == "school" and value == "") or
            (scope == "faculty" and isinstance(value, str) and bool(value.strip()) and value == value.strip()) or
            (scope == "year" and value in YEARS) or
            (scope == "class" and bool(value) and len(value) <= 30 and value == value.strip().upper()))


def valid_grant(grant):
    caps = grant.capabilities
    now = timezone.now()
    if (grant.starts_at and grant.starts_at > now) or (grant.expires_at and grant.expires_at <= now):
        return False
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
            if any(valid_grant(g) and code in g.capabilities for g in grants)}


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
            field = "faculty__iexact" if module == "staff" else ("school_class__teacher__staff_profile__faculty__iexact" if module == "timetable" else "teacher__staff_profile__faculty__iexact")
            condition |= Q(**{field: g.scope_value})
        if g.scope == "year":
            field = "school_class__year_level" if module == "timetable" else "year_level"
            condition |= Q(**{field: int(g.scope_value)})
    return qs.filter(condition)


def published_rows(publication, grants, module, day):
    """Read-only projection without roster IDs or raw staff identifiers."""
    from .connected_school import personal_codes, visible_slots
    applicable = [g for g in grants if valid_grant(g) and module in g.capabilities]
    whole = any(g.scope == "school" for g in applicable)
    years = {int(g.scope_value) for g in applicable if g.scope == "year"}
    class_codes = {g.scope_value for g in applicable if g.scope == "class"}
    faculties = {g.scope_value.casefold() for g in applicable if g.scope == "faculty"}
    codes = set()
    if faculties and not whole:
        bound_ids = {b["user"] for b in publication.snapshot.get("bindings", {}).values()
                     if isinstance(b, dict) and isinstance(b.get("user"), int)}
        profiles = StaffProfile.objects.filter(user_id__in=bound_ids, user__is_active=True).select_related("user")
        for profile in profiles:
            if profile.faculty.casefold() in faculties:
                codes.update(personal_codes(publication, profile.user))
    classes = {c["code"]: c for c in publication.snapshot.get("classes", [])}
    def year_allowed(code):
        values = classes.get(code, {}).get("years", [])
        return bool(values) and all(type(y) is int and y in years for y in values)
    def slot_allowed(slot):
        return whole or slot.get("staff") in codes or slot.get("code") in class_codes or year_allowed(slot.get("code"))
    if module == "published_classes":
        permitted_codes = {s["code"] for s in publication.snapshot.get("slots", []) if s.get("staff") in codes}
        return [{"code": c["code"], "name": c["name"], "years": c.get("years", [])}
                for c in classes.values() if whole or c["code"] in permitted_codes or c["code"] in class_codes or year_allowed(c["code"])]
    return [{"code": s["code"], "period_label": s.get("period_label", ""), "room": s.get("room", ""),
             "start": s.get("start", ""), "end": s.get("end", "")}
            for s in visible_slots(publication, day) if slot_allowed(s)]
