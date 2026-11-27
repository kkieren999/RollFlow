from django.conf import settings
from django.http import HttpResponseForbidden,HttpResponseBadRequest
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from .live_views import page
from .leadership_experience import dashboard

@never_cache
@require_GET
def overview(request):
    if not request.user.is_authenticated:return redirect("teacher-login")
    if not settings.ROLLFLOW_PROTECTED_WORKSPACE:
        return HttpResponseForbidden("Protected workspace required.")
    try:summary=dashboard(request.user,request.GET)
    except (ValueError,TypeError,OverflowError) as exc:return HttpResponseBadRequest(str(exc))
    if summary is None:return HttpResponseForbidden("Explicit report permission for this exact scope required.")
    return page(request,"leadership_overview.html",leadership=summary)
