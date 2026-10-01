#!/usr/bin/env python
"""S4-3 leverage-up candidate validation (research only; no broker access, no orders, no policy change).

Pre-result contract: LEVERAGE_UP_PROTOCOL_2026-10-01.md (+ .sha256 sidecar). Modes:
  --self-test   engine / metric / state-machine checks (must pass before --run)
  --collect     download NDX, SPX, DTB3, Shiller into leverage_up_inputs_2026-10-01/ (public data only)
  --run         evaluate from stored inputs only; writes results JSON, pairs CSV, Korean results markdown
Parameters, rules and gates are fixed by the protocol; never edit them after seeing a result.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import math
import multiprocessing as mp
import random
import sys
import time
import types
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

HERE = Path(__file__).resolve().parent
INPUT_DIR = HERE / "leverage_up_inputs_2026-10-01"
SOURCES_JSON = INPUT_DIR / "leverage_up_inputs_sources.json"
CPV_DIR = HERE / "cpv_inputs_2026-10-01"
CPV_SOURCES = CPV_DIR / "cpv_inputs_sources.json"
S4_DIR = HERE / "soxl_signal_inputs_2026-10-01"
S4_SOURCES = S4_DIR / "soxl_signal_inputs_sources.json"
PROTOCOL = HERE / "LEVERAGE_UP_PROTOCOL_2026-10-01.md"
PROTOCOL_SIDECAR = HERE / "LEVERAGE_UP_PROTOCOL_2026-10-01.sha256"
STEM = "leverage_up_2026-10-01"
RESULTS_JSON = HERE / f"{STEM}_results.json"
PAIRS_CSV = HERE / f"{STEM}_pairs.csv"
RESULTS_MD = HERE / "LEVERAGE_UP_RESULTS_2026-10-01.md"

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"}
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start}&coed={end}"
SHILLER_URLS = ("http://www.econ.yale.edu/~shiller/data/ie_data.xls",)
END_DATE = "2026-09-29"
SERIES = {  # name -> (yahoo ticker, requested first date)
    "NDX": ("^NDX", "1985-10-01"),
    "SPX": ("^GSPC", "1954-01-04"),
}

# ----------------------------------------------------------------------------
# protocol constants (fixed before any result)
# ----------------------------------------------------------------------------
FEE1 = {"SOX": 0.0035, "N": 0.0020, "S": 0.0009}          # 1x ETF fee per year (to confirm)
BANDS = (0.0, 0.025, 0.05, 0.075, 0.10, 0.125, 0.15)
SHIFTS = tuple(range(20))
COST = 0.0010
COSTS = (0.0010, 0.0020, 0.0050)
MARKETS = ("SOX", "N", "S")
EARLY_END = {"SOX": pd.Timestamp("2010-03-10"), "N": pd.Timestamp("1994-05-03"), "S": pd.Timestamp("1994-05-03")}
POST_START = pd.Timestamp("2010-03-11")
LATE_START = pd.Timestamp("1994-05-04")
PERIODS = {
    "SOX": [("1994-99", "1994-01-01", "1999-12-31"), ("2000-02", "2000-01-01", "2002-12-31"), ("2003-07", "2003-01-01", "2007-12-31"),
            ("2008-09", "2008-01-01", "2009-12-31"), ("2010-15", "2010-01-01", "2015-12-31"), ("2016-20", "2016-01-01", "2020-12-31"),
            ("2021-25", "2021-01-01", "2025-12-31"), ("2026", "2026-01-01", "2026-12-31")],
    "N": [("1985-89", "1985-01-01", "1989-12-31"), ("1990-94", "1990-01-01", "1994-12-31"), ("1995-99", "1995-01-01", "1999-12-31"),
          ("2000-04", "2000-01-01", "2004-12-31"), ("2005-09", "2005-01-01", "2009-12-31"), ("2010-14", "2010-01-01", "2014-12-31"),
          ("2015-19", "2015-01-01", "2019-12-31"), ("2020-26", "2020-01-01", "2026-12-31")],
    "S": [("1954-59", "1954-01-01", "1959-12-31"), ("1960s", "1960-01-01", "1969-12-31"), ("1970s", "1970-01-01", "1979-12-31"),
          ("1980s", "1980-01-01", "1989-12-31"), ("1990s", "1990-01-01", "1999-12-31"), ("2000s", "2000-01-01", "2009-12-31"),
          ("2010s", "2010-01-01", "2019-12-31"), ("2020-26", "2020-01-01", "2026-12-31")],
}
SEG_NAMES = {"SOX": ("full", "early", "post"), "N": ("full", "early", "late", "post"), "S": ("full", "early", "late", "post")}
METRIC_COLS = ("cagr", "mdd", "w1_min", "w1_med", "w1_pathfrac", "w1_endfrac", "w3_min", "w3_med", "w3_pathfrac", "w3_endfrac", "meanx", "dd20n", "n")
MAIN = ["T1", "T2", "F1.32", "K132-G", "T2-132b", "X1"]
CAND_ORDER = ["B0"] + MAIN
FIX_STEP = 0.04
FIX_GRID = [round(0.40 + FIX_STEP * k, 2) for k in range(int(round((3.00 - 0.40) / FIX_STEP)) + 1)]

# reference engine (protocol Appendix A) is embedded verbatim for self-test cross-checks
REFERENCE_ENGINE_SRC = r'''import numpy as np, pandas as pd

def features(close, rate_pct, er1=0.0035):
    d = pd.DataFrame({'px': close})
    d['rate'] = rate_pct.reindex(close.index.union(rate_pct.index)).ffill().reindex(close.index) / 100.0
    d['r'] = d['px'].pct_change(); d['rc'] = d['rate'] / 252.0
    d['r3'] = 3 * d['r'] - 0.0095 / 252 - 2 * d['rc']          # 3배 상품(차입비 = 국채 금리)
    d['r1'] = d['r'] - er1 / 252                                 # 1배 ETF(보수만)
    d = d.iloc[1:].copy()
    d['sig20'] = d['r'].rolling(20).std()
    d['sig_med'] = d['sig20'].expanding(min_periods=120).median() * np.sqrt(252)
    d['dd252'] = d['px'] / d['px'].rolling(252, min_periods=1).max() - 1
    d['sma200'] = d['px'].rolling(200).mean(); d['ext'] = d['px'] / d['sma200'] - 1
    return d

def with_cash(d, model='usd0'):
    """남는 현금 일 수익만 바꾼다. usd0 = 달러 예수금 0%(기본), tbill = 국채 금리(탐색 대조용)."""
    d = d.copy()
    d['rc'] = 0.0 if model == 'usd0' else d['rate'] / 252
    return d

COLS = ('px', 'sig_med', 'dd252', 'sma200', 'ext')

def simulate(d, target, band=0.10, cost=0.0010, lev_ret=None):
    """비교 구현 '3배 + 현금': w = X/3, 나머지 현금(rc). 종가 t 결정 → 종가 t+1 체결."""
    rL = d['r3'].values if lev_ret is None else lev_ret; rc = d['rc'].values
    E = np.empty(len(d)); X = np.empty(len(d)); e, w, pend, st = 1.0, None, None, {}
    cols = {c: d[c].values for c in COLS}
    for i in range(len(d)):
        if i > 0:
            gl = w * (1 + rL[i]); gc = (1 - w) * (1 + rc[i]); e = e * (gl + gc); w = gl / (gl + gc)
        if pend is not None:
            if w is None: w = pend; e -= e * cost * pend
            elif abs(pend - w) >= band - 1e-12 or (pend == 0 < w) or (w == 0 < pend):
                e -= e * cost * abs(pend - w); w = pend
        if w is None: w = 0.0
        E[i] = e; X[i] = 3 * w
        pend = min(1.0, max(0.0, target({c: cols[c][i] for c in cols}, st, e) / 3.0))
    return pd.Series(E, d.index), pd.Series(X, d.index)

def simulate_core(d, target, band=0.10, cost=0.0010, lev_ret=None, one_ret=None):
    """기본 구현 'ETF 코어': X ≥ 1이면 3배 (X−1)/2 + 1배 ETF 나머지(현금 0), X < 1이면 1배 ETF X + 현금.
    3배 또는 1배 비중이 목표에서 폭 이상 벗어나거나 3배가 0에서/0으로 갈 때 체결. 비용은 두 상품 거래량 합에."""
    rL = d['r3'].values if lev_ret is None else lev_ret
    r1 = d['r1'].values if one_ret is None else one_ret; rc = d['rc'].values
    E = np.empty(len(d)); X = np.empty(len(d)); e = 1.0; wl = wx = None; pend = None; st = {}; n = 0
    cols = {c: d[c].values for c in COLS}
    split = lambda x: ((x - 1) / 2, 1 - (x - 1) / 2) if x >= 1 else (0.0, x)
    for i in range(len(d)):
        if i > 0:
            gl = wl * (1 + rL[i]); gx = wx * (1 + r1[i]); gc = (1 - wl - wx) * (1 + rc[i])
            tot = gl + gx + gc; e *= tot; wl, wx = gl / tot, gx / tot
        if pend is not None:
            tl, tx = split(pend)
            if wl is None:
                wl, wx = tl, tx; e -= e * cost * (tl + tx)
            elif abs(tl - wl) >= band - 1e-12 or abs(tx - wx) >= band - 1e-12 or (tl == 0 < wl) or (wl == 0 < tl):
                e -= e * cost * (abs(tl - wl) + abs(tx - wx)); wl, wx = tl, tx; n += 1
        if wl is None: wl, wx = 0.0, 0.0
        E[i] = e; X[i] = 3 * wl + wx
        pend = max(0.0, target({c: cols[c][i] for c in cols}, st, e))
    return pd.Series(E, d.index), pd.Series(X, d.index), n

def fixed(L): return lambda row, st, e: L          # B0 = fixed(1.0), F1.32 = fixed(1.32)

def make_G(base=1.0, extra=0.5, trend=True, overheat=False, brake=None,
           off=0.80, on=0.90, L=252, k_hot=1.0, k_cool=0.5, ma_key='sma200'):
    """T1 = make_G(1.0, 0.5), T2 = make_G(1.0, 0.5, overheat=True),
    K132-G = make_G(1.32, 0.0, trend=False, brake=1.0), T2-132b = make_G(1.32, 0.5, overheat=True, brake=1.0)."""
    def f(row, st, e):
        h = st.setdefault('hist', []); h.append(e)
        if len(h) > L: h.pop(0)
        hw = max(h)
        if e < off * hw: st['gate'] = False
        elif e >= on * hw: st['gate'] = True
        gate = st.get('gate', True)
        if overheat and not np.isnan(row['ext']) and not np.isnan(row['sig_med']):
            if row['ext'] >= k_hot * row['sig_med']: st['hot'] = True
            elif row['ext'] <= k_cool * row['sig_med']: st['hot'] = False
        tr = ((not np.isnan(row[ma_key])) and row['px'] > row[ma_key]) if trend else True
        b = base if (gate or brake is None) else brake
        return b + (extra if (tr and gate and not st.get('hot', False)) else 0.0)
    return f

def make_X1(add=0.5, k_dd=0.75, k_reb=1.2, k_stop=0.45, k_exit=0.30):
    def f(row, st, e):
        dd, px, sm = row['dd252'], row['px'], row['sig_med']
        if np.isnan(dd) or np.isnan(sm): return 1.0
        if st.get('cool'):
            if dd >= -k_exit * sm: st['cool'] = False
            return 1.0
        lvl = st.get('lvl', 0.0)
        if lvl == 0.0 and dd <= -k_dd * sm:
            lvl = add; st['entry'] = px; st['trough'] = px; st['s0'] = sm
        if lvl > 0:
            st['trough'] = min(st['trough'], px); s0 = st['s0']
            if dd >= -k_exit * s0 or px >= st['trough'] * (1 + k_reb * s0) or px <= st['entry'] * (1 - k_stop * s0):
                lvl = 0.0; st['cool'] = True
        st['lvl'] = lvl
        return 1.0 + lvl
    return f
'''


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def read_sidecar() -> dict[str, str]:
    out = {}
    for line in PROTOCOL_SIDECAR.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def check_protocol() -> dict[str, str]:
    side = read_sidecar()
    lf = lf_sha256(PROTOCOL)
    if lf != side.get("lf_normalized_sha256"):
        raise RuntimeError("protocol changed after it was fixed (LF-normalized sha256 differs from sidecar)")
    return {"raw_bytes_sha256": sha256_file(PROTOCOL), "lf_normalized_sha256": lf,
            "sidecar_raw_bytes_sha256": side.get("raw_bytes_sha256", ""), "fixed_at": side.get("fixed_at", "")}


def clean(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.isoformat()
    return obj


# ----------------------------------------------------------------------------
# data collection (--collect): public data only
# ----------------------------------------------------------------------------
def http_get(url: str, attempts: int = 6, timeout: int = 90, headers: dict[str, str] | None = None) -> bytes:
    last = ""
    for k in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=YAHOO_HEADERS if headers is None else headers), timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:  # network errors are retried, then reported
            last = repr(exc)
            time.sleep(4 * (k + 1))
    raise RuntimeError(f"GET failed: {url[:90]} {last}")


def fetch_yahoo_raw(ticker: str, start: str, end: str) -> tuple[pd.DataFrame, str]:
    params = {"period1": int(pd.Timestamp(start, tz="UTC").timestamp()),
              "period2": int((pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)).timestamp()),
              "interval": "1d", "events": "div,splits", "includeAdjustedClose": "true"}
    url = YAHOO_URL.format(ticker=urllib.parse.quote(ticker)) + "?" + urllib.parse.urlencode(params)
    payload = json.loads(http_get(url).decode("utf-8"))
    chart = payload.get("chart") or {}
    if chart.get("error") or not chart.get("result"):
        raise RuntimeError(f"Yahoo error for {ticker}: {chart.get('error')}")
    res = chart["result"][0]
    quote = (res.get("indicators") or {}).get("quote", [{}])[0]
    adj = ((res.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose")
    ts = res.get("timestamp") or []
    frame = pd.DataFrame({"date": pd.to_datetime(ts, unit="s", utc=True).tz_localize(None).normalize(),
                          "open": quote.get("open"), "high": quote.get("high"), "low": quote.get("low"),
                          "close": quote.get("close"), "volume": quote.get("volume"),
                          "adjclose": adj if adj is not None else quote.get("close")})
    frame = frame.set_index("date").sort_index()
    if frame.index.has_duplicates:
        raise RuntimeError(f"Yahoo returned duplicate dates for {ticker}")
    return frame, url


def fetch_fred(sid: str, start: str, end: str) -> tuple[pd.Series, str]:
    url = FRED_URL.format(sid=sid, start=start, end=end)
    df = pd.read_csv(io.BytesIO(http_get(url, headers={})))      # FRED stalls on a browser User-Agent; the default urllib agent answers fast
    df.columns = ["date", sid]
    df["date"] = pd.to_datetime(df["date"])
    df[sid] = pd.to_numeric(df[sid], errors="coerce")
    ser = df.dropna().set_index("date")[sid].astype(float)
    return ser, url


def write_csv(frame: pd.DataFrame | pd.Series, path: Path, label: str = "date") -> dict[str, Any]:
    frame.to_csv(path, index_label=label)
    return {"path": path.name, "rows": int(len(frame)), "sha256": sha256_file(path)}


def parse_shiller(xls_bytes: bytes) -> pd.DataFrame:
    import xlrd  # allowed by the user (pip); only used to read the public Shiller workbook
    book = xlrd.open_workbook(file_contents=xls_bytes)
    sh = book.sheet_by_name("Data")
    rows = []
    for r in range(sh.nrows):
        v = sh.cell_value(r, 0)
        if isinstance(v, float) and 1800 < v < 2100:
            s = f"{v:.2f}"
            year, month = int(s[:4]), int(s[-2:])
            if not 1 <= month <= 12:
                continue
            p, d = sh.cell_value(r, 1), sh.cell_value(r, 2)
            if isinstance(p, float) and isinstance(d, float) and p > 0 and d >= 0:
                rows.append((pd.Timestamp(year=year, month=month, day=1), float(p), float(d)))
    out = pd.DataFrame(rows, columns=["month", "P", "D"]).drop_duplicates("month").set_index("month").sort_index()
    out["dp"] = out["D"] / out["P"]
    return out


def calendar_audit(frame: pd.DataFrame, name: str, expected_first: str) -> dict[str, Any]:
    close = frame["close"]
    idx = frame.index
    info: dict[str, Any] = {"first_date": idx[0].date().isoformat(), "last_date": idx[-1].date().isoformat(), "rows": int(len(frame))}
    info["requested_first_date"] = expected_first
    info["null_or_nonpositive_close_dates"] = [d.date().isoformat() for d in idx[close.isna() | (close <= 0)]]
    info["weekend_dates"] = [d.date().isoformat() for d in idx[idx.dayofweek >= 5]]
    gaps = pd.Series(idx[1:] - idx[:-1], index=idx[1:])
    info["gaps_over_5_calendar_days"] = [{"to": d.date().isoformat(), "days": int(g.days)} for d, g in gaps[gaps > pd.Timedelta(days=5)].items()]
    ret = close.pct_change()
    big = ret[ret.abs() >= 0.15]
    info["abs_return_ge_15pct"] = [{"date": d.date().isoformat(), "ret": float(v), "close": float(close.loc[d])} for d, v in big.items()]
    return info


def collect() -> int:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    proto = check_protocol()
    src: dict[str, Any] = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "end_date": END_DATE,
                           "protocol_lf_sha256": proto["lf_normalized_sha256"],
                           "single_source": "Yahoo chart API for indices; FRED for DTB3; Shiller ie_data.xls (no second source)",
                           "series": {}}
    stop: list[str] = []
    cpv = json.loads(CPV_SOURCES.read_text(encoding="utf-8"))
    sox_path = CPV_DIR / cpv["series"]["SOX"]["csv"]["path"]
    if sha256_file(sox_path) != cpv["series"]["SOX"]["csv"]["sha256"]:
        raise RuntimeError("SOX CSV hash differs from cpv sources JSON")
    sox_idx = pd.read_csv(sox_path, index_col="date", parse_dates=["date"]).index
    old_ndx = pd.read_csv(CPV_DIR / cpv["series"]["NDX"]["csv"]["path"], index_col="date", parse_dates=["date"])["close"]
    frames: dict[str, pd.DataFrame] = {}
    for name, (ticker, first) in SERIES.items():
        try:
            frame, url = fetch_yahoo_raw(ticker, first, END_DATE)
        except Exception as exc:
            stop.append(f"{ticker}: {exc!r}")
            continue
        frames[name] = frame
        info = {"ticker": ticker, "url": url, "single_source": True, "csv": write_csv(frame, INPUT_DIR / f"{name}_yahoo_raw.csv")}
        info.update(calendar_audit(frame, name, first))
        late = frame.index[frame.index >= LATE_START]
        info["late_extra_vs_sox_calendar"] = [d.date().isoformat() for d in late.difference(sox_idx)][:50]
        info["late_missing_vs_sox_calendar"] = [d.date().isoformat() for d in sox_idx.difference(late)][:50]
        info["late_extra_count"] = int(len(late.difference(sox_idx)))
        info["late_missing_count"] = int(len(sox_idx.difference(late)))
        if frame.index[0] != pd.Timestamp(first):
            stop.append(f"{ticker}: first row {info['first_date']} != {first}")
        if info["null_or_nonpositive_close_dates"]:
            stop.append(f"{ticker}: {len(info['null_or_nonpositive_close_dates'])} null/non-positive closes")
        if info["weekend_dates"]:
            stop.append(f"{ticker}: {len(info['weekend_dates'])} weekend dates")
        if info["late_extra_count"] or info["late_missing_count"]:
            stop.append(f"{ticker}: 1994-05-04+ sessions differ from the verified SOX calendar extra={info['late_extra_count']} missing={info['late_missing_count']}")
        if frame.index[-1] != pd.Timestamp(END_DATE):
            stop.append(f"{ticker}: last row {info['last_date']} != {END_DATE}")
        src["series"][name] = info
    if "NDX" in frames:
        new = frames["NDX"]["close"]
        both = new.index.intersection(old_ndx.index)
        diff = (new.loc[both] - old_ndx.loc[both]).abs()
        src["series"]["NDX"]["old_file_close_check"] = {"overlap_rows": int(len(both)), "max_abs_diff": float(diff.max()),
                                                         "rows_with_diff_gt_1e-6": int((diff > 1e-6).sum())}
        if len(both) != len(old_ndx) or (diff > 1e-6).any():
            stop.append("NDX: close differs from the existing cpv NDX file on the 1994-05-04+ overlap")
    if "NDX" in frames and "SPX" in frames:
        a, b = frames["NDX"].index, frames["SPX"].index
        lo, hi = pd.Timestamp("1985-10-01"), pd.Timestamp("1994-05-03")
        ax, bx = a[(a >= lo) & (a <= hi)], b[(b >= lo) & (b <= hi)]
        src["ndx_vs_spx_sessions_1985_1994"] = {"ndx_only": [d.date().isoformat() for d in ax.difference(bx)][:50],
                                                "spx_only": [d.date().isoformat() for d in bx.difference(ax)][:50],
                                                "ndx_only_count": int(len(ax.difference(bx))), "spx_only_count": int(len(bx.difference(ax)))}
    try:
        dtb3, url = fetch_fred("DTB3", "1954-01-01", END_DATE)
        src["dtb3"] = {"url": url, "rows": int(len(dtb3)), "first": dtb3.index[0].date().isoformat(), "last": dtb3.index[-1].date().isoformat(),
                       "csv": write_csv(pd.DataFrame({"DTB3": dtb3}), INPUT_DIR / "DTB3_full.csv")}
        dg = pd.read_csv(CPV_DIR / cpv["treasury"]["csv"]["path"], index_col="date", parse_dates=["date"])["DGS3MO"]
        ov = dtb3.index.intersection(dg.index)
        d_ov = (dtb3.loc[ov] - dg.loc[ov])
        src["dtb3"]["overlap_with_dgs3mo"] = {"rows": int(len(ov)), "mean_diff_pct_points": float(d_ov.mean()), "min": float(d_ov.min()), "max": float(d_ov.max()),
                                             "note": "report only; splice at 1981-09-01 per protocol"}
        if dtb3.index[0] > pd.Timestamp("1954-01-05"):
            stop.append("DTB3 starts after 1954-01-05")
    except Exception as exc:
        stop.append(f"DTB3: {exc!r}")
    try:
        raw = http_get(SHILLER_URLS[0], attempts=4)
        (INPUT_DIR / "shiller_ie_data.xls").write_bytes(raw)
        sh = parse_shiller(raw)
        src["shiller"] = {"url": SHILLER_URLS[0], "xls": {"path": "shiller_ie_data.xls", "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
                          "csv": write_csv(sh, INPUT_DIR / "SHILLER_dividend_yield.csv", "month"), "first_month": sh.index[0].date().isoformat(),
                          "last_month": sh.index[-1].date().isoformat(), "status": "ok"}
    except Exception as exc:
        src["shiller"] = {"status": "unavailable", "error": repr(exc)[:300]}
    src["status"] = "stopped" if stop else "passed"
    src["stop_reasons"] = stop
    SOURCES_JSON.write_text(json.dumps(clean(src), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": src["status"], "stop_reasons": stop, "shiller": src["shiller"].get("status")}, ensure_ascii=False))
    return 2 if stop else 0


def _verify(path: Path, sha: str, label: str) -> None:
    if sha256_file(path) != sha:
        raise RuntimeError(f"{label}: CSV hash differs from its sources JSON")


def load_inputs(with_real: bool = True) -> dict[str, Any]:
    src = json.loads(SOURCES_JSON.read_text(encoding="utf-8"))
    if src.get("status") != "passed":
        raise RuntimeError("input collection did not pass; run --collect")
    cpv = json.loads(CPV_SOURCES.read_text(encoding="utf-8"))
    out: dict[str, Any] = {"sources": src, "cpv_sources": cpv}
    _verify(CPV_DIR / cpv["series"]["SOX"]["csv"]["path"], cpv["series"]["SOX"]["csv"]["sha256"], "SOX")
    out["close"] = {"SOX": pd.read_csv(CPV_DIR / cpv["series"]["SOX"]["csv"]["path"], index_col="date", parse_dates=["date"])["close"].astype(float)}
    for name, key in (("NDX", "N"), ("SPX", "S")):
        info = src["series"][name]["csv"]
        _verify(INPUT_DIR / info["path"], info["sha256"], name)
        out["close"][key] = pd.read_csv(INPUT_DIR / info["path"], index_col="date", parse_dates=["date"])["close"].astype(float)
    _verify(CPV_DIR / cpv["treasury"]["csv"]["path"], cpv["treasury"]["csv"]["sha256"], "DGS3MO")
    dg = pd.read_csv(CPV_DIR / cpv["treasury"]["csv"]["path"], index_col="date", parse_dates=["date"])["DGS3MO"].astype(float)
    _verify(INPUT_DIR / src["dtb3"]["csv"]["path"], src["dtb3"]["csv"]["sha256"], "DTB3")
    dt3 = pd.read_csv(INPUT_DIR / src["dtb3"]["csv"]["path"], index_col="date", parse_dates=["date"])["DTB3"].astype(float)
    splice = pd.Timestamp("1981-09-01")
    out["rate_pct"] = pd.concat([dt3[dt3.index < splice], dg[dg.index >= splice]]).sort_index()
    out["shiller"] = None
    sh = src.get("shiller", {})
    if sh.get("status") == "ok":
        _verify(INPUT_DIR / sh["csv"]["path"], sh["csv"]["sha256"], "Shiller")
        out["shiller"] = pd.read_csv(INPUT_DIR / sh["csv"]["path"], index_col="month", parse_dates=["month"])
    if with_real:
        s4 = json.loads(S4_SOURCES.read_text(encoding="utf-8"))
        real = {}
        for sym in ("SOXL", "SOXX", "QQQ", "TQQQ"):
            c = s4["symbols"][sym]["combined_csv"]
            _verify(S4_DIR / c["path"], c["sha256"], sym)
            real[sym] = pd.read_csv(S4_DIR / c["path"], index_col="date", parse_dates=["date"])["adjclose"].astype(float)
        out["real"] = real
    return out


def dividend_daily(index: pd.DatetimeIndex, sh: pd.DataFrame) -> tuple[pd.Series, int]:
    """Daily dividend = that month's D/P / 252. Sessions after the last Shiller month carry the last value (count returned)."""
    months = index.to_period("M").to_timestamp()
    dp = sh["dp"].reindex(months.unique().union(sh.index)).sort_index().ffill().reindex(months)
    carried = int((index > (sh.index[-1] + pd.offsets.MonthEnd(0))).sum())
    if dp.isna().any():
        raise RuntimeError("Shiller dividend yield missing for some sessions (series starts too late)")
    return pd.Series(dp.values / 252.0, index=index), carried


# ----------------------------------------------------------------------------
# features and engine
# ----------------------------------------------------------------------------
def features(close: pd.Series, rate_pct: pd.Series, er1: float, div_daily: pd.Series | None = None) -> pd.DataFrame:
    """Protocol Appendix A features + sma150/sma250 (neighbors). div_daily adds a daily dividend to the 1x/3x return legs only."""
    d = pd.DataFrame({"px": close})
    d["rate"] = rate_pct.reindex(close.index.union(rate_pct.index)).ffill().reindex(close.index) / 100.0
    d["r"] = d["px"].pct_change()
    d["rc"] = d["rate"] / 252.0
    rt = d["r"] if div_daily is None else d["r"] + div_daily.reindex(close.index)
    d["r3"] = 3 * rt - 0.0095 / 252 - 2 * d["rc"]
    d["r1"] = rt - er1 / 252
    d = d.iloc[1:].copy()
    if d["rate"].isna().any() or d["r3"].isna().any():
        raise RuntimeError("rate/return is NaN for some session (no rate before first observation?)")
    d["sig20"] = d["r"].rolling(20).std()
    d["sig_med"] = d["sig20"].expanding(min_periods=120).median() * np.sqrt(252)
    d["dd252"] = d["px"] / d["px"].rolling(252, min_periods=1).max() - 1
    d["sma200"] = d["px"].rolling(200).mean()
    d["ext"] = d["px"] / d["sma200"] - 1
    d["sma150"] = d["px"].rolling(150).mean()
    d["sma250"] = d["px"].rolling(250).mean()
    return d


class Feat:
    """Python-list view of a feature frame (fast scalar access in the engine loop)."""

    def __init__(self, d: pd.DataFrame):
        self.d = d
        self.n = len(d)
        self.idx = d.index
        self.L = {c: d[c].tolist() for c in ("px", "sig_med", "dd252", "sma150", "sma200", "sma250", "ext", "r3", "r1", "rate")}
        self.rc = {"usd0": [0.0] * self.n, "tbill": (d["rate"] / 252.0).tolist()}


def fixed(L: float) -> dict[str, Any]:
    return {"kind": "fixed", "L": L}


def G(base=1.0, extra=0.5, trend=True, overheat=False, brake=None, off=0.80, on=0.90, L=252, k_hot=1.0, k_cool=0.5, ma="sma200") -> dict[str, Any]:
    return {"kind": "G", "base": base, "extra": extra, "trend": trend, "overheat": overheat, "brake": brake, "off": off, "on": on,
            "L": L, "k_hot": k_hot, "k_cool": k_cool, "ma": ma}


def X1(add=0.5, k_dd=0.75, k_reb=1.2, k_stop=0.45, k_exit=0.30) -> dict[str, Any]:
    return {"kind": "X1", "add": add, "k_dd": k_dd, "k_reb": k_reb, "k_stop": k_stop, "k_exit": k_exit}


def SEQ(seq: list[float]) -> dict[str, Any]:  # tests only
    return {"kind": "SEQ", "seq": list(seq)}


def make_target(spec: dict[str, Any], L: dict[str, list[float]], stats: dict[str, int]):
    """Per-run target function f(i, e) -> target exposure X* (reads only data up to index i)."""
    kind = spec["kind"]
    if kind == "fixed":
        v = spec["L"]
        return lambda i, e: v
    if kind == "SEQ":
        seq = spec["seq"]
        return lambda i, e: seq[i]
    px, sig, ext = L["px"], L["sig_med"], L["ext"]
    if kind == "G":
        base, extra, trend, overheat, brake = spec["base"], spec["extra"], spec["trend"], spec["overheat"], spec["brake"]
        off, on, Lw, k_hot, k_cool = spec["off"], spec["on"], spec["L"], spec["k_hot"], spec["k_cool"]
        sma = L[spec["ma"]]
        dq: collections.deque = collections.deque()
        state = {"gate": True, "hot": False}

        def f(i, e):
            while dq and dq[-1][1] <= e:
                dq.pop()
            dq.append((i, e))
            if Lw is not None:
                while dq[0][0] <= i - Lw:
                    dq.popleft()
            hw = dq[0][1]
            if e < off * hw:
                if state["gate"]:
                    stats["gate_off"] += 1
                state["gate"] = False
            elif e >= on * hw:
                state["gate"] = True
            gate = state["gate"]
            if overheat:
                x, s = ext[i], sig[i]
                if x == x and s == s:
                    if x >= k_hot * s:
                        state["hot"] = True
                    elif x <= k_cool * s:
                        state["hot"] = False
            if trend:
                m = sma[i]
                tr = (m == m) and px[i] > m
            else:
                tr = True
            b = base if (gate or brake is None) else brake
            return b + (extra if (tr and gate and not state["hot"]) else 0.0)
        return f
    if kind == "X1":
        add, k_dd, k_reb, k_stop, k_exit = spec["add"], spec["k_dd"], spec["k_reb"], spec["k_stop"], spec["k_exit"]
        dd252 = L["dd252"]
        st = {"cool": False, "lvl": 0.0, "entry": 0.0, "trough": 0.0, "s0": 0.0}

        def f(i, e):
            dd, p, sm = dd252[i], px[i], sig[i]
            if dd != dd or sm != sm:
                return 1.0
            if st["cool"]:
                if dd >= -k_exit * sm:
                    st["cool"] = False
                return 1.0
            lvl = st["lvl"]
            if lvl == 0.0 and dd <= -k_dd * sm:
                lvl = add
                st["entry"] = p
                st["trough"] = p
                st["s0"] = sm
                stats["x1_entry"] += 1
            if lvl > 0:
                st["trough"] = min(st["trough"], p)
                s0 = st["s0"]
                if dd >= -k_exit * s0 or p >= st["trough"] * (1 + k_reb * s0) or p <= st["entry"] * (1 - k_stop * s0):
                    lvl = 0.0
                    st["cool"] = True
            st["lvl"] = lvl
            return 1.0 + lvl
        return f
    raise ValueError(f"unknown spec kind {kind}")


def simulate(F: Feat, spec: dict[str, Any], band: float, cost: float, impl: str, cash: str = "usd0",
             lev_ret: list[float] | None = None, one_ret: list[float] | None = None) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
    """impl 'core' = ETF core (3x (X-1)/2 + 1x rest, X<1 -> 1x X + cash); impl 'cash3' = X/3 in 3x + cash.
    Decide at close t, fill at close t+1. Same arithmetic order as the protocol Appendix A engine."""
    n = F.n
    rL = F.L["r3"] if lev_ret is None else lev_ret
    r1 = F.L["r1"] if one_ret is None else one_ret
    rc = F.rc[cash]
    stats = {"gate_off": 0, "x1_entry": 0}
    f = make_target(spec, F.L, stats)
    E = [0.0] * n
    X = [0.0] * n
    e = 1.0
    pend = None
    ntr = 0
    nup = 0
    prev_up = False
    bm = band - 1e-12
    if impl == "core":
        wl = wx = None
        for i in range(n):
            if i > 0:
                gl = wl * (1 + rL[i])
                gx = wx * (1 + r1[i])
                gc = (1 - wl - wx) * (1 + rc[i])
                tot = gl + gx + gc
                e *= tot
                wl, wx = gl / tot, gx / tot
            if pend is not None:
                if pend >= 1:
                    tl, tx = (pend - 1) / 2, 1 - (pend - 1) / 2
                else:
                    tl, tx = 0.0, pend
                if wl is None:
                    wl, wx = tl, tx
                    e -= e * cost * (tl + tx)
                elif abs(tl - wl) >= bm or abs(tx - wx) >= bm or (tl == 0 < wl) or (wl == 0 < tl):
                    e -= e * cost * (abs(tl - wl) + abs(tx - wx))
                    wl, wx = tl, tx
                    ntr += 1
            if wl is None:
                wl, wx = 0.0, 0.0
            E[i] = e
            X[i] = 3 * wl + wx
            pend = f(i, e)
            if pend < 0.0:
                pend = 0.0
            up = pend > 1.0 + 1e-12
            if up and not prev_up:
                nup += 1
            prev_up = up
    elif impl == "cash3":
        w = None
        for i in range(n):
            if i > 0:
                gl = w * (1 + rL[i])
                gc = (1 - w) * (1 + rc[i])
                e = e * (gl + gc)
                w = gl / (gl + gc)
            if pend is not None:
                if w is None:
                    w = pend
                    e -= e * cost * pend
                elif abs(pend - w) >= bm or (pend == 0 < w) or (w == 0 < pend):
                    e -= e * cost * abs(pend - w)
                    w = pend
                    ntr += 1
            if w is None:
                w = 0.0
            E[i] = e
            X[i] = 3 * w
            t = f(i, e)
            up = t > 1.0 + 1e-12
            if up and not prev_up:
                nup += 1
            prev_up = up
            pend = min(1.0, max(0.0, t / 3.0))
    else:
        raise ValueError(impl)
    stats["ntr"] = ntr
    stats["nup"] = nup
    return np.asarray(E), np.asarray(X), stats


# ----------------------------------------------------------------------------
# metrics
# ----------------------------------------------------------------------------
def cagr_of(S: np.ndarray, nsess: int) -> float:
    r = S[-1] / S[0]
    return float(r ** (252.0 / nsess) - 1.0) if r > 0 else -1.0


def mdd_of(S: np.ndarray) -> float:
    return float((S / np.maximum.accumulate(S) - 1.0).min())


def dd20_count(S: np.ndarray) -> int:
    M = np.maximum.accumulate(S)
    newhigh = np.zeros(len(S), dtype=bool)
    newhigh[1:] = M[1:] > M[:-1]
    grp = np.cumsum(newhigh)
    below = (S / M - 1.0) <= -0.20
    return int(np.unique(grp[below]).size)


def window_stats(T: np.ndarray, L: int) -> tuple[float, float, float, float]:
    """(median, worst, path-min <= -20% fraction, end <= -20% fraction) of L-session windows fully inside T."""
    m = len(T) - L
    if m <= 0:
        return (float("nan"),) * 4
    ret = T[L:] / T[:m] - 1.0
    pm = sliding_window_view(T, L + 1).min(axis=1) / T[:m] - 1.0
    return float(np.median(ret)), float(ret.min()), float((pm <= -0.20).mean()), float((ret <= -0.20).mean())


def seg_metrics(E: np.ndarray, X: np.ndarray, a: int, b: int) -> tuple[float, ...]:
    """Metrics for sessions a..b-1 of a continuous run. Base = close before session a (E[0]=1 for a=0)."""
    n = b - a
    if n <= 1:
        return (float("nan"),) * (len(METRIC_COLS) - 1) + (float(n),)
    S = E[a:b] / 1.0 if a == 0 else np.concatenate(([1.0], E[a:b] / E[a - 1]))
    T = E[a:b]
    w1 = window_stats(T, 252)
    w3 = window_stats(T, 756)
    return (cagr_of(S, n), mdd_of(S), w1[1], w1[0], w1[2], w1[3], w3[1], w3[0], w3[2], w3[3], float(X[a:b].mean()), float(dd20_count(S)), float(n))


def period_growth(E: np.ndarray, a: int, b: int) -> tuple[float, float]:
    base = 1.0 if a == 0 else E[a - 1]
    return float(math.log(E[b - 1] / base)), float(b - a)


def seg_bounds(idx: pd.DatetimeIndex, market: str) -> dict[str, tuple[int, int]]:
    n = len(idx)
    ss = lambda ts: int(idx.searchsorted(ts, side="left"))
    early_end = ss(EARLY_END[market] + pd.Timedelta(days=1))
    out = {"full": (0, n), "early": (0, early_end), "post": (ss(POST_START), n)}
    if market != "SOX":
        out["late"] = (ss(LATE_START), n)
    return out


def period_bounds(idx: pd.DatetimeIndex, market: str) -> dict[str, tuple[int, int]]:
    out = {}
    for name, lo, hi in PERIODS[market]:
        a = int(idx.searchsorted(pd.Timestamp(lo), side="left"))
        b = int(idx.searchsorted(pd.Timestamp(hi) + pd.Timedelta(days=1), side="left"))
        if b - a > 1:
            out[name] = (a, b)
    return out


def base_market(market: str) -> str:
    return "S" if market == "S_TR" else market      # S_TR = SPX with Shiller dividends (G1/G4/G6 return criteria)


def row_columns(market: str) -> list[str]:
    market = base_market(market)
    cols = ["market", "cand", "impl", "cost", "cash", "band", "shift", "n_sessions", "adj_per_year", "nup", "gate_off", "x1_entry"]
    for s in SEG_NAMES[market]:
        cols += [f"{s}__{m}" for m in METRIC_COLS]
    for name, _, _ in PERIODS[market]:
        cols += [f"per__{name}__g", f"per__{name}__n"]
    return cols


def make_row(market: str, label: str, impl: str, cost: float, cash: str, band: float, shift: int, F: Feat,
             E: np.ndarray, X: np.ndarray, stats: dict[str, int], segs: dict[str, tuple[int, int]], pers: dict[str, tuple[int, int]]) -> list[Any]:
    years = F.n / 252.0
    row: list[Any] = [market, label, impl, cost, cash, band, shift, F.n, max(stats["ntr"] - 1, 0) / years, stats["nup"], stats["gate_off"], stats["x1_entry"]]
    base = base_market(market)
    for s in SEG_NAMES[base]:
        a, b = segs[s]
        row += list(seg_metrics(E, X, a, b))
    for name, _, _ in PERIODS[base]:
        if name in pers:
            row += list(period_growth(E, *pers[name]))
        else:
            row += [float("nan"), 0.0]
    return row


# ----------------------------------------------------------------------------
# candidate registry (fixed by the protocol)
# ----------------------------------------------------------------------------
def build_registry() -> dict[str, dict[str, Any]]:
    R: dict[str, dict[str, Any]] = {
        "B0": fixed(1.0),
        "T1": G(1.0, 0.5),
        "T2": G(1.0, 0.5, overheat=True),
        "F1.32": fixed(1.32),
        "K132-G": G(1.32, 0.0, trend=False, brake=1.0),
        "T2-132b": G(1.32, 0.5, overheat=True, brake=1.0),
        "X1": X1(),
    }
    nb: dict[str, dict[str, Any]] = {}
    nb["T1|sma150"] = G(1.0, 0.5, ma="sma150")
    nb["T1|sma250"] = G(1.0, 0.5, ma="sma250")
    nb["T1|add0.25"] = G(1.0, 0.25)
    nb["T1|add0.75"] = G(1.0, 0.75)
    nb["T1|gate0.75/0.85"] = G(1.0, 0.5, off=0.75, on=0.85)
    nb["T1|gate0.85/0.95"] = G(1.0, 0.5, off=0.85, on=0.95)
    nb["T1|win126"] = G(1.0, 0.5, L=126)
    nb["T1|win504"] = G(1.0, 0.5, L=504)
    nb["T2|hot0.75"] = G(1.0, 0.5, overheat=True, k_hot=0.75, k_cool=0.375)
    nb["T2|hot1.25"] = G(1.0, 0.5, overheat=True, k_hot=1.25, k_cool=0.625)
    nb["K132-G|base1.25"] = G(1.25, 0.0, trend=False, brake=1.0)
    nb["K132-G|base1.40"] = G(1.40, 0.0, trend=False, brake=1.0)
    nb["K132-G|gate0.75/0.85"] = G(1.32, 0.0, trend=False, brake=1.0, off=0.75, on=0.85)
    nb["K132-G|gate0.85/0.95"] = G(1.32, 0.0, trend=False, brake=1.0, off=0.85, on=0.95)
    nb["T2-132b|base1.25"] = G(1.25, 0.5, overheat=True, brake=1.0)
    nb["T2-132b|base1.40"] = G(1.40, 0.5, overheat=True, brake=1.0)
    nb["T2-132b|gate0.75/0.85"] = G(1.32, 0.5, overheat=True, brake=1.0, off=0.75, on=0.85)
    nb["T2-132b|gate0.85/0.95"] = G(1.32, 0.5, overheat=True, brake=1.0, off=0.85, on=0.95)
    nb["T2-132b|hot0.75"] = G(1.32, 0.5, overheat=True, brake=1.0, k_hot=0.75, k_cool=0.375)
    nb["T2-132b|hot1.25"] = G(1.32, 0.5, overheat=True, brake=1.0, k_hot=1.25, k_cool=0.625)
    nb["X1|enter0.5"] = X1(k_dd=0.5)
    nb["X1|enter1.0"] = X1(k_dd=1.0)
    nb["X1|stop0.30"] = X1(k_stop=0.30)
    nb["X1|stop0.60"] = X1(k_stop=0.60)
    nb["X1|exit0.9"] = X1(k_reb=0.9)
    nb["X1|exit1.5"] = X1(k_reb=1.5)
    nb["X1|nostop"] = X1(k_stop=1e9)
    R.update(nb)
    R["F1.32|1.25"] = fixed(1.25)          # report only (fixed multiple)
    R["F1.32|1.40"] = fixed(1.40)
    R["REF|fixed1.25"] = fixed(1.25)       # report only
    R["REF|fixed1.5"] = fixed(1.5)
    R["REF|T1_nogate"] = G(1.0, 0.5, off=0.0, on=0.0)
    R["REF|T2_nogate"] = G(1.0, 0.5, overheat=True, off=0.0, on=0.0)
    R["REF|T1_fullHWM"] = G(1.0, 0.5, L=None)
    R["REF|T2-132_nobrake"] = G(1.32, 0.5, overheat=True, brake=None)
    return R


REGISTRY = build_registry()
NEIGHBORS = {c: [k for k in REGISTRY if k.startswith(c + "|")] for c in MAIN}      # judged (F1.32 neighbors are report only)
JUDGED_NEIGHBORS = {c: v for c, v in NEIGHBORS.items() if c != "F1.32"}
REF_LABELS = [k for k in REGISTRY if k.startswith("REF|")]


def spec_for(label: str) -> dict[str, Any]:
    if label.startswith("FIX|"):
        return fixed(float(label.split("|", 1)[1]))
    return REGISTRY[label]


# ----------------------------------------------------------------------------
# (--run part is appended below; see run_study)
# ----------------------------------------------------------------------------
_W: dict[str, Any] = {}


def _init_worker() -> None:
    inp = load_inputs(with_real=False)
    _W["close"] = inp["close"]
    _W["rate"] = inp["rate_pct"]
    _W["div"] = None
    if inp["shiller"] is not None:
        _W["div"], _ = dividend_daily(inp["close"]["S"].index, inp["shiller"])
    _W["key"] = None
    _W["F"] = None


def get_feat(market: str, shift: int) -> Feat:
    key = (market, shift)
    if _W.get("key") == key:
        return _W["F"]
    base = base_market(market)
    close = _W["close"][base].iloc[shift:]
    d = features(close, _W["rate"], FEE1[base], _W["div"] if market == "S_TR" else None)
    F = Feat(d)
    F.segs = seg_bounds(F.idx, base)
    F.pers = period_bounds(F.idx, base)
    _W["key"], _W["F"] = key, F
    return F


def run_chunk(task: tuple[str, int, tuple[float, ...], list[tuple[str, str, float, str]]]) -> tuple[str, list[list[Any]]]:
    market, shift, bands, jobs = task
    F = get_feat(market, shift)
    rows = []
    for band in bands:
        for label, impl, cost, cash in jobs:
            E, X, st = simulate(F, spec_for(label), band, cost, impl, cash=cash)
            rows.append(make_row(market, label, impl, cost, cash, band, shift, F, E, X, st, F.segs, F.pers))
    return market, rows


def phase1_jobs(market: str) -> list[tuple[str, str, float, str]]:
    jobs: list[tuple[str, str, float, str]] = []
    if market in MARKETS:
        for c in CAND_ORDER:
            jobs += [(c, "core", COST, "usd0"), (c, "cash3", COST, "usd0")]
        for cost in COSTS[1:]:
            jobs += [(c, "core", cost, "usd0") for c in CAND_ORDER]
        for c in MAIN:
            jobs += [(k, "core", COST, "usd0") for k in NEIGHBORS[c]]
        jobs += [(k, "core", COST, "usd0") for k in REF_LABELS]
    else:  # S_TR: dividend-corrected SPX for the return criteria of G1/G4/G6
        for cost in COSTS:
            jobs += [(c, "core", cost, "usd0") for c in CAND_ORDER]
        for c in MAIN:
            if c != "F1.32":
                jobs += [(k, "core", COST, "usd0") for k in JUDGED_NEIGHBORS[c]]
    return jobs


def dispatch(pool, tasks: list[Any], label: str) -> dict[str, pd.DataFrame]:
    rows: dict[str, list[list[Any]]] = collections.defaultdict(list)
    t0 = time.time()
    for k, (market, part) in enumerate(pool.imap_unordered(run_chunk, tasks, chunksize=1), 1):
        rows[market] += part
        if k % 10 == 0 or k == len(tasks):
            print(f"[{label}] {k}/{len(tasks)} chunks, {time.time() - t0:.0f}s", flush=True)
    return {m: pd.DataFrame(r, columns=row_columns(m)) for m, r in rows.items()}


# ----------------------------------------------------------------------------
# aggregation helpers
# ----------------------------------------------------------------------------
def sel(df: pd.DataFrame, cand: str, impl: str = "core", cost: float = COST, cash: str = "usd0") -> pd.DataFrame:
    m = (df["cand"].values == cand) & (df["impl"].values == impl) & (df["cost"].values == cost) & (df["cash"].values == cash)
    return df[m].set_index(["band", "shift"]).sort_index()


def delta(df: pd.DataFrame, cand: str, col: str, base: str = "B0", impl: str = "core", cost: float = COST, cash: str = "usd0") -> pd.Series:
    a, b = sel(df, cand, impl, cost, cash)[col], sel(df, base, impl, cost, cash)[col]
    if len(a) != len(BANDS) * len(SHIFTS) or not a.index.equals(b.index):
        raise RuntimeError(f"pairing mismatch for {cand}/{base} {impl} {cost} {cash}: {len(a)} vs {len(b)}")
    return a - b


def tri(vals: list[Any]) -> bool | None:
    if any(v is False for v in vals):
        return False
    if any(v is None for v in vals):
        return None
    return True


def g1_eval(dfs: dict[str, pd.DataFrame], tr_ok: bool, c: str, cost: float = COST) -> dict[str, Any]:
    res: dict[str, Any] = {}
    for mk in ("N", "S"):
        if mk == "S" and not tr_ok:
            res[mk] = None
            continue
        df = dfs["S_TR"] if (mk == "S" and tr_ok) else dfs[mk]
        dd = delta(df, c, "full__cagr", cost=cost)
        res[mk] = {"mean": float(dd.mean()), "frac_nonneg": float((dd >= 0).mean()), "ok": bool(dd.mean() >= 0.005 and (dd >= 0).mean() >= 0.70)}
    res["ok"] = tri([None if res[m] is None else res[m]["ok"] for m in ("N", "S")])
    return res


def g3_eval(dfs: dict[str, pd.DataFrame], c: str) -> dict[str, Any]:
    res: dict[str, Any] = {}
    for mk in MARKETS:
        for seg in ("full", "post"):
            dm = delta(dfs[mk], c, f"{seg}__mdd")
            dw = delta(dfs[mk], c, f"{seg}__w1_min")
            res[f"{mk}_{seg}"] = {"mdd_diff": float(dm.mean()), "w1_worst_diff": float(dw.mean()),
                                  "ok": bool(dm.mean() >= -0.15 and dw.mean() >= -0.15)}
    res["ok"] = all(v["ok"] for k, v in res.items() if k != "ok")
    return res


def g4_eval(dfs: dict[str, pd.DataFrame], tr_ok: bool, c: str) -> dict[str, Any]:
    res: dict[str, Any] = {}
    n_cagr = delta(dfs["N"], c, "early__cagr").mean()
    n_mdd = delta(dfs["N"], c, "early__mdd").mean()
    res["N0"] = {"cagr_diff": float(n_cagr), "mdd_diff": float(n_mdd), "ok": bool(n_cagr >= -0.005 and n_mdd >= -0.15)}
    s_mdd = delta(dfs["S"], c, "early__mdd").mean()
    s_price_cagr = delta(dfs["S"], c, "early__cagr").mean()
    if tr_ok:
        s_cagr = delta(dfs["S_TR"], c, "early__cagr").mean()
        ok = bool(s_cagr >= -0.005 and s_mdd >= -0.15)
    else:
        s_cagr = None
        ok = False if s_mdd < -0.15 else None
    res["S0"] = {"cagr_diff": None if s_cagr is None else float(s_cagr), "cagr_diff_price": float(s_price_cagr), "mdd_diff": float(s_mdd), "ok": ok}
    res["ok"] = tri([res["N0"]["ok"], res["S0"]["ok"]])
    return res


def g7_eval(dfs: dict[str, pd.DataFrame], c: str) -> dict[str, Any]:
    res: dict[str, Any] = {}
    for mk in ("N", "S"):
        ex = {}
        a, b = sel(dfs[mk], c), sel(dfs[mk], "B0")
        for name, _, _ in PERIODS[mk]:
            diff = (a[f"per__{name}__g"] - b[f"per__{name}__g"]).to_numpy()
            ex[name] = float(np.nanmean(diff)) if np.isfinite(diff).any() else float("nan")
        pos = {k: max(v, 0.0) for k, v in ex.items() if not math.isnan(v)}
        tot = sum(pos.values())
        share = (max(pos.values()) / tot) if tot > 0 else 0.0
        top = max(pos, key=pos.get) if tot > 0 else None
        res[mk] = {"log_excess": ex, "top_period": top, "top_share": share, "ok": bool(share <= 0.50)}
    res["ok"] = all(res[m]["ok"] for m in ("N", "S"))
    return res


def verdict_of(g: dict[str, Any]) -> str:
    if g["G3"] is False or g["G4"] is False:
        return "기각"
    if any(v is False for v in g.values()):
        return "검토 전용"
    if any(v is None for v in g.values()):
        return "검토 전용(판정 불가 항목 있음)"
    return "S5 제안 후보(forward shadow 필요)"


def evaluate_gates(dfs: dict[str, pd.DataFrame], tr_ok: bool, fixm: dict[tuple[str, str], float]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for c in MAIN:
        d: dict[str, Any] = {}
        d["G1"] = g1_eval(dfs, tr_ok, c)
        if c == "F1.32":
            d["G2"] = {"ok": True, "note": "해당 없음(고정 배수)"}
        else:
            g2: dict[str, Any] = {}
            for mk in ("N", "S"):
                m = fixm[(c, mk)]
                a, f = sel(dfs[mk], c), sel(dfs[mk], f"FIX|{m:.2f}")
                g2[mk] = {"fixed_multiple": m, "cagr_c": float(a["full__cagr"].mean()), "cagr_fixed": float(f["full__cagr"].mean()),
                          "mdd_c": float(a["full__mdd"].mean()), "mdd_fixed": float(f["full__mdd"].mean()),
                          "ok": bool(a["full__cagr"].mean() >= f["full__cagr"].mean() and a["full__mdd"].mean() >= f["full__mdd"].mean())}
            g2["ok"] = all(g2[m]["ok"] for m in ("N", "S"))
            d["G2"] = g2
        d["G3"] = g3_eval(dfs, c)
        d["G4"] = g4_eval(dfs, tr_ok, c)
        if c == "F1.32":
            d["G5"] = {"ok": True, "note": "해당 없음(고정 배수, 이웃은 보고만)"}
        else:
            nbs = {}
            for nb in JUDGED_NEIGHBORS[c]:
                g1n, g3n = g1_eval(dfs, tr_ok, nb), g3_eval(dfs, nb)
                nbs[nb] = {"G1": g1n["ok"], "G3": g3n["ok"], "pass": tri([g1n["ok"], g3n["ok"]]),
                           "G1_N": g1n["N"], "G1_S": g1n["S"], "G3_detail": {k: v for k, v in g3n.items() if k != "ok"}}
            t = sum(1 for v in nbs.values() if v["pass"] is True)
            f = sum(1 for v in nbs.values() if v["pass"] is False)
            n = len(nbs)
            ok5 = True if t > n / 2 else (False if f >= n / 2 else None)
            d["G5"] = {"ok": ok5, "n": n, "passed": t, "failed": f, "undetermined": n - t - f, "neighbors": nbs}
        g6_20 = g1_eval(dfs, tr_ok, c, cost=COSTS[1])
        g6_50 = {}
        for mk in ("N", "S"):
            if mk == "S" and not tr_ok:
                g6_50[mk] = None
                continue
            df = dfs["S_TR"] if (mk == "S" and tr_ok) else dfs[mk]
            dd = delta(df, c, "full__cagr", cost=COSTS[2])
            g6_50[mk] = {"mean": float(dd.mean()), "ok": bool(dd.mean() >= 0)}
        d["G6"] = {"bp20_G1": g6_20, "bp50": g6_50,
                   "ok": tri([g6_20["ok"]] + [None if g6_50[m] is None else g6_50[m]["ok"] for m in ("N", "S")])}
        d["G7"] = g7_eval(dfs, c)
        flat = {k: d[k]["ok"] for k in ("G1", "G2", "G3", "G4", "G5", "G6", "G7")}
        d["flat"] = flat
        d["verdict"] = verdict_of(flat)
        out[c] = d
    return out


def i1_eval(dfs: dict[str, pd.DataFrame]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for c in CAND_ORDER:
        per: dict[str, Any] = {}
        for mk in MARKETS:
            a, b = sel(dfs[mk], c, "core"), sel(dfs[mk], c, "cash3")
            dc = float((a["full__cagr"] - b["full__cagr"]).mean())
            dm = float((a["full__mdd"] - b["full__mdd"]).mean())
            per[mk] = {"cagr_core": float(a["full__cagr"].mean()), "cagr_cash3": float(b["full__cagr"].mean()), "cagr_diff": dc,
                       "mdd_core": float(a["full__mdd"].mean()), "mdd_cash3": float(b["full__mdd"].mean()), "mdd_diff": dm,
                       "ok": bool(dc > 0 and dm >= -0.02)}
        out[c] = {"markets": per, "ok": all(per[m]["ok"] for m in MARKETS)}
    return out


def pair_summary(dfs: dict[str, pd.DataFrame], labels: list[str], impl: str = "core", cost: float = COST, cash: str = "usd0") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for mk in MARKETS:
        out[mk] = {}
        for c in labels:
            a = sel(dfs[mk], c, impl, cost, cash)
            ent: dict[str, Any] = {"adj_per_year": float(a["adj_per_year"].mean()), "mean_exposure": float(a["full__meanx"].mean()),
                                   "level_cagr_full": float(a["full__cagr"].mean()), "level_mdd_full": float(a["full__mdd"].mean())}
            for seg in SEG_NAMES[mk]:
                for met in ("cagr", "mdd", "w1_min", "w3_min"):
                    d = delta(dfs[mk], c, f"{seg}__{met}", impl=impl, cost=cost, cash=cash)
                    ent[f"{seg}__d_{met}"] = {"mean": float(d.mean()), "min": float(d.min()), "max": float(d.max()),
                                              "frac_nonneg": float((d >= 0).mean())}
                lv = a[f"{seg}__cagr"]
                ent[f"{seg}__level"] = {"cagr": float(lv.mean()), "mdd": float(a[f"{seg}__mdd"].mean()), "w1_med": float(a[f"{seg}__w1_med"].mean()),
                                        "w1_min": float(a[f"{seg}__w1_min"].mean()), "w1_pathfrac": float(a[f"{seg}__w1_pathfrac"].mean()),
                                        "w1_endfrac": float(a[f"{seg}__w1_endfrac"].mean()), "w3_med": float(a[f"{seg}__w3_med"].mean()),
                                        "w3_min": float(a[f"{seg}__w3_min"].mean()), "w3_pathfrac": float(a[f"{seg}__w3_pathfrac"].mean()),
                                        "w3_endfrac": float(a[f"{seg}__w3_endfrac"].mean()),
                                        "dd20n": float(a[f"{seg}__dd20n"].mean())}
            out[mk][c] = ent
    return out


def period_table(dfs: dict[str, pd.DataFrame], mk: str, labels: list[str], df_src: pd.DataFrame | None = None) -> dict[str, Any]:
    df = dfs[mk] if df_src is None else df_src
    out: dict[str, Any] = {}
    b0 = sel(df, "B0")
    for name, _, _ in PERIODS[mk]:
        g0, n0 = b0[f"per__{name}__g"], b0[f"per__{name}__n"]
        ent = {"B0_cagr": float(np.nanmean(np.exp(g0 * 252.0 / n0) - 1.0))}
        for c in labels:
            a = sel(df, c)
            gc, nc = a[f"per__{name}__g"], a[f"per__{name}__n"]
            ent[c] = float(np.nanmean((np.exp(gc * 252.0 / nc) - 1.0) - (np.exp(g0 * 252.0 / n0) - 1.0)))
        out[name] = ent
    return out


def crash_events(F: Feat) -> list[dict[str, int]]:
    px = np.asarray(F.L["px"])
    dd = np.asarray(F.L["dd252"])
    n = len(px)
    ev = []
    i = 0
    while i < n:
        if dd[i] <= -0.30:
            lo = max(0, i - 251)
            pk = lo + int(np.argmax(px[lo:i + 1]))
            k = i + 1
            while k < n and dd[k] <= -0.10:
                k += 1
            end = min(k, n - 1)
            tr = i + int(np.argmin(px[i:end + 1]))
            ev.append({"peak": pk, "start": i, "trough": tr, "end": end})
            i = end + 1
        else:
            i += 1
    return ev


def crash_table(inputs: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for mk in MARKETS:
        d = features(inputs["close"][mk], inputs["rate_pct"], FEE1[mk])
        F = Feat(d)
        Es = {c: simulate(F, REGISTRY[c], 0.10, COST, "core")[0] for c in CAND_ORDER}
        rows = []
        for e in crash_events(F):
            pk, tr = e["peak"], e["trough"]
            px = F.L["px"]
            row = {"peak": F.idx[pk].date().isoformat(), "start": F.idx[e["start"]].date().isoformat(), "trough": F.idx[tr].date().isoformat(),
                   "end": F.idx[e["end"]].date().isoformat(), "index_dd": px[tr] / px[pk] - 1.0,
                   "index_after1y": (px[tr + 252] / px[tr] - 1.0) if tr + 252 < F.n else None, "cands": {}}
            for c, E in Es.items():
                row["cands"][c] = {"dd": float(E[tr] / E[pk] - 1.0), "after1y": float(E[tr + 252] / E[tr] - 1.0) if tr + 252 < F.n else None}
            rows.append(row)
        out[mk] = rows
    return out


def current_conditions(inputs: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for mk in MARKETS:
        d = features(inputs["close"][mk], inputs["rate_pct"], FEE1[mk])
        r = d.iloc[-1]
        out[mk] = {"date": d.index[-1].date().isoformat(), "close": float(r["px"]), "sma200": float(r["sma200"]), "ext": float(r["ext"]),
                   "sigma_median": float(r["sig_med"]), "overheat_if_ext_ge_sigma_median": bool(r["ext"] >= r["sig_med"]),
                   "above_sma200": bool(r["px"] > r["sma200"]), "dd252": float(r["dd252"]), "sig20_annual": float(d["r"].iloc[-20:].std() * math.sqrt(252))}
    return out


def real_products(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    pairs = (("SOX", "SOXL", "SOXX", POST_START), ("N", "TQQQ", "QQQ", None))
    for mk, p3, p1, start in pairs:
        d = features(inputs["close"][mk], inputs["rate_pct"], FEE1[mk])
        s = start or max(inputs["real"][p3].index[0], inputs["real"][p1].index[0])
        ds = d.loc[s:]
        lr = inputs["real"][p3].pct_change().reindex(ds.index)
        ro = inputs["real"][p1].pct_change().reindex(ds.index)
        miss = int(lr.iloc[1:].isna().sum() + ro.iloc[1:].isna().sum())
        if miss:
            out.append({"pair": f"{p3}/{p1}", "error": f"{miss} NaN returns after alignment with {mk} sessions"})
            continue
        F = Feat(ds)
        lrl, rol = lr.fillna(0.0).tolist(), ro.fillna(0.0).tolist()
        for c in CAND_ORDER:
            for impl in ("core", "cash3"):
                E, X, st = simulate(F, REGISTRY[c], 0.10, COST, impl, lev_ret=lrl, one_ret=rol)
                m = seg_metrics(E, X, 0, len(E))
                out.append({"pair": f"{p3}/{p1}", "start": ds.index[0].date().isoformat(), "end": ds.index[-1].date().isoformat(), "cand": c, "impl": impl,
                            "cagr": m[0], "mdd": m[1], "w1_min": m[2], "w1_med": m[3], "mean_exposure": m[10], "adj_per_year": max(st["ntr"] - 1, 0) / (len(E) / 252)})
    return out


def optimal_table(opt: dict[str, pd.DataFrame]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    segs = {"SOX": [("전체", "full"), ("1994~2010", "early"), ("2010~", "post"), ("2021~2025", "per:2021-25")],
            "N": [("전체", "full"), ("N0", "early"), ("N1", "late")], "S": [("전체", "full"), ("S0", "early"), ("S1", "late")]}
    for mk, df in opt.items():
        df = df.copy()
        df["m"] = df["cand"].str.split("|").str[1].astype(float)
        df = df.sort_values("m")
        out[mk] = {}
        for label, key in segs[mk]:
            if key.startswith("per:"):
                nm = key[4:]
                cagr = np.exp(df[f"per__{nm}__g"] * 252.0 / df[f"per__{nm}__n"]) - 1.0
            else:
                cagr = df[f"{key}__cagr"]
            cagr = cagr.set_axis(df["m"].round(2).values)
            best = float(cagr.idxmax())
            bv = float(cagr.max())
            share = lambda m: (float(cagr.loc[round(m, 2)]) / bv) if bv > 0 else None
            out[mk][label] = {"best_multiple": best, "best_cagr": bv, "cagr_at_1.00": float(cagr.loc[1.0]), "cagr_at_1.32": float(cagr.loc[1.32]),
                              "share_1.00": share(1.0), "share_1.32": share(1.32)}
    return out


# ----------------------------------------------------------------------------
# report
# ----------------------------------------------------------------------------
def fm(x: Any, nd: int = 1) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x * 100:.{nd}f}%"


def fp(x: Any, nd: int = 1) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x * 100:+.{nd}f}"


def mark(v: Any) -> str:
    return "해당 없음" if v == "NA" else ("통과" if v is True else ("실패" if v is False else "판정 불가"))


def mdt(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    lines += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(lines)


def write_report(res: dict[str, Any]) -> None:
    g, i1, ps = res["gates"], res["i1"], res["pair_summary"]
    tr_ok = res["dividend"]["available"]
    L: list[str] = []
    L.append("# S4-3 1.0배 초과 노출 후보 검증 결과 (2026-10-01)")
    L.append("")
    L.append("- 성격: 연구 전용(D/C 등급). 정책·상태 파일과 주문·수량에 영향이 없다. 정책 반영은 S5 제안 → S6 Judge → S7 사용자 승인 → forward shadow 뒤.")
    L.append(f"- 프로토콜 해시(LF 정규화): `{res['protocol']['lf_normalized_sha256']}`. 판정은 기본값·ETF 코어·10bp 기준이고, 검증 시장은 NDX·SPX이다. SOX는 설계 구간이라 G3만 쓴다.")
    L.append("")
    L.append("## 0. 결론")
    L.append("")
    for c in MAIN:
        L.append(f"- **{c}**: {g[c]['verdict']}")
    L.append("")
    s5 = [c for c in MAIN if g[c]["verdict"].startswith("S5")]
    ev = res["i1_overall"]
    L.append(f"- **구현 판정 I1**: {ev['verdict']} (판정 대상: {', '.join(['B0'] + s5)}).")
    for c in ["B0"] + MAIN:
        L.append(f"  - {c}: 3개 시장 모두 통과 = {'예' if i1[c]['ok'] else '아니오'}")
    if not tr_ok:
        L.append("- SPX 배당 보정을 못 해서 G1·G4(연수익)·G6의 SPX 부분이 판정 불가이고, 모든 후보의 최고 판정이 검토 전용으로 제한됐다.")
    else:
        d = res["dividend"]
        L.append(f"- SPX의 G1·G4·G6 연수익 판정은 Shiller 배당(D/P)을 반영했다. Shiller 자료가 {d['last_month']}까지라 그 이후 {d['carried_sessions']}세션은 마지막 월 값을 이어 썼다. 가격 지수 결과는 병기한다.")
    L.append("- 모든 수치는 합성 3배·1배(가격 지수) 모형이고, 세금·키움 수수료율·1배 ETF 추종 오차는 모형에 없다(확인 필요).")
    L.append("")
    L.append("## 1. 게이트 표 (ETF 코어, 기본값)")
    L.append("")
    rows = []
    for c in MAIN:
        d = g[c]
        g1 = d["G1"]
        g1s = " / ".join([f"N {fp(g1['N']['mean'], 2)}%p·{g1['N']['frac_nonneg'] * 100:.0f}%"] + ([f"S {fp(g1['S']['mean'], 2)}%p·{g1['S']['frac_nonneg'] * 100:.0f}%"] if g1["S"] else ["S 판정 불가"]))
        g3 = d["G3"]
        worst = min(g3[k]["mdd_diff"] for k in g3 if k != "ok")
        worst1 = min(g3[k]["w1_worst_diff"] for k in g3 if k != "ok")
        g4 = d["G4"]
        g5 = d["G5"]
        g5s = "해당 없음" if g5.get("note") else f"{g5['passed']}/{g5['n']} 통과"
        g7 = d["G7"]
        rows.append([c, f"{mark(d['flat']['G1'])} ({g1s})", "해당 없음" if d["G2"].get("note") else mark(d["flat"]["G2"]),
                     f"{mark(d['flat']['G3'])} (최대 낙폭 차 최악 {fp(worst)}%p, 1년 창 최악 차 최악 {fp(worst1)}%p)",
                     f"{mark(d['flat']['G4'])} (N0 {fp(g4['N0']['cagr_diff'], 2)}/{fp(g4['N0']['mdd_diff'])}, S0 {fp(g4['S0']['cagr_diff'], 2) if g4['S0']['cagr_diff'] is not None else 'n/a'}/{fp(g4['S0']['mdd_diff'])})",
                     ("해당 없음" if g5.get("note") else f"{mark(d['flat']['G5'])} ({g5s})"), mark(d["flat"]["G6"]),
                     f"{mark(d['flat']['G7'])} (N {g7['N']['top_period']} {g7['N']['top_share'] * 100:.0f}%, S {g7['S']['top_period']} {g7['S']['top_share'] * 100:.0f}%)",
                     d["verdict"]])
    L.append(mdt(["후보", "G1 성장", "G2 효율", "G3 꼬리", "G4 미사용 구간", "G5 이웃", "G6 비용", "G7 집중", "판정"], rows))
    L.append("")
    L.append("- G1 칸: 평균 연수익 차(%p)·140쌍 중 차 ≥ 0 비율. G3 칸: 6개 칸(SOX·N·S × 전체·2010~) 중 가장 나쁜 값(%p). G4 칸: 연수익 차(%p)/최대 낙폭 차(%p).")
    L.append("- G1·G4·G6의 SPX 연수익 부분은 배당 보정(S_TR) 기준이다. 낙폭·꼬리·G2·G7은 가격 지수 기준이다.")
    L.append("")
    L.append("### 1.1 G2 효율 비교 (같은 평균 노출의 고정 배수 대비, N·S 전체, 가격 지수)")
    L.append("")
    rows = []
    for c in MAIN:
        if c == "F1.32":
            continue
        for mk in ("N", "S"):
            x = g[c]["G2"][mk]
            rows.append([c, mk, f"{x['fixed_multiple']:.2f}", fm(x["cagr_c"]), fm(x["cagr_fixed"]), fm(x["mdd_c"], 0), fm(x["mdd_fixed"], 0), mark(x["ok"])])
    L.append(mdt(["후보", "시장", "비교 고정 배수", "후보 연수익", "고정 연수익", "후보 최대 낙폭", "고정 최대 낙폭", "판정"], rows))
    L.append("")
    L.append("## 2. 구현 판정 I1 (ETF 코어 대 3배 + 현금, 현금 0%, 140쌍 평균)")
    L.append("")
    rows = []
    for c in CAND_ORDER:
        for mk in MARKETS:
            x = i1[c]["markets"][mk]
            rows.append([c, mk, fm(x["cagr_core"]), fm(x["cagr_cash3"]), fp(x["cagr_diff"], 2), fm(x["mdd_core"], 0), fm(x["mdd_cash3"], 0), fp(x["mdd_diff"]), mark(x["ok"])])
    L.append(mdt(["후보", "시장", "ETF 코어 연수익", "3배+현금 연수익", "차(%p)", "코어 최대 낙폭", "3배+현금 최대 낙폭", "낙폭 차(%p)", "통과"], rows))
    L.append("")
    L.append(f"- 종합: {ev['verdict']}. 기각·검토 전용 후보의 I1 결과는 위 표에 보고만 한다.")
    L.append("")
    L.append("## 3. 후보 대 B0 짝 비교 요약 (140쌍 평균 [최소, 최대], 차 = 후보 − B0)")
    L.append("")
    for mk in MARKETS:
        L.append(f"### {mk}")
        L.append("")
        rows = []
        for c in MAIN:
            e = ps[mk][c]
            def cell(seg, met):
                x = e[f"{seg}__d_{met}"]
                return f"{fp(x['mean'])} [{fp(x['min'])}, {fp(x['max'])}]"
            segs = SEG_NAMES[mk]
            rows.append([c, f"{e['mean_exposure']:.2f}", f"{e['adj_per_year']:.1f}"] +
                        [cell(s, "cagr") for s in segs] + [cell("full", "mdd"), cell("post", "mdd"), cell("full", "w1_min"), cell("post", "w1_min")])
        hdr = ["후보", "평균 노출", "연 조정"] + [f"연수익 차 {s}" for s in SEG_NAMES[mk]] + ["최대 낙폭 차 전체", "최대 낙폭 차 2010~", "1년 창 최악 차 전체", "1년 창 최악 차 2010~"]
        L.append(mdt(hdr, rows))
        L.append("")
        L.append(f"수준값(140쌍 평균, 전체 구간, ETF 코어): 1년 창은 252세션 단순 수익, 3년 창은 756세션 누적 수익. 경로 비율 = 창 안 최저 자산이 창 시작 대비 −20% 이하인 창 비율, 끝 비율 = 창 끝 수익 ≤ −20% 비율.")
        L.append("")
        rows = []
        for c in CAND_ORDER:
            lv = ps[mk][c]["full__level"]
            rows.append([c, fm(lv["cagr"]), fm(lv["mdd"], 0), f"{lv['dd20n']:.1f}", fm(lv["w1_med"]), fm(lv["w1_min"], 0), fm(lv["w1_pathfrac"]), fm(lv["w1_endfrac"]),
                         fm(lv["w3_med"]), fm(lv["w3_min"], 0), fm(lv["w3_pathfrac"]), fm(lv["w3_endfrac"])])
        L.append(mdt(["후보", "연수익", "최대 낙폭", "−20% 도달 횟수", "1년 중앙값", "1년 최악", "1년 경로 비율", "1년 끝 비율", "3년 중앙값", "3년 최악", "3년 경로 비율", "3년 끝 비율"], rows))
        L.append("")
    if tr_ok:
        L.append("### SPX 배당 보정(S_TR) 대 가격 지수 — G1 연수익 차")
        L.append("")
        rows = [[c, fp(g[c]["G1"]["S"]["mean"], 2), fp(ps["S"][c]["full__d_cagr"]["mean"], 2)] for c in MAIN]
        L.append(mdt(["후보", "S_TR 평균 차(%p)", "가격 지수 평균 차(%p)"], rows))
        L.append("")
    L.append("## 4. 시기별 연수익 차 (B0 대비 %p/년, 140쌍 평균)")
    L.append("")
    for mk in MARKETS:
        L.append(f"### {mk}")
        L.append("")
        pt = res["period_tables"][mk]
        rows = [[name, fm(v["B0_cagr"])] + [fp(v[c]) for c in MAIN] for name, v in pt.items()]
        L.append(mdt(["시기", "B0 연수익"] + MAIN, rows))
        L.append("")
        if mk in ("N", "S"):
            rows = []
            for c in MAIN:
                x = g[c]["G7"][mk]
                rows.append([c, x["top_period"] or "-", f"{x['top_share'] * 100:.0f}%", mark(x["ok"])])
            L.append(mdt(["후보", "초과수익 최대 시기", "양의 합 중 몫", "G7"], rows))
            L.append("")
    L.append("## 5. 급락 사건 (dd252 ≤ −30%, 조정 폭 10%p, 시작일 이동 0, ETF 코어)")
    L.append("")
    for mk in MARKETS:
        L.append(f"### {mk} ({len(res['crash'][mk])}건)")
        L.append("")
        rows = []
        for e in res["crash"][mk]:
            rows.append([f"{e['peak']}→{e['trough']}", fm(e["index_dd"], 0) + " / " + (fm(e["index_after1y"], 0) if e["index_after1y"] is not None else "n/a")] +
                        [fm(e["cands"][c]["dd"], 0) + " / " + (fm(e["cands"][c]["after1y"], 0) if e["cands"][c]["after1y"] is not None else "n/a") for c in CAND_ORDER])
        L.append(mdt(["고점→저점", "지수"] + CAND_ORDER, rows))
        L.append("")
    L.append("- 칸 = 고점→저점 낙폭 / 저점 뒤 252세션 수익. SOX는 문서 2.5절 7건(1995~96, 1997~98, 2000~02, 2007~08, 2020, 2022, 2024~25)과 대조해 차이를 아래에 적는다.")
    L.append(f"- SOX 대조: {res['crash_check']}")
    L.append("")
    L.append("## 6. 이웃 (G5)")
    L.append("")
    rows = []
    for c in MAIN:
        if c == "F1.32":
            continue
        for nb, v in g[c]["G5"]["neighbors"].items():
            rows.append([nb, mark(v["G1"]), mark(v["G3"]), mark(v["pass"])])
    L.append(mdt(["이웃", "G1", "G3", "통과"], rows))
    L.append("")
    L.append("- 과반 기준: " + ", ".join(f"{c} {g[c]['G5']['passed']}/{g[c]['G5']['n']}" for c in MAIN if c != "F1.32") + ".")
    fn = res.get("ref_summary")
    if fn:
        L.append("")
        L.append("### 보고 전용 참고 설정 (판정 제외)")
        L.append("")
        rows = []
        for mk in MARKETS:
            for lab, e in fn[mk].items():
                rows.append([lab, mk, fp(e["full__d_cagr"]["mean"], 2), fp(e["full__d_mdd"]["mean"]), fp(e["post__d_mdd"]["mean"])])
        L.append(mdt(["설정", "시장", "연수익 차 전체(%p)", "최대 낙폭 차 전체(%p)", "최대 낙폭 차 2010~(%p)"], rows))
    L.append("")
    L.append("## 7. 비용·현금 이자 민감도 (보고)")
    L.append("")
    rows = []
    for cost in COSTS:
        for mk in MARKETS:
            cs = res["cost_summary"][f"{cost}"][mk]
            rows.append([f"{cost * 1e4:.0f}bp", mk] + [fp(cs[c], 2) for c in MAIN])
    L.append(mdt(["비용", "시장"] + [f"{c} 연수익 차(%p)" for c in MAIN], rows))
    L.append("")
    L.append("- 위 표는 140쌍 평균 연수익 차(전체)이다. 같은 비용을 B0에도 적용했다.")
    L.append("")
    rows = []
    for r in res["cash_sensitivity"]:
        rows.append([r["market"], r["cand"], r["impl"], fm(r["cagr_usd0"]), fm(r["cagr_tbill"]), fm(r["mdd_usd0"], 0), fm(r["mdd_tbill"], 0)])
    L.append("현금 이자 민감도(조정 폭 10%p, 시작일 0, 전체 구간): 남는 현금 0%(기본) 대 국채 금리.")
    L.append("")
    L.append(mdt(["시장", "후보", "구현", "연수익 현금 0%", "연수익 국채 금리", "최대 낙폭 현금 0%", "최대 낙폭 국채 금리"], rows))
    L.append("")
    L.append("## 8. 최적 고정 배수 (보고 전용, ETF 코어, 조정 폭 0, 10bp, 시작일 0)")
    L.append("")
    rows = []
    for mk, segs in res["optimal"].items():
        for label, v in segs.items():
            rows.append([mk, label, f"{v['best_multiple']:.2f}", fm(v["best_cagr"]), fm(v["cagr_at_1.00"]), fm(v["cagr_at_1.32"]),
                         fm(v["share_1.00"], 0) if v["share_1.00"] is not None else "해당 없음", fm(v["share_1.32"], 0) if v["share_1.32"] is not None else "해당 없음"])
    L.append(mdt(["시장", "구간", "최적 배수", "최적 연수익", "1.00배 연수익", "1.32배 연수익", "1.00배 몫", "1.32배 몫"], rows))
    L.append("")
    L.append("- 최적점 주변은 평평하다. 최적점 하나에 의미를 두지 않는다.")
    L.append("")
    L.append("## 9. 실제 상품 2010~ (보고 전용, 수정종가, 조정 폭 10%p)")
    L.append("")
    rows = []
    for r in res["real"]:
        if "error" in r:
            rows.append([r["pair"], "-", "-", r["error"], "-", "-", "-"])
        else:
            rows.append([r["pair"], r["cand"], r["impl"], fm(r["cagr"]), fm(r["mdd"], 0), fm(r["w1_min"], 0), f"{r['mean_exposure']:.2f}"])
    L.append(mdt(["상품(3배/1배)", "후보", "구현", "연수익", "최대 낙폭", "1년 창 최악", "평균 노출"], rows))
    L.append("")
    L.append("## 10. 표본 크기 (조정 폭 10%p, 시작일 0, 전체 구간)")
    L.append("")
    rows = []
    for mk in MARKETS:
        for c in CAND_ORDER:
            x = res["counts"][mk][c]
            rows.append([mk, c, x["nup"], x["gate_off"], x["x1_entry"], f"{x['adj_per_year']:.1f}"])
    L.append(mdt(["시장", "후보", "1.0 초과 전환 횟수", "게이트 꺼짐 횟수", "X1 진입 횟수", "연 조정 횟수"], rows))
    L.append("")
    L.append("## 11. 현재 지수 조건 (보고 전용, 주문·수량 아님)")
    L.append("")
    rows = [[mk, v["date"], f"{v['close']:.0f}", f"{v['sma200']:.0f}", fm(v["ext"]), fm(v["sigma_median"]), "예" if v["overheat_if_ext_ge_sigma_median"] else "아니오", fm(v["dd252"])]
            for mk, v in res["current"].items()]
    L.append(mdt(["지수", "날짜", "종가", "200일선", "200일선 대비", "σ 중앙값(연)", "과열(≥1σ)", "252세션 고점 대비"], rows))
    L.append("")
    L.append("## 12. 데이터 점검 요약과 확인 필요")
    L.append("")
    for line in res["data_notes"]:
        L.append(f"- {line}")
    L.append("- 확인 필요: 키움 수수료율, 1배 ETF 보수와 추종지수(SOXX·SMH, QQQ), 리밸런싱 때 실현되는 양도차익 세금(모형에 없음), 합성 3배 차입비 가정(국채 금리 ×2, 보수 0.95%).")
    L.append("- 이 결과는 S5 제안 입력일 뿐이며 어떤 정책·상태·주문도 바꾸지 않는다.")
    RESULTS_MD.write_text("\n".join(L) + "\n", encoding="utf-8")


def pairs_csv(dfs: dict[str, pd.DataFrame]) -> int:
    parts = []
    for mk, df in dfs.items():
        base = base_market(mk)
        key = ["impl", "cost", "cash", "band", "shift"]
        b0 = df[df["cand"] == "B0"].set_index(key)
        out = df[["market", "cand", "impl", "cost", "cash", "band", "shift", "adj_per_year", "nup", "gate_off", "x1_entry", "full__cagr", "full__mdd", "full__meanx"]].copy()
        mi = pd.MultiIndex.from_frame(df[key])
        for s in SEG_NAMES[base]:
            for met in ("cagr", "mdd", "w1_min"):
                out[f"d_{s}_{met}"] = df[f"{s}__{met}"].values - b0[f"{s}__{met}"].reindex(mi).values
        parts.append(out.rename(columns={"full__cagr": "cagr_full", "full__mdd": "mdd_full", "full__meanx": "mean_exposure_full"}))
    allp = pd.concat(parts, ignore_index=True)
    allp.to_csv(PAIRS_CSV, index=False, float_format="%.8g")
    return len(allp)


def run_study(args: argparse.Namespace) -> int:
    global BANDS, SHIFTS, RESULTS_JSON, PAIRS_CSV, RESULTS_MD
    t_start = time.time()
    proto = check_protocol()
    if args.smoke:  # plumbing check only: 2 bands x 2 shifts, outputs outside the repo; protocol parameters are untouched
        BANDS, SHIFTS = (0.0, 0.10), (0, 1)
        out_dir = Path(args.smoke)
        out_dir.mkdir(parents=True, exist_ok=True)
        RESULTS_JSON, PAIRS_CSV, RESULTS_MD = out_dir / "r.json", out_dir / "p.csv", out_dir / "r.md"
    elif self_test() != 0:
        print("self-test failed; --run stops")
        return 1
    inputs = load_inputs()
    tr_ok = inputs["shiller"] is not None
    carried = 0
    if tr_ok:
        _, carried = dividend_daily(inputs["close"]["S"].index, inputs["shiller"])
    markets_all = ["S_TR", "S", "N", "SOX"] if tr_ok else ["S", "N", "SOX"]
    ctx = mp.get_context("spawn")
    with ctx.Pool(args.workers, initializer=_init_worker) as pool:
        tasks = [(mk, s, BANDS, phase1_jobs(mk)) for mk in markets_all for s in SHIFTS]
        dfs = dispatch(pool, tasks, "phase1")
        fixm: dict[tuple[str, str], float] = {}
        for c in MAIN:
            if c == "F1.32":
                continue
            for mk in ("N", "S"):
                mx = float(sel(dfs[mk], c)["full__meanx"].mean())
                fixm[(c, mk)] = round(round(mx * 20.0) / 20.0, 2)
        tasks2 = []
        for mk in ("N", "S"):
            ms = sorted({m for (c, k), m in fixm.items() if k == mk})
            for s in SHIFTS:
                tasks2.append((mk, s, BANDS, [(f"FIX|{m:.2f}", "core", COST, "usd0") for m in ms]))
        dfs2 = dispatch(pool, tasks2, "phase2-fixed")
        for mk, d2 in dfs2.items():
            dfs[mk] = pd.concat([dfs[mk], d2], ignore_index=True)
        opt_tasks = [(mk, 0, (0.0,), [(f"FIX|{m:.2f}", "core", COST, "usd0") for m in FIX_GRID]) for mk in MARKETS]
        opt = dispatch(pool, opt_tasks, "phase3-optimal")
        sens_jobs = [(c, impl, COST, "tbill") for c in CAND_ORDER for impl in ("core", "cash3")]
        sens = dispatch(pool, [(mk, 0, (0.10,), sens_jobs) for mk in MARKETS], "phase3-cash")

    gates = evaluate_gates(dfs, tr_ok, fixm)
    i1 = i1_eval(dfs)
    s5 = [c for c in MAIN if gates[c]["verdict"].startswith("S5")]
    i1_all = all(i1[c]["ok"] for c in ["B0"] + s5)
    i1_overall = {"verdict": "ETF 코어 권장" if i1_all else "현행 유지", "checked": ["B0"] + s5}
    labels_main = CAND_ORDER
    psum = pair_summary(dfs, labels_main)
    ref_summary = pair_summary(dfs, REF_LABELS)
    ref_summary = {mk: {lab: v for lab, v in ref_summary[mk].items()} for mk in MARKETS}
    cost_summary = {}
    for cost in COSTS:
        cost_summary[f"{cost}"] = {mk: {c: float(delta(dfs[mk], c, "full__cagr", cost=cost).mean()) for c in MAIN} for mk in MARKETS}
    period_tables = {mk: period_table(dfs, mk, MAIN) for mk in MARKETS}
    counts = {}
    for mk in MARKETS:
        counts[mk] = {}
        for c in CAND_ORDER:
            r = sel(dfs[mk], c).loc[(0.10, 0)]
            counts[mk][c] = {"nup": int(r["nup"]), "gate_off": int(r["gate_off"]), "x1_entry": int(r["x1_entry"]), "adj_per_year": float(r["adj_per_year"])}
    cash_rows = []
    for mk in MARKETS:
        for c in CAND_ORDER:
            for impl in ("core", "cash3"):
                a = sel(dfs[mk], c, impl).loc[(0.10, 0)]
                b = sel(sens[mk], c, impl, cash="tbill").loc[(0.10, 0)]
                cash_rows.append({"market": mk, "cand": c, "impl": impl, "cagr_usd0": float(a["full__cagr"]), "cagr_tbill": float(b["full__cagr"]),
                                  "mdd_usd0": float(a["full__mdd"]), "mdd_tbill": float(b["full__mdd"])})
    crash = crash_table(inputs)
    sox_events = [(e["peak"], e["trough"]) for e in crash["SOX"]]
    crash_check = ("재현 건수 " + str(len(sox_events)) + "건: " + ", ".join(f"{p}→{t}" for p, t in sox_events) + ". 문서 2.5절은 7건이다. "
                   + ("건수가 같다." if len(sox_events) == 7 else "건수가 다르다(정의·시작일 차이, 확인 필요)."))
    real = real_products(inputs)
    optimal = optimal_table(opt)
    cur = current_conditions(inputs)
    src = inputs["sources"]
    data_notes = []
    for nm in ("NDX", "SPX"):
        v = src["series"][nm]
        data_notes.append(f"{nm}: {v['first_date']}~{v['last_date']} {v['rows']}행(Yahoo 단일 출처). 1994-05 이후 세션은 SOX 달력과 일치(여분 {v['late_extra_count']}, 누락 {v['late_missing_count']}). "
                          f"5일 초과 공백 {[x['to'] + ' ' + str(x['days']) + '일' for x in v['gaps_over_5_calendar_days']]}. 이상치(|일간| ≥ 15%): "
                          + ", ".join(f"{x['date']} {x['ret'] * 100:+.1f}%" for x in v["abs_return_ge_15pct"]) + "(실제 사건으로 보여 표시만 함).")
    data_notes.append("NDX 새 수집분과 기존 cpv NDX 파일의 1994-05-04~ 종가 차이: 최대 " + f"{src['series']['NDX']['old_file_close_check']['max_abs_diff']:.2e}.")
    data_notes.append(f"NDX·SPX 세션 집합(1985-10~1994-05) 차이: {src['ndx_vs_spx_sessions_1985_1994']['ndx_only_count']}/{src['ndx_vs_spx_sessions_1985_1994']['spx_only_count']}건.")
    data_notes.append(f"금리: 1981-09-01 이후 DGS3MO, 이전 DTB3. 겹치는 구간 DTB3−DGS3MO 평균 {src['dtb3']['overlap_with_dgs3mo']['mean_diff_pct_points']:.2f}%p(최소 {src['dtb3']['overlap_with_dgs3mo']['min']:.2f}).")
    data_notes.append("Shiller 배당: " + (f"{src['shiller']['first_month'][:7]}~{src['shiller']['last_month'][:7]}, 이후 {carried}세션 이어 씀." if tr_ok else "받지 못함 → 배당 미보정."))
    res = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(), "protocol": proto, "runner_sha256": sha256_file(Path(__file__).resolve()),
        "inputs_sources_sha256": sha256_file(SOURCES_JSON), "cpv_sources_sha256": sha256_file(CPV_SOURCES), "s4_sources_sha256": sha256_file(S4_SOURCES),
        "self_test": "passed", "workers": args.workers, "bands": BANDS, "shifts": [SHIFTS[0], SHIFTS[-1]], "pairs_per_candidate": len(BANDS) * len(SHIFTS),
        "dividend": {"available": tr_ok, "carried_sessions": carried, "last_month": src["shiller"].get("last_month") if tr_ok else None},
        "gates": gates, "i1": i1, "i1_overall": i1_overall, "pair_summary": psum, "ref_summary": ref_summary, "cost_summary": cost_summary,
        "period_tables": period_tables, "counts": counts, "cash_sensitivity": cash_rows, "crash": crash, "crash_check": crash_check, "real": real,
        "optimal": optimal, "current": cur, "fixed_multiples_used": {f"{c}|{mk}": m for (c, mk), m in fixm.items()}, "data_notes": data_notes,
        "elapsed_seconds": time.time() - t_start,
    }
    RESULTS_JSON.write_text(json.dumps(clean(res), ensure_ascii=False, indent=1), encoding="utf-8")
    write_report(res)
    allrows = dict(dfs)
    npairs = pairs_csv(allrows)
    print(json.dumps({"verdicts": {c: gates[c]["verdict"] for c in MAIN}, "i1": i1_overall, "pairs_rows": npairs, "elapsed_s": round(time.time() - t_start)}, ensure_ascii=False))
    return 0



# ----------------------------------------------------------------------------
# self-test
# ----------------------------------------------------------------------------
def _toy_feat(n: int, px: list[float] | None = None, r: float = 0.0) -> Feat:
    idx = pd.bdate_range("2000-01-03", periods=n)
    px = px or [100.0] * n
    d = pd.DataFrame({"px": px, "rate": [0.0] * n, "r": [0.0] * n, "rc": [0.0] * n, "r3": [r] * n, "r1": [r] * n,
                      "sig_med": [0.3] * n, "dd252": [0.0] * n, "sma150": [90.0] * n, "sma200": [90.0] * n, "sma250": [90.0] * n,
                      "ext": [0.1] * n}, index=idx)
    return Feat(d)


def load_reference():
    ns: dict[str, Any] = {"__name__": "reference_engine"}
    exec(compile(REFERENCE_ENGINE_SRC, "appendix_a", "exec"), ns)
    # COLS extended only so neighbor ma_key variants can be compared (functions read COLS from this namespace)
    ns["COLS"] = ("px", "sig_med", "dd252", "sma200", "ext", "sma150", "sma250")
    return types.SimpleNamespace(**ns)


def ref_target(mod, spec: dict[str, Any]):
    k = spec["kind"]
    if k == "fixed":
        return mod.fixed(spec["L"])
    if k == "G":
        return mod.make_G(base=spec["base"], extra=spec["extra"], trend=spec["trend"], overheat=spec["overheat"], brake=spec["brake"],
                          off=spec["off"], on=spec["on"], L=(10 ** 9 if spec["L"] is None else spec["L"]), k_hot=spec["k_hot"], k_cool=spec["k_cool"],
                          ma_key=spec["ma"])
    if k == "X1":
        return mod.make_X1(add=spec["add"], k_dd=spec["k_dd"], k_reb=spec["k_reb"], k_stop=spec["k_stop"], k_exit=spec["k_exit"])
    raise ValueError(k)


def self_test() -> int:
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, note: str = "") -> None:
        results.append((name, bool(ok), note))
        print(("PASS " if ok else "FAIL ") + name + (f" :: {note}" if note else ""), flush=True)

    inputs = load_inputs()
    ref = load_reference()

    # ---- (2) hand check of synthetic 1x/3x returns and the ETF-core B0 path
    close = pd.Series([100.0, 110.0, 99.0, 108.9], index=pd.bdate_range("2000-01-03", periods=4))
    rate = pd.Series([4.0] * 4, index=close.index)
    d = features(close, rate, 0.0035)
    r = [0.10, -0.10, 0.10]
    exp3 = [3 * x - 0.0095 / 252 - 2 * 0.04 / 252 for x in r]
    exp1 = [x - 0.0035 / 252 for x in r]
    check("2 synthetic 3x/1x returns match hand arithmetic",
          np.allclose(d["r3"].values, exp3, rtol=0, atol=1e-12)
          and np.allclose(d["r1"].values, exp1, rtol=0, atol=1e-12) and len(d) == 3, f"r3={exp3[0]:.6f}")
    # note: first session (no return) is dropped, so d starts at session 2 (return +10%)
    F2 = Feat(d)
    E, X, st = simulate(F2, fixed(1.0), 0.10, 0.001, "core")
    # i=0 all cash; i=1 fill (cost 1x on 1.0); i=2 return on 1x
    e_hand = (1 - 0.001 * 1.0) * (1 + d["r1"].iloc[2])
    check("2 core B0 hand path (entry cost then 1x return)", abs(E[2] - e_hand) < 1e-15 and st["ntr"] == 1 and abs(X[1] - 1.0) < 1e-15, f"E2={E[2]:.8f}")

    # ---- (3) band and zero entry/exit, both implementations (zero-return toy so weights never drift)
    Ft = _toy_feat(9)
    seq = [1.0, 1.05, 1.10, 1.5, 1.0, 1.04, 1.0, 1.0, 1.0]
    E, X, st = simulate(Ft, SEQ(seq), 0.10, 0.001, "core")
    expX = [0.0, 1.0, 1.05, 1.05, 1.5, 1.0, 1.04, 1.0, 1.0]
    check("3 core band + zero entry/exit path", np.allclose(X, expX, atol=1e-12) and st["ntr"] == 6, f"X={np.round(X, 4).tolist()} ntr={st['ntr']}")
    seq3 = [1.0, 1.05, 1.1, 1.5, 1.0, 0.06, 0.0, 0.06, 0.06]
    E, X, st = simulate(Ft, SEQ(seq3), 0.10, 0.001, "cash3")
    # decisions fill next session: w*=X/3. 1.0->1/3 entry; 1.05->.35 (|d|<band, no trade); 1.1->.3667 (no); 1.5->.5 trade; 1.0->.3333 trade;
    # .06->.02 (diff .313 >= band) trade; 0.0 -> exit; .06 -> entry from 0 (even though < band)
    expX3 = [0.0, 1.0, 1.0, 1.0, 1.5, 1.0, 0.06, 0.0, 0.06]
    check("3 cash3 band + zero entry/exit path", np.allclose(X, expX3, atol=1e-12) and st["ntr"] == 6, f"X={np.round(X, 4).tolist()} ntr={st['ntr']}")

    # ---- (4) gate: 0.80 / 0.90 of the 252-session high, toy equity path
    stats = {"gate_off": 0, "x1_entry": 0}
    Lk = _toy_feat(300).L
    fK = make_target(G(1.32, 0.0, trend=False, brake=1.0), Lk, stats)
    path = [1.0, 1.0, 0.85, 0.79, 0.85, 0.89, 0.90]
    got = [fK(i, e) for i, e in enumerate(path)]
    check("4 gate off below 0.80 of high, on at/above 0.90", got == [1.32, 1.32, 1.32, 1.0, 1.0, 1.0, 1.32] and stats["gate_off"] == 1, f"{got}")
    stats = {"gate_off": 0, "x1_entry": 0}
    fW = make_target(G(1.32, 0.0, trend=False, brake=1.0), Lk, stats)
    ws = [fW(i, 2.0 if i == 0 else 1.5) for i in range(253)]
    check("4 gate: old high leaves the 252-session window", ws[251] == 1.0 and ws[252] == 1.32, f"{ws[251]},{ws[252]}")

    # ---- (5) overheat hysteresis (ext >= 1.0 sigma on, <= 0.5 sigma off)
    Fo = _toy_feat(8)
    Fo.L["ext"] = [0.20, 0.31, 0.20, 0.15, 0.29, 0.30, 0.16, 0.15]
    fO = make_target(G(1.0, 0.5, overheat=True), Fo.L, {"gate_off": 0, "x1_entry": 0})
    got = [fO(i, 1.0) for i in range(8)]
    check("5 overheat hysteresis", got == [1.5, 1.0, 1.0, 1.5, 1.5, 1.0, 1.0, 1.5], f"{got}")

    # ---- (6) X1 state machine
    Fx = _toy_feat(16)
    Fx.L["dd252"] = [-0.10, -0.23, -0.30, -0.31, -0.40, -0.05, -0.25, -0.20, -0.20, -0.05, -0.24, -0.08, float("nan"), -0.25, -0.25, -0.25]
    Fx.L["px"] = [100, 80, 70, 69, 60, 90, 50, 60, 68.5, 90, 60, 62, 62, 60, 60, 60]
    stx = {"gate_off": 0, "x1_entry": 0}
    fX = make_target(X1(), Fx.L, stx)
    got = [fX(i, 1.0) for i in range(16)]
    exp = [1.0, 1.5, 1.5, 1.0, 1.0, 1.0, 1.5, 1.5, 1.0, 1.0, 1.5, 1.0, 1.0, 1.0, 1.0, 1.0]
    # t3: stop (69 <= 80*(1-.45*.3)=69.2); t4: cooling blocks re-entry; t5: cool released; t6 re-entry; t8: take-profit (68.5 >= 50*(1+1.2*.3)=68);
    # t9: cool released; t10 entry; t11: dd recovered to -0.08 >= -0.3*.3=-0.09 -> exit; t12 NaN -> 1.0; t13..: cooling until dd>=-0.09 (never)
    check("6 X1 entry / stop / take-profit / recovery / cooling", got == exp and stx["x1_entry"] == 3, f"{got} entries={stx['x1_entry']}")

    # ---- (8) ETF core toy: two product costs, brake 3x -> 1x, X<1 leaves cash
    Fc = _toy_feat(6)
    E, X, st = simulate(Fc, SEQ([1.0, 1.5, 1.0, 0.5, 0.5, 0.5]), 0.10, 0.001, "core")
    e = 1.0
    e -= e * 0.001 * 1.0           # i=1: 1x 100%
    e -= e * 0.001 * (0.25 + 0.25)  # i=2: 1.5 -> 3x 25% + 1x 75% from 1x 100%
    e -= e * 0.001 * (0.25 + 0.25)  # i=3: brake 1.0 -> 3x 25% leaves, 1x back to 100%
    e -= e * 0.001 * (0.0 + 0.5)    # i=4: X=0.5 -> 1x 50% + cash 50%
    check("8 ETF core toy: costs on both products, 3x->1x brake, X<1 cash", abs(E[4] - e) < 1e-15 and abs(X[2] - 1.5) < 1e-12 and abs(X[3] - 1.0) < 1e-12 and abs(X[4] - 0.5) < 1e-12, f"E4={E[4]:.8f} expected={e:.8f}")

    # ---- metric helpers
    S = np.array([1.0, 1.21, 1.331])
    check("10 cagr uses len(segment) sessions", abs(cagr_of(S, 3) - (1.331 ** (252 / 3) - 1)) < 1e-9)
    S2 = np.array([1.0, 1.2, 0.9, 0.95, 1.3, 0.95, 0.9, 1.4])
    S3 = np.array([1.0, 1.2, 0.9, 1.1, 0.9])
    check("10 -20% count once per new-high episode", dd20_count(S2) == 2 and dd20_count(S3) == 1, f"{dd20_count(S2)},{dd20_count(S3)}")
    T = np.array([1.0, 0.7, 1.2, 0.8, 1.0])
    med, worst, pf, ef = window_stats(T, 2)
    ret = np.array([1.2 / 1.0 - 1, 0.8 / 0.7 - 1, 1.0 / 1.2 - 1])
    check("10 window stats (median, worst, path fraction, end fraction)", abs(med - np.median(ret)) < 1e-12 and abs(worst - ret.min()) < 1e-12 and abs(pf - 2 / 3) < 1e-12 and abs(ef - 0.0) < 1e-12, f"{med:.4f},{worst:.4f},{pf:.3f},{ef:.3f}")
    rng = np.random.default_rng(3)
    Er = np.cumprod(1 + rng.normal(0.0005, 0.01, 1000))
    Er[0] = 1.0
    idx = pd.bdate_range("2000-01-03", periods=1000)
    pb = [(0, 400), (400, 700), (700, 1000)]
    gsum = sum(period_growth(Er, a, b)[0] for a, b in pb)
    check("10 period log growth sums to the total", abs(gsum - math.log(Er[-1])) < 1e-12)

    # ---- (1) no future information: truncated histories give the same targets/paths
    sox = inputs["close"]["SOX"]
    rate = inputs["rate_pct"]
    base_close = sox.iloc[:3300]
    dfull = features(base_close, rate, FEE1["SOX"])
    Ff = Feat(dfull)
    cuts = [900, 1300, 1700, 2100, 2500, 2800, 3000, 3200, 3290]
    ok_all = True
    bad = ""
    for lab in ["B0", "T1", "T2", "F1.32", "K132-G", "T2-132b", "X1"]:
        for impl in ("core", "cash3"):
            Efull, Xfull, _ = simulate(Ff, REGISTRY[lab], 0.10, COST, impl)
            for t in cuts:
                dcut = features(base_close.iloc[:t], rate, FEE1["SOX"])
                Ecut, Xcut, _ = simulate(Feat(dcut), REGISTRY[lab], 0.10, COST, impl)
                if not (np.array_equal(Xcut, Xfull[:len(Xcut)]) and np.array_equal(Ecut, Efull[:len(Ecut)])):
                    ok_all = False
                    bad = f"{lab}/{impl}@{t}"
    check("1 no future information (truncated histories, 9 cut points, 7 candidates x 2 implementations)", ok_all, bad)

    # ---- features identical to the reference features on shared columns
    dref = ref.features(base_close, rate, 0.0035)
    shared = ["px", "rate", "r", "rc", "r3", "r1", "sig20", "sig_med", "dd252", "sma200", "ext"]
    check("1 features equal the Appendix A features (shared columns, exact)", all(np.array_equal(dref[c].values, dfull[c].values, equal_nan=True) for c in shared))

    # ---- (7) Appendix A reference reproduction on the full SOX history (continuous run from 1994-05-05)
    dsox = features(sox, rate, FEE1["SOX"])
    Fs = Feat(dsox)
    exp_vals = {
        "1": {"impl": "cash3", "cash": "tbill", "v": {"B0": (13.3, -87), "T1": (16.8, -91), "T2": (17.1, -90), "X1": (13.6, -90), "F1.32": (13.3, -97), "K132-G": (15.8, -90), "T2-132b": (17.8, -90)}},
        "3": {"impl": "core", "cash": "usd0", "v": {"B0": (15.1, -88), "T1": (19.1, -89), "T2": (19.2, -88), "X1": (14.1, -90), "F1.32": (16.2, -96), "K132-G": (18.3, -89), "T2-132b": (19.1, -91)}},
        "4": {"impl": "cash3", "cash": "usd0", "v": {"B0": (11.6, -90), "T1": (15.6, -91), "T2": (15.0, -90), "X1": (11.9, -91), "F1.32": (13.5, -96), "K132-G": (14.6, -91), "T2-132b": (15.9, -92)}},
    }
    detail = {}
    for key, cfg in exp_vals.items():
        bad = []
        for lab, (ec, em) in cfg["v"].items():
            E, X, _ = simulate(Fs, REGISTRY[lab], 0.10, COST, cfg["impl"], cash=cfg["cash"])
            m = seg_metrics(E, X, 0, len(E))
            got = (round(m[0] * 100, 1), int(round(m[1] * 100)))
            detail[f"{key}/{lab}"] = (got, (ec, em))
            if got != (ec, em):
                bad.append(f"{lab}: got {got} expected {(ec, em)}")
        check(f"7 reference values ({key}) reproduced to 1 decimal / whole % (SOX, band 10%p)", not bad, "; ".join(bad))
    # real SOXL B0 (Appendix A style): SOX-full-history features, cut at 2010-03-11, cash start, SOXL adjusted returns
    soxl = inputs["real"]["SOXL"]
    ds = dsox.loc[POST_START:].copy()
    fs = Feat(ds)
    lr = soxl.pct_change().reindex(ds.index)
    if lr.iloc[1:].isna().any():
        check("7 SOXL real B0 aligns with SOX sessions", False, f"{int(lr.iloc[1:].isna().sum())} NaN returns")
    else:
        lr = lr.fillna(0.0).tolist()
        E, X, _ = simulate(fs, fixed(1.0), 0.10, COST, "cash3", cash="tbill", lev_ret=lr)
        m = seg_metrics(E, X, 0, len(E))
        w = window_stats(E, 252)
        check("7 real SOXL B0 (T-bill cash): 1-year window median 25.9%, CAGR 22.8%", round(w[0] * 100, 1) == 25.9 and round(m[0] * 100, 1) == 22.8,
              f"median={w[0] * 100:.2f}% cagr={m[0] * 100:.2f}%")

    # ---- (9) optimized engine equals the Appendix A engine on >=200 random configurations
    rnd = random.Random(20261001)
    labels = [k for k in REGISTRY if not k.startswith("REF|F") and not k.startswith("F1.32|")]
    labels += ["REF|T1_nogate", "REF|T2_nogate", "REF|T1_fullHWM", "REF|T2-132_nobrake"]
    labels = sorted(set(labels))
    worst_rel = 0.0
    nbad = 0
    nconf = 0
    cache_feat: dict[Any, Any] = {}
    for _ in range(240):
        mk = rnd.choice(MARKETS)
        ser = inputs["close"][mk]
        ln = rnd.randint(1400, 2600)
        st0 = rnd.randint(0, len(ser) - ln - 1)
        cl = ser.iloc[st0:st0 + ln]
        key = (mk, st0, ln)
        if key not in cache_feat:
            dd_ = features(cl, rate, FEE1[mk])
            cache_feat[key] = (dd_, Feat(dd_))
        dd_, Fm = cache_feat[key]
        lab = rnd.choice(labels)
        impl = rnd.choice(["core", "cash3"])
        cash = rnd.choice(["usd0", "tbill"])
        band = rnd.choice(list(BANDS) + [round(rnd.uniform(0, 0.2), 4)])
        cost = rnd.choice(COSTS)
        spec = REGISTRY[lab]
        E1, X1_, s1 = simulate(Fm, spec, band, cost, impl, cash=cash)
        dref = ref.with_cash(dd_, cash)
        tgt = ref_target(ref, spec)
        if impl == "core":
            E2, X2, n2 = ref.simulate_core(dref, tgt, band=band, cost=cost)
        else:
            E2, X2 = ref.simulate(dref, tgt, band=band, cost=cost)
            n2 = None
        rel = float(np.max(np.abs(E1 / E2.values - 1.0)))
        worst_rel = max(worst_rel, rel)
        nconf += 1
        if rel > 1e-12 or not np.allclose(X1_, X2.values, rtol=0, atol=1e-12):
            nbad += 1
        if n2 is not None and n2 != s1["ntr"]:
            nbad += 1
    check(f"9 optimized engine equals Appendix A engine ({nconf} random configs, mixed candidates/bands/starts/markets/implementations/cash)",
          nbad == 0 and nconf >= 200, f"max relative error {worst_rel:.2e}, mismatches {nbad}")

    failed = [n for n, ok, _ in results if not ok]
    print(json.dumps({"checks": len(results), "failed": failed}, ensure_ascii=False))
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--workers", type=int, default=max(1, (mp.cpu_count() or 2) - 2))
    ap.add_argument("--smoke", default=None, help="plumbing check with 2 bands x 2 shifts; writes to this directory, not the repo")
    args = ap.parse_args()
    if args.collect:
        return collect()
    if args.self_test:
        return self_test()
    if args.run:
        return run_study(args)  # noqa: F821  (defined in the run part)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
