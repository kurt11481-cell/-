#!/usr/bin/env python3
"""Redesign T2 F9: compare the auto-core's judgments with the integrated check's run record (read only).

Units: symbol x trigger group (aliases resolved to the registry kind), buy-requirement row x cells 1 2 4 5 and
cell 3 (ok against anything else), exposure N (+/-0.01), band and single-stock cap breaches, R5 states, R-REC1
open and RG1-RG4. An LLM "near" is not a hit. Every difference gets a pre-registered category (prompt appendix
B, fixed before any result was seen); what cannot be categorized is B7 UNEXPLAINED. Cowork explains B7 items in
docs/claude/redesign-t2-compare-explained.json (LLM_ERROR with the rule quote, or CORE_BUG). The streak is
recounted from all decide records on every run: a day adds 1 when it was compared and every B7 of it is
explained as LLM_ERROR with no CORE_BUG; only a day without the integrated check's run copy is skipped; anything
else (an unexplained day, a decide FAIL, a run that ended before F1) resets to 0. B2 items that used more than
the 1% price margin are listed in b2_wide for Cowork's R2 review.

CLI: python auto_core_compare.py --decision <decision.json> [--explained <file>] prints the compare block.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validation_common import load_json, validate_instance

import auto_core_rules as rules


SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parent
COMPARE_SCHEMA = SKILL_ROOT / "schemas/auto-core-compare.schema.json"
EXPLAINED_PATH = REPO_ROOT / "docs/claude/redesign-t2-compare-explained.json"
COMPARE_SCHEMA_VERSION = "auto-core-compare-1.0"
REQUIRED_DAYS = 5
# Prompt appendix B (pre-registered): categories and their automatic conditions.
CATEGORIES = {
    "B1": "SAME", "B2": "DATA_DEFINITION", "B3": "LLM_ONLY", "B4": "RESEARCH_RECORD",
    "B5": "RULE_CODE_PRECEDENCE", "B6": "TIMING", "B7": "UNEXPLAINED",
}
B2_PRICE_MARGIN = 0.01      # price condition margin <= 1.0% of the close
B2_RSI_MARGIN = 2.0         # RSI +/- 2.0
B2_HLV_MARGIN = 0.03        # conditions on high, low or volume (C2, ATR band): margin <= 3%
B2_KNOWN_MARGIN = 0.03      # the four known definition differences: margin <= 3%
# r2 R2-10 (Cowork, within appendix B): N differs by close definition only up to |dN| <= 0.03; R5 only when the
# core close / peak is within 1 percentage point of a line (0.70, 0.75); wider differences are B7.
B2_N_MARGIN = 0.03
B2_R5_MARGIN = 0.01
FLOAT_EQUAL = rules.FLOAT_EQUAL  # representation tolerance on the lines above, not a threshold
NOT_COMPARED = "NOT_COMPARED"   # decide ended before F9 (before F1): the streak resets
NO_NEW_SESSION = "NO_NEW_SESSION"  # r3 R3-3: no session closed since the ledger source (no new judgment): kept
LLM_ONLY_IDS = {"S2", "S3", "S7", "N1", "N2", "N3", "N4", "N10", "U1", "U2", "U3", "BE1", "BE2", "BE3", "BE9",
                "DL1", "DL2", "DL3", "DL9", "AM1", "AM2", "AM3", "AM9", "M6", "BE4", "N5", "U4", "DL4", "AM4"}
SEPARATE_IDS = {"EXP", "CAP", "RREC", "R5", "NOCARD", "V6"}
HLV_GROUPS = {"overheat_fade", "oversold_rebound"}
EMA_GROUPS = {"overheat", "oversold", "trend_break", "trend_recover", "new_low", "new_high", "rebound_fail",
              "pullback_rebound", "overheat_fade", "oversold_rebound"}
RESEARCH_GROUPS = {"good_news_drop", "bad_news_rise"}
B5_PRODUCTS = ("PWR", "LITE")


def _llm_hit(state: Any) -> bool:
    return state == "hit"  # near, wait, interp, lead, info, rumor, unk, none: not a hit


def alias_groups(registry_entries: dict[str, Any]) -> dict[str, dict[str, str]]:
    """{symbol: {trigger id: group}} for card triggers, plus the common rules for every symbol."""
    common = {rule: group for rule, (group, _side, _kind) in rules.COMMON_RULES.items()}
    out: dict[str, dict[str, str]] = {}
    for symbol, entry in (registry_entries or {}).items():
        mapping = dict(common)
        for trigger in entry.get("card_triggers") or []:
            group = rules.CARD_KINDS.get(trigger["kind"], (None, None))[0]
            if group:
                mapping[trigger["id"]] = group
        out[symbol] = mapping
    out["*"] = common
    return out


def _margin(symbol_result: dict[str, Any], group: str) -> float | None:
    """Relative distance of the deciding close-based quantity to its line (display margins from decide)."""
    margins = symbol_result.get("margins") or {}
    return margins.get(group)


def _category_for_trigger(*, symbol: str, group: str, core: dict[str, Any], research_ok: bool, timing: bool,
                          close_differs: bool) -> tuple[str, str, float | None, float | None]:
    """(category, detail, margin, limit); margin and limit only for a B2 by margin."""
    if timing:
        return "B6", "LLM_RUN_SESSION_OR_INCOMPLETE", None, None
    if group in RESEARCH_GROUPS and not research_ok:
        return "B4", "RESEARCH_RECORD_MISSING_OR_DROPPED", None, None
    margin = _margin(core, group)
    rsi_gap = (core.get("margins") or {}).get("rsi_gap")
    if core.get("groups", {}).get(group, {}).get("state") == "unk" and group in HLV_GROUPS:
        return "B2", "CORE_INCOMPLETE_BARS", None, None
    if group in ("overheat", "oversold") and rsi_gap is not None and rsi_gap <= B2_RSI_MARGIN:
        return "B2", f"RSI_GAP:{rsi_gap:.2f}", None, None
    limit = B2_PRICE_MARGIN
    if group in HLV_GROUPS:
        limit = B2_HLV_MARGIN
    if close_differs or group in EMA_GROUPS or symbol == "MVLL":
        limit = max(limit, B2_KNOWN_MARGIN)
    if margin is not None and margin <= limit:
        return "B2", f"MARGIN:{margin:.4f}<={limit}", margin, limit
    return "B7", "UNEXPLAINED", None, None


def _r5_distance(item: dict[str, Any]) -> float | None:
    """Distance of the core close / peak to the nearer R5 line (0.70 review, 0.75 near), in ratio points."""
    try:
        ratio = float(str(item.get("close"))) / float(str(item.get("peak")))
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return min(abs(ratio - float(rules.C["R5_REVIEW_FRACTION"])), abs(ratio - float(rules.C["R5_NEAR_FRACTION"])))


def compare(decision: dict[str, Any], run: dict[str, Any] | None, registry_entries: dict[str, Any],
            research_ok: bool) -> dict[str, Any]:
    """Items and categories for one decide record against the integrated check run copy."""
    out: dict[str, Any] = {"status": "NO_RECORD", "items": [], "categories": {key: 0 for key in CATEGORIES},
                           "unexplained": [], "llm_run": None, "b2_wide": [], "b2_wide_count": 0}
    if not isinstance(run, dict):
        return out
    basis = str(run.get("basis") or "")
    statuses = {item.get("label"): item.get("value") for item in run.get("status") or [] if isinstance(item, dict)}
    incomplete = str(statuses.get("\uc810\uac80 \uc0c1\ud0dc") or "").startswith("\ubd88\uc644\uc804")
    timing = (decision["evaluation_session"] not in basis) or incomplete
    out.update(status="COMPARED", llm_run={"date": run.get("date"), "basis": basis, "incomplete": incomplete})
    aliases = alias_groups(registry_entries)
    llm_closes = {item.get("code"): item.get("close") for item in run.get("tickers") or [] if isinstance(item, dict)}

    def add(key: str, unit: str, core_value: Any, llm_value: Any, category: str, detail: str) -> None:
        out["items"].append({"item_key": key, "unit": unit, "core": core_value, "llm": llm_value,
                             "category": category, "detail": detail})
        out["categories"][category] += 1
        if category == "B7":
            out["unexplained"].append(key)

    # Triggers: symbol x group.
    llm_groups: dict[tuple[str, str], bool] = {}
    for block in run.get("triggers") or []:
        symbol = block.get("code")
        mapping = aliases.get(symbol) or aliases["*"]
        for item in block.get("items") or []:
            for rule_id in str(item.get("id") or "").split("\u00b7"):
                rule_id = rule_id.strip()
                if rule_id in LLM_ONLY_IDS:
                    add(f"{symbol}:{rule_id}", "trigger", None, item.get("state"), "B3", "LLM_ONLY")
                    continue
                if rule_id in SEPARATE_IDS or rule_id not in mapping:
                    continue
                key = (symbol, mapping[rule_id])
                llm_groups[key] = llm_groups.get(key, False) or _llm_hit(item.get("state"))
    for symbol, result in (decision.get("symbols") or {}).items():
        core_close = (result.get("indicators") or {}).get("close")
        llm_close = llm_closes.get(symbol)
        close_differs = (core_close is not None and isinstance(llm_close, (int, float)) and core_close
                         and abs(llm_close / core_close - 1) > 0.0005)
        for group, entry in (result.get("groups") or {}).items():
            core_hit = entry["state"] in ("hit", "review")
            llm_hit = llm_groups.get((symbol, group), False)
            if core_hit == llm_hit:
                add(f"{symbol}:{group}", "trigger", entry["state"], llm_hit, "B1", "SAME")
            else:
                category, detail, margin, limit = _category_for_trigger(symbol=symbol, group=group, core=result,
                                                                        research_ok=research_ok, timing=timing,
                                                                        close_differs=bool(close_differs))
                add(f"{symbol}:{group}", "trigger", entry["state"], llm_hit, category, detail)
                if margin is not None and margin > B2_PRICE_MARGIN + FLOAT_EQUAL:
                    # r2 R2-10: a B2 that used the 3% allowance beyond the 1% price margin, for Cowork's R2 review.
                    out["b2_wide"].append({"item_key": f"{symbol}:{group}", "margin": round(margin, 6), "limit": limit})

    # Buy requirement rows.
    llm_rows = {row.get("code"): row for row in (run.get("buyReq") or {}).get("rows") or [] if isinstance(row, dict)}
    for row in decision.get("buy_requirements") or []:
        llm = llm_rows.get(row["code"])
        if llm is None:
            continue
        for index in (0, 1, 2, 3, 4):
            core_cell, llm_cells = row["c"][index], llm.get("c") or []
            llm_cell = llm_cells[index] if index < len(llm_cells) and isinstance(llm_cells[index], dict) else {}
            core_ok, llm_ok = core_cell["s"] == "ok", llm_cell.get("s") == "ok"
            key = f"buyReq:{row['code']}:{index + 1}"
            if core_ok == llm_ok:
                add(key, "buy_requirement", core_cell["s"], llm_cell.get("s"), "B1", "SAME")
                continue
            if timing:
                add(key, "buy_requirement", core_cell["s"], llm_cell.get("s"), "B6", "LLM_RUN_SESSION_OR_INCOMPLETE")
            elif index == 0 and not research_ok:
                add(key, "buy_requirement", core_cell["s"], llm_cell.get("s"), "B4", "RESEARCH_RECORD_MISSING")
            elif index == 0 and "EARNINGS" in core_cell["t"] and not core_ok:
                add(key, "buy_requirement", core_cell["s"], llm_cell.get("s"), "B5", "P_EARN_R1_UNVERIFIED_IS_BLACKOUT")
            elif index == 1 and row["code"] in B5_PRODUCTS:
                add(key, "buy_requirement", core_cell["s"], llm_cell.get("s"), "B5", "POLICY_UNREGISTERED_PRODUCT")
            elif index == 2 and llm_cell.get("s") == "info":
                add(key, "buy_requirement", core_cell["s"], llm_cell.get("s"), "B5", "LLM_INFO_STATE")
            elif index == 4 and not research_ok:
                add(key, "buy_requirement", core_cell["s"], llm_cell.get("s"), "B4", "RG1_NEEDS_RESEARCH_RECORD")
            else:
                add(key, "buy_requirement", core_cell["s"], llm_cell.get("s"), "B7", "UNEXPLAINED")

    # Exposure, caps, R5, R-REC1.
    exposure = (run.get("account") or {}).get("exposure") or {}
    core_n = (decision.get("exposure") or {}).get("N")
    if isinstance(exposure.get("n"), (int, float)) and core_n is not None:
        delta = abs(exposure["n"] - core_n)
        same = delta <= 0.01
        add("exposure:N", "exposure", core_n, exposure["n"],
            "B1" if same else "B6" if timing else "B2" if delta <= B2_N_MARGIN + FLOAT_EQUAL else "B7",
            "SAME" if same else f"N_DIFFERENCE:{delta:.4f}")
    llm_caps = sorted(exposure.get("capBreaches") or [])
    core_caps = sorted((decision.get("exposure") or {}).get("caps") or [])
    if exposure:
        add("exposure:caps", "exposure", core_caps, llm_caps,
            "B1" if core_caps == llm_caps else "B6" if timing else "B7", "SAME" if core_caps == llm_caps else "CAP_SET")
    llm_peaks = {item.get("code"): item.get("state") for item in run.get("peakReviews") or [] if isinstance(item, dict)}
    for item in (decision.get("exposure") or {}).get("peaks") or []:
        if item["symbol"] not in llm_peaks:
            continue
        core_state, llm_state = item["state"], llm_peaks[item["symbol"]]
        same = (core_state in ("review", "hit")) == (llm_state == "hit") and (core_state == "near") == (llm_state == "near")
        distance = _r5_distance(item)
        near_line = distance is not None and distance <= B2_R5_MARGIN + FLOAT_EQUAL
        add(f"R5:{item['symbol']}", "r5", core_state, llm_state,
            "B1" if same else "B6" if timing else "B2" if near_line else "B7",
            "SAME" if same else "R5_DIFFERENCE" + ("" if distance is None else f":{distance:.4f}"))
    shock = run.get("shock") or {}
    core_shock = decision.get("shock") or {}
    if shock:
        same = bool(shock.get("open")) == bool(core_shock.get("open"))
        add("RREC:open", "rrec1", core_shock.get("open"), shock.get("open"),
            "B1" if same else "B6" if timing else "B7", "SAME" if same else "OPEN_DIFFERS")
        llm_rg = shock.get("rg") or {}
        for gate in ("RG1", "RG2", "RG3", "RG4"):
            core_value = (core_shock.get("rg") or {}).get(gate)
            llm_value = llm_rg.get(gate.lower(), llm_rg.get(gate))
            if core_value is None or llm_value is None:
                continue
            core_ok, llm_ok = core_value == "ok", llm_value in ("ok", True, "hit")
            if core_ok == llm_ok:
                add(f"RREC:{gate}", "rrec1", core_value, llm_value, "B1", "SAME")
            elif timing:
                add(f"RREC:{gate}", "rrec1", core_value, llm_value, "B6", "LLM_RUN_SESSION_OR_INCOMPLETE")
            elif gate == "RG1" and not research_ok:
                add(f"RREC:{gate}", "rrec1", core_value, llm_value, "B4", "RG1_NEEDS_RESEARCH_RECORD")
            elif gate == "RG3":
                add(f"RREC:{gate}", "rrec1", core_value, llm_value, "B2", "L0_REGULAR_LOW_DEFINITION")
            else:
                add(f"RREC:{gate}", "rrec1", core_value, llm_value, "B7", "UNEXPLAINED")
    out["b2_wide_count"] = len(out["b2_wide"])
    return out


def load_explained(path: Path = EXPLAINED_PATH) -> tuple[list[dict[str, Any]], list[str]]:
    """Cowork's explanations (schema: auto-core-compare.schema.json properties.explained_file)."""
    path = Path(path)
    if not path.is_file():
        return [], []
    try:
        document = load_json(path)
        schema = load_json(COMPARE_SCHEMA)["properties"]["explained_file"]
    except (OSError, ValueError, KeyError):
        return [], ["EXPLAINED_FILE_UNREADABLE"]
    errors = validate_instance(document, COMPARE_SCHEMA, schema_bytes=json.dumps(schema).encode("utf-8"))
    if errors:
        return [], ["EXPLAINED_FILE_INVALID"] + errors[:3]
    return list(document["items"]), []


def day_passes(day: str, unexplained: list[str], explained: list[dict[str, Any]]) -> bool:
    mine = [item for item in explained if item["date"] == day]
    if any(item["verdict"] == "CORE_BUG" for item in mine):
        return False
    llm_errors = {item["item_key"] for item in mine if item["verdict"] == "LLM_ERROR"}
    return all(key in llm_errors for key in unexplained)


def streak_block(decision: dict[str, Any] | None) -> dict[str, Any] | None:
    """The compare block one decide record contributes to the streak: a FAIL record (or an unreadable one, None)
    counts as not compared (r2 R2-10)."""
    if decision is None:
        return None
    if decision.get("status") == "FAIL":
        return {"status": "DECIDE_FAIL"}
    return decision.get("compare")


def streak(days: list[tuple[str, dict[str, Any] | None]], explained: list[dict[str, Any]]) -> int:
    """Recount from the start: days = [(run day, compare block or None)] in date order. Only a day without the
    integrated check's run copy (NO_RECORD) or without a new session (NO_NEW_SESSION, r3 R3-3) keeps the count; a
    compared day adds 1 when every B7 is explained as LLM_ERROR with no CORE_BUG; anything else (decide FAIL,
    ended before F1, unreadable) resets it (r2 R2-10)."""
    count = 0
    for day, block in days:
        status = (block or {}).get("status")
        if status in ("NO_RECORD", NO_NEW_SESSION):
            continue  # no integrated-check run copy, or the same session as before: kept
        if status != "COMPARED":
            count = 0
            continue
        count = count + 1 if day_passes(day, block.get("unexplained") or [], explained) else 0
    return count


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="Compare a decide record with the integrated check run (read only)")
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--explained", type=Path, default=EXPLAINED_PATH)
    args = parser.parse_args(argv)
    decision = load_json(args.decision)
    block = decision.get("compare") or {}
    explained, errors = load_explained(args.explained)
    print(json.dumps({"run_day_kst": decision.get("run_day_kst"), "status": block.get("status"),
                      "streak": block.get("streak"), "unexplained": block.get("unexplained"),
                      "categories": block.get("categories"), "explained_errors": errors,
                      "today_passes": day_passes(decision.get("run_day_kst"), block.get("unexplained") or [], explained)},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
