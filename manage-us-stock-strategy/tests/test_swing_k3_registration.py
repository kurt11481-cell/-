"""swing-k3: PLTR and CRWD added to the approved new-buy products; canonical instrument registry filled.

Reads the real registry, alert policy and auto_core_tickets constants. Holdings for the reconciliation
check are synthetic (BE, LITE, SOXL). Nothing here writes a repository file or calls a broker.
"""

from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import auto_core_tickets as tickets  # noqa: E402
import portfolio_exposure as pe  # noqa: E402
import reconcile_broker_state as cli  # noqa: E402
from validate_registry_consistency import validate_registry_consistency  # noqa: E402
from validation_common import canonical_hash  # noqa: E402

REGISTRY = REPO_ROOT / "workspace/policies/instrument_registry.json"
POLICY = REPO_ROOT / "stock-strategy-system/alert_policy.json"
REGISTERED = ("LITE", "PWR", "MU", "DELL", "AMD", "TQQQ", "PLTR", "CRWD")
NEW_APPROVED = ("PLTR", "CRWD")
APPROVED_BEFORE = ("BE", "MU", "NBIS", "DELL", "AMD", "SOXL", "TQQQ", "DRAM", "PWR", "LITE")
CARD_STOCK_CORE_BEFORE = ["BE", "MU", "NBIS", "DELL", "AMD", "PWR", "LITE"]
IDENTITY_ERROR = "canonical instrument registry record is missing or unverified"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class RegistryRecordTests(unittest.TestCase):
    """(a) (b) the eight registry records and the policy hash."""

    def test_a_eight_symbols_are_verified_and_none_is_buy_approved(self) -> None:
        instruments = _load(REGISTRY)["instruments"]
        for symbol in REGISTERED:
            with self.subTest(symbol=symbol):
                record = instruments[symbol]
                self.assertTrue(record["identity_status"].startswith("verified"))
                self.assertEqual(record["identity_verification_status"], "VERIFIED")
                self.assertTrue(record["official_identity_source_url"].startswith("https://www.sec.gov/Archives/edgar/data/"))
                self.assertEqual(record["leverage_factor_status"], "verified")
                self.assertIs(record["watchlist_approved"], False)
                self.assertEqual(record["candidate_status"], "inactive")
                self.assertIs(record["short_sale_approved"], False)
        for symbol, record in instruments.items():
            with self.subTest(symbol=symbol):
                self.assertIs(record["new_buy_instrument_approved"], False)
        self.assertEqual((instruments["TQQQ"]["instrument_type"], instruments["TQQQ"]["leverage_factor"],
                          instruments["TQQQ"]["daily_target_multiple"], instruments["TQQQ"]["confirmation_proxy"]),
                         ("leveraged_etf", 3.0, 3.0, "QQQ"))
        for symbol in ("LITE", "PWR", "MU", "DELL", "AMD", "PLTR", "CRWD"):
            self.assertEqual((instruments[symbol]["instrument_type"], instruments[symbol]["leverage_factor"]),
                             ("stock", 1.0))
        self.assertIs(_load(REGISTRY)["authority"]["can_place_or_schedule_orders"], False)

    def test_b_registry_and_policy_hash_validate(self) -> None:
        registry, policy = _load(REGISTRY), _load(POLICY)
        result = validate_registry_consistency(registry, policy, REGISTRY)
        self.assertEqual(result["status"], "VALIDATED", result["errors"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(policy["decision_harness"]["instrument_registry_authority"]["required_canonical_sha256"],
                         canonical_hash(registry))
        self.assertFalse(result["order_authority"])


class PolicyValueTests(unittest.TestCase):
    """(c) PLTR and CRWD enter the exposure policy; thresholds and existing order stay."""

    def test_c_policy_adds_pltr_crwd_only(self) -> None:
        section = _load(POLICY)["portfolio_exposure_policy"]
        for symbol in NEW_APPROVED:
            self.assertEqual(section["nominal_multipliers"][symbol], 1)
        self.assertEqual(section["card_stock_core"], CARD_STOCK_CORE_BEFORE + list(NEW_APPROVED))
        self.assertEqual(section["card_stock_core"][:7], CARD_STOCK_CORE_BEFORE)
        thresholds = section["thresholds"]
        self.assertEqual(thresholds["hard_ceiling_when_exposure_gte"], 1.9)
        self.assertEqual(thresholds["reduce_when_exposure_gte"], 1.85)
        self.assertEqual(section["target_exposure"], 1.55)
        self.assertEqual(section["single_stock_nominal_cap"], 0.4)
        self.assertEqual(section["allowed_index_etfs"], ["SOXL", "TQQQ", "DRAM", "QQQ"])
        self.assertEqual(section["add_default"], "card_add_stock_only")  # policy-a-1126
        self.assertIs(section["order_authority"], False)
        self.assertEqual(section["quantity_authority"], "none")

    def test_c_missing_earnings_record_blocks_the_new_card_stocks(self) -> None:
        config = pe.exposure_config(_load(POLICY))
        for symbol in NEW_APPROVED:
            self.assertEqual(pe.increase_blockers(symbol, config=config, weights={}, peaks={}, earnings=None,
                                                  calendar_sessions=[], buy_session=None),
                             ["EARNINGS_DATE_UNVERIFIED"])


class TicketConstantTests(unittest.TestCase):
    """(d) APPROVED_BUY gains PLTR and CRWD; the index and parking lists stay."""

    def test_d_approved_buy(self) -> None:
        self.assertEqual(tickets.APPROVED_BUY, APPROVED_BEFORE + NEW_APPROVED)
        self.assertEqual(tickets.INDEX_ETFS, ("SOXL", "TQQQ", "DRAM", "QQQ"))
        self.assertEqual(tickets.PARKING_ETFS, ("QQQ",))
        self.assertEqual(tickets.AUTHORITY, {"order_authority": False, "quantity_authority": "ORDER_TICKET_HUMAN_ENTRY",
                                             "execution_quantity": None})


class ReconcileIdentityTests(unittest.TestCase):
    """(e) the post-apply alert-engine check no longer reports LITE as an unverified registry record."""

    def test_e_canonical_identity_has_no_missing_record(self) -> None:
        self.assertEqual(cli.canonical_identity_errors(set(REGISTERED) | {"BE", "SOXL"}, REGISTRY), [])

    def test_e_alert_engine_check_with_synthetic_be_lite_soxl(self) -> None:
        import apply_user_confirmed_broker_snapshot as apply_module
        import test_reconcile_broker_state as recon

        policy = _load(POLICY)
        state = recon.base_state()
        state["strategy_version"] = policy["strategy_version"]
        rows = [recon.holding_row("BE", "4", "150.5", evaluation="700", pnl="98"),
                recon.holding_row("LITE", "2", "80.25", evaluation="200", pnl="39.5"),
                recon.holding_row("SOXL", "10", "30.75", evaluation="400", pnl="92.5")]
        results = recon.account_results(recon.utc(datetime.now(timezone.utc) - timedelta(seconds=30)), holdings=rows)
        check = cli.alert_engine_check(policy, registry_path=REGISTRY)
        proposal = recon.make_proposal(state, results=results, check=check)
        preview = apply_module.preview_updated_state(state, proposal)
        self.assertEqual({ticker for ticker, quantity in preview["holdings"].items() if quantity > 0},
                         {"BE", "LITE", "SOXL"})
        errors = check(state, proposal)["errors"]
        self.assertFalse([error for error in errors if IDENTITY_ERROR in error], errors)


class ContrastTests(unittest.TestCase):
    """(f) symbols outside the change stay blocked."""

    def test_f_unregistered_and_unapproved_stay_blocked(self) -> None:
        config = pe.exposure_config(_load(POLICY))
        self.assertEqual(pe.increase_blockers("XLE", config=config, weights={}, peaks={}, earnings=None,
                                              calendar_sessions=[], buy_session=None), ["UNREGISTERED_INSTRUMENT"])
        self.assertNotIn("NOW", tickets.APPROVED_BUY)
        self.assertNotIn("PANW", tickets.APPROVED_BUY)
        self.assertEqual(cli.canonical_identity_errors({"PANW"}, REGISTRY), [f"PANW: {IDENTITY_ERROR}"])


if __name__ == "__main__":
    unittest.main()
