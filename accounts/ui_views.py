from django.conf import settings
from django.http import HttpResponseBadRequest,HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from .security_service import eligible_account

@never_cache
@require_POST
def theme(request):
    if not settings.ROLLFLOW_PROTECTED_WORKSPACE or not eligible_account(request.user):
        return HttpResponseForbidden("Staff access required.")
    value=request.POST.get("theme")
    if value not in ("light","dark"):
        return HttpResponseBadRequest("Choose light or dark.")
    request.session["rf_theme"]=value
    target=request.POST.get("next","")
    if not target.startswith("/") or target.startswith("//") or not url_has_allowed_host_and_scheme(target,allowed_hosts=set(),require_https=request.is_secure()):
        return redirect("live-home")
    return redirect(target)
