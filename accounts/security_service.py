"""Shared lifecycle guards and append-only permission audit helpers."""
from django.contrib.auth.models import User
from .models import AccessAudit, PendingTeacherSetup, StaffAccessGrant


def eligible_account(user):
    return bool(user.is_authenticated and user.is_active and not
                PendingTeacherSetup.objects.filter(user_id=user.pk, activated_at__isnull=True).exists())


def lock_administrator(actor):
    """Call within atomic before changing account/permission state.
    Deterministic lock order prevents two admins concurrently disabling each other."""
    admins = list(User.objects.select_for_update().filter(is_staff=True, is_superuser=True).order_by("pk"))
    return any(u.pk == actor.pk and eligible_account(u) for u in admins)


def audit(actor, action, target=None, before=None, after=None):
    return AccessAudit.objects.create(actor=actor, target=target, action=action,
                                      before=before or {}, after=after or {})


def grant_state(g):
    return {"grant":g.pk,"role":g.role,"scope":g.scope,"scope_value":g.scope_value,
            "capabilities":list(g.capabilities),"template":g.template_id,
            "starts_at":g.starts_at.isoformat() if g.starts_at else None,
            "expires_at":g.expires_at.isoformat() if g.expires_at else None}


def account_state(user):
    from .models import StaffProfile
    profile = StaffProfile.objects.filter(user=user).first()
    return {"active":user.is_active,"administrator":bool(user.is_staff and user.is_superuser),
            "teaching":profile.teaching_enabled if profile else None,
            "legacy_teacher":user.groups.filter(name="Teacher").exists(),
            "identity_verified":bool(profile and profile.timetable_link_verified)}


def revoke_account_grants(actor, target):
    for grant in StaffAccessGrant.objects.select_for_update().filter(user=target).order_by("pk"):
        audit(actor, "grant_revoked_on_deactivation", target, before=grant_state(grant))
        grant.delete()
