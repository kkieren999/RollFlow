from django.test import TestCase,Client,override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from . import test_live_foundation
from .models import StaffAccessGrant

@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True,SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False)
class ProtectedWorkspaceUITests(TestCase):
    def setUp(self):
        test_live_foundation.LiveFoundationTests.setUp(self)

    def test_teacher_shell_and_no_admin_navigation(self):
        for route in ("/live/","/live/day/","/teacher/week/",self.url):
            r=self.client.get(route)
            self.assertContains(r,'data-rf-shell="protected"',count=1)
            self.assertContains(r,"Daily Schedule")
            self.assertNotContains(r,'data-rf-group="Account Management"')
            self.assertNotContains(r,"OtherPupil")
        self.assertEqual(self.client.get("/manage/access/").status_code,403)

    def test_grants_drive_menu_not_role_label(self):
        user=User.objects.create_user("fake-leader",password="Fictional-password-42!")
        self.client.force_login(user)
        g=StaffAccessGrant.objects.create(user=user,role="Principal",scope="year",scope_value="7",
            capabilities=["students"],granted_by=self.admin)
        r=self.client.get("/live/")
        self.assertContains(r,'data-rf-group="Student Search"')
        self.assertNotContains(r,'data-rf-group="Account Management"')
        self.assertNotContains(r,'data-rf-group="Attendance Overview"')
        self.assertEqual(self.client.get("/workspace/staff/").status_code,403)
        g.expires_at=timezone.now()-timedelta(seconds=1)
        g.save(update_fields=["expires_at"])
        self.assertEqual(self.client.get("/live/").status_code,403)

    def test_theme_post_and_safe_redirect(self):
        self.assertEqual(self.client.get("/account/theme/").status_code,405)
        self.assertRedirects(self.client.post("/account/theme/",{"theme":"dark","next":"/live/day/"}),"/live/day/")
        self.assertContains(self.client.get("/live/day/"),'data-theme="dark"')
        self.assertEqual(self.client.post("/account/theme/",{"theme":"bad"}).status_code,400)
        self.assertRedirects(self.client.post("/account/theme/",{"theme":"light","next":"//example.invalid"}),"/live/")
        csrf=Client(enforce_csrf_checks=True)
        csrf.force_login(self.teacher)
        self.assertEqual(csrf.post("/account/theme/",{"theme":"dark"}).status_code,403)

    def test_admin_and_scope_form_use_shell(self):
        self.client.force_login(self.admin)
        for route in ("/manage/","/manage/access/","/manage/security/templates/","/manage/oneschool/documents/"):
            r=self.client.get(route)
            self.assertContains(r,'data-rf-shell="protected"',count=1)
            self.assertContains(r,'data-rf-group="Account Management"')
        r=self.client.get("/manage/access/")
        self.assertContains(r,'id="rf-scope-capabilities"')
        payload={"action":"grant","user":self.teacher.pk,"role":"Principal","scope":"faculty","scope_value":"",
                 "capabilities":["attendance_monitor"]}
        r=self.client.post("/manage/access/",payload)
        self.assertContains(r,"Enter a valid scope")
        self.assertContains(r,"These modules cannot be safely scoped")
        self.assertFalse(StaffAccessGrant.objects.filter(user=self.teacher).exists())

    def test_missing_coverage_is_explicit_not_a_server_error(self):
        from .oneschool_views import coverage_message
        self.assertIn("coverage is unavailable",coverage_message(self.version,self.day))
        self.client.force_login(self.admin)
        r=self.client.get("/manage/")
        self.assertContains(r,"Published classes")
        self.assertContains(r,'data-rf-shell="protected"')

    def test_rc27_shell_snapshot_is_render_local(self):
        from unittest.mock import patch
        from . import live_views, workspace_ui
        with patch.object(live_views,"shell",wraps=live_views.shell) as primary, patch.object(workspace_ui,"shell",wraps=workspace_ui.shell) as fallback:
            self.assertContains(self.client.get("/live/"),'data-rf-shell="protected"')
            self.assertEqual(primary.call_count,1)
            self.assertEqual(fallback.call_count,0)
            self.assertContains(self.client.get("/live/day/"),'data-rf-shell="protected"')
            self.assertEqual(primary.call_count,2)
            self.assertEqual(fallback.call_count,0)
            self.client.force_login(self.admin)
            self.assertContains(self.client.get("/manage/"),'data-rf-group="Account Management"')
            self.assertEqual(fallback.call_count,1)
            self.client.force_login(self.teacher)
            self.assertNotContains(self.client.get("/live/"),'data-rf-group="Account Management"')
            self.assertEqual(primary.call_count,3)

    def test_accessible_main_and_attendance_totals(self):
        self.assertContains(self.client.get("/live/day/"),'id="main-content" tabindex="-1"')
        self.assertContains(self.client.get("/live/day/"),'aria-label="Account menu for')
        res=self.client.get(self.url)
        self.assertContains(res,'aria-label="Attendance totals" aria-live="polite" aria-atomic="true"')
        self.assertContains(res,'<th scope="col">Student</th>',html=True)
