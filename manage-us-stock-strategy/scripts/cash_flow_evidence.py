#!/usr/bin/env python3
"""S5 R6 cash-flow evidence: normalize a saved Kiwoom transaction history and build a declaration.

The raw file is the read-only Kiwoom CLI output for ust21100 (transaction history) that Cowork saved.
This module never calls Kiwoom. It reads one file, drops the account label, classifies rows with the
reviewed keyword table (assets/kiwoom-transaction-history-classification.json) and fails closed on
anything it cannot classify. Dividends, fees, taxes and interest are never external cash flows.

normalize  raw CLI JSON -> sanitized evidence file (no account identifier)
The declaration block built here is embedded in a reconciliation proposal, so the user confirms it
with that proposal's confirmation code. Nothing here writes portfolio state, policy or ledgers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from validation_common import canonical_hash, validate_instance, write_json


SKILL_ROOT = Path(__file__).resolve().parents[1]
CLASSIFICATION_PATH = SKILL_ROOT / "assets/kiwoom-transaction-history-classification.json"
EVIDENCE_SCHEMA = SKILL_ROOT / "schemas/kiwoom-cash-flow-evidence.schema.json"
EVIDENCE_SCHEMA_VERSION = "kiwoom-cash-flow-evidence-1.0"
DECLARATION_SCHEMA_VERSION = "cash-flow-declaration-1.0"
API_ID = "ust21100"
CENT = Decimal("0.01")
ZERO = Decimal("0")
DATE_COMPACT = re.compile(r"\d{8}")
EXTERNAL_CLASSES = ("DEPOSIT", "WITHDRAWAL", "FX")
NON_EXTERNAL_CLASSES = ("DIVIDEND", "FEE_TAX_INTEREST", "TRADE")
LIMIT_RULE = "DECLARED_WITHIN_UNEXPLAINED_CASH_CHANGE"
SETTLED_STATUSES = ("NO_EXTERNAL_FLOW", "DECLARED_IN_FULL")


class CashFlowError(ValueError):
    """Fail-closed cash-flow evidence or declaration error with a public reason code."""


def _decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    return number if number.is_finite() else None


def money(value: Decimal) -> str:
    return f"{value.quantize(CENT):.2f}"


def _iso_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _compact_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if DATE_COMPACT.fullmatch(text) is None:
        return None
    try:
        return date(int(text[:4]), int(text[4:6]), int(text[6:8]))
    except ValueError:
        return None


def load_classification(path: Path = CLASSIFICATION_PATH) -> dict[str, Any]:
    table = json.loads(Path(path).read_text(encoding="utf-8"))
    if table.get("api_id") != API_ID or not isinstance(table.get("rules"), list):
        raise CashFlowError("CASH_FLOW_CLASSIFICATION_TABLE_INVALID")
    return table


def _matches(values: dict[str, str], fields: Any, keywords: Any) -> bool:
    text = " ".join(values.get(str(name), "") for name in fields or [])
    return any(keyword and keyword in text for keyword in keywords or [])


def classify_row(kind_name: str, memo: str, table: dict[str, Any]) -> tuple[str, int | None]:
    """First matching rule wins. Returns (classification, sign).

    sign is None for non-external rows and for external rows whose direction is unknown or ambiguous
    (both a plus and a minus keyword match). A TRANSFER rule becomes DEPOSIT or WITHDRAWAL by its sign.
    """
    values = {"deal_kind_nm": kind_name, "rmrk_nm": memo}
    for rule in table["rules"]:
        if not _matches(values, rule.get("fields"), rule.get("match_any")):
            continue
        classification = str(rule.get("classification"))
        if classification in NON_EXTERNAL_CLASSES:
            return classification, None
        if classification not in ("TRANSFER", "FX"):
            return "UNCLASSIFIED", None
        signs = {1 if sign_rule.get("sign") == "+" else -1
                 for sign_rule in rule.get("sign_rules") or []
                 if _matches(values, rule.get("sign_fields"), sign_rule.get("match_any"))}
        sign = next(iter(signs)) if len(signs) == 1 else None
        if classification == "TRANSFER":
            classification = "DEPOSIT" if sign == 1 else "WITHDRAWAL" if sign == -1 else "TRANSFER_SIGN_UNKNOWN"
        return classification, sign
    return "UNCLASSIFIED", None


def normalize_transaction_history(raw: Any, *, period_from: str, period_to: str, raw_sha256: str,
                                  table: dict[str, Any] | None = None) -> dict[str, Any]:
    """Sanitize one saved ust21100 response. The account label is never copied into the result."""
    table = table or load_classification()
    start, end = _iso_date(period_from), _iso_date(period_to)
    if start is None or end is None or start > end:
        raise CashFlowError("CASH_FLOW_EVIDENCE_PERIOD_INVALID")
    body = raw.get("result") if isinstance(raw, dict) and isinstance(raw.get("result"), dict) else raw
    if not isinstance(body, dict) or not isinstance(body.get("result_list"), list):
        raise CashFlowError("CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID")
    if body.get("return_code") != 0:
        raise CashFlowError("CASH_FLOW_EVIDENCE_RETURN_CODE_NOT_ZERO")
    rows: list[dict[str, Any]] = []
    unresolved: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(body["result_list"]):
        if not isinstance(item, dict):
            raise CashFlowError("CASH_FLOW_EVIDENCE_ROW_NOT_OBJECT")
        deal_date = _compact_date(item.get("deal_dt"))
        deal_no = str(item.get("deal_no") or "").strip()
        if deal_date is None or not deal_no:
            raise CashFlowError(f"CASH_FLOW_EVIDENCE_ROW_KEY_INVALID:{index}")
        if not start <= deal_date <= end:
            raise CashFlowError(f"CASH_FLOW_EVIDENCE_ROW_OUTSIDE_PERIOD:{index}")
        key = f"{deal_date.isoformat()}:{deal_no}"
        if key in seen:
            raise CashFlowError(f"CASH_FLOW_EVIDENCE_ROW_DUPLICATE:{key}")
        seen.add(key)
        kind_name, memo = str(item.get("deal_kind_nm") or "").strip(), str(item.get("rmrk_nm") or "").strip()
        currency = str(item.get("crnc_code") or "").strip().upper()
        classification, sign = classify_row(kind_name, memo, table)
        amount = _decimal(item.get("fc_exct_amt"))
        fee, deal_tax, foreign_tax = (_decimal(item.get(name)) or ZERO
                                      for name in ("fc_cmsn", "fc_deal_tax", "frgn_pay_txam"))
        signed: Decimal | None = None
        row_unresolved: list[str] = []
        if classification == "UNCLASSIFIED":
            row_unresolved.append("CASH_FLOW_ROW_UNCLASSIFIED")
        elif classification == "TRANSFER_SIGN_UNKNOWN":
            row_unresolved.append("CASH_FLOW_SIGN_UNKNOWN")
        elif classification in EXTERNAL_CLASSES:
            if currency != "USD":
                if classification == "FX":
                    row_unresolved.append("CASH_FLOW_FX_ROW_CURRENCY_NOT_USD")
                else:
                    classification = "NON_USD_IGNORED"
            elif amount is None:
                row_unresolved.append("CASH_FLOW_AMOUNT_INVALID")
            elif amount < 0:
                row_unresolved.append("CASH_FLOW_AMOUNT_NEGATIVE")
            elif sign is None:
                row_unresolved.append("CASH_FLOW_SIGN_UNKNOWN")
            else:
                signed = (amount * sign).quantize(CENT)
        rows.append({
            "key": key, "deal_date": deal_date.isoformat(), "kind_name": kind_name, "memo": memo,
            "currency": currency or None, "classification": classification,
            "signed_amount_usd": money(signed) if signed is not None else None,
            "settlement_amount": money(amount) if amount is not None else None,
            "fee_usd": money(fee), "tax_usd": money(deal_tax + foreign_tax),
            "unresolved": row_unresolved,
        })
        unresolved.extend(f"{code}:{key}" for code in row_unresolved)
    rows.sort(key=lambda row: row["key"])
    external = [row for row in rows if row["classification"] in EXTERNAL_CLASSES and row["signed_amount_usd"]]
    dividends = [row for row in rows if row["classification"] == "DIVIDEND" and row["currency"] == "USD"]
    usd_rows = [row for row in rows if row["currency"] == "USD"]
    evidence: dict[str, Any] = {
        "schema_version": EVIDENCE_SCHEMA_VERSION, "artifact_type": "KIWOOM_CASH_FLOW_EVIDENCE",
        "source": {"provider": "KIWOOM", "api_id": API_ID, "collection": "COWORK_READ_ONLY_CLI_EVIDENCE_FILE",
                   "raw_sha256": raw_sha256, "pagination_complete": "ASSERTED_BY_COLLECTOR"},
        "period_from": start.isoformat(), "period_to": end.isoformat(),
        "account_identifier_stored": False, "row_count": len(rows), "rows": rows,
        "totals": {
            "external_net_usd": money(sum((Decimal(row["signed_amount_usd"]) for row in external), ZERO)),
            "dividend_settlement_usd": money(sum((Decimal(row["settlement_amount"] or "0") for row in dividends), ZERO)),
            "fees_usd": money(sum((Decimal(row["fee_usd"]) for row in usd_rows), ZERO)),
            "taxes_usd": money(sum((Decimal(row["tax_usd"]) for row in usd_rows), ZERO)),
        },
        "unresolved": sorted(unresolved),
        "classification_table_sha256": canonical_hash(table),
        "order_authority": False, "quantity_authority": "none",
        "evidence_hash": "0" * 64,
    }
    evidence["evidence_hash"] = evidence_content_hash(evidence)
    return evidence


def evidence_content_hash(evidence: dict[str, Any]) -> str:
    return canonical_hash({key: value for key, value in evidence.items() if key != "evidence_hash"})


def evidence_errors(evidence: Any) -> list[str]:
    if not isinstance(evidence, dict):
        return ["CASH_FLOW_EVIDENCE_NOT_OBJECT"]
    errors = [f"CASH_FLOW_EVIDENCE_SCHEMA:{item}" for item in validate_instance(evidence, EVIDENCE_SCHEMA)]
    if errors:
        return errors
    if evidence_content_hash(evidence) != evidence["evidence_hash"]:
        errors.append("CASH_FLOW_EVIDENCE_HASH_MISMATCH")
    return errors


def _external_rows(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"key": row["key"], "deal_date": row["deal_date"], "classification": row["classification"],
             "signed_amount_usd": row["signed_amount_usd"]}
            for row in evidence["rows"]
            if row["classification"] in EXTERNAL_CLASSES and row["signed_amount_usd"] is not None]


def settled_keys(prior_blocks: list[Any]) -> set[str]:
    """Keys already counted by earlier blocks that were declared in full (dedupe across overlapping periods)."""
    counted: set[str] = set()
    for block in prior_blocks:
        if not isinstance(block, dict) or declaration_block_errors(block):
            continue
        keys = [row["key"] for row in block["external_rows"]]
        # Same rule as cash_flow_chain: a block that does not repeat the dedupe exactly is not counted.
        if sorted(block["previously_counted_keys"]) != sorted(key for key in keys if key in counted):
            continue
        if block["declaration_status"] in SETTLED_STATUSES:
            counted.update(keys)
    return counted


def _within_limit(declared: Decimal, limit: Decimal) -> bool:
    return ZERO <= declared <= limit if limit >= 0 else limit <= declared <= ZERO


def build_declaration(evidence: dict[str, Any], *, declared_usd: Any, prior_blocks: list[Any]) -> dict[str, Any]:
    """Build the proposal block. A declaration beyond the unexplained cash change is rejected."""
    errors = evidence_errors(evidence)
    if errors:
        raise CashFlowError(errors[0])
    external = _external_rows(evidence)
    counted = settled_keys(prior_blocks)
    previously = sorted(row["key"] for row in external if row["key"] in counted)
    new_net = sum((Decimal(row["signed_amount_usd"]) for row in external if row["key"] not in counted), ZERO)
    unresolved = list(evidence["unresolved"])
    declared: Decimal | None = None
    if declared_usd is not None:
        declared = _decimal(declared_usd)
        if declared is None or declared != declared.quantize(CENT):
            raise CashFlowError("CASH_FLOW_DECLARATION_AMOUNT_INVALID")
        if unresolved:
            raise CashFlowError("CASH_FLOW_DECLARATION_BLOCKED_BY_UNRESOLVED_EVIDENCE")
        if not _within_limit(declared, new_net):
            raise CashFlowError("CASH_FLOW_DECLARATION_EXCEEDS_LIMIT")
    if unresolved:
        status = "EVIDENCE_UNRESOLVED"
    elif new_net == 0:
        status, declared = "NO_EXTERNAL_FLOW", ZERO
    elif declared is None:
        status = "UNDECLARED"
    else:
        status = "DECLARED_IN_FULL" if declared == new_net else "PARTIALLY_DECLARED"
    remainder = new_net - (declared if declared is not None else ZERO)
    return {
        "schema_version": DECLARATION_SCHEMA_VERSION,
        "evidence": {"evidence_hash": evidence["evidence_hash"], "raw_sha256": evidence["source"]["raw_sha256"],
                     "api_id": API_ID, "period_from": evidence["period_from"], "period_to": evidence["period_to"],
                     "row_count": evidence["row_count"], "unresolved": unresolved},
        "external_rows": external, "previously_counted_keys": previously,
        "new_external_net_usd": money(new_net),
        "declared_cash_flow_usd": money(declared) if declared is not None else None,
        "undeclared_remainder_usd": money(remainder),
        "declaration_status": status,
        "hwm_adjustment_usd": money(declared) if status in SETTLED_STATUSES and declared is not None else None,
        "excluded_from_cash_flow": {"dividend_settlement_usd": evidence["totals"]["dividend_settlement_usd"],
                                    "fees_usd": evidence["totals"]["fees_usd"],
                                    "taxes_usd": evidence["totals"]["taxes_usd"]},
        "limit_rule": LIMIT_RULE, "order_authority": False, "quantity_authority": "none",
    }


def declaration_block_errors(block: Any) -> list[str]:
    """Self-consistency of one block; apply re-runs this so a hand-edited block cannot be written."""
    if not isinstance(block, dict) or block.get("schema_version") != DECLARATION_SCHEMA_VERSION:
        return ["CASH_FLOW_DECLARATION_SCHEMA_VERSION"]
    try:
        rows = block["external_rows"]
        previously = set(block["previously_counted_keys"])
        keys = [row["key"] for row in rows]
        if len(keys) != len(set(keys)) or not previously <= set(keys):
            return ["CASH_FLOW_DECLARATION_KEYS_INCONSISTENT"]
        new_net = sum((Decimal(row["signed_amount_usd"]) for row in rows if row["key"] not in previously), ZERO)
        if Decimal(block["new_external_net_usd"]) != new_net:
            return ["CASH_FLOW_DECLARATION_NET_INCONSISTENT"]
        declared_text = block["declared_cash_flow_usd"]
        declared = Decimal(declared_text) if declared_text is not None else None
        unresolved = list(block["evidence"]["unresolved"])
        status = block["declaration_status"]
        if _iso_date(block["evidence"]["period_from"]) is None or _iso_date(block["evidence"]["period_to"]) is None:
            return ["CASH_FLOW_DECLARATION_PERIOD_INVALID"]
        if declared is not None and not _within_limit(declared, new_net):
            return ["CASH_FLOW_DECLARATION_EXCEEDS_LIMIT"]
        expected = ("EVIDENCE_UNRESOLVED" if unresolved else "NO_EXTERNAL_FLOW" if new_net == 0
                    else "UNDECLARED" if declared is None
                    else "DECLARED_IN_FULL" if declared == new_net else "PARTIALLY_DECLARED")
        if status != expected or (unresolved and declared is not None):
            return ["CASH_FLOW_DECLARATION_STATUS_INCONSISTENT"]
        if Decimal(block["undeclared_remainder_usd"]) != new_net - (declared if declared is not None else ZERO):
            return ["CASH_FLOW_DECLARATION_REMAINDER_INCONSISTENT"]
        adjustment = block["hwm_adjustment_usd"]
        if (adjustment is not None) != (status in SETTLED_STATUSES) or (
                adjustment is not None and Decimal(adjustment) != declared):
            return ["CASH_FLOW_DECLARATION_ADJUSTMENT_INCONSISTENT"]
    except (KeyError, TypeError, InvalidOperation, ValueError):
        return ["CASH_FLOW_DECLARATION_FIELDS_INVALID"]
    return []


def cash_flow_chain(items: list[dict[str, Any]], *, start_date: str) -> dict[str, Any]:
    """Walk every ledger reconciliation in order and judge the post-activation ones.

    items: [{"as_of": date string, "state_revision": int, "block": declaration block or None,
             "post_activation": bool}].
    Dedupe uses the same rule as build_declaration (keys of earlier blocks declared in full), so a
    block that repeats that dedupe exactly is counted and its declared amount adjusts the HWM from its
    as_of date. A post-activation reconciliation is clear only when its evidence starts no later than
    the day after the covered period, reaches its own as_of date and declares the whole new external
    net. Otherwise HWM and line evaluation are on hold from that as_of until a later one is clear.
    """
    covered = _iso_date(start_date)
    if covered is None:
        raise CashFlowError("CASH_FLOW_CHAIN_START_DATE_INVALID")
    counted: set[str] = set()
    steps: list[dict[str, Any]] = []
    adjustments: list[dict[str, str]] = []
    hold_from: str | None = None
    for item in items:
        block, as_of = item.get("block"), _iso_date(item.get("as_of"))
        post_activation = item.get("post_activation") is True
        reasons: list[str] = []
        block_errors = declaration_block_errors(block) if block is not None else []
        usable = block is not None and not block_errors
        if usable:
            expected_previous = sorted(row["key"] for row in block["external_rows"] if row["key"] in counted)
            if sorted(block["previously_counted_keys"]) != expected_previous:
                usable = False
                block_errors = ["CASH_FLOW_DEDUPE_MISMATCH"]
        settled = usable and block["declaration_status"] in SETTLED_STATUSES
        if settled:
            counted.update(row["key"] for row in block["external_rows"])
        if post_activation:
            if as_of is None:
                reasons.append("RECONCILIATION_AS_OF_INVALID")
            elif block is None:
                reasons.append("CASH_FLOW_EVIDENCE_MISSING")
            elif not usable:
                reasons.extend(block_errors)
            else:
                period_from = _iso_date(block["evidence"]["period_from"])
                period_to = _iso_date(block["evidence"]["period_to"])
                contiguous = period_from <= covered + timedelta(days=1)
                if not contiguous:
                    reasons.append("CASH_FLOW_COVERAGE_GAP")
                elif period_to < as_of:
                    reasons.append("CASH_FLOW_COVERAGE_ENDS_BEFORE_AS_OF")
                if not settled:
                    reasons.append("CASH_FLOW_" + block["declaration_status"])
                else:
                    # Coverage only advances over a period whose external flows were declared in full,
                    # so an undeclared flow must be covered again and declared by a later reconciliation.
                    if contiguous:
                        covered = max(covered, period_to)
                    if Decimal(block["hwm_adjustment_usd"]) != 0:
                        adjustments.append({"effective_date": as_of.isoformat(),
                                            "amount_usd": block["hwm_adjustment_usd"],
                                            "state_revision": str(item.get("state_revision"))})
            if reasons:
                hold_from = hold_from or (as_of.isoformat() if as_of else str(item.get("as_of")))
            else:
                hold_from = None
        steps.append({"as_of": item.get("as_of"), "state_revision": item.get("state_revision"),
                      "post_activation": post_activation,
                      "status": "NOT_REQUIRED" if not post_activation else "HOLD" if reasons else "CLEAR",
                      "reasons": reasons, "hold_from": hold_from if post_activation else None})
    return {"steps": steps, "adjustments": adjustments, "hold_active": hold_from is not None,
            "hold_from": hold_from, "covered_through": covered.isoformat()}


def read_ledger_blocks(ledger_path: Path) -> list[Any]:
    """Declaration blocks recorded by earlier applies, in ledger order. A missing ledger has none."""
    path = Path(ledger_path)
    if not path.is_file():
        return []
    blocks = []
    for raw in path.read_bytes().splitlines():
        if raw.strip():
            entry = json.loads(raw.decode("utf-8"))
            if isinstance(entry, dict) and entry.get("cash_flow_declaration") is not None:
                blocks.append(entry["cash_flow_declaration"])
    return blocks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sanitize one saved Kiwoom ust21100 response (read-only)")
    commands = parser.add_subparsers(dest="command", required=True)
    normalize = commands.add_parser("normalize")
    normalize.add_argument("--raw", type=Path, required=True)
    normalize.add_argument("--from", dest="period_from", required=True, help="YYYY-MM-DD")
    normalize.add_argument("--to", dest="period_to", required=True, help="YYYY-MM-DD")
    normalize.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    raw_bytes = args.raw.read_bytes()
    try:
        evidence = normalize_transaction_history(
            json.loads(raw_bytes.decode("utf-8-sig")), period_from=args.period_from, period_to=args.period_to,
            raw_sha256=hashlib.sha256(raw_bytes).hexdigest())
    except (CashFlowError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}))
        return 2
    if args.output.exists():
        print(json.dumps({"status": "FAIL", "error": "CASH_FLOW_EVIDENCE_OUTPUT_EXISTS"}))
        return 2
    write_json(args.output, evidence)
    print(json.dumps({"status": "OK", "evidence_hash": evidence["evidence_hash"], "row_count": evidence["row_count"],
                      "external_net_usd": evidence["totals"]["external_net_usd"],
                      "unresolved_count": len(evidence["unresolved"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
