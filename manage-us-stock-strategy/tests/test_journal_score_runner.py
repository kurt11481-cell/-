"""evo-s3: behaviour of run_journal_score.ps1 under Windows PowerShell 5.1.

The first scheduled run (2026-10-18) ended before WEEKLY_LATEST.json was written: Get-JsonValue called
.Contains() on the Dictionary[string,object] that the JavaScriptSerializer returns, which has no such method.
The static tests never ran PowerShell, so nobody saw it. These tests run a COPY of the runner inside a temporary
repository next to a fake scorer that writes a report the way the real one does. The repository runner and the
real scorer are never executed (no Kiwoom, no repository data, nothing written outside the temporary folder).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
RUNNER_NAME = "run_journal_score.ps1"
MODE_VARIABLE = "FAKE_SCORER_MODE"

# The fake scorer: writes workspace/outputs/journal-scores/<UTC time>/journal-scores.json as the mode says, records
# its arguments and ends with the exit code the mode says. The learning block has nested objects and arrays like
# the real report (counts and epochs objects, a buckets array).
FAKE_SCORER = '''import datetime
import json
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parents[2]
mode = __import__("os").environ["FAKE_SCORER_MODE"]
root.joinpath("argv.txt").write_text(" ".join(sys.argv[1:]), encoding="ascii")
folder = root / "workspace" / "outputs" / "journal-scores" / datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
folder.mkdir(parents=True, exist_ok=True)
learning = {
    "errors": [],
    "counts": {"scored": 3, "pending": 1},
    "epochs": {"E1": {"n": 2, "labels": ["a", "b"]}},
    "buckets": [{"name": "b1", "n": 3}, {"name": "b2", "n": 4}],
}
report = {"schema": "journal-scores/fake", "rows": [1, 2, 3], "learning": learning}
exit_code = 0
if mode == "no_learning" or mode == "stale":
    del report["learning"]
elif mode == "learning_failed":
    report["learning"] = {"errors": [{"reason": "LEARNING_FAILED: broken input"}]}
elif mode == "scorer_exit":
    exit_code = 2
target = folder / "journal-scores.json"
if mode == "not_json":
    target.write_text("this is { not json", encoding="ascii")
else:
    target.write_text(json.dumps(report), encoding="ascii")
sys.exit(exit_code)
'''

STALE_NAME = "20200101T000000Z"


class RunnerTextTests(unittest.TestCase):
    """Text checks that also run where PowerShell does not."""

    def setUp(self):
        self.text = (SCRIPTS / RUNNER_NAME).read_bytes().decode("ascii")

    def test_key_check_does_not_use_the_missing_dictionary_method(self):
        self.assertNotIn(".Contains(", self.text)
        self.assertNotIn(".ContainsKey(", self.text)
        self.assertIn("$Object.Keys -ccontains $Name", self.text)

    def test_exception_path_is_present(self):
        for token in ("catch {", "RUNNER_FAIL RUNNER_EXCEPTION", '-Reason "RUNNER_EXCEPTION"', "$exitCode = -1",
                      "exit 4"):
            with self.subTest(token=token):
                self.assertIn(token, self.text)
        self.assertLess(self.text.index('Write-RunnerLine ("RUNNER_START'), self.text.index("exit 4"))


@unittest.skipUnless(os.name == "nt" and shutil.which("powershell.exe"), "Windows PowerShell is not available")
class RunnerCopyBehaviourTests(unittest.TestCase):
    """Runs a copy of the runner in a temporary repository whose scorer is a fake."""

    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.root = Path(self._temporary.name).resolve()
        scripts = self.root / "manage-us-stock-strategy" / "scripts"
        scripts.mkdir(parents=True)
        self.runner = scripts / RUNNER_NAME
        shutil.copyfile(SCRIPTS / RUNNER_NAME, self.runner)
        self.fake = scripts / "score_decision_journal.py"
        self.fake.write_text(FAKE_SCORER, encoding="ascii")
        self.scores = self.root / "workspace" / "outputs" / "journal-scores"
        self.scores.mkdir(parents=True)

    def tearDown(self):
        self._temporary.cleanup()

    def run_copy(self, mode: str) -> subprocess.CompletedProcess:
        # Only the copy under the temporary folder may run; the repository files never do.
        for path in (self.runner, self.fake):
            self.assertTrue(path.resolve().is_relative_to(self.root), path)
            self.assertFalse(path.resolve().is_relative_to(ROOT.resolve()), path)
        self.assertNotEqual(self.runner.resolve(), (SCRIPTS / RUNNER_NAME).resolve())
        environment = dict(os.environ)
        environment[MODE_VARIABLE] = mode
        return subprocess.run(
            [shutil.which("powershell.exe"), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(self.runner), "-RepositoryRoot", str(self.root), "-PythonPath", sys.executable],
            cwd=str(self.root), env=environment, capture_output=True, timeout=180,
        )

    def log_text(self) -> str:
        logs = sorted((self.scores / "logs").glob("*.log"))
        self.assertEqual(len(logs), 1, logs)
        return logs[0].read_text(encoding="utf-8", errors="replace")

    def weekly(self) -> dict:
        return json.loads((self.scores / "WEEKLY_LATEST.json").read_text(encoding="utf-8"))

    def assert_outcome(self, result, *, process_exit, status, reason, field_exit, present, failed, log_exit):
        detail = (result.stdout, result.stderr, self.log_text())
        self.assertEqual(result.returncode, process_exit, detail)
        document = self.weekly()
        self.assertEqual(document["schema"], "journal-score-weekly/v1", detail)
        self.assertEqual(document["status"], status, detail)
        self.assertEqual(document["reason"], reason, detail)
        self.assertEqual(document["exit_code"], field_exit, detail)
        self.assertIs(document["learning_present"], present, detail)
        self.assertIs(document["learning_failed"], failed, detail)
        self.assertIs(document["order_authority"], False, detail)
        self.assertIn("RUNNER_START", self.log_text())
        self.assertIn("RUNNER_END exit=%d status=%s" % (log_exit, status), self.log_text(), detail)
        self.assertFalse((self.scores / "WEEKLY_LATEST.json.tmp").exists())
        return document

    def test_1_learning_report_gives_ok_and_exit_0(self):
        # Regression test of the 2026-10-18 defect: nested objects and arrays go through the .NET serializer.
        result = self.run_copy("ok")
        # The runner's [string]$Reason parameter turns the null reason of an OK run into "" (unchanged behaviour).
        document = self.assert_outcome(result, process_exit=0, status="OK", reason="", field_exit=0,
                                       present=True, failed=False, log_exit=0)
        self.assertEqual((self.root / "argv.txt").read_text(encoding="ascii"), "--learning")
        self.assertTrue(document["report_path"].endswith("journal-scores.json"), document)
        self.assertNotIn("RUNNER_FAIL", self.log_text())

    def test_2_report_without_learning_block_fails(self):
        result = self.run_copy("no_learning")
        self.assert_outcome(result, process_exit=1, status="FAIL", reason="NO_LEARNING_REPORT", field_exit=0,
                            present=False, failed=False, log_exit=1)
        self.assertIsNone(self.weekly()["report_path"])

    def test_3_learning_failed_block_fails_with_nonzero_process_exit(self):
        result = self.run_copy("learning_failed")
        self.assert_outcome(result, process_exit=1, status="FAIL", reason="LEARNING_FAILED", field_exit=0,
                            present=True, failed=True, log_exit=1)

    def test_4_scorer_exit_code_is_kept(self):
        result = self.run_copy("scorer_exit")
        self.assert_outcome(result, process_exit=2, status="FAIL", reason="SCORER_EXIT", field_exit=2,
                            present=True, failed=False, log_exit=2)

    def test_5_report_that_is_not_json_fails(self):
        result = self.run_copy("not_json")
        self.assert_outcome(result, process_exit=1, status="FAIL", reason="REPORT_NOT_JSON", field_exit=0,
                            present=False, failed=False, log_exit=1)

    def test_6_report_folder_from_before_the_start_is_not_picked(self):
        stale = self.scores / STALE_NAME
        stale.mkdir()
        (stale / "journal-scores.json").write_text(json.dumps({"learning": {"errors": []}}), encoding="ascii")
        result = self.run_copy("stale")
        self.assert_outcome(result, process_exit=1, status="FAIL", reason="NO_LEARNING_REPORT", field_exit=0,
                            present=False, failed=False, log_exit=1)

    def test_7_exception_after_start_is_logged_and_exits_4(self):
        # A folder in place of the temp file makes the status write throw in the try block and again in the catch.
        (self.scores / "WEEKLY_LATEST.json.tmp").mkdir()
        result = self.run_copy("ok")
        detail = (result.stdout, result.stderr)
        log = self.log_text()
        self.assertEqual(result.returncode, 4, detail + (log,))
        self.assertIn("RUNNER_START", log)
        self.assertIn("RUNNER_FAIL RUNNER_EXCEPTION type=", log)
        self.assertIn("message=", log)
        self.assertNotIn("RUNNER_END", log)
        self.assertFalse((self.scores / "WEEKLY_LATEST.json").exists())


if __name__ == "__main__":
    unittest.main()
