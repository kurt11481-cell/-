#!/usr/bin/env python3
"""fx-5b R-RI1 reissue-cap replay: A (current) vs B (R-RI1) vs C (no reissue). Read-only historical computation.

Pre-registration: docs/claude/fx5b-r-ri1-preregistration-2026-10-09.md (hash-locked 2026-10-09T16:47:05+09:00 before any
computation). Section numbers below refer to it. Inputs: Kiwoom adjusted daily candles (usa06012, raw responses saved
byte-for-byte), 7 tickers = watchlist members + buyable holdings (MVLL excluded: sell-only product).
"""
import argparse, csv, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
BT = ROOT / "stock-strategy-system/backtests"
PREREG = ROOT / "docs/claude/fx5b-r-ri1-preregistration-2026-10-09.md"
PREREG_SHA = ROOT / "docs/claude/fx5b-r-ri1-preregistration-2026-10-09.sha256"
RAW = BT / "fx5b_inputs_2026-10-09/kiwoom_raw"
TICKERS = ["SOXL", "NBIS", "MU", "BE", "DELL", "PWR", "LITE"]
EXPECTED = {
    "SOXL": "e8faa3ac68bf2c283b2c4ae84c232cbb60a3a2b61dddc7869dee03c37aba980f",
    "NBIS": "70bf3302cf750631b49187f32b18199a5a2cbe28ed7213b565247e86fddf8e94",
    "MU": "db9f9fa7a9e0492b5521ba8b7b10eb30a05005495417185622338f75f5359cc1",
    "BE": "4f1f9aba713a05f63af24f9d81fbf1762e5953cab4f02856b5f03b3ab1de6426",
    "DELL": "982a91b232255bf36f6affa75a0c134278df213aab35a18efa1e4cc087ae30cd",
    "PWR": "02d9c7d2b0b451581d5df10ea099134fd0a9dc5b82a112aaec32e273eecafc27",
    "LITE": "d81ede0bb41ea3f692185352045ff721134085046dce256e52d0529ef3fbe193",
}
OUT_JSON = BT / "fx5b_r_ri1_replay_2026-10-09_results.json"
OUT_CSV = BT / "fx5b_r_ri1_replay_2026-10-09_main_decisions.csv"
MAIN_START = pd.Timestamp("2024-10-08")
HALF2_START = pd.Timestamp("2025-10-08")
LONG_START = pd.Timestamp("2016-01-04")
COST = 0.001
K = 0.5          # cap = base * (1 + 0.5 sigma)   (design 7-2)
THR = -0.0025    # criterion 1: -0.25 %p
MIN_S = 15       # criterion 0


def sha(p, lf=False):
    b = Path(p).read_bytes()
    return hashlib.sha256(b.replace(b"\r\n", b"\n") if lf else b).hexdigest()


def raw_path(t):
    return RAW / f"{t}_kiwoom_usa06012_daily_adj1_20261009.json"


# ------------------------------------------------------------------ section 2: data processing
def parse_rows(rows):
    df = pd.DataFrame({"date": pd.to_datetime([x["dt"] for x in rows], format="%Y%m%d"),
                       "open": [float(x["open_pric"]) for x in rows], "high": [float(x["high_pric"]) for x in rows],
                       "low": [float(x["low_pric"]) for x in rows], "close": [float(x["cur_prc"]) for x in rows],
                       "volume": [float(x["acc_trde_qty"]) for x in rows]})
    df = df.sort_values("date").reset_index(drop=True)                       # P1
    k = 0
    while (k < len(df) and df.volume[k] == 0 and df.open[k] == df.high[k] == df.low[k] == df.close[k]):
        k += 1                                                                # P2 leading placeholders
    df = df.iloc[k:].reset_index(drop=True)
    gaps = df.date.diff().dt.days
    big = np.where(gaps > 7)[0]                                               # P3
    cut = int(big[-1]) if len(big) else 0
    df = df.iloc[cut:].reset_index(drop=True)
    return df, k, cut


def load(t):
    rows = json.loads(raw_path(t).read_text(encoding="utf-8"))["result"]["result_list"]
    return parse_rows(rows)


# ------------------------------------------------------------------ section 3: rules
def sigma60(close):
    r = pd.Series(close).pct_change()
    return r.rolling(60).std(ddof=1).to_numpy()


def decisions(ticker, df):
    c = df.close.to_numpy(float); d = df.date.to_numpy(); n = len(c)
    s = sigma60(c)
    out = []
    for t in range(n):
        if np.isnan(s[t]) or t + 22 > n - 1:
            continue
        cap1 = c[t] * (1 + K * s[t])
        f1 = c[t + 1] <= cap1
        capA2 = c[t + 1] * (1 + K * s[t + 1])
        capB2 = min(capA2, cap1)
        rec = dict(ticker=ticker, t=t, date=pd.Timestamp(d[t]), base=c[t], sigma=s[t], cap1=cap1, capA2=capA2,
                   capB2=capB2, c1=c[t + 1], c2=c[t + 2])
        for arm in ("A", "B", "C"):
            if f1:
                f, att = t + 1, 1
            elif arm == "A" and c[t + 2] <= capA2:
                f, att = t + 2, 2
            elif arm == "B" and c[t + 2] <= capB2:
                f, att = t + 2, 2
            else:
                f, att = None, 0
            o = dict(filled=f is not None, attempt=att)
            for H in (10, 20):
                if f is not None:
                    P = c[f] * (1 + COST)
                    o[f"R{H}"] = c[f + H] / P - 1
                    o[f"D{H}"] = c[t + 1 + H] / P - 1
                    o[f"U{H}"] = None
                else:
                    o[f"R{H}"] = None
                    o[f"D{H}"] = 0.0
                    o[f"U{H}"] = c[t + 1 + H] / cap1 - 1
            if f is not None:
                o["fill_vs_cap1"] = c[f] / cap1 - 1
                o["fill_vs_base"] = c[f] / c[t] - 1
            else:
                o["fill_vs_cap1"] = o["fill_vs_base"] = None
            rec[arm] = o
        rec["S_AB"] = bool(rec["A"]["attempt"] == 2 and c[t + 2] > cap1)
        rec["S_BC"] = bool(rec["B"]["attempt"] == 2)
        out.append(rec)
    return out


# ------------------------------------------------------------------ section 4: metrics and criteria
def st(x):
    x = [v for v in x if v is not None]
    if not x:
        return dict(n=0)
    a = np.array(x, float)
    return dict(n=int(len(a)), median=float(np.median(a)), mean=float(a.mean()), min=float(a.min()), max=float(a.max()),
                share_pos=float((a > 0).mean()))


def arm_metrics(D):
    out = {}
    for arm in ("A", "B", "C"):
        fills = [r[arm] for r in D if r[arm]["filled"]]
        unf = [r[arm] for r in D if not r[arm]["filled"]]
        out[arm] = dict(decisions=len(D), fill_rate=len(fills) / len(D) if D else None,
                        first_attempt_fills=sum(1 for o in fills if o["attempt"] == 1),
                        reissue_fills=sum(1 for o in fills if o["attempt"] == 2),
                        M2_fill_vs_cap1=st([o["fill_vs_cap1"] for o in fills]),
                        M2_fill_vs_base=st([o["fill_vs_base"] for o in fills]),
                        M3_R10=st([o["R10"] for o in fills]), M3_R20=st([o["R20"] for o in fills]),
                        M4_U10=st([o["U10"] for o in unf]), M4_U20=st([o["U20"] for o in unf]),
                        M5_D20_mean=float(np.mean([r[arm]["D20"] for r in D])) if D else None,
                        M5_D10_mean=float(np.mean([r[arm]["D10"] for r in D])) if D else None)
    return out


def crit(D, H=20, with_halves=True):
    """Criteria 0-3 (B vs A) and 0'-3' (C vs B)."""
    first_R = [r["A"][f"R{H}"] for r in D if r["A"]["attempt"] == 1]   # identical for all arms
    base_med = float(np.median(first_R)) if first_R else None
    mD = lambda X, arm: float(np.mean([r[arm][f"D{H}"] for r in X])) if X else None
    halves = {"전반": [r for r in D if r["date"] < HALF2_START], "후반": [r for r in D if r["date"] >= HALF2_START]}
    res = {}
    for name, (new, old, sset) in {"B_vs_A": ("B", "A", "S_AB"), "C_vs_B": ("C", "B", "S_BC")}.items():
        S = [r for r in D if r[sset]]
        chase = [r[old][f"R{H}"] for r in S]
        c1 = mD(D, new) - mD(D, old) if D else None
        o = dict(n_decisions=len(D), n_S=len(S), c0=len(S) >= MIN_S, diff1=c1, c1=bool(c1 is not None and c1 >= THR),
                 med_R_S=float(np.median(chase)) if chase else None, med_R_first=base_med,
                 mean_R_S=float(np.mean(chase)) if chase else None)
        o["c2"] = bool(o["med_R_S"] is not None and base_med is not None and o["med_R_S"] <= base_med)
        if with_halves:
            o["halves"] = {}
            for hn, X in halves.items():
                dd = (mD(X, new) - mD(X, old)) if X else None
                o["halves"][hn] = dict(n=len(X), n_S=sum(1 for r in X if r[sset]), diff1=dd,
                                       c1=bool(dd is not None and dd >= THR))
            o["c3"] = all(v["c1"] for v in o["halves"].values())
            o["candidate"] = bool(o["c0"] and o["c1"] and o["c2"] and o["c3"])
            o["verdict"] = ("표본 부족 — 보류" if not o["c0"] else ("채택 후보" if o["candidate"] else "미달")) \
                if name == "B_vs_A" else ("표본 부족" if not o["c0"] else ("C 검토 후보" if o["candidate"] else "미달"))
        res[name] = o
    return res


# ------------------------------------------------------------------ self-test
class _T:
    def __init__(self): self.k = 0; self.fail = []
    def ok(self, c, name):
        self.k += 1
        if not c: self.fail.append(name)


def _df(closes):
    n = len(closes)
    return pd.DataFrame({"date": pd.bdate_range("2020-01-01", periods=n), "open": closes, "high": closes,
                         "low": closes, "close": closes, "volume": np.ones(n)})


def self_test():
    T = _T()
    rng = np.random.default_rng(3)
    # sigma definition
    cl = 100 * np.cumprod(1 + rng.normal(0, 0.02, 200))
    s = sigma60(cl)
    r = np.diff(cl) / cl[:-1]
    T.ok(np.isnan(s[59]) and abs(s[60] - np.std(r[0:60], ddof=1)) < 1e-14 and abs(s[150] - np.std(r[90:150], ddof=1)) < 1e-14,
         "sigma60 ddof=1 window")
    # lookahead: sigma at t from truncated series
    T.ok(abs(sigma60(cl[:121])[120] - s[120]) < 1e-15, "no lookahead sigma")
    # construct a series: flat noise for 61 sessions so sigma exists, then controlled path
    base = list(100 * np.cumprod(1 + rng.normal(0, 0.01, 61)))
    def mk(tail):
        return _df(np.array(base + tail + [base[-1]] * 30))
    t0 = 60
    c60 = base[-1]
    s60 = sigma60(np.array(base + [c60] * 5))[60]
    cap1 = c60 * (1 + 0.5 * s60)
    # case 1: first attempt fills at exactly cap1 (<= boundary)
    D = decisions("X", mk([cap1, c60, c60]))
    r0 = [x for x in D if x["t"] == t0][0]
    T.ok(r0["A"]["attempt"] == 1 and r0["B"]["attempt"] == 1 and r0["C"]["attempt"] == 1, "first fill at boundary")
    # case 2: day1 above cap1, day2 between cap1 and capA2 -> A fills on reissue, B not (S_AB), C not
    up = cap1 * 1.02
    D = decisions("X", mk([up, cap1 * 1.01, cap1 * 1.01]))
    r0 = [x for x in D if x["t"] == t0][0]
    T.ok(r0["A"]["attempt"] == 2 and not r0["B"]["filled"] and not r0["C"]["filled"] and r0["S_AB"] and not r0["S_BC"],
         "S_AB case")
    T.ok(abs(r0["capB2"] - min(r0["capA2"], r0["cap1"])) < 1e-12 and r0["capB2"] == r0["cap1"], "B cap = min")
    # case 3: day2 back below cap1 -> A and B fill same price, C not (S_BC)
    D = decisions("X", mk([up, cap1 * 0.99, cap1 * 0.99]))
    r0 = [x for x in D if x["t"] == t0][0]
    T.ok(r0["A"]["attempt"] == 2 and r0["B"]["attempt"] == 2 and not r0["C"]["filled"] and r0["S_BC"] and not r0["S_AB"]
         and r0["A"]["R20"] == r0["B"]["R20"], "S_BC case")
    # case 4: decision-level return with common end and cost
    cc = np.array(base + [up, cap1 * 1.01] + list(np.linspace(cap1 * 1.01, cap1 * 1.3, 30)))
    D = decisions("X", _df(cc))
    r0 = [x for x in D if x["t"] == t0][0]
    P = cc[t0 + 2] * 1.001
    T.ok(abs(r0["A"]["D20"] - (cc[t0 + 21] / P - 1)) < 1e-12 and abs(r0["A"]["R20"] - (cc[t0 + 22] / P - 1)) < 1e-12
         and r0["B"]["D20"] == 0.0 and abs(r0["B"]["U20"] - (cc[t0 + 21] / r0["cap1"] - 1)) < 1e-12, "D/R/U definitions")
    # eligibility t+22 <= n-1
    T.ok(max(x["t"] for x in D) == len(cc) - 1 - 22, "eligibility t+22")
    # placeholder rows and gap rule
    rows = [dict(dt=f"2024010{i+1}", cur_prc="5", open_pric="5", high_pric="5", low_pric="5", acc_trde_qty="0") for i in range(3)]
    rows += [dict(dt="20240110", cur_prc="6", open_pric="5", high_pric="6", low_pric="5", acc_trde_qty="10"),
             dict(dt="20240111", cur_prc="6", open_pric="6", high_pric="6", low_pric="6", acc_trde_qty="0"),
             dict(dt="20240201", cur_prc="7", open_pric="7", high_pric="7", low_pric="6", acc_trde_qty="9"),
             dict(dt="20240202", cur_prc="8", open_pric="7", high_pric="8", low_pric="7", acc_trde_qty="9")]
    df, k, cut = parse_rows(list(reversed(rows)))
    T.ok(k == 3 and cut == 2 and list(df.close) == [7.0, 8.0], "placeholder + gap rule")
    df2, k2, cut2 = parse_rows(rows[:5])
    T.ok(k2 == 3 and cut2 == 0 and len(df2) == 2 and df2.volume.iloc[1] == 0, "interior zero volume kept")
    print(f"self-test: {T.k} checks, {len(T.fail)} failed")
    for f in T.fail:
        print("FAIL", f)
    return not T.fail


# ------------------------------------------------------------------ run
def run():
    want = dict(l.split("=", 1) for l in PREREG_SHA.read_text(encoding="utf-8").splitlines() if "=" in l)
    raw = sha(PREREG)
    assert raw == want["raw_bytes_sha256"].strip() and sha(PREREG, True) == want["lf_normalized_sha256"].strip()
    text = PREREG.read_text(encoding="utf-8")
    for t, h in EXPECTED.items():
        assert sha(raw_path(t)) == h and h in text, f"input hash {t}"
    data, allD, meta = {}, [], {}
    for t in TICKERS:
        df, k, cut = load(t)
        D = decisions(t, df)
        data[t] = D; allD += D
        main = [r for r in D if r["date"] >= MAIN_START]
        meta[t] = dict(rows=len(df), first=str(df.date.iloc[0].date()), last=str(df.date.iloc[-1].date()),
                       dropped_leading=k, gap_cut=cut, max_gap_days=int(df.date.diff().dt.days.max()),
                       main_decisions=len(main), main_first=str(main[0]["date"].date()) if main else None,
                       main_last=str(main[-1]["date"].date()) if main else None)
    main = [r for r in allD if r["date"] >= MAIN_START]
    res = dict(meta=dict(prereg_raw_sha256=raw, script_sha256=sha(__file__), inputs=EXPECTED, tickers=meta))
    res["main"] = dict(arms=arm_metrics(main), criteria=crit(main))
    common = [r for r in main if r["S_BC"]]
    res["main"]["reissue_common_AB"] = dict(n=len(common), R10=st([r["A"]["R10"] for r in common]),
                                           R20=st([r["A"]["R20"] for r in common]))
    res["per_ticker"] = {}
    for t in TICKERS:
        X = [r for r in main if r["ticker"] == t]
        am = arm_metrics(X); cr = crit(X, with_halves=False)
        res["per_ticker"][t] = dict(decisions=len(X), fill_rate={a: am[a]["fill_rate"] for a in "ABC"},
                                    S_AB=cr["B_vs_A"]["n_S"], S_BC=cr["C_vs_B"]["n_S"],
                                    D20_mean={a: am[a]["M5_D20_mean"] for a in "ABC"},
                                    diff1_B_A=cr["B_vs_A"]["diff1"], diff1_C_B=cr["C_vs_B"]["diff1"])
    longD = [r for r in allD if r["date"] >= LONG_START]
    res["sens_long"] = dict(arms=arm_metrics(longD), criteria=crit(longD, with_halves=False),
                            decisions_by_ticker={t: sum(1 for r in longD if r["ticker"] == t) for t in TICKERS})
    res["sens_H10"] = crit(main, H=10)
    exs = [r for r in main if r["ticker"] != "SOXL"]
    res["sens_ex_SOXL"] = dict(arms=arm_metrics(exs), criteria=crit(exs))
    pw = [r for r in main if r["ticker"] == "PWR"][-99:]
    res["ref_PWR_last99"] = dict(first=str(pw[0]["date"].date()), last=str(pw[-1]["date"].date()),
                                 first_attempt_unfilled=sum(1 for r in pw if r["A"]["attempt"] != 1),
                                 S_AB=sum(1 for r in pw if r["S_AB"]), S_BC=sum(1 for r in pw if r["S_BC"]),
                                 fill_rate={a: sum(1 for r in pw if r[a]["filled"]) / len(pw) for a in "ABC"},
                                 D20_mean={a: float(np.mean([r[a]["D20"] for r in pw])) for a in "ABC"},
                                 sigma_median=float(np.median([r["sigma"] for r in pw])))
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        cols = ["ticker", "date", "base", "sigma", "cap1", "capA2", "capB2", "c1", "c2", "S_AB", "S_BC"]
        armc = ["attempt", "fill_vs_cap1", "R10", "R20", "D10", "D20", "U10", "U20"]
        w = csv.writer(fh)
        w.writerow(cols + [f"{a}_{k}" for a in "ABC" for k in armc])
        for r in main:
            w.writerow([r["ticker"], str(r["date"].date())] + [r[k] for k in cols[2:]] + [r[a][k] for a in "ABC" for k in armc])
    OUT_JSON.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    cr = res["main"]["criteria"]
    print("main decisions", len(main), {a: round(res["main"]["arms"][a]["fill_rate"], 6) for a in "ABC"})
    for k, o in cr.items():
        print(k, "S", o["n_S"], "diff1 %.6f" % o["diff1"], "medS %.6f medFirst %.6f" % (o["med_R_S"], o["med_R_first"]),
              {h: round(v["diff1"], 6) for h, v in o["halves"].items()}, o["verdict"])
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
