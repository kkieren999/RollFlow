import functools
import http.client
import threading
import unittest
import tempfile
from pathlib import Path
from .build_pages import build
from .public_assets import PUBLIC_FILES
from http.server import ThreadingHTTPServer
from .training import TrainingHandler, ROOT

class TrainingServerTests(unittest.TestCase):
    def test_pages_and_training_share_allowlist(self):
        with tempfile.TemporaryDirectory() as temp:
            out=build(Path(temp)/"site")
            actual={p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
            self.assertEqual(actual,set(PUBLIC_FILES)|{".nojekyll"})
            self.assertEqual((out/"index.html").read_bytes(),(ROOT/"index.html").read_bytes())
            self.assertFalse((out/"legacy").exists())
            self.assertFalse((out/"accounts").exists())
            self.assertFalse((out/"rollflow").exists())
            with self.assertRaises(ValueError):
                build(out)

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
