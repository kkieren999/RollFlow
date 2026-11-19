from django.conf import settings
from django.db import models

class StaffProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="staff_profile")
    staff_id = models.CharField(max_length=40, blank=True, unique=True, null=True)
    faculty = models.CharField(max_length=100, blank=True)
    campus = models.CharField(max_length=100, blank=True)
    def __str__(self):
        return self.user.get_username()

class SecurityEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    event = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)
    subject = models.CharField(max_length=150, blank=True)
    class Meta:
        ordering = ["-created_at"]

class LoginWindow(models.Model):
    # HMAC-derived key; do not log passwords or retain the raw IP.
    key = models.CharField(max_length=64, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField()
