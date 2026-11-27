import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from deployment.bundle_integrity import manifest
from deployment.pilot_readiness import inspect
from rollflow.release_policy import VERSION, OPEN_GATES, assert_school_release
from rollflow.pilot_plan import plan


class PilotReadinessTests(unittest.TestCase):
    def test_catalogue_is_blank_and_does_not_approve(self):
        data=plan()
        self.assertFalse(data["production_approved"])
        self.assertEqual(data["school_startup"],"blocked")
        self.assertEqual(len(data["scenarios"]),12)
        self.assertEqual(len({x["id"] for x in data["scenarios"]}),12)
        self.assertTrue(all(x["status"]=="not assessed" and x["evidence_reference"] is None for x in data["scenarios"]))
        self.assertEqual({x["id"] for x in data["gates"]},{k for k,_ in OPEN_GATES})
        self.assertTrue(all(x["status"]=="open" for x in data["gates"]))
        data["scenarios"][0]["status"]="passed"
        self.assertEqual(plan()["scenarios"][0]["status"],"not assessed")
        with patch.dict("os.environ",{"ROLLFLOW_PILOT_APPROVED":"1","ROLLFLOW_PRODUCTION_APPROVED":"1"}):
            with self.assertRaises(RuntimeError):assert_school_release()

    def test_bundle_identity_and_tamper(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"BUILD-INFO.json").write_text(json.dumps({"version":VERSION,"source_commit":"a"*40}))
            (root/"fictional.txt").write_text("fixture")
            manifest(root)
            data=inspect(root,"a"*40)
            self.assertTrue(data["bundle_matches_expected_commit"])
            self.assertFalse(data["production_approved"])
            self.assertEqual(data["bundle"]["verified_files"],2)
            with self.assertRaises(ValueError):inspect(root,"b"*40)
            with self.assertRaises(ValueError):inspect(expected_commit="a"*40)
            (root/"fictional.txt").write_text("changed")
            with self.assertRaises(ValueError):inspect(root,"a"*40)
