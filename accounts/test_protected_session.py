from django.contrib.auth.models import User
from django.test import TestCase,override_settings
from . import test_live_foundation
from .models import PendingTeacherSetup

@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True,SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False)
class ProtectedSessionTests(TestCase):
    def setUp(self):
        test_live_foundation.LiveFoundationTests.setUp(self)

    def test_protected_pages_are_not_cacheable(self):
        for url in ("/live/","/live/day/",self.url,"/teacher/week/"):
            response=self.client.get(url)
            self.assertEqual(response.status_code,200)
            self.assertIn("no-store",response["Cache-Control"])
            self.assertIn("private",response["Cache-Control"])

    def test_pending_session_is_denied_and_flushed(self):
        from unittest.mock import patch
        # Test the middleware's shared eligibility decision, independent of
        # the particular account setup workflow or its fixture requirements.
        with patch("accounts.security_service.eligible_account",return_value=False):
            response=self.client.get("/teacher/week/")
        self.assertEqual(response.status_code,403)
        self.assertIn("no-store",response["Cache-Control"])
        self.assertNotIn("_auth_user_id",self.client.session)

    def test_deactivated_user_cannot_use_old_session(self):
        self.teacher.is_active=False
        self.teacher.save(update_fields=["is_active"])
        response=self.client.get("/live/")
        self.assertIn(response.status_code,(302,403))
        self.assertNotContains(response,"FictionalPupil",status_code=response.status_code)
