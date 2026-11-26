import functools
import http.client
import threading
import unittest
from http.server import ThreadingHTTPServer
from .training import TrainingHandler, ROOT

class TrainingServerTests(unittest.TestCase):
    def test_isolated_public_files_only(self):
        handler = functools.partial(TrainingHandler, directory=str(ROOT))
        with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for path, status in [("/", 200), ("/styles/rollflow-design.css", 200), ("/shared/schedule-core.js", 200),
                                     ("/legacy/index.html",404),
                                     ("/../index.html",404), ("/accounts/models.py",404), ("/manage/",404)]:
                    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
                    conn.request("GET", path)
                    res = conn.getresponse()
                    self.assertEqual(res.status,status,path)
                    self.assertIn("connect-src 'self'",res.getheader("Content-Security-Policy"))
                    res.read()
                    conn.close()
                conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
                conn.request("GET", "/", headers={"Host":"untrusted.example"})
                self.assertEqual(conn.getresponse().status,403)
                conn.close()
            finally:
                server.shutdown()
                thread.join()
