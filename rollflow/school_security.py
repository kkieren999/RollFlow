"""Prevent unexpected external resource loads in the school application."""
from django.conf import settings

POLICY = (
    "default-src 'self'; script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
    "font-src 'self' data:; connect-src 'self'; object-src 'none'; "
    "base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
)

class LocalOnlyResourcesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if settings.ROLLFLOW_SCHOOL_MODE:
            response["Content-Security-Policy"] = POLICY
            response["Referrer-Policy"] = "no-referrer"
        return response
