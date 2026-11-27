"""Fictional leadership dashboard and workforce planner acceptance."""
from datetime import timedelta
from django.test import TestCase,override_settings
from django.contrib.auth.models import User
from django.utils import timezone
from . import test_reporting,test_workforce,test_live_foundation
from .models import StaffAccessGrant,WorkforceEntry,ReliefAttendanceAssignment
from .workforce_service import coverage

@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True,SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False)
class LeadershipExperienceTests(TestCase):
    def setUp(self):
        test_reporting.ReportingTests.setUp(self)
        self.overview="/live/leadership/"

    def report_grant(self,scope,value,caps):
        return test_reporting.ReportingTests.report_grant(self,scope,value,caps)

    def test_dashboard_requires_exact_domain_and_scope(self):
        self.assertEqual(self.client.get(self.overview).status_code,403)
        self.report_grant("year","7",["report_attendance"])
        self.report_grant("school","",["report_workforce"])
        r=self.client.get(self.overview,{"domain":"attendance","scope":"year","value":"7",
            "start":self.day.isoformat(),"end":self.day.isoformat()})
        self.assertContains(r,"Year: 7")
        self.assertEqual(r.context["leadership"]["completion"],0)
        self.assertEqual(dict((m["label"],m["value"]) for m in r.context["leadership"]["metrics"])["Scheduled lesson keys"],1)
        self.assertNotContains(r,"FictionalPupil")
        self.assertNotContains(r,"OtherPupil")
        self.assertNotContains(r,"Export CSV")
        self.assertEqual(self.client.get(self.overview,{"domain":"attendance","scope":"school"}).status_code,403)
        self.assertEqual(self.client.get(self.overview,{"domain":"workforce","scope":"year","value":"7"}).status_code,403)
        self.assertEqual(self.client.get("/live/attendance/").status_code,403)
        self.assertEqual(self.client.get("/live/workforce/").status_code,403)
        self.assertContains(self.client.get("/live/"),"Leadership dashboards")
        self.assertEqual(self.client.post(self.overview,{}).status_code,405)

    def test_completion_updates_after_certification_and_scope_expiry(self):
        grant=self.report_grant("faculty","English",["report_attendance"])
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post(self.url,test_live_foundation.LiveFoundationTests.payload(self,"submit")).status_code,302)
        self.client.force_login(self.leader)
        r=self.client.get(self.overview)
        self.assertEqual(r.context["leadership"]["completion"],100)
        self.assertContains(r,"Not student attendance percentage")
        grant.expires_at=timezone.now()-timedelta(seconds=1);grant.save(update_fields=["expires_at"])
        self.assertEqual(self.client.get(self.overview).status_code,403)

    def test_year_scope_excludes_departed_student_and_source_unavailable(self):
        self.report_grant("year","7",["report_attendance"])
        self.student.left_on=self.day-timedelta(days=1);self.student.save(update_fields=["left_on"])
        r=self.client.get(self.overview)
        self.assertEqual(dict((m["label"],m["value"]) for m in r.context["leadership"]["metrics"])["Scheduled lesson keys"],0)
        self.assertIsNone(r.context["leadership"]["completion"])
        self.pub.active=False;self.pub.save(update_fields=["active"])
        r=self.client.get(self.overview)
        self.assertContains(r,"Unavailable is not zero")
        self.assertEqual(r.context["leadership"]["metrics"],[])
        self.assertEqual(self.client.get(self.overview,{"start":"bad"}).status_code,400)

@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True,SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False)
class OperationsExperienceTests(TestCase):
    def setUp(self):
        test_workforce.WorkforceTests.setUp(self)

    def create(self,kind,**kw):
        return test_workforce.WorkforceTests.create(self,kind,**kw)

    def test_candidate_preview_and_conflicts(self):
        query={"lesson":"ENG7|P1|09:00","date":self.day.isoformat()}
        r=self.client.get(self.relief,query)
        self.assertEqual(r.context["candidates"],[])
        test_workforce.WorkforceTests.free_other(self)
        r=self.client.get(self.relief,query)
        self.assertEqual([x["pk"] for x in r.context["candidates"]],[self.other.pk])
        self.assertContains(r,"verify suitability")
        self.assertEqual(self.create("duty",staff=self.other.pk,start="09:00",end="10:00",location="Fictional courtyard").status_code,302)
        self.assertEqual(self.client.get(self.relief,query).context["candidates"],[])
        self.client.force_login(self.monitor)
        self.assertEqual(self.client.get(self.relief,query).status_code,403)

    def test_workforce_tabs_and_write_boundary(self):
        self.assertEqual(self.create("absence",staff=self.teacher.pk).status_code,302)
        self.assertEqual(self.create("duty",staff=self.other.pk,start="10:00",end="10:30",location="Fictional courtyard").status_code,302)
        r=self.client.get(self.board,{"view":"absence"})
        self.assertEqual([e.kind for e in r.context["entries"]],["absence"])
        r=self.client.get(self.board,{"view":"duty"})
        self.assertEqual([e.kind for e in r.context["entries"]],["duty"])
        self.assertEqual(r.context["current_counts"]["absence"],1)
        self.assertEqual(self.client.get(self.board,{"view":"invalid"}).status_code,400)
        StaffAccessGrant.objects.create(user=self.monitor,role="Business Manager",scope="school",capabilities=["workforce_monitor"],granted_by=self.admin)
        self.client.force_login(self.monitor)
        self.assertContains(self.client.get(self.board,{"view":"absence"}),"Staff availability")
        self.assertNotContains(self.client.get(self.board),"Approve change")
        self.assertEqual(self.create("closure").status_code,403)

    def test_coverage_revalidates_original_binding(self):
        test_workforce.WorkforceTests.free_other(self)
        self.assertEqual(self.create("absence",staff=self.teacher.pk).status_code,302)
        self.assertEqual(self.client.post(self.relief,{"action":"assign","publication":str(self.pub.pk),
            "lesson":"ENG7|P1|09:00","teacher":self.other.pk}).status_code,302)
        self.assertTrue(coverage(self.pub,self.day)[0]["covered"])
        self.profile.timetable_link_verified=False;self.profile.save(update_fields=["timetable_link_verified"])
        self.assertFalse(coverage(self.pub,self.day)[0]["covered"])

    def test_attendance_script_not_inside_title(self):
        self.client.force_login(self.teacher)
        r=self.client.get(self.url)
        html=r.content.decode()
        self.assertIn("teacher-attendance.js",html)
        self.assertNotIn("teacher-attendance.js",html.split("</title>",1)[0])
        self.assertIn("rf-mark-select",html)


    def test_operational_summary_only_explicit_monitors(self):
        from .leadership_experience import operational_summary
        self.assertEqual(operational_summary(self.other,self.pub),[])
        self.client.force_login(self.monitor)
        self.assertEqual([s["label"] for s in operational_summary(self.monitor,self.pub)],["Attendance Overview"])
        r=self.client.get("/live/")
        self.assertContains(r,"Today's whole-school operational monitoring")
        self.assertNotContains(r,"FictionalPupil")
        self.assertNotContains(r,'data-rf-operations="Workforce Allocations"')
        self.assertEqual(self.client.get("/live/leadership/").status_code,403)
        g=StaffAccessGrant.objects.create(user=self.monitor,role="Business Manager",scope="school",
            capabilities=["workforce_monitor"],granted_by=self.admin)
        self.assertContains(self.client.get("/live/"),'data-rf-operations="Workforce Allocations"')
        g.delete()
        self.assertNotContains(self.client.get("/live/"),'data-rf-operations="Workforce Allocations"')
