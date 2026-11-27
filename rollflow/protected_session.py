"""Apply account eligibility and cache policy consistently to protected routes."""
from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpResponseForbidden
from django.utils.cache import add_never_cache_headers


class ProtectedSessionMiddleware:
    def __init__(self,get_response):
        self.get_response=get_response

    def __call__(self,request):
        protected=settings.ROLLFLOW_PROTECTED_WORKSPACE
        if protected and request.user.is_authenticated:
            from accounts.security_service import eligible_account
            if not eligible_account(request.user):
                logout(request)
                response=HttpResponseForbidden("Account access is unavailable. Contact your authorised administrator.")
                add_never_cache_headers(response)
                return response
        authenticated=protected and request.user.is_authenticated
        response=self.get_response(request)
        # Includes legacy protected views and successful sign-in/out redirects.
        if protected and (authenticated or request.user.is_authenticated):
            add_never_cache_headers(response)
        return response
