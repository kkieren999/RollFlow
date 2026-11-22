"""Fictional-only tests of calendar evidence and imported account security."""
import io
from unittest.mock import patch
from django.contrib.auth.models import Group, User
from django.test import TestCase, SimpleTestCase, Client, override_settings
from .automated_setup import page_details, inspect_pdf_setup, suggested_csv
from .models import OneSchoolArchiveBatch, PendingTeacherSetup, StaffProfile, ConnectedStaffMapping

DAYS=["Monday","Tuesday","Wednesday","Thursday","Friday"]

def layout(code="FAKE01", monday="8:50-10:00"):
    def row(label, cells):
        return label.ljust(15)+''.join(s.ljust(30) for s in cells)
    return "\n".join([
        "Fictional High School","Staff Timetable - Fictional Term",
        code+" - Example, Teacher",row("",DAYS),
        row("P1",[monday]+["9:00-10:10"]*4),
        row("P2",["11:00-12:10"]+["10:10-11:20"]*4),
        row("P3",["12:10-1:20"]+["12:05-1:15"]*4),
        row("P4",["1:50-2:55"]+["1:45-2:55"]*4),
        row("HCG",[""]+["8:50-9:00"]*4),
        "Legend:",
    ])

class FakePage:
    def __init__(self, code, start="8:50-10:00", missing=False):
        self.code,self.start,self.missing=code,start,missing
    def extract_text(self, **kwargs):
        if kwargs:
            return "unstructured" if self.missing else layout(self.code,self.start)
        return self.code+"\n - \nExample\n, Teacher\nRef-TTStaffTimetable-V5.36-1000-123456- Sort-S"

class CalendarExtractionTests(SimpleTestCase):
    def test_grid_preserves_monday_and_school_day_clock(self):
        person,slots=page_details(layout(),"FAKE01\n-\nExample\nTeacher")
        self.assertEqual(person,{"code":"FAKE01","first":"Teacher","last":"Example"})
        self.assertEqual(slots[1,"P1"],("08:50","10:00"))
        self.assertEqual(slots[5,"P4"],("13:45","14:55"))
        self.assertEqual(slots[2,"HCG"],("08:50","09:00"))
        self.assertNotIn((1,"HCG"),slots)
    @patch("accounts.automated_setup.PdfReader")
    def test_consensus_missing_and_conflicting_time(self,reader):
        reader.return_value.is_encrypted=False
        reader.return_value.pages=[FakePage("FAKE01"),FakePage("FAKE02"),FakePage("FAKE03",missing=True)]
        result=inspect_pdf_setup(b"fictional","123456")
        self.assertEqual(len(result["people"]),2)
        self.assertEqual(result["missing_names"],[3])
        self.assertEqual(result["missing_grids"],[3])
        self.assertEqual(result["periods"][0]["votes"],2)
        self.assertIn("Monday,4,13:50,14:55",suggested_csv(result))
        reader.return_value.pages=[FakePage("FAKE01"),FakePage("FAKE02","8:55-10:00")]
        result=inspect_pdf_setup(b"fictional","123456")
        self.assertTrue(result["periods"][0]["conflict"])
        self.assertEqual(result["periods"][0]["start"],"")
        with self.assertRaisesRegex(ValueError,"version"):
            inspect_pdf_setup(b"fictional","999999")

@override_settings(SECURE_SSL_REDIRECT=False,SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False)
class PendingTeacherTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_superuser("fictional-admin",password="Fictional-Password-219!")
        self.batch=OneSchoolArchiveBatch.objects.create(kind="staff_pdf",label="Fictional PDF",created_by=self.admin,status="applied")
        self.candidate=dict(people=[
            dict(code="FAKE01",first="Teacher",last="Example",slots=2),
            dict(code="FAKE02",first="Teacher",last="Practice",slots=4)
        ],periods=[],extras=[],missing_names=[],missing_grids=[],conflicting_codes=[],unrecognised_teaching_codes=[],legend_disagreements=0,pages=2,term_hint="Fictional",source_batch=self.batch.pk,digest="reviewed")
        mocked=patch("accounts.automated_views.setup_candidate",return_value=self.candidate)
        mocked.start()
        self.addCleanup(mocked.stop)
        self.client.force_login(self.admin)
    def action(self,action,selected=None,**kwargs):
        return self.client.post("/manage/connected/setup/",dict(action=action,selected=selected or ["FAKE01"],confirm="yes",digest="reviewed",**kwargs))
    def test_prepare_disabled_and_activation_requires_individual_verified_id(self):
        self.assertContains(self.client.get("/manage/connected/setup/"),"Automated School Setup")
        self.assertEqual(self.action("prepare",["FAKE01","FAKE02"]).status_code,302)
        self.assertEqual(PendingTeacherSetup.objects.count(),2)
        p=PendingTeacherSetup.objects.get(staff_code="FAKE01")
        self.assertFalse(p.user.is_active)
        self.assertFalse(p.user.has_usable_password())
        self.assertFalse(p.user.staff_profile.timetable_link_verified)
        self.assertIsNone(p.user.staff_profile.staff_id)
        self.action("prepare")
        self.assertEqual(PendingTeacherSetup.objects.count(),2)
        self.action("activate",id_FAKE01="OFFICIAL01",verify_FAKE01="yes")
        p.user.refresh_from_db()
        self.assertFalse(p.user.is_active)
        p.user.set_password("Fictional-Password-123!")
        p.user.save(update_fields=["password"])
        self.client.post(f"/manage/staff/{p.user_id}/status/",{"active":"1"})
        p.user.refresh_from_db()
        self.assertFalse(p.user.is_active)
        self.assertRedirects(self.client.get(f"/manage/staff/{p.user_id}/edit/"),"/manage/connected/setup/",fetch_redirect_response=False)
        self.action("activate",id_FAKE01="OFFICIAL01")
        p.user.refresh_from_db()
        self.assertFalse(p.user.is_active)
        self.action("activate",id_FAKE01="OFFICIAL01",verify_FAKE01="yes")
        p.user.refresh_from_db()
        p.refresh_from_db()
        self.assertTrue(p.user.is_active)
        self.assertIsNotNone(p.activated_at)
        self.assertEqual(p.user.staff_profile.staff_id,"OFFICIAL01")
        self.assertEqual(ConnectedStaffMapping.objects.get(staff_code="FAKE01").verified_staff_id,"OFFICIAL01")
        self.assertFalse(PendingTeacherSetup.objects.get(staff_code="FAKE02").user.is_active)
    def test_conflict_is_atomic_and_existing_account_untouched(self):
        existing=User.objects.create_user("rf-fake02",password="Fictional-existing-123!")
        self.action("prepare",["FAKE01","FAKE02"])
        self.assertFalse(PendingTeacherSetup.objects.exists())
        existing.refresh_from_db()
        self.assertTrue(existing.is_active)
        self.assertTrue(existing.check_password("Fictional-existing-123!"))
        self.action("prepare")
        p=PendingTeacherSetup.objects.get()
        p.user.set_password("Fictional-password-123!")
        p.user.save(update_fields=["password"])
        StaffProfile.objects.create(user=existing,staff_id="OFFICIAL01")
        self.action("activate",id_FAKE01="OFFICIAL01",verify_FAKE01="yes")
        p.user.refresh_from_db()
        self.assertFalse(p.user.is_active)
        self.assertFalse(ConnectedStaffMapping.objects.exists())
    def test_stale_review_teacher_and_csrf_denied(self):
        res=self.client.post("/manage/connected/setup/",{"action":"prepare","selected":"FAKE01","confirm":"yes","digest":"stale"})
        self.assertEqual(res.status_code,400)
        self.assertFalse(PendingTeacherSetup.objects.exists())
        secure=Client(enforce_csrf_checks=True)
        secure.force_login(self.admin)
        self.assertEqual(secure.post("/manage/connected/setup/").status_code,403)
        teacher=User.objects.create_user("fictional-teacher",password="Fictional-password-123!")
        teacher.groups.add(Group.objects.get(name="Teacher"))
        self.client.force_login(teacher)
        self.assertEqual(self.client.get("/manage/connected/setup/").status_code,403)
        self.assertEqual(self.action("prepare").status_code,403)
