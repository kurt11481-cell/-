#!/usr/bin/env python3
"""Render a validated holding card JSON to Markdown (I1, K2).

Output is the 5-line portfolio header plus one 11-row table per holding, in the
format fixed by the G3 decision (the pilot card format). Korean text comes from
assets/locales/holding-card-ko-KR.json. A card that fails validate_holding_card
is never rendered. The renderer reads files and writes one create-only
Markdown file; it never touches state, policy or ledgers.
"""
from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_holding_card import validate_card  # noqa: E402

LOCALE_PATH = SKILL_ROOT / "assets/locales/holding-card-ko-KR.json"
OUTPUT_NAME = "cards.md"
SEP = " " + chr(0xB7) + " "
ROW_ORDER = (
    "rule_result", "judgment", "cash_and_alternatives", "numbers", "thesis", "material_risk",
    "kill_criteria", "next_event", "change_conditions", "data_status", "past_performance",
)


class RenderError(Exception):
    """Raised when a card cannot be rendered."""


def load_messages(path: Path = LOCALE_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))["messages"]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _cell(text: Any) -> str:
    return " ".join(str(text).replace("|", "/").split())


def _number(value: Any, messages: dict[str, Any], min_decimals: int = 2, max_decimals: int = 4) -> str:
    if value is None:
        return messages["unknown"]
    text = f"{Decimal(str(value)):,.{max_decimals}f}".rstrip("0")
    whole, _, fraction = text.partition(".")
    if min_decimals == 0 and not fraction:
        return whole
    return f"{whole}.{fraction.ljust(min_decimals, '0')}"


def _signed(value: Any, messages: dict[str, Any], decimals: int, prefix: str = "") -> str:
    if value is None:
        return messages["unknown"]
    amount = Decimal(str(value))
    sign = "+" if amount > 0 else ("-" if amount < 0 else "")
    return f"{sign}{prefix}{abs(amount):,.{decimals}f}"


def _quantity(value: Any, messages: dict[str, Any]) -> str:
    if value is None:
        return messages["unknown"]
    amount = Decimal(str(value))
    return f"{amount:,.0f}" if amount == amount.to_integral_value() else f"{amount:,}"


def _banner(fact_pack: dict[str, Any], messages: dict[str, Any]) -> str:
    status = _dict(fact_pack.get("status"))
    cap = _dict(status.get("confidence_cap"))
    grade = status.get("evidence_grade")
    if cap.get("max_conviction") == "HIGH":
        return messages["banner_open"].format(grade=grade)
    labels = messages["cap_reasons"]
    reasons = ", ".join(labels.get(code, code) for code in cap.get("reasons") or []) or messages["unknown"]
    return messages["banner_capped"].format(grade=grade, reasons=reasons)


def render_header(card: dict[str, Any], fact_pack: dict[str, Any], messages: dict[str, Any]) -> list[str]:
    source = _dict(fact_pack.get("source"))
    header = _dict(card.get("header"))
    lines = [
        _banner(fact_pack, messages),
        "",
        "# " + messages["header_title"].format(date=source.get("trading_date")),
        "",
        messages["header_run_line"].format(run_id=source.get("manual_run_id"), as_of=source.get("decision_as_of")),
        "",
    ]
    for key in ("conclusion_primary", "conclusion_secondary", "status", "exposure", "upcoming_events"):
        lines.append(f"- **{messages['header_labels'][key]}:** {header[key]}")
    market = _dict(header.get("market_environment"))
    if market.get("status") == "SAVE_PROVIDED":
        for text in market.get("lines") or []:
            lines.append(f"- **{messages['market_label']}:** {text}")
    else:
        lines.append(f"- {messages['market_not_received']}")
    return lines


def _rule_cell(position: dict[str, Any], row: dict[str, Any], messages: dict[str, Any]) -> str:
    rules = _dict(row.get("rule_results"))
    hard = _dict(rules.get("hard_risk"))
    parts: list[str] = []
    if hard.get("status") == "EVALUATED":
        reference = ""
        if hard.get("premarket_reference_remaining_pct") is not None:
            reference = messages["hard_risk_reference"].format(value=_signed(hard["premarket_reference_remaining_pct"], messages, 1))
        parts.append(messages["hard_risk_line"].format(
            rule_id=hard.get("rule_id"), boundary=_number(hard.get("boundary_usd"), messages),
            session=hard.get("close_session"), close=_number(hard.get("close_usd"), messages),
            verdict=messages["verdict_breach" if hard.get("breached") else "verdict_ok"],
            remaining=_signed(hard.get("remaining_pct"), messages, 1), reference=reference,
        ))
    else:
        parts.append(messages["hard_risk_not_evaluated"].format(reason=hard.get("reason")))
    direction = rules.get("rule_direction")
    if direction in ("REDUCE", "HOLD"):
        basis = ", ".join(messages["direction_basis"].get(code, code) for code in rules.get("rule_direction_basis") or [])
        parts.append(messages["direction_line"].format(direction=messages["directions"][direction], basis=basis) + ".")
    else:
        parts.append(messages["direction_none"] + ".")
    timing = _dict(rules.get("timing"))
    parts.append(messages["timing_line"].format(status=messages["timing_statuses"].get(timing.get("status"), timing.get("status"))) + ".")
    parts.append(position["rule_result"])
    return " ".join(parts)


def _judgment_cell(position: dict[str, Any], cap: str, messages: dict[str, Any]) -> str:
    action = position["action"]
    conviction = messages["convictions"][position["conviction"]]
    if cap != "HIGH":
        conviction += messages["cap_suffix"]
    head = [f"**{messages['actions'][action]}", messages["conviction_label"].format(value=conviction)]
    marker = None
    if action == "WITHHELD":
        marker = messages["withheld_reasons"][position["withheld_reason"]]
    elif action in ("TRIM", "EXIT"):
        marker = position["reason_tag"]
    elif action == "HOLD":
        marker = messages["review_required_true" if position["review_required"] else "review_required_false"]
    text = SEP.join(head + ([marker] if marker else [])) + "**"
    if position["rule_agreement"] == "DIFFERENT":
        agreement = messages["agreement_different"].format(reason=position["rule_disagreement_reason"])
    else:
        agreement = messages["agreement_same"]
    return f"{text}{SEP}**{agreement}**. {position['rationale']} {messages['no_quantity_notice']}"


def _numbers_cell(numbers: dict[str, Any], messages: dict[str, Any]) -> str:
    labels = messages["numbers"]
    return SEP.join([
        labels["quantity"].format(value=_quantity(numbers.get("held_quantity"), messages)),
        labels["average_cost"].format(value=_number(numbers.get("average_cost_usd"), messages)),
        labels["mark"].format(value=_number(numbers.get("mark_price_usd"), messages)),
        labels["market_value"].format(value=_number(numbers.get("market_value_usd"), messages)),
        labels["weight"].format(value=_number(numbers.get("weight_pct"), messages, 1, 1)),
        labels["pnl"].format(
            usd=_signed(numbers.get("unrealized_pnl_usd"), messages, 2, "$"),
            pct=_signed(numbers.get("unrealized_pnl_pct"), messages, 1),
        ),
        labels["leverage"].format(value=_number(numbers.get("leverage_factor"), messages, 0, 2)),
        labels["confirmed_close"].format(value=_number(numbers.get("confirmed_close_usd"), messages)),
        labels["display_only"],
    ])


def _data_status_cell(position: dict[str, Any], row: dict[str, Any], messages: dict[str, Any]) -> str:
    status = _dict(position.get("data_status"))
    codes = messages["missing_codes"]
    missing = [codes.get(code, code) for code in row.get("missing") or []] + list(status.get("missing") or [])
    text = status["summary"]
    if missing:
        text += f" **{messages['missing_prefix']}:** " + "; ".join(missing)
    return text


def render_position(position: dict[str, Any], row: dict[str, Any], fact_pack: dict[str, Any], messages: dict[str, Any]) -> list[str]:
    source = _dict(fact_pack.get("source"))
    cap = str(_dict(_dict(fact_pack.get("status")).get("confidence_cap")).get("max_conviction"))
    thesis = _dict(position.get("thesis"))
    kill = _dict(position.get("kill_criteria"))
    cells = {
        "rule_result": _rule_cell(position, row, messages),
        "judgment": _judgment_cell(position, cap, messages),
        "cash_and_alternatives": position["cash_and_alternatives"],
        "numbers": _numbers_cell(_dict(position.get("numbers")), messages),
        "thesis": messages["thesis_line"].format(
            status=messages["thesis_statuses"][thesis["status"]], statement=thesis["statement"]
        ) + " " + messages["thesis_change"].format(value=thesis["change_vs_previous"]),
        "material_risk": position["material_risk"],
        "kill_criteria": f"{messages['kill_conditions']}: " + "; ".join(kill["conditions"])
        + f". {messages['kill_distance']}: {kill['current_distance']}",
        "next_event": position["next_event"],
        "change_conditions": " ".join(f"{index}) {text}" for index, text in enumerate(position["change_conditions"], 1)),
        "data_status": _data_status_cell(position, row, messages),
        "past_performance": position["past_performance"],
    }
    lines = [
        _banner(fact_pack, messages),
        "",
        "# " + messages["card_title"].format(ticker=position["ticker"], date=source.get("trading_date")),
        "",
        messages["card_run_line"].format(run_id=source.get("manual_run_id")),
        "",
        f"| {messages['column_header']} | {messages['column_content']} |",
        "|---|---|",
    ]
    lines.extend(f"| {messages['rows'][key]} | {_cell(cells[key])} |" for key in ROW_ORDER)
    return lines


def render_markdown(card: dict[str, Any], fact_pack: dict[str, Any], messages: dict[str, Any] | None = None) -> str:
    messages = messages or load_messages()
    errors = validate_card(card, fact_pack)
    if errors:
        raise RenderError(messages["rejected"].format(codes=", ".join(errors)))
    blocks = ["\n".join(render_header(card, fact_pack, messages))]
    for position in card["positions"]:
        blocks.append("\n".join(render_position(position, fact_pack["tickers"][position["ticker"]], fact_pack, messages)))
    return "\n\n---\n\n".join(blocks) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--card", type=Path, required=True)
    parser.add_argument("--fact-pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        card = json.loads(args.card.read_text(encoding="utf-8-sig"))
        fact_pack = json.loads(args.fact_pack.read_text(encoding="utf-8-sig"))
        text = render_markdown(card, fact_pack)
        target = args.output or args.card.parent / OUTPUT_NAME
        with target.open("xb") as handle:
            handle.write(text.encode("utf-8"))
    except (OSError, ValueError, RenderError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "OK", "output": str(target)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
