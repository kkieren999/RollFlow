from datetime import timedelta
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from django.urls import reverse
from .models import AccessAudit, RoleTemplate, StaffAccessGrant, StaffProfile, Student, ConnectedSchoolPublication
from .school_access import grants_for


@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True, SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class SecurityFoundationTests(TestCase):
    def setUp(self):
        self.admin=User.objects.create_superuser("v4-admin",password="Fictional-Admin-42!")
        self.user=User.objects.create_user("v4-staff",password="Fictional-Staff-42!")
        self.other=User.objects.create_user("v4-other",password="Fictional-Other-42!")
        StaffProfile.objects.create(user=self.user,faculty="English")
        Student.objects.create(student_id="V4S7",first_name="AllowedPupil",last_name="Example",year_level=7)
        Student.objects.create(student_id="V4S8",first_name="DeniedPupil",last_name="Example",year_level=8)
        self.client.force_login(self.admin)
        self.url=reverse("school-access-manage")
        self.staff=Client()
        self.staff.force_login(self.user)

    def grant(self, **kw):
        defaults=dict(user=self.user,role="Head of Year",scope="year",scope_value="7",
                      capabilities=["students"],granted_by=self.admin)
        return StaffAccessGrant.objects.create(**{**defaults,**kw})

    def test_reusable_template_snapshot_and_archive(self):
        self.assertRedirects(self.client.post("/manage/security/templates/",{
            "action":"create","name":"Year review v1","scope":"year","capabilities":["students"]}),
            "/manage/security/templates/")
        t=RoleTemplate.objects.get()
        payload={"action":"grant","user":self.user.pk,"role":"Head of Year","scope":"year",
                 "scope_value":"7","template":t.pk}
        self.assertRedirects(self.client.post(self.url,payload),self.url)
        self.assertEqual(StaffAccessGrant.objects.get().capabilities,["students"])
        self.assertContains(self.staff.get("/workspace/students/"),"AllowedPupil")
        self.assertNotContains(self.staff.get("/workspace/students/"),"DeniedPupil")
        self.assertEqual(self.staff.get("/workspace/staff/").status_code,403)
        self.assertContains(self.client.get(reverse("security-effective",args=[self.user.pk])),"Year review v1")
        self.assertRedirects(self.client.post("/manage/security/templates/",{"action":"archive","template":t.pk}),"/manage/security/templates/")
        self.assertContains(self.staff.get("/workspace/students/"),"AllowedPupil")
        self.assertEqual(self.client.post(self.url,payload).status_code,200)
        self.assertEqual(StaffAccessGrant.objects.count(),1)
        self.assertTrue(AccessAudit.objects.filter(action="template_archived").exists())
        self.assertEqual(AccessAudit.objects.get(action="grant_created").target_id,self.user.pk)

    def test_time_bounds_enforced_in_existing_session(self):
        g=self.grant(starts_at=timezone.now()+timedelta(hours=1),expires_at=timezone.now()+timedelta(hours=2))
        self.assertEqual(self.staff.get("/workspace/students/").status_code,403)
        g.starts_at=timezone.now()-timedelta(minutes=1)
        g.save()
        self.assertContains(self.staff.get("/workspace/students/"),"AllowedPupil")
        g.expires_at=timezone.now()-timedelta(seconds=1)
        g.save()
        self.assertEqual(self.staff.get("/workspace/students/").status_code,403)
        self.assertEqual(grants_for(self.user),[])

    def test_invalid_scope_forgery_and_no_admin_escalation(self):
        t=RoleTemplate.objects.create(name="English directory",scope="faculty",capabilities=["staff"],created_by=self.admin)
        p={"action":"grant","user":self.user.pk,"role":"Custom","scope":"school","scope_value":"",
           "template":t.pk,"capabilities":["students"]}
        self.assertEqual(self.client.post(self.url,p).status_code,200)
        self.assertEqual(StaffAccessGrant.objects.count(),0)
        self.grant(role="System Administrator")
        for url in ["/manage/","/manage/security/templates/","/manage/security/history/",self.url,reverse("security-effective",args=[self.other.pk])]:
            self.assertEqual(self.staff.get(url).status_code,403)
        self.assertEqual(self.staff.post(self.url,p).status_code,403)
        self.assertEqual(self.staff.post("/manage/security/templates/",{"action":"create","name":"Escalate","scope":"school","capabilities":["students"]}).status_code,403)
        self.assertEqual(self.staff.get("/live/attendance/").status_code,403)
        self.assertFalse(User.objects.get(pk=self.user.pk).is_superuser)

    def test_revoke_audit_and_deactivation_revokes_grants(self):
        g=self.grant()
        self.assertRedirects(self.client.post(self.url,{"action":"revoke","grant_id":g.pk}),self.url)
        self.assertEqual(self.staff.get("/workspace/students/").status_code,403)
        self.assertEqual(AccessAudit.objects.get(action="grant_revoked").before["scope_value"],"7")
        self.grant()
        url=reverse("management-staff-status",args=[self.user.pk])
        self.client.post(url,{"active":"0"})
        self.assertFalse(User.objects.get(pk=self.user.pk).is_active)
        self.assertFalse(StaffAccessGrant.objects.filter(user=self.user).exists())
        self.assertEqual(self.staff.get("/workspace/students/").status_code,302)
        self.client.post(url,{"active":"1"})
        self.staff.force_login(self.user)
        self.assertEqual(self.staff.get("/workspace/students/").status_code,403)
        self.assertTrue(AccessAudit.objects.filter(action="grant_revoked_on_deactivation",target=self.user).exists())
        self.assertEqual(self.client.post(reverse("management-staff-status",args=[self.admin.pk]),{"active":"0"}).status_code,403)

    def test_password_change_requires_old_password_and_revokes_other_sessions(self):
        self.grant()
        second=Client()
        second.force_login(self.user)
        p={"old_password":"wrong","new_password1":"A-new-fictional-42-password!","new_password2":"A-new-fictional-42-password!"}
        self.assertEqual(self.staff.post("/account/password/",p).status_code,200)
        self.assertTrue(User.objects.get(pk=self.user.pk).check_password("Fictional-Staff-42!"))
        p["old_password"]="Fictional-Staff-42!"
        self.assertEqual(self.staff.post("/account/password/",p).status_code,302)
        self.assertTrue(User.objects.get(pk=self.user.pk).check_password(p["new_password1"]))
        self.assertContains(self.staff.get("/workspace/students/"),"AllowedPupil")
        self.assertEqual(second.get("/workspace/students/").status_code,302)
        e=AccessAudit.objects.get(action="self_password_changed")
        self.assertEqual(e.before,{})
        self.assertEqual(e.after,{})

    def test_csrf_required_for_mutations_and_raw_admin_read_only(self):
        c=Client(enforce_csrf_checks=True)
        c.force_login(self.admin)
        self.assertEqual(c.post("/manage/security/templates/",{"action":"create"}).status_code,403)
        self.assertEqual(c.post(self.url,{"action":"revoke","grant_id":1}).status_code,403)
        self.assertEqual(self.client.post("/admin/auth/user/add/",{"username":"bypass"}).status_code,403)
        self.assertFalse(User.objects.filter(username="bypass").exists())

    def test_class_grant_is_metadata_only_and_bound_to_publication(self):
        day=timezone.localdate()
        pub=ConnectedSchoolPublication.objects.create(name="Fictional",starts=day,ends=day,
            published_by=self.admin,digest="b"*64,snapshot={"source":"dated","calendar":{"dates":[day.isoformat()]},
                "classes":[{"code":"ENG7","name":"English7","students":[]},{"code":"SCI8","name":"Science8","students":[]}],
                "slots":[]})
        p={"action":"grant","user":self.user.pk,"role":"Relief Teacher","scope":"class",
           "scope_value":"ENG7","capabilities":["published_classes"]}
        self.assertEqual(self.client.post(self.url,p).status_code,200)
        self.assertFalse(StaffAccessGrant.objects.exists())
        p["expires_at"]=(timezone.now()+timedelta(hours=1)).isoformat()
        self.assertRedirects(self.client.post(self.url,p),self.url)
        self.assertContains(self.staff.get("/workspace/published_classes/"),"English7")
        self.assertNotContains(self.staff.get("/workspace/published_classes/"),"Science8")
        self.assertEqual(self.staff.get("/live/roll/?code=ENG7&period=P1&start=09:00").status_code,403)
        pub.active=False
        pub.save()
        self.assertEqual(self.staff.get("/workspace/published_classes/").status_code,403)
