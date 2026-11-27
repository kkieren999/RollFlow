"""RC2.8 synthetic transactional reliability checks. Real races require PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.db import connection, connections, close_old_connections, IntegrityError
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from . import test_live_foundation, test_movements
from .models import (AttendanceRoll, AttendanceRevision, StudentMovement, MovementEvent,
                     WorkforceNotice, AccessAudit, SecurityEvent, WorkforceEntry)


@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True, SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class AtomicFailureTests(TestCase):
    def setUp(self):
        test_movements.MovementTests.setUp(self)

    def test_attendance_history_failure_rolls_back_roll_and_audit(self):
        payload=test_live_foundation.LiveFoundationTests.payload(self,"submit")
        with patch("accounts.live_views.AttendanceRevision.objects.create",side_effect=IntegrityError("synthetic fault")):
            response=self.client.post(self.url,payload)
        self.assertEqual(response.status_code,409)
        self.assertFalse(AttendanceRoll.objects.exists())
        self.assertFalse(AttendanceRevision.objects.exists())
        self.assertFalse(SecurityEvent.objects.filter(event="attendance_submit").exists())
        self.assertEqual(self.client.post(self.url,payload).status_code,302)
        self.assertEqual(AttendanceRoll.objects.count(),1)
        self.assertEqual(AttendanceRevision.objects.count(),1)

    def test_movement_event_failure_rolls_back_departure_and_can_retry(self):
        payload=test_movements.MovementTests.issue_data(self)
        with patch("accounts.movement_service.MovementEvent.objects.create",side_effect=IntegrityError("synthetic fault")):
            response=self.client.post(self.issue_url,payload)
        self.assertEqual(response.status_code,409)
        self.assertFalse(StudentMovement.objects.exists())
        self.assertFalse(MovementEvent.objects.exists())
        self.assertFalse(SecurityEvent.objects.filter(event="movement_issue").exists())
        self.assertEqual(self.client.post(self.issue_url,payload).status_code,302)
        self.assertEqual(StudentMovement.objects.count(),1)
        self.assertEqual(MovementEvent.objects.count(),1)
        self.assertFalse(AttendanceRoll.objects.exists())


@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True, SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False)
class ConcurrentReliabilityTests(TransactionTestCase):
    def setUp(self):
        if connection.vendor!="postgresql":
            self.skipTest("Concurrent write serialization requires PostgreSQL")
        test_movements.MovementTests.setUp(self)

    def race(self,requests):
        """Each worker has its own session and DB connection; bounded lock waits."""
        clients=[]
        for user,path,payload in requests:
            client=Client()
            client.force_login(user)
            clients.append((client,path,payload))
        gate=Barrier(len(clients))
        def send(item):
            close_old_connections()
            try:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SET lock_timeout = '10s'")
                    cursor.execute("SET statement_timeout = '20s'")
                gate.wait(timeout=20)
                client,path,payload=item
                return client.post(path,payload).status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(clients)) as executor:
            return list(executor.map(send,clients))

    def test_duplicate_movement_and_reception_transition(self):
        payload=test_movements.MovementTests.issue_data(self)
        self.assertEqual(sorted(self.race([(self.teacher,self.issue_url,payload)]*2)),[302,409])
        movement=StudentMovement.objects.get()
        self.assertEqual(movement.events.count(),1)
        url=f"/live/movements/{movement.pk}/change/"
        self.assertEqual(sorted(self.race([(self.receiver,url,{"action":"arrive","revision":"1"})]*2)),[302,409])
        movement.refresh_from_db()
        self.assertEqual((movement.state,movement.revision),("arrived",2))
        self.assertEqual(list(movement.events.order_by("revision").values_list("action",flat=True)),["issue","arrive"])
        self.assertFalse(AttendanceRoll.objects.exists())

    def test_same_notice_acknowledged_once(self):
        notice=WorkforceNotice.objects.create(recipient=self.teacher,publication=self.pub,
            day=self.day,message="Fictional reliability notice")
        path=f"/live/workforce/notices/{notice.pk}/ack/"
        self.assertEqual(self.race([(self.teacher,path,{})]*2),[302,302])
        notice.refresh_from_db()
        self.assertIsNotNone(notice.acknowledged_at)
        self.assertEqual(AccessAudit.objects.filter(action="workforce_notice_acknowledged").count(),1)

    def test_independent_teachers_and_duplicate_submission(self):
        from .live_views import roster_token
        first=test_live_foundation.LiveFoundationTests.payload(self,"submit")
        second={**first,"roster_token":roster_token([self.outside])}
        del second["mark_"+str(self.student.pk)]
        second["mark_"+str(self.outside.pk)]="L"
        result=self.race([(self.teacher,self.url,first),(self.teacher,self.url,first),
                          (self.other,self.other_url,second)])
        self.assertEqual(sorted(result[:2]),[302,409])
        self.assertEqual(result[2],302)
        self.assertEqual(AttendanceRoll.objects.count(),2)
        self.assertEqual(AttendanceRevision.objects.count(),2)
        self.assertEqual(AttendanceRoll.objects.get(teacher=self.other).marks,{str(self.outside.pk):"L"})

    def test_closure_and_attendance_cannot_both_commit(self):
        payload=test_live_foundation.LiveFoundationTests.payload(self,"submit")
        closure={"action":"create","publication":str(self.pub.pk),"kind":"closure","confirm":"on"}
        result=self.race([(self.teacher,self.url,payload),(self.admin,"/live/workforce/",closure)])
        self.assertEqual(result.count(302),1)
        self.assertIn(result[0],(302,403,409))
        self.assertIn(result[1],(200,302,409))
        self.assertNotEqual(AttendanceRoll.objects.exists(),WorkforceEntry.objects.filter(kind="closure").exists())
