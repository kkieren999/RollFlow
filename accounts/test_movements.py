"""Synthetic V4.3 state machine and scope regression tests."""
from datetime import datetime,time,timedelta
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import Client,TestCase,override_settings
from django.utils import timezone
from django.db import IntegrityError,transaction
from . import test_live_foundation
from .models import StudentMovement,MovementDestination,MovementEvent,StaffAccessGrant,AttendanceRoll


@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True,SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False)
class MovementTests(TestCase):
    def setUp(self):
        test_live_foundation.LiveFoundationTests.setUp(self)
        self.now=timezone.make_aware(datetime.combine(self.day,time(9,15)))
        clock=patch("accounts.movement_views.movement_clock",return_value=self.now)
        clock.start()
        self.addCleanup(clock.stop)
        self.dest=MovementDestination.objects.create(name="Fictional service desk",expected_minutes=15,
            requires_reception=True,created_by=self.admin)
        self.other_dest=MovementDestination.objects.create(name="Other service desk",expected_minutes=10,
            requires_reception=True,created_by=self.admin)
        self.unstaffed=MovementDestination.objects.create(name="Fictional water break",created_by=self.admin)
        self.receiver=User.objects.create_user("fictional-receiver",password="Fictional-42-password!")
        self.wrong_receiver=User.objects.create_user("fictional-other-receiver",password="Fictional-42-password!")
        self.receiver_grant=StaffAccessGrant.objects.create(user=self.receiver,role="Student Services",scope="destination",
            scope_value=str(self.dest.pk),capabilities=["movement_receive"],granted_by=self.admin)
        StaffAccessGrant.objects.create(user=self.wrong_receiver,role="Student Services",scope="destination",
            scope_value=str(self.other_dest.pk),capabilities=["movement_receive"],granted_by=self.admin)
        StaffAccessGrant.objects.create(user=self.monitor,role="Custom",scope="school",scope_value="",
            capabilities=["movement_monitor"],granted_by=self.admin)
        self.issue_url="/live/movements/issue/?code=ENG7&period=P1&start=09:00"
        self.board="/live/movements/"

    def issue_data(self,**kw):
        return dict({"publication":str(self.pub.pk),"student":str(self.student.pk),"destination":str(self.dest.pk),"confirm":"yes"},**kw)

    def make_pass(self,**kw):
        self.client.force_login(self.teacher)
        r=self.client.post(self.issue_url,self.issue_data(**kw))
        self.assertEqual(r.status_code,302)
        return StudentMovement.objects.latest("pk")

    def act(self,user,m,action,revision,**kw):
        self.client.force_login(user)
        return self.client.post(f"/live/movements/{m.pk}/change/",{"action":action,"revision":str(revision),**kw})

    def test_staffed_lifecycle_scope_and_revisions(self):
        m=self.make_pass()
        self.assertEqual(m.state,"outbound")
        self.assertEqual(m.due_at,self.now+timedelta(minutes=15))
        path=f"/live/movements/{m.pk}/"
        self.assertEqual(self.act(self.teacher,m,"return",1).status_code,403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(path).status_code,404)
        self.client.force_login(self.wrong_receiver)
        self.assertEqual(self.client.get(path).status_code,404)
        self.assertNotContains(self.client.get(self.board),"FictionalPupil")
        self.assertEqual(self.act(self.wrong_receiver,m,"arrive",1).status_code,404)
        self.client.force_login(self.monitor)
        self.assertContains(self.client.get(self.board),"FictionalPupil")
        self.assertEqual(self.act(self.monitor,m,"arrive",1).status_code,403)
        self.assertEqual(self.act(self.receiver,m,"release",1).status_code,403)
        self.assertEqual(self.act(self.receiver,m,"arrive",1).status_code,302)
        self.assertEqual(self.act(self.receiver,m,"release",1).status_code,409)
        self.assertEqual(self.act(self.receiver,m,"release",2).status_code,302)
        self.assertEqual(self.act(self.receiver,m,"return",3).status_code,403)
        self.assertEqual(self.act(self.teacher,m,"return",3).status_code,302)
        m.refresh_from_db()
        self.assertEqual(m.state,"returned")
        self.assertIsNotNone(m.closed_at)
        self.assertEqual(list(m.events.order_by("revision").values_list("action",flat=True)),["issue","arrive","release","return"])
        self.assertEqual(self.act(self.teacher,m,"return",4).status_code,403)
        self.assertFalse(AttendanceRoll.objects.exists())

    def test_issue_rejects_forged_roster_wrong_time_and_duplicate(self):
        self.assertEqual(self.client.post(self.issue_url,self.issue_data(student=str(self.outside.pk))).status_code,403)
        self.assertEqual(self.client.post(self.issue_url,self.issue_data(publication="999")).status_code,400)
        with patch("accounts.movement_views.movement_clock",return_value=self.now+timedelta(hours=2)):
            self.assertEqual(self.client.post(self.issue_url,self.issue_data()).status_code,403)
        self.make_pass()
        self.assertEqual(self.client.post(self.issue_url,self.issue_data()).status_code,409)
        self.assertEqual(StudentMovement.objects.count(),1)
        self.assertEqual(MovementEvent.objects.count(),1)

    def test_unstaffed_and_admin_closure_are_distinct(self):
        m=self.make_pass(destination=str(self.unstaffed.pk))
        self.assertEqual(self.act(self.teacher,m,"return",1).status_code,302)
        m=self.make_pass()
        self.assertEqual(self.act(self.admin,m,"close",1,reason="free text").status_code,409)
        self.assertEqual(self.act(self.admin,m,"close",1,reason="unresolved_followup").status_code,302)
        m.refresh_from_db()
        self.assertEqual(m.state,"closed")
        self.assertNotEqual(m.state,"returned")
        self.assertEqual(m.events.get(revision=2).reason_code,"unresolved_followup")

    def test_revocation_identity_change_and_archive(self):
        m=self.make_pass()
        self.dest.active=False
        self.dest.save()
        self.assertEqual(self.act(self.receiver,m,"arrive",1).status_code,302)
        self.receiver_grant.delete()
        self.assertEqual(self.act(self.receiver,m,"release",2).status_code,403)
        self.student.student_id="DIFFERENT"
        self.student.save()
        self.client.force_login(self.teacher)
        self.assertNotContains(self.client.get(self.board),"FictionalPupil")
        self.assertContains(self.client.get(self.board),"Identity changed")
        self.assertEqual(self.act(self.admin,m,"release",2).status_code,403)
        self.assertEqual(self.act(self.admin,m,"close",2,reason="entered_in_error").status_code,302)

    def test_overdue_carryover_and_csrf(self):
        m=self.make_pass()
        StudentMovement.objects.filter(pk=m.pk).update(lesson_date=self.day-timedelta(days=1),
            departed_at=timezone.now()-timedelta(hours=2),due_at=timezone.now()-timedelta(hours=1))
        self.client.force_login(self.monitor)
        response=self.client.get(self.board)
        self.assertEqual(response.context["open_count"],1)
        self.assertEqual(response.context["overdue_count"],1)
        c=Client(enforce_csrf_checks=True)
        c.force_login(self.receiver)
        self.assertEqual(c.post(f"/live/movements/{m.pk}/change/",{"action":"arrive","revision":"1"}).status_code,403)
        self.assertEqual(self.client.get(self.board,{"student":self.outside.pk}).context["open_count"],0)

    def test_destination_grant_validation(self):
        self.client.force_login(self.admin)
        p={"action":"grant","user":self.receiver.pk,"role":"Student Services","scope":"school",
           "scope_value":"","capabilities":["movement_receive"]}
        n=StaffAccessGrant.objects.count()
        self.assertEqual(self.client.post("/manage/access/",p).status_code,200)
        self.assertEqual(StaffAccessGrant.objects.count(),n)
        p.update(scope="destination",scope_value=str(self.unstaffed.pk))
        self.assertEqual(self.client.post("/manage/access/",p).status_code,200)
        self.assertEqual(StaffAccessGrant.objects.count(),n)
        p["scope_value"]=str(self.other_dest.pk)
        self.assertEqual(self.client.post("/manage/access/",p).status_code,302)
        self.assertEqual(StaffAccessGrant.objects.count(),n+1)
