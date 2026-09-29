#!/usr/bin/env python3
"""Production binding checks for the approved 2026-09-03 K3 calendar recovery."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "manage-us-stock-strategy/scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from integrated_authority_snapshot import (  # noqa: E402
    derive_us_market_session_authority_from_snapshot,
    load_production_integrated_authority_snapshot,
)


COHORT = "identity-session-k3-prod-20260903-v1"
IDENTITY_HASH = "d8b03aa434c969e8fba338865eb3e6567bc78821d9b7b702e47d7403f2bc5e60"
SESSION_HASH = "2421eeb7e115ad640b6b0ec76d0d88cfe2a49499c12c39dc35ea5f71c1fed22b"
MANIFEST_HASH = "8a23e784cbdbe244c6dbe220937be0b7e023de417eec56009e8f03191ecde200"


def session_view(timestamp: str):
    snapshot = load_production_integrated_authority_snapshot(
        trusted_root=ROOT,
        decision_as_of=timestamp,
        resolved_at=timestamp,
        run_id="k3-calendar-recovery-test",
    )
    return snapshot, derive_us_market_session_authority_from_snapshot(
        snapshot,
        timestamp,
        primary_listing_operating_mic="XNAS",
        decision_as_of=timestamp,
    )


class K3SessionCalendarCoverageRecoveryTest(unittest.TestCase):
    def test_01_production_cohort_and_artifact_bindings(self):
        snapshot, _ = session_view("2026-09-03T14:41:00Z")
        self.assertEqual(COHORT, snapshot.activation_cohort_id)
        self.assertEqual(MANIFEST_HASH, snapshot.combined_activation_manifest_sha256)
        self.assertEqual(IDENTITY_HASH, snapshot.identity.registry_hash)
        self.assertEqual(SESSION_HASH, snapshot.session.calendar_hash)
        self.assertEqual("2026-09-03.1", snapshot.session.artifact["calendar_version"])
        self.assertEqual("2026-12-31", snapshot.session.artifact["coverage_end"])

    def test_02_target_and_adjacent_sessions_are_regular(self):
        snapshot, view = session_view("2026-09-03T14:41:00Z")
        sessions = {
            row["session_date"]: row for row in snapshot.session.artifact["sessions"]
        }
        for session_date in ("2026-09-02", "2026-09-03", "2026-09-04"):
            with self.subTest(session_date=session_date):
                self.assertEqual("REGULAR", sessions[session_date]["close_type"])
                self.assertTrue(
                    sessions[session_date]["core_open_at"].endswith("09:30:00-04:00")
                )
                self.assertTrue(
                    sessions[session_date]["core_close_at"].endswith("16:00:00-04:00")
                )
        self.assertEqual("VERIFIED", view.authority_status)
        self.assertEqual("CORE_OPEN", view.market_phase)
        self.assertEqual("2026-09-02", view.expected_completed_session.session_date)

    def test_03_regular_core_phase_boundaries(self):
        cases = (
            ("2026-09-04T13:29:59Z", "PRE_CORE"),
            ("2026-09-04T13:30:00Z", "CORE_OPEN"),
            ("2026-09-04T19:59:59Z", "CORE_OPEN"),
            ("2026-09-04T20:00:00Z", "POST_CORE"),
        )
        for timestamp, phase in cases:
            with self.subTest(timestamp=timestamp):
                _, view = session_view(timestamp)
                self.assertEqual("VERIFIED", view.authority_status)
                self.assertEqual(phase, view.market_phase)

    def test_04_labor_day_is_closed(self):
        _, view = session_view("2026-09-07T16:00:00Z")
        self.assertEqual("VERIFIED", view.authority_status)
        self.assertEqual("NON_TRADING_DATE", view.market_phase)
        self.assertIsNone(view.current_date_session)
        self.assertEqual("2026-09-04", view.expected_completed_session.session_date)

    def test_05_date_beyond_verified_horizon_fails_closed(self):
        _, view = session_view("2027-01-04T15:00:00Z")
        self.assertEqual("NOT_VERIFIED", view.authority_status)
        self.assertEqual("OUT_OF_COVERAGE", view.authority_reason)


if __name__ == "__main__":
    unittest.main()
