from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from . import test_movements, test_live_foundation
from .models import AttendanceRoll, StudentMovement, AttendanceRevision


@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True, SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class WorkflowIntegrationTests(TestCase):
    def setUp(self):
        test_movements.MovementTests.setUp(self)

    def profile_url(self):
        return reverse("teacher-student-detail", kwargs={"pk": self.student.pk})

    def test_profile_links_only_current_own_verified_roll(self):
        res = self.client.get(self.profile_url())
        self.assertContains(res, "Today's verified lessons")
        self.assertContains(res, "Not recorded")
        self.assertNotContains(res, "SCI8")
        self.assertNotContains(res, "OtherPupil")
        payload = test_live_foundation.LiveFoundationTests.payload
        self.assertEqual(self.client.post(self.url, payload(self,"draft",mark="A")).status_code,302)
        res = self.client.get(self.profile_url())
        self.assertContains(res, "Draft — not certified")
        self.assertNotContains(res, ">Absent<")
        self.assertEqual(self.client.post(self.url,payload(self,"submit",1,"L")).status_code,302)
        self.assertContains(self.client.get(self.profile_url()), "<strong>Late</strong>", html=True)
        roll=AttendanceRoll.objects.get()
        AttendanceRevision.objects.filter(roll=roll,revision=roll.revision).update(marks={})
        self.assertContains(self.client.get(self.profile_url()), "Review required")
        self.assertNotContains(self.client.get(self.profile_url()), ">Late<")

    def test_movement_visibility_and_no_attendance_side_effect(self):
        res=self.client.post(self.issue_url,{"publication":str(self.pub.pk),"student":str(self.student.pk),"destination":str(self.dest.pk),"confirm":"yes"})
        self.assertEqual(res.status_code,302)
        movement=StudentMovement.objects.get()
        res=self.client.get(self.profile_url())
        self.assertContains(res,movement.destination_name)
        self.assertContains(res,reverse("movement-detail",kwargs={"pk":movement.pk}))
        self.assertFalse(AttendanceRoll.objects.exists())
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.profile_url()).status_code,404)
        self.client.force_login(self.monitor)
        self.assertEqual(self.client.get(self.profile_url()).status_code,403)
        self.client.force_login(self.teacher)
        self.student.student_id="CHANGED"
        self.student.save(update_fields=["student_id"])
        self.assertEqual(self.client.get(self.profile_url()).status_code,404)

    def test_movement_scripts_outside_title_and_lesson_navigation(self):
        for path in (self.issue_url,self.board):
            res=self.client.get(path)
            html=res.content.decode()
            self.assertEqual(res.status_code,200)
            self.assertIn("movement-experience.js",html)
            self.assertNotIn("<script",html.split("<title>",1)[1].split("</title>",1)[0])
        self.assertContains(self.client.get(self.issue_url),'aria-label="Current lesson workflows"')
        self.assertContains(self.client.get(self.url),'aria-label="Current lesson workflows"')

    def test_only_current_lesson_shows_movement_action(self):
        from .workflow_integration import lesson_links
        row=self.pub.snapshot["slots"][0]
        self.assertTrue(lesson_links(row,self.now)["movement"])
        self.assertFalse(lesson_links(row,self.now+timedelta(hours=2))["movement"])
