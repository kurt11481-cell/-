from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import portfolio_status as ps  # noqa: E402

NOW = "2026-09-30T12:00:00+00:00"
SECRET_SHARES = 987654


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def make_state(updated: str, broker_as_of: str) -> dict:
    return {
        "last_updated_at": updated,
        "holdings": {"NBIS": SECRET_SHARES},
        "last_confirmed_broker_snapshot": {
            "as_of": broker_as_of[:10], "as_of_timestamp": broker_as_of,
            "evidence_sha256": "deadbeef" * 8, "proposal_id": "secretproposal",
        },
    }


def make_analysis(root: Path, run: str, decided: str, diff: str, open_status: str) -> None:
    write_json(root / "workspace/outputs/manual-portfolio-analysis" / run / ps.ANALYSIS_FILE, {
        "manual_run_id": run, "decision_as_of": decided, "broker_diff_status": diff,
        "broker_snapshot_as_of": decided,
        "broker_observed_state": {"operation_statuses": {"account_open_items": open_status}},
    })


def full_root(tmp: Path, *, updated: str = "2026-09-30T03:35:43+00:00",
              broker: str = "2026-09-30T03:35:03Z") -> Path:
    write_json(tmp / ps.DEFAULT_PATHS["state"], make_state(updated, broker))
    ledger = tmp / ps.DEFAULT_PATHS["ledger"]
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(
        json.dumps({"event": "APPLY", "confirmed_at": "2026-09-30T02:46:32+00:00", "state_revision_after": 15}) + "\n"
        + "not json\n\n"
        + json.dumps({"event": "APPLY", "confirmed_at": "2026-09-30T03:35:43+00:00", "state_revision_after": 16}) + "\n",
        encoding="utf-8")
    make_analysis(tmp, "manual-20260917T151230Z-a", "2026-09-17T15:12:30+00:00", "DIFFERENT", "PASS")
    make_analysis(tmp, "manual-20260930T112114Z-b", "2026-09-30T11:21:14+00:00", "MATCH",
                  "KIWOOM_API_RESPONSE_ERROR")
    write_json(tmp / ps.DEFAULT_PATHS["baseline_index"], {"active": {
        "SOXL": {"baseline_id": "soxl-v2", "activated_at": "2026-08-14T08:30:38Z"},
        "NBIS": {"baseline_id": "nbis-v4", "activated_at": "2026-08-14T11:20:17.694777+00:00"},
    }})
    for name in ("2026-08-10", "2026-09-30-r2", "2026-09-30", "notes"):
        (tmp / ps.DEFAULT_PATHS["cards_dir"] / name).mkdir(parents=True)
    # Real entry types: an S5 record and a user decision are never pending, only card decisions are.
    write_json(tmp / ps.DEFAULT_PATHS["journal"], {"entries": [
        {"entry_type": "s5_activation", "sequence": 1},
        {"entry_type": "card_decision", "sequence": 2, "payload": {"decision_id": "a" * 64}},
        {"entry_type": "card_decision", "sequence": 3, "payload": {"decision_id": "b" * 64}},
        {"entry_type": "card_user_decision", "sequence": 4, "payload": {"decision_id": "a" * 64}}]})
    return tmp


def run_cli(root: Path, *extra: str) -> tuple[int, str, dict]:
    output = root / "out" / "latest.json"
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = ps.main(["--root", str(root), "--output", str(output), "--now", NOW, *extra])
    return code, buffer.getvalue().strip(), json.loads(output.read_text(encoding="utf-8"))


class PortfolioStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="portfolio_status_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_item_calculations(self) -> None:
        full_root(self.tmp)
        code, line, report = run_cli(self.tmp)
        self.assertEqual(code, 0)
        self.assertEqual(report["state"]["status"], "OK")
        self.assertAlmostEqual(report["state"]["age_days"], 0.35, places=2)
        self.assertFalse(report["state"]["stale"])
        self.assertEqual(report["broker_snapshot"]["date"], "2026-09-30")
        self.assertAlmostEqual(report["broker_snapshot"]["age_days"], 0.35, places=2)
        analysis = report["latest_analysis"]
        self.assertEqual(analysis["run_id"], "manual-20260930T112114Z-b")
        self.assertEqual(analysis["broker_diff_status"], "MATCH")
        self.assertEqual(report["open_orders"], {"status": "ERROR", "bridge_status": "KIWOOM_API_RESPONSE_ERROR"})
        recon = report["latest_reconciliation"]
        self.assertEqual((recon["entry_count"], recon["invalid_lines"], recon["state_revision_after"]), (2, 1, 16))
        self.assertEqual(recon["date"], "2026-09-30")
        tickers = report["baselines"]["tickers"]
        self.assertEqual(list(tickers), ["NBIS", "SOXL"])
        self.assertAlmostEqual(tickers["SOXL"]["age_days"], 47.15, places=2)
        self.assertEqual(report["latest_card"], {"status": "OK", "date": "2026-09-30", "age_days": 0.0})
        self.assertEqual(report["scoring_pending"]["pending_count"], 2)
        self.assertEqual(report["scoring_pending"]["score_report"], "MISSING")
        self.assertNotIn("assumed_schema", report["scoring_pending"])
        self.assertEqual(report["warnings"], ["OPEN_ORDERS_NOT_PASS"])
        self.assertIn("9/30", line)
        self.assertIn("KIWOOM_API_RESPONSE_ERROR", line)
        self.assertIn("채점 대기 2건", line)
        self.assertTrue(report["read_only"])
        self.assertFalse(report["order_authority"])

    def write_score_report(self, head: object, pending: object) -> None:
        directory = self.tmp / ps.DEFAULT_PATHS["scores_dir"] / "20260930T120000Z"
        write_json(directory / ps.SCORE_REPORT_FILE, {"journal": {"head_sha256": head},
                                                       "summary": {"pending_decisions": pending,
                                                                   "unscorable_decisions": 0}})

    def test_pending_uses_the_score_report_only_when_it_matches_the_journal_head(self) -> None:
        full_root(self.tmp)
        journal = json.loads((self.tmp / ps.DEFAULT_PATHS["journal"]).read_text(encoding="utf-8"))
        from validation_common import canonical_hash
        head = canonical_hash(journal["entries"][-1])
        self.write_score_report(head, 1)
        pending = run_cli(self.tmp)[2]["scoring_pending"]
        self.assertEqual((pending["pending_count"], pending["score_report"], pending["decision_count"]), (1, "CURRENT", 2))
        self.write_score_report("0" * 64, 0)  # a newer report made from a different journal state
        pending = run_cli(self.tmp)[2]["scoring_pending"]
        self.assertEqual((pending["pending_count"], pending["score_report"]), (2, "STALE"))

    def test_journal_without_card_decisions_has_nothing_pending(self) -> None:
        full_root(self.tmp)
        write_json(self.tmp / ps.DEFAULT_PATHS["journal"], {"entries": [{"entry_type": "s5_activation", "sequence": 1}]})
        pending = run_cli(self.tmp)[2]["scoring_pending"]
        self.assertEqual((pending["status"], pending["pending_count"]), ("OK", 0))

    def test_missing_files_do_not_fail(self) -> None:
        code, line, report = run_cli(self.tmp)
        self.assertEqual(code, 0)
        for key in ("state", "broker_snapshot", "latest_analysis", "latest_reconciliation",
                    "baselines", "latest_card", "scoring_pending"):
            self.assertEqual(report[key]["status"], "MISSING", key)
        self.assertEqual(report["open_orders"]["status"], "MISSING")
        self.assertEqual(report["warnings"], ["STATE_MISSING", "BROKER_SNAPSHOT_MISSING"])
        self.assertIn("상태 파일 없음", line)
        self.assertIn("마지막 카드 없음", line)

    def test_card_folder_with_impossible_date_is_ignored(self) -> None:
        (self.tmp / ps.DEFAULT_PATHS["cards_dir"] / "2026-13-45").mkdir(parents=True)
        code, _, report = run_cli(self.tmp)
        self.assertEqual((code, report["latest_card"]["status"]), (0, "MISSING"))
        (self.tmp / ps.DEFAULT_PATHS["cards_dir"] / "2026-09-29").mkdir()
        _, _, report = run_cli(self.tmp)
        self.assertEqual((report["latest_card"]["date"], report["latest_card"]["age_days"]), ("2026-09-29", 1.0))

    def test_invalid_state_file_is_reported_not_raised(self) -> None:
        path = self.tmp / ps.DEFAULT_PATHS["state"]
        path.parent.mkdir(parents=True)
        path.write_text("{broken", encoding="utf-8")
        code, line, report = run_cli(self.tmp)
        self.assertEqual(code, 0)
        self.assertEqual(report["state"]["status"], "INVALID")
        self.assertIn("상태 파일 읽기 실패", line)

    def test_stale_state_warning(self) -> None:
        full_root(self.tmp, updated="2026-08-12T00:00:00+00:00", broker="2026-08-12T00:00:00Z")
        _, line, report = run_cli(self.tmp)
        self.assertTrue(report["state"]["stale"])
        self.assertTrue(report["broker_snapshot"]["stale"])
        self.assertGreater(report["state"]["age_days"], 49)
        self.assertIn("STATE_STALE", report["warnings"])
        self.assertIn("BROKER_SNAPSHOT_STALE", report["warnings"])
        self.assertTrue(line.startswith("경고: 상태가 오래됨"))
        self.assertIn("상태 기준 8/12 (49일)", line)

    def test_stale_threshold_is_an_argument(self) -> None:
        full_root(self.tmp, updated="2026-09-20T12:00:00+00:00")
        _, _, report = run_cli(self.tmp, "--stale-days", "30")
        self.assertFalse(report["state"]["stale"])
        _, _, report = run_cli(self.tmp, "--stale-days", "4")
        self.assertTrue(report["state"]["stale"])

    def test_broker_diff_and_pass_open_orders(self) -> None:
        full_root(self.tmp)
        make_analysis(self.tmp, "manual-20260930T130000Z-c", "2026-09-30T13:00:00+00:00", "DIFFERENT", "PASS")
        _, line, report = run_cli(self.tmp)
        self.assertEqual(report["warnings"], ["BROKER_DIFF_NOT_MATCH"])
        self.assertEqual(report["open_orders"]["status"], "PASS")
        self.assertIn("조정 대기", line)

    def test_output_has_no_holdings_hashes_or_ids(self) -> None:
        full_root(self.tmp)
        run_cli(self.tmp)
        text = (self.tmp / "out" / "latest.json").read_text(encoding="utf-8")
        for secret in (str(SECRET_SHARES), "deadbeef", "secretproposal"):
            self.assertNotIn(secret, text)

    def test_inputs_are_not_modified(self) -> None:
        full_root(self.tmp)

        def digest() -> dict[str, str]:
            return {str(p.relative_to(self.tmp)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted(self.tmp.rglob("*")) if p.is_file() and "out" not in p.parts}

        before = digest()
        run_cli(self.tmp)
        self.assertEqual(digest(), before)

    def test_explicit_paths_override_root(self) -> None:
        state = self.tmp / "elsewhere" / "state.json"
        write_json(state, make_state("2026-09-29T12:00:00+00:00", "2026-09-29T12:00:00Z"))
        _, _, report = run_cli(self.tmp, "--state", str(state))
        self.assertEqual(report["state"]["date"], "2026-09-29")

    def test_status_output_is_gitignored(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git not available")
        result = subprocess.run(
            ["git", "check-ignore", "-q", "workspace/outputs/status/latest.json"],
            cwd=REPO_ROOT, capture_output=True, text=True)
        if result.returncode not in (0, 1):
            self.skipTest("not a git checkout")
        self.assertEqual(result.returncode, 0, "workspace/outputs/status/ must be listed in .gitignore")


class LocaleContractTests(unittest.TestCase):
    def test_script_is_ascii_and_locale_covers_every_warning(self) -> None:
        self.assertTrue((SKILL_ROOT / "scripts/portfolio_status.py").read_text(encoding="utf-8").isascii())
        messages = ps.load_messages()
        for code in ("STATE_MISSING", "STATE_STALE", "BROKER_SNAPSHOT_MISSING", "BROKER_SNAPSHOT_STALE",
                     "BROKER_DIFF_NOT_MATCH", "OPEN_ORDERS_NOT_PASS"):
            self.assertIn(code, messages["warnings"])

    def test_invalid_now_is_rejected(self) -> None:
        self.assertEqual(ps.main(["--now", "not-a-time"]), 2)


if __name__ == "__main__":
    unittest.main()
