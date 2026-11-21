"""Regression tests for Windows initdb's private password-file access."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from deployment import native


IDENTITY = '"SCHOOL\\\\teacher","S-1-5-21-1234-5678-9012-1001"\r\n'


class WindowsPasswordPermissionsTests(unittest.TestCase):
    def test_password_file_acl_grants_explicit_current_sid_only(self):
        target = Path("test-initial-password.txt")
        with patch("deployment.native.subprocess.check_output", return_value=IDENTITY) as who, \
             patch("deployment.native.subprocess.run") as executed:
            native.harden_windows_acl(target)

        who.assert_called_once_with(
            ["whoami.exe", "/user", "/fo", "csv", "/nh"],
            text=True, errors="replace",
        )
        executed.assert_called_once_with(
            ["icacls.exe", str(target), "/inheritance:r", "/grant:r",
             "*S-1-5-21-1234-5678-9012-1001:F"],
            check=True, stdout=subprocess.DEVNULL,
        )

    def test_state_directory_acl_applies_only_to_current_sid_and_children(self):
        target = Path("instance-directory")
        with patch("deployment.native.subprocess.check_output", return_value=IDENTITY), \
             patch("deployment.native.subprocess.run") as executed:
            native.harden_windows_acl(target, directory=True)

        executed.assert_called_once_with(
            ["icacls.exe", str(target), "/inheritance:r", "/grant:r",
             "*S-1-5-21-1234-5678-9012-1001:(OI)(CI)F"],
            check=True, stdout=subprocess.DEVNULL,
        )

    def test_invalid_sid_fails_closed_without_changing_permissions(self):
        for identity in ('"SCHOOL\\\\teacher","not-a-sid"\n', "", '"user","S-1-5-21-1","extra"'):
            with self.subTest(identity=identity), \
                 patch("deployment.native.subprocess.check_output", return_value=identity), \
                 patch("deployment.native.subprocess.run") as executed:
                with self.assertRaises(RuntimeError):
                    native.harden_windows_acl(Path("some-private-file"))
                executed.assert_not_called()

    def test_acl_command_failure_stops_setup(self):
        with patch("deployment.native.subprocess.check_output", return_value=IDENTITY), \
             patch("deployment.native.subprocess.run",
                   side_effect=subprocess.CalledProcessError(5, "icacls.exe")):
            with self.assertRaises(subprocess.CalledProcessError):
                native.harden_windows_acl(Path("some-private-file"))

    def test_initdb_failure_cleans_up_temporary_password(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pg_bin = root / "pgbin"
            pg_bin.mkdir()
            for name in ("initdb", "pg_ctl", "postgres", "pg_dump"):
                (pg_bin / (name + native.EXE)).touch()
            args = SimpleNamespace(
                mode="staging", host=None, pg_bin=pg_bin,
                db_port=55432, web_port=8080, no_admin=True,
            )
            state = root / "instance"
            with patch("deployment.native.harden_windows_acl"), \
                 patch("deployment.native.run",
                       side_effect=subprocess.CalledProcessError(1, "initdb")):
                with self.assertRaises(subprocess.CalledProcessError):
                    native.init(args, state)
            self.assertFalse((state / "initial-password.txt").exists())


if __name__ == "__main__":
    unittest.main()
