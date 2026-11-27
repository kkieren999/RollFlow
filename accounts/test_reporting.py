"""Fictional leadership report permission and aggregation regressions."""
from datetime import timedelta
from django.contrib.auth.models import User
from django.test import Client,TestCase,override_settings
from django.utils import timezone
from . import test_live_foundation
from .models import AccessAudit,StaffAccessGrant,StudentMovement,MovementDestination,WorkforceEntry,SupportTask,Student
from .reporting import build
from .report_views import csv_cell,pdf_bytes
from pypdf import PdfReader
import io

@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True,SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False)
class ReportingTests(TestCase):
    def setUp(self):
        test_live_foundation.LiveFoundationTests.setUp(self)
        self.leader=User.objects.create_user("fictional-leader",password="Fictional-password-42!")
        self.profile.faculty="English"
        self.profile.save()
        self.other_profile.faculty="Science"
        self.other_profile.save()
        self.path="/live/reports/"
        self.client.force_login(self.leader)

    def report_grant(self,scope,value,caps):
        return StaffAccessGrant.objects.create(user=self.leader,role="Custom",scope=scope,scope_value=value,
            capabilities=caps,granted_by=self.admin)

    def params(self,domain="attendance",scope="year",value="7",**kw):
        return dict({"domain":domain,"scope":scope,"value":value,"start":self.day.isoformat(),"end":self.day.isoformat()},**kw)

    def test_explicit_report_scope_and_no_cross_domain_borrowing(self):
        self.assertEqual(self.client.get(self.path).status_code,403)
        self.report_grant("year","7",["report_attendance"])
        self.report_grant("school","",["report_movements"])
        self.assertContains(self.client.get("/live/"),"Leadership dashboards")
        r=self.client.get(self.path,self.params())
        self.assertEqual(r.status_code,200)
        self.assertEqual(dict(r.context["data"]["rows"])["Scheduled lesson keys"],1)
        self.assertNotContains(r,"FictionalPupil")
        self.assertNotContains(r,"OtherPupil")
        self.assertEqual(self.client.get(self.path,self.params(scope="school",value="")).status_code,403)
        self.assertEqual(self.client.get(self.path,self.params(domain="movements")).status_code,403)
        self.assertEqual(self.client.get(self.path,self.params(value="8")).status_code,403)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.path).status_code,403)

    def test_faculty_and_mixed_year_validation(self):
        self.report_grant("faculty","English",["report_attendance"])
        self.report_grant("year","7",["report_attendance"])
        r=self.client.get(self.path,self.params(scope="faculty",value="English"))
        self.assertEqual(dict(r.context["data"]["rows"])["Scheduled lesson keys"],1)
        self.pub.snapshot["classes"][0]["years"]=[7,8]
        self.pub.save()
        r=self.client.get(self.path,self.params())
        self.assertEqual(dict(r.context["data"]["rows"])["Scheduled lesson keys"],0)
        self.profile.timetable_link_verified=False
        self.profile.save()
        r=self.client.get(self.path,self.params(scope="faculty",value="English"))
        self.assertEqual(dict(r.context["data"]["rows"])["Scheduled lesson keys"],0)

    def test_exports_require_exact_grant_and_digest_and_audit(self):
        self.report_grant("year","7",["report_attendance"])
        self.report_grant("school","",["export_attendance"])
        r=self.client.get(self.path,self.params())
        p=self.params(digest=r.context["digest"],confirm="yes",format="csv")
        self.assertEqual(self.client.post(self.path,p).status_code,403)
        g=self.report_grant("year","7",["export_attendance"])
        self.assertEqual(self.client.post(self.path,{**p,"digest":"bad"}).status_code,409)
        self.assertEqual(self.client.post(self.path,{**p,"confirm":"no"}).status_code,400)
        r=self.client.post(self.path,p)
        self.assertEqual(r.status_code,200)
        self.assertIn(b"Scheduled lesson keys,1",r.content)
        self.assertNotIn(b"FICTIONAL001",r.content)
        self.assertNotIn(b"FictionalPupil",r.content)
        self.assertIn("no-store",r["Cache-Control"])
        r=self.client.post(self.path,{**p,"format":"pdf"})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r["Content-Type"],"application/pdf")
        pdf=" ".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
        self.assertIn("Scheduled lesson keys",pdf)
        self.assertNotIn("FictionalPupil",pdf)
        self.assertEqual(AccessAudit.objects.filter(action="leadership_report_export").count(),2)
        g.expires_at=timezone.now()-timedelta(seconds=1)
        g.save()
        self.assertEqual(self.client.post(self.path,p).status_code,403)
        c=Client(enforce_csrf_checks=True)
        c.force_login(self.leader)
        self.assertEqual(c.post(self.path,p).status_code,403)

    def test_attendance_submission_invalidates_review_digest(self):
        self.report_grant("year","7",["report_attendance","export_attendance"])
        r=self.client.get(self.path,self.params())
        p=self.params(digest=r.context["digest"],confirm="yes",format="csv")
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post(self.url,test_live_foundation.LiveFoundationTests.payload(self,"submit")).status_code,302)
        self.client.force_login(self.leader)
        self.assertEqual(self.client.post(self.path,p).status_code,409)
        r=self.client.get(self.path,self.params())
        self.assertEqual(dict(r.context["data"]["rows"])["Verified submitted rolls"],1)

    def test_workforce_and_movement_aggregates(self):
        self.report_grant("year","7",["report_movements","report_workforce"])
        d=MovementDestination.objects.create(name="Fictional desk",created_by=self.admin)
        now=timezone.now()
        for student,actor,code in [(self.student,self.teacher,"ENG7"),(self.outside,self.other,"SCI8")]:
            StudentMovement.objects.create(publication=self.pub,student=student,issuer=actor,destination=d,
                destination_name=d.name,requires_reception=False,lesson_date=self.day,class_code=code,
                period="P1",start="09:00",end="10:00",departed_at=now-timedelta(minutes=20),due_at=now-timedelta(minutes=10))
            WorkforceEntry.objects.create(publication=self.pub,day=self.day,kind="absence",staff=actor,created_by=self.admin)
        r=self.client.get(self.path,self.params(domain="movements"))
        self.assertEqual(dict(r.context["data"]["rows"])["Recorded departures"],1)
        self.assertEqual(dict(r.context["data"]["rows"])["Currently overdue from selected dates"],1)
        r=self.client.get(self.path,self.params(domain="workforce"))
        rows=dict(r.context["data"]["rows"])
        self.assertEqual(rows["Lessons affected by recorded unavailability"],1)
        self.assertNotIn("Full-day unavailability records",rows)
        self.assertNotContains(r,"fictional-teacher")

    def test_support_suppression_fixed_week_and_source_gate(self):
        self.report_grant("school","",["report_support","export_support"])
        start=self.day-timedelta(days=self.day.weekday()+7)
        end=start+timedelta(days=6)
        self.pub.starts=start
        self.pub.ends=self.day
        self.pub.snapshot["calendar"]["dates"] += [(start+timedelta(days=i)).isoformat() for i in range(5)]
        self.pub.save()
        t=SupportTask.objects.create(publication=self.pub,student=self.student,class_code="ENG7",
            requested_by=self.teacher,assigned_to=self.other,category="practice",due_on=end)
        from datetime import datetime,time
        SupportTask.objects.filter(pk=t.pk).update(created_at=timezone.make_aware(datetime.combine(start,time(12))))
        p=self.params(domain="support",scope="school",value="",start=start.isoformat(),end=end.isoformat())
        r=self.client.get(self.path,p)
        self.assertEqual(dict(r.context["data"]["rows"])["Students with educational tasks"],"Suppressed")
        self.assertEqual(dict(r.context["data"]["rows"])["Students with educational referrals"],"Suppressed")
        self.assertNotContains(r,"FictionalPupil")
        self.assertEqual(self.client.get(self.path,{**p,"start":(start+timedelta(days=1)).isoformat()}).status_code,400)
        self.pub.active=False
        self.pub.save()
        self.assertContains(self.client.get(self.path,p),"No current source-ready")
        self.assertEqual(csv_cell(" =1+1"),"' =1+1")
