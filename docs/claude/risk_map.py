#!/usr/bin/env python3
"""evolve-1029 account risk map (display only).

Pre-registered in docs/claude/trading-tools-review-2026-10-29.md section 11-2 (CEO confirmation
2026-10-29 19:58 KST). Reads saved Kiwoom usa06012 daily responses and one weights file
(symbol -> weight of account equity, cash = 1 - sum, cash return 0) and writes one JSON result.
It never calls a broker, never reads state or policy, and grants no order or quantity authority.

Run in the cloud container (skfolio 1.12.2), python -I risk_map.py --manifest M --weights W --asof D --out O.
manifest: {"SYM": ["kiwoom json", ...]} (later files win on the same date);
"MVLL": "2xMRVL" marks the structural proxy (2 x MRVL daily simple return).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2

ALPHA = 0.05                 # 95% VaR / CVaR
LOOKBACK = 1260              # sessions (5 years)
H = 20                       # holding period, sessions
BACKTEST_START = "2016-01-01"
R3_START = "2011-01-01"
BETA_MIN_REAL = 60           # real sessions needed before a beta proxy may be used
R4_SOXX_DROP = -0.20
R5_REAL_START_BEFORE = "2019-01-01"
R5_SCENARIOS = [("SOXX", -0.20), ("SOXX", -0.30), ("QQQ", -0.15)]
R5_SAMPLES = 10_000
AS_SIMS = 10_000
SEED = 1029
# Bars replaced only if a re-fetch still shows the same print (11-2 data defects).
KNOWN_BAD_HL = {("QQQ", "2026-10-27")}


def sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_kiwoom(paths: list[str]) -> pd.DataFrame:
    rows: dict[str, dict] = {}
    for path in paths:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        body = doc.get("result", doc)
        if body.get("return_code") not in (0, None):
            raise SystemExit(f"bad return_code in {path}")
        for r in body["result_list"]:
            d = r["dt"]
            rows[f"{d[:4]}-{d[4:6]}-{d[6:]}"] = r
    frame = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    out = pd.DataFrame(index=pd.to_datetime(frame.index))
    for col, src in (("open", "open_pric"), ("high", "high_pric"), ("low", "low_pric"),
                     ("close", "cur_prc"), ("volume", "acc_trde_qty"), ("amount", "acc_trde_prica")):
        out[col] = pd.to_numeric(frame[src].str.replace("+", "", regex=False), errors="coerce").abs().values
    # Leading zero-volume placeholder rows (NBIS 2024-08-21..10-18) are not trading.
    traded = out["volume"] > 0
    if traded.any():
        out = out.loc[traded.idxmax():]
    return out


def clean_hl(sym: str, bars: pd.DataFrame, refetched_same: bool) -> tuple[pd.DataFrame, list[str]]:
    notes = []
    for s, day in KNOWN_BAD_HL:
        ts = pd.Timestamp(day)
        if s == sym and ts in bars.index and refetched_same:
            o, c = bars.at[ts, "open"], bars.at[ts, "close"]
            bars.at[ts, "high"], bars.at[ts, "low"] = max(o, c), min(o, c)
            notes.append(f"{sym} {day} high/low set to max/min(open, close)")
    return bars, notes


def tail_stats(returns: np.ndarray) -> tuple[float, float]:
    """VaR and CVaR as positive loss fractions (empirical, linear quantile)."""
    losses = -np.asarray(returns, dtype=float)
    var = float(np.quantile(losses, 1 - ALPHA))
    cvar = float(losses[losses >= var].mean())
    return var, cvar


def hold_returns(daily: pd.DataFrame, h: int) -> pd.DataFrame:
    """Per-asset compounded h-session simple returns over every window ending at each row."""
    log = np.log1p(daily)
    return np.expm1(log.rolling(h).sum()).dropna()


def kupiec(n: int, x: int) -> float:
    p, ph = ALPHA, x / n
    l0 = (n - x) * math.log(1 - p) + x * math.log(p)
    l1 = ((n - x) * math.log(1 - ph) if x < n else 0.0) + (x * math.log(ph) if x > 0 else 0.0)
    return float(1 - chi2.cdf(-2 * (l0 - l1), 1))


class Universe:
    """Daily simple returns on the SOXX calendar, real where available, proxies marked."""

    def __init__(self, bars: dict[str, pd.DataFrame], proxies: dict[str, str]):
        cal = bars["SOXX"].index
        close = pd.DataFrame({s: b["close"].reindex(cal) for s, b in bars.items()})
        self.real_start = {s: b.index[0] for s, b in bars.items()}
        # Inside an asset's own history a missing close is carried (0 return) and counted.
        self.missing = {s: int(close.loc[self.real_start[s]:, s].isna().sum()) for s in bars}
        close = close.ffill()
        rets = close.pct_change()
        for s in bars:
            rets.loc[:self.real_start[s], s] = np.nan
        self.real = rets.iloc[1:]
        self.proxies = proxies
        for sym, rule in proxies.items():
            if rule == "2xMRVL":
                self.real[sym] = 2.0 * self.real["MRVL"]
                self.real_start[sym] = self.real_start["MRVL"]

    def beta(self, sym: str, until: pd.Timestamp) -> float | None:
        cols = self.real[[sym, "SOXX"]].loc[:until].dropna()
        if len(cols) < BETA_MIN_REAL:
            return None
        x, y = cols["SOXX"].values, cols[sym].values
        return float(np.dot(x - x.mean(), y - y.mean()) / np.dot(x - x.mean(), x - x.mean()))

    def filled(self, syms: list[str], beta_until: pd.Timestamp, start, end, real_only: bool):
        """Returns frame on [start, end]; per-asset flag 'proxy' or None if it must go to cash."""
        frame = self.real.loc[start:end, syms].copy()
        status = {}
        for s in syms:
            gap = frame[s].isna()
            proxied = s in self.proxies
            if gap.any():
                if real_only:
                    status[s] = None
                    continue
                b = self.beta(s, beta_until)
                if b is None:
                    status[s] = None
                    continue
                frame.loc[gap, s] = b * frame.loc[gap, "SOXX"] if "SOXX" in frame else np.nan
                proxied = True
            if real_only and s in self.proxies:
                status[s] = None
                continue
            status[s] = "proxy" if proxied else "real"
        return frame, status


def portfolio(frame: pd.DataFrame, weights: dict[str, float], status: dict) -> tuple[np.ndarray, dict]:
    w = {s: v for s, v in weights.items() if status.get(s) is not None}
    to_cash = sum(v for s, v in weights.items() if status.get(s) is None)
    proxy_share = sum(v for s, v in w.items() if status[s] == "proxy")
    return np.array([w.get(s, 0.0) for s in frame.columns]), {"to_cash": to_cash, "proxy": proxy_share}


def window_returns(daily: pd.DataFrame, wvec: np.ndarray, h: int) -> np.ndarray:
    return hold_returns(daily, h).values @ wvec


def backtest(u: Universe, weights: dict[str, float], syms: list[str], real_only: bool, rng) -> dict:
    cal = u.real.index
    start = cal.searchsorted(pd.Timestamp(BACKTEST_START))
    rows, preds = [], []
    s = start
    while s + H <= len(cal):
        if s - LOOKBACK < 0:
            s += H
            continue
        t0 = cal[s - 1]
        frame, status = u.filled(syms, t0, cal[s - LOOKBACK], cal[s + H - 1], real_only)
        wvec, share = portfolio(frame, weights, status)
        look = frame.iloc[:LOOKBACK].fillna(0.0)
        dist = window_returns(look, wvec, H)
        var, cvar = tail_stats(dist)
        outcome = frame.iloc[LOOKBACK:].fillna(0.0)
        actual = float(np.prod(1 + outcome.values, axis=0) @ wvec - wvec.sum())
        rows.append({"start": str(cal[s].date()), "end": str(cal[s + H - 1].date()), "var": var,
                     "cvar": cvar, "actual": actual, "breach": actual < -var,
                     "to_cash": share["to_cash"], "proxy": share["proxy"]})
        preds.append(dist)
        s += H
    n = len(rows)
    x = sum(r["breach"] for r in rows)
    # Acerbi-Szekely Z2 (one-sided: ES under-estimated when Z2 is too negative).
    var = np.array([r["var"] for r in rows])
    cvar = np.array([r["cvar"] for r in rows])

    def z2(actuals: np.ndarray) -> np.ndarray:
        return (actuals * (actuals < -var) / cvar).sum(axis=-1) / (n * ALPHA) + 1

    z_obs = float(z2(np.array([r["actual"] for r in rows])))
    draws = np.column_stack([rng.choice(p, size=AS_SIMS) for p in preds])  # (sims, windows)
    sims = z2(draws)
    breach_rows = [r for r in rows if r["breach"]]
    ratio = (float(np.mean([-r["actual"] for r in breach_rows]) / np.mean([r["cvar"] for r in breach_rows]))
             if breach_rows else None)
    kp = kupiec(n, x)
    asp = float((sims <= z_obs).mean())
    return {"windows": n, "breaches": x, "kupiec_p": kp, "kupiec_pass": kp >= 0.05,
            "z2": z_obs, "z2_p": asp, "z2_pass": asp >= 0.05, "breach_loss_over_cvar": ratio,
            "mean_proxy_share": float(np.mean([r["proxy"] for r in rows])) if rows else None,
            "mean_to_cash_share": float(np.mean([r["to_cash"] for r in rows])) if rows else None,
            "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--asof", required=True)
    ap.add_argument("--qqq-refetch-same", action="store_true")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    from skfolio import Portfolio, RiskMeasure
    from skfolio.distribution import VineCopula
    import skfolio

    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    weights = {k: float(v) for k, v in json.loads(Path(a.weights).read_text(encoding="utf-8"))["weights"].items()}
    proxies = {s: rule for s, rule in manifest.items() if isinstance(rule, str)}
    bars, notes = {}, []
    for sym, paths in manifest.items():
        if isinstance(paths, str):
            continue
        b = load_kiwoom(paths)
        b, n = clean_hl(sym, b, a.qqq_refetch_same)
        bars[sym], notes = b.loc[:a.asof], notes + n
    u = Universe(bars, proxies)
    held = sorted(weights)
    syms = sorted(set(held) | {"SOXX", "QQQ"})
    asof = u.real.index[u.real.index <= pd.Timestamp(a.asof)][-1]
    rng = np.random.default_rng(SEED)

    # Current view: lookback ends at asof; proxies use data up to asof (no later data exists).
    cal = u.real.index
    end = cal.get_loc(asof)
    frame, status = u.filled(syms, asof, cal[end - LOOKBACK + 1], asof, False)
    wvec, share = portfolio(frame, weights, status)
    daily = frame.fillna(0.0)
    p1 = daily.values @ wvec
    r1_var, r1_cvar = tail_stats(p1)
    r2_var, r2_cvar = tail_stats(window_returns(daily, wvec, H))
    port = Portfolio(X=daily, weights=wvec, compounded=True)
    contrib = dict(zip(daily.columns, np.asarray(port.contribution(measure=RiskMeasure.CVAR), dtype=float)))

    # R3: fixed daily weights from 2011, compounded.
    f3, st3 = u.filled(syms, asof, pd.Timestamp(R3_START), asof, False)
    w3, sh3 = portfolio(f3, weights, st3)
    p3 = Portfolio(X=f3.fillna(0.0), weights=w3, compounded=True)

    # R4: SOXX 20-session drops of more than 20%, one worst window per episode.
    hr = hold_returns(f3.fillna(0.0), H)
    soxx = hr["SOXX"]
    hits = soxx[soxx <= R4_SOXX_DROP]
    episodes, last = [], None
    for ts in hits.index:
        i = hr.index.get_loc(ts)
        if last is not None and i - last <= H:
            if soxx[ts] < soxx[episodes[-1]]:
                episodes[-1] = ts
        else:
            episodes.append(ts)
        last = i
    def proxy_share(first: pd.Timestamp) -> float:
        return float(sum(weights[s] for s in held if st3.get(s) is not None
                         and (s in proxies or u.real_start[s] > first)))

    r4 = []
    for ts in episodes:
        first = hr.index[hr.index.get_loc(ts) - H + 1]
        r4.append({"start": str(first.date()), "end": str(ts.date()), "soxx": float(soxx[ts]),
                   "account": float(hr.loc[ts].values @ w3), "proxy_share": proxy_share(first)})

    # R5: vine copula on overlapping 20-session returns, real data only, early-history names.
    early = [s for s in syms if s not in proxies and u.real_start[s] < pd.Timestamp(R5_REAL_START_BEFORE)]
    early += [s for s in syms if s in proxies and u.real_start[s] < pd.Timestamp(R5_REAL_START_BEFORE)]
    span_start = max(u.real_start[s] for s in early)
    x5 = hold_returns(u.real.loc[span_start:asof, early].dropna(), H)
    excluded = sorted(set(held) - set(early))
    w5 = np.array([weights.get(s, 0.0) for s in x5.columns])
    vine = VineCopula(central_assets=["SOXX", "QQQ"], log_transform=True, n_jobs=1, random_state=SEED).fit(x5)
    r5 = []
    for sym, shock in R5_SCENARIOS:
        sample = vine.sample(n_samples=R5_SAMPLES, conditioning={sym: shock}) @ w5
        r5.append({"condition": f"{sym} {shock:+.0%} / {H} sessions", "median": float(np.median(sample)),
                   "p05": float(np.quantile(sample, 0.05))})

    result = {
        "artifact": "EVOLVE_1029_RISK_MAP", "display_only": True, "order_authority": False,
        "quantity_authority": "none", "asof": str(asof.date()),
        "versions": {"skfolio": skfolio.__version__, "numpy": np.__version__, "pandas": pd.__version__,
                     "python": sys.version.split()[0]},
        "script_sha256": sha256(__file__),
        "inputs": {s: [{"file": Path(p).name, "sha256": sha256(p)} for p in v]
                   for s, v in manifest.items() if not isinstance(v, str)},
        "proxies": proxies, "notes": notes, "missing_closes_carried": u.missing,
        "real_start": {s: str(t.date()) for s, t in u.real_start.items()},
        "cash_weight": 1 - sum(weights.values()),
        "R1_day_cvar95": r1_cvar, "R1_day_var95": r1_var,
        "R2_20d_var95": r2_var, "R2_20d_cvar95": r2_cvar,
        "current_proxy_share": share["proxy"], "current_to_cash_share": share["to_cash"],
        "R3_max_drawdown": float(p3.max_drawdown), "R3_cdar95": float(p3.cdar),
        "R3_window": [str(f3.index[0].date()), str(f3.index[-1].date())], "R3_proxy_share": sh3["proxy"],
        "R3_to_cash_share": sh3["to_cash"],
        "R4_episodes": r4,
        "R5_scenarios": r5, "R5_fit_span": [str(x5.index[0].date()), str(x5.index[-1].date())],
        "R5_excluded_weight": float(sum(weights[s] for s in excluded)), "R5_excluded": excluded,
        "R6_cvar_contribution": {s: contrib[s] for s in held if s in contrib},
        "calibration": {"all": backtest(u, weights, syms, False, rng),
                        "real_only": backtest(u, weights, syms, True, rng)},
    }
    cal_ok = all(result["calibration"][k][t] for k in ("all", "real_only") for t in ("kupiec_pass", "z2_pass"))
    result["calibrated"] = cal_ok
    Path(a.out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("asof", "calibrated", "R1_day_cvar95", "R2_20d_cvar95")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
