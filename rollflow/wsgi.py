import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rollflow.settings")
from django.conf import settings
from .release_policy import assert_school_release
if settings.ROLLFLOW_SCHOOL_MODE or settings.ROLLFLOW_LIVE_TIMETABLE:
    assert_school_release()
application = get_wsgi_application()
