"""Disposable Linux CI recovery fixture; never run on real records."""
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.utils import timezone
from datetime import timedelta
from accounts.models import (Student, ConnectedSchoolPublication, AttendanceRoll,
    AttendanceRevision, MovementDestination, StudentMovement, MovementEvent, WorkforceNotice)


def guard():
    if not settings.DEBUG or settings.ROLLFLOW_SCHOOL_MODE:
        raise RuntimeError("Synthetic CI staging only.")
    return User.objects.get(username="ci_local_admin",is_superuser=True)


def seed():
    actor=guard()
    student=Student.objects.create(student_id="RC28-CI-ONLY",first_name="Synthetic",last_name="Recovery",year_level=7)
    day=timezone.localdate()
    pub=ConnectedSchoolPublication.objects.create(name="RC28 synthetic recovery",starts=day,ends=day,
        digest="8"*64,published_by=actor,snapshot={"student_identity":{str(student.pk):student.student_id}})
    roll=AttendanceRoll.objects.create(publication=pub,lesson_date=day,class_code="RC28CI",period="P1",
        start="09:00",end="10:00",teacher=actor,roster=[student.pk],marks={str(student.pk):"L"},revision=2,
        submitted_at=timezone.now())
    AttendanceRevision.objects.create(roll=roll,revision=1,actor=actor,action="submit",marks={str(student.pk):"P"})
    AttendanceRevision.objects.create(roll=roll,revision=2,actor=actor,action="correct",marks=roll.marks,reason="Synthetic recovery correction")
    dest=MovementDestination.objects.create(name="RC28 fictional desk",created_by=actor)
    now=timezone.now()
    movement=StudentMovement.objects.create(publication=pub,student=student,issuer=actor,destination=dest,
        destination_name=dest.name,requires_reception=False,lesson_date=day,class_code="RC28CI",period="P1",
        start="09:00",end="10:00",state="returned",revision=2,departed_at=now-timedelta(minutes=5),
        due_at=now+timedelta(minutes=5),closed_at=now)
    MovementEvent.objects.create(movement=movement,revision=1,actor=actor,action="issue",to_state="outbound")
    MovementEvent.objects.create(movement=movement,revision=2,actor=actor,action="return",from_state="outbound",to_state="returned")
    WorkforceNotice.objects.create(recipient=actor,publication=pub,day=day,message="RC28 synthetic recovery notice")
    session=SessionStore();session["rc28_fixture"]=True;session.save()


def verify(restored):
    actor=guard()
    student=Student.objects.get(student_id="RC28-CI-ONLY")
    roll=AttendanceRoll.objects.get(class_code="RC28CI")
    assert roll.teacher_id==actor.pk and roll.roster==[student.pk] and roll.submitted_at
    assert roll.revision==2 and roll.marks=={str(student.pk):"L"}
    assert list(roll.history.order_by("revision").values_list("action","marks"))==[
        ("submit",{str(student.pk):"P"}),("correct",{str(student.pk):"L"})]
    movement=StudentMovement.objects.get(student=student)
    assert movement.state=="returned" and movement.closed_at and movement.revision==2
    assert list(movement.events.order_by("revision").values_list("action",flat=True))==["issue","return"]
    assert WorkforceNotice.objects.filter(recipient=actor,message="RC28 synthetic recovery notice").count()==1
    if restored:
        assert not Session.objects.exists(),"Restored sessions must be invalidated"
    else:
        assert Session.objects.exists(),"Original sessions must remain untouched"
    print("Synthetic attendance revisions, movement history, private notice and session policy verified")
