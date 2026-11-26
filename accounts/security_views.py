from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_GET
from .models import RoleTemplate, AccessAudit, SecurityEvent
from .school_access import CAPABILITIES, SCOPES, grants_for
from .security_service import audit, eligible_account, grant_state, lock_administrator, account_state
from .staff_views import administrator, revoke_sessions
from .permissions import can_teach


class TemplateForm(forms.Form):
    name = forms.CharField(max_length=80)
    scope = forms.ChoiceField(choices=[(s,s.title()) for s in SCOPES])
    capabilities = forms.MultipleChoiceField(choices=list(CAPABILITIES.items()), widget=forms.CheckboxSelectMultiple)

    def clean(self):
        c = super().clean()
        if c.get("scope") in SCOPES and not set(c.get("capabilities", [])).issubset(SCOPES[c["scope"]]):
            self.add_error("capabilities", "The selected modules do not support that scope.")
        if c.get("name") and RoleTemplate.objects.filter(name__iexact=c["name"]).exists():
            self.add_error("name", "Choose a new template name; archive old versions instead of editing them.")
        return c


@administrator
@require_http_methods(["GET","POST"])
def templates(request):
    form = TemplateForm(request.POST if request.method=="POST" and request.POST.get("action")=="create" else None)
    if request.method == "POST":
        with transaction.atomic():
            if not lock_administrator(request.user):
                return HttpResponseForbidden("Administrator access revoked.")
            action = request.POST.get("action")
            if action == "archive":
                template = get_object_or_404(RoleTemplate.objects.select_for_update(), pk=request.POST.get("template"))
                if template.active:
                    template.active=False
                    template.save(update_fields=["active"])
                    audit(request.user,"template_archived",before={"template":template.pk,"active":True},
                          after={"template":template.pk,"active":False})
                return redirect("security-templates")
            if action != "create":
                return HttpResponseBadRequest("Unknown action.")
            if form.is_valid():
                c=form.cleaned_data
                try:
                    with transaction.atomic():
                        template=RoleTemplate.objects.create(**c,created_by=request.user)
                except IntegrityError:
                    form.add_error("name","Template name already exists.")
                else:
                    audit(request.user,"template_created",after={"template":template.pk,"name":template.name,
                          "scope":template.scope,"capabilities":template.capabilities})
                    return redirect("security-templates")
    return render(request,"security_templates.html",{"form":form,"templates":Paginator(RoleTemplate.objects.order_by("name"),50).get_page(request.GET.get("page"))})


@administrator
@require_GET
def effective(request, pk):
    user=get_object_or_404(User,pk=pk)
    return render(request,"security_effective.html",{"target":user,"state":account_state(user),
        "teaching":can_teach(user),"grants":[grant_state(g) for g in grants_for(user)]})


@administrator
@require_GET
def history(request):
    qs=AccessAudit.objects.select_related("actor","target").order_by("-created_at","-pk")
    return render(request,"security_history.html",{"events":Paginator(qs,50).get_page(request.GET.get("page"))})


@never_cache
@require_http_methods(["GET","POST"])
def password(request):
    if not request.user.is_authenticated:
        return redirect("teacher-login")
    if not eligible_account(request.user):
        return HttpResponseForbidden("Account not authorised.")
    form=PasswordChangeForm(request.user, request.POST if request.method=="POST" else None)
    if request.method=="POST" and form.is_valid():
        with transaction.atomic():
            target=User.objects.select_for_update().get(pk=request.user.pk)
            if not eligible_account(target) or target.password != request.user.password:
                return HttpResponseForbidden("Account changed. Sign in again.")
            target.set_password(form.cleaned_data["new_password1"])
            target.save(update_fields=["password"])
            revoke_sessions(target)
            audit(target,"self_password_changed",target)
            SecurityEvent.objects.create(actor=target,event="password_changed")
            update_session_auth_hash(request,target)
        return redirect("teacher-login")
    return render(request,"security_password.html",{"form":form})
