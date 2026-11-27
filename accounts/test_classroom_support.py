"""Fictional classroom and need-to-know support regression coverage."""
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import TestCase,Client,override_settings
from django.utils import timezone
from . import test_live_foundation
from .models import ClassroomPlan,ClassroomObservation,SupportTask,SupportReferral,StaffAccessGrant,ReliefAttendanceAssignment
from .live_views import roster_token

@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True,SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False)
class ClassroomSupportTests(TestCase):
    def setUp(self):
        test_live_foundation.LiveFoundationTests.setUp(self)
        self.tools="/live/classroom/?code=ENG7&period=P1&start=09:00"
        self.board="/live/support/"
        self.aide=User.objects.create_user("fictional-aide",password="Fictional-password-42!")
        self.reviewer=User.objects.create_user("fictional-reviewer",password="Fictional-password-42!")
        self.coord=User.objects.create_user("fictional-coordinator",password="Fictional-password-42!")
        self.unassigned=User.objects.create_user("fictional-unassigned",password="Fictional-password-42!")
        for user,cap in [(self.aide,"support_task"),(self.reviewer,"support_referral"),
                         (self.coord,"support_coordinator"),(self.unassigned,"support_task")]:
            StaffAccessGrant.objects.create(user=user,role="Custom",scope="school",scope_value="",capabilities=[cap],granted_by=self.admin)

    def post(self,action,**kw):
        data={"action":action,"publication":str(self.pub.pk),"roster_token":roster_token([self.student])}
        data.update(kw)
        return self.client.post(self.tools,data)

    def change(self,user,kind,record,action,rev,**kw):
        self.client.force_login(user)
        return self.client.post(f"/live/support/{kind}/{record.pk}/change/",{"action":action,"revision":str(rev),**kw})

    def test_seating_authority_revision_and_forged_student(self):
        self.assertContains(self.client.get(self.tools),"FictionalPupil")
        self.assertNotContains(self.client.get(self.tools),"OtherPupil")
        field="seat_"+str(self.student.pk)
        self.assertEqual(self.post("seating",revision="0",**{field:"1"}).status_code,302)
        self.assertEqual(ClassroomPlan.objects.get().seats,{str(self.student.pk):1})
        self.assertEqual(self.post("seating",revision="0",**{field:"2"}).status_code,409)
        self.assertEqual(self.post("seating",revision="1",**{field:"2","seat_"+str(self.outside.pk):"3"}).status_code,400)
        self.assertContains(self.client.get(self.tools),"Seat 1")
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.tools).status_code,403)

    def test_observation_is_private_and_withdrawable(self):
        self.assertEqual(self.post("observe",student=self.outside.pk,category="engaged").status_code,403)
        self.assertEqual(self.post("observe",student=self.student.pk,category="free text").status_code,400)
        self.assertEqual(self.post("observe",student=self.student.pk,category="engaged").status_code,302)
        obs=ClassroomObservation.objects.get()
        self.assertContains(self.client.get(self.tools),"engaged")
        self.assertEqual(self.post("withdraw_observation",observation=obs.pk).status_code,302)
        obs.refresh_from_db()
        self.assertIsNotNone(obs.withdrawn_at)

    def test_named_task_lifecycle_and_revocation(self):
        self.assertEqual(self.post("task",student=self.student.pk,category="practice",recipient=self.other.pk).status_code,403)
        self.assertEqual(self.post("task",student=self.student.pk,category="practice",recipient=self.aide.pk).status_code,302)
        task=SupportTask.objects.get()
        self.client.force_login(self.aide)
        self.assertContains(self.client.get(self.board),"FictionalPupil")
        self.assertNotContains(self.client.get(self.board),"OtherPupil")
        self.client.force_login(self.unassigned)
        self.assertNotContains(self.client.get(self.board),"FictionalPupil")
        self.assertEqual(self.change(self.unassigned,"task",task,"accept",1).status_code,404)
        self.assertEqual(self.change(self.admin,"task",task,"accept",1).status_code,403)
        self.assertEqual(self.change(self.aide,"task",task,"complete",1).status_code,403)
        self.assertEqual(self.change(self.aide,"task",task,"accept",1).status_code,302)
        self.assertEqual(self.change(self.aide,"task",task,"complete",1).status_code,409)
        StaffAccessGrant.objects.filter(user=self.aide).delete()
        self.assertEqual(self.change(self.aide,"task",task,"complete",2).status_code,403)
        task.refresh_from_db()
        self.assertEqual(task.state,"accepted")
        self.assertEqual(self.change(self.teacher,"task",task,"cancel",2).status_code,302)
        task.refresh_from_db()
        self.assertEqual(task.state,"cancelled")

    def test_referral_review_and_reassignment(self):
        self.assertEqual(self.post("referral",student=self.student.pk,category="learning_review").status_code,302)
        r=SupportReferral.objects.get()
        self.client.force_login(self.reviewer)
        self.assertNotContains(self.client.get(self.board),"FictionalPupil")
        self.assertEqual(self.change(self.reviewer,"referral",r,"review",1).status_code,404)
        self.assertEqual(self.change(self.coord,"referral",r,"assign",1,recipient=self.aide.pk).status_code,403)
        self.assertEqual(self.change(self.coord,"referral",r,"assign",1,recipient=self.reviewer.pk).status_code,302)
        self.client.force_login(self.reviewer)
        self.assertContains(self.client.get(self.board),"FictionalPupil")
        self.assertEqual(self.change(self.reviewer,"referral",r,"review",2).status_code,302)
        self.assertEqual(self.change(self.reviewer,"referral",r,"close",3).status_code,302)
        r.refresh_from_db()
        self.assertEqual(r.state,"closed")
        self.assertIsNotNone(r.closed_at)

    def test_relief_cannot_create_persistent_support_and_stale_identity(self):
        self.assertEqual(self.post("task",student=self.student.pk,category="practice",recipient=self.aide.pk).status_code,302)
        task=SupportTask.objects.get()
        self.pub.snapshot["slots"][1]["start"]="11:00"
        self.pub.snapshot["slots"][1]["end"]="12:00"
        self.pub.save()
        self.client.force_login(self.admin)
        r=self.client.post("/manage/attendance/relief/",{"action":"assign","publication":str(self.pub.pk),"lesson":"ENG7|P1|09:00","teacher":self.other.pk})
        self.assertEqual(r.status_code,302)
        self.client.force_login(self.other)
        self.assertContains(self.client.get(self.tools),"Relief access is limited")
        self.assertEqual(self.post("observe",student=self.student.pk,category="engaged").status_code,403)
        self.student.student_id="CHANGED"
        self.student.save()
        self.client.force_login(self.aide)
        self.assertNotContains(self.client.get(self.board),"FictionalPupil")
        self.assertEqual(self.change(self.aide,"task",task,"accept",1).status_code,404)

    def test_expiry_publication_and_csrf(self):
        self.assertEqual(self.post("task",student=self.student.pk,category="practice",recipient=self.aide.pk).status_code,302)
        task=SupportTask.objects.get()
        c=Client(enforce_csrf_checks=True)
        c.force_login(self.aide)
        self.assertEqual(c.post(f"/live/support/task/{task.pk}/change/",{"action":"accept","revision":"1"}).status_code,403)
        StaffAccessGrant.objects.filter(user=self.aide).update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.change(self.aide,"task",task,"accept",1).status_code,403)
        self.pub.active=False
        self.pub.save()
        self.client.force_login(self.coord)
        self.assertNotContains(self.client.get(self.board),"FictionalPupil")
