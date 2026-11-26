"""Teaching authority is separate from administrative account classification."""
from django.contrib.auth.models import User
from django.db.models import Q
from .models import StaffProfile

def can_teach(user):
    if not user.is_authenticated or not user.is_active:
        return False
    enabled = StaffProfile.objects.filter(user_id=user.pk).values_list("teaching_enabled", flat=True).first()
    if enabled is not None:
        return enabled
    # Preserve existing deployments without automatically granting teaching to superusers.
    return (not user.is_staff and not user.is_superuser
            and user.groups.filter(name="Teacher").exists())

def teaching_users():
    return User.objects.filter(is_active=True).filter(
        Q(staff_profile__teaching_enabled=True) |
        Q(staff_profile__teaching_enabled__isnull=True, is_staff=False,
          is_superuser=False, groups__name="Teacher")
    ).distinct()
