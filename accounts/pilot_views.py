"""Read-only administrator rehearsal guidance; no approval or mutation endpoint."""
from django.conf import settings
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET
from rollflow.pilot_plan import plan
from .staff_views import administrator


@administrator
@require_GET
def readiness(request):
    if not settings.ROLLFLOW_PROTECTED_WORKSPACE:
        raise Http404
    return render(request,"pilot_readiness.html",{"pilot":plan()})
