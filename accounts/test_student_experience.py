"""Fictional student workflows: read scopes, follow-up audits and existing write contract."""
from datetime import timedelta
from django.test import TestCase,override_settings
from django.utils import timezone
from . import test_movements,test_classroom_support
from .models import SupportTask,SupportReferral,StudentMovement,MovementEvent,ClassroomPlan,AccessAudit

@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True,SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False)
class StudentMovementDayTests(TestCase):
    def setUp(self):
        test_movements.MovementTests.setUp(self)

    def issue_data(self,**kw):
        return test_movements.MovementTests.issue_data(self,**kw)

    def test_multiple_visits_by_recorded_period_and_scope(self):
        first=test_movements.MovementTests.make_pass(self)
        self.assertEqual(test_movements.MovementTests.act(self,self.admin,first,"close",1,reason="entered_in_error").status_code,302)
        second=test_movements.MovementTests.make_pass(self,destination=str(self.other_dest.pk))
        url=f"/live/movements/{first.pk}/day/"
        r=self.client.get(url)
        self.assertContains(r,"Student movement day")
        self.assertContains(r,"P1")
        self.assertEqual(r.context["total"],2)
        self.client.force_login(self.receiver)
        r=self.client.get(url)
        self.assertEqual(r.context["total"],1)
        self.assertNotContains(r,self.other_dest.name)
        self.assertEqual(self.client.get(f"/live/movements/{second.pk}/day/").status_code,404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code,404)
        self.client.force_login(self.monitor)
        self.assertEqual(self.client.get(url).context["total"],2)
        self.assertEqual(self.client.get(url,{"date":(self.day+timedelta(days=1)).isoformat()}).status_code,400)

    def test_changed_identity_is_not_disclosed_and_outside_interval(self):
        m=test_movements.MovementTests.make_pass(self)
        url=f"/live/movements/{m.pk}/day/"
        StudentMovement.objects.filter(pk=m.pk).update(departed_at=self.now+timedelta(hours=2))
        self.assertContains(self.client.get(url),"Outside recorded lesson interval")
        self.student.student_id="CHANGED"
        self.student.save(update_fields=["student_id"])
        self.assertEqual(self.client.get(url).status_code,404)
        self.assertNotContains(self.client.get(self.board),"FictionalPupil")

@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True,SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False)
class FollowUpExperienceTests(TestCase):
    def setUp(self):
        test_classroom_support.ClassroomSupportTests.setUp(self)

    def post(self,action,**kw):
        return test_classroom_support.ClassroomSupportTests.post(self,action,**kw)

    def change(self,user,kind,record,action,rev,**kw):
        return test_classroom_support.ClassroomSupportTests.change(self,user,kind,record,action,rev,**kw)

    def test_due_dates_and_reschedule_permission_revision_audit(self):
        due=self.day+timedelta(days=2)
        self.assertEqual(self.post("task",student=self.student.pk,category="practice",recipient=self.aide.pk,due=due.isoformat()).status_code,302)
        task=SupportTask.objects.get()
        self.assertEqual(task.due_on,due)
        self.assertEqual(self.change(self.aide,"task",task,"reschedule",1,due=(self.day+timedelta(days=3)).isoformat()).status_code,403)
        new=self.day+timedelta(days=4)
        self.assertEqual(self.change(self.teacher,"task",task,"reschedule",1,due=new.isoformat()).status_code,302)
        task.refresh_from_db()
        self.assertEqual(task.due_on,new)
        self.assertEqual(task.revision,2)
        self.assertEqual(task.state,"pending")
        self.assertEqual(self.change(self.teacher,"task",task,"reschedule",1,due=due.isoformat()).status_code,409)
        self.assertEqual(self.change(self.coord,"task",task,"reschedule",2,due=(self.day+timedelta(days=91)).isoformat()).status_code,409)
        self.assertEqual(self.change(self.coord,"task",task,"reschedule",2,due="").status_code,400)
        self.assertTrue(AccessAudit.objects.filter(action="support_reschedule").exists())

    def test_follow_up_tabs_do_not_expand_authority(self):
        self.assertEqual(self.post("task",student=self.student.pk,category="practice",recipient=self.aide.pk).status_code,302)
        self.assertEqual(self.post("referral",student=self.student.pk,category="learning_review").status_code,302)
        SupportTask.objects.update(due_on=self.day-timedelta(days=1))
        self.client.force_login(self.aide)
        r=self.client.get(self.board,{"view":"followups"})
        self.assertEqual(r.context["counts"],{"tasks":1,"referrals":0,"followups":1,"closed":0})
        self.assertContains(r,"FictionalPupil")
        self.client.force_login(self.unassigned)
        self.assertNotContains(self.client.get(self.board,{"view":"followups"}),"FictionalPupil")
        self.client.force_login(self.coord)
        self.assertEqual(self.client.get(self.board,{"view":"referrals"}).context["rows"].paginator.count,1)
        self.assertEqual(self.client.get(self.board,{"view":"invalid"}).status_code,400)

    def test_seating_progressive_enhancement_and_invalid_due(self):
        r=self.client.get(self.tools)
        self.assertContains(r,'id="rf-seat-grid"')
        self.assertContains(r,'id="rf-class-action-picker"')
        self.assertNotContains(r,"OtherPupil")
        field="seat_"+str(self.student.pk)
        self.assertEqual(self.post("seating",revision="0",**{field:"12"}).status_code,302)
        self.assertContains(self.client.get(self.tools),"Seat 12")
        self.assertEqual(ClassroomPlan.objects.get().seats,{str(self.student.pk):12})
        self.assertEqual(self.post("referral",student=self.student.pk,category="learning_review",due=(self.day-timedelta(days=1)).isoformat()).status_code,409)
        self.assertFalse(SupportReferral.objects.exists())
