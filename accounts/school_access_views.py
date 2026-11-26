from django import forms
from django.utils import timezone
from .security_service import audit, grant_state, lock_administrator
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods
from .models import StaffAccessGrant, SecurityEvent, StaffProfile, PendingTeacherSetup, RoleTemplate
from .staff_views import administrator
from .permissions import can_teach
from .school_access import ROLES, CAPABILITIES, SCOPES, valid_scope, grants_for, visible_modules, scoped_rows, published_rows


class GrantForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.none())
    role = forms.ChoiceField(choices=[(r, r) for r in ROLES])
    custom_role = forms.CharField(max_length=80, required=False)
    template = forms.ModelChoiceField(queryset=RoleTemplate.objects.none(), required=False, help_text="Optional reviewed bundle. Its scope and capabilities are copied at assignment; choose matching scope. Role label is copied.")
    starts_at = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={"type":"datetime-local"}), help_text="School local time; blank means immediately.")
    expires_at = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={"type":"datetime-local"}), help_text="School local time; blank means no scheduled expiry.")
    scope = forms.ChoiceField(choices=[("faculty", "Staff faculty"), ("year", "Year level"), ("school", "Whole school"), ("class", "Published class (read only)")])
    scope_value = forms.CharField(max_length=100, required=False, help_text="Exact existing faculty name, or year 7–12. Leave blank for whole school.")
    capabilities = forms.MultipleChoiceField(choices=list(CAPABILITIES.items()), widget=forms.CheckboxSelectMultiple, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["template"].queryset = RoleTemplate.objects.filter(active=True).order_by("name")
        self.fields["template"].label_from_instance = lambda t: f"{t.name} · {t.scope}"
        self.fields["user"].queryset = User.objects.exclude(
            pending_teacher_setup__activated_at__isnull=True,
            pending_teacher_setup__isnull=False).filter(is_active=True).order_by("username")

    def clean(self):
        c = super().clean()
        scope, value = c.get("scope"), c.get("scope_value", "")
        caps = c.get("capabilities", [])
        role = c.get("role")
        template = c.get("template")
        if template:
            if scope != template.scope or (caps and set(caps) != set(template.capabilities)):
                self.add_error("template", "Use the exact template scope and capability bundle, or leave capabilities blank to copy them.")
            caps = c["capabilities"] = template.capabilities
        if not caps:
            self.add_error("capabilities", "Select at least one permitted module or a template.")
        start, end = c.get("starts_at"), c.get("expires_at")
        if end and (end <= timezone.now() or (start and end <= start)):
            self.add_error("expires_at", "Expiry must be in the future and after the start.")
        if scope == "class":
            from .connected_school import current
            pub = current()
            if not pub or not any(row.get("code") == value for row in pub.snapshot.get("classes", [])):
                self.add_error("scope_value", "Choose an exact class code from the active publication.")
        if not valid_scope(scope, value):
            self.add_error("scope_value", "Enter a valid scope.")
        elif scope == "faculty" and not StaffProfile.objects.filter(faculty__iexact=value).exists():
            self.add_error("scope_value", "Choose an existing faculty exactly.")
        if scope in SCOPES and not set(caps).issubset(SCOPES[scope]):
            self.add_error("capabilities", "These modules cannot be safely scoped to the selected area.")
        if not template and role == "Head of Department" and scope != "faculty":
            self.add_error("scope", "HOD grants must be faculty scoped.")
        if not template and role == "Head of Year" and scope != "year":
            self.add_error("scope", "Head of Year grants must be year scoped.")
        if not template and role == "Custom" and not c.get("custom_role"):
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
                if not lock_administrator(request.user):
                    return HttpResponseForbidden("Administrator access revoked.")
                grant = get_object_or_404(StaffAccessGrant.objects.select_for_update(), pk=request.POST.get("grant_id"))
                SecurityEvent.objects.create(actor=request.user, event="school_access_revoked", subject=f"{grant.pk} {grant.user.username} {grant.role} {grant.scope} {grant.scope_value}"[:150])
                audit(request.user, "grant_revoked", grant.user, before=grant_state(grant))
                grant.delete()
            messages.success(request, "Access revoked immediately.")
            return redirect("school-access-manage")
        if action == "grant" and form.is_valid():
            c = form.cleaned_data
            with transaction.atomic():
                if not lock_administrator(request.user):
                    return HttpResponseForbidden("Administrator access revoked.")
                template = c.get("template")
                if template:
                    current_template = RoleTemplate.objects.select_for_update().filter(pk=template.pk, active=True).first()
                    if not current_template or current_template.scope != c["scope"] or current_template.capabilities != c["capabilities"]:
                        return HttpResponseForbidden("Template changed. Reload and review.")
                user = User.objects.select_for_update().get(pk=c["user"].pk)
                if not user.is_active or PendingTeacherSetup.objects.filter(user=user, activated_at__isnull=True).exists():
                    return HttpResponseForbidden("Account not eligible.")
                grant = StaffAccessGrant.objects.create(user=user, role=template.name if template else (c["custom_role"] if c["role"] == "Custom" else c["role"]),
                    template=template, starts_at=c.get("starts_at"), expires_at=c.get("expires_at"),
                    scope=c["scope"], scope_value=c["scope_value"], capabilities=c["capabilities"], granted_by=request.user)
                audit(request.user, "grant_created", user, after=grant_state(grant))
                SecurityEvent.objects.create(actor=request.user, event="school_access_granted", subject=str(grant.pk))
            messages.success(request, "Access granted. Existing teaching rights are unchanged.")
            return redirect("school-access-manage")
        if action != "grant":
            return HttpResponseForbidden("Unknown access action.")
    grants = StaffAccessGrant.objects.select_related("user", "granted_by", "template").order_by("user__username", "pk")
    return render(request, "school_access_manage.html", {"form": form, "grants": Paginator(grants, 50).get_page(request.GET.get("page"))})


@never_cache
@require_GET
def workspace(request, module=None):
    if not request.user.is_authenticated:
        return redirect("teacher-login")
    grants = grants_for(request.user)
    modules = visible_modules(grants)
    if module == "attendance_monitor" and module in modules:
        return redirect("live-monitor")
    if not modules or (module is not None and module not in modules):
        return HttpResponseForbidden("Assigned staff access required.")
    publication = day = None
    if module in ("published_classes", "published_timetable"):
        from .connected_school import current, selected_day
        publication = current()
        day = selected_day(publication, request.GET.get("date")) if publication else None
        data = published_rows(publication, grants, module, day) if publication else []
    else:
        data = scoped_rows(grants, module) if module else []
    rows = Paginator(data, 50).get_page(request.GET.get("page")) if module else None
    return render(request, "school_workspace.html", {
        "grants": grants, "modules": modules, "module": module, "rows": rows,
        "publication": publication, "day": day,
        "teaching": can_teach(request.user),
        "admin_access": request.user.is_staff and request.user.is_superuser,
    })
