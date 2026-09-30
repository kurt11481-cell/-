#!/usr/bin/env python3
"""Protocol-locked CPV (room-proportional + volatility-adjusted) start-date-shifting window study (S4-2).

Historical research only.  It never reads or changes broker state, never uses
Kiwoom tools, and never places or schedules an order.  Nothing here has order or
quantity authority; results are D/C-grade research.

The pre-result contract is SOXL_CPV_WINDOW_PROTOCOL_2026-10-01.md (+ .sha256 sidecar).
The runner refuses to run if the protocol changed.  S4 files are only read (importlib).

  --self-test   synthetic/S4-input checks, no network
  --collect     fetch public data (Yahoo ^SOX/^NDX/SOXX, FRED DGS3MO full history)
  --run         run the protocol on the saved inputs and write the results
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
S4_SCRIPT = HERE / "walk_forward_soxl_signals_2026-10-01.py"
S4_INPUT_DIR = HERE / "soxl_signal_inputs_2026-10-01"
S4_SOURCES = S4_INPUT_DIR / "soxl_signal_inputs_sources.json"
INPUT_DIR = HERE / "cpv_inputs_2026-10-01"
SOURCES_JSON = INPUT_DIR / "cpv_inputs_sources.json"
PROTOCOL = HERE / "SOXL_CPV_WINDOW_PROTOCOL_2026-10-01.md"
PROTOCOL_SIDECAR = HERE / "SOXL_CPV_WINDOW_PROTOCOL_2026-10-01.sha256"
STEM = "soxl_cpv_window_2026-10-01"
RESULTS_JSON = HERE / f"{STEM}_results.json"
WINDOWS_CSV = HERE / f"{STEM}_windows.csv"
RESULTS_MD = HERE / "SOXL_CPV_WINDOW_RESULTS_2026-10-01.md"

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"}
INDEX_START = "1994-05-04"
SOXX_START = "2001-07-13"
U_END = pd.Timestamp("2010-03-10")
A_START = pd.Timestamp("2010-03-11")

# Parameters are fixed by the protocol; never edit after seeing a result.
CAP = 0.633
FLOOR = 0.80
EXPENSE = 0.0095
LENGTHS = (252, 756)
COSTS = (10.0, 20.0, 50.0)
BAND = 0.10
SIGMA_WINDOWS = (15, 20, 30)
MIN_MEDIAN = 120
REGIMES = {"U1": (1994, 1999), "U2": (2000, 2002), "U3": (2003, 2007), "U4": (2008, 2009),
           "A1": (2010, 2015), "A2": (2016, 2020), "A3": (2021, 2025)}
SEG_REGIMES = {"U": ["U1", "U2", "U3", "U4"], "A": ["A1", "A2", "A3"]}
CONFIGS: dict[str, dict[str, Any]] = {
    "B0": dict(kind="fixed", w=CAP, band=BAND),
    "BF10": dict(kind="fixed", w=0.333, band=BAND),
    "BV10": dict(kind="bv", w=0.333, sw=20, band=BAND),
    "BAD": dict(kind="bad", band=BAND),
    "CPV": dict(kind="cpv", m=2.0, sw=20, use_v=True, floor="fixed", band=BAND),
    "CPV_m1.5": dict(kind="cpv", m=1.5, sw=20, use_v=True, floor="fixed", band=BAND),
    "CPV_m2.5": dict(kind="cpv", m=2.5, sw=20, use_v=True, floor="fixed", band=BAND),
    "CPV_sw15": dict(kind="cpv", m=2.0, sw=15, use_v=True, floor="fixed", band=BAND),
    "CPV_sw30": dict(kind="cpv", m=2.0, sw=30, use_v=True, floor="fixed", band=BAND),
    "CPV_noV": dict(kind="cpv", m=2.0, sw=20, use_v=False, floor="fixed", band=BAND),
    "CPV_band5": dict(kind="cpv", m=2.0, sw=20, use_v=True, floor="fixed", band=0.05),
    "CPV_band15": dict(kind="cpv", m=2.0, sw=20, use_v=True, floor="fixed", band=0.15),
    "CPV_floorRaise": dict(kind="cpv", m=2.0, sw=20, use_v=True, floor="raise", band=BAND),
}
NEIGHBORS = ["CPV_m1.5", "CPV_m2.5", "CPV_sw15", "CPV_sw30", "CPV_noV", "CPV_band5", "CPV_band15"]
BASELINES = ["B0", "BAD", "BV10", "BF10"]
MAIN_SET = ["CPV"] + BASELINES
CRASH_STARTS = [("2000", "2000-01-03", "U"), ("2008", "2008-01-02", "U"), ("2020", "2020-01-02", "A"),
                ("2022", "2022-01-03", "A"), ("2025", "2025-01-02", "A")]
MAIN_CSV_CONFIGS = MAIN_SET


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_MODS: dict[str, Any] = {}


def s4():
    if "s4" not in _MODS:
        _MODS["s4"] = load_module("s4_signals_readonly", S4_SCRIPT)
    return _MODS["s4"]


def clean(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        return None if not math.isfinite(float(obj)) else float(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp, datetime, date)):
        return obj.isoformat()
    if isinstance(obj, np.ndarray):
        return clean(obj.tolist())
    return obj


def read_sidecar() -> dict[str, str]:
    out = {}
    for line in PROTOCOL_SIDECAR.read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def check_protocol() -> dict[str, str]:
    side = read_sidecar()
    raw, lf = sha256_file(PROTOCOL), lf_sha256(PROTOCOL)
    if lf != side.get("lf_normalized_sha256"):
        raise RuntimeError("protocol changed after it was fixed (LF-normalized sha256 differs from sidecar)")
    return {"raw_bytes_sha256": raw, "lf_normalized_sha256": lf, "sidecar_raw_bytes_sha256": side.get("raw_bytes_sha256", ""),
            "fixed_at": side.get("fixed_at", "")}


# ----------------------------------------------------------------------------
# calendar (NYSE full closures, 1994+), built on the S4 generator
# ----------------------------------------------------------------------------
def cpv_full_closures() -> set[str]:
    out = set(s4().nyse_full_closures(1994, 2027))
    # S4's generator observes MLK Day every year; it was a NYSE holiday only from 1998.
    for y in range(1994, 1998):
        out.discard(s4()._nth_weekday(y, 1, 0, 3).isoformat())
    out.update({"2001-09-11", "2001-09-12", "2001-09-13", "2001-09-14", "2004-06-11", "2007-01-02"})
    return out


def sessions(start: str, end: str) -> pd.DatetimeIndex:
    idx = pd.date_range(start, end, freq="B")
    return idx.difference(pd.to_datetime(sorted(cpv_full_closures()))).sort_values()


# ----------------------------------------------------------------------------
# data collection (--collect)
# ----------------------------------------------------------------------------
def fetch_yahoo_raw(ticker: str, start: str, end: str, attempts: int = 4) -> tuple[pd.DataFrame, str]:
    params = {"period1": int(pd.Timestamp(start, tz="UTC").timestamp()),
              "period2": int((pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)).timestamp()),
              "interval": "1d", "events": "div,splits", "includeAdjustedClose": "true"}
    url = YAHOO_URL.format(ticker=urllib.parse.quote(ticker)) + "?" + urllib.parse.urlencode(params)
    last = ""
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=YAHOO_HEADERS), timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            chart = payload.get("chart") or {}
            if chart.get("error") or not chart.get("result"):
                raise RuntimeError(f"Yahoo error for {ticker}: {chart.get('error')}")
            res = chart["result"][0]
            quote = (res.get("indicators") or {}).get("quote", [{}])[0]
            adj = ((res.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose")
            ts = res.get("timestamp") or []
            frame = pd.DataFrame({"date": pd.to_datetime(ts, unit="s", utc=True).date,
                                  "open": quote.get("open"), "high": quote.get("high"), "low": quote.get("low"),
                                  "close": quote.get("close"), "volume": quote.get("volume"),
                                  "adjclose": adj if adj is not None else quote.get("close")})
            frame["date"] = pd.to_datetime(frame["date"])
            frame = frame.set_index("date").sort_index()
            if frame.index.has_duplicates:
                raise RuntimeError(f"Yahoo returned duplicate dates for {ticker}")
            return frame, url
        except Exception as exc:
            last = repr(exc)
            time.sleep(4)
    raise RuntimeError(f"Yahoo fetch failed for {ticker}: {last}")


def _write_csv(frame: pd.DataFrame | pd.Series, path: Path, label: str = "date") -> dict[str, Any]:
    frame.to_csv(path, index_label=label)
    return {"path": path.name, "rows": int(len(frame)), "sha256": sha256_file(path)}


def collect(end: str | None) -> int:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    s4src = json.loads(S4_SOURCES.read_text(encoding="utf-8"))
    end = end or s4src["end_date"]
    src: dict[str, Any] = {"generated_at_utc": datetime.now(timezone.utc).isoformat(), "end_date": end,
                           "protocol_lf_sha256": lf_sha256(PROTOCOL), "single_source": "Yahoo chart API (index data; no second source)",
                           "calendar": {"generator": "cpv_full_closures in this script (S4 generator + pre-2009 rules)"}, "series": {}}
    stop: list[str] = []
    expected = sessions(INDEX_START, end)
    for name, ticker in (("SOX", "^SOX"), ("NDX", "^NDX")):
        try:
            frame, url = fetch_yahoo_raw(ticker, INDEX_START, end)
        except Exception as exc:
            stop.append(f"{ticker}: {exc!r}")
            continue
        info: dict[str, Any] = {"ticker": ticker, "url": url, "single_source": True}
        info["csv"] = _write_csv(frame, INPUT_DIR / f"{name}_yahoo_raw.csv")
        missing_close = frame.index[frame["close"].isna() | (frame["close"] <= 0)]
        info["null_or_nonpositive_close_dates"] = [d.date().isoformat() for d in missing_close]
        info["null_ohlc_other_rows"] = int(frame[["open", "high", "low"]].isna().any(axis=1).sum())
        extra = frame.index.difference(expected)
        absent = expected.difference(frame.index)
        info["first_date"], info["last_date"] = frame.index[0].date().isoformat(), frame.index[-1].date().isoformat()
        info["extra_sessions_vs_calendar"] = [d.date().isoformat() for d in extra][:50]
        info["missing_sessions_vs_calendar"] = [d.date().isoformat() for d in absent][:50]
        info["extra_count"], info["missing_count"] = int(len(extra)), int(len(absent))
        if frame.index[0] != pd.Timestamp(INDEX_START):
            stop.append(f"{ticker}: first row {info['first_date']} != {INDEX_START}")
        if len(missing_close):
            stop.append(f"{ticker}: {len(missing_close)} sessions with null/non-positive close")
        if len(extra) or len(absent):
            stop.append(f"{ticker}: session mismatch vs generated calendar extra={len(extra)} missing={len(absent)}")
        src["series"][name] = info
    try:
        soxx, surl = fetch_yahoo_raw("SOXX", SOXX_START, str(U_END.date()))
        sinfo = {"ticker": "SOXX", "url": surl, "single_source": True, "csv": _write_csv(soxx, INPUT_DIR / "SOXX_yahoo_2001_2010_raw.csv"),
                 "first_date": soxx.index[0].date().isoformat(), "last_date": soxx.index[-1].date().isoformat()}
        src["series"]["SOXX_2001_2010"] = sinfo
    except Exception as exc:
        stop.append(f"SOXX: {exc!r}")
    treasury, tq = s4().fetch_treasury_retry("1981-01-01", end)
    src["treasury"] = dict(tq)
    if treasury is None:
        stop.append("DGS3MO: unavailable (no zero-yield substitution allowed in this study)")
    else:
        src["treasury"]["csv"] = _write_csv(pd.DataFrame({"DGS3MO": treasury}), INPUT_DIR / "DGS3MO_full.csv")
        if treasury.index[0] > pd.Timestamp(INDEX_START):
            stop.append("DGS3MO starts after the index start")
        obs_days = set(treasury.index)
        no_obs = [d for d in expected if d not in obs_days]
        src["treasury"]["sessions_without_same_day_observation"] = int(len(no_obs))
        src["treasury"]["missing_handling"] = "last observation before the session is carried (rate_array); count recorded"
    src["status"] = "stopped" if stop else "passed"
    src["stop_reasons"] = stop
    SOURCES_JSON.write_text(json.dumps(clean(src), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": src["status"], "end_date": end, "stop_reasons": stop}, ensure_ascii=False))
    return 2 if stop else 0


def load_cpv_inputs() -> dict[str, Any]:
    src = json.loads(SOURCES_JSON.read_text(encoding="utf-8"))
    if src.get("status") != "passed":
        raise RuntimeError("CPV input collection did not pass; run --collect")
    out: dict[str, Any] = {"sources": src}
    for name in ("SOX", "NDX"):
        info = src["series"][name]
        path = INPUT_DIR / info["csv"]["path"]
        if sha256_file(path) != info["csv"]["sha256"]:
            raise RuntimeError(f"{name}: CSV hash differs from sources JSON")
        df = pd.read_csv(path, index_col="date", parse_dates=["date"])
        if not df.index.equals(sessions(INDEX_START, src["end_date"])):
            raise RuntimeError(f"{name}: calendar completeness audit failed")
        out[name] = df["close"].astype(float)
    sp = INPUT_DIR / src["series"]["SOXX_2001_2010"]["csv"]["path"]
    if sha256_file(sp) != src["series"]["SOXX_2001_2010"]["csv"]["sha256"]:
        raise RuntimeError("SOXX CSV hash differs")
    out["SOXX"] = pd.read_csv(sp, index_col="date", parse_dates=["date"])["adjclose"].astype(float)
    tp = INPUT_DIR / src["treasury"]["csv"]["path"]
    if sha256_file(tp) != src["treasury"]["csv"]["sha256"]:
        raise RuntimeError("DGS3MO hash differs")
    out["treasury_full"] = pd.read_csv(tp, index_col="date", parse_dates=["date"])["DGS3MO"].astype(float)
    return out


def load_s4_inputs() -> dict[str, Any]:
    """S4 inputs are read through S4's own loader, which checks every CSV hash against the S4 sources JSON."""
    data = s4().load_inputs()
    data["s4_sources_sha256"] = sha256_file(S4_SOURCES)
    data["s4_runner_sha256"] = sha256_file(S4_SCRIPT)
    return data


# ----------------------------------------------------------------------------
# series
# ----------------------------------------------------------------------------
@dataclass
class Series:
    name: str
    dates: pd.DatetimeIndex
    O: np.ndarray
    C: np.ndarray
    open_ok: np.ndarray
    days: np.ndarray
    rate: np.ndarray
    v: dict[int, np.ndarray] = field(default_factory=dict)
    first_valid: int = 0

    @property
    def n(self) -> int:
        return len(self.C)


def vol_ratio(C: np.ndarray, window: int) -> np.ndarray:
    return s4().c1_series(C, window, "expanding")


def attach_v(ser: Series) -> Series:
    ser.v = {w: vol_ratio(ser.C, w) for w in SIGMA_WINDOWS}
    firsts = []
    for w, arr in ser.v.items():
        ok = np.isfinite(arr)
        if not ok.any():
            raise RuntimeError(f"{ser.name}: v window {w} never valid")
        first = int(np.argmax(ok))
        if not ok[first:].all():
            raise RuntimeError(f"{ser.name}: v window {w} has gaps after first valid index")
        firsts.append(first)
    ser.first_valid = max(firsts)
    return ser


def synth_3x_returns(close: pd.Series, treasury: pd.Series | None) -> pd.Series:
    ret = close.pct_change()
    rate = s4().rate_array(close.index, treasury)  # DGS3MO/100, last observation strictly before the session
    r3 = 3.0 * ret - EXPENSE / 252.0 - 2.0 * rate / 252.0
    r3.iloc[0] = np.nan
    if (r3.dropna() <= -1.0).any():
        bad = r3.dropna()[r3.dropna() <= -1.0]
        raise RuntimeError(f"synthetic 3x return <= -100% on {[d.date().isoformat() for d in bad.index[:5]]}; stopping (no clipping)")
    return r3


def days_array(dates: pd.DatetimeIndex) -> np.ndarray:
    return np.r_[1.0, np.diff(dates.values.astype("datetime64[D]").astype(np.int64)).astype(float)]


def synthetic_series(name: str, close: pd.Series, treasury: pd.Series | None) -> Series:
    r3 = synth_3x_returns(close, treasury)
    level = (1.0 + r3.fillna(0.0)).cumprod().to_numpy(float)
    dates = close.index
    return attach_v(Series(name, dates, level.copy(), level, np.ones(len(dates), bool), days_array(dates),
                           s4().rate_array(dates, treasury)))


def actual_series(data: dict[str, Any]) -> Series:
    f = s4().build_features(data["frames"]["SOXL"], data["frames"]["SOXX"], data["split_days"]["SOXX"], data["treasury"])
    return attach_v(Series("A", f.dates, f.tO.copy(), f.tC.copy(), f.open_ok.copy(), f.days.copy(), f.rate.copy()))


# ----------------------------------------------------------------------------
# scalar reference engine (mirrors S4 simulate() arithmetic)
# ----------------------------------------------------------------------------
def band_pending(tgt: float, w: float, band: float) -> float | None:
    if tgt <= 1e-12:
        return 0.0 if w > 1e-12 else None
    if w <= 1e-12:
        return tgt
    if abs(tgt - w) >= band - 1e-12:
        return tgt
    return None


def decide_scalar(cfg: dict[str, Any], v_t: float, E: float, w: float, st: dict[str, Any], t: int) -> float | None:
    kind = cfg["kind"]
    if kind == "fixed":
        tgt = cfg["w"]
    elif kind == "bv":
        tgt = cfg["w"] * v_t
    elif kind == "bad":
        if E <= 0.80:
            st["stage"] = 2
        elif E <= 0.90 and st["stage"] < 1:
            st["stage"] = 1
        if st["stage"] == 2 and st["lock_t"] is None:
            st["lock_t"] = t
        tgt = (CAP, 0.333, 0.0)[st["stage"]]
    else:
        st["peak"] = max(st["peak"], E)
        F = FLOOR * (st["peak"] if cfg["floor"] == "raise" else 1.0)
        if st["lock"] or E <= F:
            if not st["lock"]:
                st["lock_t"] = t
            st["lock"] = True
            tgt = 0.0
        else:
            c = max(0.0, (E - F) / E)
            tgt = min(CAP, cfg["m"] * c) * (v_t if cfg["use_v"] else 1.0)
    return band_pending(tgt, w, cfg["band"])


def sim_window_scalar(ser: Series, s: int, L: int, cfg: dict[str, Any], cost_bps: float, cash_yield: bool = True,
                      v_override: np.ndarray | None = None) -> dict[str, Any]:
    if s < 1 or s + L - 1 >= ser.n:
        raise RuntimeError("invalid window")
    O, C, ok, days, rate = ser.O, ser.C, ser.open_ok, ser.days, ser.rate
    vs = v_override if v_override is not None else ser.v.get(cfg.get("sw", 20))
    cost = cost_bps / 10_000.0
    st: dict[str, Any] = {"lock": False, "stage": 0, "peak": 1.0, "lock_t": None}
    S, cash = 0.0, 1.0
    V, W = [1.0], []
    fills = stale = 0
    vt = float(vs[s - 1]) if vs is not None else 1.0
    pending = decide_scalar(cfg, vt, 1.0, 0.0, st, s - 1)
    for t in range(s, s + L):
        valid = bool(ok[t]) and math.isfinite(O[t]) and O[t] > 0
        if valid:
            S *= O[t] / C[t - 1]
        if cash_yield and cash > 0:
            cash *= 1.0 + rate[t] * days[t] / 365.0
        if pending is not None:
            if valid:
                v_open = S + cash
                delta = pending * v_open - S
                if abs(delta) > 1e-15:
                    c = cost * abs(delta)
                    S += delta
                    cash -= delta + c
                    fills += 1
                pending = None
            else:
                stale += 1
        if valid:
            S *= C[t] / O[t]
        else:
            S *= C[t] / C[t - 1]
        v = S + cash
        w = S / v
        V.append(v)
        W.append(w)
        vt = float(vs[t]) if vs is not None else 1.0
        pending = decide_scalar(cfg, vt, v, w, st, t)
    locked = bool(st["lock"]) or st["stage"] == 2
    return {"V": np.array(V), "W": np.array(W), "locked": locked, "lock_t": st["lock_t"], "fills": fills, "stale": stale}


# ----------------------------------------------------------------------------
# vectorised engine: one pass over all window starts (same arithmetic, same operation order)
# ----------------------------------------------------------------------------
def band_vec(tgt: np.ndarray, w: np.ndarray, band: float) -> np.ndarray:
    zero = tgt <= 1e-12
    out = np.full(tgt.shape, np.nan)
    out = np.where(zero & (w > 1e-12), 0.0, out)
    enter = ~zero & (w <= 1e-12)
    out = np.where(enter, tgt, out)
    adj = ~zero & ~enter & (np.abs(tgt - w) >= band - 1e-12)
    return np.where(adj, tgt, out)


def decide_vec(cfg: dict[str, Any], v_t: np.ndarray | None, E: np.ndarray, w: np.ndarray, st: dict[str, np.ndarray]) -> np.ndarray:
    kind = cfg["kind"]
    if kind == "fixed":
        tgt = np.full(E.shape, cfg["w"])
    elif kind == "bv":
        tgt = cfg["w"] * v_t
    elif kind == "bad":
        lvl = np.where(E <= 0.80, 2, np.where(E <= 0.90, 1, 0))
        st["stage"] = np.maximum(st["stage"], lvl)
        tgt = np.choose(st["stage"], [CAP, 0.333, 0.0])
        st["lock"] = st["stage"] == 2
    else:
        st["peak"] = np.maximum(st["peak"], E)
        F = FLOOR * (st["peak"] if cfg["floor"] == "raise" else 1.0)
        st["lock"] = st["lock"] | (E <= F)
        c = np.maximum(0.0, (E - F) / E)
        tgt = np.minimum(CAP, cfg["m"] * c) * (v_t if cfg["use_v"] else 1.0)
        tgt = np.where(st["lock"], 0.0, tgt)
    return band_vec(tgt, w, cfg["band"])


def sim_windows_vec(ser: Series, starts: np.ndarray, L: int, cfg: dict[str, Any], cost_bps: float,
                    cash_yield: bool = True) -> dict[str, np.ndarray]:
    starts = np.asarray(starts, dtype=int)
    m = len(starts)
    O, C, ok, days, rate = ser.O, ser.C, ser.open_ok, ser.days, ser.rate
    vs = ser.v.get(cfg.get("sw", 20))
    cost = cost_bps / 10_000.0
    S, cash = np.zeros(m), np.ones(m)
    st = {"lock": np.zeros(m, bool), "stage": np.zeros(m, int), "peak": np.ones(m)}
    minV, sumW, fills = np.ones(m), np.zeros(m), np.zeros(m, int)
    Vend = np.ones(m)
    pend = decide_vec(cfg, vs[starts - 1] if vs is not None else None, np.ones(m), np.zeros(m), st)
    for k in range(L):
        t = starts + k
        Ot, Ct, Cp = O[t], C[t], C[t - 1]
        valid = ok[t] & np.isfinite(Ot) & (Ot > 0)
        S = np.where(valid, S * (Ot / Cp), S)
        if cash_yield:
            cash = np.where(cash > 0, cash * (1.0 + rate[t] * days[t] / 365.0), cash)
        has = ~np.isnan(pend)
        do = has & valid
        v_open = S + cash
        delta = np.where(do, pend * v_open - S, 0.0)
        fill = np.abs(delta) > 1e-15
        c = np.where(fill, cost * np.abs(delta), 0.0)
        S = S + np.where(fill, delta, 0.0)
        cash = cash - np.where(fill, delta + c, 0.0)
        fills += fill
        pend = np.where(do, np.nan, pend)
        S = np.where(valid, S * (Ct / np.where(valid, Ot, 1.0)), S * (Ct / Cp))
        V = S + cash
        w = S / V
        minV = np.minimum(minV, V)
        sumW += w
        Vend = V
        pend = decide_vec(cfg, vs[t] if vs is not None else None, V, w, st)
    return {"final": Vend, "min": minV, "meanW": sumW / L, "locked": st["lock"].copy(), "fills": fills}


# ----------------------------------------------------------------------------
# window sets and metrics
# ----------------------------------------------------------------------------
def regime_of(ts: pd.Timestamp, prefix_ok: tuple[str, ...]) -> str | None:
    for name, (a, b) in REGIMES.items():
        if name[0] in prefix_ok and a <= ts.year <= b:
            return name
    return None


def window_table(ser: Series, L: int, last_idx: int, prefix_ok: tuple[str, ...]) -> pd.DataFrame:
    lo = max(ser.first_valid + 1, 1)
    hi = last_idx - L + 1
    if hi < lo:
        return pd.DataFrame(columns=["s", "end", "regime"])
    s = np.arange(lo, hi + 1)
    reg = [regime_of(ser.dates[i], prefix_ok) for i in s]
    return pd.DataFrame({"s": s, "end": s + L - 1, "regime": reg})


def cell_metrics(final: np.ndarray, minv: np.ndarray, locked: np.ndarray, meanw: np.ndarray, fills: np.ndarray,
                 s: np.ndarray, L: int) -> dict[str, Any]:
    n = len(final)
    if n == 0:
        return {"n": 0}
    ret = final - 1.0
    return {
        "n": int(n), "n_nonoverlap": int((int(s.max()) - int(s.min()) + L) // L),
        "final_median": float(np.median(ret)), "final_mean": float(np.mean(ret)), "final_p25": float(np.percentile(ret, 25)),
        "worst_final": float(ret.min()), "share_final_le_m20": float(np.mean(ret <= -0.20 + 1e-12)),
        "worst_min_equity": float(minv.min()), "median_min_equity": float(np.median(minv)),
        "share_min_le_078": float(np.mean(minv <= 0.78 + 1e-12)), "share_min_le_090": float(np.mean(minv <= 0.90 + 1e-12)),
        "lock_share": float(np.mean(locked)), "avg_eff_leverage": float(3.0 * np.mean(meanw)),
        "avg_fills": float(np.mean(fills)),
    }


@dataclass
class SegData:
    ser: Series
    last_idx: int
    prefix: tuple[str, ...]
    tables: dict[int, pd.DataFrame] = field(default_factory=dict)


def build_segments(a: Series, sox: Series, ndx: Series) -> dict[str, SegData]:
    u_last = int(sox.dates.get_loc(U_END))
    segs = {"U": SegData(sox, u_last, ("U",)), "A": SegData(a, a.n - 1, ("A",)), "N": SegData(ndx, ndx.n - 1, ("U", "A"))}
    for sd in segs.values():
        for L in LENGTHS:
            sd.tables[L] = window_table(sd.ser, L, sd.last_idx, sd.prefix)
    return segs


def run_key(cfg: str, cost: float, cash: bool) -> str:
    return f"{cfg}|{cost:g}bp|{'cash' if cash else 'nocash'}"


def evaluate_run(segs: dict[str, SegData], cfg_name: str, cost: float, cash: bool,
                 csv_rows: list[pd.DataFrame] | None = None) -> dict[str, Any]:
    cfg = CONFIGS[cfg_name]
    out: dict[str, Any] = {}
    for seg_name, sd in segs.items():
        cells: dict[str, dict[str, Any]] = {}
        for L in LENGTHS:
            tab = sd.tables[L]
            if tab.empty:
                continue
            res = sim_windows_vec(sd.ser, tab["s"].to_numpy(), L, cfg, cost, cash)
            reg = tab["regime"].to_numpy(object)
            names = [seg_name] + (SEG_REGIMES.get(seg_name) or ["U1", "U2", "U3", "U4", "A1", "A2", "A3"])
            for cell in names:
                mask = np.ones(len(tab), bool) if cell == seg_name else (reg == cell)
                cells.setdefault(cell, {})[str(L)] = cell_metrics(res["final"][mask], res["min"][mask], res["locked"][mask],
                                                                    res["meanW"][mask], res["fills"][mask],
                                                                    tab["s"].to_numpy()[mask], L)
            if csv_rows is not None and seg_name in ("U", "A"):
                csv_rows.append(pd.DataFrame({
                    "config": cfg_name, "length": L, "segment": seg_name, "regime": reg,
                    "start_date": sd.ser.dates[tab["s"].to_numpy()].date, "end_date": sd.ser.dates[tab["end"].to_numpy()].date,
                    "final_return": res["final"] - 1.0, "min_equity": res["min"], "locked": res["locked"],
                    "avg_eff_leverage": 3.0 * res["meanW"], "fills": res["fills"]}))
        out[seg_name] = cells
    return out


# ----------------------------------------------------------------------------
# cross-check (protocol appendix 2-A)
# ----------------------------------------------------------------------------
def cross_check(segs: dict[str, SegData], n_random: int = 120, n_lock: int = 100, seed: int = 20261001) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    report: dict[str, Any] = {"seed": seed, "max_rel_error": 0.0, "checked_windows": 0, "rows": []}
    plans = [(c, 10.0, True) for c in CONFIGS] + [("CPV", 50.0, False), ("CPV", 20.0, True), ("BAD", 50.0, False)]
    for cfg_name, cost, cash in plans:
        cfg = CONFIGS[cfg_name]
        cnt = lock_cnt = 0
        worst = 0.0
        for seg_name in ("U", "A"):
            sd = segs[seg_name]
            for L in LENGTHS:
                tab = sd.tables[L]
                if tab.empty:
                    continue
                starts_all = tab["s"].to_numpy()
                res_all = sim_windows_vec(sd.ser, starts_all, L, cfg, cost, cash)
                idx = rng.choice(len(starts_all), size=min(n_random, len(starts_all)), replace=False)
                lock_idx = np.where(res_all["locked"])[0]
                if len(lock_idx):
                    idx = np.union1d(idx, rng.choice(lock_idx, size=min(n_lock, len(lock_idx)), replace=False))
                # re-run only the sampled starts through the vector engine as well (tests index handling)
                res_sub = sim_windows_vec(sd.ser, starts_all[idx], L, cfg, cost, cash)
                for j, i in enumerate(idx):
                    sc = sim_window_scalar(sd.ser, int(starts_all[i]), L, cfg, cost, cash)
                    for key, a_, b_ in (("final", res_all["final"][i], sc["V"][-1]), ("min", res_all["min"][i], float(sc["V"].min())),
                                        ("meanW", res_all["meanW"][i], float(sc["W"].mean())),
                                        ("final_sub", res_sub["final"][j], sc["V"][-1])):
                        rel = abs(a_ - b_) / max(abs(b_), 1e-12)
                        worst = max(worst, rel)
                        if rel > 1e-12:
                            raise RuntimeError(f"cross-check mismatch {cfg_name} {seg_name} L={L} s={starts_all[i]} {key}: {a_} vs {b_}")
                    if bool(res_all["locked"][i]) != sc["locked"] or int(res_all["fills"][i]) != sc["fills"]:
                        raise RuntimeError(f"cross-check lock/fills mismatch {cfg_name} {seg_name} L={L} s={starts_all[i]}")
                    cnt += 1
                    lock_cnt += int(sc["locked"])
        report["rows"].append({"config": cfg_name, "cost_bps": cost, "cash_yield": cash, "windows": cnt, "locked_windows": lock_cnt,
                               "max_rel_error": worst})
        report["checked_windows"] += cnt
        report["max_rel_error"] = max(report["max_rel_error"], worst)
        if cnt < 200:
            raise RuntimeError(f"cross-check sampled only {cnt} windows for {cfg_name}")
    return report


# ----------------------------------------------------------------------------
# gates
# ----------------------------------------------------------------------------
ALL_CELLS = ["U", "U1", "U2", "U3", "U4", "A", "A1", "A2", "A3"]
U_CELLS = ["U", "U1", "U2", "U3", "U4"]


def _cells(run: dict[str, Any], names: list[str], L: int) -> list[tuple[str, dict[str, Any]]]:
    out = []
    for nm in names:
        seg = nm[0]
        c = run.get(seg, {}).get(nm, {}).get(str(L))
        out.append((nm, c if c else {"n": 0}))
    return out


def gate_h1(run: dict[str, Any], names: list[str] = ALL_CELLS) -> dict[str, Any]:
    fails, na = [], []
    for L in LENGTHS:
        for nm, c in _cells(run, names, L):
            if c["n"] == 0:
                na.append(f"{nm}/{L}")
            elif c["share_min_le_078"] > 0.02 + 1e-12 or c["worst_min_equity"] < 0.75 - 1e-12:
                fails.append({"cell": nm, "length": L, "share_min_le_078": c["share_min_le_078"], "worst_min_equity": c["worst_min_equity"]})
    return {"pass": not fails, "failures": fails, "not_applicable": na}


def gate_h3(run: dict[str, Any], names: list[str] = ALL_CELLS) -> dict[str, Any]:
    fails, na = [], []
    for nm, c in _cells(run, names, 252):
        if c["n"] == 0:
            na.append(f"{nm}/252")
        elif c["lock_share"] > 0.15 + 1e-12:
            fails.append({"cell": nm, "length": 252, "lock_share": c["lock_share"]})
    return {"pass": not fails, "failures": fails, "not_applicable": na}


def gate_h2(cpv: dict[str, Any], bv: dict[str, Any], seg: str) -> dict[str, Any]:
    c = cpv.get(seg, {}).get(seg, {}).get("756")
    b = bv.get(seg, {}).get(seg, {}).get("756")
    if not c or not b or c["n"] == 0 or b["n"] == 0:
        return {"pass": False, "note": "no 3-year windows", "cpv_median": None, "bv10_median": None}
    cm, bm = c["final_median"], b["final_median"]
    ok = (cm >= 0.9 * bm) if (cm > 0 and bm > 0) else (cm >= bm)
    return {"pass": bool(ok), "cpv_median": cm, "bv10_median": bm}


def evaluate_gates(runs: dict[str, dict[str, Any]], segs: dict[str, SegData]) -> dict[str, Any]:
    k = lambda cfg, cost=10.0, cash=True: runs[run_key(cfg, cost, cash)]
    cpv = k("CPV")
    h1, h3 = gate_h1(cpv), gate_h3(cpv)
    h2 = {"A": gate_h2(cpv, k("BV10"), "A"), "U": gate_h2(cpv, k("BV10"), "U")}
    h2["pass"] = bool(h2["A"]["pass"] and h2["U"]["pass"])
    nb = {}
    for name in NEIGHBORS:
        r = k(name)
        a, b = gate_h1(r), gate_h3(r)
        nb[name] = {"H1": a["pass"], "H3": b["pass"], "pass": bool(a["pass"] and b["pass"])}
    n_pass = sum(1 for v in nb.values() if v["pass"])
    cpv20, cpv50 = k("CPV", 20.0), k("CPV", 50.0)
    h20 = {"H1": gate_h1(cpv20)["pass"], "H2": gate_h2(cpv20, k("BV10", 20.0), "A")["pass"] and gate_h2(cpv20, k("BV10", 20.0), "U")["pass"],
           "H3": gate_h3(cpv20)["pass"]}
    h50 = {"H1": gate_h1(cpv50)["pass"]}
    nocash = k("CPV", 10.0, False)
    h4 = {"neighbors": nb, "neighbors_passing": n_pass, "neighbors_majority": bool(n_pass >= 4), "cost_20bp": h20,
          "cost_20bp_pass": bool(all(h20.values())), "cost_50bp": h50, "cost_50bp_pass": bool(h50["H1"]),
          "nocash_report_only": {"H1": gate_h1(nocash)["pass"], "H3": gate_h3(nocash)["pass"],
                                 "H2": bool(gate_h2(nocash, k("BV10", 10.0, False), "A")["pass"] and gate_h2(nocash, k("BV10", 10.0, False), "U")["pass"])}}
    h4["pass"] = bool(h4["neighbors_majority"] and h4["cost_20bp_pass"] and h4["cost_50bp_pass"])
    h5 = {"H1": gate_h1(cpv, U_CELLS), "H3": gate_h3(cpv, U_CELLS)}
    h5["pass"] = bool(h5["H1"]["pass"] and h5["H3"]["pass"])
    nu = (cpv["U"]["U"]["252"]["n_nonoverlap"] if "252" in cpv.get("U", {}).get("U", {}) else 0)
    na = (cpv["A"]["A"]["252"]["n_nonoverlap"] if "252" in cpv.get("A", {}).get("A", {}) else 0)
    h6 = {"nonoverlap_1y_U": nu, "nonoverlap_1y_A": na, "total": nu + na}
    all_pass = bool(h1["pass"] and h2["pass"] and h3["pass"] and h4["pass"] and h5["pass"])
    if all_pass:
        verdict = "S5 제안 후보(forward shadow 필요)"
    elif not (h1["pass"] and h3["pass"] and h5["pass"]):
        verdict = "기각"
    else:
        verdict = "검토 전용"
    return {"H1": h1, "H2": h2, "H3": h3, "H4": h4, "H5": h5, "H6": h6, "verdict": verdict}


# ----------------------------------------------------------------------------
# additional reports
# ----------------------------------------------------------------------------
def synthetic_validation(sox_close: pd.Series, treasury_full: pd.Series, soxl_close: pd.Series) -> dict[str, Any]:
    r3 = synth_3x_returns(sox_close, treasury_full)
    soxl = soxl_close.pct_change()
    common = soxl.dropna().index.intersection(r3.dropna().index)
    a, b = r3.loc[common], soxl.loc[common]
    diff = a - b
    years = (common[-1] - common[0]).days / 365.25
    cum_a, cum_b = float((1 + a).prod()), float((1 + b).prod())
    return {"sessions": int(len(common)), "first": common[0].date().isoformat(), "last": common[-1].date().isoformat(),
            "mean_daily_diff_synth_minus_soxl": float(diff.mean()), "std_daily_diff": float(diff.std()),
            "corr_daily": float(np.corrcoef(a, b)[0, 1]), "max_abs_daily_diff": float(diff.abs().max()),
            "max_abs_diff_date": diff.abs().idxmax().date().isoformat(),
            "annualised_cumulative_diff": float((cum_a / cum_b) ** (1.0 / years) - 1.0), "cum_synth": cum_a, "cum_soxl": cum_b,
            "note": "SOXL's underlying index changed over time (확인 필요). ^SOX is a price index (no dividends)."}


def u_data_check(sox_close: pd.Series, soxx_adj: pd.Series) -> dict[str, Any]:
    r = sox_close.pct_change()
    big = r[r.abs() >= 0.15]
    rx = soxx_adj.pct_change()
    common = r.dropna().index.intersection(rx.dropna().index)
    common = common[(common >= pd.Timestamp(SOXX_START)) & (common <= U_END)]
    diff = (r.loc[common] - rx.loc[common])
    suspects = diff[diff.abs() >= 0.08]
    big_rows = []
    for d, val in big.items():
        covered = d in rx.index and d >= pd.Timestamp(SOXX_START) + pd.Timedelta(days=1) and d <= U_END
        big_rows.append({"date": d.date().isoformat(), "sox_return": float(val),
                         "soxx_return": float(rx.get(d, np.nan)) if covered else None,
                         "status": "cross-checked" if covered else "교차검증 불가(확인 필요)"})
    return {"sox_abs_ret_ge_15pct": big_rows, "soxx_overlap_sessions": int(len(common)),
            "corr_sox_soxx_daily": float(np.corrcoef(r.loc[common], rx.loc[common])[0, 1]),
            "max_abs_diff": float(diff.abs().max()), "max_abs_diff_date": diff.abs().idxmax().date().isoformat(),
            "suspect_days_diff_ge_8pp": [{"date": d.date().isoformat(), "diff": float(v)} for d, v in suspects.items()],
            "stop": bool(len(suspects))}


def crash_paths(segs: dict[str, SegData]) -> list[dict[str, Any]]:
    out = []
    for label, day, seg in CRASH_STARTS:
        sd = segs[seg]
        s = int(sd.ser.dates.searchsorted(pd.Timestamp(day)))
        for L in LENGTHS:
            row: dict[str, Any] = {"label": label, "segment": seg, "start_session": sd.ser.dates[s].date().isoformat(), "length": L}
            if s - 1 < sd.ser.first_valid or s + L - 1 > sd.last_idx:
                row["status"] = "해당 없음(창 조건 불충족)"
                out.append(row)
                continue
            row["status"] = "ok"
            for cfg_name in ("CPV", "BAD", "B0"):
                r = sim_window_scalar(sd.ser, s, L, CONFIGS[cfg_name], 10.0)
                V, W = r["V"], r["W"]
                item = {"final_return": float(V[-1] - 1.0), "min_equity": float(V.min()),
                        "min_equity_date": sd.ser.dates[s - 1 + int(V.argmin())].date().isoformat() if V.argmin() > 0 else sd.ser.dates[s - 1].date().isoformat(),
                        "locked": r["locked"], "lock_date": sd.ser.dates[r["lock_t"]].date().isoformat() if r["lock_t"] is not None else None,
                        "fills": r["fills"]}
                if cfg_name == "CPV":
                    item.update({"equity_63": float(V[min(63, L)]), "equity_126": float(V[min(126, L)]), "equity_252": float(V[min(252, L)]),
                                 "max_weight": float(W.max()), "mean_weight": float(W.mean())})
                row[cfg_name] = item
            out.append(row)
    return out


def current_condition(a: Series) -> dict[str, Any]:
    v = float(a.v[20][-1])
    return {"as_of": a.dates[-1].date().isoformat(), "v_sigma20": v, "c_at_baseline_equity": 0.2,
            "rule_weight": min(CAP, 2.0 * 0.2) * v, "rule_effective_leverage_cap": 3.0 * min(CAP, 2.0 * 0.2) * v,
            "structural_cap_effective_leverage": 3.0 * CAP * v,
            "note": "보고 전용. 기준 자산 = 2026-09-29 자산일 때 규칙상 상한. 주문·수량이 아니다."}


# ----------------------------------------------------------------------------
# --run
# ----------------------------------------------------------------------------
def run(args: argparse.Namespace) -> int:
    t0 = time.time()
    proto = check_protocol()
    inputs = load_cpv_inputs()
    a_data = load_s4_inputs()
    sox_close, ndx_close = inputs["SOX"], inputs["NDX"]
    check = u_data_check(sox_close, inputs["SOXX"])
    if check["stop"]:
        print(json.dumps({"status": "stopped_data_anomaly", "suspect_days": check["suspect_days_diff_ge_8pp"]}, ensure_ascii=False))
        return 2
    treasury_full = inputs["treasury_full"]
    sox = synthetic_series("U", sox_close, treasury_full)
    ndx = synthetic_series("N", ndx_close, treasury_full)
    a = actual_series(a_data)
    segs = build_segments(a, sox, ndx)
    meta = {"protocol": proto, "s4_sources_sha256": a_data["s4_sources_sha256"], "s4_runner_sha256": a_data["s4_runner_sha256"],
            "runner_sha256": sha256_file(Path(__file__).resolve()), "cpv_sources_sha256": sha256_file(SOURCES_JSON),
            "a_first_date": a.dates[0].date().isoformat(), "a_last_date": a.dates[-1].date().isoformat(),
            "u_first_date": sox.dates[0].date().isoformat(), "u_last_date": U_END.date().isoformat(),
            "first_valid_index": {"A": a.first_valid, "U": sox.first_valid, "N": ndx.first_valid},
            "window_counts": {k: {str(L): int(len(sd.tables[L])) for L in LENGTHS} for k, sd in segs.items()}}
    cc = cross_check(segs)
    print(f"cross-check ok: {cc['checked_windows']} windows, max rel error {cc['max_rel_error']:.2e}", flush=True)
    runs: dict[str, dict[str, Any]] = {}
    csv_rows: list[pd.DataFrame] = []
    plan: list[tuple[str, float, bool]] = [(c, 10.0, True) for c in CONFIGS]
    plan += [(c, cost, True) for cost in (20.0, 50.0) for c in MAIN_SET]
    plan += [(c, 10.0, False) for c in MAIN_SET]
    for cfg_name, cost, cash in plan:
        use_csv = csv_rows if (cost == 10.0 and cash and cfg_name in MAIN_CSV_CONFIGS) else None
        full = evaluate_run(segs, cfg_name, cost, cash, use_csv)
        runs[run_key(cfg_name, cost, cash)] = full
    gates = evaluate_gates(runs, segs)
    results = {
        "meta": meta, "cross_check": cc, "runs": {k: {seg: v for seg, v in r.items() if seg in ("U", "A")} for k, r in runs.items()},
        "ndx_aux_report_only": {k: r["N"] for k, r in runs.items() if r.get("N") and k.endswith("|10bp|cash") and k.split("|")[0] in MAIN_SET},
        "gates": gates, "synthetic_validation": synthetic_validation(sox_close, treasury_full, pd.Series(a.C, index=a.dates)),
        "u_data_check": check, "crash_paths": crash_paths(segs), "current_condition": current_condition(a),
        "synthetic_ndx_note": "^NDX aux: same synthetic formula, close-fill throughout, report only (appendix 1-15).",
        "treasury_check_overlap": treasury_overlap_check(a_data["treasury"], treasury_full),
        "elapsed_seconds": round(time.time() - t0, 1), "post_hoc": [],
        "authority": {"order_authority": False, "quantity_authority": "none", "grade": "D/C research"},
    }
    RESULTS_JSON.write_text(json.dumps(clean(results), ensure_ascii=False, indent=2), encoding="utf-8")
    pd.concat(csv_rows, ignore_index=True).to_csv(WINDOWS_CSV, index=False, float_format="%.10g")
    write_report(results)
    print(json.dumps({"status": "done", "verdict": gates["verdict"], "elapsed": results["elapsed_seconds"]}, ensure_ascii=False))
    return 0


def treasury_overlap_check(s4_t: pd.Series | None, full: pd.Series) -> dict[str, Any]:
    if s4_t is None:
        return {"status": "no S4 treasury"}
    common = s4_t.index.intersection(full.index)
    d = (s4_t.loc[common] - full.loc[common]).abs()
    return {"overlap_rows": int(len(common)), "max_abs_diff_pct_points": float(d.max()) if len(d) else None}


# ----------------------------------------------------------------------------
# report (Korean, conclusion first)
# ----------------------------------------------------------------------------
def pct(x: Any, nd: int = 1) -> str:
    return "-" if x is None else f"{x * 100:.{nd}f}%"


def write_report(res: dict[str, Any]) -> None:
    g, runs = res["gates"], res["runs"]
    mark = lambda ok: "통과" if ok else "실패"
    L: list[str] = []
    L.append("# SOXL CPV 시작일 이동 창 검증 결과 (2026-10-01)\n")
    L.append("## 결론\n")
    L.append(f"- **판정: {g['verdict']}**  (연구 등급 D/C, 활성화 권한 없음. 정책 반영은 S5 제안 → S6 Judge → S7 사용자 승인 → forward shadow 뒤.)")
    fails = [n for n in ("H1", "H2", "H3", "H4", "H5") if not g[n]["pass"]]
    L.append(f"- 게이트 실패: {', '.join(fails) if fails else '없음'}. 상세는 아래 게이트 표.")
    L.append("- 사전 명시: m = 2.0은 2011~2025 실제 데이터를 본 뒤 고른 값이라 A 결과에는 설계 오염 가능성이 있다. U(1994~2010 합성)는 이 규칙에 쓴 적 없는 유일한 깨끗한 검증이다.")
    L.append(f"- 벡터화 엔진 교차검증: {res['cross_check']['checked_windows']}개 창, 최대 상대오차 {res['cross_check']['max_rel_error']:.1e}.\n")
    L.append("## 게이트 표 (CPV 기본값, 10bp, 현금 이자 포함)\n")
    L.append("| 게이트 | 결과 | 세부 |\n|---|---|---|")
    h1 = g["H1"]
    L.append(f"| H1 바닥 유지(필수) | {mark(h1['pass'])} | 실패 칸 {len(h1['failures'])}개" + (": " + ", ".join(f"{f['cell']}/{f['length']}(≤0.78 비율 {pct(f['share_min_le_078'])}, 최악 {f['worst_min_equity']:.3f})" for f in h1["failures"][:8]) if h1["failures"] else "") + f"; 해당 없음 {', '.join(h1['not_applicable']) or '없음'} |")
    h2 = g["H2"]
    L.append(f"| H2 성장 | {mark(h2['pass'])} | A 3년 중앙값 CPV {pct(h2['A']['cpv_median'])} vs BV10 {pct(h2['A']['bv10_median'])}; U 3년 CPV {pct(h2['U']['cpv_median'])} vs BV10 {pct(h2['U']['bv10_median'])} |")
    h3 = g["H3"]
    L.append(f"| H3 잠금 | {mark(h3['pass'])} | 실패 칸 {len(h3['failures'])}개" + (": " + ", ".join(f"{f['cell']}(잠금 {pct(f['lock_share'])})" for f in h3["failures"][:8]) if h3["failures"] else "") + " |")
    h4 = g["H4"]
    L.append(f"| H4 견고성 | {mark(h4['pass'])} | 이웃 통과 {h4['neighbors_passing']}/7(과반 {mark(h4['neighbors_majority'])}), 20bp {mark(h4['cost_20bp_pass'])}, 50bp H1 {mark(h4['cost_50bp_pass'])}; 현금 이자 0% 병기 H1 {mark(h4['nocash_report_only']['H1'])}/H2 {mark(h4['nocash_report_only']['H2'])}/H3 {mark(h4['nocash_report_only']['H3'])} |")
    h5 = g["H5"]
    L.append(f"| H5 미사용 구간 U | {mark(h5['pass'])} | U에서 H1 {mark(h5['H1']['pass'])}, H3 {mark(h5['H3']['pass'])} |")
    h6 = g["H6"]
    L.append(f"| H6 표본(보고) | - | 겹치지 않는 1년 창: U {h6['nonoverlap_1y_U']}, A {h6['nonoverlap_1y_A']}, 합계 {h6['total']} |\n")
    L.append("이웃 7개: " + ", ".join(f"{k} {mark(v['pass'])}" for k, v in h4["neighbors"].items()) + "\n")
    cols = "| 칸 | 설정 | 창 수 | 겹치지 않는 창 | 최종 중앙값 | 평균 | 하위 25% | 최악 최종 | 최저 자산(최악) | ≤0.78 비율 | ≤0.90 비율 | 최종 ≤−20% | 잠금 | 평균 유효 레버리지 |\n|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"
    def table(cfgs: list[str], key_fmt, length: int, cost_label: str) -> None:
        L.append(f"\n### 창 {length}세션 ({'1년' if length == 252 else '3년'}), {cost_label}\n")
        L.append(cols)
        for cell in ALL_CELLS:
            for c in cfgs:
                r = runs[key_fmt(c)].get(cell[0], {}).get(cell, {}).get(str(length))
                if not r or r["n"] == 0:
                    L.append(f"| {cell} | {c} | 해당 없음 |" + " |" * 11)
                    continue
                L.append(f"| {cell} | {c} | {r['n']} | {r['n_nonoverlap']} | {pct(r['final_median'])} | {pct(r['final_mean'])} | {pct(r['final_p25'])} | {pct(r['worst_final'])} | {r['worst_min_equity']:.3f} | {pct(r['share_min_le_078'])} | {pct(r['share_min_le_090'])} | {pct(r['share_final_le_m20'])} | {pct(r['lock_share'])} | {r['avg_eff_leverage']:.2f}x |")
    L.append("## 기준선 대비 표 (U·A·세부 국면, 10bp)")
    for length in LENGTHS:
        table(MAIN_SET, lambda c: run_key(c, 10.0, True), length, "10bp")
    L.append("\n## 이웃 표 (CPV 이웃 7개 + 바닥 올림(보고만), 10bp)")
    for length in LENGTHS:
        table(NEIGHBORS + ["CPV_floorRaise"], lambda c: run_key(c, 10.0, True), length, "10bp")
    L.append("\n## 비용·현금 이자 민감도 (CPV와 기준선)")
    for label, cost, cash in (("20bp", 20.0, True), ("50bp", 50.0, True), ("10bp, 현금 이자 0%", 10.0, False)):
        for length in LENGTHS:
            table(MAIN_SET, lambda c, cost=cost, cash=cash: run_key(c, cost, cash), length, label)
    sv = res["synthetic_validation"]
    L.append("\n## 합성 검증 (보고만): 합성 3배(^SOX) vs 실제 SOXL, 2010-03-11~2026-09-29\n")
    L.append("| 항목 | 값 |\n|---|---|")
    L.append(f"| 비교 세션 수 | {sv['sessions']} ({sv['first']}~{sv['last']}) |")
    L.append(f"| 일간 수익률 차이 평균(합성−실제) | {sv['mean_daily_diff_synth_minus_soxl'] * 100:.4f}%p |")
    L.append(f"| 일간 수익률 차이 표준편차 | {sv['std_daily_diff'] * 100:.3f}%p |")
    L.append(f"| 일간 상관 | {sv['corr_daily']:.4f} |")
    L.append(f"| 최대 일간 차이 | {sv['max_abs_daily_diff'] * 100:.2f}%p ({sv['max_abs_diff_date']}) |")
    L.append(f"| 연 누적 차이(합성/실제) | {pct(sv['annualised_cumulative_diff'])} (누적 합성 {sv['cum_synth']:.2f}배, 실제 {sv['cum_soxl']:.2f}배) |")
    L.append("- 확인 필요: SOXL 기준 지수가 시기별로 바뀌었을 수 있다(^SOX는 배당 제외 가격지수).\n")
    ck = res["u_data_check"]
    L.append("## U 데이터 점검 (보고만)\n")
    L.append(f"- ^SOX 대 Yahoo SOXX(2001-07-13~2010-03-10) 일간 수익률 상관 {ck['corr_sox_soxx_daily']:.4f}, 최대 차이 {ck['max_abs_diff'] * 100:.2f}%p ({ck['max_abs_diff_date']}), 8%p 이상 차이 날 {len(ck['suspect_days_diff_ge_8pp'])}개.")
    L.append(f"- ^SOX 일간 |수익률| ≥ 15%인 날 {len(ck['sox_abs_ret_ge_15pct'])}개:\n")
    L.append("| 날짜 | ^SOX | SOXX | 상태 |\n|---|---|---|---|")
    for r in ck["sox_abs_ret_ge_15pct"]:
        L.append(f"| {r['date']} | {pct(r['sox_return'], 2)} | {pct(r['soxx_return'], 2)} | {r['status']} |")
    L.append("\n## 급락 국면 시작 창 경로 요약 (보고 전용, 10bp)\n")
    L.append("| 국면 | 시작 세션 | 창 | CPV 최종 | CPV 최저(날짜) | 잠금 날짜 | 63/126/252세션 자산 | 최대/평균 비중 | 체결 | BAD 최종/최저 | B0 최종/최저 |\n|---|---|---|---|---|---|---|---|---|---|---|")
    for r in res["crash_paths"]:
        if r["status"] != "ok":
            L.append(f"| {r['label']} | {r['start_session']} | {r['length']} | {r['status']} |" + " |" * 7)
            continue
        c, b, z = r["CPV"], r["BAD"], r["B0"]
        L.append(f"| {r['label']} | {r['start_session']} | {r['length']} | {pct(c['final_return'])} | {c['min_equity']:.3f} ({c['min_equity_date']}) | {c['lock_date'] or '-'} | {c['equity_63']:.3f}/{c['equity_126']:.3f}/{c['equity_252']:.3f} | {c['max_weight']:.3f}/{c['mean_weight']:.3f} | {c['fills']} | {pct(b['final_return'])}/{b['min_equity']:.3f} | {pct(z['final_return'])}/{z['min_equity']:.3f} |")
    cc_ = res["current_condition"]
    L.append(f"\n## 현재 조건 표시 (보고 전용, 주문·수량 아님)\n")
    L.append(f"- 기준일 {cc_['as_of']}, 기준 자산 = 그날 자산(c = 0.2)일 때 규칙상 유효 레버리지 상한 {cc_['rule_effective_leverage_cap']:.2f}x (v = {cc_['v_sigma20']:.3f}), 구조적 상한(c ≥ 0.317) {cc_['structural_cap_effective_leverage']:.2f}x.")
    L.append("\n## ^NDX 합성 3배 보조 (보고만, 전 구간 종가 체결, 시작 연도 국면별, 10bp)\n")
    L.append("| 칸 | 창 | 설정 | 창 수 | 최종 중앙값 | 하위 25% | 최악 최종 | 최저 자산(최악) | ≤0.78 비율 | 잠금 |\n|---|---|---|---|---|---|---|---|---|---|")
    for cell in ["N"] + list(REGIMES):
        for length in LENGTHS:
            for c in MAIN_SET:
                r = res["ndx_aux_report_only"].get(run_key(c, 10.0, True), {}).get(cell if cell != "N" else "N", {}).get(str(length))
                if not r or r["n"] == 0:
                    continue
                L.append(f"| {cell} | {length} | {c} | {r['n']} | {pct(r['final_median'])} | {pct(r['final_p25'])} | {pct(r['worst_final'])} | {r['worst_min_equity']:.3f} | {pct(r['share_min_le_078'])} | {pct(r['lock_share'])} |")
    L.append("\n## 한계와 확인 필요\n")
    L.append("- ^SOX·^NDX는 배당 제외 가격지수라 합성 3배 수익이 실제보다 조금 낮게 나올 수 있다(부록 2-C).")
    L.append("- 지수 데이터는 Yahoo 단일 출처이며 교차 출처 검증이 없다. U 구간 체결은 종가 + 하루 지연 가정이며 실제 SOXL은 2010년 이전에 없었다.")
    L.append("- 합성 3배는 일간 재조정 공식 모형이다(추적 오차, 스왑·차입 비용의 시기별 차이, 기준 지수 변경은 반영하지 않음).")
    L.append("- 창이 겹치므로 창 수는 독립 표본 수가 아니다. 독립에 가까운 표본은 '겹치지 않는 창' 열이다.")
    L.append("- m = 2.0은 in-sample 선택(사전 명시). A 결과는 설계 오염 가능성이 있다.")
    L.append("- 사전 등록 외 post-hoc 탐색 없음. 세금·환율 제외.")
    L.append("- 정책·상태·주문에는 어떤 권한도 없다. S5 제안 → S6 Judge → S7 사용자 승인 → forward shadow 이전에는 활성화하지 않는다.")
    RESULTS_MD.write_text("\n".join(L) + "\n", encoding="utf-8")


# ----------------------------------------------------------------------------
# --self-test
# ----------------------------------------------------------------------------
def _toy_series(n: int = 700, seed: int = 7, open_equals_close: bool = False, crash: bool = False) -> Series:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2015-01-05", periods=n)
    ret = rng.normal(0.0008, 0.03, n)
    ret[0] = 0.0
    if crash:
        ret[300:303] = -0.45
        ret[303:320] = 0.06
    C = 100.0 * np.cumprod(1.0 + ret)
    gap = rng.normal(0.0, 0.01, n)
    O = C * np.r_[1.0, C[:-1] / C[1:]] * 0.0 + np.r_[C[0], C[:-1]] * (1.0 + gap)
    if open_equals_close:
        O = C.copy()
    rate = np.full(n, 0.03)
    ser = Series("toy", dates, O, C, np.ones(n, bool), days_array(dates), rate)
    return attach_v(ser)


def self_test() -> int:
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, note: str = "") -> None:
        results.append((name, bool(ok), note))

    cfg_all = {k: v for k, v in CONFIGS.items()}
    # 1. no future information: prefix history gives identical v and identical window paths
    ser = _toy_series(700, crash=True)
    t0 = 520
    pre = Series("pre", ser.dates[:t0 + 1], ser.O[:t0 + 1], ser.C[:t0 + 1], ser.open_ok[:t0 + 1], ser.days[:t0 + 1], ser.rate[:t0 + 1])
    attach_v(pre)
    same_v = all(np.array_equal(ser.v[w][:t0 + 1], pre.v[w], equal_nan=True) for w in SIGMA_WINDOWS)
    s_, L_ = ser.first_valid + 1, 200
    same_path = all(np.array_equal(sim_window_scalar(ser, s_, L_, cfg, 10.0)["V"], sim_window_scalar(pre, s_, L_, cfg, 10.0)["V"]) for cfg in cfg_all.values())
    check("1 no-lookahead (truncated history == full history)", same_v and same_path)

    # 2. floor lock: after E <= F the book goes to cash and never restarts
    ser_c = _toy_series(700, crash=True)
    lock_seen = False
    ok2 = True
    for s in range(ser_c.first_valid + 1, 420):
        r = sim_window_scalar(ser_c, s, 250, CONFIGS["CPV"], 10.0)
        if r["locked"]:
            lock_seen = True
            li = r["lock_t"] - s + 1  # V index of the locking close
            ok2 &= bool(r["V"][li] <= 0.80 + 1e-12) and bool(np.all(r["W"][li:] <= 1e-9))
            # weight after lock stays zero even if prices recover
            ok2 &= bool(np.all(np.diff(r["V"][li + 1:]) >= -1e-12))
    bad = sim_window_scalar(ser_c, 250, 250, CONFIGS["BAD"], 10.0)
    check("2 floor lock (cash until window end, no restart)", lock_seen and ok2, f"lock windows seen={lock_seen}")

    # 3. fill timing: real-open windows fill at t+1 open; synthetic windows fill at t+1 close
    n = 60
    dates = pd.bdate_range("2020-01-06", periods=n)
    C = np.linspace(100.0, 130.0, n) * (1.0 + 0.02 * np.sin(np.arange(n)))
    O = C * 1.01
    flat = Series("t", dates, O.copy(), C.copy(), np.ones(n, bool), days_array(dates), np.zeros(n))
    fixed = dict(kind="fixed", w=0.5, band=0.10)
    r = sim_window_scalar(flat, 10, 5, fixed, 0.0, cash_yield=False)
    expect_open = 1.0 + 0.5 * (C[10] / O[10] - 1.0)
    syn = Series("s", dates, C.copy(), C.copy(), np.ones(n, bool), days_array(dates), np.zeros(n))
    r2 = sim_window_scalar(syn, 10, 5, fixed, 0.0, cash_yield=False)
    expect_close = 1.0
    expect_next = 1.0 + 0.5 * (C[11] / C[10] - 1.0)
    check("3 fill timing (open t+1 real / close t+1 synthetic)",
          abs(r["V"][1] - expect_open) < 1e-14 and abs(r2["V"][1] - expect_close) < 1e-14 and abs(r2["V"][2] - expect_next) < 1e-12)

    # 4. synthetic 3x formula by hand
    cl = pd.Series([100.0, 102.0, 99.96], index=pd.to_datetime(["2020-01-02", "2020-01-03", "2020-01-06"]))
    tr = pd.Series([4.0, 5.0], index=pd.to_datetime(["2019-12-31", "2020-01-03"]))
    r3 = synth_3x_returns(cl, tr)
    e1 = 3 * 0.02 - 0.0095 / 252 - 2 * (4.0 / 100) / 252          # rate known before 2020-01-03 is 12-31 (4%)
    e2 = 3 * (99.96 / 102.0 - 1.0) - 0.0095 / 252 - 2 * (5.0 / 100) / 252
    check("4 synthetic 3x formula (hand check)", abs(r3.iloc[1] - e1) < 1e-15 and abs(r3.iloc[2] - e2) < 1e-15 and math.isnan(r3.iloc[0]))

    # 5. cost and band rule (0-entry / 0-exit exceptions)
    c5 = [band_pending(0.45, 0.40, 0.10) is None, band_pending(0.50, 0.40, 0.10) == 0.50, band_pending(0.05, 0.0, 0.10) == 0.05,
          band_pending(0.0, 0.05, 0.10) == 0.0, band_pending(0.0, 0.0, 0.10) is None, band_pending(0.45, 0.40, 0.05) == 0.45]
    flat2 = Series("t", dates, C.copy(), C.copy(), np.ones(n, bool), days_array(dates), np.zeros(n))
    rc = sim_window_scalar(flat2, 10, 1, dict(kind="fixed", w=0.5, band=0.10), 10.0, cash_yield=False)
    cost_ok = abs(rc["V"][1] - (1.0 - 0.5 * 0.001)) < 1e-14
    check("5 cost (10bp of traded notional) and band rule", all(c5) and cost_ok)

    # 6. window boundary: sigma median uses data through t only; first valid index as specified
    ser6 = _toy_series(700, seed=11)
    future = ser6.C.copy()
    future[400:] *= np.linspace(1.0, 3.0, len(future) - 400)
    alt = Series("alt", ser6.dates, ser6.O, future, ser6.open_ok, ser6.days, ser6.rate)
    attach_v(alt)
    same = all(np.array_equal(ser6.v[w][:400], alt.v[w][:400], equal_nan=True) for w in SIGMA_WINDOWS)
    firsts = {w: int(np.argmax(np.isfinite(ser6.v[w]))) for w in SIGMA_WINDOWS}
    check("6 window boundary (sigma median through t; first valid idx = window+119)",
          same and firsts == {15: 134, 20: 139, 30: 149} and ser6.first_valid == 149, str(firsts))

    # 7. fixed 0.633 reproduces S4 simulate() B0 (real S4 inputs when available, toy otherwise), rel err <= 1e-12
    def vs_s4(ser_: Series, label: str) -> tuple[bool, float]:
        n_ = ser_.n
        ref = s4().simulate(ser_.O, ser_.C, ser_.open_ok, ser_.days, ser_.rate, np.full(n_, CAP), BAND, "band", 10.0)
        mine = sim_window_scalar(ser_, 1, n_ - 1, CONFIGS["B0"], 10.0)
        vec = sim_windows_vec(ser_, np.array([1]), n_ - 1, CONFIGS["B0"], 10.0)
        err = float(np.max(np.abs(mine["V"][1:] / ref["V"][1:] - 1.0)))
        err = max(err, abs(vec["final"][0] / ref["V"][-1] - 1.0))
        return err <= 1e-12, err
    ok7, err7 = True, 0.0
    toy = _toy_series(900, seed=3)
    a_, e_ = vs_s4(toy, "toy")
    ok7 &= a_
    err7 = max(err7, e_)
    toy_u = _toy_series(900, seed=5, open_equals_close=True)
    a_, e_ = vs_s4(toy_u, "toy-close-fill")
    ok7 &= a_
    err7 = max(err7, e_)
    real_note = "real S4 inputs not found (toy only)"
    try:
        real = actual_series(load_s4_inputs())
        a_, e_ = vs_s4(real, "real-A")
        ok7 &= a_
        err7 = max(err7, e_)
        real_note = "incl. real S4 A inputs"
    except Exception as exc:  # pragma: no cover
        real_note = f"real S4 inputs unavailable: {exc!r}"
        ok7 = False
    check("7 fixed 0.633 == S4 simulate() B0 (rel err <= 1e-12)", ok7, f"max rel err {err7:.2e}; {real_note}")

    # vectorised == scalar on toy data (all configs, includes lock windows)
    ser_v = _toy_series(700, crash=True, seed=9)
    starts = np.arange(ser_v.first_valid + 1, 700 - 150)
    worst, lockn = 0.0, 0
    for name, cfg in CONFIGS.items():
        res = sim_windows_vec(ser_v, starts, 150, cfg, 20.0, True)
        for i in range(0, len(starts), 7):
            sc = sim_window_scalar(ser_v, int(starts[i]), 150, cfg, 20.0, True)
            worst = max(worst, abs(res["final"][i] / sc["V"][-1] - 1.0), abs(res["min"][i] / sc["V"].min() - 1.0))
            lockn += int(sc["locked"])
            assert bool(res["locked"][i]) == sc["locked"] and int(res["fills"][i]) == sc["fills"]
    check("7b vectorised engine == scalar engine (toy, all configs)", worst <= 1e-12 and lockn > 0, f"max rel err {worst:.2e}, locked windows {lockn}")

    width = max(len(n_) for n_, _, _ in results)
    failed = 0
    for name, ok, note in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {note}")
        failed += 0 if ok else 1
    print(json.dumps({"self_test": "passed" if not failed else "failed", "checks": len(results)}))
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--end", default=None)
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if args.collect:
        return collect(args.end)
    if args.run:
        return run(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
