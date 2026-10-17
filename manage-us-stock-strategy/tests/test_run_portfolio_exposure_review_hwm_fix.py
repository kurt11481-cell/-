"""hwm-fix runner side: each replayed ledger revision is linked to its broker read (temp folders only).

ledger proposal_id -> saved reconciliation proposal (content hash) -> broker snapshot (snapshot hash) ->
verified cash and the same holdings. Anything else leaves that revision without a capture and says why.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import apply_user_confirmed_broker_snapshot as apply_module  # noqa: E402
import run_portfolio_exposure_review as runner  # noqa: E402
from kiwoom_broker_shadow import proposal_content_hash  # noqa: E402
from test_run_portfolio_exposure_review import EVAL, RunnerCase, broker_record  # noqa: E402
from validation_common import canonical_hash  # noqa: E402

READS = {15: ("2026-09-28T23:00:00.100000Z", "2026-09-28T23:00:01.200000+00:00"),
         16: ("2026-09-29T23:10:00.100000Z", "2026-09-29T23:10:01.200000+00:00")}


def broker_snapshot(holdings: dict[str, float], *, order_available: float, deposit: float, d1_sell: float = 0.0,
                    cash_status: str = "VERIFIED_POSITIVE") -> dict[str, Any]:
    """The fields of kiwoom_broker_shadow.normalize_snapshot that the link reads (synthetic values)."""
    snapshot = {
        "schema_version": "1.0", "status": "KIWOOM_BROKER_SNAPSHOT_SHADOW", "account_identifier_stored": False,
        "holdings": [{"ticker": ticker, "held_quantity": quantity, "settled_quantity": quantity}
                     for ticker, quantity in sorted(holdings.items())],
        "cash": {"currency": "USD", "foreign_currency_deposit": deposit, "withdrawable_cash": deposit,
                 "order_available_cash": order_available, "settled_available_cash": min(deposit, order_available),
                 "cash_status": cash_status,
                 "unsettled_funds": {"d1_sell_settlement_usd": d1_sell, "d1_buy_settlement_usd": 0.0,
                                     "d2_sell_settlement_usd": 0.0, "d2_buy_settlement_usd": 0.0}},
        "snapshot_hash": "0" * 64,
    }
    snapshot["snapshot_hash"] = canonical_hash({key: value for key, value in snapshot.items() if key != "snapshot_hash"})
    return snapshot


class CaptureCase(RunnerCase):
    def states(self) -> list[dict]:
        base = {"schema_version": "1.3", "state_revision": 14, "holdings": {"SOXL": 30, "MVLL": 10},
                "available_cash_usd": 6500.0, "last_confirmed_broker_snapshot": broker_record("2026-09-25")}
        second = dict(base, state_revision=15, holdings={"SOXL": 30}, available_cash_usd=6500.0,
                      last_confirmed_broker_snapshot=broker_record("2026-09-28"))
        third = dict(second, state_revision=16, available_cash_usd=7000.0,
                     last_confirmed_broker_snapshot=broker_record("2026-09-29"))
        return [base, second, third]

    def save_proposal(self, revision: int, snapshot: dict[str, Any], **source: Any) -> str:
        folder = Path("workspace/outputs/reconciliation") / f"R{revision}"
        (self.root / folder).mkdir(parents=True, exist_ok=True)
        (self.root / folder / "kiwoom_broker_snapshot.shadow.json").write_text(json.dumps(snapshot), encoding="utf-8")
        earliest, latest = READS[revision]
        proposal = {"schema_version": "kiwoom-reconciliation-1.0", "proposal_id": "", "confirm_code": "",
                    "source": {"snapshot_hash": snapshot["snapshot_hash"],
                               "snapshot_path": (folder / "kiwoom_broker_snapshot.shadow.json").as_posix(),
                               "earliest_required_retrieved_at": earliest, "broker_snapshot_as_of": latest, **source}}
        proposal["proposal_id"] = proposal_content_hash(proposal)
        proposal["confirm_code"] = "TESTONLY"
        (self.root / folder / "reconciliation_proposal.json").write_text(json.dumps(proposal), encoding="utf-8")
        return proposal["proposal_id"]

    def append(self, before: dict, after: dict, changes: list[dict], proposal_id: Any) -> None:
        status = apply_module.ledger_status(self.ledger_path)
        entry = {"schema_version": "1.0", "event": "APPLY", "proposal_schema_version": "kiwoom-reconciliation-1.0",
                 "proposal_id": proposal_id, "confirmed_at": "2026-09-30T00:00:00+00:00",
                 "state_revision_before": before["state_revision"], "state_revision_after": after["state_revision"],
                 "portfolio_hash_before": canonical_hash(before), "portfolio_hash_after": canonical_hash(after),
                 "changes": changes, "state_changed_outside_ledger": False,
                 "previous_entry_sha256": status["last_entry_sha256"]}
        apply_module._append_ledger(self.ledger_path, entry)

    def write_linked_ledger(self, ids: tuple[Any, Any]) -> None:
        base, second, third = self.states()
        self.append(base, second, [
            {"field": "holdings", "key": "MVLL", "old_value": 10, "new_value": None},
            {"field": "last_confirmed_broker_snapshot", "key": "as_of", "old_value": "2026-09-25",
             "new_value": "2026-09-28"}], ids[0])
        self.append(second, third, [
            {"field": "available_cash_usd", "key": None, "old_value": 6500.0, "new_value": 7000.0},
            {"field": "last_confirmed_broker_snapshot", "key": "as_of", "old_value": "2026-09-28",
             "new_value": "2026-09-29"}], ids[1])
        self.state_path.write_text(json.dumps(third, indent=2), encoding="utf-8")

    def replay(self) -> tuple[list[dict], list[dict]]:
        entries = runner.read_ledger_entries(self.ledger_path)
        snapshots, _, _ = runner.reconstruct_snapshots(json.loads(self.state_path.read_text(encoding="utf-8")),
                                                       entries, chain_ok=True, ledger_exists=True)
        return snapshots, entries

    def default_ids(self) -> tuple[str, str]:
        return (self.save_proposal(15, broker_snapshot({"SOXL": 30.0}, order_available=7000.0, deposit=6500.0,
                                                       d1_sell=500.0)),
                self.save_proposal(16, broker_snapshot({"SOXL": 30.0}, order_available=7000.0, deposit=7000.0)))


class BrokerCaptureTests(CaptureCase):
    def test_r1_linked_revisions_get_a_capture_and_the_replay_is_unchanged(self) -> None:
        self.write_linked_ledger(self.default_ids())
        snapshots, entries = self.replay()
        before = copy.deepcopy(snapshots)
        captures, notes = runner.broker_captures(snapshots, entries, self.root)
        self.assertEqual(snapshots, before)
        self.assertEqual(notes, [])
        self.assertEqual(sorted(captures), [15, 16])  # the base state (revision 14) has no capture and no note
        self.assertEqual(captures[15], {
            "earliest_read_at": READS[15][0], "latest_read_at": READS[15][1], "order_available_cash_usd": "7000.0",
            "foreign_currency_deposit_usd": "6500.0",
            "unsettled": {"d1_sell_settlement_usd": "500.0", "d1_buy_settlement_usd": "0.0",
                          "d2_sell_settlement_usd": "0.0", "d2_buy_settlement_usd": "0.0"},
            "proposal_id": entries[0]["proposal_id"],
            "snapshot_hash": broker_snapshot({"SOXL": 30.0}, order_available=7000.0, deposit=6500.0,
                                             d1_sell=500.0)["snapshot_hash"]})
        self.assertEqual(captures[16]["order_available_cash_usd"], "7000.0")
        # reconstruct_snapshots itself is untouched (same keys and values as test_run_portfolio_exposure_review).
        self.assertEqual([(item["state_revision"], item["as_of"], item["holdings"], item["cash_usd"],
                           item["holdings_decreased"], item["from_ledger_entry"]) for item in snapshots], [
            (14, "2026-09-25", {"SOXL": 30, "MVLL": 10}, "6500.0", False, False),
            (15, "2026-09-28", {"SOXL": 30}, "6500.0", True, True),
            (16, "2026-09-29", {"SOXL": 30}, "7000.0", False, True)])

    def unlinked(self, ids: tuple[Any, Any]) -> tuple[dict, list[str]]:
        if self.ledger_path.exists():
            self.ledger_path.unlink()
        self.write_linked_ledger(ids)
        snapshots, entries = self.replay()
        return runner.broker_captures(snapshots, entries, self.root)

    def test_r2_each_broken_link_leaves_no_capture_and_a_reason(self) -> None:
        good = self.default_ids()
        cases = []
        cases.append(((None, good[1]), "15:PROPOSAL_ID_MISSING"))
        cases.append((("f" * 64, good[1]), "15:PROPOSAL_NOT_FOUND"))
        # A proposal file edited after it was hashed.
        path = self.root / "workspace/outputs/reconciliation/R15/reconciliation_proposal.json"
        edited = json.loads(path.read_text(encoding="utf-8"))
        edited["source"]["broker_snapshot_as_of"] = "2026-09-28T23:59:00+00:00"
        bad_dir = self.root / "workspace/outputs/reconciliation/R15-edited"
        bad_dir.mkdir(parents=True)
        (bad_dir / "reconciliation_proposal.json").write_text(json.dumps(edited), encoding="utf-8")
        path.unlink()
        cases.append(((good[0], good[1]), "15:PROPOSAL_HASH_MISMATCH"))
        for ids, reason in cases:
            with self.subTest(reason=reason):
                captures, notes = self.unlinked(ids)
                self.assertIsNone(captures[15])
                self.assertEqual(notes, [f"BROKER_CAPTURE_UNLINKED:{reason}"])
                self.assertIsNotNone(captures[16])

    def test_r2_snapshot_cash_and_holdings_defects(self) -> None:
        second = self.save_proposal(16, broker_snapshot({"SOXL": 30.0}, order_available=7000.0, deposit=7000.0))
        snapshot = broker_snapshot({"SOXL": 30.0}, order_available=7000.0, deposit=6500.0, d1_sell=500.0)
        tampered = dict(snapshot, cash=dict(snapshot["cash"], order_available_cash=7100.0))  # hash no longer matches
        for variant, reason in (
                (tampered, "SNAPSHOT_HASH_MISMATCH"),
                (broker_snapshot({"SOXL": 31.0}, order_available=7000.0, deposit=6500.0), "HOLDINGS_MISMATCH"),
                (broker_snapshot({"SOXL": 30.0}, order_available=7000.0, deposit=6500.0, cash_status="UNVERIFIED"),
                 "CASH_NOT_VERIFIED"),
                (broker_snapshot({"SOXL": 30.0}, order_available=-1.0, deposit=6500.0), "CASH_AMOUNT_INVALID")):
            with self.subTest(reason=reason):
                folder = self.root / "workspace/outputs/reconciliation/R15"
                if folder.exists():
                    for item in folder.iterdir():
                        item.unlink()
                proposal_id = self.save_proposal(15, variant)
                captures, notes = self.unlinked((proposal_id, second))
                self.assertIsNone(captures[15])
                self.assertEqual(notes, [f"BROKER_CAPTURE_UNLINKED:15:{reason}"])
        # The snapshot file itself missing.
        (folder / "kiwoom_broker_snapshot.shadow.json").unlink()
        proposal = json.loads((folder / "reconciliation_proposal.json").read_text(encoding="utf-8"))
        captures, notes = self.unlinked((proposal["proposal_id"], second))
        self.assertEqual(notes, ["BROKER_CAPTURE_UNLINKED:15:SNAPSHOT_NOT_FOUND"])

    def test_r3_auto_core_ledger_snapshot_after_reads_the_same_holdings_and_cash(self) -> None:
        import auto_core  # noqa: PLC0415 - the compare-streak reader of reconstruct_snapshots

        self.write_linked_ledger(self.default_ids())
        found = auto_core._ledger_snapshot_after(self.state_path, "2026-09-29T00:00:00+00:00")
        self.assertEqual((found["state_revision"], found["holdings"], found["cash_usd"]), (15, {"SOXL": 30}, "6500.0"))

    def test_r4_the_run_passes_captures_and_session_times_and_labels_another_evidence_root(self) -> None:
        self.write_linked_ledger(self.default_ids())
        self.write_default_histories()
        seen: list[dict] = []
        real = runner.build_exposure_review

        def spy(**kwargs: Any) -> dict:
            seen.append(kwargs)
            return real(**kwargs)

        with mock.patch.object(runner, "build_exposure_review", side_effect=spy):
            _, _, default_review = self.run_review()
            _, _, other_review = self.run_review("--evidence-root", str(self.root))
        self.assertEqual(sorted(seen[0]["broker_captures"]), [15, 16])
        self.assertTrue(all(value is None for value in seen[0]["broker_captures"].values()))  # nothing under the repo
        self.assertTrue(all(value is not None for value in seen[1]["broker_captures"].values()))
        self.assertEqual(sorted(seen[1]["session_bounds"][EVAL]), ["core_close_at", "core_open_at"])
        self.assertNotIn("evidence_root", default_review["inputs"]["non_default_inputs"])
        self.assertIn("evidence_root", other_review["inputs"]["non_default_inputs"])
        self.assertEqual(other_review["inputs"]["ledger_replay_notes"], [])
        self.assertEqual(default_review["inputs"]["ledger_replay_notes"],
                         ["BROKER_CAPTURE_UNLINKED:15:PROPOSAL_NOT_FOUND", "BROKER_CAPTURE_UNLINKED:16:PROPOSAL_NOT_FOUND"])


if __name__ == "__main__":
    unittest.main()
