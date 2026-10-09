#!/usr/bin/env python3
"""R-REC1 recovery-gate replay (SOXX). Read-only historical computation.

Pre-registration: docs/claude/r-rec1-gate-preregistration-2026-10-09.md (hash-locked before any run).
Section numbers below (S2..S9) refer to that document.

Interpretations fixed before the run (I1..I10):
 I1  All prices are adjusted by f = adjclose/close (close and low alike); signals, returns, MAE share one basis (S2).
 I2  Event day evaluation precedes gate evaluation: on an event day anchors refresh and no gate is evaluated (S4).
 I3  EV2 is read literally: every session where EV2 is true is an event day (state reading); the crossing-only
     reading is sensitivity 5 (S7).
 I4  RG3 counter = consecutive sessions ending today with close > C0 and not DS1; a DS1 session or a close <= C0 resets it.
 I5  RG3 new-low test: min(low over t_e+1..t) >= L0 (L0 fixed at the latest event day), includes today.
 I6  Gate open takes precedence over time-decay on the same session (S4).
 I7  Time-decay: t - max(last event day, last DS1 day) >= 20 and RG2 true.
 I8  Cost: 10bp applied once at the buy fill: effective price = adjclose_fill * 1.001; no exit cost (S5).
 I9  MAE_h = min(low[f+1..f+h]) / effective_price - 1 exactly as written (no clamp at zero); complete only if f+h < n.
 I10 Pair sample = opened episodes whose G and X1 R60/MAE60 are all complete.
"""
import argparse, hashlib, json, sys, csv
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "stock-strategy-system/backtests/soxl_signal_inputs_2026-10-01/SOXX_combined.csv"
PREREG = ROOT / "docs/claude/r-rec1-gate-preregistration-2026-10-09.md"
PREREG_SHA = ROOT / "docs/claude/r-rec1-gate-preregistration-2026-10-09.sha256"
DATA_SHA_EXPECTED = "00e8cdd030c38748eac563fc025222a16b2ada9e4cc09be3f6d7f28e224535f6"
OUT_JSON = ROOT / "stock-strategy-system/backtests/r_rec1_gate_replay_2026-10-09_results.json"
OUT_CSV = ROOT / "stock-strategy-system/backtests/r_rec1_gate_replay_2026-10-09_episodes.csv"
START_EVAL = "2011-01-03"
COST = 0.001


def sha256_file(p, normalize=False):
    b = Path(p).read_bytes()
    if normalize:
        b = b.replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()


def build_ind(df):
    f = df["adjclose"] / df["close"]
    c = df["adjclose"].astype(float)
    lo = (df["low"] * f).astype(float)
    r = c.pct_change()
    ema = c.ewm(span=50, adjust=False).mean()
    ema[: 49] = np.nan
    return dict(
        dates=df.index.to_numpy(),
        c=c.to_numpy(), lo=lo.to_numpy(), r=r.to_numpy(),
        sig60=r.rolling(60).std().to_numpy(), sig5=r.rolling(5).std().to_numpy(),
        ema50=ema.to_numpy(), sma200=c.rolling(200).mean().to_numpy(),
        h20=c.rolling(20).max().to_numpy(),
    )


def simulate(ind, s0, ev2_mode="state", rebase=False, use_sma200=False):
    c, lo, r = ind["c"], ind["lo"], ind["r"]
    s60, s5, ema, sma, h20 = ind["sig60"], ind["sig5"], ind["ema50"], ind["sma200"], ind["h20"]
    n = len(c)
    ev2 = np.zeros(n, dtype=bool)
    for t in range(n):
        if not (np.isnan(s60[t]) or np.isnan(h20[t])):
            ev2[t] = c[t] <= h20[t] * (1 - 3 * s60[t])
    eps = []
    opened = False
    for t in range(s0, n):
        ev1 = (not np.isnan(s60[t])) and (r[t] <= -2.0 * s60[t])
        e2 = ev2[t] if ev2_mode == "state" else (ev2[t] and not ev2[t - 1])
        is_event = bool(ev1 or e2)
        if not opened:
            if is_event:
                opened = True
                ep = dict(t0=t, te=t, status=None, gate_day=None, fill=None, decay_day=None, refreshes=0)
                C0, L0, minlow, cnt, last_reset = c[t], lo[t], np.inf, 0, t
            continue
        if is_event:
            ep["te"] = t; ep["refreshes"] += 1
            C0, L0, minlow, cnt, last_reset = c[t], lo[t], np.inf, 0, t
            continue
        minlow = min(minlow, lo[t])
        ds1 = (c[t] < L0) or (c[t] < ema[t])
        if ds1:
            cnt = 0; last_reset = t
        else:
            cnt = cnt + 1 if c[t] > C0 else 0
        if rebase and c[t] < L0:
            L0, C0, minlow = lo[t], c[t], np.inf
        rg1 = (t - ep["te"]) >= 2
        rg2 = c[t] >= ema[t]
        if use_sma200:
            rg2 = bool(rg2 and (not np.isnan(sma[t])) and c[t] >= sma[t])
        rg3 = (cnt >= 2) and (minlow >= L0)
        rg4 = (abs(r[t]) <= 2.0 * s60[t]) and (s5[t] <= 1.5 * s60[t])
        if rg1 and rg2 and rg3 and rg4:
            ep["gate_day"] = t
            if t + 1 < n:
                ep["status"] = "opened"; ep["fill"] = t + 1
            else:
                ep["status"] = "opened_nofill"
            eps.append(ep); opened = False
        elif (t - last_reset) >= 20 and rg2:
            ep["status"] = "decay"; ep["decay_day"] = t
            eps.append(ep); opened = False
    if opened:
        ep["status"] = "censored"; eps.append(ep)
    return eps


def metr(ind, f):
    c, lo = ind["c"], ind["lo"]
    n = len(c)
    P = c[f] * (1 + COST)
    o = {}
    for h in (20, 60):
        if f + h < n:
            o[f"R{h}"] = float(c[f + h] / P - 1)
            o[f"MAE{h}"] = float(lo[f + 1: f + h + 1].min() / P - 1)
        else:
            o[f"R{h}"] = None; o[f"MAE{h}"] = None
    return o


def summ(x):
    x = [v for v in x if v is not None]
    if not x:
        return dict(n=0)
    a = np.array(x)
    return dict(n=len(a), median=float(np.median(a)), mean=float(a.mean()), p25=float(np.percentile(a, 25)),
                p75=float(np.percentile(a, 75)), min=float(a.min()), max=float(a.max()))


def pair_eval(ind, eps, x1_mode="ideal", pick=None):
    G, X = [], []
    for ep in eps:
        if ep["status"] != "opened":
            continue
        if pick is not None and not pick(ep):
            continue
        fx = ep["t0"] if x1_mode == "ideal" else ep["t0"] + 1
        if fx >= len(ind["c"]):
            continue
        g, x = metr(ind, ep["fill"]), metr(ind, fx)
        if None in (g["R60"], g["MAE60"], x["R60"], x["MAE60"]):
            continue
        G.append(g); X.append(x)
    N = len(G)
    if N == 0:
        return dict(N=0, verdict="표본 없음")
    mg, mx = np.median([g["MAE60"] for g in G]), np.median([x["MAE60"] for x in X])
    rg, rx = np.median([g["R60"] for g in G]), np.median([x["R60"] for x in X])
    a, b = mg - mx, rg - rx
    pa, pb = a >= 0.02, b >= -0.03
    verdict = "표본 부족 — 보류" if N < 15 else ("채택 후보" if (pa and pb) else "미달")
    return dict(N=N, MAE60_G_med=float(mg), MAE60_X1_med=float(mx), diff_a=float(a), pass_a=bool(pa),
                R60_G_med=float(rg), R60_X1_med=float(rx), diff_b=float(b), pass_b=bool(pb), verdict=verdict,
                MAE60_G_pos=int(sum(1 for g in G if g["MAE60"] > 0)), MAE60_X1_pos=int(sum(1 for x in X if x["MAE60"] > 0)))


def status_counts(eps):
    d = {}
    for e in eps:
        d[e["status"]] = d.get(e["status"], 0) + 1
    closed = d.get("opened", 0) + d.get("opened_nofill", 0) + d.get("decay", 0)
    d["closed"] = closed
    d["never_open_ratio"] = (d.get("decay", 0) / closed) if closed else None
    return d


def full_report(ind, eps):
    n = len(ind["c"])
    rep = {"status": status_counts(eps), "pair": pair_eval(ind, eps)}
    rep["pair_x1_next_session"] = pair_eval(ind, eps, "next")
    # time to fill, missed rebound
    sess, missed = [], []
    for e in eps:
        if e["status"] == "opened":
            sess.append(e["fill"] - e["t0"])
            missed.append(float(ind["c"][e["fill"]] / ind["c"][e["t0"]] - 1))
    rep["sessions_t0_to_fill"] = summ(sess)
    rep["missed_rebound_G_over_X1"] = summ(missed)
    # never-opened episodes: X1 outcomes
    ne = []
    for e in eps:
        if e["status"] == "decay":
            ne.append(metr(ind, e["t0"]))
    rep["never_opened_X1_R60"] = summ([m["R60"] for m in ne])
    rep["never_opened_X1_MAE60"] = summ([m["MAE60"] for m in ne])
    # combined view over closed episodes (opened with G complete, decay) and X1 complete
    gc_r, gc_m, xc_r, xc_m = [], [], [], []
    for e in eps:
        if e["status"] not in ("opened", "decay"):
            continue
        x = metr(ind, e["t0"])
        if x["R60"] is None:
            continue
        if e["status"] == "opened":
            g = metr(ind, e["fill"])
            if g["R60"] is None:
                continue
            gc_r.append(g["R60"]); gc_m.append(g["MAE60"])
        else:
            gc_r.append(0.0); gc_m.append(0.0)
        xc_r.append(x["R60"]); xc_m.append(x["MAE60"])
    rep["combined_G_R60"] = summ(gc_r); rep["combined_X1_R60"] = summ(xc_r)
    rep["combined_G_MAE60"] = summ(gc_m); rep["combined_X1_MAE60"] = summ(xc_m)
    rep["opened_X1_R60"] = summ([metr(ind, e["t0"])["R60"] for e in eps if e["status"] == "opened"])
    rep["opened_G_R60"] = summ([metr(ind, e["fill"])["R60"] for e in eps if e["status"] == "opened"])
    # T20 reporting
    rep["opened_G_R20"] = summ([metr(ind, e["fill"])["R20"] for e in eps if e["status"] == "opened"])
    rep["opened_X1_R20"] = summ([metr(ind, e["t0"])["R20"] for e in eps if e["status"] == "opened"])
    rep["opened_G_MAE20"] = summ([metr(ind, e["fill"])["MAE20"] for e in eps if e["status"] == "opened"])
    rep["opened_X1_MAE20"] = summ([metr(ind, e["t0"])["MAE20"] for e in eps if e["status"] == "opened"])
    rep["refreshes_per_episode"] = summ([e["refreshes"] for e in eps])
    return rep


# ---------------------------------------------------------------- self-test
def _mk(c, lo=None, ema=None, s60=0.02, s5=0.005, h20=0.0):
    c = np.array(c, float); n = len(c)
    lo = np.array(lo if lo is not None else c * 0.995, float)
    r = np.full(n, np.nan); r[1:] = c[1:] / c[:-1] - 1
    return dict(dates=np.arange(n), c=c, lo=lo, r=r, sig60=np.full(n, s60), sig5=np.full(n, s5),
                ema50=np.full(n, 80.0) if ema is None else np.array(ema, float), sma200=np.full(n, 50.0),
                h20=np.full(n, h20, float))


class _T:
    def __init__(self): self.k = 0; self.fail = []
    def ok(self, cond, name):
        self.k += 1
        if not cond: self.fail.append(name)


def self_test():
    T = _T()
    # base: flat 100 up to day 9, shock day 10 close 94 (-6% <= -4% => EV1), then recovery
    def base(extra, lows=None, ema=None, n_flat=10):
        c = [100.0] * n_flat + [94.0] + extra
        return _mk(c, lo=lows, ema=ema)
    # a: closes above C0=94 on days 11,12 => gate on day 12 (t-te=2), fill 13
    ind = base([95.0, 95.5, 96.0, 96.0, 96.0])
    ep = simulate(ind, 5)
    T.ok(len(ep) == 1 and ep[0]["t0"] == 10 and ep[0]["status"] == "opened" and ep[0]["gate_day"] == 12 and ep[0]["fill"] == 13, "a gate day 12")
    # b: day 11 close <= C0 (but >= L0) resets the counter; days 13,14 above C0 -> gate day 14? counter: d12 95 ->1, d13 -> 2
    ex = [93.5, 95.0, 95.5, 96.0, 96.0, 96.0]
    lw = [99.5] * 10 + [92.0] + [x - 0.5 for x in ex]
    ind = base(ex, lows=lw)
    ep = simulate(ind, 5)
    T.ok(ep[0]["status"] == "opened" and ep[0]["gate_day"] == 13, "b close<=C0 resets counter -> gate day 13")
    # b2: DS1 via EMA50 resets the counter: ema above close on day 12 only
    ex = [95.0, 95.5, 96.0, 96.0, 96.0, 96.0]
    lw = [99.5] * 10 + [93.5] + [x - 0.2 for x in ex]
    em = [80.0] * 12 + [99.0] + [80.0] * 4
    ind = base(ex, lows=lw, ema=em)
    ep = simulate(ind, 5)
    T.ok(ep[0]["status"] == "opened" and ep[0]["gate_day"] == 14, "b2 DS1 (ema50) resets counter -> gate day 14 (days 13,14)")
    # c: new low below L0 intraday (close above L0) blocks gate -> decay
    lows = [99.5] * 10 + [93.5] + [90.0, 94.5, 95.0, 95.0, 95.0]
    ind = base([95.0, 95.0, 95.5, 96.0, 96.0], lows=lows)
    ep = simulate(ind, 5)
    T.ok(ep[0]["status"] != "opened", "c intraday new low blocks gate")
    # d: stays <= C0 but >= L0 and above ema50 for 25 days -> decay at te+20
    ex = [93.8] * 25
    lw = [99.5] * 10 + [93.5] + [x - 0.2 for x in ex]
    ind = base(ex, lows=lw)
    ep = simulate(ind, 5)
    T.ok(ep[0]["status"] == "decay" and ep[0]["decay_day"] == 30, "d decay at te+20")
    # e: precedence: <=C0 until te+18, above on te+19, te+20 -> both gate and decay on te+20 -> opened
    ex = [93.8] * 18 + [95.0, 95.0, 95.0]
    lw = [99.5] * 10 + [93.5] + [x - 0.2 for x in ex]
    ind = base(ex, lows=lw)
    ep = simulate(ind, 5)
    T.ok(ep[0]["status"] == "opened" and ep[0]["gate_day"] == 30, "e gate precedence over decay")
    # f: censored
    ind = base([93.0] * 3)
    ep = simulate(ind, 5)
    T.ok(ep[0]["status"] == "censored", "f censored")
    # g: refresh on second event day resets anchors (day 12 another -6%)
    ind = base([95.0, 89.3, 90.0, 90.5, 91.0, 91.0])
    ep = simulate(ind, 5)
    T.ok(ep[0]["refreshes"] >= 1 and ep[0]["te"] == 12, "g refresh anchors")
    # h: RG2 false (close below ema50) -> no open
    ind = base([95.0, 95.5, 96.0, 96.0, 96.0], ema=[200.0] * 16)
    ep = simulate(ind, 5)
    T.ok(ep[0]["status"] != "opened", "h rg2 blocks")
    # i: RG4 big-move day blocks (sig5 high)
    ind = base([95.0, 95.5, 96.0, 96.0, 96.0]); ind["sig5"][:] = 0.05
    ep = simulate(ind, 5)
    T.ok(ep[0]["status"] != "opened", "i rg4 blocks")
    # j: EV2 state vs crossing: price stays 7% below 20d high for 5 days
    c = [100.0] * 10 + [93.0] * 6
    ind = _mk(c, h20=100.0)
    e_state = simulate(ind, 5, "state"); e_cross = simulate(ind, 5, "cross")
    T.ok(e_state[0]["refreshes"] == 5 and e_cross[0]["refreshes"] == 0, "j ev2 state vs crossing")
    # k: metrics and cost
    cc = [100.0] * 5 + list(np.linspace(100, 130, 61))
    ind = _mk(cc, lo=[x * 0.99 for x in cc])
    m = metr(ind, 5)
    P = 100.0 * 1.001
    T.ok(abs(m["R60"] - (cc[65] / P - 1)) < 1e-12 and abs(m["MAE60"] - (min(ind["lo"][6:66]) / P - 1)) < 1e-12, "k R60/MAE60 formula + cost")
    T.ok(metr(ind, 10)["R60"] is None, "k incomplete window -> None")
    # l: lookahead: prefix simulation equals full simulation for closed episodes
    rng = np.random.default_rng(7)
    rr = rng.normal(0.0005, 0.02, 1500); rr[[300, 301, 700, 1100]] = [-0.09, -0.05, -0.08, -0.1]
    px = 100 * np.cumprod(1 + rr)
    df = pd.DataFrame({"adjclose": px, "close": px, "low": px * (1 - 0.01 * rng.random(1500))},
                      index=pd.bdate_range("2008-01-01", periods=1500))
    full = build_ind(df); n1 = 1200
    pre = build_ind(df.iloc[:n1])
    for key in ("sig60", "sig5", "ema50", "sma200", "h20"):
        a, b = full[key][:n1], pre[key]
        T.ok(np.allclose(a, b, equal_nan=True), f"l indicator {key} no lookahead")
    ef, ep_ = simulate(full, 260), simulate(pre, 260)
    cl_f = [(e["t0"], e["status"], e["gate_day"], e["decay_day"]) for e in ef
            if e["status"] in ("opened", "decay") and (e["gate_day"] or e["decay_day"]) < n1 - 1]
    cl_p = [(e["t0"], e["status"], e["gate_day"], e["decay_day"]) for e in ep_
            if e["status"] in ("opened", "decay") and (e["gate_day"] or e["decay_day"]) < n1 - 1]
    T.ok(cl_f == cl_p and len(cl_f) > 0, "l prefix invariance of closed episodes")
    print(f"self-test: {T.k} checks, {len(T.fail)} failed")
    for f in T.fail: print("FAIL", f)
    return not T.fail


# ---------------------------------------------------------------- run
def run():
    # hash checks before any computation
    want = dict(l.split("=", 1) for l in PREREG_SHA.read_text().splitlines() if "=" in l)
    raw = sha256_file(PREREG); lf = sha256_file(PREREG, True)
    assert raw == want["raw_bytes_sha256"] and lf == want["lf_normalized_sha256"], "preregistration hash mismatch"
    dsha = sha256_file(DATA)
    assert dsha == DATA_SHA_EXPECTED, "input hash mismatch"
    assert DATA_SHA_EXPECTED in PREREG.read_text(encoding="utf-8"), "input hash not recorded in preregistration"
    df = pd.read_csv(DATA, parse_dates=["date"]).set_index("date")
    ind = build_ind(df)
    s0 = int(np.argmax(df.index >= pd.Timestamp(START_EVAL)))
    res = dict(meta=dict(prereg_raw_sha256=raw, input_sha256=dsha, script_sha256=sha256_file(__file__),
                         n_rows=len(df), first=str(df.index[0].date()), last=str(df.index[-1].date()),
                         eval_start=str(df.index[s0].date())))
    prim = simulate(ind, s0)
    res["primary"] = full_report(ind, prim)
    d0 = pd.Timestamp("2018-12-31")
    d = ind["dates"]
    res["sens4_first_half"] = pair_eval(ind, prim, pick=lambda e: pd.Timestamp(d[e["t0"]]) <= d0)
    res["sens4_second_half"] = pair_eval(ind, prim, pick=lambda e: pd.Timestamp(d[e["t0"]]) > d0)
    for key, kw in (("sens2_rebase", dict(rebase=True)), ("sens3_sma200", dict(use_sma200=True)),
                    ("sens5_ev2_crossing", dict(ev2_mode="cross"))):
        e = simulate(ind, s0, **kw)
        res[key] = dict(status=status_counts(e), pair=pair_eval(ind, e), pair_x1_next=pair_eval(ind, e, "next"),
                        report=full_report(ind, e))
    rows = []
    for e in prim:
        row = dict(t0=str(pd.Timestamp(d[e["t0"]]).date()), last_event=str(pd.Timestamp(d[e["te"]]).date()),
                   status=e["status"], refreshes=e["refreshes"],
                   gate_day=str(pd.Timestamp(d[e["gate_day"]]).date()) if e["gate_day"] is not None else "",
                   fill=str(pd.Timestamp(d[e["fill"]]).date()) if e["fill"] is not None else "",
                   decay_day=str(pd.Timestamp(d[e["decay_day"]]).date()) if e["decay_day"] is not None else "")
        x = metr(ind, e["t0"]); row.update({f"X1_{k}": x[k] for k in x})
        if e["fill"] is not None:
            g = metr(ind, e["fill"]); row.update({f"G_{k}": g[k] for k in g})
        rows.append(row)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        keys = sorted({k for r_ in rows for k in r_}, key=lambda k: (k not in ("t0", "last_event", "status"), k))
        w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
    OUT_JSON.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res["primary"]["status"], ensure_ascii=False))
    print(json.dumps(res["primary"]["pair"], ensure_ascii=False, indent=1))
    print("wrote", OUT_JSON.name, OUT_CSV.name)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true"); ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(0 if self_test() else 1)
    if a.run:
        run()
    else:
        ap.print_help()
