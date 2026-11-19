#!/usr/bin/env python3
"""P1 freshness gate replay (pick-freshness-p1). READ ONLY.

Reads past core runs (workspace/outputs/auto-core/<day>/decision.json), finds the registry version each run
used (byte sha256 of the committed blob with CRLF line ends, the way the Windows working tree stores it),
drops buy-side card-table evidence whose as_of is not later than the latest actual earnings session A
(appendix A), and recomputes r_max / basis_met / new_basis_met / composition with the formula of
manage-us-stock-strategy/scripts/auto_core_tickets.py evidence_summary (lines 118-152). The formula is not
changed. Writes nothing; prints a JSON result to stdout.

Usage (repo root):  python3 docs/claude/pick_freshness_replay.py [--repo .] [--from 2026-10-13] [--to 2026-11-19]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

REGISTRY = "docs/claude/card-evidence-registry.json"
CORE_DIR = "workspace/outputs/auto-core"
CONFIG = "workspace/policies/auto_core.json"
C_ONLY_R_CAP = Fraction(1, 3)          # auto_core_tickets.py S["C_ONLY_R_CAP"]

# Appendix A: actual earnings sessions (US date) from SEC EDGAR 8-K Item 2.02 / 6-K, ascending.
# A session before the first listed one is unknown ("A 모름").
APPENDIX_A = {
    "PWR": ["2026-07-30", "2026-10-29"],
    "BE": ["2026-07-28", "2026-10-22"],
    "LITE": ["2026-08-11", "2026-11-02"],
    "MU": ["2026-06-24", "2026-09-30"],
    "DELL": ["2026-09-01"],
    "PLTR": ["2026-08-03", "2026-11-02"],
    "AMD": ["2026-08-04", "2026-11-03"],
    "NBIS": ["2026-11-12"],
    "MRVL": ["2026-08-27"],
}
# Appendix B: boundary exceptions (id, as_of) counted fresh. Fixed list; never grows after fixing.
EXCEPTION_B = {("BE-SE1", "2026-10-22"), ("LITE-SE1", "2026-11-02")}

# Answer key (prereg 5절), written before the run from registry as_of + appendix A only.
# (id, as_of) -> first evaluation session it must be caught as stale.
KEY_STALE = {
    ("PWR-SE1", "2026-10-03"): "2026-10-29",
    ("LITE-SE1", "2026-10-03"): "2026-11-02",
    ("LITE-SE3", "2026-10-03"): "2026-11-02",
    ("PLTR-SE1", "2026-10-17"): "2026-11-02",
    ("PLTR-SE3", "2026-10-17"): "2026-11-02",
    ("AMD-SE1", "2026-10-02"): "2026-11-03",
    # added after the fixing card, before any run, from registry versions + appendix A only (no core output)
    ("BE-SE1", "2026-10-02"): "2026-10-22",
    ("PWR-SE3", "2026-10-03"): "2026-10-29",
}
# Must stay fresh (counted) whenever they are used: id prefix or (id, as_of).
KEY_FRESH_PREFIX = ("MU-SE1", "MU-SE3", "DELL-")
KEY_FRESH_EXACT = {("BE-SE1", "2026-10-22"), ("LITE-SE1", "2026-11-02")}
KEY_FRESH_AS_OF_FROM = {"PLTR-": "2026-11-03"}   # PLTR v2 items (as_of >= 11-03)


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True).stdout


def registry_versions(repo: Path) -> dict[str, tuple[str, dict]]:
    """sha256 of CRLF bytes -> (commit, parsed registry) for every committed registry version."""
    out: dict[str, tuple[str, dict]] = {}
    for commit in git(repo, "log", "--format=%H", "--", REGISTRY).decode().split():
        blob = git(repo, "show", f"{commit}:{REGISTRY}")
        lf = blob.replace(b"\r\n", b"\n")
        for raw in (lf.replace(b"\n", b"\r\n"), lf):
            out.setdefault(hashlib.sha256(raw).hexdigest(), (commit[:7], json.loads(lf.decode("utf-8"))))
    return out


def earnings_session(symbol: str, session: str) -> str | None:
    past = [d for d in APPENDIX_A.get(symbol, []) if d <= session]
    return past[-1] if past else None


def freshness(item: dict, symbol: str, session: str) -> str:
    """fresh / stale / boundary / unknown (prereg 2절)."""
    a = earnings_session(symbol, session)
    if a is None:
        return "unknown"
    as_of = item.get("as_of") or ""
    if (item["id"], as_of) in EXCEPTION_B:
        return "fresh"
    if as_of < a:
        return "stale"
    if as_of == a:
        return "boundary"
    return "fresh"


def key_label(item_id: str, as_of: str, session: str) -> str:
    k = KEY_STALE.get((item_id, as_of))
    if k is not None:
        return "stale" if session >= k else "fresh_before"
    if (item_id, as_of) in KEY_FRESH_EXACT or item_id.startswith(KEY_FRESH_PREFIX):
        return "fresh"
    for prefix, start in KEY_FRESH_AS_OF_FROM.items():
        if item_id.startswith(prefix) and as_of >= start:
            return "fresh"
    return "outside_key"


def frac(text: str) -> Fraction:
    return Fraction(text)


def recompute(ev: dict, static_strong: list[str], static_weak: list[str], card_defined: bool | None,
              eligible: bool, cap: Fraction | None) -> dict | None:
    """auto_core_tickets.py evidence_summary lines 128-146, inputs taken from the stored buy evidence."""
    official = list(ev.get("official") or [])
    price_groups = list(ev.get("price_groups") or [])
    strong = static_strong + official
    weak_kinds = sorted(set(static_weak) | set(price_groups))
    new_strong = official
    new_kinds = list(ev.get("new_kinds") or [])
    r = Fraction(1) if strong else Fraction(1, 2) if len(weak_kinds) >= 2 else Fraction(0)
    if price_groups and not strong and not static_weak:
        if card_defined is None:
            return None                                     # cannot reproduce common_only
        common_only = not card_defined
    else:
        common_only = False
    if common_only:
        r = min(r, C_ONLY_R_CAP)
    research_only = bool(official) and not static_strong
    if research_only and cap is not None:
        r = min(r, cap)
    if not eligible:
        r = Fraction(0)
    composition = "C 단독" if common_only else "카드 표 {} + 새 {}".format(
        len(static_strong) + len(static_weak), len(new_strong) + len(new_kinds))
    return {"r_max": r, "basis_met": bool(strong) or len(weak_kinds) >= 2,
            "new_basis_met": bool(new_strong) or len(new_kinds) >= 2, "composition": composition}


def card_defined_from(symbol_result: dict | None) -> bool | None:
    """auto_core_rules.price_evidence side '+': a hit group counts as card-defined only when one of its card
    triggers is hit today. Rebuilt from decision.json symbols.<sym>.groups / triggers (stored by the core)."""
    if not symbol_result or "groups" not in symbol_result:
        return None
    hits = [g for g in symbol_result["groups"].values() if g.get("side") == "+" and g.get("state") == "hit"]
    card_hit = {t.get("group") for t in symbol_result.get("triggers") or []
                if t.get("source") == "card" and t.get("side") == "+" and t.get("state") == "hit"}
    return any(g["group"] in card_hit for g in hits)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--from", dest="start", default="2026-10-13")
    ap.add_argument("--to", dest="end", default="2026-11-19")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    cap_text = json.loads((repo / CONFIG).read_text(encoding="utf-8")).get("research_only_strong_r_cap")
    cap = Fraction(cap_text) if cap_text is not None else None
    versions = registry_versions(repo)

    days, skipped, invalid, rows = [], [], [], []
    for path in sorted((repo / CORE_DIR).glob("20*/decision.json")):
        day = path.parent.name
        if not (args.start <= day <= args.end):
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        session = d.get("evaluation_session")
        if not d.get("evidence") or not session:
            skipped.append({"day": day, "why": "evidence 또는 evaluation_session 없음"})
            continue
        sha = ((d.get("inputs") or {}).get("registry") or {}).get("sha256")
        hit = versions.get(sha or "")
        if hit is None:
            invalid.append({"day": day, "why": f"등록부 sha256 {str(sha)[:12]} 커밋 판 없음"})
            continue
        commit, registry = hit
        add_codes = {r["code"] for r in d.get("buy_requirements") or [] if r.get("add")}
        buy_tickets = sum(1 for t in d.get("tickets") or [] if str(t.get("side", "")).lower() == "buy")
        days.append({"day": day, "session": session, "registry": commit, "buy_tickets": buy_tickets})
        for symbol, sides in sorted(d["evidence"].items()):
            ev = sides.get("buy")
            if not ev:
                continue
            entry = (registry.get("symbols") or {}).get(symbol) or {}
            items = [i for i in entry.get("static_evidence") or []
                     if i.get("direction") == "+" and i.get("strength") != "neutral"]
            used_strong = [i for i in items if i["strength"] == "strong" and i["id"] in ev.get("static_strong", [])]
            used_weak = [i for i in items if i["strength"] == "weak" and i["e1_kind"] in ev.get("static_weak_kinds", [])]
            base = {"day": day, "session": session, "symbol": symbol}
            if not ev.get("static_strong") and not ev.get("static_weak_kinds"):
                continue                                        # no card-table evidence counted that day
            if sorted(i["id"] for i in used_strong) != sorted(ev["static_strong"]) or \
                    sorted({i["e1_kind"] for i in used_weak}) != sorted(ev["static_weak_kinds"]):
                rows.append({**base, "status": "재현 불일치(등록부 판과 코어 셈이 다름)"})
                continue
            card_defined = card_defined_from((d.get("symbols") or {}).get(symbol))
            if card_defined is not None and sorted(ev.get("price_groups") or []) != sorted(
                    g["group"] for g in d["symbols"][symbol]["groups"].values()
                    if g.get("side") == "+" and g.get("state") == "hit"):
                rows.append({**base, "status": "재현 불일치(가격 묶음)"})
                continue
            orig = recompute(ev, list(ev["static_strong"]), list(ev["static_weak_kinds"]), card_defined, True, cap)
            if orig is None:
                rows.append({**base, "status": "재현 불가(card_defined)"})
                continue
            eligible = not (frac(ev["r_max"]) == 0 and orig["r_max"] > 0)
            if orig["composition"] != ev["composition"] or (eligible and orig["basis_met"] != ev["basis_met"]):
                rows.append({**base, "status": "재현 불일치 composition/basis_met"})
                continue
            if eligible and orig["r_max"] != frac(ev["r_max"]):
                rows.append({**base, "status": f"재현 불일치 r_max {ev['r_max']} ≠ {orig['r_max']}"})
                continue
            marks = [{"id": i["id"], "as_of": i.get("as_of"), "kind": i["e1_kind"], "strength": i["strength"],
                      "state": freshness(i, symbol, session), "key": key_label(i["id"], i.get("as_of") or "", session)}
                     for i in used_strong + used_weak]
            out = {}
            for variant, drop in (("b_unknown_dropped", {"stale", "boundary", "unknown"}),
                                  ("a_unknown_counted", {"stale", "boundary"})):
                keep = {m["id"] for m in marks if m["state"] not in drop}
                s2 = [i["id"] for i in used_strong if i["id"] in keep]
                w2 = sorted({i["e1_kind"] for i in used_weak if i["id"] in keep})
                new = recompute(ev, s2, w2, card_defined, eligible, cap)
                if new is None:
                    out[variant] = {"status": "재현 불가(card_defined)"}
                    continue
                out[variant] = {"r_max": str(new["r_max"]), "basis_met": new["basis_met"],
                                "new_basis_met": new["new_basis_met"], "composition": new["composition"],
                                "changed_r_max": new["r_max"] != frac(ev["r_max"]),
                                "changed_basis": new["basis_met"] != ev["basis_met"],
                                "changed_composition": new["composition"] != ev["composition"]}
            rows.append({**base, "status": "ok", "add_row": symbol in add_codes,
                         "now": {k: ev[k] for k in ("r_max", "basis_met", "new_basis_met", "composition")},
                         "items": marks, **out})

    ok = [r for r in rows if r["status"] == "ok"]
    items = [(r["day"], r["session"], r["symbol"], m) for r in ok for m in r["items"]]
    caught = {(m["id"], m["as_of"], s) for _, s, _, m in items if m["state"] in ("stale", "boundary")}
    key_stale = {(m["id"], m["as_of"], s) for _, s, _, m in items if m["key"] == "stale"}
    missed = sorted(key_stale - caught)
    false_stale = sorted({(m["id"], m["as_of"], s) for _, s, _, m in items
                          if m["state"] in ("stale", "boundary") and m["key"] != "stale"})
    seen_keys = {(m["id"], m["as_of"]) for _, _, _, m in items}
    key_not_observed = sorted(k for k in KEY_STALE if k not in seen_keys)
    invalid_in_window = [x for x in invalid if x["day"] >= min(KEY_STALE.values())]

    def pick(variant: str, flag: str, add_only: bool = False) -> list:
        return [{"day": r["day"], "symbol": r["symbol"], "now": r["now"], "gate": r[variant]}
                for r in ok if r[variant].get(flag) and (r["add_row"] or not add_only)]

    result = {
        "replay": "pick-freshness-p1", "range": [args.start, args.end], "days": days, "skipped": skipped,
        "invalid": invalid, "not_reproduced": [r for r in rows if r["status"] != "ok"],
        "a_r_max_changed": pick("b_unknown_dropped", "changed_r_max"),
        "b_add_basis_changed": pick("b_unknown_dropped", "changed_basis", add_only=True),
        "c_composition_changed": pick("b_unknown_dropped", "changed_composition"),
        "d_buy_ticket_days": sum(1 for x in days if x["buy_tickets"]),
        "e_sell_side_changed": 0,                # sell side is never touched (static counts on buy only)
        "f_unknown": [{"day": d, "symbol": s, "id": m["id"]} for d, _, s, m in items if m["state"] == "unknown"],
        "f_variant_a_r_max_changed": pick("a_unknown_counted", "changed_r_max"),
        "g_qqq_lines": "재현 불가 — 134·161행은 통합 점검 출력이라 decision.json으로 다시 만들 수 없음",
        "key_check": {"key_stale_seen": sorted(key_stale), "missed": missed, "false_stale": false_stale,
                      "key_not_observed": key_not_observed},
    }
    variant_gaps = [{"day": r["day"], "symbol": r["symbol"]} for r in ok
                    for v in ("b_unknown_dropped", "a_unknown_counted") if r[v].get("status")]
    result["not_reproduced"] += variant_gaps
    if invalid_in_window or result["not_reproduced"]:
        verdict = "INVALID"
    elif false_stale:
        verdict = "FAIL"
    elif missed:
        verdict = "FAIL"
    elif not (result["a_r_max_changed"] or result["b_add_basis_changed"] or result["c_composition_changed"]):
        verdict = "NO_CHANGE"
    else:
        verdict = "ADOPT_CANDIDATE"
    result["verdict"] = verdict
    json.dump(result, sys.stdout, ensure_ascii=False, indent=1, default=str)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
