#!/usr/bin/env python3
"""E1a 'shock-absorbing first share' replay on Nasdaq-100 1985-2010
(preregistration docs/claude/e1a-ndx-preregistration-2026-11-26.md).

Historical computation only: no order tool, no policy/state/journal write, no network.
Usage: python e1a_ndx_replay.py --repo <repo copy> --self-test | --run
--self-test = hashes of inputs/code + synthetic data only (no NDX status is computed; allowed before fixing).
--run       = sidecar check + real-data structural tests (prereg 6-2/6-3/6-4b-c) + one performance run.
V0 = production auto_core_rules.rrec1 (candidate=None); E1a = a source copy with two anchored edits (prereg 2).
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import inspect
import json
import math
import statistics
import sys
import types
from pathlib import Path

import numpy as np

REPO = Path(sys.argv[sys.argv.index("--repo") + 1]) if "--repo" in sys.argv else Path(".")
SCRIPTS = REPO / "manage-us-stock-strategy" / "scripts"
NDX = REPO / "stock-strategy-system" / "backtests" / "leverage_up_inputs_2026-10-01" / "NDX_yahoo_raw.csv"
DOCS = REPO / "docs" / "claude"
PREREG = DOCS / "e1a-ndx-preregistration-2026-11-26.md"
SIDECAR = DOCS / "e1a-ndx-preregistration-2026-11-26.sha256"
OUT_JSON = DOCS / "e1a-ndx-results.json"
HASHES = {
    NDX: "d6ea7409215429bbd220fb80218bc72ec5632ee260eaf583b3af0b4fb0367f39",
    SCRIPTS / "auto_core_rules.py": "ba979d234ea95644c6bb78456e8f500974060ab96c23f8dafe97281acaa4ea6a",
    SCRIPTS / "portfolio_exposure.py": "9a5360c58f55b18a36c906c011132588152e85cd20cce6bc768288a7a1b1fb09",
}
KEEP, COST, H, START, END, WINDOW = 130, 1.001, 60, 130, "2010-12-31", 60

# --- anchored source edits (prereg 2) -------------------------------------------------------------
DS1_DEF = ('    def ds1(i: int) -> bool | None:\n'
           '        return _any(_cmp(s["close"][i], "lt", l0), _cmp(s["close"][i], "lt", s["ema50"][i]))\n')
DS1_LOW = ('    def ds1_low(i: int) -> bool | None:\n'
           '        return _cmp(s["close"][i], "lt", l0)\n')
LOOP_OLD = ('    last_ds1 = e\n'
            '    ds1_seen = None\n'
            '    closed_at = None\n'
            '    current: dict[str, bool | None] = {}\n'
            '    for i in range(e + 1, t + 1):\n'
            '        flag = ds1(i)\n'
            '        if flag:\n'
            '            last_ds1, ds1_seen = i, s["days"][i]\n'
            '        current = gates(i, last_ds1)\n'
            '        if all(value is True for value in current.values()):\n'
            '            closed_at = s["days"][i]\n'
            '            break\n')


def loop_new(reset: str, keys: str) -> str:
    """reset = DS1 used for the RG3 count of the first-buy check; keys = gates required for the first buy."""
    return ('    last_ds1 = e\n'
            '    last_first = e\n'
            '    ds1_seen = None\n'
            '    closed_at = None\n'
            '    current: dict[str, bool | None] = {}\n'
            '    for i in range(e + 1, t + 1):\n'
            '        flag = ds1(i)\n'
            '        if flag:\n'
            '            last_ds1, ds1_seen = i, s["days"][i]\n'
            f'        if {reset}(i):\n'
            '            last_first = i\n'
            '        current = gates(i, last_ds1)\n'
            '        first = gates(i, last_first)\n'
            f'        if all(first[key] is True for key in {keys}):\n'
            '            closed_at = s["days"][i]\n'
            '            out["first_buy_open"] = True\n'
            '            break\n')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rules():
    src = (SCRIPTS / "portfolio_exposure.py").read_text(encoding="utf-8")
    fn = [n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == "_sample_std"][0]
    stub = types.ModuleType("portfolio_exposure")
    exec(compile("import math\nfrom decimal import Decimal\n" + ast.get_source_segment(src, fn), "pe_std", "exec"),
         stub.__dict__)
    sys.modules["portfolio_exposure"] = stub
    sys.path.insert(0, str(SCRIPTS))
    import auto_core_rules as rules  # noqa: E402
    return rules


RULES = load_rules()


def variant_fn(reset: str, keys: str, name: str):
    src = inspect.getsource(RULES.rrec1)
    assert src.count(DS1_DEF) == 1 and src.count(LOOP_OLD) == 1, "anchor lines not unique"
    src = src.replace(DS1_DEF, DS1_DEF + DS1_LOW).replace(LOOP_OLD, loop_new(reset, keys))
    src = src.replace("def rrec1(", f"def {name}(", 1)
    ns = dict(RULES.__dict__)
    exec(compile(src, name, "exec"), ns)
    return ns[name]


ALL4 = '("RG1", "RG2", "RG3", "RG4")'
FN = {"V0": RULES.rrec1,
      "V0copy": variant_fn("ds1", ALL4, "rrec1_v0copy"),                      # both edits reverted (6-2)
      "E1a": variant_fn("ds1_low", '("RG1", "RG3", "RG4")', "rrec1_e1a")}


def load(path: Path):
    out = {}
    for r in csv.DictReader(open(path, encoding="utf-8")):
        if r["date"] > END:
            continue
        out[r["date"]] = {k: float(r[k]) for k in ("open", "high", "low", "close", "volume")}
    return out


def build(bars):
    days = sorted(bars)
    s = RULES.build_series({"sessions": bars}, days, days[-1])
    assert s["days"] == days, "series not contiguous"
    return days, s


def view(s, t):
    lo = max(0, t - KEEP + 1)
    return {k: v[lo:t + 1] for k, v in s.items()}


def call(name, s, t):
    return FN[name](benchmark=view(s, t), candidate=None, evaluation_session=s["days"][t], ev3_user_dates=[],
                    thesis_damage=[], candidate_symbol=None, research_sessions=None)


def since_event(o, days, t):
    """Sessions from the last EV1/EV2 in the 60-session window to t; 60 when the window has none (prereg 2 T)."""
    ev = o.get("events") or []
    return t - days.index(ev[-1]["date"]) if ev else WINDOW


def kind(o, day):
    if o.get("closed_at") == day:
        return "first_buy" if o.get("first_buy_open") else (
            "open" if all(v == "ok" for v in o["rg"].values()) else "decay")
    return "no_event_in_window" if not o.get("events") else "other"


def leg(s, f):
    """Own-window return and MAE for a buy at close[f]*COST held 60 sessions (prereg 4)."""
    p = s["close"][f] * COST
    return s["close"][f + H] / p - 1, min(s["low"][f + 1:f + H + 1]) / p - 1


def first(allowed, t0, n):
    return next((k for k in range(t0, n) if allowed(k)), None)


def episodes(days, s, st):
    n = len(days)
    ok = lambda v: (lambda k: st[v][k]["status"] == "ok")
    raw, censored = [], 0
    for t in range(START + 1, n):
        if not (st["V0"][t - 1]["status"] == "ok" and st["V0"][t]["status"] != "ok"):
            continue
        if not all(k >= 0 and s["sigma60"][k] is not None for k in range(t - 59, t + 1)):
            continue
        uE = first(lambda k: ok("V0")(k) or ok("E1a")(k), t, n)
        u0 = first(ok("V0"), t, n)
        if uE is None or uE + 1 + H >= n or (u0 is not None and u0 + 1 + H >= n):
            censored += 1
            continue
        raw.append({"t": t, "uE": uE, "u0": u0, "wait": since_event(st["E1a"][uE], days, uE)})
    return raw, censored


def finish(days, s, st, raw):
    n = len(raw)
    half = n // 2
    halves = [raw[:half], raw[half:]]
    N = [math.ceil(statistics.median([e["wait"] for e in h])) if h else None for h in halves]
    eps = []
    for hi, h in enumerate(halves):
        Nx = N[1 - hi]  # cross-fitted (prereg 2 T): never the own half
        for e in h:
            t, uE, u0 = e["t"], e["uE"], e["u0"]
            uT = None if Nx is None else first(
                lambda k: st["V0"][k]["status"] == "ok" or since_event(st["V0"][k], days, k) >= Nx, t, len(days))
            ep = {"t0": days[t], "half": hi, "N_used": Nx,
                  "u": {"V0": days[u0] if u0 is not None else None, "E1a": days[uE],
                        "T": days[uT] if uT is not None else None},
                  "kind": {"V0": kind(st["V0"][u0], days[u0]) if u0 is not None else None,
                           "E1a": ("same_day_as_V0" if u0 == uE else kind(st["E1a"][uE], days[uE]))}}
            fE = uE + 1
            ep["E1a"] = dict(zip(("R", "MAE"), leg(s, fE)), price=s["close"][fE] * COST)
            if u0 is None:
                ep["V0"] = {"R": 0.0, "MAE": 0.0, "price": None, "cash": True}
            else:
                ep["V0"] = dict(zip(("R", "MAE"), leg(s, u0 + 1)), price=s["close"][u0 + 1] * COST, cash=False)
            ep["T"] = (dict(zip(("R", "MAE"), leg(s, uT + 1))) if uT is not None and uT + 1 + H < len(days)
                       else None)
            fX = t + 1
            ep["X1p"] = dict(zip(("R", "MAE"), leg(s, fX))) if fX + H < len(days) else None
            ep["binding"] = uE != u0
            ep["d"] = None if u0 is None else u0 - uE
            ep["g"] = None if u0 is None else ep["E1a"]["price"] / ep["V0"]["price"] - 1
            ep["dR"] = ep["E1a"]["R"] - ep["V0"]["R"]
            # report only: common window [fE, fE+60], V0 cash until it buys inside the window
            end = fE + H
            if u0 is not None and u0 + 1 < end:
                p0 = s["close"][u0 + 1] * COST
                ep["common_V0"] = {"R": s["close"][end] / p0 - 1, "MAE": min(s["low"][u0 + 2:end + 1] or [p0]) / p0 - 1}
            else:
                ep["common_V0"] = {"R": 0.0, "MAE": 0.0}
            eps.append(ep)
    return eps, N


def p10(x):
    return float(np.percentile(x, 10)) if x else None


def judge(eps):
    B = [e for e in eps if e["binding"]]
    Bb = [e for e in B if e["g"] is not None]
    r = {"episodes": len(eps), "binding": len(B), "binding_bought": len(Bb)}
    if B:
        mE, m0 = [e["E1a"]["MAE"] for e in B], [e["V0"]["MAE"] for e in B]
        r.update(dR_median=statistics.median([e["dR"] for e in B]),
                 tail_diff=p10(mE) - p10(m0), worst_diff=min(mE) - min(m0))
        r["halves"] = {h: {"n": len(hb), "dR_median": statistics.median(hb) if hb else None}
                       for h, hb in ((h, [e["dR"] for e in B if e["half"] == h]) for h in (0, 1))}
    if Bb:
        g = [e["g"] for e in Bb]
        r.update(g_median=statistics.median(g), g_p90=float(np.percentile(g, 90)), g_max=max(g))
    T = [e for e in eps if e["T"] is not None]
    if T:
        r.update(T_n=len(T), E_R_median=statistics.median([e["E1a"]["R"] for e in T]),
                 T_R_median=statistics.median([e["T"]["R"] for e in T]),
                 E_tail=p10([e["E1a"]["MAE"] for e in T]), T_tail=p10([e["T"]["MAE"] for e in T]))
    r["all_dR_mean"] = statistics.fmean([e["dR"] for e in eps]) if eps else None
    r["all_dR_median"] = statistics.median([e["dR"] for e in eps]) if eps else None
    return r


def verdict(r):
    if r["episodes"] < 30 or r["binding"] < 15:
        return "INCONCLUSIVE", {"reason": "sample short"}
    c = {"2_g_median_le_-2pct": r.get("g_median") is not None and r["g_median"] <= -0.02,
         "3_dR_median_ge_1pp": r["dR_median"] >= 0.01,
         "4a_tail_diff_ge_0": r["tail_diff"] >= 0.0,
         "4b_worst_diff_ge_-3pp": r["worst_diff"] >= -0.03,
         "5_beats_T": r.get("T_n", 0) > 0 and r["E_R_median"] > r["T_R_median"] and r["E_tail"] >= r["T_tail"],
         "6_halves_positive": all(h["n"] >= 5 and h["dR_median"] is not None and h["dR_median"] > 0
                                  for h in r["halves"].values())}
    return ("CANDIDATE" if all(c.values()) else "BELOW_STANDARD"), c


def check_hashes():
    side = SIDECAR.read_text(encoding="utf-8").split()
    assert side[0] == sha(PREREG), "preregistration hash mismatch"
    assert side[side.index("runner") + 1] == sha(Path(__file__)), "runner hash mismatch"


def synth_series(closes, lows=None):
    import datetime as dt
    d0 = dt.date(2001, 1, 1)
    days = [(d0 + dt.timedelta(i)).isoformat() for i in range(len(closes))]
    bars = {d: {"open": c, "close": c, "high": c * 1.002, "low": (lows[i] if lows else c * 0.998), "volume": 1.0}
            for i, (d, c) in enumerate(zip(days, closes))}
    return days, RULES.build_series({"sessions": bars}, days, days[-1])


def synthetic():
    """Prereg 6-4 a: index below EMA50 but RG1/RG3/RG4 met -> V0 blocked, E1a open (first_buy)."""
    w = 0.012
    closes = [100.0]
    for i in range(1, 120):                                       # rise with +-1.2% wiggle (sigma60 ~1.2%)
        closes.append(closes[-1] * (1.003 + (w if i % 2 else -w)))
    for i in range(30):                                           # slow fade below EMA50, no EV2
        closes.append(closes[-1] * (0.9985 + (w if i % 2 else -w)))
    closes.append(closes[-1] * 0.95)                              # EV1 event
    for k in range(25):                                           # calm climb, still under EMA50 at first
        closes.append(closes[-1] * (1.002 + (0.004 if k % 2 else -0.004)))
    days, s = synth_series(closes)
    hit = False
    for t in range(148, len(days)):
        v0, e1 = call("V0", s, t), call("E1a", s, t)
        if (s["close"][t] < s["ema50"][t] and e1["status"] == "ok" and e1.get("first_buy_open")
                and e1.get("closed_at") == days[t]):
            assert v0["status"] != "ok", "synthetic a: V0 should be blocked under EMA50"
            hit = True
    assert hit, "synthetic a: E1a never opened below EMA50"
    # V0copy must equal V0 here too
    for t in range(140, len(days)):
        x, y = call("V0", s, t), call("V0copy", s, t)
        assert (x["status"], x["open"], x["rg"], x.get("closed_at")) == (y["status"], y["open"], y["rg"], y.get("closed_at"))
    synthetic_bc()
    return True


def synthetic_bc():
    """Prereg 6-4 b, c on a fixed-seed random series (independent review 2026-11-26, review-scripts/patch_test.py):
    structural() passes for E1a with at least one RG2-ok session opened only by E1a, and FAILS for a wrong copy
    whose ds1 (line 926) is replaced wholesale (that copy would also speed up the time decay)."""
    import random
    rnd = random.Random(20261126)
    closes, lows = [100.0], [99.5]
    for i in range(1, 1500):
        r = rnd.gauss(0.0004, 0.012) - (rnd.uniform(0.03, 0.08) if rnd.random() < 0.012 else 0.0)
        closes.append(closes[-1] * (1 + r))
        lows.append(min(closes[-2], closes[-1]) * (1 - abs(rnd.gauss(0, 0.006))))
    days, s = synth_series(closes, lows)
    bad_def = ('    def ds1(i: int) -> bool | None:\n'
               '        return _cmp(s["close"][i], "lt", l0)\n')
    src = inspect.getsource(RULES.rrec1).replace(DS1_DEF, bad_def).replace(
        LOOP_OLD, loop_new("ds1", '("RG1", "RG3", "RG4")')).replace("def rrec1(", "def rrec1_bad(", 1)
    ns = dict(RULES.__dict__)
    exec(compile(src, "rrec1_bad", "exec"), ns)

    def states(e1):
        keep = FN["E1a"]
        FN["E1a"] = e1
        try:
            return {v: {t: call(v, s, t) for t in range(START, len(days))} for v in ("V0", "V0copy", "E1a")}
        finally:
            FN["E1a"] = keep
    info = structural(days, s, states(FN["E1a"]))
    assert info["e1a_only_with_rg2_ok"] > 0, "synthetic b: no RG2-ok session opened only by E1a"
    try:
        structural(days, s, states(ns["rrec1_bad"]))
    except AssertionError:
        return info
    raise AssertionError("synthetic c: a copy with ds1 replaced wholesale was not caught")


def structural(days, s, st):
    """Prereg 6-2, 6-3, 6-4 b/c on the real series (run only)."""
    reset_hits = 0
    for t in st["V0"]:
        x, y, e = st["V0"][t], st["V0copy"][t], st["E1a"][t]
        assert (x["status"], x["open"], x["rg"], x.get("closed_at")) == (
            y["status"], y["open"], y["rg"], y.get("closed_at")), "V0copy != V0 " + days[t]
        if x["status"] == "ok":
            assert e["status"] == "ok", "V0 allowed but E1a copy blocked " + days[t]
        if e["status"] == "ok" and x["status"] != "ok":
            # 6-4 c: an E1a-only opening must come from the first-buy check, never from a faster time decay
            assert e.get("first_buy_open"), "E1a-only opening not from first-buy check " + days[t]
            if x["rg"].get("RG2") == "ok":
                reset_hits += 1  # 6-4 b: same RG2, so the EMA50 DS1 reset made the difference
    return {"e1a_only_with_rg2_ok": reset_hits}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test", action="store_true")
    g.add_argument("--run", action="store_true")
    a = ap.parse_args()
    for p, h in HASHES.items():
        assert sha(p) == h, f"input hash mismatch {p.name}"
    synthetic()
    print("self-test ok (hashes + synthetic)")
    if a.self_test:
        return
    check_hashes()
    assert not OUT_JSON.exists(), "results already exist (one run only)"
    days, s = build(load(NDX))
    st = {v: {t: call(v, s, t) for t in range(START, len(days))} for v in ("V0", "V0copy", "E1a")}
    info = structural(days, s, st)
    raw, censored = episodes(days, s, st)
    eps, N = finish(days, s, st, raw)
    r = judge(eps)
    v, crit = verdict(r) if r.get("binding") else ("INCONCLUSIVE", {"reason": "no binding"})
    out = {"preregistration_sha256": sha(PREREG), "runner_sha256": sha(Path(__file__)),
           "inputs": {p.name: h for p, h in HASHES.items()}, "days": [days[0], days[-1], len(days)],
           "limitation": "NDX file already used in R-REC1-X/fx5a 2026-10-09 (other question); grade cap C, one step lower",
           "verdict_E1a": v, "criteria": crit, "summary": r, "N_cross": N, "right_censored": censored,
           "structural": info, "episodes": eps}
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("verdict_E1a", "criteria", "summary", "N_cross", "right_censored",
                                          "structural")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
