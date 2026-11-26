from django.contrib.auth.models import User
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from django.urls import reverse
from .models import (AttendanceRoll, AttendanceRevision, ConnectedSchoolPublication,
                     ImportedTimetable, StaffProfile, StaffAccessGrant, Student)
from .live_views import roster_token


@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True, SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class LiveFoundationTests(TestCase):
    def setUp(self):
        from unittest.mock import patch
        clock=patch('accounts.live_views.lesson_started',return_value=True)
        clock.start()
        self.addCleanup(clock.stop)
        self.day = timezone.localdate()
        self.admin = User.objects.create_superuser("fictional-admin", password="Fictional-password-42!")
        self.teacher = User.objects.create_user("fictional-teacher", password="Fictional-password-42!")
        self.other = User.objects.create_user("fictional-other", password="Fictional-password-42!")
        self.monitor = User.objects.create_user("fictional-monitor", password="Fictional-password-42!")
        self.profile = StaffProfile.objects.create(user=self.teacher, staff_id="TEACH001", teaching_enabled=True, timetable_link_verified=True)
        self.other_profile = StaffProfile.objects.create(user=self.other, staff_id="OTHER001", teaching_enabled=True, timetable_link_verified=True)
        self.grant = StaffAccessGrant.objects.create(user=self.monitor, role="Attendance Officer",
            scope="school", capabilities=["attendance_monitor"], granted_by=self.admin)
        self.student = Student.objects.create(student_id="FICTIONAL001", first_name="FictionalPupil", last_name="Example", year_level=7)
        self.outside = Student.objects.create(student_id="FICTIONAL002", first_name="OtherPupil", last_name="Example", year_level=8)
        self.version = ImportedTimetable.objects.create(name="Fictional timetable", digest="f"*64,
            status=ImportedTimetable.Status.PUBLISHED)
        self.pub = ConnectedSchoolPublication.objects.create(name="Fictional publication",
            starts=self.day, ends=self.day, digest="a"*64, published_by=self.admin,
            snapshot={"source":"dated","timetable_version":self.version.pk,
                      "calendar":{"dates":[self.day.isoformat()]},
                      "stats":{"rosters_ready":True,"skipped_pairs":0},
                      "classes":[{"code":"ENG7","name":"English","years":[7],"students":[self.student.pk]},
                                 {"code":"SCI8","name":"Science","years":[8],"students":[self.outside.pk]}],
                      "student_identity":{str(self.student.pk):self.student.student_id,
                                          str(self.outside.pk):self.outside.student_id},
                      "bindings":{"TEACH001":{"profile":self.profile.pk,"user":self.teacher.pk,"staff_id":"TEACH001"},
                                  "OTHER001":{"profile":self.other_profile.pk,"user":self.other.pk,"staff_id":"OTHER001"}},
                      "slots":[{"code":"ENG7","name":"English","date":self.day.isoformat(),"period":"P1","start":"09:00","end":"10:00","staff":"TEACH001","room":"F01"},
                               {"code":"SCI8","name":"Science","date":self.day.isoformat(),"period":"P1","start":"09:00","end":"10:00","staff":"OTHER001","room":"F02"}]})
        self.url = reverse("live-roll")+"?code=ENG7&period=P1&start=09%3A00"
        self.other_url = reverse("live-roll")+"?code=SCI8&period=P1&start=09%3A00"
        self.client.force_login(self.teacher)

    def payload(self, action="draft", rev=0, mark="P"):
        return {"action":action,"revision":str(rev),"publication":str(self.pub.pk),
                "day":self.day.isoformat(),"roster_token":roster_token([self.student]),
                "mark_"+str(self.student.pk):mark,"certify":"yes"}

    def test_protected_login_and_authorised_home(self):
        self.client.logout()
        self.assertRedirects(self.client.post("/",{"username":self.teacher.username,"password":"Fictional-password-42!"}),"/live/")
        self.assertRedirects(self.client.get("/teacher/"),"/live/day/")
        self.assertContains(self.client.get("/live/"),"My daily schedule")
        self.assertNotContains(self.client.get("/live/"),"Attendance overview")
        self.assertNotContains(self.client.get("/live/day/"),"SCI8")
        self.assertContains(self.client.get(self.url),"FictionalPupil")
        self.assertNotContains(self.client.get(self.url),"OtherPupil")

    def test_teacher_draft_submit_monitor_separate_session(self):
        officer = Client()
        officer.force_login(self.monitor)
        self.assertContains(officer.get("/live/attendance/"),"Not started")
        self.assertRedirects(self.client.post(self.url,self.payload()),self.url)
        self.assertContains(officer.get("/live/attendance/"),"Draft")
        self.assertRedirects(self.client.post(self.url,self.payload("submit",1,"L")),self.url)
        saved = AttendanceRoll.objects.get()
        self.assertEqual(saved.marks,{str(self.student.pk):"L"})
        self.assertIsNotNone(saved.submitted_at)
        self.assertEqual(list(saved.history.order_by("revision").values_list("action",flat=True)),["draft","submit"])
        response = officer.get("/live/attendance/")
        self.assertContains(response,"Submitted")
        self.assertNotContains(response,"FictionalPupil")
        self.assertEqual(self.client.post(self.url,self.payload("draft",2)).status_code,409)
        self.assertEqual(AttendanceRevision.objects.count(),2)
        self.assertEqual(officer.post(self.url,self.payload()).status_code,403)
        self.assertEqual(officer.get(self.url).status_code,403)

    def test_forgery_stale_revision_and_csrf(self):
        self.assertEqual(self.client.get(self.other_url).status_code,403)
        self.assertEqual(self.client.post(self.other_url,self.payload()).status_code,403)
        self.assertEqual(self.client.post(self.url,{**self.payload(),"mark_"+str(self.outside.pk):"A"}).status_code,400)
        self.assertEqual(self.client.post(self.url,self.payload(mark="invalid")).status_code,400)
        self.assertEqual(self.client.post(self.url,{**self.payload(),"roster_token":"forged"}).status_code,409)
        self.assertContains(self.client.post(self.url,self.payload("submit",mark="")),"Mark every student")
        self.assertEqual(AttendanceRoll.objects.count(),0)
        self.assertRedirects(self.client.post(self.url,self.payload()),self.url)
        self.assertEqual(self.client.post(self.url,self.payload("draft",0,"A")).status_code,409)
        c=Client(enforce_csrf_checks=True)
        c.force_login(self.teacher)
        self.assertEqual(c.post(self.url,self.payload("draft",1)).status_code,403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code,403)
        self.assertEqual(self.client.get("/live/attendance/").status_code,403)

    def test_identity_revocation_and_incomplete_roster(self):
        self.profile.timetable_link_verified=False
        self.profile.save()
        self.assertEqual(self.client.get(self.url).status_code,403)
        self.profile.timetable_link_verified=True
        self.profile.save()
        self.student.student_id="CHANGED"
        self.student.save()
        self.assertEqual(self.client.get(self.url).status_code,409)
        self.student.student_id="FICTIONAL001"
        self.student.save()
        self.pub.snapshot["stats"]["skipped_pairs"]=1
        self.pub.save()
        self.assertEqual(self.client.get(self.url).status_code,403)
        self.assertEqual(AttendanceRoll.objects.count(),0)

    def test_republication_blocks_edit_and_revoked_monitor(self):
        self.assertRedirects(self.client.post(self.url,self.payload()),self.url)
        self.pub.active=False
        self.pub.save()
        ConnectedSchoolPublication.objects.create(name="Replacement",starts=self.day,ends=self.day,
            digest="b"*64,published_by=self.admin,snapshot=self.pub.snapshot)
        self.assertEqual(self.client.get(self.url).status_code,409)
        self.assertEqual(self.client.post(self.url,self.payload("submit",1)).status_code,409)
        self.client.force_login(self.monitor)
        self.assertContains(self.client.get("/live/attendance/"),"Publication changed")
        self.grant.delete()
        self.assertEqual(self.client.get("/live/attendance/").status_code,403)

    def test_ambiguous_overlapping_lesson_fails_closed(self):
        row=dict(self.pub.snapshot["slots"][0], period="P2",start="09:30",end="10:30")
        self.pub.snapshot["slots"].append(row)
        self.pub.save()
        self.assertEqual(self.client.get(self.url).status_code,403)

    def test_no_fictional_fallback_when_no_publication(self):
        self.pub.active=False
        self.pub.save()
        self.assertRedirects(self.client.get("/teacher/"),"/live/day/")
        self.assertContains(self.client.get("/live/day/"),"No unambiguous verified lessons")
        self.assertNotContains(self.client.get("/live/day/"),"rollflow-server-identity")

    def test_local_transfer_requires_admin_and_exact_submitted_revision(self):
        from .models import AttendanceTransferReview, AccessAudit
        self.assertEqual(self.client.post(self.url,self.payload("submit")).status_code,302)
        roll=AttendanceRoll.objects.get()
        path=f"/manage/school-data/transfers/{roll.pk}/"
        self.assertEqual(self.client.get(path).status_code,403)
        self.client.force_login(self.monitor)
        self.assertEqual(self.client.get(path).status_code,403)
        self.client.force_login(self.admin)
        r=self.client.get(path)
        self.assertContains(r,"not an approved OneSchool import format")
        digest=r.context["digest"]
        self.assertTrue(digest)
        self.assertEqual(self.client.post(path,{"confirm":"yes","action":"export","digest":"bad"}).status_code,200)
        self.assertFalse(AttendanceTransferReview.objects.exists())
        self.assertContains(self.client.post(path,{"confirm":"yes","action":"reconcile","digest":digest}),"Export and review")
        r=self.client.post(path,{"confirm":"yes","action":"export","digest":digest})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r["Content-Type"],"text/csv; charset=utf-8")
        self.assertIn("LOCAL-REVIEW",r["Content-Disposition"])
        self.assertIn(b"FICTIONAL001",r.content)
        self.assertNotIn(b"FICTIONAL002",r.content)
        self.assertNotIn(b"FictionalPupil",r.content)
        self.assertEqual(AttendanceTransferReview.objects.count(),1)
        self.assertEqual(self.client.post(path,{"confirm":"yes","action":"reconcile","digest":digest}).status_code,302)
        self.assertIsNotNone(AttendanceTransferReview.objects.get().reconciled_at)
        self.assertContains(self.client.post(path,{"confirm":"yes","action":"reconcile","digest":digest}),"already been")
        self.assertTrue(AccessAudit.objects.filter(action="attendance_manual_reconcile").exists())

    def test_local_transfer_rejects_identity_change_and_csv_injection(self):
        from .data_views import safe_csv_cell
        for value in ("=HYPERLINK(1)"," +1","@SUM(1)","-1","tab\tvalue"):
            with self.assertRaises(ValueError):
                safe_csv_cell(value)
        self.assertEqual(self.client.post(self.url,self.payload("submit")).status_code,302)
        roll=AttendanceRoll.objects.get()
        self.client.force_login(self.admin)
        self.student.student_id="REPLACED"
        self.student.save()
        self.assertContains(self.client.get(f"/manage/school-data/transfers/{roll.pk}/"),"Student identity changed")

