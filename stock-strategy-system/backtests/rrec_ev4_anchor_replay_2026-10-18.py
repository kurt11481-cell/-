#!/usr/bin/env python3
"""R-REC1 EV4 anchor replay (preregistration docs/claude/rrec-ev4-anchor-preregistration-2026-10-18.md).

Preregistration sha256 (raw = LF): 480ae3f71f554c64df76cfcce5c79b5347f3bc71cff5d53c3985ffec349aff97
(fixed 2026-10-18 09:00 KST, Q1 tail criterion = A c0). Historical computation only: no order tool, no
policy/state/journal/scheduled-task/production-code write.

Interpretations (numbers = preregistration sections):
J1 (3) proxy account A_0 = 28473.94 on the first session close, A_t = A_{t-1} (1 + L r_t) in float, total_t =
   Decimal(f"{A_t:.2f}"), HWM only on total > HWM, EV4_t = auto_core_rules.ev4_open(total_t, HWM_t) unchanged.
J2 (4/5) the ev4_sessions list given to rrec1 at session t = the variant's sessions inside the same 130-session
   view (all <= t). rrec1 only looks up days of its 60-session window, so this equals the full <= t list
   (self-test iii checks it on random sessions).
J3 (6) u_V = first session in [a, a+119] with status "ok" (so f_V = u_V + 1 <= a + 120). If S7 stop(u_V) is true
   the buy is "not bought" (no later retry). The reading that skips stopped sessions is reported as diagnostic S_alt.
J4 (6) anchors = E2 sessions of the proxy, at or after the evaluation start, passing the r3 left censor; no other
   date range (P2 anchors before 2011 are counted separately in the diagnostics).
J5 (6) anchor kind: first_touch (an E1 session), re_descent (L1 already touched earlier in the same HWM segment),
   v6_band (EV4 only through the V6 first line); l2_after = S7 stop(a) true (excluded from the main reading).
J6 (2-3) EV4 state share denominator = sessions with a return (n - 1).
J7 (5/6) P2: the proxy, EV4 lists, anchors and S7 stop come from the SOXX proxy on all SOXX dates; an EV4 session
   missing from a candidate's common dates moves to the next common date; an anchor missing there is dropped.
J8 (8 D6) Q250 = close_{a+250} / P - 1 or 0 (not bought); the buy cap stays a + 120.
J9 (8 D8) X_D = fixed delay D_V = round-half-up median (f_V - a) over V's main-reading pairs of the same sample
   (P2: pooled), decision session a + D_V - 1, same S7 stop and a + 120 cap.
"""
from __future__ import annotations

import argparse
import ast
import bisect
import csv
import hashlib
import json
import math
import random
import statistics
import sys
import types
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import numpy as np

REPO = Path(sys.argv[sys.argv.index("--repo") + 1]) if "--repo" in sys.argv else Path(".")
SCRIPTS = REPO / "manage-us-stock-strategy" / "scripts"
BT = REPO / "stock-strategy-system" / "backtests"
KR = BT / "fx5b_inputs_2026-10-09" / "kiwoom_raw"
PREREG = REPO / "docs" / "claude" / "rrec-ev4-anchor-preregistration-2026-10-18.md"
PREREG_SHA = "480ae3f71f554c64df76cfcce5c79b5347f3bc71cff5d53c3985ffec349aff97"
HASHES = {
    BT / "cpv_inputs_2026-10-01" / "SOX_yahoo_raw.csv": "a261cc8473368e29722a42fa120808d4f48ccdfc4d6ba91826ec0831e2f95167",
    BT / "soxl_signal_inputs_2026-10-01" / "SOXX_combined.csv": "00e8cdd030c38748eac563fc025222a16b2ada9e4cc09be3f6d7f28e224535f6",
    KR / "MU_kiwoom_usa06012_daily_adj1_20261009.json": "db9f9fa7a9e0492b5521ba8b7b10eb30a05005495417185622338f75f5359cc1",
    KR / "LITE_kiwoom_usa06012_daily_adj1_20261009.json": "d81ede0bb41ea3f692185352045ff721134085046dce256e52d0529ef3fbe193",
    KR / "DELL_kiwoom_usa06012_daily_adj1_20261009.json": "982a91b232255bf36f6affa75a0c134278df213aab35a18efa1e4cc087ae30cd",
    KR / "BE_kiwoom_usa06012_daily_adj1_20261009.json": "4f1f9aba713a05f63af24f9d81fbf1762e5953cab4f02856b5f03b3ab1de6426",
    KR / "PWR_kiwoom_usa06012_daily_adj1_20261009.json": "02d9c7d2b0b451581d5df10ea099134fd0a9dc5b82a112aaec32e273eecafc27",
    KR / "GRID_kiwoom_usa06012_daily_adj1_20261009.json": "538d94e6efba6e0114a98cffae7e65f9f8b0d7d7b7ca787a5fa79493bce8b50f",
    SCRIPTS / "auto_core_rules.py": "48433ab8d4c5eae45f9c6e54740e282cf5004807f5ce75842f64ea8cc4fbab4e",
    SCRIPTS / "portfolio_exposure.py": "9397108ee0f15696206f80681148cb20431d6deb72e915c5aa9774aff9b77a72",
    SCRIPTS / "auto_core_decide.py": "1013da08704fb74d7afb30455403d6d3e31f67d75392e93d1242f3c5cb7448f1",
    SCRIPTS / "auto_core_tickets.py": "2393fa7b19352fd435846aa67d68604b74ca1d73fb9a0e51b845931433afb8c1",
    REPO / "stock-strategy-system" / "alert_policy.json": "98ef14e0dfe1d56104a2863fcf7a61a1a9db9907355f923fde3bb5309f3e77a7",
    BT / "r_rec1_r3_replay_2026-10-16_episodes.csv": "6cb4125cf6dc81b651a9e1546d428273fb3a9b218af65fa07ca8f468460ef551",
}
SECTORS = {"MU": "B1 메모리", "LITE": "A3 광부품", "DELL": "AI 서버",
           "PWR": "A1 전력(그리드 시공)", "BE": "A1 전력(온사이트)"}
CANDIDATES = ["MU", "LITE", "DELL", "BE", "PWR"]
KEEP = 130
COST = 1.001
CAP = 120
A0 = 28473.94
L_MAIN, L_SENS = 1.55, (1.0, 2.0)
D09, D08 = Decimal("0.9"), Decimal("0.8")
FRACS = [Decimal(f"0.{k}") for k in range(9, 0, -1)]  # 0.9 ... 0.1 (E3)
VARIANTS = ["V0", "E1", "E2", "E3"]
JUDGED = ["E1", "E2"]
HALF = ("2010-12-31", "2011-01-01")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------ production code import (2-1, r3 I1)
def load_rules():
    raw = (SCRIPTS / "portfolio_exposure.py").read_bytes()
    src = raw.decode("utf-8")
    text = src.replace("\r\n", "\n")
    fn = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == "_sample_std"][0]
    seg = ast.get_source_segment(text, fn)
    assert (fn.lineno, fn.end_lineno) == (242, 246), (fn.lineno, fn.end_lineno)
    raw_lines = raw.split(b"\n")[241:246]
    seg_bytes = b"\n".join(line.rstrip(b"\r") for line in raw_lines)
    assert seg_bytes == seg.encode("utf-8"), "_sample_std bytes differ from lines 242-246"
    stub = types.ModuleType("portfolio_exposure")
    exec(compile("import math\n" + seg, "portfolio_exposure_sample_std", "exec"), stub.__dict__)
    sys.modules["portfolio_exposure"] = stub
    sys.path.insert(0, str(SCRIPTS))
    import auto_core_rules as rules  # noqa: E402
    return rules, seg


RULES, STD_SRC = None, None


# ------------------------------------------------------------------ data (2-2 = r3 2-2)
def load_sox():
    rows = list(csv.DictReader(open(BT / "cpv_inputs_2026-10-01" / "SOX_yahoo_raw.csv", encoding="utf-8")))
    return {r["date"]: {"open": float(r["open"]), "close": float(r["close"]), "high": float(r["high"]),
                        "low": float(r["low"]), "volume": float(r["volume"])} for r in rows}


def load_soxx():
    out = {}
    for r in csv.DictReader(open(BT / "soxl_signal_inputs_2026-10-01" / "SOXX_combined.csv", encoding="utf-8")):
        f = float(r["adjclose"]) / float(r["close"])
        out[r["date"]] = {"open": float(r["open"]) * f, "close": float(r["close"]) * f, "high": float(r["high"]) * f,
                          "low": float(r["low"]) * f, "volume": float(r["volume"])}
    return out


def load_kiwoom(symbol: str):
    path = next(KR.glob(f"{symbol}_kiwoom_usa06012_daily_adj1_*.json"))
    out = {}
    for x in json.loads(path.read_text(encoding="utf-8"))["result"]["result_list"]:
        d = f"{x['dt'][:4]}-{x['dt'][4:6]}-{x['dt'][6:]}"
        out[d] = {"open": float(x["open_pric"]), "close": float(x["cur_prc"]), "high": float(x["high_pric"]),
                  "low": float(x["low_pric"]), "volume": float(x["acc_trde_qty"] or 0)}
    return out


def series_on(bars: dict, days: list[str]):
    return RULES.build_series({"sessions": {d: bars[d] for d in days}}, days, days[-1])


def view(s: dict, t: int):
    lo = max(0, t - KEEP + 1)
    return {k: v[lo:t + 1] for k, v in s.items()}


def first_eval(bench, cand=None, rg2=None):
    keys = [bench] + ([cand] if cand else []) + ([rg2] if rg2 else [])
    return next(t for t in range(len(bench["days"]))
                if all(x["sigma60"][t] is not None and x["ema50"][t] is not None for x in keys))


# ------------------------------------------------------------------ proxy account and variant lists (3, 4)
def build_proxy(closes: list[float], lev: float, a0: float = A0, totals_override=None):
    """Returns totals, hwm, segment ids, EV4 flags, variant index lists, S7 stop flags, E1 set per segment."""
    n = len(closes)
    totals, hwms, seg = [], [], []
    if totals_override is None:
        a = a0
        for t in range(n):
            if t > 0:
                a = a * (1 + lev * (closes[t] / closes[t - 1] - 1))
            totals.append(Decimal(f"{a:.2f}"))
    else:
        totals = list(totals_override)
        n = len(totals)
    hwm, sid = None, -1
    for t in range(n):
        if hwm is None or totals[t] > hwm:
            hwm, sid = totals[t], sid + 1
        hwms.append(hwm)
        seg.append(sid)
    ev4 = [bool(RULES.ev4_open(totals[t], hwms[t])) for t in range(n)]
    e1, e3, seen1, seen3, l2first, e1_at = [], set(), set(), set(), {}, {}
    for t in range(n):
        s = seg[t]
        if s not in seen1 and totals[t] <= hwms[t] * D09:
            seen1.add(s)
            e1.append(t)
            e1_at[s] = t
        for j, fr in enumerate(FRACS):
            if (s, j) not in seen3 and totals[t] <= hwms[t] * fr:
                seen3.add((s, j))
                e3.add(t)
        if s not in l2first and totals[t] <= hwms[t] * D08:
            l2first[s] = t
    stop = [seg[t] in l2first and l2first[seg[t]] <= t for t in range(n)]
    lists = {"V0": [t for t in range(n) if ev4[t]], "E1": e1,
             "E2": [t for t in range(n) if ev4[t] and (t == 0 or not ev4[t - 1])], "E3": sorted(e3)}
    ratio = min(float(totals[t] / hwms[t]) for t in range(n))
    return {"totals": totals, "hwm": hwms, "seg": seg, "ev4": ev4, "lists": lists, "stop": stop,
            "e1_at": e1_at, "l2first": l2first, "min_ratio": ratio}


def anchor_kind(px: dict, a: int) -> str:
    s = px["seg"][a]
    if px["e1_at"].get(s) == a:
        return "first_touch"
    if s in px["e1_at"] and px["e1_at"][s] < a:
        return "re_descent"
    return "v6_band"


def move_to_common(dates: list[str], common: list[str]) -> list[str]:
    """P2 (5): an EV4 session missing from the common dates moves to the next common date (none after = dropped)."""
    out = set()
    for d in dates:
        k = bisect.bisect_left(common, d)
        if k < len(common):
            out.add(common[k])
    return sorted(out)


# ------------------------------------------------------------------ status runs (5)
def run_status(bench, cand, rg2, ev4_dates: set, start: int, symbol=None, full_list=None):
    out = [None] * len(bench["days"])
    for t in range(start, len(bench["days"])):
        vb = view(bench, t)
        ev = ([d for d in full_list if d <= bench["days"][t]] if full_list is not None
              else [d for d in vb["days"] if d in ev4_dates])
        kw = dict(benchmark=vb, candidate=None if cand is None else view(cand, t),
                  evaluation_session=bench["days"][t], ev3_user_dates=[], thesis_damage=[], ev4_sessions=ev,
                  candidate_symbol=symbol, research_sessions=None)
        if rg2 is not None:
            kw["rg2_series"] = view(rg2, t)
        out[t] = RULES.rrec1(**kw)
    return out


def end_kind(o: dict, day: str) -> str:
    if o.get("closed_at") == day:
        return "open" if all(v == "ok" for v in o["rg"].values()) else "decay"
    if o.get("closed_at") is None and not o["open"]:
        return "window_exit"
    return "other:" + str(o.get("closed_at"))


# ------------------------------------------------------------------ arms (6)
def pick(allowed, stop, a: int, n: int, use_stop=True, skip_stopped=False):
    """(u, f, state). u in [a, a+CAP-1] first allowed; state bought / stopped / cash / data_end."""
    for k in range(a, min(n, a + CAP)):
        if allowed[k] and not (skip_stopped and stop[k]):
            if use_stop and stop[k]:
                return k, None, "stopped"
            if k + 1 >= n:
                return k, None, "data_end"
            return k, k + 1, "bought"
    return None, None, "cash"


def fixed(stop, a: int, delay: int, n: int, use_stop=True):
    u = a + delay - 1
    if delay < 1 or delay > CAP:
        return None, None, "cash"
    if u >= n:
        return u, None, "data_end"
    if use_stop and stop[u]:
        return u, None, "stopped"
    if u + 1 >= n:
        return u, None, "data_end"
    return u, u + 1, "bought"


def arm_metrics(price: dict, a: int, f):
    c, lo = price["close"], price["low"]
    n = len(c)
    out = {"f": f, "P": None, "R60": None, "MAE60": None,
           "Q120": (0.0 if a + 120 < n else None), "Q250": (0.0 if a + 250 < n else None)}
    if f is None:
        return out
    p = c[f] * COST
    out["P"] = p
    if f + 60 < n:
        out["R60"] = c[f + 60] / p - 1
        out["MAE60"] = min(lo[f + 1:f + 61]) / p - 1
    if a + 120 < n:
        out["Q120"] = c[a + 120] / p - 1
    if a + 250 < n:
        out["Q250"] = c[a + 250] / p - 1
    return out


def med(x):
    return statistics.median(x) if x else None


def pct10(x):
    return float(np.percentile(x, 10)) if x else None


def half_up(x: float) -> int:
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def anchor_records(sample: str, days, price, stop, anchors, allowed: dict, status: dict, lev):
    """anchors: list of (index, kind). One record per anchor with every arm (main, no-stop, alt readings)."""
    n = len(days)
    recs = []
    for a, kind in anchors:
        r = {"sample": sample, "L": lev, "a": a, "date": days[a], "kind": kind, "stop_a": stop[a], "arms": {},
             "nostop": {}, "alt": {}, "u": {}}
        for v in allowed:
            u, f, st = pick(allowed[v], stop, a, n)
            m = arm_metrics(price, a, f)
            m.update(u=u, state=st, delay=None if f is None else f - a,
                     end=None if u is None else end_kind(status[v][u], days[u]))
            r["arms"][v] = m
            u2, f2, st2 = pick(allowed[v], stop, a, n, use_stop=False)
            r["nostop"][v] = dict(arm_metrics(price, a, f2), state=st2)
            u3, f3, st3 = pick(allowed[v], stop, a, n, skip_stopped=True)
            r["alt"][v] = dict(arm_metrics(price, a, f3), state=st3)
        for lab, use in (("arms", True), ("nostop", False)):
            u, f, st = fixed(stop, a, 1, n, use_stop=use)
            r[lab]["X1p"] = dict(arm_metrics(price, a, f), state=st)
        r["alt"]["X1p"] = r["arms"]["X1p"]
        recs.append(r)
    return recs


def judge(recs: list, v: str, reading="arms", main_only=True):
    base = [r for r in recs if not (main_only and r["stop_a"])]
    q = [r for r in base if r[reading]["V0"]["Q120"] is not None]
    pairs = [r for r in base if r[reading][v]["R60"] is not None and r[reading]["X1p"]["R60"] is not None]
    out = {"anchors": len(base), "q_anchors": len(q), "pairs": len(pairs)}
    if q:
        qe, q0 = [r[reading][v]["Q120"] for r in q], [r[reading]["V0"]["Q120"] for r in q]
        out.update(d=med(qe) - med(q0), q120_med=med(qe), q120_med_v0=med(q0),
                   bought_share_q=sum(1 for r in q if r[reading][v]["f"] is not None) / len(q))
    if pairs:
        re_, rx = [r[reading][v]["R60"] for r in pairs], [r[reading]["X1p"]["R60"] for r in pairs]
        me, mx = [r[reading][v]["MAE60"] for r in pairs], [r[reading]["X1p"]["MAE60"] for r in pairs]
        out.update(b=med(re_) - med(rx), c0=pct10(me) - pct10(mx), r60_med=med(re_), r60_med_x1p=med(rx),
                   p10_mae=pct10(me), p10_mae_x1p=pct10(mx), worst_r60=min(re_), worst_mae=min(me),
                   worst_r60_x1p=min(rx), worst_mae_x1p=min(mx))
    out["short"] = len(q) < 15 or len(pairs) < 15
    return out


def criteria_ok(j: dict, need_b=True):
    if j["short"] or "d" not in j or "c0" not in j:
        return False
    return j["d"] > 0 and (j["b"] >= -0.03 if need_b else True) and j["c0"] >= 0


def verdict(tab: dict):
    """tab[sample][variant] = judge(). Samples P1, P1a, P1b, P2, P1_L1.0, P1_L2.0."""
    out = {}
    for v in JUDGED:
        p1 = tab["P1"][v]
        if p1["short"]:
            out[v] = {"pass": False, "hold": "P1 sample short"}
            continue
        steps = {"1_P1": criteria_ok(p1), "2_P1a": criteria_ok(tab["P1a"][v]), "2_P1b": criteria_ok(tab["P1b"][v]),
                 "3_P2": criteria_ok(tab["P2"][v]),
                 "4_L1.0": criteria_ok(tab["P1_L1.0"][v], need_b=False),
                 "4_L2.0": criteria_ok(tab["P1_L2.0"][v], need_b=False)}
        out[v] = {"pass": all(steps.values()), "steps": steps,
                  "P1_parts": {"d": p1.get("d"), "d_ok": p1.get("d", -1) > 0, "b": p1.get("b"),
                               "b_ok": p1.get("b", -1) >= -0.03, "c0": p1.get("c0"), "c0_ok": p1.get("c0", -1) >= 0}}
    passed = [v for v in JUDGED if out[v]["pass"]]
    chosen = "E1" if "E1" in passed else (passed[0] if passed else None)
    return {"by_variant": out, "chosen": chosen, "disposition": "ADOPT_CANDIDATE" if chosen else "NO_CHANGE"}


# ------------------------------------------------------------------ samples
def p1_context(sox_series, lev, statuses_cache, variants):
    days = sox_series["days"]
    px = build_proxy(sox_series["close"], lev)
    st = first_eval(sox_series)
    lists = {v: set(days[k] for k in px["lists"][v]) for v in variants}
    status = {v: statuses_cache.get((lev, v)) or run_status(sox_series, None, None, lists[v], st) for v in variants}
    for v in variants:
        statuses_cache[(lev, v)] = status[v]
    allowed = {v: [None if o is None else o["status"] == "ok" for o in status[v]] for v in variants}
    anchors, drop = [], {"before_eval": 0, "left_censor": 0}
    for a in px["lists"]["E2"]:
        if a < st:
            drop["before_eval"] += 1
            continue
        if not all(k >= 0 and sox_series["sigma60"][k] is not None for k in range(a - 59, a + 1)):
            drop["left_censor"] += 1
            continue
        anchors.append((a, anchor_kind(px, a)))
    return {"days": days, "px": px, "start": st, "status": status, "allowed": allowed, "anchors": anchors,
            "drop": drop, "lists": lists}


def p2_contexts(soxx_bars, grid, variants):
    soxx_days = sorted(soxx_bars)
    soxx_full = series_on(soxx_bars, soxx_days)
    px = build_proxy(soxx_full["close"], L_MAIN)
    out = {}
    for sym in CANDIDATES:
        cb = load_kiwoom(sym)
        g = RULES.rg2_benchmark(SECTORS[sym])
        days = sorted(set(soxx_bars) & set(cb) & (set(grid) if g == "GRID" else set(soxx_bars)))
        bench, cand = series_on(soxx_bars, days), series_on(cb, days)
        rg2 = series_on(grid, days) if g == "GRID" else None
        assert bench["days"] == cand["days"] == days
        st = first_eval(bench, cand, rg2)
        full_idx = {d: i for i, d in enumerate(soxx_days)}
        stop = [px["stop"][full_idx[d]] for d in days]
        lists = {v: set(move_to_common([soxx_days[k] for k in px["lists"][v]], days)) for v in variants}
        status = {v: run_status(bench, cand, rg2, lists[v], st, sym) for v in variants}
        allowed = {v: [None if o is None else o["status"] == "ok" for o in status[v]] for v in variants}
        pos = {d: i for i, d in enumerate(days)}
        anchors, drop = [], {"not_common": 0, "before_eval": 0, "left_censor": 0}
        for k in px["lists"]["E2"]:
            d = soxx_days[k]
            if d not in pos:
                drop["not_common"] += 1
                continue
            a = pos[d]
            if a < st:
                drop["before_eval"] += 1
                continue
            if not all(j >= 0 and bench["sigma60"][j] is not None and cand["sigma60"][j] is not None
                       for j in range(a - 59, a + 1)):
                drop["left_censor"] += 1
                continue
            anchors.append((a, anchor_kind(px, k)))
        out[sym] = {"days": days, "bench": bench, "cand": cand, "rg2": rg2, "rg2_name": g, "start": st,
                    "stop": stop, "lists": lists, "status": status, "allowed": allowed, "anchors": anchors,
                    "drop": drop}
    return px, soxx_days, out


def structure_counts(px, days, anchors, lev):
    n = len(days)
    main = [(a, k) for a, k in anchors if not px["stop"][a]]
    return {"L": lev, "drawdown_events_l1": len(px["e1_at"]),
            "ev4_state_sessions": sum(px["ev4"][1:]), "sessions_with_return": n - 1,
            "anchors": len(anchors), "anchors_range": [days[anchors[0][0]], days[anchors[-1][0]]] if anchors else None,
            "anchors_first_touch": sum(1 for _, k in anchors if k == "first_touch"),
            "anchors_re_descent": sum(1 for _, k in anchors if k == "re_descent"),
            "anchors_v6_band": sum(1 for _, k in anchors if k == "v6_band"),
            "anchors_l2_after": sum(1 for a, _ in anchors if px["stop"][a]),
            "main_anchors": len(main), "main_le2010": sum(1 for a, _ in main if days[a] <= HALF[0]),
            "main_ge2011": sum(1 for a, _ in main if days[a] >= HALF[1]),
            "q120_anchors_all": sum(1 for a, _ in anchors if a + 120 < n), "min_ratio": px["min_ratio"]}


# ------------------------------------------------------------------ diagnostics (8)
def ev2_flags(s):
    sig = RULES.C["RREC_EV2_SIGMA"]
    return [s["sigma60"][i] is not None and s["hi20"][i] is not None and
            s["close"][i] <= s["hi20"][i] * (1 - sig * s["sigma60"][i]) for i in range(len(s["days"]))]


def d1_d3(series, start, status, ev4flags, variants):
    ev2 = ev2_flags(series)
    pos = {d: i for i, d in enumerate(series["days"])}
    out = {}
    n = len(series["days"])
    for v in variants:
        ts = range(start, n)
        blocked = [t for t in ts if status[v][t]["status"] != "ok"]
        rep = [t for t in blocked if (status[v][t].get("event") or {}).get("kinds") == ["EV2"]
               and pos[status[v][t]["event"]["date"]] > 0 and ev2[pos[status[v][t]["event"]["date"]] - 1]]
        out[v] = {"blocked_share": len(blocked) / len(ts), "ev2_rebase_share_of_blocked":
                  (len(rep) / len(blocked)) if blocked else None}
    if ev4flags is not None:
        out["ev4_state_share_eval"] = sum(1 for t in range(start, n) if ev4flags[t]) / (n - start)
    return out


def d2(recs, v):
    main = [r for r in recs if not r["stop_a"]]
    arms = [r["arms"][v] for r in main]
    bought = [a for a in arms if a["f"] is not None]
    ends = {}
    for a in arms:
        if a["end"] is not None:
            ends[a["end"]] = ends.get(a["end"], 0) + 1
    return {"n": len(main), "delay_median": med([a["delay"] for a in bought]),
            "delay_q": [float(np.percentile([a["delay"] for a in bought], q)) for q in (25, 50, 75)] if bought else None,
            "cash_share": sum(1 for a in arms if a["state"] == "cash") / len(arms) if arms else None,
            "stopped_share": sum(1 for a in arms if a["state"] == "stopped") / len(arms) if arms else None,
            "data_end": sum(1 for a in arms if a["state"] == "data_end"), "end_kind_at_u": ends,
            "window_exit": ends.get("window_exit", 0)}


def d6(recs, v):
    main = [r for r in recs if not r["stop_a"]]
    q = [r for r in main if r["arms"]["V0"]["Q250"] is not None]
    jv, j0 = judge(recs, v), judge(recs, "V0")
    return {"worst_r60": jv.get("worst_r60"), "worst_mae60": jv.get("worst_mae"), "p10_mae60": jv.get("p10_mae"),
            "v0_worst_r60": j0.get("worst_r60"), "v0_worst_mae60": j0.get("worst_mae"), "v0_p10_mae60": j0.get("p10_mae"),
            "x1p_worst_r60": jv.get("worst_r60_x1p"), "x1p_worst_mae60": jv.get("worst_mae_x1p"),
            "x1p_p10_mae60": jv.get("p10_mae_x1p"),
            "p10_mae60_minus_v0": (jv["p10_mae"] - j0["p10_mae"]) if "p10_mae" in jv and "p10_mae" in j0 else None,
            "q250_n": len(q), "q250_med": med([r["arms"][v]["Q250"] for r in q]),
            "q250_med_v0": med([r["arms"]["V0"]["Q250"] for r in q]),
            "q250_med_x1p": med([r["arms"]["X1p"]["Q250"] for r in q if r["arms"]["X1p"]["Q250"] is not None])}


def d8(recs, v, price_of, n_of):
    """J9: fixed-delay arm X_D with D_V = round-half-up median delay over V's main pairs."""
    main = [r for r in recs if not r["stop_a"]]
    pairs = [r for r in main if r["arms"][v]["R60"] is not None and r["arms"]["X1p"]["R60"] is not None]
    if not pairs:
        return None
    dv = half_up(med([r["arms"][v]["delay"] for r in pairs]))
    both = []
    for r in main:
        price, n = price_of(r), n_of(r)
        u, f, st = fixed(stops_of(r), r["a"], dv, n)
        m = arm_metrics(price, r["a"], f)
        if r["arms"][v]["R60"] is not None and m["R60"] is not None:
            both.append((r["arms"][v], m))
    if not both:
        return {"D": dv, "pairs": 0}
    return {"D": dv, "pairs": len(both),
            "r60_med_minus_xd": med([x["R60"] for x, _ in both]) - med([y["R60"] for _, y in both]),
            "p10_mae60_minus_xd": pct10([x["MAE60"] for x, _ in both]) - pct10([y["MAE60"] for _, y in both])}


_STOPS = {}


def stops_of(r):
    return _STOPS[(r["sample"], r["L"])]


def d7_records():
    """Actual decide records (read only): account.ev4_open, total, s7_hwm_usd per evaluation session."""
    base = REPO / "workspace" / "outputs" / "auto-core"
    rows = []
    for p in sorted(base.glob("2026-10-*/decision.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        acc = d.get("account") or {}
        rows.append({"session": d.get("evaluation_session"), "ev4_open": acc.get("ev4_open"),
                     "total": acc.get("total"), "hwm": acc.get("s7_hwm_usd"), "file": str(p.relative_to(REPO))})
    rows = [r for r in rows if r["session"] and "2026-10-12" <= r["session"] <= "2026-10-16"]
    rows.sort(key=lambda r: r["session"])
    v0 = [r["session"] for r in rows if r["ev4_open"]]
    e2 = [r["session"] for i, r in enumerate(rows) if r["ev4_open"] and (i == 0 or not rows[i - 1]["ev4_open"])]
    e1, e3, seen = [], [], set()
    hwms = {r["hwm"] for r in rows}
    for r in rows:
        tot, h = Decimal(str(r["total"])), Decimal(str(r["hwm"]))
        if "L1" not in seen and tot <= h * D09:
            seen.add("L1")
            e1.append(r["session"])
        hit = False
        for fr in FRACS:
            if fr not in seen and tot <= h * fr:
                seen.add(fr)
                hit = True
        if hit:
            e3.append(r["session"])
    return {"rows": rows, "hwm_values": sorted(str(h) for h in hwms), "V0": v0, "E1": e1, "E2": e2, "E3": e3,
            "note": "E1/E3 count from the first record (2026-10-12); an L1 touch in the same drawdown before it is 확인 필요"}


# ------------------------------------------------------------------ r3 frame (D4) and self-test (i)
def r3_episodes(days, bench, cand, status, start, lo, hi):
    n = len(days)
    allowed = {t: status[t]["status"] == "ok" for t in range(start, n)}
    eps = []
    for t in range(start + 1, n):
        if not (allowed[t - 1] and not allowed[t]):
            continue
        if not (lo <= days[t] <= hi):
            continue
        if not all(k >= 0 and bench["sigma60"][k] is not None and (cand is None or cand["sigma60"][k] is not None)
                   for k in range(t - 59, t + 1)):
            continue
        u = next((k for k in range(t + 1, n) if allowed[k]), None)
        if u is None:
            continue
        eps.append({"t0": t, "u": u, "kind": end_kind(status[u], days[u]), "delay": u + 1 - t})
    return eps


def r3_frame(days, price, eps):
    """D4: r3 section 5 numbers a, b, c on G (u+1) vs X1' (t0+1), pairs with R60 and MAE60 complete."""
    rows = []
    for e in eps:
        g, x = arm_metrics(price, e["t0"], e["u"] + 1 if e["u"] + 1 < len(days) else None), \
            arm_metrics(price, e["t0"], e["t0"] + 1)
        if g["R60"] is not None and x["R60"] is not None:
            rows.append((g, x, e))
    if not rows:
        return {"episodes": len(eps), "pairs": 0}
    gm, xm = [g["MAE60"] for g, _, _ in rows], [x["MAE60"] for _, x, _ in rows]
    gr, xr = [g["R60"] for g, _, _ in rows], [x["R60"] for _, x, _ in rows]
    return {"episodes": len(eps), "pairs": len(rows), "a": med(gm) - med(xm), "b": med(gr) - med(xr),
            "c": pct10(gm) - pct10(xm), "delay_median": med([e["delay"] for _, _, e in rows]),
            "window_exit": sum(1 for e in eps if e["kind"] == "window_exit")}


def r3_reference():
    out = {}
    with open(BT / "r_rec1_r3_replay_2026-10-16_episodes.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["variant"] == "V0":
                out.setdefault(r["sample"], []).append((r["t0"], r["u"], r["kind"]))
    return out


# ------------------------------------------------------------------ main
def check_hashes():
    for p, h in HASHES.items():
        assert sha(p) == h, f"hash mismatch {p}"
    raw = PREREG.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PREREG_SHA, "preregistration raw sha256 differs"
    assert hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest() == PREREG_SHA, "preregistration LF sha256 differs"


def main_run(out_dir: Path):
    check_hashes()
    sox = load_sox()
    sox_s = series_on(sox, sorted(sox))
    soxx, grid = load_soxx(), load_kiwoom("GRID")
    cache = {}
    p1 = {L_MAIN: p1_context(sox_s, L_MAIN, cache, VARIANTS)}
    for lev in L_SENS:
        p1[lev] = p1_context(sox_s, lev, cache, ["V0", "E1", "E2"])
    soxx_px, soxx_days, p2 = p2_contexts(soxx, grid, VARIANTS)

    recs = {}
    for lev, ctx in p1.items():
        _STOPS[("P1", lev)] = ctx["px"]["stop"]
        recs[("P1", lev)] = anchor_records("P1", ctx["days"], sox_s, ctx["px"]["stop"], ctx["anchors"],
                                           ctx["allowed"], ctx["status"], lev)
    for sym, ctx in p2.items():
        _STOPS[(sym, L_MAIN)] = ctx["stop"]
        recs[(sym, L_MAIN)] = anchor_records(sym, ctx["days"], ctx["cand"], ctx["stop"], ctx["anchors"],
                                             ctx["allowed"], ctx["status"], L_MAIN)
    r1 = recs[("P1", L_MAIN)]
    parts = {"P1": r1, "P1a": [r for r in r1 if r["date"] <= HALF[0]], "P1b": [r for r in r1 if r["date"] >= HALF[1]],
             "P2": [r for sym in CANDIDATES for r in recs[(sym, L_MAIN)]],
             "P1_L1.0": recs[("P1", 1.0)], "P1_L2.0": recs[("P1", 2.0)]}
    parts.update({f"P2_{sym}": recs[(sym, L_MAIN)] for sym in CANDIDATES})
    parts["P2_ge2011"] = [r for r in parts["P2"] if r["date"] >= HALF[1]]
    tab = {}
    for k, rr in parts.items():
        vs = ["V0", "E1", "E2"] + (["E3"] if not k.startswith("P1_L") else [])
        tab[k] = {v: judge(rr, v) for v in vs}
    ver = verdict(tab)

    price_of = (lambda r: sox_s if r["sample"] == "P1" else p2[r["sample"]]["cand"])
    n_of = (lambda r: len(sox_s["days"]) if r["sample"] == "P1" else len(p2[r["sample"]]["days"]))
    diag = {"structure": {}, "drops": {}, "D1_D3": {}, "D2": {}, "D4": {}, "D5": {}, "D6": {}, "D8": {},
            "S_alt": {}, "P2_ge2011": {}}
    for lev, ctx in p1.items():
        diag["structure"][f"P1_L{lev}"] = structure_counts(ctx["px"], ctx["days"], ctx["anchors"], lev)
        diag["drops"][f"P1_L{lev}"] = ctx["drop"]
        diag["D1_D3"][f"P1_L{lev}"] = d1_d3(sox_s, ctx["start"], ctx["status"], ctx["px"]["ev4"], list(ctx["status"]))
    soxx_all_anchors = [(a, anchor_kind(soxx_px, a)) for a in soxx_px["lists"]["E2"]]
    diag["structure"]["SOXX_proxy_all_E2"] = structure_counts(soxx_px, soxx_days, soxx_all_anchors, L_MAIN)
    for sym, ctx in p2.items():
        diag["drops"][sym] = dict(ctx["drop"], kept=len(ctx["anchors"]), rg2=ctx["rg2_name"],
                                  first_eval=ctx["days"][ctx["start"]],
                                  pre2011_kept=sum(1 for a, _ in ctx["anchors"] if ctx["days"][a] < HALF[1]))
        n = len(ctx["days"])
        ev4f = [d in ctx["lists"]["V0"] for d in ctx["days"]]
        diag["D1_D3"][sym] = d1_d3(ctx["bench"], ctx["start"], ctx["status"], ev4f, VARIANTS)
    for k in ("P1", "P1a", "P1b", "P2", "P1_L1.0", "P1_L2.0"):
        vs = ["V0", "E1", "E2"] + (["E3"] if not k.startswith("P1_L") else [])
        diag["D2"][k] = {v: d2(parts[k], v) for v in vs}
        diag["D6"][k] = {v: d6(parts[k], v) for v in vs if v != "V0"}
        diag["D8"][k] = {v: d8(parts[k], v, price_of, n_of) for v in vs}
        diag["S_alt"][k] = {v: judge(parts[k], v, reading="alt") for v in vs}
    for k in ("P1", "P2"):
        rr = parts[k]
        diag["D5"][k] = {"nostop_all_anchors": {v: judge(rr, v, reading="nostop", main_only=False)
                                                for v in VARIANTS},
                         "by_kind": {kind: {v: judge([r for r in rr if r["kind"] == kind and not r["stop_a"]], v)
                                            for v in VARIANTS}
                                     for kind in ("first_touch", "re_descent", "v6_band")},
                         "l2_after_nostop": {v: judge([r for r in rr if r["stop_a"]], v, reading="nostop",
                                                      main_only=False) for v in VARIANTS}}
    # D4: r3 section 5 frame
    st = p1[L_MAIN]["start"]
    for v in VARIANTS:
        e = r3_episodes(sox_s["days"], sox_s, None, p1[L_MAIN]["status"][v], st, "0000-00-00", "2010-12-31")
        diag["D4"][f"SOX_le2010/{v}"] = r3_frame(sox_s["days"], sox_s, e)
        e = r3_episodes(sox_s["days"], sox_s, None, p1[L_MAIN]["status"][v], st, "2011-01-03", "2026-09-29")
        diag["D4"][f"SOX_ge2011/{v}"] = r3_frame(sox_s["days"], sox_s, e)
        pooled = {"episodes": 0}
        rows = []
        for sym, ctx in p2.items():
            e = r3_episodes(ctx["days"], ctx["bench"], ctx["cand"], ctx["status"][v], ctx["start"],
                            "2011-01-03", "2026-09-29")
            rows.append(r3_frame(ctx["days"], ctx["cand"], e))
        diag["D4"][f"P2_per_candidate/{v}"] = rows
    diag["D7"] = d7_records()

    results = {"prereg_sha256": PREREG_SHA, "verdict": ver, "table": tab, "diagnostics": diag,
               "first_eval": {"P1": sox_s["days"][p1[L_MAIN]["start"]]},
               "data_end": {"SOX": sox_s["days"][-1], "SOXX": soxx_days[-1]}}
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = "rrec_ev4_anchor_replay_2026-10-18"
    (out_dir / f"{stem}_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=1, default=str),
                                                  encoding="utf-8", newline="\n")
    with open(out_dir / f"{stem}_anchors.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        head = ["sample", "L", "anchor", "kind", "stop_a"]
        arms = VARIANTS + ["X1p"]
        for v in arms:
            head += [f"{v}_state", f"{v}_delay", f"{v}_end", f"{v}_R60", f"{v}_MAE60", f"{v}_Q120", f"{v}_Q250"]
        w.writerow(head)
        for key in sorted(recs, key=lambda k: (k[0] != "P1", k[0], k[1])):
            for r in recs[key]:
                row = [r["sample"], r["L"], r["date"], r["kind"], int(r["stop_a"])]
                for v in arms:
                    m = r["arms"].get(v)
                    if m is None:
                        row += [""] * 7
                        continue
                    row += [m.get("state"), m.get("delay", "") if v != "X1p" else (1 if m["f"] is not None else ""),
                            m.get("end", ""), m["R60"], m["MAE60"], m["Q120"], m["Q250"]]
                w.writerow(row)
    return results


# ------------------------------------------------------------------ self-test (9 step 2)
def self_test():
    check_hashes()
    groups = {}
    sox = load_sox()
    sox_s = series_on(sox, sorted(sox))
    soxx, grid = load_soxx(), load_kiwoom("GRID")

    # (i) r3 call as is (ev4_sessions = []) reproduces the r3 V0 episode rows (t0, u, end kind)
    ref = r3_reference()
    got = {}
    st = first_eval(sox_s)
    status = run_status(sox_s, None, None, set(), st)
    got["SOX"] = [(sox_s["days"][e["t0"]], sox_s["days"][e["u"]], e["kind"])
                  for e in r3_episodes(sox_s["days"], sox_s, None, status, st, "0000-00-00", "2010-12-31")]
    soxx_s = series_on(soxx, sorted(soxx))
    st = first_eval(soxx_s)
    status = run_status(soxx_s, None, None, set(), st)
    got["SOXX"] = [(soxx_s["days"][e["t0"]], soxx_s["days"][e["u"]], e["kind"])
                   for e in r3_episodes(soxx_s["days"], soxx_s, None, status, st, "2011-01-03", "2026-09-29")]
    for sym in CANDIDATES:
        cb = load_kiwoom(sym)
        g = RULES.rg2_benchmark(SECTORS[sym])
        days = sorted(set(soxx) & set(cb) & (set(grid) if g == "GRID" else set(soxx)))
        bench, cand = series_on(soxx, days), series_on(cb, days)
        rg2 = series_on(grid, days) if g == "GRID" else None
        st = first_eval(bench, cand, rg2)
        status = run_status(bench, cand, rg2, set(), st, sym)
        got[sym] = [(days[e["t0"]], days[e["u"]], e["kind"])
                    for e in r3_episodes(days, bench, cand, status, st, "2011-01-03", "2026-09-29")]
    mism = {k: {"ref": len(ref.get(k, [])), "got": len(got[k]),
                "diff": sorted(set(ref.get(k, [])) ^ set(got[k]))[:5]} for k in got if ref.get(k, []) != got[k]}
    assert not mism, f"self-test (i) failed: {mism}"
    groups["i"] = {k: len(v) for k, v in got.items()}

    # (ii) proxy EV4 = rules.ev4_open, E1-E3 unit cases
    px = build_proxy(sox_s["close"], L_MAIN)
    for t in range(len(px["totals"])):
        tot, h = px["totals"][t], px["hwm"][t]
        assert px["ev4"][t] == (tot <= Decimal("25626.55") or tot <= h * Decimal("0.9")), t
    def lists_of(seq):
        return build_proxy([], 1.0, totals_override=[Decimal(x) for x in seq])
    q = lists_of(["30000.00", "27000.01", "27000.00", "27000.01", "26000.00"])  # 1-cent boundary
    assert q["ev4"] == [False, False, True, False, True] and q["lists"]["E1"] == [2] and q["lists"]["E2"] == [2, 4]
    q = lists_of(["30000.00", "26999.00", "30000.00", "26999.00", "30000.01", "26999.00"])  # equal HWM no rearm
    assert q["seg"] == [0, 0, 0, 0, 1, 1] and q["lists"]["E1"] == [1, 5] and q["lists"]["E2"] == [1, 3, 5]
    q = lists_of(["30000.00", "20000.00", "17000.00", "17500.00", "16000.00"])  # several lines on one day
    assert q["lists"]["E3"] == [1, 2] and q["lists"]["E1"] == [1] and q["stop"] == [False, True, True, True, True]
    q = lists_of(["28473.94", "25626.55", "25626.54", "25626.56", "25626.55"])  # V6 $0.004 boundary, E1 not in E2
    assert q["ev4"] == [False, True, True, False, True], q["ev4"]
    assert q["lists"]["E1"] == [2] and q["lists"]["E2"] == [1, 4] and 2 not in q["lists"]["E2"]
    assert anchor_kind(q, 1) == "v6_band" and anchor_kind(q, 4) == "re_descent"
    q = lists_of(["30000.00", "26999.00", "28000.00", "26500.00"])
    assert anchor_kind(q, 1) == "first_touch" and anchor_kind(q, 3) == "re_descent"
    groups["ii"] = "ok"

    # (iii) sliced = rebuilt (random 50 sessions, P1 and MU, with E2 and V0 lists) and _sample_std bytes
    rnd = random.Random(20261018)
    lists = {v: [sox_s["days"][k] for k in px["lists"][v]] for v in ("V0", "E2")}
    st = first_eval(sox_s)
    for t in rnd.sample(range(st, len(sox_s["days"])), 50):
        days = sox_s["days"][:t + 1]
        full_s = series_on(sox, days)
        for v, lst in lists.items():
            kw = dict(evaluation_session=days[-1], ev3_user_dates=[], thesis_damage=[], candidate_symbol=None,
                      research_sessions=None)
            full = RULES.rrec1(benchmark=full_s, candidate=None, ev4_sessions=[d for d in lst if d <= days[-1]], **kw)
            vb = view(sox_s, t)
            cut = RULES.rrec1(benchmark=vb, candidate=None, ev4_sessions=[d for d in vb["days"] if d in set(lst)], **kw)
            assert json.dumps(full, sort_keys=True, default=str) == json.dumps(cut, sort_keys=True, default=str), (v, t)
    soxx_days = sorted(soxx)
    spx = build_proxy(series_on(soxx, soxx_days)["close"], L_MAIN)
    cb = load_kiwoom("MU")
    days_mu = sorted(set(soxx) & set(cb))
    bench, cand = series_on(soxx, days_mu), series_on(cb, days_mu)
    mu_list = move_to_common([soxx_days[k] for k in spx["lists"]["E2"]], days_mu)
    st = first_eval(bench, cand)
    for t in rnd.sample(range(st, len(days_mu)), 50):
        dd = days_mu[:t + 1]
        kw = dict(evaluation_session=dd[-1], ev3_user_dates=[], thesis_damage=[], candidate_symbol="MU",
                  research_sessions=None)
        full = RULES.rrec1(benchmark=series_on(soxx, dd), candidate=series_on(cb, dd),
                           ev4_sessions=[d for d in mu_list if d <= dd[-1]], **kw)
        vb = view(bench, t)
        cut = RULES.rrec1(benchmark=vb, candidate=view(cand, t),
                          ev4_sessions=[d for d in vb["days"] if d in set(mu_list)], **kw)
        assert json.dumps(full, sort_keys=True, default=str) == json.dumps(cut, sort_keys=True, default=str), ("MU", t)
    groups["iii"] = {"sessions": 100, "std_src_bytes_match": True}

    # (iv) anchors, stop, buy feasibility, pairs, cash 0, cost, quantiles, P2 move
    n = 400
    price = {"close": [100.0 + (i % 7) for i in range(n)], "low": [95.0 for _ in range(n)]}
    stop = [False] * n
    allowed = [False] * n
    a = 10
    allowed[a + 119] = True                     # first allowed at a+119 -> f = a+120 bought
    u, f, s = pick(allowed, stop, a, n)
    assert (u, f, s) == (a + 119, a + 120, "bought")
    m = arm_metrics(price, a, f)
    assert abs(m["Q120"] - (1 / COST - 1)) < 1e-15            # f = a+120: cost only
    allowed[a + 119] = False
    allowed[a + 120] = True                     # first allowed at a+120 -> cash
    assert pick(allowed, stop, a, n)[2] == "cash" and arm_metrics(price, a, None)["Q120"] == 0.0
    allowed = [False] * n
    allowed[a + 3] = True
    stop[a + 3] = True                          # stop on the u day -> not bought
    assert pick(allowed, stop, a, n)[2] == "stopped"
    assert pick(allowed, stop, a, n, use_stop=False)[2] == "bought"
    allowed[a + 8] = True
    assert pick(allowed, stop, a, n, skip_stopped=True)[:2] == (a + 8, a + 9)
    assert fixed(stop, a + 3, 1, n)[2] == "stopped"       # X1' on an a day with stop
    q = build_proxy([], 1.0, totals_override=[Decimal(x) for x in
                                                ["30000.00", "26000.00", "23999.99", "29000.00", "31000.00", "27000.00"]])
    assert q["stop"] == [False, False, True, True, False, False] and q["l2first"] == {0: 2}
    m = arm_metrics(price, n - 100, n - 60)      # f+60 = n is outside the data; a+120 too
    assert m["R60"] is None and m["MAE60"] is None and m["Q120"] is None and m["P"] is not None
    m = arm_metrics(price, n - 121, n - 61)      # f+60 = n-1 and a+120 = n-1 are inside
    assert m["R60"] is not None and m["Q120"] is not None and m["Q250"] is None
    m = arm_metrics(price, 0, 1)
    assert m["R60"] == price["close"][61] / (price["close"][1] * COST) - 1
    assert m["MAE60"] == 95.0 / (price["close"][1] * COST) - 1
    assert pct10([0, 10]) == 1.0 and pct10(list(range(10))) == 0.9 and med([1, 2, 3, 4]) == 2.5
    assert half_up(2.5) == 3 and half_up(3.5) == 4
    assert move_to_common(["2020-01-04", "2020-01-06", "2020-01-09"], ["2020-01-03", "2020-01-06", "2020-01-07"]) == \
        ["2020-01-06"]
    recs = [{"stop_a": False, "arms": {"V0": {"Q120": 0.0, "R60": None, "MAE60": None, "f": None},
                                       "E1": {"Q120": 0.1, "R60": 0.2, "MAE60": -0.1, "f": 1},
                                       "X1p": {"Q120": 0.05, "R60": 0.1, "MAE60": -0.2, "f": 1}}},
            {"stop_a": True, "arms": {"V0": {"Q120": 0.0, "R60": None, "MAE60": None, "f": None},
                                      "E1": {"Q120": -0.5, "R60": -0.5, "MAE60": -0.6, "f": 1},
                                      "X1p": {"Q120": -0.5, "R60": -0.5, "MAE60": -0.6, "f": 1}}}]
    j = judge(recs, "E1")
    assert j["anchors"] == 1 and j["pairs"] == 1 and abs(j["d"] - 0.1) < 1e-15 and abs(j["b"] - 0.1) < 1e-15 \
        and abs(j["c0"] - 0.1) < 1e-15 and j["short"]
    groups["iv"] = "ok"
    print(json.dumps({"self_test": "ok", "groups": groups}, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    RULES, STD_SRC = load_rules()
    if args.self_test:
        self_test()
    if args.run:
        r = main_run(Path(args.out) if args.out else BT)
        print(json.dumps({"verdict": r["verdict"]["chosen"], "disposition": r["verdict"]["disposition"]}))
