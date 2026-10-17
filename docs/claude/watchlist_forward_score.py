#!/usr/bin/env python3
"""wl-fwd-score: does the watchlist R2.1 score predict forward returns? (pre-registered 2026-10-17)

Pre-registration: docs/claude/watchlist-forward-score-preregistration-2026-10-17.md (criteria are fixed there,
this script only computes them). Read-only: reads every committed version of docs/claude/watchlist-registry.json
(git history) plus the working copy. Writes nothing. No authority, no orders.

Usage (repo root): python docs/claude/watchlist_forward_score.py [--horizon-weeks 4] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import subprocess
from pathlib import Path

REL = "docs/claude/watchlist-registry.json"
REPO = Path(__file__).resolve().parents[2]
# Pre-registered thresholds (section 4 of the pre-registration). Do not edit after 2026-10-17.
MIN_WEEKS, MIN_PAIRS = 8, 12
P1_RHO, P2_SHARE, P3_SPREAD = 0.15, 0.60, 0.02
PARTS = {"total": None, "biz": ("S1", "S2"), "price": ("S3", "S5", "S7"), "S4": ("S4",)}


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args], capture_output=True, timeout=120)


def load_documents(repo: Path) -> list[dict]:
    docs = []
    log = _git(repo, "log", "--reverse", "--format=%H", "--", REL)
    for rev in log.stdout.decode().split() if log.returncode == 0 else []:
        shown = _git(repo, "show", f"{rev}:{REL}")
        if shown.returncode == 0:
            try:
                docs.append(json.loads(shown.stdout.decode("utf-8-sig")))
            except ValueError:
                pass
    try:
        docs.append(json.loads((repo / REL).read_text(encoding="utf-8-sig")))
    except (OSError, ValueError):
        pass
    return docs


def snapshots(docs: list[dict]) -> dict[str, dict[str, dict]]:
    """{basis YYYYMMDD: {code: {score, items, close, role}}}; a row counts only when its close date = basis."""
    out: dict[str, dict[str, dict]] = {}
    for doc in docs:  # oldest first, so a later version of the same basis wins
        run = doc.get("weeklyRun") or {}
        basis = run.get("basis")
        if not basis:
            continue
        rows: dict[str, dict] = {}
        sources = [(c.get("code"), c, "candidate") for c in doc.get("candidates") or []]
        sources += [(code, m, "member") for code, m in (run.get("memberData") or {}).items()]
        for code, item, role in sources:
            detail = item.get("detail") or {}
            if not code or detail.get("closeDate") != basis or not isinstance(detail.get("close"), (int, float)):
                continue
            if not isinstance(item.get("score"), (int, float)) or not isinstance(item.get("items"), dict):
                continue
            rows[code] = {"score": item["score"], "items": item["items"], "close": float(detail["close"]),
                          "role": role}
        if rows:
            out[basis] = rows
    return out


def _day(basis: str) -> dt.date:
    return dt.date(int(basis[:4]), int(basis[4:6]), int(basis[6:]))


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2
        i = j + 1
    return ranks


def spearman(x: list[float], y: list[float]) -> float | None:
    if len(x) < 3:
        return None
    rx, ry = _ranks(x), _ranks(y)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sxx * syy) ** 0.5


def part_value(row: dict, part: str) -> float:
    keys = PARTS[part]
    return float(row["score"]) if keys is None else float(sum(row["items"].get(k) or 0 for k in keys))


def tercile_spread(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 6:
        return None
    k = n // 3
    hi_cut = sorted(xs, reverse=True)[k - 1]
    lo_cut = sorted(xs)[k - 1]
    top = [y for x, y in zip(xs, ys) if x >= hi_cut]
    bottom = [y for x, y in zip(xs, ys) if x <= lo_cut]
    if not top or not bottom or hi_cut == lo_cut:
        return None
    return statistics.fmean(top) - statistics.fmean(bottom)


def evaluate(snaps: dict[str, dict[str, dict]], horizon_weeks: int) -> dict:
    bases = sorted(snaps)
    weeks = []
    for base in bases:
        target = _day(base) + dt.timedelta(days=7 * horizon_weeks)
        fwd = [b for b in bases if abs((_day(b) - target).days) <= 3]
        if not fwd:
            continue
        later = snaps[fwd[0]]
        codes = sorted(set(snaps[base]) & set(later))
        rets = [later[c]["close"] / snaps[base][c]["close"] - 1 for c in codes]
        week = {"base": base, "forward": fwd[0], "pairs": len(codes)}
        for part in PARTS:
            xs = [part_value(snaps[base][c], part) for c in codes]
            week[part] = {"rho": spearman(xs, rets), "spread": tercile_spread(xs, rets)}
        weeks.append(week)
    usable = [w for w in weeks if w["pairs"] >= MIN_PAIRS]
    summary = {}
    for part in PARTS:
        rhos = [w[part]["rho"] for w in usable if w[part]["rho"] is not None]
        spreads = [w[part]["spread"] for w in usable if w[part]["spread"] is not None]
        summary[part] = {
            "weeks": len(rhos),
            "mean_rho": statistics.fmean(rhos) if rhos else None,
            "share_rho_pos": (sum(r > 0 for r in rhos) / len(rhos)) if rhos else None,
            "mean_spread": statistics.fmean(spreads) if spreads else None,
        }
        s = summary[part]
        if s["weeks"] < MIN_WEEKS:
            s["verdict"] = "INSUFFICIENT_SAMPLE"
        else:
            ok = (s["mean_rho"] >= P1_RHO and s["share_rho_pos"] >= P2_SHARE
                  and s["mean_spread"] is not None and s["mean_spread"] >= P3_SPREAD)
            s["verdict"] = "PASS" if ok else "FAIL"
    return {"horizon_weeks": horizon_weeks, "snapshots": bases, "weeks": weeks, "summary": summary,
            "criteria": {"min_weeks": MIN_WEEKS, "min_pairs": MIN_PAIRS, "P1_mean_rho": P1_RHO,
                         "P2_share_rho_pos": P2_SHARE, "P3_mean_tercile_spread": P3_SPREAD},
            "order_authority": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--horizon-weeks", type=int, default=4)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repo", type=Path, default=REPO)
    args = parser.parse_args()
    result = evaluate(snapshots(load_documents(args.repo)), args.horizon_weeks)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return
    fmt = lambda v, p=2: "-" if v is None else f"{v:.{p}f}"
    print(f"wl-fwd-score horizon {result['horizon_weeks']}w · snapshots {', '.join(result['snapshots'])}")
    for w in result["weeks"]:
        print(f"  {w['base']}->{w['forward']} n={w['pairs']} " + " ".join(
            f"{p}:rho {fmt(w[p]['rho'])}/spr {fmt(w[p]['spread'], 3)}" for p in PARTS))
    for part, s in result["summary"].items():
        print(f"  [{part}] weeks {s['weeks']} mean_rho {fmt(s['mean_rho'])} pos {fmt(s['share_rho_pos'])} "
              f"spread {fmt(s['mean_spread'], 3)} -> {s['verdict']}")


if __name__ == "__main__":
    main()
