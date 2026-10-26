"""Decision scorer: SPY benchmark closes from reference-closes/SPY.json, else from the auto-core close history.

Synthetic files in temp folders only (d10-spy)."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[1]
ROOT = SKILL_ROOT.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import regular_session_close_history as rsch  # noqa: E402
import score_decision_journal as scorer  # noqa: E402
from test_s7_calendar_binding import SESSION_0829, build_authority_root  # noqa: E402

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
VERIFIED_SESSIONS = ("2026-09-24", "2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30")
WINTER_SESSION = "2026-01-05"  # core close at -05:00: the label time zone is not verified for that offset
CLOSES = {"2026-09-24": "500.10", "2026-09-25": "501.20", "2026-09-28": "502.30", "2026-09-29": "503.40",
          "2026-09-30": "504.50"}
REFERENCE_NOTE = "synthetic reference closes for tests"


class SpyHistoryCase(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="score_spy_history_"))
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.closes_root = self.root / "closes"
        self.trusted = self.root / "trusted"
        self.calendar = build_authority_root(self.trusted, extra_calendars=(SESSION_0829,))
        patcher = mock.patch.object(rsch, "TRUSTED_ROOT", self.trusted)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_reference(self, closes: dict[str, str]) -> Path:
        path = self.closes_root / "reference-closes" / "SPY.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema_version": "reference-closes-1.0", "symbol": "SPY",
                                    "source_note": REFERENCE_NOTE, "closes": closes}), encoding="utf-8")
        return path

    def write_history(self, closes: dict[str, str], symbol: str = "SPY") -> Path:
        """Synthetic pages (15:30 bar and 16:00 bar per session) -> history file, as the auto-core leaves it."""
        rows = []
        for session in sorted(closes, reverse=True):
            day = session.replace("-", "")
            for label, price in (("160000", "1.0000"), ("153000", closes[session])):
                rows.append({"cur_prc": price, "trde_qty": "1", "open_pric": price, "high_pric": price,
                             "low_pric": price, "cntr_tm": day + label, "bus_dt": day, "upd_stkpc_tp": "", "upd_rt": ""})
        rows[-1]["upd_stkpc_tp"] = "1f"
        folder = self.closes_root / "pages" / symbol
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "p1.json").write_text(json.dumps({"result": {"result_list": rows, "return_code": 0}}),
                                        encoding="utf-8")
        snapshot, _ = rsch.load_production_snapshot(NOW)
        history = rsch.build_history(symbol=symbol, exchange="NYSE", page_paths=[folder / "p1.json"],
                                     calendar=rsch.load_calendar(self.calendar, snapshot))
        target = self.closes_root / "history" / f"{symbol}.close-history.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(history), encoding="utf-8")
        return target

    def inputs(self) -> dict:
        return scorer.load_inputs(tickers=[], closes_root=self.closes_root, calendar_path=self.calendar, now=NOW)

    def report_benchmark(self, inputs: dict) -> dict:
        journal = {"status": "OK", "entries": [], "head_sha256": "0" * 64, "errors": []}
        report = scorer.score_journal(
            journal, calendar=inputs["calendar"], closes=inputs["closes"], unverified=inputs["unverified"],
            benchmark=inputs["benchmark"], corporate_actions=inputs["corporate_actions"], evaluation_as_of=NOW)
        return report["benchmark"]

    def test_a_reference_file_only_is_unchanged(self) -> None:
        self.write_reference(CLOSES)
        expected = scorer.load_reference_closes(self.closes_root)
        self.assertEqual({"status": "OK", "closes": CLOSES, "errors": []}, expected)
        inputs = self.inputs()
        self.assertEqual(expected, inputs["benchmark"])
        self.assertEqual({"symbol": "SPY", "label": "REFERENCE_ONLY", "status": "OK", "errors": []},
                         self.report_benchmark(inputs))

    def test_a2_invalid_reference_file_is_not_replaced_by_history(self) -> None:
        path = self.write_reference(CLOSES)
        path.write_text("{not json", encoding="utf-8")
        self.write_history(CLOSES)
        benchmark = self.inputs()["benchmark"]
        self.assertEqual({"status": "INVALID", "closes": {}, "errors": ["REFERENCE_CLOSES_NOT_JSON"]}, benchmark)

    def test_b_nothing_is_missing(self) -> None:
        benchmark = self.inputs()["benchmark"]
        self.assertEqual({"status": "MISSING", "closes": {}, "errors": []}, benchmark)
        self.assertEqual("MISSING", self.report_benchmark(self.inputs())["status"])

    def test_c_history_only_is_used_with_source(self) -> None:
        self.write_history(CLOSES)
        inputs = self.inputs()
        benchmark = inputs["benchmark"]
        self.assertEqual("OK", benchmark["status"])
        self.assertEqual(CLOSES, benchmark["closes"])
        self.assertEqual([], benchmark["errors"])
        self.assertEqual("KIWOOM_CLOSE_HISTORY", benchmark["source"])
        block = self.report_benchmark(inputs)
        self.assertEqual("KIWOOM_CLOSE_HISTORY", block["source"])
        self.assertEqual("REFERENCE_ONLY", block["label"])

    def test_d_reference_file_wins_over_history(self) -> None:
        reference = {session: str(float(value) + 100) for session, value in CLOSES.items()}
        self.write_reference(reference)
        self.write_history(CLOSES)
        benchmark = self.inputs()["benchmark"]
        self.assertEqual({"status": "OK", "closes": reference, "errors": []}, benchmark)
        self.assertNotIn("source", benchmark)

    def test_e_broken_history_is_invalid_without_exception(self) -> None:
        target = self.write_history(CLOSES)
        history = json.loads(target.read_text(encoding="utf-8"))
        history["sessions"][0]["close"] = "999.00"
        target.write_text(json.dumps(history), encoding="utf-8")
        benchmark = self.inputs()["benchmark"]
        self.assertEqual("INVALID", benchmark["status"])
        self.assertEqual({}, benchmark["closes"])
        self.assertIn("CLOSE_HISTORY_HASH_MISMATCH", benchmark["errors"])
        self.assertEqual("INVALID", self.report_benchmark(self.inputs())["status"])

    def test_e2_history_not_json_is_invalid(self) -> None:
        target = self.write_history(CLOSES)
        target.write_text("{not json", encoding="utf-8")
        benchmark = self.inputs()["benchmark"]
        self.assertEqual("INVALID", benchmark["status"])
        self.assertEqual({}, benchmark["closes"])
        self.assertEqual(["CLOSE_HISTORY_NOT_JSON"], benchmark["errors"])

    def test_e3_unverified_session_is_left_out(self) -> None:
        self.write_history({**CLOSES, WINTER_SESSION: "480.00"})
        history = json.loads((self.closes_root / "history/SPY.close-history.json").read_text(encoding="utf-8"))
        winter = next(item for item in history["sessions"] if item["session_date"] == WINTER_SESSION)
        self.assertTrue(winter["unverified_reasons"], "fixture must hold an unverified session")
        benchmark = self.inputs()["benchmark"]
        self.assertEqual("OK", benchmark["status"])
        self.assertNotIn(WINTER_SESSION, benchmark["closes"])
        self.assertEqual(CLOSES, benchmark["closes"])

    def test_e4_only_unverified_sessions_is_invalid(self) -> None:
        self.write_history({WINTER_SESSION: "480.00", "2026-01-06": "481.00"})
        benchmark = self.inputs()["benchmark"]
        self.assertEqual("INVALID", benchmark["status"])
        self.assertEqual({}, benchmark["closes"])
        self.assertEqual(["CLOSE_HISTORY_NO_VERIFIED_SESSIONS"], benchmark["errors"])

    def test_f_no_calendar_keeps_missing(self) -> None:
        self.write_history(CLOSES)
        self.assertEqual({"status": "MISSING", "closes": {}, "errors": []},
                         scorer.load_benchmark_closes(self.closes_root, None, lambda *_args: self.fail("no read")))


if __name__ == "__main__":
    unittest.main()
