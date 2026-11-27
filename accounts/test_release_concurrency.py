"""PostgreSQL-only real concurrent requests using fictional attendance fixtures."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.db import connection,close_old_connections
from django.test import TransactionTestCase,Client,override_settings
from . import test_live_foundation
from .models import AttendanceRoll,AttendanceRevision

@skipUnless(connection.vendor=="postgresql","Row-lock concurrency gate requires PostgreSQL.")
@override_settings(ROLLFLOW_PROTECTED_WORKSPACE=True,SECURE_SSL_REDIRECT=False,
                   SESSION_COOKIE_SECURE=False,CSRF_COOKIE_SECURE=False)
class ReleaseConcurrencyTests(TransactionTestCase):
    def setUp(self):
        # TransactionTestCase commits fixture rows so separate worker DB connections can read them.
        test_live_foundation.LiveFoundationTests.setUp(self)

    def test_two_concurrent_certifications_keep_one_revision(self):
        clients=[Client(),Client()]
        for c in clients:c.force_login(self.teacher)
        payload=test_live_foundation.LiveFoundationTests.payload(self,"submit")
        barrier=Barrier(2)
        def submit(client):
            close_old_connections()
            try:
                barrier.wait(timeout=15)
                return client.post(self.url,payload).status_code
            finally:close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses=list(pool.map(submit,clients))
        self.assertCountEqual(statuses,[302,409])
        self.assertEqual(AttendanceRoll.objects.count(),1)
        roll=AttendanceRoll.objects.get()
        self.assertIsNotNone(roll.submitted_at)
        self.assertEqual(AttendanceRevision.objects.filter(roll=roll).count(),1)
