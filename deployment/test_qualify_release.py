import json
import tempfile
import unittest
from pathlib import Path
from deployment.bundle_integrity import manifest,digest
from deployment.qualify_release import qualify
from rollflow.release_policy import VERSION,CHANNEL


class QualificationTests(unittest.TestCase):
    def test_exact_packages_and_integrity_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            installers=root/"installers";installers.mkdir()
            local=root/"local";local.mkdir()
            client=root/"client";client.mkdir()
            for kind,bundle,docs in (("LocalLab",local,local/"app"/"docs"),("Workstation",client,client/"pilot-docs")):
                docs.mkdir(parents=True)
                for name in ("v5.0-rc4-release-qualification.md","v5.0-rc4-ict-handover.md",
                             "v5.0-rc3-pilot-readiness.md","v5.0-rc3-acceptance-record.md"):
                    (docs/name).write_text("synthetic")
                (bundle/"BUILD-INFO.json").write_text(json.dumps({"version":VERSION,"channel":CHANNEL,"source_commit":"a"*40}))
                if kind=="LocalLab":
                    (bundle/"app"/"manage.py").write_text("synthetic")
                    (bundle/"postgres"/"bin").mkdir(parents=True)
                    (bundle/"postgres"/"bin"/"postgres.exe").write_bytes(b"synthetic")
                    (bundle/"Pilot Readiness.cmd").write_text("synthetic")
                else:(bundle/"workstation.py").write_text("synthetic")
                manifest(bundle)
                name=f"RollFlow-V{VERSION}-{kind}-x64-STAGING-Setup.exe"
                exe=installers/name
                exe.write_bytes(b"fictional test binary")
                (installers/(name+".sha256")).write_text(digest(exe)+"  "+name+"\n")
            data=qualify(installers,local,client,"a"*40)
            self.assertEqual(len(data["packages"]),2)
            self.assertFalse(data["production_approved"])
            self.assertEqual(len(data["open_gates"]),10)
            with self.assertRaises(ValueError):qualify(installers,local,client,"b"*40)
            exe.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError,"checksum mismatch"):
                qualify(installers,local,client,"a"*40)
            exe.write_bytes(b"fictional test binary")
            (client/"app").mkdir()
            with self.assertRaisesRegex(ValueError,"local server"):
                qualify(installers,local,client,"a"*40)
