"""Synthetic fixtures only for a disposable restored Windows CI instance."""
import os
from pathlib import Path
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from accounts.models import ConnectedSchoolPublication,ImportedTimetable,StaffProfile,Student,StaffAccessGrant

@transaction.atomic
def seed():
    state=Path(settings.ROLLFLOW_ARCHIVE_STATE_DIR)
    if (settings.ROLLFLOW_SCHOOL_MODE or state.name!="rf-restored"
        or os.environ.get("RF_PROTECTED_BROWSER_FIXTURE")!="yes"):
        raise RuntimeError("Refusing to seed outside the isolated staging CI restore.")
    password=os.environ["RF_PROTECTED_BROWSER_PASSWORD"]
    teacher=User.objects.create_user("browser_teacher",password=password)
    other=User.objects.create_user("browser_other",password=password)
    monitor=User.objects.create_user("browser_monitor",password=password)
    admin=User.objects.get(username="upgrade-fixture")
    profiles=[StaffProfile.objects.create(user=u,staff_id=code,teaching_enabled=True,timetable_link_verified=True)
        for u,code in [(teacher,"BROWSER001"),(other,"BROWSER002")]]
    students=[Student.objects.create(student_id="BROWSERSTUDENT"+str(i),first_name=name,last_name="Fictional",year_level=year)
        for i,name,year in [(1,"BrowserAllowed",7),(2,"BrowserDenied",8)]]
    StaffAccessGrant.objects.create(user=monitor,role="Attendance Officer",scope="school",capabilities=["attendance_monitor"],granted_by=admin)
    day=timezone.localdate()
    version=ImportedTimetable.objects.create(name="CI browser timetable",digest="b"*64,status=ImportedTimetable.Status.PUBLISHED)
    ConnectedSchoolPublication.objects.filter(active=True).update(active=False)
    bindings={p.staff_id:{"profile":p.pk,"user":p.user_id,"staff_id":p.staff_id} for p in profiles}
    classes=[{"code":code,"name":"Fictional class","years":[s.year_level],"students":[s.pk]}
        for code,s in zip(("BROWSER7","BROWSER8"),students)]
    slots=[{"code":c["code"],"name":c["name"],"date":day.isoformat(),"period":"P1","start":"00:00","end":"23:59",
        "staff":p.staff_id,"room":"CI room"} for c,p in zip(classes,profiles)]
    ConnectedSchoolPublication.objects.create(name="CI browser publication",starts=day,ends=day,digest="c"*64,published_by=admin,
        snapshot={"source":"dated","timetable_version":version.pk,"calendar":{"dates":[day.isoformat()]},
            "stats":{"rosters_ready":True,"skipped_pairs":0},"classes":classes,"slots":slots,
            "student_identity":{str(s.pk):s.student_id for s in students},"bindings":bindings})


    # Role-specific fictional staging profiles; deliberately limited to actual
    # implemented scopes, not copied demo authority. No real identities.
    User.objects.create_superuser("browser_admin",email="admin@example.invalid",password=password)
    profiles[0].faculty="English"
    profiles[0].save(update_fields=["faculty"])
    profiles[1].faculty="Mathematics"
    profiles[1].save(update_fields=["faculty"])
    for key,role,scope,value,caps,teaches in [
        ("principal","Principal","school","",["staff","students","published_classes","published_timetable","attendance_monitor","movement_monitor","workforce_monitor","report_attendance"],False),
        ("deputy","Deputy Principal","school","",["staff","students","published_classes","published_timetable","attendance_monitor","movement_monitor","workforce_monitor","report_attendance","report_workforce"],False),
        ("hod","Head of Department","faculty","English",["staff","published_classes","published_timetable","report_attendance"],False),
        ("ylc","Head of Year","year","7",["students","published_classes","published_timetable","report_attendance"],False),
        ("business","Business Manager","school","",["staff","workforce_monitor","report_workforce"],False),
        ("office","Administration Officer","school","",["staff","students","movement_monitor","workforce_monitor","report_workforce"],False),
        ("learning","Learning Support Teacher","school","",["support_task","support_referral"],True),
        ("aide","Teacher Aide","school","",["support_task"],False),
        ("relief","Relief Teacher","school","",["support_task"],True),
        ("guidance","Guidance Officer","school","",["support_referral"],False),
    ]:
        u=User.objects.create_user("browser_"+key,password=password,first_name="Fictional",last_name=role)
        StaffProfile.objects.create(user=u,staff_id="BROWSER_"+key.upper(),teaching_enabled=teaches,
            faculty="English" if key=="hod" else "")
        StaffAccessGrant.objects.create(user=u,role=role,scope=scope,scope_value=value,capabilities=caps,granted_by=admin)

    from accounts.models import MovementDestination
    MovementDestination.objects.create(name="Fictional CI water break",expected_minutes=10,
        requires_reception=False,created_by=admin)

def reset_test_login_windows():
    # All synthetic browser accounts share the CI runner's loopback IP.
    # Reset only within the explicitly named disposable CI restore; never
    # alter the normal application's throttling or a school database.
    state=Path(settings.ROLLFLOW_ARCHIVE_STATE_DIR)
    if (settings.ROLLFLOW_SCHOOL_MODE or state.name!="rf-restored"
        or os.environ.get("RF_PROTECTED_BROWSER_FIXTURE")!="yes"):
        raise RuntimeError("Refusing to reset login windows outside the disposable fixture.")
    from accounts.models import LoginWindow
    LoginWindow.objects.all().delete()
