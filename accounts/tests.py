from django.contrib.auth.models import Group, User
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from .models import SecurityEvent

@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class AuthenticationTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user("testteacher", password="Fictional-test-password-42")
        self.teacher.groups.add(Group.objects.get(name="Teacher"))
        self.admin = User.objects.create_superuser("testadmin", password="Fictional-admin-password-42")
    def test_unauthenticated_teacher_redirect(self):
        self.assertRedirects(self.client.get("/teacher/"), "/")
    def test_teacher_login_and_identity(self):
        response = self.client.post("/", {"username": "testteacher", "password": "Fictional-test-password-42"})
        self.assertRedirects(response, "/teacher/")
        self.assertContains(self.client.get("/teacher/"), "rollflow-server-identity")
        self.assertEqual(SecurityEvent.objects.filter(event="login").count(), 1)
    def test_admin_portal_separation(self):
        self.assertEqual(self.client.post("/admin-login/", {"username": "testteacher", "password": "Fictional-test-password-42"}).status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.client.force_login(self.teacher)
        self.assertRedirects(self.client.get("/admin/"), "/admin/login/?next=/admin/", fetch_redirect_response=False)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/teacher/").status_code, 403)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
    def test_weak_public_demo_credentials_not_valid(self):
        response = self.client.post("/", {"username": "teacher", "password": "teacher"})
        self.assertContains(response, "Incorrect username or password")
        self.assertNotIn("_auth_user_id", self.client.session)
    def test_logout_post_only(self):
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get("/logout/").status_code, 405)
        self.assertRedirects(self.client.post("/logout/"), "/")
        self.assertNotIn("_auth_user_id", self.client.session)
    def test_csrf(self):
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post("/", {"username": "testteacher", "password": "Fictional-test-password-42"}).status_code, 403)
    def test_disabled_teacher(self):
        self.teacher.is_active = False
        self.teacher.save()
        self.assertContains(self.client.post("/", {"username": "testteacher", "password": "Fictional-test-password-42"}), "Incorrect username or password")
    def test_login_throttled(self):
        for _ in range(10):
            self.assertEqual(self.client.post("/", {"username": "testteacher", "password": "wrong"}).status_code, 200)
        self.assertEqual(self.client.post("/", {"username": "testteacher", "password": "wrong"}).status_code, 429)


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class StaffManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("testadmin", password="Fictional-admin-password-42")
        self.teacher = User.objects.create_user("testteacher", password="Fictional-teacher-password-42")
        self.teacher.groups.add(Group.objects.get(name="Teacher"))
        self.client.force_login(self.admin)
    def details(self, **extra):
        return {"staff_id": "STF003", "username": "newteacher", "first_name": "Fictional", "last_name": "Example", "faculty": "Maths", "campus": "Test", "role": "teacher", "active": "on", "password": "Strong-example-passphrase-92", "password_confirm": "Strong-example-passphrase-92", **extra}
    def test_portal_role_and_redirect(self):
        self.client.logout()
        self.assertRedirects(self.client.get("/manage/"), "/admin-login/")
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get("/manage/staff/").status_code, 403)
        self.client.logout()
        self.assertRedirects(self.client.post("/admin-login/", {"username":"testadmin","password":"Fictional-admin-password-42"}), "/manage/")
    def test_create_staff_and_hash_password(self):
        self.assertRedirects(self.client.post("/manage/staff/add/", self.details()), "/manage/staff/")
        user = User.objects.get(username="newteacher")
        self.assertTrue(user.check_password("Strong-example-passphrase-92"))
        self.assertTrue(user.groups.filter(name="Teacher").exists())
        self.assertEqual(user.staff_profile.staff_id, "STF003")
        self.assertEqual(SecurityEvent.objects.filter(event="staff_created", subject="newteacher").count(), 1)
    def test_duplicate_and_weak_passwords(self):
        self.assertEqual(self.client.post("/manage/staff/add/", self.details(username="TESTTEACHER")).status_code, 200)
        self.assertEqual(self.client.post("/manage/staff/add/", self.details(password="teacher", password_confirm="teacher")).status_code, 200)
        self.assertFalse(User.objects.filter(username="newteacher").exists())
    def test_disable_and_self_protection(self):
        self.assertEqual(self.client.post(f"/manage/staff/{self.admin.pk}/status/", {"active":"0"}).status_code, 403)
        self.assertRedirects(self.client.post(f"/manage/staff/{self.teacher.pk}/status/", {"active":"0"}), "/manage/staff/")
        self.teacher.refresh_from_db()
        self.assertFalse(self.teacher.is_active)
    def test_password_reset(self):
        self.assertRedirects(self.client.post(f"/manage/staff/{self.teacher.pk}/reset/", {"password":"New-fictional-passphrase-82","password_confirm":"New-fictional-passphrase-82"}), "/manage/staff/")
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password("New-fictional-passphrase-82"))
    def test_csv_import_and_activation_guard(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        data = b"staff_id,username,first_name,last_name,faculty,campus\nSTF999,csvteacher,Sample,Teacher,Maths,Test\n"
        self.assertRedirects(self.client.post("/manage/staff/import/", {"csv": SimpleUploadedFile("staff.csv", data)}), "/manage/staff/")
        user = User.objects.get(username="csvteacher")
        self.assertFalse(user.is_active)
        self.assertFalse(user.has_usable_password())
        self.client.post(f"/manage/staff/{user.pk}/status/", {"active":"1"})
        user.refresh_from_db()
        self.assertFalse(user.is_active)
    def test_import_atomic_on_duplicate(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        data = b"staff_id,username,first_name,last_name,faculty,campus\nSTF991,freshstaff,Sample,Teacher,Maths,Test\nSTF992,testteacher,Sample,Teacher,Maths,Test\n"
        self.assertEqual(self.client.post("/manage/staff/import/", {"csv": SimpleUploadedFile("staff.csv", data)}).status_code, 200)
        self.assertFalse(User.objects.filter(username="freshstaff").exists())
    def test_mutations_require_csrf(self):
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.admin)
        self.assertEqual(c.post(f"/manage/staff/{self.teacher.pk}/status/", {"active":"0"}).status_code, 403)


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class StudentManagementTests(TestCase):
    def setUp(self):
        from .models import Student
        self.admin = User.objects.create_superuser("studentadmin", password="Fictional-admin-passphrase-64")
        self.teacher = User.objects.create_user("sampleteacher", password="Fictional-teacher-passphrase-65")
        self.teacher.groups.add(Group.objects.get(name="Teacher"))
        self.student = Student.objects.create(student_id="SAMPLE1", first_name="Fictional", last_name="Student", year_level=10)
        self.client.force_login(self.admin)

    def details(self, **extra):
        return {"student_id":"SAMPLE2", "first_name":"Example", "last_name":"Learner", "preferred_name":"", "year_level":"7", "home_group":"7A", "status":"active", "enrolled_on":"2026-01-27", "left_on":"", **extra}

    def test_student_directory_and_permissions(self):
        self.assertContains(self.client.get("/manage/students/"), "SAMPLE1")
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get("/manage/students/").status_code, 403)
        self.assertEqual(self.client.get(f"/manage/students/{self.student.pk}/").status_code, 403)
        self.assertEqual(self.client.post("/manage/students/add/", self.details()).status_code, 403)

    def test_create_and_stable_identifier(self):
        from .models import Student
        response = self.client.post("/manage/students/add/", self.details())
        record = Student.objects.get(student_id="SAMPLE2")
        self.assertRedirects(response, f"/manage/students/{record.pk}/")
        self.client.post(f"/manage/students/{record.pk}/edit/", self.details(student_id="CHANGED", year_level="8"))
        record.refresh_from_db()
        self.assertEqual(record.student_id, "SAMPLE2")
        self.assertEqual(record.year_level, 8)
        self.assertTrue(SecurityEvent.objects.filter(event="student_updated", subject="SAMPLE2").exists())

    def test_validation_and_leaving_dates(self):
        from .models import Student
        for bad in (self.details(student_id="sample1"), self.details(year_level="6"), self.details(status="left"), self.details(status="active", left_on="2026-02-01"), self.details(status="left", left_on="2025-01-01")):
            self.assertEqual(self.client.post("/manage/students/add/", bad).status_code, 200)
        self.assertEqual(Student.objects.count(), 1)
        self.client.post("/manage/students/add/", self.details(status="left", left_on="2026-11-01"))
        self.assertEqual(Student.objects.get(student_id="SAMPLE2").status, "left")

    def test_csv_atomic_duplicate_and_filter(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import Student
        header = b"student_id,first_name,last_name,preferred_name,year_level,home_group,status,enrolled_on,left_on\n"
        valid = b"SAMPLE3,Sample,Learner,,8,8A,active,2026-01-27,\n"
        duplicate = b"SAMPLE3,Another,Learner,,8,8A,active,,\n"
        self.assertEqual(self.client.post("/manage/students/import/", {"csv":SimpleUploadedFile("students.csv", header+valid+duplicate)}).status_code, 200)
        self.assertFalse(Student.objects.filter(student_id="SAMPLE3").exists())
        self.assertRedirects(self.client.post("/manage/students/import/", {"csv":SimpleUploadedFile("students.csv",header+valid)}), "/manage/students/")
        response = self.client.get("/manage/students/?year=8&group=8A")
        self.assertContains(response, "SAMPLE3")
        self.assertNotContains(response, "SAMPLE1")

    def test_photo_validation_and_protection(self):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import StudentPhoto
        pk = self.student.pk
        bad = SimpleUploadedFile("bad.png", b"not an image", content_type="image/png")
        self.assertEqual(self.client.post(f"/manage/students/{pk}/photo/upload/", {"photo":bad}).status_code, 200)
        self.assertFalse(StudentPhoto.objects.filter(student=self.student).exists())
        buffer = io.BytesIO()
        Image.new("RGB", (800, 1000), "green").save(buffer, format="PNG")
        good = SimpleUploadedFile("sample.png", buffer.getvalue(), content_type="image/png")
        self.assertRedirects(self.client.post(f"/manage/students/{pk}/photo/upload/", {"photo":good}), f"/manage/students/{pk}/")
        response = self.client.get(f"/manage/students/{pk}/photo/")
        self.assertEqual(response["Content-Type"], "image/jpeg")
        with Image.open(io.BytesIO(response.content)) as portrait:
            self.assertLessEqual(portrait.width, 480)
            self.assertLessEqual(portrait.height, 640)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.get(f"/manage/students/{pk}/photo/").status_code, 403)
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.post(f"/manage/students/{pk}/photo/remove/"), f"/manage/students/{pk}/")
        self.assertFalse(StudentPhoto.objects.filter(student=self.student).exists())

    def test_mutation_csrf(self):
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.admin)
        self.assertEqual(c.post("/manage/students/add/", self.details()).status_code, 403)


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class TimetableManagementTests(TestCase):
    def setUp(self):
        from .models import SchoolClass, SchoolPeriod, Room, Student
        self.admin = User.objects.create_superuser("planadmin", password="Fictional-admin-passphrase-99")
        self.teacher = User.objects.create_user("planteacher", password="Fictional-teacher-passphrase-98")
        self.other = User.objects.create_user("otherteacher", password="Fictional-teacher-passphrase-97")
        group = Group.objects.get(name="Teacher")
        self.teacher.groups.add(group)
        self.other.groups.add(group)
        self.klass = SchoolClass.objects.create(code="DEMO101",name="Mathematics",subject="Maths",year_level=10,teacher=self.teacher)
        self.other_class = SchoolClass.objects.create(code="DEMO102",name="Science",subject="Science",year_level=10,teacher=self.other)
        self.room = Room.objects.create(code="M01")
        self.room2 = Room.objects.create(code="S01")
        self.period = SchoolPeriod.objects.get(code="1")
        self.student = Student.objects.create(student_id="PLAN1",first_name="Sample",last_name="Learner",year_level=10)
        self.client.force_login(self.admin)

    def slot(self, **extra):
        return {"school_class":self.klass.pk,"teacher":self.teacher.pk,"room":self.room.pk,"weekday":"1","period":self.period.pk,"active":"on",**extra}

    def test_class_directory_and_edit(self):
        self.assertContains(self.client.get("/manage/classes/"),"DEMO101")
        self.assertRedirects(self.client.post(f"/manage/classes/{self.klass.pk}/edit/",{"code":"CHANGED","name":"Maths A","subject":"Maths","year_level":"10","teacher":self.teacher.pk,"active":"on"}),f"/manage/classes/{self.klass.pk}/")
        self.klass.refresh_from_db()
        self.assertEqual(self.klass.code,"DEMO101")
        self.assertEqual(self.klass.name,"Maths A")

    def test_enrolment_history(self):
        from .models import ClassEnrolment
        url=f"/manage/classes/{self.klass.pk}/enrol/"
        data={"student":self.student.pk,"start_date":"2026-01-27"}
        self.assertRedirects(self.client.post(url,data),f"/manage/classes/{self.klass.pk}/")
        e=ClassEnrolment.objects.get(school_class=self.klass,student=self.student)
        self.assertEqual(self.client.post(url,data).status_code,200)
        self.assertRedirects(self.client.post(f"/manage/enrolments/{e.pk}/end/",{"end_date":"2026-06-30"}),f"/manage/classes/{self.klass.pk}/")
        self.assertRedirects(self.client.post(url,{"student":self.student.pk,"start_date":"2026-07-01"}),f"/manage/classes/{self.klass.pk}/")
        self.assertEqual(ClassEnrolment.objects.filter(student=self.student).count(),2)

    def test_conflicts_and_archive(self):
        from .models import TimetableSlot
        url="/manage/timetable/add/"
        self.assertRedirects(self.client.post(url,self.slot()),"/manage/timetable/")
        for data in (self.slot(school_class=self.other_class.pk,room=self.room2.pk),self.slot(school_class=self.other_class.pk,teacher=self.other.pk),self.slot(teacher=self.other.pk,room=self.room2.pk)):
            self.assertEqual(self.client.post(url,data).status_code,200)
        self.assertEqual(TimetableSlot.objects.count(),1)
        slot=TimetableSlot.objects.get()
        self.assertRedirects(self.client.post(f"/manage/timetable/{slot.pk}/archive/"),"/manage/timetable/")
        self.assertRedirects(self.client.post(url,self.slot()),"/manage/timetable/")
        self.assertEqual(TimetableSlot.objects.count(),2)

    def test_teacher_read_only_timetable(self):
        from .models import TimetableSlot
        TimetableSlot.objects.create(school_class=self.klass,teacher=self.teacher,room=self.room,weekday=1,period=self.period)
        TimetableSlot.objects.create(school_class=self.other_class,teacher=self.other,room=self.room2,weekday=1,period=self.period)
        self.client.force_login(self.teacher)
        response=self.client.get("/teacher/timetable/")
        self.assertContains(response,"DEMO101")
        self.assertNotContains(response,"DEMO102")
        self.assertEqual(self.client.get("/manage/classes/").status_code,403)
        self.assertEqual(self.client.post("/manage/timetable/add/",self.slot()).status_code,403)

    def test_csv_rejects_entire_import_on_unknown_reference(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import TimetableSlot
        data=b"class_code,teacher_username,room_code,weekday,period_code\nDEMO101,planteacher,M01,1,1\nUNKNOWN,planteacher,M01,2,1\n"
        self.assertEqual(self.client.post("/manage/timetable/import/",{"csv":SimpleUploadedFile("timetable.csv",data)}).status_code,200)
        self.assertEqual(TimetableSlot.objects.count(),0)

    def test_csrf_and_period_overlap(self):
        c=Client(enforce_csrf_checks=True)
        c.force_login(self.admin)
        self.assertEqual(c.post("/manage/timetable/add/",self.slot()).status_code,403)
        self.assertEqual(self.client.post("/manage/periods/add/",{"code":"EXTRA","label":"Extra","start_time":"09:30","end_time":"10:00"}).status_code,200)


    def test_school_period_remove_restore_and_history(self):
        from .models import SchoolPeriod, TimetableSlot
        self.assertRedirects(self.client.post("/manage/periods/add/",{"code":"EXTRA","label":"Extra","start_time":"15:15","end_time":"15:30"}),"/manage/timetable/")
        period=SchoolPeriod.objects.get(code="EXTRA")
        slot=TimetableSlot.objects.create(school_class=self.klass,teacher=self.teacher,room=self.room,weekday=1,period=period)
        url=f"/manage/periods/{period.pk}/remove/"
        self.assertContains(self.client.get(url),"1 scheduled lesson(s) will be archived")
        self.assertRedirects(self.client.post(url),"/manage/timetable/")
        period.refresh_from_db()
        self.assertFalse(period.active)
        self.assertTrue(TimetableSlot.objects.filter(pk=slot.pk,active=False).exists())
        self.assertEqual(self.client.post("/manage/timetable/add/",self.slot(period=period.pk)).status_code,200)
        self.assertRedirects(self.client.post(f"/manage/periods/{period.pk}/restore/"),"/manage/timetable/")
        period.refresh_from_db()
        self.assertTrue(period.active)
        slot.refresh_from_db()
        self.assertFalse(slot.active)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post(url).status_code,403)


    def test_master_timetable_access_filters_and_resources(self):
        from .models import TimetableSlot, SchoolPeriod
        slot=TimetableSlot.objects.create(school_class=self.klass,teacher=self.teacher,room=self.room,weekday=1,period=self.period)
        TimetableSlot.objects.create(school_class=self.other_class,teacher=self.other,room=self.room2,weekday=2,period=self.period)
        response=self.client.get("/manage/master/?day=1")
        self.assertContains(response,"Master Timetable")
        self.assertContains(response,"DEMO101")
        self.assertNotContains(response,"DEMO102")
        self.assertContains(response,"Staff clashes")
        self.assertContains(response,"Free resources")
        self.assertContains(self.client.get("/manage/master/?day=1&year=10&slot="+str(slot.pk)),"Edit lesson")
        self.assertNotContains(self.client.get("/manage/master/?day=1&q=nomatch"),"DEMO101")
        self.assertNotContains(self.client.get("/manage/master/?day=1&year=7"),"DEMO101")
        break_period=SchoolPeriod.objects.create(code="BREAKX",label="First break",start_time="08:50",end_time="09:00")
        self.assertContains(self.client.get("/manage/master/?day=1"),"First break")
        self.assertNotContains(self.client.get("/manage/master/?day=1&breaks=hide"),"<strong>First break</strong>",html=True)
        self.client.force_login(self.teacher)
        self.assertContains(self.client.get("/teacher/master/?day=2"),"DEMO102")
        self.assertNotContains(self.client.get("/teacher/master/?day=1&slot="+str(slot.pk)),"Edit lesson")
        self.assertEqual(self.client.get("/manage/master/").status_code,403)
        self.client.logout()
        self.assertRedirects(self.client.get("/teacher/master/"),"/")


@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class OneSchoolImportTests(TestCase):
    def setUp(self):
        from .models import StaffProfile
        self.admin = User.objects.create_superuser("importadmin", password="Fictional-import-password-52")
        self.teacher = User.objects.create_user("importteacher", password="Fictional-teacher-password-54")
        self.teacher.groups.add(Group.objects.get(name="Teacher"))
        StaffProfile.objects.create(user=self.teacher,staff_id="DEMO01")
        self.client.force_login(self.admin)

    def csv(self, extra=""):
        from .oneschool_csv import HEADER
        return (",".join(HEADER)+"\nDEMO071A,Mathematics,07,Mon,23/11/2026,PERIOD 1,08:50,10:00,DEMO01,,DEMOA,Example,Teacher,M01,Sample room\nDEMO071A,Mathematics,07,Tue,24/11/2026,PERIOD 1,09:00,10:10,DEMO02,,DEMOB,Example,Teacher,M02,Sample room\n"+extra).encode()

    def upload(self, data=None):
        from django.core.files.uploadedfile import SimpleUploadedFile
        return self.client.post("/manage/oneschool/",{"name":"Fictional term","fictional":"on","csv":SimpleUploadedFile("sample.csv", data if data is not None else self.csv())})

    def test_parser_variable_bell_times_and_shared_resources(self):
        from .oneschool_csv import parse
        days,summary,digest=parse(self.csv("DEMO072B,Science,07,Mon,23/11/2026,PERIOD 1,08:50,10:00,DEMO01,,DEMOA,Example,Teacher,M01,Sample room\n"))
        self.assertEqual(summary["lessons"],3)
        self.assertEqual(summary["warnings"]["staff_overlap"],1)
        self.assertEqual(summary["warnings"]["room_overlap"],1)
        self.assertEqual(days["2026-11-23"][0]["start"],"08:50")
        self.assertEqual(days["2026-11-24"][0]["start"],"09:00")
        self.assertNotIn("Staff_MISID",days["2026-11-23"][0])
        self.assertNotIn("Staff_Last_Name",days["2026-11-23"][0])

    def test_draft_deduplication_and_invalid_import(self):
        from .models import ImportedTimetable, ImportedTimetableDay
        self.assertEqual(self.upload().status_code,302)
        self.assertEqual(self.upload().status_code,302)
        self.assertEqual(ImportedTimetable.objects.count(),1)
        self.assertEqual(ImportedTimetableDay.objects.count(),2)
        self.assertEqual(self.upload(self.csv().replace(b"23/11/2026",b"24/11/2026")).status_code,200)
        self.assertEqual(ImportedTimetable.objects.count(),1)

    def test_publish_and_teacher_scope(self):
        from .models import ImportedTimetable
        self.upload()
        v=ImportedTimetable.objects.get()
        self.client.post(f"/manage/oneschool/{v.pk}/publish/")
        v.refresh_from_db()
        self.assertEqual(v.status,"draft")
        self.client.post(f"/manage/oneschool/{v.pk}/publish/",{"ack":"yes"})
        v.refresh_from_db()
        self.assertEqual(v.status,"published")
        self.assertContains(self.client.get("/manage/master/?date=2026-11-23"),"08:50")
        self.assertContains(self.client.get("/manage/master/?date=2026-11-24"),"09:00")
        self.client.force_login(self.teacher)
        self.assertContains(self.client.get("/teacher/timetable/?date=2026-11-23"),"DEMO071A")
        self.assertNotContains(self.client.get("/teacher/timetable/?date=2026-11-24"),"DEMO071A")
        self.assertContains(self.client.get("/teacher/master/?date=2026-11-24"),"DEMO071A")
        self.assertEqual(self.client.get("/manage/oneschool/").status_code,403)
        self.assertEqual(self.client.post(f"/manage/oneschool/{v.pk}/publish/",{"ack":"yes"}).status_code,403)

    def test_new_publish_retains_prior_snapshot(self):
        from .models import ImportedTimetable, ImportedTimetableDay
        self.upload()
        first=ImportedTimetable.objects.get()
        self.client.post(f"/manage/oneschool/{first.pk}/publish/",{"ack":"yes"})
        self.upload(self.csv().replace(b"M02",b"M03"))
        second=ImportedTimetable.objects.exclude(pk=first.pk).get()
        self.assertEqual(ImportedTimetable.objects.get(status="published"),first)
        self.client.post(f"/manage/oneschool/{second.pk}/publish/",{"ack":"yes"})
        first.refresh_from_db()
        self.assertEqual(first.status,"archived")
        self.assertEqual(ImportedTimetable.objects.get(status="published"),second)
        self.assertEqual(ImportedTimetableDay.objects.filter(version=first).count(),2)

    def test_direct_publish_disabled_in_demo(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import ImportedTimetable
        response=self.client.post("/manage/oneschool/",{"name":"Fictional","fictional":"on","publish_now":"yes","replace_ack":"yes","csv":SimpleUploadedFile("sample.csv",self.csv())})
        self.assertEqual(response.status_code,200)
        self.assertEqual(ImportedTimetable.objects.count(),0)

    @override_settings(ROLLFLOW_LIVE_TIMETABLE=True)
    def test_direct_publish_requires_authorisation_and_valid_csv(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import ImportedTimetable
        def upload(raw,ack="yes"):
            return self.client.post("/manage/oneschool/",{"name":"Fictional live example","fictional":"on","publish_now":"yes","replace_ack":ack,"csv":SimpleUploadedFile("sample.csv",raw)})
        self.assertEqual(upload(self.csv(),"").status_code,200)
        self.assertEqual(ImportedTimetable.objects.count(),0)
        self.assertEqual(upload(self.csv()).status_code,302)
        first=ImportedTimetable.objects.get(status="published")
        self.assertEqual(upload(self.csv().replace(b"23/11/2026",b"24/11/2026")).status_code,200)
        self.assertEqual(ImportedTimetable.objects.get(status="published"),first)
        self.assertEqual(upload(self.csv().replace(b"M02",b"M03")).status_code,302)
        first.refresh_from_db()
        self.assertEqual(first.status,"archived")
        self.assertEqual(ImportedTimetable.objects.filter(status="published").count(),1)
        self.client.force_login(self.teacher)
        self.assertRedirects(self.client.get("/teacher/"),"/teacher/timetable/",fetch_redirect_response=False)


    @override_settings(ROLLFLOW_LIVE_TIMETABLE=True)
    def test_operational_import_has_no_fictional_or_draft_controls(self):
        response=self.client.get("/manage/oneschool/")
        self.assertContains(response,"Import & publish timetable")
        self.assertNotContains(response,"Download fictional sample")
        self.assertNotContains(response,"Validate & create draft")
        self.assertEqual(self.client.get("/manage/oneschool/sample/").status_code,403)
        self.assertContains(self.client.get("/manage/master/"),"No timetable published")
        self.client.force_login(self.teacher)
        self.assertContains(self.client.get("/teacher/master/"),"No timetable published")
        self.assertContains(self.client.get("/teacher/timetable/"),"No timetable published")


    def test_published_dashboard_and_master_lookup(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from .models import ImportedTimetable
        self.upload(self.csv())
        v=ImportedTimetable.objects.get()
        self.client.post(f"/manage/oneschool/{v.pk}/publish/",{"ack":"yes"})
        dashboard=self.client.get("/manage/")
        self.assertContains(dashboard,"Imported allocations")
        self.assertContains(dashboard,"Imported rooms")
        self.assertContains(dashboard,v.name)
        response=self.client.get("/manage/master/?date=2026-11-23")
        self.assertContains(response,"Previous week")
        self.assertContains(response,"Next week")
        self.assertContains(response,"Compact view")
        self.assertContains(response,"DEMO071A")
        self.assertNotContains(self.client.get("/manage/master/?date=2026-11-23&room=UNKNOWN"),"DEMO071A")
        self.assertNotContains(self.client.get("/manage/master/?date=2026-11-23&staff=UNKNOWN"),"DEMO071A")
        self.assertContains(self.client.get("/manage/master/?date=2026-11-23&staff=DEMOA"),"DEMO071A")
        self.client.force_login(self.teacher)
        self.assertContains(self.client.get("/teacher/timetable/?date=2026-11-23&staff=DEMOB"),"DEMO071A")
        self.assertNotContains(self.client.get("/teacher/timetable/?date=2026-11-24&staff=DEMOB"),"DEMO071A")

    def test_remember_management_tab_and_safe_sort(self):
        self.client.get("/manage/timetable/?tab=periods")
        response=self.client.get("/manage/timetable/")
        self.assertEqual(response.context["tab"],"periods")
        self.assertEqual(self.client.get("/manage/staff/?sort=not_a_field").status_code,200)
        self.assertEqual(self.client.get("/manage/students/?sort=not_a_field").status_code,200)
        self.assertEqual(self.client.get("/manage/classes/?sort=not_a_field").status_code,200)


    def test_v344_identity_and_strict_quoting(self):
        from .oneschool_csv import parse
        source=self.csv()
        _,summary,digest=parse(source)
        self.assertEqual(summary["source_rows"],2)
        self.assertEqual(parse(source)[2],digest)
        self.assertNotEqual(parse(source.replace(b"DEMO071A",b"DEMO071B"))[2],digest)
        repeated=source+source.splitlines(keepends=True)[1]
        _,repeat_summary,repeat_digest=parse(repeated)
        self.assertEqual(repeat_summary["source_rows"],3)
        self.assertEqual(repeat_summary["lessons"],2)
        self.assertEqual(repeat_summary["warnings"]["duplicate_rows"],1)
        self.assertNotEqual(repeat_digest,digest)
        with self.assertRaises(ValueError):
            parse(source.replace(b"DEMO071A",b'DEMO"071A"'))
        with self.assertRaises(ValueError):
            parse(source.replace(b"DEMO071A",b'"DEMO071A"x'))
        with self.assertRaises(ValueError):
            parse(source.replace(b"23/11/2026",b"23/11/9999"))

    def test_v344_date_limits_and_visible_counts(self):
        from .models import ImportedTimetable
        self.upload(self.csv("DEMO072B,Science,07,Mon,23/11/2026,FIRST BREAK 1,10:00,10:15,DEMO03,,DEMOC,Example,Teacher,M03,Sample room\\n".replace("\\n","\n")))
        v=ImportedTimetable.objects.get()
        self.client.post(f"/manage/oneschool/{v.pk}/publish/",{"ack":"yes"})
        response=self.client.get("/manage/master/?date=2026-11-23&breaks=hide")
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.context["visible_count"],1)
        self.assertContains(response,"1 of 1 visible allocations match")
        self.assertEqual(self.client.get("/manage/master/?date=9999-12-31").status_code,200)
        self.assertEqual(self.client.get("/manage/master/?date=0001-01-01").status_code,200)
        self.assertEqual(self.client.get("/manage/master/?date=2099-12-31").status_code,200)
        self.assertContains(self.client.get("/manage/master/?date=2026-11-23&staff_id=DEMO01"),"DEMO071A")
        self.assertNotContains(self.client.get("/manage/master/?date=2026-11-23&staff_id=DEMO02"),"DEMO071A")

    def test_v344_coverage_message(self):
        from datetime import date
        from types import SimpleNamespace
        from .oneschool_views import coverage_message,shift_date
        v=SimpleNamespace(summary={"first_date":"2026-02-02","last_date":"2026-10-30"})
        self.assertIn("expired",coverage_message(v,date(2026,11,20)))
        self.assertIn("future",coverage_message(v,date(2026,1,1)))
        self.assertEqual(coverage_message(v,date(2026,3,1)),"")
        self.assertEqual(shift_date(date(2099,12,31),7),date(2099,12,31))



@override_settings(
    ROLLFLOW_LIVE_TIMETABLE=True,
    SECURE_SSL_REDIRECT=False,
    SESSION_COOKIE_SECURE=False,
    CSRF_COOKIE_SECURE=False,
)
class ConnectedTeacherPortalTests(TestCase):
    """Only a verified, administrator-maintained OneSchool identity may see a
    teacher's live personal timetable. The complete import stays admin-only.
    """

    def setUp(self):
        from datetime import date
        from .models import ImportedTimetable, ImportedTimetableDay, StaffProfile
        self.admin = User.objects.create_superuser(
            "connectedadmin", password="Fictional-admin-password-46"
        )
        group = Group.objects.get(name="Teacher")
        self.teacher = User.objects.create_user(
            "teachera", first_name="Teacher", last_name="A",
            password="Fictional-teacher-password-46",
        )
        self.teacher.groups.add(group)
        self.other = User.objects.create_user(
            "teacherb", password="Fictional-teacher-password-47",
        )
        self.other.groups.add(group)
        self.link = StaffProfile.objects.create(
            user=self.teacher, staff_id="TEACH01", timetable_link_verified=False
        )
        StaffProfile.objects.create(
            user=self.other, staff_id="TEACH02", timetable_link_verified=True
        )
        self.version = ImportedTimetable.objects.create(
            name="Fictional published term", digest="a" * 64,
            status="published", created_by=self.admin,
            summary={
                "first_date": "2026-11-23", "last_date": "2026-11-24",
                "lessons": 3, "days": 2,
            },
        )
        def row(code, staff_id, staff_code, start):
            return {
                "code": code, "subject": "Fictional mathematics",
                "year": 7, "period": "PERIOD 1",
                "start": start, "end": "10:00", "room": "R01",
                "room_name": "Example room", "staff_id": staff_id,
                "staff_code": staff_code,
            }
        ImportedTimetableDay.objects.create(
            version=self.version, date=date(2026, 11, 23),
            allocations=[
                row("MY-CLASS", "TEACH01", "SHARED-CODE", "08:50"),
                row("PRIVATE-OTHER-CLASS", "TEACH02", "SHARED-CODE", "08:50"),
                row("UNALLOCATED-CLASS", "", "SHARED-CODE", "08:50"),
            ],
        )
        ImportedTimetableDay.objects.create(
            version=self.version, date=date(2026, 11, 24),
            allocations=[row("OTHER-TUESDAY-CLASS", "TEACH02", "SHARED-CODE", "09:00")],
        )

    def test_anonymous_and_admin_cannot_open_personal_week(self):
        self.assertRedirects(self.client.get("/teacher/week/"), "/")
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get("/teacher/week/").status_code, 403)
        self.assertEqual(self.client.get("/teacher/timetable/").status_code, 403)
        self.client.force_login(self.teacher)
        self.assertEqual(self.client.post("/teacher/week/").status_code, 405)

    def test_unverified_link_cannot_display_imported_teaching(self):
        self.client.force_login(self.teacher)
        day = self.client.get("/teacher/timetable/?date=2026-11-23")
        week = self.client.get("/teacher/week/?date=2026-11-23")
        self.assertContains(day, "not been verified")
        self.assertNotContains(day, "MY-CLASS")
        self.assertContains(week, "not been verified")
        self.assertNotContains(week, "MY-CLASS")
        self.assertNotContains(week, "PRIVATE-OTHER-CLASS")

    def test_verified_teacher_sees_only_own_day_and_week(self):
        self.link.timetable_link_verified = True
        self.link.save(update_fields=["timetable_link_verified"])
        self.client.force_login(self.teacher)
        day = self.client.get(
            "/teacher/timetable/?date=2026-11-23&staff_id=TEACH02&staff=SHARED-CODE"
        )
        self.assertContains(day, "MY-CLASS")
        self.assertNotContains(day, "PRIVATE-OTHER-CLASS")
        self.assertNotContains(day, "UNALLOCATED-CLASS")
        week = self.client.get(
            "/teacher/week/?date=2026-11-23&staff_id=TEACH02&username=teacherb"
        )
        self.assertContains(week, "MY-CLASS")
        self.assertNotContains(week, "PRIVATE-OTHER-CLASS")
        self.assertNotContains(week, "UNALLOCATED-CLASS")
        self.assertNotContains(week, "OTHER-TUESDAY-CLASS")
        self.assertNotContains(week, "TEACH02")
        self.assertContains(week, "No assigned lessons on this day")
        self.assertContains(week, "My day")
        self.assertContains(week, "My week")
        self.assertNotContains(week, "Fictional master timetable")

    def test_other_teacher_can_only_see_their_own(self):
        self.client.force_login(self.other)
        response = self.client.get("/teacher/week/?date=2026-11-23")
        self.assertContains(response, "PRIVATE-OTHER-CLASS")
        self.assertContains(response, "OTHER-TUESDAY-CLASS")
        self.assertNotContains(response, "MY-CLASS")

    def test_live_master_route_cannot_disclose_school_wide_data(self):
        self.link.timetable_link_verified = True
        self.link.save(update_fields=["timetable_link_verified"])
        self.client.force_login(self.teacher)
        self.assertRedirects(
            self.client.get("/teacher/master/?date=2026-11-23"),
            "/teacher/timetable/", fetch_redirect_response=False,
        )
        self.client.force_login(self.admin)
        self.assertContains(
            self.client.get("/manage/master/?date=2026-11-23"),
            "PRIVATE-OTHER-CLASS",
        )

    def test_missing_mapping_and_ambiguous_mapping_fail_closed(self):
        from .models import StaffProfile
        self.client.force_login(self.teacher)
        self.link.staff_id = None
        self.link.timetable_link_verified = True
        self.link.save(update_fields=["staff_id", "timetable_link_verified"])
        self.assertContains(
            self.client.get("/teacher/week/?date=2026-11-23"),
            "no linked OneSchool staff ID",
        )
        self.link.staff_id = "TEACH01"
        self.link.save(update_fields=["staff_id"])
        # The database's unique index is case-sensitive; reject ambiguous
        # legacy IDs even when they differ only in case.
        extra = User.objects.create_user("duplicate", password="Fictional-password-73")
        StaffProfile.objects.create(
            user=extra, staff_id="teach01", timetable_link_verified=True
        )
        response = self.client.get("/teacher/week/?date=2026-11-23")
        self.assertContains(response, "ambiguous")
        self.assertNotContains(response, "MY-CLASS")

    def test_switching_publication_updates_week_immediately(self):
        from datetime import date
        from .models import ImportedTimetable, ImportedTimetableDay
        self.link.timetable_link_verified = True
        self.link.save(update_fields=["timetable_link_verified"])
        self.client.force_login(self.teacher)
        self.assertContains(self.client.get("/teacher/week/?date=2026-11-23"), "MY-CLASS")
        self.version.status = "archived"
        self.version.save(update_fields=["status"])
        latest = ImportedTimetable.objects.create(
            name="Replacement snapshot", digest="b" * 64,
            status="published", created_by=self.admin,
            summary={"first_date": "2026-11-23", "last_date": "2026-11-23"},
        )
        ImportedTimetableDay.objects.create(
            version=latest, date=date(2026, 11, 23),
            allocations=[
                {
                    "code": "REPLACEMENT-LESSON", "subject": "New fictional lesson",
                    "year": 8, "period": "PERIOD 2", "start": "11:00",
                    "end": "12:00", "room": "R02", "staff_id": "TEACH01",
                    "staff_code": "SHARED-CODE",
                }
            ],
        )
        response = self.client.get("/teacher/week/?date=2026-11-23")
        self.assertContains(response, "REPLACEMENT-LESSON")
        self.assertNotContains(response, "MY-CLASS")
        self.assertNotContains(response, "PRIVATE-OTHER-CLASS")

    def test_invalid_week_date_is_bounded(self):
        self.link.timetable_link_verified = True
        self.link.save(update_fields=["timetable_link_verified"])
        self.client.force_login(self.teacher)
        for value in ("invalid", "0001-01-01", "9999-12-31"):
            with self.subTest(date=value):
                self.assertEqual(
                    self.client.get("/teacher/week/", {"date": value}).status_code,
                    200,
                )

    def test_admin_verification_is_explicit_and_revoked_on_id_change(self):
        from .models import SecurityEvent
        self.client.force_login(self.admin)
        endpoint = f"/manage/staff/{self.teacher.pk}/edit/"
        def save(staff_id, verified=False):
            return self.client.post(endpoint, {
                "staff_id": staff_id,
                "username": self.teacher.username,
                "first_name": "Teacher", "last_name": "A",
                "faculty": "Maths", "campus": "Test",
                "role": "teacher", "active": "on",
                **({"verify_timetable_link": "on"} if verified else {}),
            })
        self.assertEqual(save("TEACH01").status_code, 302)
        self.link.refresh_from_db()
        self.assertFalse(self.link.timetable_link_verified)
        self.assertContains(self.client.get("/manage/staff/"), "OneSchool timetable link: unverified")
        self.assertEqual(save("TEACH01", verified=True).status_code, 302)
        self.link.refresh_from_db()
        self.assertTrue(self.link.timetable_link_verified)
        self.assertContains(self.client.get("/manage/staff/"), "OneSchool timetable link: verified")
        self.assertTrue(
            SecurityEvent.objects.filter(
                actor=self.admin, subject="teachera", event="staff_link_verified"
            ).exists()
        )
        self.assertEqual(save("TEACH01").status_code, 302)
        self.link.refresh_from_db()
        self.assertTrue(self.link.timetable_link_verified)
        self.assertEqual(save("NEWSTAFF").status_code, 302)
        self.link.refresh_from_db()
        self.assertFalse(self.link.timetable_link_verified)
        self.assertEqual(self.link.staff_id, "NEWSTAFF")
        self.client.force_login(self.teacher)
        response = self.client.get("/teacher/week/?date=2026-11-23")
        self.assertContains(response, "not been verified")
        self.assertNotContains(response, "MY-CLASS")
        self.assertEqual(save("TEACH01", verified=True).status_code, 403)
