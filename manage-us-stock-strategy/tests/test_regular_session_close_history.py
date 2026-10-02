"""Regular-session close history from saved Kiwoom 30-minute pages (P3: final regular bar, start-time label)."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock
from datetime import datetime, timezone

SKILL_ROOT = Path(__file__).resolve().parents[1]
ROOT = SKILL_ROOT.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import regular_session_close_history as rsch  # noqa: E402
from test_s7_calendar_binding import SESSION_0829, build_authority_root  # noqa: E402

# Market data only (SOXX 30-minute bars saved by Cowork on 2026-10-01); no account data.
FIXTURE_PAGES = SKILL_ROOT / "tests/fixtures/regular-session-closes/SOXX"
# Full-year 2026 calendar artifact (the one the Production integrated authority activates).
CALENDAR = (ROOT / "workspace/calendar-authority/artifacts"
            / "2421eeb7e115ad640b6b0ec76d0d88cfe2a49499c12c39dc35ea5f71c1fed22b/us-equities-core-session-v2.calendar.json")


def row(stamp: str, close: str, marker: str = "") -> dict[str, str]:
    return {"cur_prc": close, "trde_qty": "100", "open_pric": close, "high_pric": close, "low_pric": close,
            "cntr_tm": stamp, "bus_dt": stamp[:8], "upd_stkpc_tp": marker, "upd_rt": ""}


def page(rows: list[tuple[str, str]]) -> dict[str, Any]:
    """Rows newest first; the last row carries the page-end marker like a real page."""
    items = [row(stamp, close) for stamp, close in rows]
    items[-1]["upd_stkpc_tp"] = "1f"
    return {"result": {"result_list": items, "return_code": 0, "return_msg": "ok"}}


class CloseHistoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="close_history_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.calendar = rsch.load_calendar(CALENDAR, None)

    def pages_dir(self, symbol: str, documents: dict[str, Any]) -> Path:
        folder = self.tmp / "pages" / symbol
        folder.mkdir(parents=True)
        for name, document in documents.items():
            (folder / name).write_text(json.dumps(document), encoding="utf-8")
        return folder

    def sample_dir(self) -> Path:
        folder = self.tmp / "pages" / "SOXX"
        shutil.copytree(FIXTURE_PAGES, folder)
        return folder

    def build(self, folder: Path, symbol: str = "SOXX", **extra: Any) -> dict[str, Any]:
        return rsch.build_history(symbol=symbol, exchange="NASDAQ", page_paths=sorted(folder.glob("*.json")),
                                  calendar=extra.pop("calendar", self.calendar), **extra)

    def test_real_sample_picks_the_1530_bar_close_not_the_1600_bar(self) -> None:
        history = self.build(self.sample_dir())
        self.assertEqual(rsch.history_errors(history), [])
        closes = rsch.closes_by_session(history)
        self.assertEqual(list(closes), ["2026-09-24", "2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30"])
        self.assertEqual((closes["2026-09-30"], closes["2026-09-29"]), ("568.2000", "567.4500"))
        self.assertNotEqual(closes["2026-09-30"], "570.8000")  # 16:00 bar close includes after-hours trades
        self.assertNotEqual(closes["2026-09-30"], "568.6400")  # 16:00 bar open
        self.assertEqual({item["bar_cntr_tm"][8:] for item in history["sessions"]}, {"153000"})
        self.assertEqual(history["continuity"], {"status": "CONTIGUOUS", "missing_sessions": []})
        self.assertEqual(history["close_definition"]["label"], "APPROXIMATE_CLOSE")
        self.assertIs(history["close_definition"]["official_close"], False)
        self.assertEqual(history["source"]["price_adjustment"], "RAW_UNADJUSTED")
        self.assertEqual((history["order_authority"], history["quantity_authority"]), (False, "none"))
        self.assertEqual([item["sha256"] for item in history["pages"]], [
            hashlib.sha256((FIXTURE_PAGES / name).read_bytes()).hexdigest()
            for name in ("soxx_30m_20260930_p1.json", "soxx_30m_20260930_p2.json")])

    def test_page_end_marker_is_not_an_adjustment_flag_but_other_markers_are_rejected(self) -> None:
        folder = self.sample_dir()
        document = json.loads((folder / "soxx_30m_20260930_p1.json").read_text(encoding="utf-8"))
        self.assertEqual(document["result"]["result_list"][99]["upd_stkpc_tp"], "1f")
        document["result"]["result_list"][10]["upd_stkpc_tp"] = "1f"
        (folder / "soxx_30m_20260930_p1.json").write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaisesRegex(rsch.CloseHistoryError, "PAGE_ADJUSTMENT_FIELD_UNEXPECTED"):
            self.build(folder)
        document["result"]["result_list"][10]["upd_stkpc_tp"] = ""
        document["result"]["result_list"][10]["upd_rt"] = "0.5"
        (folder / "soxx_30m_20260930_p1.json").write_text(json.dumps(document), encoding="utf-8")
        with self.assertRaisesRegex(rsch.CloseHistoryError, "PAGE_ADJUSTMENT_FIELD_UNEXPECTED"):
            self.build(folder)

    def test_calendar_that_is_not_the_active_authority_leaves_closes_unverified(self) -> None:
        history = self.build(self.sample_dir())
        self.assertEqual(history["calendar"]["authority_status"], "EXPLICIT_ARTIFACT_NOT_ACTIVE")
        self.assertTrue(all(item["verified"] is False and item["unverified_reasons"] == ["SESSION_CALENDAR_NOT_ACTIVE"]
                            for item in history["sessions"]))
        self.assertEqual(rsch.unverified_reasons(history, ["2026-09-30"]), ["SESSION_CALENDAR_NOT_ACTIVE"])
        # The calendar is ACTIVE only when it is the one the integrated authority activates (hash equality).
        trusted = self.tmp / "trusted"
        calendar_copy = build_authority_root(trusted, extra_calendars=(SESSION_0829,))
        with mock.patch.object(rsch, "TRUSTED_ROOT", trusted):
            snapshot, failure = rsch.load_production_snapshot(datetime(2026, 10, 1, tzinfo=timezone.utc))
        self.assertIsNone(failure)
        active = rsch.load_calendar(calendar_copy, snapshot)
        self.assertEqual(active["identity"]["authority_status"], "ACTIVE")
        history = self.build(self.tmp / "pages" / "SOXX", calendar=active)
        self.assertTrue(all(item["verified"] and not item["unverified_reasons"] for item in history["sessions"]))
        other = trusted / "workspace/calendar-authority/artifacts" / SESSION_0829 / calendar_copy.name
        self.assertEqual(rsch.load_calendar(other, snapshot)["identity"]["authority_status"],
                         "EXPLICIT_ARTIFACT_NOT_ACTIVE")

    def test_newest_bar_of_a_file_is_not_trusted_as_complete(self) -> None:
        folder = self.pages_dir("TEST", {"p1.json": page([
            ("20260930153000", "10.50"), ("20260930150000", "10.40"),
            ("20260929160000", "10.30"), ("20260929153000", "10.20"), ("20260929150000", "10.10")])})
        history = self.build(folder, "TEST")
        self.assertEqual(rsch.closes_by_session(history), {"2026-09-29": "10.20"})  # 9/30 15:30 may still be forming
        folder = self.pages_dir("TESTB", {"p1.json": page([
            ("20260930160000", "10.60"), ("20260930153000", "10.50"), ("20260929153000", "10.20"),
            ("20260929150000", "10.10")])})
        self.assertEqual(rsch.closes_by_session(self.build(folder, "TESTB")),
                         {"2026-09-29": "10.20", "2026-09-30": "10.50"})

    def test_early_close_uses_the_bar_before_the_early_close(self) -> None:
        folder = self.pages_dir("TEST", {"p1.json": page([
            ("20261127133000", "9.99"), ("20261127130000", "9.90"), ("20261127123000", "9.80"),
            ("20261127120000", "9.70"), ("20261125153000", "9.50"), ("20261125150000", "9.40")])})
        history = self.build(folder, "TEST")
        early = history["sessions"][-1]
        self.assertEqual((early["session_date"], early["close"], early["bar_cntr_tm"], early["close_type"]),
                         ("2026-11-27", "9.80", "20261127123000", "EARLY"))
        # Bar labels were measured only under UTC-04:00; standard-time sessions stay unverified.
        self.assertIn("BAR_LABEL_TIMEZONE_UNVERIFIED_FOR_UTC_OFFSET", early["unverified_reasons"])
        self.assertFalse(early["verified"])

    def test_missing_session_inside_the_range_is_reported_as_a_gap(self) -> None:
        folder = self.pages_dir("TEST", {"p1.json": page([
            ("20260930160000", "3"), ("20260930153000", "3"), ("20260928153000", "1"), ("20260928150000", "1")])})
        history = self.build(folder, "TEST")
        self.assertEqual(history["continuity"], {"status": "GAPS", "missing_sessions": ["2026-09-29"]})
        self.assertNotIn("2026-09-29", rsch.closes_by_session(history))
        self.assertIn("CLOSE_HISTORY_GAP", rsch.unverified_reasons(history, ["2026-09-29"]))

    def test_conflicting_rows_between_pages_are_rejected(self) -> None:
        rows = [("20260930160000", "3"), ("20260930153000", "3"), ("20260929153000", "2"), ("20260929150000", "2")]
        changed = [("20260930160000", "3"), ("20260930153000", "3.01"), ("20260929153000", "2"),
                   ("20260929150000", "2")]
        folder = self.pages_dir("TEST", {"p1.json": page(rows), "p2.json": page(changed)})
        with self.assertRaisesRegex(rsch.CloseHistoryError, "PAGE_ROWS_CONFLICT:20260930153000"):
            self.build(folder, "TEST")

    def test_page_folder_must_be_named_after_the_symbol(self) -> None:
        with self.assertRaisesRegex(rsch.CloseHistoryError, "PAGE_FOLDER_SYMBOL_MISMATCH"):
            self.build(self.sample_dir(), "SOXL")

    def test_malformed_pages_are_rejected(self) -> None:
        good = [("20260930160000", "3"), ("20260930153000", "3"), ("20260929153000", "2")]
        cases = {
            "PAGE_ROW_ORDER_INVALID": page(list(reversed(good))),
            "PAGE_ROW_TIME_INVALID": page(good[:2] + [("20260929151500", "2")]),
            "PAGE_ROW_PRICE_INVALID": page(good[:2] + [("20260929153000", "0")]),
            "PAGE_RETURN_CODE_NOT_ZERO": {"result": {"result_list": [row("20260930153000", "1")], "return_code": 5}},
            "PAGE_SHAPE_INVALID": {"result": {"result_list": [], "return_code": 0}},
        }
        for index, (code, document) in enumerate(cases.items()):
            folder = self.pages_dir(f"T{index}", {"p1.json": document})
            with self.assertRaisesRegex(rsch.CloseHistoryError, code):
                self.build(folder, f"T{index}")
        document = page(good)
        document["result"]["result_list"][0]["extra"] = "x"
        with self.assertRaisesRegex(rsch.CloseHistoryError, "PAGE_ROW_KEYS_INVALID"):
            self.build(self.pages_dir("T9", {"p1.json": document}), "T9")
        folder = self.pages_dir("T8", {"p1.json": page(good), "p2.json": page(good)})
        with self.assertRaisesRegex(rsch.CloseHistoryError, "PAGE_DUPLICATE"):
            self.build(folder, "T8")

    def test_tampered_history_or_page_is_detected(self) -> None:
        folder = self.sample_dir()
        history = self.build(folder)
        self.assertEqual(rsch.history_errors(history, pages_dir=folder), [])
        tampered = json.loads(json.dumps(history))
        tampered["sessions"][-1]["close"] = "600.0000"
        self.assertEqual(rsch.history_errors(tampered), ["CLOSE_HISTORY_HASH_MISMATCH"])
        (folder / "soxx_30m_20260930_p1.json").write_bytes(
            (folder / "soxx_30m_20260930_p1.json").read_bytes().replace(b"568.2000", b"568.2100"))
        self.assertEqual(rsch.history_errors(history, pages_dir=folder),
                         ["CLOSE_HISTORY_PAGE_HASH_MISMATCH:soxx_30m_20260930_p1.json"])
        (folder / "soxx_30m_20260930_p2.json").unlink()
        self.assertIn("CLOSE_HISTORY_PAGE_MISSING:soxx_30m_20260930_p2.json",
                      rsch.history_errors(history, pages_dir=folder))

    def test_reference_close_is_shown_as_a_difference_only(self) -> None:
        folder = self.sample_dir()
        plain = self.build(folder)
        history = self.build(folder, reference_closes={"2026-09-30": "570.80"})
        last = history["sessions"][-1]
        self.assertEqual((last["close"], last["reference_close"], last["reference_difference"]),
                         ("568.2000", "570.80", "-2.6000"))
        self.assertEqual(rsch.closes_by_session(history), rsch.closes_by_session(plain))
        self.assertEqual([item["verified"] for item in history["sessions"]],
                         [item["verified"] for item in plain["sessions"]])

    def test_cli_build_is_create_only_and_verify_rechecks(self) -> None:
        folder = self.sample_dir()
        output = self.tmp / "history" / "SOXX.close-history.json"
        arguments = ["build", "--symbol", "SOXX", "--exchange", "NASDAQ", "--pages-dir", str(folder),
                     "--calendar", str(CALENDAR), "--output", str(output)]
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit), \
                mock.patch("sys.stderr", io.StringIO()):
            rsch.main(arguments + ["--calendar-activation", str(self.tmp / "fake.json")])  # no such override
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rsch.main(arguments), 0)
            self.assertEqual(rsch.main(arguments), 2)  # never overwrites
            self.assertEqual(rsch.main(["verify", "--history", str(output), "--pages-dir", str(folder)]), 0)
            output.write_text(output.read_text(encoding="utf-8").replace("568.2000", "568.2001"), encoding="utf-8")
            self.assertEqual(rsch.main(["verify", "--history", str(output)]), 2)

    def test_update_extends_a_history_but_never_changes_an_earlier_close(self) -> None:
        first = [("20260929160000", "2"), ("20260929153000", "2"), ("20260928153000", "1"), ("20260928150000", "1")]
        folder = self.pages_dir("TEST", {"p1.json": page(first)})
        output = self.tmp / "history" / "TEST.close-history.json"
        arguments = ["build", "--symbol", "TEST", "--exchange", "NASDAQ", "--pages-dir", str(folder),
                     "--calendar", str(CALENDAR), "--output", str(output)]
        with contextlib.redirect_stdout(io.StringIO()) as buffer:
            self.assertEqual(rsch.main(arguments), 0)
            (folder / "p2.json").write_text(json.dumps(page(
                [("20260930160000", "3"), ("20260930153000", "3"), ("20260929153000", "2")])), encoding="utf-8")
            self.assertEqual(rsch.main(arguments), 2)  # still create-only without --update
            self.assertEqual(rsch.main(arguments + ["--update"]), 0)
            self.assertEqual(rsch.closes_by_session(json.loads(output.read_text(encoding="utf-8"))),
                             {"2026-09-28": "1", "2026-09-29": "2", "2026-09-30": "3"})
            # A page set that would change or drop an earlier session is refused.
            (folder / "p1.json").unlink()
            self.assertEqual(rsch.main(arguments + ["--update"]), 2)
        self.assertIn("CLOSE_HISTORY_UPDATE_CHANGES_EARLIER_SESSION:2026-09-28", buffer.getvalue())
        self.assertEqual(len(rsch.closes_by_session(json.loads(output.read_text(encoding="utf-8")))), 3)

    def test_invalid_calendar_is_rejected(self) -> None:
        bad = self.tmp / "calendar.json"
        bad.write_text(json.dumps({"sessions": []}), encoding="utf-8")
        with self.assertRaisesRegex(rsch.CloseHistoryError, "CALENDAR_ARTIFACT_INVALID"):
            rsch.load_calendar(bad, None)


if __name__ == "__main__":
    unittest.main()
