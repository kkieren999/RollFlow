import tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from deployment.native import init,exclusive_operation
from deployment.release_readiness import report
from rollflow.release_policy import assert_school_release

class ReleaseReadinessTests(unittest.TestCase):
    def test_school_gate_is_not_an_environment_switch(self):
        with patch.dict("os.environ",{"ROLLFLOW_PRODUCTION_APPROVED":"1","ROLLFLOW_SCHOOL_MODE":"1"}):
            with self.assertRaises(RuntimeError):assert_school_release()
        self.assertFalse(report()["production_approved"])
        self.assertGreater(len(report()["open_gates"]),0)

    def test_school_init_refuses_before_any_state_creation(self):
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder)/"new"
            with self.assertRaisesRegex(RuntimeError,"school mode blocked"):
                init(SimpleNamespace(mode="school"),state)
            self.assertFalse(state.exists())

    def test_native_operation_exclusion_and_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            state=Path(folder)
            with exclusive_operation(state):
                with self.assertRaises(RuntimeError):
                    with exclusive_operation(state):pass
                self.assertTrue((state/"native-operation.lock").exists())
            self.assertFalse((state/"native-operation.lock").exists())
            with self.assertRaises(ValueError):
                with exclusive_operation(state):raise ValueError("test")
            self.assertFalse((state/"native-operation.lock").exists())

    def test_invalid_snapshot_does_not_create_destination(self):
        from deployment.recovery import restore,seal
        from subprocess import CalledProcessError
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            snap=root/"snapshot";snap.mkdir()
            (snap/"rollflow.dump").write_bytes(b"PGDMPnot a valid database")
            seal(snap,"staging")
            dest=root/"new"
            with patch("deployment.recovery.run",side_effect=CalledProcessError(1,["pg_restore"])), patch("deployment.recovery.init") as init:
                with self.assertRaises(CalledProcessError):
                    restore(snap,dest,root,55433,18081)
                init.assert_not_called()
            self.assertFalse(dest.exists())

    def test_tampered_snapshot_fails_before_runtime(self):
        from deployment.recovery import restore,seal
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            snap=root/"snapshot";snap.mkdir()
            (snap/"rollflow.dump").write_bytes(b"PGDMPfictional")
            seal(snap,"staging")
            (snap/"rollflow.dump").write_bytes(b"PGDMPmodified")
            dest=root/"new"
            with patch("deployment.recovery.run") as command:
                with self.assertRaisesRegex(ValueError,"Checksum mismatch"):
                    restore(snap,dest,root,55433,18081)
                command.assert_not_called()
            self.assertFalse(dest.exists())
