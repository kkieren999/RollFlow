from django.conf import settings
from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group
from .models import StaffProfile, SecurityEvent

class RollFlowAdmin(AdminSite):
    site_header = "RollFlow · Administration"
    site_title = "RollFlow Admin"
    index_title = "School management foundation"
    login_template = "login.html"
    def has_permission(self, request):
        from .security_service import eligible_account
        return bool(eligible_account(request.user) and request.user.is_staff and request.user.is_superuser)
    def login(self, request, extra_context=None):
        # No alternative login path that bypasses portal rate limiting.
        from django.shortcuts import redirect
        return redirect("admin-login")
    def logout(self, request, extra_context=None):
        from .views import sign_out
        return sign_out(request)

class ProtectedReadOnly:
    """Protected deployments must use audited application account forms, not raw ORM admin writes."""
    def has_add_permission(self, request):
        return not settings.ROLLFLOW_PROTECTED_WORKSPACE and super().has_add_permission(request)
    def has_change_permission(self, request, obj=None):
        return not settings.ROLLFLOW_PROTECTED_WORKSPACE and super().has_change_permission(request, obj)
    def has_delete_permission(self, request, obj=None):
        return not settings.ROLLFLOW_PROTECTED_WORKSPACE and super().has_delete_permission(request, obj)

class StaffAdmin(ProtectedReadOnly, UserAdmin):
    # Preserve account identifiers and historical attribution.
    def has_delete_permission(self, request, obj=None):
        return False

class ProfileAdmin(ProtectedReadOnly, ModelAdmin):
    list_display = ("user", "staff_id", "faculty", "campus")
    search_fields = ("user__username", "staff_id", "faculty")
    def has_delete_permission(self, request, obj=None):
        return False

class SecurityEventAdmin(ModelAdmin):
    list_display = ("created_at", "event", "actor", "subject")
    readonly_fields = ("created_at", "event", "actor", "subject")
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

admin_site = RollFlowAdmin(name="rollflow_admin")
admin_site.register(User, StaffAdmin)
class GroupAdmin(ProtectedReadOnly, ModelAdmin):
    pass

admin_site.register(Group, GroupAdmin)
admin_site.register(StaffProfile, ProfileAdmin)
admin_site.register(SecurityEvent, SecurityEventAdmin)
