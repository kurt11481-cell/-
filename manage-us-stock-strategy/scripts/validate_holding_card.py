#!/usr/bin/env python3
"""Validate a holding card against its schema and its fact pack (I1, K2).

The card is analysis only. This validator rejects, with distinct codes:
  1. ORDER_FIELD_FORBIDDEN           order/quantity/plan fields anywhere (recursive)
  2. JUDGMENT_EMPTY                  blank action, rationale or conviction
  3. WITHHOLD_NOT_ALLOWED            WITHHELD without an allowed reason in the fact pack
  4. RULE_DISAGREEMENT_UNLABELED     action differs from the rule direction, no label
  5. CONVICTION_CAP_VIOLATION        conviction above the fact pack cap
  6. NUMBER_MISMATCH                 card number differs from the fact pack
  7. RUN_ID_MISMATCH / AS_OF_MISMATCH / FACT_PACK_HASH_MISMATCH
plus REASON_TAG_* / HOLD_REVIEW_FLAG_* (G3 decision 4) and TICKER_SET_MISMATCH.
It reads files only and never writes state, policy or ledgers.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from validation_common import canonical_hash, validate_instance  # noqa: E402

CARD_SCHEMA = SKILL_ROOT / "schemas/holding-card.schema.json"
FORBIDDEN_KEYS = frozenset({
    "order_intent_terms", "proposed_quantity", "limit_price", "target_weight_pct", "plan_status",
    "order_type", "time_in_force", "approved_price_rule", "stop_price", "order_quantity",
    "execution_quantity",
})
ACTION_TOKENS = frozenset({"order", "orders", "buy", "sell", "trade", "trading", "purchase", "execution", "proposed", "target"})
AMOUNT_TOKENS = frozenset({"qty", "quantity", "shares", "share", "amount", "size", "count", "price", "weight", "notional", "value"})
KOREAN_ORDER_MARKERS = (chr(0xC8FC) + chr(0xBB38), chr(0xB9E4) + chr(0xC218), chr(0xB9E4) + chr(0xB3C4))
TRIM_TAGS = frozenset({"TRIM_CONCENTRATION", "TRIM_RISK", "TRIM_TECHNICAL", "TRIM_PROFIT", "TRIM_VALUATION"})
EXIT_TAGS = frozenset({"EXIT_HARD_STOP", "EXIT_THESIS", "ROTATE_REVIEW", "KEEP_CASH"})
WITHHOLD_REASONS = ("BROKER_UNAVAILABLE", "IDENTITY_UNVERIFIED")
REDUCE_ACTIONS = frozenset({"TRIM", "EXIT"})
NUMBER_FIELDS = (
    "held_quantity", "average_cost_usd", "mark_price_usd", "market_value_usd", "unrealized_pnl_usd",
    "unrealized_pnl_pct", "weight_pct", "leverage_factor", "confirmed_close_usd",
    "loss_limit_boundary_usd", "loss_limit_remaining_pct",
)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _blank(value: Any) -> bool:
    return not isinstance(value, str) or not value.strip()


def is_forbidden_key(key: str) -> bool:
    lowered = key.lower()
    if lowered in FORBIDDEN_KEYS or any(marker in key for marker in KOREAN_ORDER_MARKERS):
        return True
    tokens = set(lowered.split("_"))
    return bool(tokens & ACTION_TOKENS) and bool(tokens & AMOUNT_TOKENS)


def forbidden_keys(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and is_forbidden_key(key):
                found.append(f"{path}.{key}")
            found.extend(forbidden_keys(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(forbidden_keys(child, f"{path}[{index}]"))
    return found


def _same_moment(left: Any, right: Any) -> bool:
    try:
        return datetime.fromisoformat(str(left).replace("Z", "+00:00")) == datetime.fromisoformat(
            str(right).replace("Z", "+00:00")
        )
    except ValueError:
        return False


def _same_number(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, bool) or isinstance(right, bool):
        return False
    return isinstance(left, (int, float)) and isinstance(right, (int, float)) and left == right


def _fact_pack_problems(fact_pack: Any) -> list[str]:
    pack = _dict(fact_pack)
    problems = []
    if pack.get("artifact_type") != "HOLDING_FACT_PACK":
        problems.append("artifact_type")
    if pack.get("order_authority") is not False:
        problems.append("order_authority")
    if not isinstance(_dict(pack.get("source")).get("manual_run_id"), str):
        problems.append("source.manual_run_id")
    if not isinstance(pack.get("tickers"), dict) or not pack["tickers"]:
        problems.append("tickers")
    return problems


def _rule_same(direction: Any, action: str) -> bool:
    if action == "WITHHELD" or direction not in ("REDUCE", "HOLD"):
        return True
    return action in REDUCE_ACTIONS if direction == "REDUCE" else action == "HOLD"


def _position_checks(position: dict[str, Any], row: dict[str, Any], cap: str) -> list[str]:
    ticker = position.get("ticker")
    action = position.get("action")
    errors: list[str] = []

    if action == "WITHHELD":
        reason = position.get("withheld_reason")
        if reason not in WITHHOLD_REASONS or _dict(row.get("withhold_allowed")).get(reason) is not True:
            errors.append(f"WITHHOLD_NOT_ALLOWED:{ticker}")
    elif "withheld_reason" in position:
        errors.append(f"WITHHOLD_NOT_ALLOWED:{ticker}")

    tag = position.get("reason_tag")
    if action == "TRIM":
        if tag is None:
            errors.append(f"REASON_TAG_MISSING:{ticker}")
        elif tag not in TRIM_TAGS:
            errors.append(f"REASON_TAG_INVALID:{ticker}")
    elif action == "EXIT":
        if tag is None:
            errors.append(f"REASON_TAG_MISSING:{ticker}")
        elif tag not in EXIT_TAGS:
            errors.append(f"REASON_TAG_INVALID:{ticker}")
    elif tag is not None:
        errors.append(f"REASON_TAG_NOT_ALLOWED:{ticker}")

    if action == "HOLD":
        if not isinstance(position.get("review_required"), bool):
            errors.append(f"HOLD_REVIEW_FLAG_MISSING:{ticker}")
    elif "review_required" in position:
        errors.append(f"HOLD_REVIEW_FLAG_NOT_ALLOWED:{ticker}")

    direction = _dict(row.get("rule_results")).get("rule_direction")
    agreement = position.get("rule_agreement")
    if not _rule_same(direction, action):
        if agreement != "DIFFERENT" or _blank(position.get("rule_disagreement_reason")):
            errors.append(f"RULE_DISAGREEMENT_UNLABELED:{ticker}")
    elif agreement == "DIFFERENT":
        errors.append(f"RULE_AGREEMENT_LABEL_MISMATCH:{ticker}")

    if cap != "HIGH" and position.get("conviction") != "LOW":
        errors.append(f"CONVICTION_CAP_VIOLATION:{ticker}")

    display = _dict(row.get("display"))
    numbers = _dict(position.get("numbers"))
    for field in NUMBER_FIELDS:
        if not _same_number(numbers.get(field), display.get(field)):
            errors.append(f"NUMBER_MISMATCH:{ticker}:{field}")
    return errors


def validate_card(card: Any, fact_pack: Any, schema_path: Path = CARD_SCHEMA) -> list[str]:
    """Return sorted rejection codes; an empty list means the card is accepted."""
    errors: list[str] = [f"ORDER_FIELD_FORBIDDEN:{path}" for path in forbidden_keys(card)]
    if not isinstance(card, dict):
        return sorted(set(errors + ["CARD_SCHEMA_INVALID:$"]))

    positions = card.get("positions")
    if isinstance(positions, list):
        for position in positions:
            if not isinstance(position, dict):
                continue
            if any(_blank(position.get(field)) for field in ("action", "rationale", "conviction")):
                errors.append(f"JUDGMENT_EMPTY:{position.get('ticker')}")

    schema_errors = validate_instance(card, schema_path)
    errors.extend(f"CARD_SCHEMA_INVALID:{item}" for item in schema_errors)
    problems = _fact_pack_problems(fact_pack)
    if problems:
        errors.append("FACT_PACK_INVALID:" + ",".join(problems))
    if schema_errors or problems or any(item.startswith("JUDGMENT_EMPTY") for item in errors):
        return sorted(set(errors))

    pack = _dict(fact_pack)
    source = _dict(pack.get("source"))
    binding = _dict(card.get("evidence_binding"))
    if binding.get("expected_run_id") != source.get("manual_run_id"):
        errors.append("RUN_ID_MISMATCH")
    if not _same_moment(binding.get("expected_decision_as_of"), source.get("decision_as_of")):
        errors.append("AS_OF_MISMATCH")
    if card.get("fact_pack_sha256") != canonical_hash(pack):
        errors.append("FACT_PACK_HASH_MISMATCH")

    market = _dict(_dict(card.get("header")).get("market_environment"))
    if market.get("status") == "SAVE_PROVIDED" and not market.get("lines"):
        errors.append("MARKET_ENVIRONMENT_LINES_MISSING")

    cap = _dict(_dict(pack.get("status")).get("confidence_cap")).get("max_conviction")
    rows = pack["tickers"]
    seen: list[str] = [str(position.get("ticker")) for position in positions]
    if len(set(seen)) != len(seen) or set(seen) != set(rows):
        errors.append("TICKER_SET_MISMATCH")
    for position in positions:
        row = rows.get(position.get("ticker"))
        if isinstance(row, dict):
            errors.extend(_position_checks(position, row, str(cap)))
    return sorted(set(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--card", type=Path, required=True)
    parser.add_argument("--fact-pack", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        card = json.loads(args.card.read_text(encoding="utf-8-sig"))
        fact_pack = json.loads(args.fact_pack.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        print(json.dumps({"status": "FAIL", "errors": ["INPUT_UNREADABLE"]}))
        return 2
    errors = validate_card(card, fact_pack)
    print(json.dumps({"status": "FAIL" if errors else "PASS", "errors": errors}, ensure_ascii=False))
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
