#!/usr/bin/env python3
"""fx-5b R-REC1 redesign replay (V0..V3, D1, D2, S1..S5). Read-only historical computation.

Pre-registration: docs/claude/fx5b-r-rec1-redesign-preregistration-2026-10-09.md (hash-locked 2026-10-09T16:47:05+09:00
before any computation). Interpretations J1..J21 are section 5 of that document; section numbers below refer to it.

J1: the first replay script r_rec1_gate_replay_2026-10-09.py is imported unchanged (importlib). Its run() is never
called (it would overwrite the first replay's outputs). V0 must reproduce the first replay results JSON exactly
before anything else is computed (section 7 step 3).
"""
import argparse, csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BT = ROOT / "stock-strategy-system/backtests"
PREREG = ROOT / "docs/claude/fx5b-r-rec1-redesign-preregistration-2026-10-09.md"
PREREG_SHA = ROOT / "docs/claude/fx5b-r-rec1-redesign-preregistration-2026-10-09.sha256"
ITEMS = ROOT / "docs/claude/fx5b-r-rec1-redesign-items-2026-10-09.md"
OLD = BT / "r_rec1_gate_replay_2026-10-09.py"
OLD_JSON = BT / "r_rec1_gate_replay_2026-10-09_results.json"
SOXX = BT / "soxl_signal_inputs_2026-10-01/SOXX_combined.csv"
QQQ = BT / "soxl_signal_inputs_2026-10-01/QQQ_combined.csv"
PWR = BT / "fx5b_inputs_2026-10-09/kiwoom_raw/PWR_kiwoom_usa06012_daily_adj1_20261009.json"
GRID = BT / "fx5b_inputs_2026-10-09/kiwoom_raw/GRID_kiwoom_usa06012_daily_adj1_20261009.json"
EXPECTED = {
    ITEMS: "aa2b373b5db71e1625982f63dccc8ee2d6f8ab6230d2dca95328a1e8a6cfb55a",
    OLD: "b3d27a1a90806061d32f84f9cee7d6563873a968a2d8a1835121d808d7a92bb9",
    OLD_JSON: "b124a7e1e3d5f03436c92fb36279b27bdfbf9b410bd9c2e566e7179238c5cecd",
    SOXX: "00e8cdd030c38748eac563fc025222a16b2ada9e4cc09be3f6d7f28e224535f6",
    QQQ: "644aabe79e8165bc382788f6fbe46b2e25898adc95cfe1cb224c13d03560df5e",
    PWR: "02d9c7d2b0b451581d5df10ea099134fd0a9dc5b82a112aaec32e273eecafc27",
    GRID: "538d94e6efba6e0114a98cffae7e65f9f8b0d7d7b7ca787a5fa79493bce8b50f",
}
OUT_JSON = BT / "fx5b_r_rec1_redesign_replay_2026-10-09_results.json"
OUT_CSV = BT / "fx5b_r_rec1_redesign_replay_2026-10-09_episodes.csv"
START_EVAL = "2011-01-03"
HALF_END = pd.Timestamp("2018-12-31")
COST = 0.001
VARIANTS = {"V0": dict(rg4="two", partial=False), "V1": dict(rg4="down", partial=False),
            "V2": dict(rg4="two", partial=True), "V3": dict(rg4="down", partial=True)}


def sha(p, lf=False):
    b = Path(p).read_bytes()
    return hashlib.sha256(b.replace(b"\r\n", b"\n") if lf else b).hexdigest()


def load_old():
    spec = importlib.util.spec_from_file_location("r_rec1_first_replay", OLD)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


OLDM = load_old()


# ------------------------------------------------------------------ market structure
def market_from_ind(ind):
    """Single-asset market (SOXX or QQQ): event source = benchmark = candidate."""
    return dict(dates=ind["dates"], n=len(ind["c"]),
                ev_r=ind["r"], ev_s60=ind["sig60"], ev_c=ind["c"], ev_h20=ind["h20"], ev5=None,
                b_c=ind["c"], b_lo=ind["lo"], b_r=ind["r"], b_s60=ind["sig60"], b_s5=ind["sig5"], b_ema=ind["ema50"],
                k_c=ind["c"], k_lo=ind["lo"], k_ema=ind["ema50"], k_rg2=False)


def kiwoom_df(path):
    L = json.loads(Path(path).read_text(encoding="utf-8"))["result"]["result_list"]
    df = pd.DataFrame({"date": pd.to_datetime([x["dt"] for x in L], format="%Y%m%d"),
                       "open": [float(x["open_pric"]) for x in L], "high": [float(x["high_pric"]) for x in L],
                       "low": [float(x["low_pric"]) for x in L], "close": [float(x["cur_prc"]) for x in L],
                       "volume": [float(x["acc_trde_qty"]) for x in L]}).sort_values("date").reset_index(drop=True)
    # J18: drop leading zero-volume placeholder rows (O=H=L=C)
    k = 0
    while k < len(df) and df.volume[k] == 0 and df.open[k] == df.high[k] == df.low[k] == df.close[k]:
        k += 1
    df = df.iloc[k:].copy()
    df["adjclose"] = df["close"]  # adjusted=1 response -> f = 1
    return df.set_index("date"), k


def market_s5(soxx_df, pwr_df, grid_df):
    """J18: events from SOXX (EV1/EV2) + EV5 on PWR; anchors/RG3/RG4/DS1 on GRID; RG2 = GRID and PWR; returns on PWR.
    Indicators are computed on each series' own history, then aligned on common dates."""
    i_s, i_p, i_g = OLDM.build_ind(soxx_df), OLDM.build_ind(pwr_df), OLDM.build_ind(grid_df)
    common = soxx_df.index.intersection(pwr_df.index).intersection(grid_df.index)
    pos = lambda df: df.index.get_indexer(common)
    ps, pp, pg = pos(soxx_df), pos(pwr_df), pos(grid_df)
    ev5 = (~np.isnan(i_p["sig60"][pp])) & (i_p["r"][pp] <= -2.0 * i_p["sig60"][pp])
    return dict(dates=common.to_numpy(), n=len(common),
                ev_r=i_s["r"][ps], ev_s60=i_s["sig60"][ps], ev_c=i_s["c"][ps], ev_h20=i_s["h20"][ps], ev5=ev5,
                b_c=i_g["c"][pg], b_lo=i_g["lo"][pg], b_r=i_g["r"][pg], b_s60=i_g["sig60"][pg], b_s5=i_g["sig5"][pg],
                b_ema=i_g["ema50"][pg],
                k_c=i_p["c"][pp], k_lo=i_p["lo"][pp], k_ema=i_p["ema50"][pp], k_rg2=True), common


# ------------------------------------------------------------------ simulator (V0..V3 and diagnostics)
def simulate_v(X, s0, rg4="two", partial=False, refresh="all", decay_n=20, weak=False, drop=None,
               ev2_mode="state", record=False):
    n = X["n"]
    er, es, ec, eh = X["ev_r"], X["ev_s60"], X["ev_c"], X["ev_h20"]
    bc, blo, br, bs60, bs5, bema = X["b_c"], X["b_lo"], X["b_r"], X["b_s60"], X["b_s5"], X["b_ema"]
    kc, kema = X["k_c"], X["k_ema"]
    ev1a = np.zeros(n, bool); ev2a = np.zeros(n, bool); wka = np.zeros(n, bool)
    for t in range(n):
        if not np.isnan(es[t]):
            ev1a[t] = er[t] <= -2.0 * es[t]
            if not np.isnan(eh[t]):
                ev2a[t] = ec[t] <= eh[t] * (1 - 3 * es[t])
            wka[t] = (er[t] <= -1.0 * es[t])
    wka = wka & ~ev1a & ~ev2a  # J16 (EV2 state reading)
    ev5a = X["ev5"] if X["ev5"] is not None else np.zeros(n, bool)
    eps, ep, opened = [], None, False
    for t in range(s0, n):
        e2 = ev2a[t] if ev2_mode == "state" else (ev2a[t] and not ev2a[t - 1])
        e1, w, e5 = bool(ev1a[t]), bool(weak and wka[t]), bool(ev5a[t])
        is_event = e1 or bool(e2) or w or e5
        if not opened:
            if is_event:
                opened = True
                ep = dict(t0=t, te=t, status=None, gate_day=None, fill=None, t1=None, f1=None, t2=None, f2=None,
                          decay_day=None, refreshes=0, opener="EV1" if e1 else ("EV2" if e2 else ("EV5" if e5 else "W")),
                          days=[] if record else None)
                C0, L0, minlow, cnt, last_reset = bc[t], blo[t], np.inf, 0, t
            continue
        refresh_now = is_event if refresh == "all" else (e1 or e5)  # J14: under S1 only EV1 (and EV5) rebase
        if refresh_now:
            ep["te"] = t; ep["refreshes"] += 1
            C0, L0, minlow, cnt, last_reset = bc[t], blo[t], np.inf, 0, t
            continue
        minlow = min(minlow, blo[t])
        ds1 = (bc[t] < L0) or (bc[t] < bema[t])
        if ds1:
            cnt = 0; last_reset = t
        else:
            cnt = cnt + 1 if bc[t] > C0 else 0
        rg1 = (t - ep["te"]) >= 2
        rg2 = bool(bc[t] >= bema[t])
        if X["k_rg2"]:
            rg2 = bool(rg2 and kc[t] >= kema[t])
        rg3 = bool((cnt >= 2) and (minlow >= L0))
        if rg4 == "two":
            r4 = bool((abs(br[t]) <= 2.0 * bs60[t]) and (bs5[t] <= 1.5 * bs60[t]))
        else:  # J3 V1
            r4 = bool((br[t] >= -2.0 * bs60[t]) and (bs5[t] <= 1.5 * bs60[t]))
        if record:
            ep["days"].append((t, rg1, rg2, rg3, r4))
        g = {"rg1": rg1, "rg2": rg2, "rg3": rg3, "rg4": r4}
        if drop:
            g.pop(drop)
        full_gate = all(g.values())
        decay = (t - last_reset) >= decay_n and rg2
        if not partial:
            if full_gate:
                ep["gate_day"] = t
                if t + 1 < n:
                    ep["status"] = "opened"; ep["fill"] = t + 1
                else:
                    ep["status"] = "opened_nofill"
                eps.append(ep); opened = False
            elif decay:
                ep["status"] = "decay"; ep["decay_day"] = t
                eps.append(ep); opened = False
        else:
            if ep["t1"] is None:
                if rg2 and rg3:  # J4 / F3: one-third tranche
                    ep["t1"] = t
                    if t + 1 < n:
                        ep["f1"] = t + 1
                    else:
                        ep["status"] = "opened_nofill"; eps.append(ep); opened = False
                elif decay:
                    ep["status"] = "decay"; ep["decay_day"] = t
                    eps.append(ep); opened = False
            else:
                if full_gate:  # t > t1 guaranteed (same session never decides two tranches)
                    ep["t2"] = ep["gate_day"] = t
                    if t + 1 < n:
                        ep["status"] = "full"; ep["f2"] = t + 1
                    else:
                        ep["status"] = "full_nofill"
                    eps.append(ep); opened = False
                elif decay:
                    ep["status"] = "third_only"; ep["decay_day"] = t
                    eps.append(ep); opened = False
    if opened:
        ep["status"] = "censored_third" if (partial and ep["t1"] is not None) else "censored"
        eps.append(ep)
    return eps


# ------------------------------------------------------------------ metrics
def metr_k(X, f, P=None, anchor=None):
    c, lo, n = X["k_c"], X["k_lo"], X["n"]
    P = c[f] * (1 + COST) if P is None else P
    a = f if anchor is None else anchor
    o = {}
    for h in (20, 60):
        if a + h < n:
            o[f"R{h}"] = float(c[a + h] / P - 1)
            o[f"MAE{h}"] = float(lo[a + 1: a + h + 1].min() / P - 1)
        else:
            o[f"R{h}"] = None; o[f"MAE{h}"] = None
    return o


def pbar(X, ep):
    return (X["k_c"][ep["f1"]] * (1 + COST)) / 3.0 + 2.0 * (X["k_c"][ep["f2"]] * (1 + COST)) / 3.0


def g_metrics(X, ep, partial, anchor="f2"):
    if not partial:
        return metr_k(X, ep["fill"])
    P = pbar(X, ep)
    return metr_k(X, ep["f1"], P=P, anchor=ep["f2"] if anchor == "f2" else ep["f1"])


def q(x, p):
    return float(np.percentile(np.array(x, float), p))


def summ(x):
    x = [v for v in x if v is not None]
    if not x:
        return dict(n=0)
    a = np.array(x, float)
    return dict(n=int(len(a)), median=float(np.median(a)), mean=float(a.mean()), p10=float(np.percentile(a, 10)),
                p25=float(np.percentile(a, 25)), p75=float(np.percentile(a, 75)), min=float(a.min()), max=float(a.max()))


def evaluate(X, eps, partial, anchor="f2", pick=None):
    n = X["n"]; kc = X["k_c"]
    sel = [e for e in eps if (pick is None or pick(e))]
    st = {}
    for e in sel:
        st[e["status"]] = st.get(e["status"], 0) + 1
    open_s = "full" if partial else "opened"
    # pairs (a, b): G vs X1' (primary) and X1 (ideal)
    G, Xn, Xi = [], [], []
    for e in sel:
        if e["status"] != open_s or e["t0"] + 1 >= n:
            continue
        g = g_metrics(X, e, partial, anchor); xn = metr_k(X, e["t0"] + 1); xi = metr_k(X, e["t0"])
        if None in (g["R60"], g["MAE60"], xn["R60"], xn["MAE60"]):
            continue
        G.append(g); Xn.append(xn); Xi.append(xi)
    N = len(G)
    out = dict(status=st, N=N)
    if N:
        mg, rg = np.median([g["MAE60"] for g in G]), np.median([g["R60"] for g in G])
        mxn, rxn = np.median([x["MAE60"] for x in Xn]), np.median([x["R60"] for x in Xn])
        mxi, rxi = np.median([x["MAE60"] for x in Xi]), np.median([x["R60"] for x in Xi])
        out.update(MAE60_G_med=float(mg), R60_G_med=float(rg), MAE60_X1n_med=float(mxn), R60_X1n_med=float(rxn),
                   MAE60_X1_med=float(mxi), R60_X1_med=float(rxi),
                   diff_a=float(mg - mxn), diff_b=float(rg - rxn), x1_diff_a=float(mg - mxi), x1_diff_b=float(rg - rxi))
    # combined view (c)
    cg_m, cg_r, cx_m, cx_r, ci_m = [], [], [], [], []
    closed = ("full", "third_only", "decay") if partial else ("opened", "decay")
    for e in sel:
        if e["status"] not in closed or e["t0"] + 1 >= n:
            continue
        xn = metr_k(X, e["t0"] + 1); xi = metr_k(X, e["t0"])
        if xn["R60"] is None or xn["MAE60"] is None:
            continue
        if e["status"] == open_s:
            g = g_metrics(X, e, partial, anchor)
            if g["R60"] is None or g["MAE60"] is None:
                continue
            gm, gr = g["MAE60"], g["R60"]
        elif e["status"] == "third_only":
            g = metr_k(X, e["f1"])
            if g["R60"] is None or g["MAE60"] is None:
                continue
            gm, gr = g["MAE60"] / 3.0, g["R60"] / 3.0  # J7
        else:
            gm, gr = 0.0, 0.0
        cg_m.append(gm); cg_r.append(gr); cx_m.append(xn["MAE60"]); cx_r.append(xn["R60"]); ci_m.append(xi["MAE60"])
    out["combined_N"] = len(cg_m)
    if cg_m:
        out.update(diff_c=q(cg_m, 10) - q(cx_m, 10), x1_diff_c=q(cg_m, 10) - q(ci_m, 10),
                   comb_G_MAE60=summ(cg_m), comb_X1n_MAE60=summ(cx_m), comb_G_R60=summ(cg_r), comb_X1n_R60=summ(cx_r),
                   comb_X1_MAE60=summ(ci_m))
    # d
    if partial:
        sess = [e["f1"] - e["t0"] for e in sel if e["status"] in ("full", "third_only")]
    else:
        sess = [e["fill"] - e["t0"] for e in sel if e["status"] == "opened"]
    out["sessions_first_buy"] = summ(sess)
    out["d"] = float(np.median(sess)) if sess else None
    # missed rebound (J13/J20)
    if partial:
        fe = [e for e in sel if e["status"] in ("full", "third_only")]
        out["missed_first_vs_X1n"] = summ([float(kc[e["f1"]] / kc[e["t0"] + 1] - 1) for e in fe])
        out["missed_first_vs_X1"] = summ([float(kc[e["f1"]] / kc[e["t0"]] - 1) for e in fe])
        fu = [e for e in sel if e["status"] == "full"]
        out["missed_pbar_vs_X1n"] = summ([float(pbar(X, e) / (kc[e["t0"] + 1] * (1 + COST)) - 1) for e in fu])
        out["third_hold_MAE"] = summ([float(X["k_lo"][e["f1"] + 1: e["f2"] + 1].min() / (kc[e["f1"]] * (1 + COST)) - 1)
                                      for e in fu])
        th = [metr_k(X, e["f1"]) for e in sel if e["status"] == "third_only"]
        out["third_only"] = dict(n=len(th), R60=summ([m["R60"] for m in th]), MAE60=summ([m["MAE60"] for m in th]))
        out["sessions_t0_to_f2"] = summ([e["f2"] - e["t0"] for e in fu])
    else:
        oe = [e for e in sel if e["status"] == "opened"]
        out["missed_vs_X1n"] = summ([float(kc[e["fill"]] / kc[e["t0"] + 1] - 1) for e in oe])
        out["missed_vs_X1"] = summ([float(kc[e["fill"]] / kc[e["t0"]] - 1) for e in oe])
    # pass flags
    if N:
        out["pass"] = dict(a=bool(out["diff_a"] >= 0.02), b=bool(out["diff_b"] >= -0.03),
                           c=bool(out.get("diff_c") is not None and out["diff_c"] >= 0.02),
                           d=bool(out["d"] is not None and out["d"] <= 6))
    return out


def j11(main, subs):
    """J11 adoption rule for one variant / one anchor reading."""
    if main["N"] < 15:
        return dict(candidate=False, verdict="표본 부족 — 보류")
    p = main["pass"]
    main_ok = p["b"] and (p["a"] or p["c"]) and p["d"]
    passing = [k for k in ("a", "c") if p[k]]
    sub_ok, sign_ok = {}, {}
    for name, s in subs.items():
        ok = s["N"] >= 15 and s["pass"]["b"] and s["pass"]["d"]
        sub_ok[name] = bool(ok) if s["N"] >= 15 else "표본 부족(미충족)"
    for k in passing:
        sign_ok[k] = all(s["N"] >= 15 and s.get(f"diff_{k}") is not None and s[f"diff_{k}"] > 0 for s in subs.values())
    cand = bool(main_ok and all(v is True for v in sub_ok.values()) and any(sign_ok.values()))
    return dict(candidate=cand, main_ok=bool(main_ok), main_pass=p, subsets_b_and_d=sub_ok, sign_consistent=sign_ok,
                verdict="채택 후보" if cand else "미달")


def f2_flags(df, s0_date, end_date=None):
    f = df["adjclose"] / df["close"]
    o, lo, c = df["open"] * f, df["low"] * f, df["adjclose"]
    m = lo < 0.97 * np.minimum(o, c)
    w = (df.index >= pd.Timestamp(s0_date))
    if end_date is not None:
        w &= (df.index <= pd.Timestamp(end_date))
    return dict(count=int((m & w).sum()), sessions=int(w.sum()), dates=[str(d.date()) for d in df.index[m & w]])


def ep_key(e):
    return (e["t0"], e["te"], e["status"], e["gate_day"], e["fill"], e["decay_day"], e["refreshes"])


# ------------------------------------------------------------------ self-test
class _T:
    def __init__(self): self.k = 0; self.fail = []
    def ok(self, cond, name):
        self.k += 1
        if not cond: self.fail.append(name)


def self_test():
    T = _T()
    mk = OLDM._mk
    def base(extra, lows=None, ema=None):
        return mk([100.0] * 10 + [94.0] + extra, lo=lows, ema=ema)
    # 1 equivalence with the imported simulate on synthetic and random series
    for ex in ([95.0, 95.5, 96.0, 96.0, 96.0], [93.5, 95.0, 95.5, 96.0, 96.0, 96.0], [93.8] * 25, [93.0] * 3,
               [95.0, 89.3, 90.0, 90.5, 91.0, 91.0]):
        ind = base(ex)
        T.ok([ep_key(e) for e in OLDM.simulate(ind, 5)] == [ep_key(e) for e in simulate_v(market_from_ind(ind), 5)],
             f"equiv synthetic {ex[:2]}")
    rng = np.random.default_rng(11)
    for seed in range(3):
        rr = rng.normal(0.0006, 0.022, 2500); rr[rng.integers(300, 2400, 12)] = -0.08
        px = 100 * np.cumprod(1 + rr)
        df = pd.DataFrame({"adjclose": px, "close": px, "low": px * (1 - 0.012 * rng.random(2500))},
                          index=pd.bdate_range("2005-01-03", periods=2500))
        ind = OLDM.build_ind(df)
        for mode in ("state", "cross"):
            a = [ep_key(e) for e in OLDM.simulate(ind, 260, ev2_mode=mode)]
            b = [ep_key(e) for e in simulate_v(market_from_ind(ind), 260, ev2_mode=mode)]
            T.ok(a == b and len(a) > 5, f"equiv random seed{seed} {mode}")
    # 2 V1 passes an up-shock day that V0 blocks: day 12 close 99 (r=+4.2% > 2*2%)
    ind = base([95.0, 99.0, 99.0, 99.0, 99.0])
    X = market_from_ind(ind)
    v0, v1 = simulate_v(X, 5), simulate_v(X, 5, rg4="down")
    T.ok(v0[0]["gate_day"] == 13 and v1[0]["gate_day"] == 12, "V1 up-shock passes, V0 waits")
    T.ok(simulate_v(X, 5, drop="rg4")[0]["gate_day"] == 12, "D2 drop rg4")
    # 3 V2: 1/3 on RG2&RG3 day even if RG4 fails; 2/3 on next all-RG day
    v2 = simulate_v(X, 5, partial=True)
    T.ok(v2[0]["status"] == "full" and v2[0]["t1"] == 12 and v2[0]["f1"] == 13 and v2[0]["t2"] == 13
         and v2[0]["f2"] == 14, "V2 tranche timing")
    # 4 F3 same session: all RG true on day 12 -> V0 gate 12, V2 t1 12 and t2 13
    ind = base([95.0, 95.5, 96.0, 96.0, 96.0]); X = market_from_ind(ind)
    v0, v2 = simulate_v(X, 5), simulate_v(X, 5, partial=True)
    T.ok(v0[0]["gate_day"] == 12 and v2[0]["t1"] == 12 and v2[0]["t2"] == 13, "F3 no two tranches same session")
    # 5 third_only: RG4 never true after day 12 -> decay at te+20 = 30 with 1/3 held
    ind = base([95.0, 95.5] + [96.0] * 30); ind["sig5"][13:] = 0.05; X = market_from_ind(ind)
    v2 = simulate_v(X, 5, partial=True)
    T.ok(v2[0]["status"] == "third_only" and v2[0]["t1"] == 12 and v2[0]["decay_day"] == 30, "third_only at te+20")
    # 6 DS1 after the 1/3 resets the clock: ema above close on day 15 -> decay at 35
    em = np.full(len(ind["c"]), 80.0); em[15] = 99.0
    ind2 = dict(ind); ind2["ema50"] = em; X = market_from_ind(ind2)
    v2 = simulate_v(X, 5, partial=True)
    T.ok(v2[0]["status"] == "third_only" and v2[0]["decay_day"] == 35, "DS1 after 1/3 resets clock")
    # 7 S1: EV2-only days do not rebase
    ind = mk([100.0] * 10 + [93.0] * 6, h20=100.0); X = market_from_ind(ind)
    T.ok(simulate_v(X, 5)[0]["refreshes"] == 5 and simulate_v(X, 5, refresh="ev1")[0]["refreshes"] == 0, "S1 no EV2 rebase")
    # 8 S3: weak shock (-3%) opens only with weak=True
    ind = mk([100.0] * 10 + [97.0, 97.5, 98.0, 98.0, 98.0, 98.0]); X = market_from_ind(ind)
    T.ok(len(simulate_v(X, 5)) == 0 and len(simulate_v(X, 5, weak=True)) == 1, "S3 W opens episode")
    # 9 metrics: P-bar, anchor, one-third scaling, percentile
    cc = [100.0] * 5 + list(np.linspace(100, 130, 80)); ind = mk(cc, lo=[x * 0.99 for x in cc]); X = market_from_ind(ind)
    e = dict(f1=5, f2=7)
    P = (cc[5] * 1.001) / 3 + 2 * (cc[7] * 1.001) / 3
    g = g_metrics(X, e, True, "f2"); g1 = g_metrics(X, e, True, "f1")
    T.ok(abs(g["R60"] - (cc[67] / P - 1)) < 1e-12 and abs(g["MAE60"] - (min(ind["lo"][8:68]) / P - 1)) < 1e-12, "P-bar anchor f2")
    T.ok(abs(g1["R60"] - (cc[65] / P - 1)) < 1e-12 and abs(g1["MAE60"] - (min(ind["lo"][6:66]) / P - 1)) < 1e-12, "P-bar anchor f1")
    T.ok(abs(q([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], 10) - 2.0) < 1e-12, "percentile linear")
    m = metr_k(X, 5); T.ok(abs(m["R60"] - OLDM.metr(ind, 5)["R60"]) < 1e-15 and abs(m["MAE60"] - OLDM.metr(ind, 5)["MAE60"]) < 1e-15, "metr equals imported")
    # 10 no lookahead for V2/V3 on random data
    rr = rng.normal(0.0005, 0.02, 1500); rr[[300, 301, 700, 1100]] = [-0.09, -0.05, -0.08, -0.1]
    px = 100 * np.cumprod(1 + rr)
    df = pd.DataFrame({"adjclose": px, "close": px, "low": px * (1 - 0.01 * rng.random(1500))},
                      index=pd.bdate_range("2008-01-01", periods=1500))
    full, pre = market_from_ind(OLDM.build_ind(df)), market_from_ind(OLDM.build_ind(df.iloc[:1200]))
    for kw in (dict(partial=True), dict(partial=True, rg4="down"), dict(rg4="down")):
        a = [ep_key(e) + (e["t1"],) for e in simulate_v(full, 260, **kw)
             if e["status"] in ("full", "third_only", "opened", "decay") and (e["gate_day"] or e["decay_day"]) < 1199]
        b = [ep_key(e) + (e["t1"],) for e in simulate_v(pre, 260, **kw)
             if e["status"] in ("full", "third_only", "opened", "decay") and (e["gate_day"] or e["decay_day"]) < 1199]
        T.ok(a == b and len(a) > 0, f"no lookahead {kw}")
    print(f"self-test: {T.k} checks, {len(T.fail)} failed")
    for f in T.fail:
        print("FAIL", f)
    return not T.fail


# ------------------------------------------------------------------ run
def check_hashes():
    want = dict(l.split("=", 1) for l in PREREG_SHA.read_text(encoding="utf-8").splitlines() if "=" in l)
    raw, lf = sha(PREREG), sha(PREREG, True)
    assert raw == want["raw_bytes_sha256"].strip() and lf == want["lf_normalized_sha256"].strip(), "prereg hash mismatch"
    text = PREREG.read_text(encoding="utf-8")
    for p, h in EXPECTED.items():
        assert sha(p) == h, f"input hash mismatch {p.name}"
        assert h in text, f"hash not in preregistration {p.name}"
    return raw


def v0_check(ind_soxx, s0):
    """Section 7 step 3: imported V0 must reproduce the first replay JSON exactly."""
    old = json.loads(OLD_JSON.read_text(encoding="utf-8"))
    rt = lambda x: json.loads(json.dumps(x, ensure_ascii=False))
    prim = OLDM.simulate(ind_soxx, s0)
    d = ind_soxx["dates"]; d0 = pd.Timestamp("2018-12-31")
    got = {"primary": OLDM.full_report(ind_soxx, prim),
           "sens4_first_half": OLDM.pair_eval(ind_soxx, prim, pick=lambda e: pd.Timestamp(d[e["t0"]]) <= d0),
           "sens4_second_half": OLDM.pair_eval(ind_soxx, prim, pick=lambda e: pd.Timestamp(d[e["t0"]]) > d0)}
    for key, kw in (("sens2_rebase", dict(rebase=True)), ("sens3_sma200", dict(use_sma200=True)),
                    ("sens5_ev2_crossing", dict(ev2_mode="cross"))):
        e = OLDM.simulate(ind_soxx, s0, **kw)
        got[key] = dict(status=OLDM.status_counts(e), pair=OLDM.pair_eval(ind_soxx, e),
                        pair_x1_next=OLDM.pair_eval(ind_soxx, e, "next"), report=OLDM.full_report(ind_soxx, e))
    res = {k: rt(v) == old[k] for k, v in got.items()}
    return res, prim


def run():
    raw = check_hashes()
    sx = pd.read_csv(SOXX, parse_dates=["date"]).set_index("date")
    qq = pd.read_csv(QQQ, parse_dates=["date"]).set_index("date")
    ind_s, ind_q = OLDM.build_ind(sx), OLDM.build_ind(qq)
    s0_s = int(np.argmax(sx.index >= pd.Timestamp(START_EVAL))); s0_q = int(np.argmax(qq.index >= pd.Timestamp(START_EVAL)))
    chk, prim_old = v0_check(ind_s, s0_s)
    print("V0 check vs first replay JSON:", chk)
    assert all(chk.values()), "V0 does not reproduce the first replay JSON - stop"
    XS, XQ = market_from_ind(ind_s), market_from_ind(ind_q)
    eq_s = [ep_key(e) for e in OLDM.simulate(ind_s, s0_s)] == [ep_key(e) for e in simulate_v(XS, s0_s)]
    eq_q = [ep_key(e) for e in OLDM.simulate(ind_q, s0_q)] == [ep_key(e) for e in simulate_v(XQ, s0_q)]
    print("new simulator V0 == imported simulate: SOXX", eq_s, "QQQ", eq_q)
    assert eq_s and eq_q
    dS = XS["dates"]
    first = lambda e: pd.Timestamp(dS[e["t0"]]) <= HALF_END
    second = lambda e: pd.Timestamp(dS[e["t0"]]) > HALF_END
    res = dict(meta=dict(prereg_raw_sha256=raw, script_sha256=sha(__file__), inputs={p.name: h for p, h in EXPECTED.items()},
                         soxx_rows=len(sx), soxx_first=str(sx.index[0].date()), soxx_last=str(sx.index[-1].date()),
                         eval_start=str(sx.index[s0_s].date()), v0_check=chk, v0_sim_equivalence=dict(SOXX=eq_s, QQQ=eq_q)))
    main, s4, verdicts, eps_main = {}, {}, {}, {}
    for v, kw in VARIANTS.items():
        e_s = simulate_v(XS, s0_s, **kw); e_q = simulate_v(XQ, s0_q, **kw)
        eps_main[v] = e_s
        anchors = ("f2", "f1") if kw["partial"] else ("f2",)
        for an in anchors:
            key = v if an == "f2" else f"{v}_anchor_f1"
            m = evaluate(XS, e_s, kw["partial"], an)
            subs = {"전반": evaluate(XS, e_s, kw["partial"], an, first), "후반": evaluate(XS, e_s, kw["partial"], an, second),
                    "QQQ": evaluate(XQ, e_q, kw["partial"], an)}
            main[key] = m; s4[key] = subs; verdicts[key] = j11(m, subs)
    final = {}
    for v in VARIANTS:
        if VARIANTS[v]["partial"]:
            a, b = verdicts[v]["candidate"], verdicts[f"{v}_anchor_f1"]["candidate"]
            final[v] = dict(candidate=bool(a and b), anchors_agree=bool(a == b))
        else:
            final[v] = dict(candidate=verdicts[v]["candidate"], anchors_agree=True)
    chosen = next((v for v in ("V1", "V2", "V3") if final[v]["candidate"]), None)
    res.update(main=main, s4=s4, j11=verdicts, final=final,
               overall=dict(chosen=chosen, verdict=("채택 후보 " + chosen) if chosen else "재설계 미달"))
    # D1 on V0 main
    e_rec = simulate_v(XS, s0_s, record=True)
    block, rg4_last, rg4_last_up = [], 0, 0
    r, s60 = XS["b_r"], XS["b_s60"]
    for e in e_rec:
        days = {t: (a1, a2, a3, a4) for t, a1, a2, a3, a4 in e["days"]}
        for t, (a1, a2, a3, a4) in days.items():
            if a1 and a2 and a3 and not a4:
                cause = "r>2s" if r[t] > 2 * s60[t] else ("r<-2s" if r[t] < -2 * s60[t] else "sigma5_only")
                block.append(dict(t=t, date=str(pd.Timestamp(dS[t]).date()), r=float(r[t]), up=bool(r[t] > 0), cause=cause))
        if e["status"] == "opened":
            g = e["gate_day"]
            if (g - 1) in days and (g - 1) > e["te"]:
                a1, a2, a3, a4 = days[g - 1]
                if a1 and a2 and a3 and not a4:
                    rg4_last += 1; rg4_last_up += int(r[g - 1] > 0)
    cz = {}
    for b in block:
        cz[b["cause"]] = cz.get(b["cause"], 0) + 1
    res["D1"] = dict(blocking_days=len(block), up_share=(sum(b["up"] for b in block) / len(block)) if block else None,
                     by_cause=cz, rg4_last_episodes=rg4_last,
                     rg4_last_up_share=(rg4_last_up / rg4_last) if rg4_last else None,
                     evaluated_sessions=sum(len(e["days"]) for e in e_rec), blocking_list=block)
    res["D2"] = {f"drop_{k}": evaluate(XS, simulate_v(XS, s0_s, drop=k), False) for k in ("rg2", "rg3", "rg4")}
    # S1, S2
    res["S1"] = {v: evaluate(XS, simulate_v(XS, s0_s, refresh="ev1", **kw), kw["partial"]) for v, kw in VARIANTS.items()}
    res["S1_anchor_f1"] = {v: evaluate(XS, simulate_v(XS, s0_s, refresh="ev1", **kw), True, "f1") for v, kw in VARIANTS.items() if kw["partial"]}
    res["S2"] = {v: evaluate(XS, simulate_v(XS, s0_s, decay_n=10, **kw), kw["partial"]) for v, kw in VARIANTS.items()}
    # S3
    res["S3"] = {}
    for v in ("V0", "V1", "V2"):
        kw = VARIANTS[v]; e = simulate_v(XS, s0_s, weak=True, **kw)
        res["S3"][v] = dict(all=evaluate(XS, e, kw["partial"]),
                            W_opened=evaluate(XS, e, kw["partial"], pick=lambda ep: ep["opener"] == "W"))
    # S5
    pw, k_p = kiwoom_df(PWR); gr, k_g = kiwoom_df(GRID)
    X5, common = market_s5(sx, pw, gr)
    s0_5 = int(np.argmax(common >= pd.Timestamp(START_EVAL)))
    res["S5"] = dict(meta=dict(aligned_sessions=len(common), first=str(common[0].date()), last=str(common[-1].date()),
                               eval_start=str(common[s0_5].date()), eval_sessions=int(len(common) - s0_5),
                               dropped_leading_rows=dict(PWR=k_p, GRID=k_g)))
    for v, kw in VARIANTS.items():
        e5 = simulate_v(X5, s0_5, **kw)
        res["S5"][v] = evaluate(X5, e5, kw["partial"])
        if kw["partial"]:
            res["S5"][f"{v}_anchor_f1"] = evaluate(X5, e5, True, "f1")
        res["S5"][v]["openers"] = {o: sum(1 for x in e5 if x["opener"] == o) for o in ("EV1", "EV2", "EV5")}
    # J19 F2 flags
    end5 = str(common[-1].date())
    res["F2_flags"] = dict(SOXX=f2_flags(sx, START_EVAL), QQQ=f2_flags(qq, START_EVAL),
                           PWR=f2_flags(pw.loc[pw.index.isin(common)], START_EVAL, end5),
                           GRID=f2_flags(gr.loc[gr.index.isin(common)], START_EVAL, end5))
    # episodes CSV (SOXX main, V0..V3)
    rows = []
    for v, eps in eps_main.items():
        for e in eps:
            D = lambda i: str(pd.Timestamp(dS[i]).date()) if i is not None else ""
            rows.append(dict(variant=v, t0=D(e["t0"]), last_event=D(e["te"]), status=e["status"], opener=e["opener"],
                             refreshes=e["refreshes"], t1=D(e["t1"]), f1=D(e["f1"]), gate_day=D(e["gate_day"]),
                             fill=D(e["fill"] if e["fill"] is not None else e["f2"]), decay_day=D(e["decay_day"])))
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    OUT_JSON.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for v in ("V0", "V1", "V2", "V3", "V2_anchor_f1", "V3_anchor_f1"):
        m = main[v]
        print(v, m["status"], "N", m["N"], "a %.6f b %.6f c %.6f d %s" % (m["diff_a"], m["diff_b"], m["diff_c"], m["d"]),
              verdicts[v]["verdict"])
    print("overall:", res["overall"])
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
