from datetime import timedelta
from django.test import TestCase,override_settings
from django.urls import reverse
from django.utils import timezone
from . import test_live_foundation
from .models import AttendanceRoll,WorkforceEntry

@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True,SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False)
class TeacherExperienceTests(TestCase):
    def setUp(self):
        test_live_foundation.LiveFoundationTests.setUp(self)
        self.future=self.day+timedelta(days=1)
        self.past=self.day-timedelta(days=1)
        snap=self.pub.snapshot
        snap["calendar"]["dates"].extend([self.past.isoformat(),self.future.isoformat()])
        original=list(snap["slots"])
        for day in (self.past,self.future):
            snap["slots"].extend(dict(r,date=day.isoformat()) for r in original)
        self.pub.starts=self.past;self.pub.ends=self.future
        self.pub.save(update_fields=["starts","ends","snapshot"])

    def test_dates_week_and_master_exclude_other_allocations(self):
        r=self.client.get("/live/day/")
        self.assertContains(r,"Daily Schedule")
        self.assertContains(r,'data-timetable-class="ENG7"')
        self.assertNotContains(r,"SCI8")
        self.assertContains(r,"Open roll")
        for day in (self.past,self.future):
            r=self.client.get("/live/day/",{"date":day.isoformat()})
            self.assertContains(r,'data-timetable-class="ENG7"')
            self.assertNotContains(r,"SCI8")
            self.assertNotContains(r,"Open roll")
        r=self.client.get("/teacher/week/")
        self.assertEqual(len(r.context["days"]),5)
        self.assertNotContains(r,"SCI8")
        self.assertContains(self.client.get("/live/teacher/master/"),"My verified allocations only")
        self.assertNotContains(self.client.get("/live/teacher/master/"),"SCI8")
        self.assertEqual(self.client.get("/live/day/",{"date":"invalid"}).status_code,400)
        r=self.client.get("/live/day/",{"date":(self.future+timedelta(days=10)).isoformat()})
        self.assertContains(r,"No published school day")
        self.assertNotContains(r,'data-timetable-class="ENG7"')
        self.assertEqual(self.client.post(self.url+"&date="+self.past.isoformat(),test_live_foundation.LiveFoundationTests.payload(self)).status_code,400)
        self.assertEqual(AttendanceRoll.objects.count(),0)

    def test_class_and_student_scope_filters_and_direct_access(self):
        self.assertContains(self.client.get("/live/teacher/classes/"),"ENG7")
        self.assertNotContains(self.client.get("/live/teacher/classes/"),"SCI8")
        self.assertNotContains(self.client.get("/live/teacher/classes/",{"year":"8"}),"ENG7")
        self.assertContains(self.client.get("/live/teacher/classes/ENG7/"),"FictionalPupil")
        self.assertEqual(self.client.get("/live/teacher/classes/SCI8/").status_code,404)
        self.assertEqual(self.client.get("/teacher/roster/SCI8/").status_code,404)
        self.assertContains(self.client.get("/live/teacher/students/",{"q":"FictionalPupil"}),"FictionalPupil")
        self.assertNotContains(self.client.get("/live/teacher/students/"),"OtherPupil")
        self.assertEqual(self.client.get("/live/teacher/students/"+str(self.outside.pk)+"/").status_code,404)
        self.assertContains(self.client.get("/live/teacher/students/"+str(self.student.pk)+"/"),"ENG7")
        self.assertEqual(self.client.get("/live/teacher/students/",{"year":"13"}).status_code,400)
        self.profile.timetable_link_verified=False;self.profile.save(update_fields=["timetable_link_verified"])
        self.assertNotContains(self.client.get("/live/teacher/classes/"),"ENG7")
        self.assertEqual(self.client.get("/live/teacher/students/"+str(self.student.pk)+"/").status_code,404)

    def test_current_enrolment_and_identity_are_rechecked(self):
        self.student.student_id="CHANGED";self.student.save(update_fields=["student_id"])
        self.assertNotContains(self.client.get("/live/teacher/students/"),"FictionalPupil")
        self.assertEqual(self.client.get("/live/teacher/classes/ENG7/").status_code,404)
        self.assertContains(self.client.get("/live/day/"),"Roster review required")
        self.assertNotContains(self.client.get("/live/day/"),"Open roll")

    def test_room_duty_and_closure_overlays(self):
        WorkforceEntry.objects.create(publication=self.pub,day=self.day,kind="room",class_code="ENG7",period="P1",start="09:00",end="10:00",location="F99",created_by=self.admin)
        WorkforceEntry.objects.create(publication=self.pub,day=self.day,kind="duty",staff=self.teacher,start="10:00",end="10:30",location="Fictional courtyard",created_by=self.admin)
        r=self.client.get("/live/day/")
        self.assertContains(r,"Room F99")
        self.assertContains(r,"Supervision duty")
        self.assertContains(r,"Fictional courtyard")
        WorkforceEntry.objects.create(publication=self.pub,day=self.day,kind="closure",created_by=self.admin)
        r=self.client.get("/live/day/")
        self.assertContains(r,"School day closed")
        self.assertNotContains(r,"Open roll")
        self.assertEqual(self.client.get(self.url).status_code,403)

    def test_non_teacher_and_unready_source_denied(self):
        self.client.force_login(self.monitor)
        for path in ("/live/teacher/master/","/live/teacher/classes/","/live/teacher/students/","/live/teacher/classes/ENG7/"):
            self.assertEqual(self.client.get(path).status_code,403)
        self.client.force_login(self.teacher)
        self.pub.snapshot["stats"]["rosters_ready"]=False
        self.pub.save(update_fields=["snapshot"])
        self.assertNotContains(self.client.get("/live/teacher/students/"),"FictionalPupil")
        self.assertEqual(self.client.get("/live/teacher/classes/ENG7/").status_code,404)

    def test_attendance_buttons_keep_existing_submission_contract(self):
        r=self.client.get(self.url)
        self.assertContains(r,'data-mark="P"')
        self.assertContains(r,'name="mark_'+str(self.student.pk)+'"')
        self.assertRedirects(self.client.post(self.url,test_live_foundation.LiveFoundationTests.payload(self,"draft",mark="L")),self.url)
        self.assertRedirects(self.client.post(self.url,test_live_foundation.LiveFoundationTests.payload(self,"submit",rev=1,mark="P")),self.url)
        self.assertContains(self.client.get(self.url),"This roll is locked.")
        self.assertEqual(AttendanceRoll.objects.get().marks,{str(self.student.pk):"P"})


    def test_relief_directory_and_roll_recheck_original_binding(self):
        from .models import ReliefAttendanceAssignment
        # Remove the relief teacher's conflicting lesson on today only.
        self.pub.snapshot["slots"]=[r for r in self.pub.snapshot["slots"] if not
            (r["code"]=="SCI8" and r["date"]==self.day.isoformat())]
        self.pub.save(update_fields=["snapshot"])
        ReliefAttendanceAssignment.objects.create(publication=self.pub,lesson_date=self.day,
            class_code="ENG7",period="P1",start="09:00",end="10:00",regular_teacher=self.teacher,
            relief_teacher=self.other,created_by=self.admin,expires_at=timezone.now()+timedelta(hours=1))
        self.client.force_login(self.other)
        self.assertContains(self.client.get("/live/day/"),"Relief cover")
        self.assertContains(self.client.get("/live/teacher/classes/ENG7/"),"FictionalPupil")
        self.profile.timetable_link_verified=False
        self.profile.save(update_fields=["timetable_link_verified"])
        self.assertNotContains(self.client.get("/live/day/"),'data-timetable-class="ENG7"')
        self.assertEqual(self.client.get("/live/teacher/classes/ENG7/").status_code,404)
        self.assertEqual(self.client.get(self.url).status_code,403)
