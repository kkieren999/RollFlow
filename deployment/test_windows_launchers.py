import tempfile
from pathlib import Path
import unittest
from .windows_launchers import write_launchers, EXISTING, FRESH


class WindowsLauncherTests(unittest.TestCase):
    def test_full_workspace_default_and_database_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_launchers(root)
            website = (root / "Start RollFlow.cmd").read_text()
            self.assertIn("-m deployment.training", website)
            self.assertNotIn("deployment.native", website)
            self.assertEqual(website, (root / "Open Training Demo.cmd").read_text())
            self.assertNotEqual(EXISTING, FRESH)
            for name in ("First Setup Fresh.cmd", "Start Fresh Protected.cmd",
                         "Upgrade Fresh Protected.cmd", "Manage Fresh Protected.cmd",
                         "Backup Fresh Protected.cmd", "First Setup.cmd"):
                self.assertIn(FRESH, (root / name).read_text(), name)
                self.assertNotIn(EXISTING, (root / name).read_text(), name)
            for name in ("Start Existing Protected.cmd", "Upgrade Existing.cmd",
                         "Manage RollFlow.cmd", "Backup RollFlow.cmd"):
                self.assertIn(EXISTING, (root / name).read_text(), name)
                self.assertNotIn(" init", (root / name).read_text(), name)
            self.assertIn("--db-port 55438 --web-port 18087", (root / "First Setup Fresh.cmd").read_text())
            self.assertIn("Start RollFlow.cmd", (root / "Protected Workspace.cmd").read_text())
