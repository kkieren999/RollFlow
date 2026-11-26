from django import forms
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods
from .models import StaffAccessGrant, SecurityEvent, StaffProfile, PendingTeacherSetup
from .staff_views import administrator
from .permissions import can_teach
from .school_access import ROLES, CAPABILITIES, SCOPES, valid_scope, grants_for, visible_modules, scoped_rows


class GrantForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.none())
    role = forms.ChoiceField(choices=[(r, r) for r in ROLES])
    custom_role = forms.CharField(max_length=80, required=False)
    scope = forms.ChoiceField(choices=[("faculty", "Staff faculty"), ("year", "Year level"), ("school", "Whole school")])
    scope_value = forms.CharField(max_length=100, required=False, help_text="Exact existing faculty name, or year 7–12. Leave blank for whole school.")
    capabilities = forms.MultipleChoiceField(choices=list(CAPABILITIES.items()), widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.exclude(
            pending_teacher_setup__activated_at__isnull=True,
            pending_teacher_setup__isnull=False).filter(is_active=True).order_by("username")

    def clean(self):
        c = super().clean()
        scope, value = c.get("scope"), c.get("scope_value", "")
        caps = c.get("capabilities", [])
        role = c.get("role")
        if not valid_scope(scope, value):
            self.add_error("scope_value", "Enter a valid scope.")
        elif scope == "faculty" and not StaffProfile.objects.filter(faculty__iexact=value).exists():
            self.add_error("scope_value", "Choose an existing faculty exactly.")
        if scope in SCOPES and not set(caps).issubset(SCOPES[scope]):
            self.add_error("capabilities", "These modules cannot be safely scoped to the selected area.")
        if role == "Head of Department" and scope != "faculty":
            self.add_error("scope", "HOD grants must be faculty scoped.")
        if role == "Head of Year" and scope != "year":
            self.add_error("scope", "Head of Year grants must be year scoped.")
        if role == "Custom" and not c.get("custom_role"):
            self.add_error("custom_role", "Enter a custom role label.")
        return c


@administrator
@require_http_methods(["GET", "POST"])
def manage_access(request):
    form = GrantForm(request.POST if request.method == "POST" and request.POST.get("action") == "grant" else None)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "revoke":
            with transaction.atomic():
                grant = get_object_or_404(StaffAccessGrant.objects.select_for_update(), pk=request.POST.get("grant_id"))
                SecurityEvent.objects.create(actor=request.user, event="school_access_revoked", subject=str(grant.pk))
                grant.delete()
            messages.success(request, "Access revoked immediately.")
            return redirect("school-access-manage")
        if action == "grant" and form.is_valid():
            c = form.cleaned_data
            with transaction.atomic():
                user = User.objects.select_for_update().get(pk=c["user"].pk)
                if not user.is_active or PendingTeacherSetup.objects.filter(user=user, activated_at__isnull=True).exists():
                    return HttpResponseForbidden("Account not eligible.")
                grant = StaffAccessGrant.objects.create(user=user, role=c["custom_role"] if c["role"] == "Custom" else c["role"],
                    scope=c["scope"], scope_value=c["scope_value"], capabilities=c["capabilities"], granted_by=request.user)
                SecurityEvent.objects.create(actor=request.user, event="school_access_granted", subject=str(grant.pk))
            messages.success(request, "Access granted. Existing teaching rights are unchanged.")
            return redirect("school-access-manage")
        if action != "grant":
            return HttpResponseForbidden("Unknown access action.")
    grants = StaffAccessGrant.objects.select_related("user", "granted_by").order_by("user__username", "pk")
    return render(request, "school_access_manage.html", {"form": form, "grants": Paginator(grants, 50).get_page(request.GET.get("page"))})


@never_cache
@require_GET
def workspace(request, module=None):
    if not request.user.is_authenticated:
        return redirect("teacher-login")
    grants = grants_for(request.user)
    modules = visible_modules(grants)
    if not modules or (module is not None and module not in modules):
        return HttpResponseForbidden("Assigned staff access required.")
    rows = Paginator(scoped_rows(grants, module), 50).get_page(request.GET.get("page")) if module else None
    return render(request, "school_workspace.html", {
        "grants": grants, "modules": modules, "module": module, "rows": rows,
        "teaching": can_teach(request.user),
        "admin_access": request.user.is_staff and request.user.is_superuser,
    })
