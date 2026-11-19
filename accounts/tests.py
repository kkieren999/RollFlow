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
