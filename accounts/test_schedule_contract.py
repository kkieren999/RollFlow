from datetime import date, timedelta
from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.utils import timezone
from .models import ConnectedSchoolPublication, ConnectedStaffMapping, StaffProfile
from .schedule_contract import project_days

class ScheduleProjectionTests(TestCase):
    def test_projection_allowlists_fields(self):
        d=date(2026,11,26)
        result=project_days([{"date":d,"rows":[{"code":"FAKE7","name":"Maths <script>","period_label":"P1","start":"09:00","end":"10:00","room":"A","staff":"PRIVATE","student_id":"PRIVATE"}]}])
        row=result["days"][0]["lessons"][0]
        self.assertEqual(set(row),{"date","code","title","period","time","room","assignment"})
        self.assertEqual(row["date"],"2026-11-26")
        self.assertEqual(result["version"],1)

@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class SharedConnectedScheduleTests(TestCase):
    def test_scoped_server_snapshot_and_revocation(self):
        admin=User.objects.create_superuser("fake-admin-contract",password="Fictional123!")
        teacher=User.objects.create_user("fake-teacher-contract",password="Fictional123!")
        teacher.groups.add(Group.objects.get(name="Teacher"))
        profile=StaffProfile.objects.create(user=teacher,staff_id="FAKE-A",timetable_link_verified=True)
        mapping=ConnectedStaffMapping.objects.create(profile=profile,staff_code="CODE-A",verified_staff_id="FAKE-A",verified_by=admin)
        today=timezone.localdate()
        monday=today-timedelta(days=today.weekday())
        snap={"calendar":{"times":{f"{day}:1":["09:00","10:00"] for day in range(1,6)},"closed":[]},
          "classes":[{"code":"MINE","name":"My class"},{"code":"OTHER","name":"Other class"}],
          "slots":[{"code":"MINE","day":1,"period":1,"staff":"CODE-A","room":"A"},{"code":"OTHER","day":1,"period":1,"staff":"CODE-B","room":"B"}],
          "bindings":{"CODE-A":{"profile":profile.pk,"user":teacher.pk,"staff_id":"FAKE-A","verification":mapping.verified_at.isoformat()}}}
        ConnectedSchoolPublication.objects.create(name="Fictional term",starts=monday,ends=monday+timedelta(days=14),snapshot=snap,source_batches={},digest="b"*64,published_by=admin)
        self.client.force_login(teacher)
        url="/teacher/timetable/?date="+monday.isoformat()
        response=self.client.get(url)
        self.assertContains(response,'id="rf-shared-schedule"')
        data=response.context["shared_schedule"]
        self.assertEqual([x["code"] for d in data["days"] for x in d["lessons"]],["MINE"])
        self.assertNotContains(response,"OTHER")
        self.assertNotContains(response,"FAKE-A")
        profile.teaching_enabled=False
        profile.save(update_fields=["teaching_enabled"])
        self.assertNotEqual(self.client.get(url).status_code,200)
