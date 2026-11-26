"""Authorised read-only access to the published OneSchool timetable.

Never accept staff identity from a URL, browser storage or CSV staff-code alias.
Only the current Django account's administrator-maintained StaffProfile may
grant a personal timetable. Live school mode additionally requires a fresh
administrator verification; old migrated links are deliberately unverified.
"""
from django.conf import settings
from .models import StaffProfile
from .permissions import can_teach


def staff_identity(user):
    """Return (normalised OneSchool ID or None, user-friendly reason)."""
    if not can_teach(user):
        return None, "An active teacher account is required."
    profile = StaffProfile.objects.filter(user_id=user.pk).first()
    if not profile or not profile.staff_id or not profile.staff_id.strip():
        return None, "Your account has no linked OneSchool staff ID. Contact your administrator."
    key = profile.staff_id.strip().upper()
    if settings.ROLLFLOW_LIVE_TIMETABLE and not profile.timetable_link_verified:
        return None, "Your OneSchool staff ID has not been verified by an administrator."
    # The model has a case-sensitive unique index. Fail closed if legacy data
    # contains conflicting IDs that differ only by case.
    if StaffProfile.objects.filter(staff_id__iexact=key).count() != 1:
        return None, "Staff ID mapping is ambiguous. Contact your administrator."
    return key, ""


def assigned_rows(allocations, staff_id):
    """Scope published allocations to one canonical staff ID, never staff code."""
    if not staff_id:
        return []
    return [row for row in allocations if isinstance(row, dict)
            and isinstance(row.get("staff_id"), str)
            and row["staff_id"].strip().upper() == staff_id]
