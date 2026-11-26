"""Fictional workforce planning and authority regressions."""
from datetime import timedelta
from django.test import TestCase,Client,override_settings
from django.utils import timezone
from . import test_live_foundation
from .models import WorkforceEntry,WorkforceNotice,StaffAccessGrant,ReliefAttendanceAssignment,AttendanceRoll
from .attendance import own_lessons
from .attendance_operations import daily_status

@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True,SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False)
class WorkforceTests(TestCase):
    def setUp(self):
        test_live_foundation.LiveFoundationTests.setUp(self)
        self.board="/live/workforce/"
        self.relief="/manage/attendance/relief/"
        self.client.force_login(self.admin)

    def create(self,kind,**kw):
        data={"action":"create","publication":str(self.pub.pk),"kind":kind,"confirm":"on"}
        data.update(kw)
        return self.client.post(self.board,data)

    def cancel(self,entry):
        return self.client.post(self.board,{"action":"cancel","publication":str(self.pub.pk),"entry":entry.pk,"confirm":"yes"})

    def free_other(self):
        self.pub.snapshot["slots"][1]["start"]="11:00"
        self.pub.snapshot["slots"][1]["end"]="12:00"
        self.pub.save()

    def test_absence_coverage_and_existing_relief_authority(self):
        self.free_other()
        self.assertEqual(self.create("absence",staff=self.teacher.pk).status_code,302)
        entry=WorkforceEntry.objects.get()
        self.assertEqual(self.client.get(self.board).context["uncovered"],1)
        self.assertEqual(own_lessons(self.pub,self.teacher,self.day),[])
        rows,summary=daily_status(self.pub,self.day)
        self.assertTrue(any("Uncovered absence" in r["status"] for r in rows))
        p={"action":"assign","publication":str(self.pub.pk),"lesson":"ENG7|P1|09:00","teacher":self.other.pk}
        self.assertEqual(self.client.post(self.relief,p).status_code,302)
        self.assertEqual(self.client.get(self.board).context["uncovered"],0)
        self.assertContains(self.cancel(entry),"Resolve existing relief")
        self.client.force_login(self.other)
        self.assertContains(self.client.get(self.url),"FictionalPupil")
        self.assertNotContains(self.client.get(self.url),"OtherPupil")
        self.assertEqual(self.client.post(self.url,self.payload("submit")).status_code,302)
        self.assertEqual(AttendanceRoll.objects.get().teacher_id,self.other.pk)

    def test_duty_and_room_conflicts(self):
        r=self.create("duty",staff=self.teacher.pk,start="09:15",end="09:30",location="Fictional courtyard")
        self.assertContains(r,"overlapping allocation")
        self.assertEqual(self.create("duty",staff=self.teacher.pk,start="10:00",end="10:30",location="Fictional courtyard").status_code,302)
        self.assertContains(self.create("absence",staff=self.teacher.pk),"Resolve existing")
        self.assertContains(self.create("room",lesson="ENG7|P1|09:00",location="F02"),"overlapping allocation")
        self.free_other()
        self.assertEqual(self.create("room",lesson="ENG7|P1|09:00",location="F02").status_code,302)
        self.assertEqual(own_lessons(self.pub,self.teacher,self.day)[0]["room"],"F02")
        self.assertEqual(self.pub.snapshot["slots"][0]["room"],"F01")
        room=WorkforceEntry.objects.get(kind="room")
        self.assertEqual(self.cancel(room).status_code,302)
        self.assertEqual(own_lessons(self.pub,self.teacher,self.day)[0]["room"],"F01")

    def test_relief_rejects_supervision_or_unavailability(self):
        self.free_other()
        self.assertEqual(self.create("duty",staff=self.other.pk,start="09:00",end="10:00",location="Fictional courtyard").status_code,302)
        p={"action":"assign","publication":str(self.pub.pk),"lesson":"ENG7|P1|09:00","teacher":self.other.pk}
        self.assertContains(self.client.post(self.relief,p),"assigned to supervision")
        self.assertFalse(ReliefAttendanceAssignment.objects.exists())
        self.assertEqual(self.cancel(WorkforceEntry.objects.get()).status_code,302)
        self.assertEqual(self.create("absence",staff=self.other.pk).status_code,302)
        self.assertContains(self.client.post(self.relief,p),"unavailable")
        self.assertFalse(ReliefAttendanceAssignment.objects.exists())

    def test_closure_and_existing_attendance_protection(self):
        self.assertEqual(self.create("closure").status_code,302)
        closure=WorkforceEntry.objects.get()
        self.assertEqual(own_lessons(self.pub,self.teacher,self.day),[])
        self.assertEqual(daily_status(self.pub,self.day)[1]["expected"],0)
        self.assertContains(self.client.get("/live/attendance/"),"Approved school day closure")
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(self.url).status_code,403)
        self.client.force_login(self.admin)
        self.assertEqual(self.cancel(closure).status_code,302)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post(self.url,self.payload("submit")).status_code,302)
        self.client.force_login(self.admin)
        self.assertContains(self.create("closure"),"Recorded attendance")
        self.assertContains(self.create("room",lesson="ENG7|P1|09:00",location="F02"),"existing roll/movement")

    def test_private_notices_read_only_monitor_and_csrf(self):
        self.assertEqual(self.create("absence",staff=self.teacher.pk).status_code,302)
        n=WorkforceNotice.objects.get(recipient=self.teacher)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.board).status_code,403)
        self.assertEqual(self.client.post(f"/live/workforce/notices/{n.pk}/ack/").status_code,404)
        self.assertNotContains(self.client.get("/live/workforce/mine/"),n.message)
        self.client.force_login(self.teacher)
        self.assertContains(self.client.get("/live/workforce/mine/"),n.message)
        self.assertEqual(self.client.post(f"/live/workforce/notices/{n.pk}/ack/").status_code,302)
        n.refresh_from_db()
        self.assertIsNotNone(n.acknowledged_at)
        StaffAccessGrant.objects.create(user=self.monitor,role="Custom",scope="school",scope_value="",capabilities=["workforce_monitor"],granted_by=self.admin)
        self.client.force_login(self.monitor)
        self.assertContains(self.client.get(self.board),"Uncovered")
        self.assertEqual(self.create("closure").status_code,403)
        c=Client(enforce_csrf_checks=True)
        c.force_login(self.admin)
        self.assertEqual(c.post(self.board,{"action":"create","kind":"closure"}).status_code,403)

    def test_future_relief_and_publication_binding(self):
        self.free_other()
        future=self.day+timedelta(days=1)
        self.pub.ends=future
        self.pub.snapshot["calendar"]["dates"].append(future.isoformat())
        self.pub.snapshot["slots"] += [dict(r,date=future.isoformat()) for r in self.pub.snapshot["slots"]]
        self.pub.save()
        path=self.relief+"?date="+future.isoformat()
        p={"action":"assign","publication":str(self.pub.pk),"lesson":"ENG7|P1|09:00","teacher":self.other.pk}
        self.assertEqual(self.client.post(path,p).status_code,302)
        self.assertEqual(ReliefAttendanceAssignment.objects.get().lesson_date,future)
        self.assertEqual(len(own_lessons(self.pub,self.teacher,self.day)),1)
        self.assertEqual(len(own_lessons(self.pub,self.teacher,future)),0)
        self.assertEqual(len(own_lessons(self.pub,self.other,future)),2)
        self.assertEqual(self.client.post(path,{"action":"cancel","assignment":ReliefAttendanceAssignment.objects.get().pk}).status_code,302)
        self.assertEqual(len(own_lessons(self.pub,self.teacher,future)),1)
