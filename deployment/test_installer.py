import tempfile
import unittest
from pathlib import Path
from .bundle_integrity import manifest,verify
from .workstation import approved_url,configure,load

class InstallerTests(unittest.TestCase):
    def test_url_validation(self):
        self.assertEqual(approved_url("https://RollFlow.school.example:443/"),"https://rollflow.school.example/")
        for bad in ["http://school.example","https://user@school.example","https://school.example/path",
                    "https://school.example?x=1","https://school.example#x","https://school.example:8080",
                    "https://localhost","https://127.0.0.1","https://school..example","https://school.example\\x",
                    "https://school.example\n","file:///tmp/a"]:
            with self.subTest(bad=bad),self.assertRaises(ValueError):approved_url(bad)

    def test_client_config_only_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"config"/"server.json"
            configure(path,"https://school.example")
            self.assertEqual(load(path),"https://school.example/")
            with self.assertRaises(ValueError):configure(path,"http://school.example")
            self.assertEqual(load(path),"https://school.example/")

    def test_manifest_tamper_and_extra(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            f=root/"file.txt"
            f.write_text("fictional")
            manifest(root)
            self.assertEqual(verify(root,strict=True),1)
            (root/"extra").write_text("extra")
            with self.assertRaises(ValueError):verify(root,strict=True)
            (root/"extra").unlink()
            f.write_text("changed")
            with self.assertRaises(ValueError):verify(root)

    def test_manifest_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"SHA256SUMS.txt").write_text("a"*64+"  ../outside\n")
            with self.assertRaises(ValueError):verify(root)
