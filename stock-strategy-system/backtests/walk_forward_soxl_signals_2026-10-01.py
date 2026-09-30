#!/usr/bin/env python3
"""Protocol-locked SOXX-signal / SOXL-trade crash-recovery walk-forward research (S4).

Historical research only.  It never reads or changes broker state, never uses
Kiwoom tools, and never places or schedules an order.  Completed regular-session
close signals are simulated at the next regular-session open (gap included).

The pre-result contract is SOXL_SIGNAL_WALK_FORWARD_PROTOCOL_2026-10-01.md
(+ its .sha256 sidecar).  The runner refuses to run if the protocol changed.

  --self-test   synthetic-data checks, no network
  --collect     fetch public data (Nasdaq main + Yahoo cross-check, FRED DGS3MO)
  --run         run the protocol on the saved inputs and write the results
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time as dtime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
BASE_SCRIPT = HERE / "backtest_soxl_ema_policy_2026-08-05.py"
WF_SCRIPT = HERE / "walk_forward_soxl_policy_2026-08-05.py"
INPUT_DIR = HERE / "soxl_signal_inputs_2026-10-01"
SOURCES_JSON = INPUT_DIR / "soxl_signal_inputs_sources.json"
PROTOCOL = HERE / "SOXL_SIGNAL_WALK_FORWARD_PROTOCOL_2026-10-01.md"
PROTOCOL_SIDECAR = HERE / "SOXL_SIGNAL_WALK_FORWARD_PROTOCOL_2026-10-01.sha256"
STEM = "soxl_signal_walk_forward_2026-10-01"

SYMBOL_START = {"SOXX": "2010-01-04", "QQQ": "2010-01-04", "SOXL": "2010-03-11", "TQQQ": "2010-02-11"}
CAP = 0.633
CAP_LOW = 0.517
BAND = 0.10
PRIMARY = ("2021-08-05", "2026-08-04")
AUX1 = ("2013-08-05", "2021-08-04")
AUX2_START = "2026-08-05"
OOS_START_TS = pd.Timestamp(PRIMARY[0])
COSTS = (10.0, 20.0, 50.0)

# Parameters are fixed by the protocol; never edit after seeing a result.
C1_VARIANTS = {
    "C1": dict(window=20, ref="expanding", band=0.10),
    "C1_w15": dict(window=15, ref="expanding", band=0.10),
    "C1_w30": dict(window=30, ref="expanding", band=0.10),
    "C1_ref756": dict(window=20, ref="rolling756", band=0.10),
    "C1_band5": dict(window=20, ref="expanding", band=0.05),
    "C1_band15": dict(window=20, ref="expanding", band=0.15),
}
C1_REPORT_ONLY = {"C1_daily": dict(window=20, ref="expanding", band=0.0)}
C2_VARIANTS = {
    "C2": dict(k=2.5, d=0.10, g=0.020, sma=True),
    "C2_k2.0": dict(k=2.0, d=0.10, g=0.020, sma=True),
    "C2_k3.0": dict(k=3.0, d=0.10, g=0.020, sma=True),
    "C2_d8": dict(k=2.5, d=0.08, g=0.020, sma=True),
    "C2_d12": dict(k=2.5, d=0.12, g=0.020, sma=True),
    "C2_g1.5": dict(k=2.5, d=0.10, g=0.015, sma=True),
    "C2_g2.5": dict(k=2.5, d=0.10, g=0.025, sma=True),
    "C2_ema_only": dict(k=2.5, d=0.10, g=0.020, sma=False),
}
FAMILY_C1 = list(C1_VARIANTS)
FAMILY_C2 = list(C2_VARIANTS)
FAMILY_MIX = FAMILY_C1 + FAMILY_C2 + ["C3"]
GATE_ROWS = ["C1_WF", "C2_WF", "C1", "C2", "C3"]
MULT = {0: 0.0, 1: 0.5, 2: 1.0}


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_MODS: dict[str, Any] = {}


def wf_mod():
    if "wf" not in _MODS:
        _MODS["wf"] = load_module("s4_wf_policy", WF_SCRIPT)
    return _MODS["wf"]


def base_mod():
    if "base" not in _MODS:
        _MODS["base"] = load_module("s4_ema_base", BASE_SCRIPT)
    return _MODS["base"]


def clean(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        return None if not math.isfinite(float(obj)) else float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp, datetime, date)):
        return obj.isoformat()
    if isinstance(obj, np.ndarray):
        return clean(obj.tolist())
    return obj


# ----------------------------------------------------------------------------
# NYSE calendar generator (protocol A1-6)
# ----------------------------------------------------------------------------
def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    if n > 0:
        d = date(year, month, 1)
        d += timedelta(days=(weekday - d.weekday()) % 7 + 7 * (n - 1))
        return d
    d = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def nyse_full_closures(y0: int = 2009, y1: int = 2027) -> set[str]:
    from dateutil.easter import easter

    out: set[str] = set()

    def observed(d: date, saturday_to_friday: bool) -> date | None:
        if d.weekday() == 5:
            return d - timedelta(days=1) if saturday_to_friday else None
        if d.weekday() == 6:
            return d + timedelta(days=1)
        return d

    for y in range(y0, y1 + 1):
        days: list[date | None] = [
            observed(date(y, 1, 1), False),  # Saturday New Year: preceding Friday stays open
            _nth_weekday(y, 1, 0, 3),
            _nth_weekday(y, 2, 0, 3),
            easter(y) - timedelta(days=2),
            _nth_weekday(y, 5, 0, -1),
            observed(date(y, 7, 4), True),
            _nth_weekday(y, 9, 0, 1),
            _nth_weekday(y, 11, 3, 4),
            observed(date(y, 12, 25), True),
        ]
        if y >= 2022:
            days.append(observed(date(y, 6, 19), True))
        out.update(d.isoformat() for d in days if d is not None)
    out.update({"2012-10-29", "2012-10-30", "2018-12-05", "2025-01-09"})
    return out


def nyse_early_closes(closures: set[str], y0: int = 2009, y1: int = 2027) -> set[str]:
    out: set[str] = set()
    for y in range(y0, y1 + 1):
        black_friday = _nth_weekday(y, 11, 3, 4) + timedelta(days=1)
        out.add(black_friday.isoformat())
        for month, day_, next_day in ((7, 3, date(y, 7, 4)), (12, 24, date(y, 12, 25))):
            d = date(y, month, day_)
            if d.weekday() < 5 and next_day.weekday() < 5 and d.isoformat() not in closures:
                out.add(d.isoformat())
    return out - closures


FULL_CLOSURES = nyse_full_closures()


def expected_sessions(start: str, end: str) -> pd.DatetimeIndex:
    idx = pd.date_range(start, end, freq="B")
    return idx.difference(pd.to_datetime(sorted(FULL_CLOSURES))).sort_values()


def early_closes() -> set[str]:
    return nyse_early_closes(FULL_CLOSURES) | set(wf_mod().EARLY_CLOSES)


# ----------------------------------------------------------------------------
# data collection (--collect)
# ----------------------------------------------------------------------------
def last_completed_session() -> str:
    from zoneinfo import ZoneInfo

    now = datetime.now(timezone.utc).astimezone(ZoneInfo("America/New_York"))
    day = now.date() if now.time() >= dtime(16, 30) else now.date() - timedelta(days=1)
    return expected_sessions("2026-01-01", day.isoformat())[-1].date().isoformat()


def _write_csv(frame: pd.DataFrame, path: Path) -> dict[str, Any]:
    frame.to_csv(path, index_label="date")
    return {"path": path.name, "rows": int(len(frame)), "sha256": sha256_file(path)}


def fetch_treasury_retry(start: str, end: str, attempts: int = 4, timeout: int = 90):
    """Same FRED DGS3MO parsing as the existing runner, with retries for transient timeouts."""
    import time
    import urllib.parse
    import urllib.request

    wf = wf_mod()
    params = {"id": wf.FRED_SERIES, "cosd": start, "coed": end}
    url = wf.FRED_URL + "?" + urllib.parse.urlencode(params)
    last = ""
    for attempt in range(1, attempts + 1):
        try:
            # FRED stalls on a browser User-Agent from this host; the default urllib agent answers in <1s.
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                text = response.read().decode("utf-8")
            rows = []
            for line in text.splitlines()[1:]:
                day, value = line.split(",", 1)
                if value not in ("", "."):
                    rows.append((pd.Timestamp(day), float(value)))
            series = pd.Series(dict(rows), dtype=float).sort_index()
            if series.empty:
                raise RuntimeError("empty DGS3MO")
            return series, {"status": "passed", "url": url, "rows": len(series), "attempts": attempt,
                            "first": series.index[0].date().isoformat(), "last": series.index[-1].date().isoformat()}
        except Exception as exc:
            last = repr(exc)
            time.sleep(4)
    return None, {"status": "unavailable_zero_yield_used", "url": url, "error": last, "attempts": attempts}


def collect(end: str | None) -> int:
    wf, base = wf_mod(), base_mod()
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        end = end or last_completed_session()
    except Exception as exc:  # zoneinfo/tzdata unavailable: never guess the end date
        print(json.dumps({"status": "stopped", "reason": f"cannot determine last completed session: {exc!r}; pass --end"}))
        return 2
    base.NYSE_FULL_CLOSURES = set(FULL_CLOSURES)
    base.NYSE_EARLY_CLOSES = early_closes()
    sources: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "end_date": end,
        "protocol_raw_sha256": sha256_file(PROTOCOL),
        "calendar": {"generator": "nyse_full_closures/nyse_early_closes in this script"},
        "symbols": {},
    }
    stop: list[str] = []
    for sym, start in SYMBOL_START.items():
        expected = expected_sessions(start, end)
        try:
            nas = base.fetch_nasdaq(sym, start, end)
            yah, events, yurl = base.fetch_yahoo(sym, start, end)
        except Exception as exc:
            stop.append(f"{sym}: collection failed {exc!r}")
            continue
        info: dict[str, Any] = {"start": start, "end": end}
        info["nasdaq_raw_csv"] = _write_csv(nas, INPUT_DIR / f"{sym}_nasdaq_raw.csv")
        info["yahoo_raw_csv"] = _write_csv(yah, INPUT_DIR / f"{sym}_yahoo_raw.csv")
        splits = wf.split_map(events)
        info["splits"] = {k.date().isoformat(): v for k, v in splits.items()}
        info["dividends"] = {k.date().isoformat(): v for k, v in base.yahoo_dividends(events).items()}
        if yah.index[0] != pd.Timestamp(start):
            stop.append(f"{sym}: Yahoo first row {yah.index[0].date()} != listing start {start}")
        extra_y = yah.index.difference(expected)
        extra_n = nas.index.difference(expected)
        if len(extra_y) or len(extra_n):
            stop.append(
                f"{sym}: vendor sessions not in generated calendar yahoo={[d.date().isoformat() for d in extra_y][:10]} "
                f"nasdaq={[d.date().isoformat() for d in extra_n][:10]}"
            )
        # Align Nasdaq to Yahoo's split basis before applying the tolerance.
        nas_adj = nas.copy()
        split_days = sorted(splits)
        explained: list[str] = []
        mismatches: list[dict[str, Any]] = []
        for day in nas.index.intersection(yah.index).intersection(expected):
            nc, yc = float(nas.at[day, "close"]), float(yah.at[day, "close"])
            if abs(nc - yc) <= max(0.05, nc * 0.001):
                continue
            cum = math.prod(splits[s] for s in split_days if s > day)
            adj = nc / cum if cum else nc
            if cum != 1.0 and abs(adj - yc) <= max(0.05, adj * 0.001):
                for col in ("open", "high", "low", "close"):
                    nas_adj.at[day, col] = float(nas.at[day, col]) / cum
                nas_adj.at[day, "volume"] = float(nas.at[day, "volume"]) * cum
                explained.append(day.date().isoformat())
            else:
                mismatches.append({"date": day.date().isoformat(), "nasdaq_close": nc, "yahoo_close": yc})
        info["split_basis_explained_rows"] = len(explained)
        info["split_basis_explained_first_last"] = [explained[0], explained[-1]] if explained else None
        info["mismatch_count_after_split_alignment"] = len(mismatches)
        info["mismatch_examples"] = mismatches[:20]
        if mismatches:
            stop.append(f"{sym}: {len(mismatches)} Nasdaq/Yahoo close mismatches not explained by splits")
            sources["symbols"][sym] = info
            continue
        real_fetch_n, real_fetch_y = base.fetch_nasdaq, base.fetch_yahoo
        try:
            nas_adj.attrs.update(nas.attrs)
            base.fetch_nasdaq = lambda *a, **k: nas_adj
            base.fetch_yahoo = lambda *a, **k: (yah, events, yurl)
            frame, quality = base.combined_history(sym, start, end)
        except Exception as exc:
            stop.append(f"{sym}: combined_history stopped {exc!r}")
            sources["symbols"][sym] = info
            continue
        finally:
            base.fetch_nasdaq, base.fetch_yahoo = real_fetch_n, real_fetch_y
        if not frame.index.equals(expected):
            stop.append(f"{sym}: final index != expected sessions")
        frame = frame.copy()
        frame["nasdaq_split_basis_adjusted"] = frame.index.isin(pd.to_datetime(explained))
        info["combined_csv"] = _write_csv(frame, INPUT_DIR / f"{sym}_combined.csv")
        quality = dict(quality)
        quality.pop("events", None)
        info["quality"] = quality
        info["yahoo_single_source_sessions"] = list(quality.get("fallback_sessions", []))
        info["yahoo_single_source_count"] = len(info["yahoo_single_source_sessions"])
        info["first_date"], info["last_date"] = quality["first_date"], quality["last_date"]
        sources["symbols"][sym] = info
    treasury, tq = fetch_treasury_retry("2009-12-01", end)
    sources["treasury"] = dict(tq)
    if treasury is not None:
        tf = pd.DataFrame({"DGS3MO": treasury})
        sources["treasury"]["csv"] = _write_csv(tf, INPUT_DIR / "DGS3MO.csv")
    sources["status"] = "stopped" if stop else "passed"
    sources["stop_reasons"] = stop
    SOURCES_JSON.write_text(json.dumps(clean(sources), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": sources["status"], "end_date": end, "stop_reasons": stop,
                      "yahoo_single_source": {s: v.get("yahoo_single_source_count") for s, v in sources["symbols"].items()}}, ensure_ascii=False))
    return 2 if stop else 0


def load_inputs() -> dict[str, Any]:
    src = json.loads(SOURCES_JSON.read_text(encoding="utf-8"))
    if src.get("status") != "passed":
        raise RuntimeError("input collection did not pass; run --collect")
    end = src["end_date"]
    frames: dict[str, pd.DataFrame] = {}
    split_days: dict[str, set[pd.Timestamp]] = {}
    for sym, info in src["symbols"].items():
        path = INPUT_DIR / info["combined_csv"]["path"]
        if sha256_file(path) != info["combined_csv"]["sha256"]:
            raise RuntimeError(f"{sym}: combined CSV hash differs from sources JSON")
        df = pd.read_csv(path, index_col="date", parse_dates=["date"])
        if not df.index.equals(expected_sessions(SYMBOL_START[sym], end)):
            raise RuntimeError(f"{sym}: calendar completeness audit failed")
        if not (np.isfinite(df[["open", "high", "low", "close", "adjclose", "volume"]].to_numpy(float)).all()
                and (df[["open", "high", "low", "close", "adjclose", "volume"]] > 0).all().all()):
            raise RuntimeError(f"{sym}: non-positive or missing OHLCV")
        frames[sym] = df
        split_days[sym] = {pd.Timestamp(d) for d in info["splits"]}
    treasury = None
    if src.get("treasury", {}).get("csv"):
        tpath = INPUT_DIR / src["treasury"]["csv"]["path"]
        if sha256_file(tpath) != src["treasury"]["csv"]["sha256"]:
            raise RuntimeError("DGS3MO CSV hash differs")
        treasury = pd.read_csv(tpath, index_col="date", parse_dates=["date"])["DGS3MO"].astype(float)
    return {"sources": src, "frames": frames, "split_days": split_days, "treasury": treasury, "end": end}


# ----------------------------------------------------------------------------
# features and targets (causal by construction; verified by truncation tests)
# ----------------------------------------------------------------------------
def adj_frame(df: pd.DataFrame) -> pd.DataFrame:
    f = df["adjclose"] / df["close"]
    out = pd.DataFrame(index=df.index)
    out["open"] = df["open"] * f
    out["high"] = df["high"] * f
    out["low"] = df["low"] * f
    out["close"] = df["adjclose"]
    out["raw_open"] = df["open"]
    out["volume"] = df["volume"]
    out["early"] = df["is_early_close"].astype(bool)
    return out


@dataclass
class Features:
    dates: pd.DatetimeIndex
    tO: np.ndarray
    tC: np.ndarray
    open_ok: np.ndarray
    sC: np.ndarray
    s_prev: np.ndarray
    s_ret: np.ndarray
    s_sd_prev: np.ndarray
    s_sma50: np.ndarray
    s_sma200: np.ndarray
    s_ema10: np.ndarray
    s_ema20: np.ndarray
    s_vol: np.ndarray
    s_vol_prev: np.ndarray
    s_vol_ok: np.ndarray
    days: np.ndarray
    rate: np.ndarray
    signal_close: pd.Series


def rate_array(dates: pd.DatetimeIndex, treasury: pd.Series | None) -> np.ndarray:
    if treasury is None or treasury.empty:
        return np.zeros(len(dates))
    idx = treasury.index.values.astype("datetime64[ns]")
    pos = np.searchsorted(idx, dates.values.astype("datetime64[ns]"), side="left") - 1
    vals = treasury.to_numpy(float) / 100.0
    return np.where(pos >= 0, vals[np.clip(pos, 0, None)], 0.0)


def build_features(trade_df: pd.DataFrame, signal_df: pd.DataFrame,
                   signal_split_days: set[pd.Timestamp] | frozenset = frozenset(),
                   treasury: pd.Series | None = None) -> Features:
    t = adj_frame(trade_df)
    s = adj_frame(signal_df)
    dates = t.index
    if not dates.isin(s.index).all():
        raise RuntimeError("signal history does not cover the trading sessions")
    close = s["close"]
    ret = close.pct_change()
    sd_prev = ret.rolling(20).std().shift(1)
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()
    ema10 = close.ewm(span=10, adjust=False).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()
    prev_early = s["early"].shift(1, fill_value=True)
    split = pd.Series(s.index.isin(list(signal_split_days)), index=s.index)
    vol_ok = (~s["early"]) & (~prev_early) & (~split)

    def on(series: pd.Series) -> np.ndarray:
        return series.reindex(dates).to_numpy(float)

    open_ok = (np.isfinite(t["raw_open"].to_numpy(float)) & (t["raw_open"].to_numpy(float) > 0)
               & (t["volume"].to_numpy(float) > 0))
    days = np.r_[1.0, np.diff(dates.values.astype("datetime64[D]").astype(np.int64)).astype(float)]
    return Features(
        dates=dates, tO=t["open"].to_numpy(float), tC=t["close"].to_numpy(float), open_ok=open_ok,
        sC=on(close), s_prev=on(close.shift(1)), s_ret=on(ret), s_sd_prev=on(sd_prev),
        s_sma50=on(sma50), s_sma200=on(sma200), s_ema10=on(ema10), s_ema20=on(ema20),
        s_vol=on(s["volume"]), s_vol_prev=on(s["volume"].shift(1)),
        s_vol_ok=vol_ok.reindex(dates).to_numpy(bool),
        days=days, rate=rate_array(dates, treasury), signal_close=close,
    )


@dataclass
class Target:
    name: str
    w: np.ndarray
    band: float
    mode: str = "band"
    ratio: np.ndarray | None = None
    stage: np.ndarray | None = None
    events: list[dict[str, Any]] = field(default_factory=list)


def c2_stage(close, close_prev, ret, sd_prev, sma50, ema10, ema20, vol, vol_prev, vol_ok,
             k: float, d: float, g: float, use_sma: bool):
    """Stage machine: 0 out, 1 half, 2 full.  Full is reachable only from half (A1-1)."""
    n = len(close)
    stage = np.full(n, np.nan)
    events: list[dict[str, Any]] = []
    valid = np.isfinite(sma50) & np.isfinite(sd_prev) & np.isfinite(ema20)
    if not valid.any():
        return stage, events
    start = int(np.argmax(valid))
    st, entry = 2, start
    stage[start] = 2
    events.append({"idx": start, "kind": "start_full"})
    rally_low, rally_day = math.nan, 0
    for t in range(start + 1, n):
        crash = bool(ret[t] <= -k * sd_prev[t])
        if st == 2:
            lo = max(entry, t - 19)
            ref_high = float(np.max(close[lo:t + 1]))
            if crash or close[t] <= (1.0 - d) * ref_high:
                events.append({"idx": t, "kind": "exit_crash" if crash else "exit_drawdown"})
                st, rally_low, rally_day = 0, close[t], 0
        elif st == 0:
            if close[t] < rally_low:
                rally_low, rally_day = close[t], 0
            elif rally_day == 0:
                rally_day = 1 if close[t] > close_prev[t] else 0
            else:
                rally_day += 1
            if rally_day >= 4 and ret[t] >= g and bool(vol_ok[t]) and vol[t] > vol_prev[t]:
                st = 1
                events.append({"idx": t, "kind": "half_entry"})
        else:
            if crash:
                st, rally_low, rally_day = 0, close[t], 0
                events.append({"idx": t, "kind": "half_fail_crash"})
            elif close[t] < rally_low:
                st, rally_low, rally_day = 0, close[t], 0
                events.append({"idx": t, "kind": "half_fail_ftd"})
            else:
                trend = bool(ema10[t] > ema20[t]) and (bool(close[t] > sma50[t]) if use_sma else True)
                if trend:
                    st, entry = 2, t
                    events.append({"idx": t, "kind": "full_entry"})
        stage[t] = st
    return stage, events


def c1_series(tC: np.ndarray, window: int, ref_kind: str):
    ret = pd.Series(tC).pct_change()
    sig = ret.rolling(window).std()
    if ref_kind == "expanding":
        ref = sig.expanding(min_periods=120).median()
    else:
        ref = sig.rolling(756, min_periods=120).median()
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.minimum(1.0, (ref / sig).to_numpy(float))
    return ratio


def c1_episode_starts(ratio: np.ndarray) -> list[dict[str, Any]]:
    out, in_ep = [], False
    for i, r in enumerate(ratio):
        if not math.isfinite(r):
            continue
        if not in_ep and r < 0.80:
            in_ep = True
            out.append({"idx": i, "kind": "ep_start"})
        elif in_ep and r >= 0.95:
            in_ep = False
    return out


def build_targets(f: Features, cap: float, with_report_only: bool = True) -> dict[str, Target]:
    n = len(f.tC)
    out: dict[str, Target] = {}
    out["B0"] = Target("B0", np.full(n, cap), BAND)
    b1 = np.where(np.isfinite(f.s_sma200), np.where(f.sC > f.s_sma200, cap, 0.0), np.nan)
    out["B1"] = Target("B1", b1, BAND, mode="change")
    c1_items = dict(C1_VARIANTS)
    if with_report_only:
        c1_items.update(C1_REPORT_ONLY)
    for name, p in c1_items.items():
        ratio = c1_series(f.tC, p["window"], p["ref"])
        out[name] = Target(name, cap * ratio, p["band"], ratio=ratio, events=c1_episode_starts(ratio))
    for name, p in C2_VARIANTS.items():
        stage, events = c2_stage(f.sC, f.s_prev, f.s_ret, f.s_sd_prev, f.s_sma50, f.s_ema10, f.s_ema20,
                                 f.s_vol, f.s_vol_prev, f.s_vol_ok, p["k"], p["d"], p["g"], p["sma"])
        mult = np.full(n, np.nan)
        ok = np.isfinite(stage)
        mult[ok] = np.vectorize(MULT.get)(stage[ok].astype(int))
        out[name] = Target(name, cap * mult, BAND, stage=stage, events=events)
    m = np.full(n, np.nan)
    ok = np.isfinite(out["C2"].stage)
    m[ok] = np.vectorize(MULT.get)(out["C2"].stage[ok].astype(int))
    out["C3"] = Target("C3", out["C1"].w * m, BAND, ratio=out["C1"].ratio, stage=out["C2"].stage,
                       events=out["C2"].events)
    return out


# ----------------------------------------------------------------------------
# execution engine
# ----------------------------------------------------------------------------
def simulate(O, C, open_ok, days, rate, target, band, mode="band", cost_bps=10.0, cash_yield=True,
             force=None, init=None, start=0, end=None) -> dict[str, Any]:
    n = len(C)
    end = n - 1 if end is None else end
    cost = cost_bps / 10_000.0
    band_arr = np.full(n, band, dtype=float) if np.isscalar(band) else np.asarray(band, float)
    if init is None:
        S, cash, committed, pending = 0.0, 1.0, 0.0, None
    else:
        S, cash, committed, pending = init["S"], init["cash"], init["committed"], init["pending"]
    V = np.full(n, np.nan)
    W = np.full(n, np.nan)
    COMM = np.full(n, np.nan)
    PEND: list[Any] = [None] * n
    trades: list[dict[str, Any]] = []
    stale: list[int] = []
    costs = 0.0
    for t in range(start, end + 1):
        valid = bool(open_ok[t]) and math.isfinite(O[t]) and O[t] > 0
        if t > 0:
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
                    costs += c
                    trades.append({"idx": t, "delta": delta, "notional": abs(delta), "cost": c,
                                   "dweight": delta / v_open, "target": pending})
                committed, pending = pending, None
            else:
                stale.append(t)
        if valid:
            S *= C[t] / O[t]
        elif t > 0:
            S *= C[t] / C[t - 1]
        v = S + cash
        w = S / v
        V[t], W[t] = v, w
        tgt = target[t]
        if not math.isfinite(tgt):
            pending = None
        elif mode == "change":
            pending = tgt if abs(tgt - committed) > 1e-12 else None
        elif force is not None and bool(force[t]):
            pending = tgt if abs(tgt - w) > 1e-12 else None
        elif tgt <= 1e-12:
            pending = 0.0 if w > 1e-12 else None
        elif w <= 1e-12:
            pending = tgt
        elif abs(tgt - w) >= band_arr[t] - 1e-12:
            pending = tgt
        else:
            pending = None
        PEND[t], COMM[t] = pending, committed
    return {"V": V, "W": W, "COMM": COMM, "PEND": PEND, "trades": trades, "stale": stale, "costs": costs}


def run_target(f: Features, tgt: Target, cost_bps: float, cash_yield: bool = True) -> dict[str, Any]:
    return simulate(f.tO, f.tC, f.open_ok, f.days, f.rate, tgt.w, tgt.band, tgt.mode, cost_bps, cash_yield)


# ----------------------------------------------------------------------------
# folds, slices, selection, stitching
# ----------------------------------------------------------------------------
def make_folds(oos_start: str, oos_end: str) -> list[dict[str, pd.Timestamp]]:
    folds, ts, end = [], pd.Timestamp(oos_start), pd.Timestamp(oos_end)
    while ts <= end:
        nxt = ts + pd.DateOffset(months=6)
        folds.append({"train_start": ts - pd.DateOffset(months=24), "train_end": ts - pd.Timedelta(days=1),
                      "test_start": ts, "test_end": min(nxt - pd.Timedelta(days=1), end)})
        ts = nxt
    return folds


def positions(dates: pd.DatetimeIndex, start: pd.Timestamp, end: pd.Timestamp) -> tuple[int, int]:
    a = int(dates.searchsorted(start, side="left"))
    z = int(dates.searchsorted(end, side="right")) - 1
    if a < 1 or z < a:
        raise RuntimeError(f"invalid slice {start.date()}..{end.date()}")
    return a, z


def slice_metrics(run: dict[str, Any], dates: pd.DatetimeIndex, a: int, z: int, name: str) -> dict[str, Any]:
    V = run["V"]
    initial = float(V[a - 1])
    values = [(dates[i], float(V[i])) for i in range(a, z + 1)]
    trs = [{"notional_usd": tr["notional"]} for tr in run["trades"] if a <= tr["idx"] <= z]
    costs = sum(tr["cost"] for tr in run["trades"] if a <= tr["idx"] <= z) / initial  # NAV at slice start = 1
    m = wf_mod().metrics(name, initial, values, trs, costs, list(run["W"][a:z + 1]))
    years = max((dates[z] - dates[a]).days / 365.25, 1 / 252)
    m["annualized_turnover"] = m["turnover_multiple"] / years
    m["estimated_cost_nav"] = m.pop("estimated_cost_usd")
    m.pop("start_value_usd", None)
    m.pop("end_value_usd", None)
    m["fills"] = m.pop("trade_count")
    m["stale_open_freezes"] = sum(1 for i in run["stale"] if a <= i <= z)
    return m


def select_variant(runs: dict[str, dict], dates: pd.DatetimeIndex, fold: dict[str, pd.Timestamp],
                   names: list[str]) -> tuple[str, list[dict[str, Any]]]:
    assert fold["train_end"] < fold["test_start"]
    a, z = positions(dates, fold["train_start"], fold["train_end"])
    base = slice_metrics(runs["B0"], dates, a, z, "B0")
    rows = []
    for order, name in enumerate(names):
        m = slice_metrics(runs[name], dates, a, z, name)
        rows.append({"name": name, "order": order, "cagr": m["cagr"], "maximum_drawdown": m["maximum_drawdown"],
                     "calmar": m["calmar"], "turnover": m["turnover_multiple"],
                     "eligible": bool(m["maximum_drawdown"] >= base["maximum_drawdown"] - 1e-12)})
    eligible = [r for r in rows if r["eligible"]]
    if not eligible:
        return "B0", rows
    best = min(eligible, key=lambda r: (-r["cagr"], -(r["calmar"] if r["calmar"] is not None else -999.0),
                                        r["turnover"], r["order"]))
    return best["name"], rows


def stitched_run(f: Features, targets: dict[str, Target], runs: dict[str, dict], schedule: list[str],
                 fold_pos: list[tuple[int, int]], cost_bps: float, cash_yield: bool = True) -> dict[str, Any]:
    n = len(f.tC)
    p_first, p_last = fold_pos[0][0], fold_pos[-1][1]
    fold_of = np.full(n, -1)
    for i, (a, z) in enumerate(fold_pos):
        fold_of[a:z + 1] = i
    target = np.full(n, np.nan)
    band = np.full(n, BAND)
    force = np.zeros(n, bool)
    for t in range(p_first, p_last + 1):
        cur = fold_of[t]
        nxt = fold_of[t + 1] if t + 1 <= p_last else cur
        name = schedule[nxt]
        target[t] = targets[name].w[t]
        band[t] = targets[name].band
        force[t] = schedule[nxt] != schedule[cur]
    v0 = runs[schedule[0]]
    i0 = p_first - 1
    w0 = float(v0["W"][i0])
    init = {"S": w0, "cash": 1.0 - w0, "committed": float(v0["COMM"][i0]), "pending": v0["PEND"][i0]}
    out = simulate(f.tO, f.tC, f.open_ok, f.days, f.rate, target, band, "band", cost_bps, cash_yield,
                   force=force, init=init, start=p_first, end=p_last)
    out["V"][i0] = 1.0
    out["W"][i0] = w0
    return out


# ----------------------------------------------------------------------------
# gates
# ----------------------------------------------------------------------------
def g1_g2(cand: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    mdd_gain = cand["maximum_drawdown"] - base["maximum_drawdown"]
    cr, br = cand["maximum_recovery_sessions"], base["maximum_recovery_sessions"]
    g1_mdd = bool(mdd_gain >= 0.05 - 1e-12)
    g1_rec = bool(cr <= 0.9 * br + 1e-12)
    bc = base["cagr"]
    g1_cagr = bool(cand["cagr"] >= 0.9 * bc) if bc > 0 else bool(cand["cagr"] >= bc)
    cc, bcal = cand["calmar"], base["calmar"]
    g2 = bool(cc is not None and bcal is not None and cc >= bcal + 0.10 * abs(bcal) - 1e-12)
    return {
        "G1": bool(g1_mdd and g1_rec and g1_cagr), "G1_mdd_gain_pp": mdd_gain * 100, "G1_mdd_ok": g1_mdd,
        "G1_recovery_sessions": [cr, br], "G1_recovery_ok": g1_rec,
        "G1_cagr_ratio": (cand["cagr"] / bc) if bc else None, "G1_cagr_ok": g1_cagr,
        "G1_prior_protocol_criterion_1": bool(cand["cagr"] - bc >= 0.05 and
                                              cand["maximum_drawdown"] >= base["maximum_drawdown"] - 0.03),
        "G2": g2, "G2_calmar_ratio": (cc / bcal) if cc is not None and bcal else None,
    }


def gate_folds(cand_folds: list[dict], base_folds: list[dict], regimes: list[dict]) -> dict[str, Any]:
    n = len(cand_folds)
    need = math.ceil(0.7 * n - 1e-9)
    improved = [i for i in range(n)
                if cand_folds[i]["maximum_drawdown"] > base_folds[i]["maximum_drawdown"] + 1e-12]
    ret_better = [i for i in range(n) if cand_folds[i]["total_return"] > base_folds[i]["total_return"]]
    bull = any(regimes[i]["regime"] == "bull" for i in improved)
    bear_hv = any(regimes[i]["regime"] == "bear" or regimes[i]["high_volatility"] for i in improved)
    excess = [cand_folds[i]["total_return"] - base_folds[i]["total_return"] for i in range(n)]
    pos = [max(0.0, x) for x in excess]
    if sum(pos) <= 0:
        g5, g5_note, share = True, "no_positive_excess_not_applicable", None
    else:
        share = max(pos) / sum(pos)
        g5, g5_note = bool(share <= 0.5 + 1e-12), "evaluated"
    return {
        "G3": bool(len(improved) >= need and bull and bear_hv), "G3_improved_folds_mdd": len(improved),
        "G3_required": need, "G3_improved_fold_numbers": [i + 1 for i in improved],
        "G3_includes_bull": bull, "G3_includes_bear_or_high_vol": bear_hv,
        "G3_return_better_folds_prior_protocol_style": len(ret_better),
        "G5": g5, "G5_max_fold_share_of_positive_excess": share, "G5_note": g5_note,
        "fold_excess_returns": excess,
    }


# ----------------------------------------------------------------------------
# additional (non-gate) reports
# ----------------------------------------------------------------------------
def extremes(run, dates, a, z) -> dict[str, Any]:
    V = run["V"]
    r = V[a:z + 1] / V[a - 1:z] - 1.0
    out = {"worst_day": float(np.min(r)), "days_le_-10pct": int(np.sum(r <= -0.10)),
           "days_le_-20pct": int(np.sum(r <= -0.20))}
    starts = range(a - 1, z - 252 + 1)
    hit10 = hit20 = cnt = 0
    for s in starts:
        low = float(np.min(V[s + 1:s + 253]) / V[s] - 1.0)
        cnt += 1
        hit10 += low <= -0.10
        hit20 += low <= -0.20
    out["start_days_evaluated"] = cnt
    out["prob_hit_-10pct_within_252"] = hit10 / cnt if cnt else None
    out["prob_hit_-20pct_within_252"] = hit20 / cnt if cnt else None
    return out


def crash_episodes(sC: np.ndarray) -> list[dict[str, int | None]]:
    eps, in_ep = [], False
    peak_price, peak_idx, trough = sC[0], 0, 0
    ep_peak_idx = ep_peak_price = None
    for i in range(1, len(sC)):
        if not in_ep:
            if sC[i] >= peak_price:
                peak_price, peak_idx = sC[i], i
            elif sC[i] / peak_price - 1.0 <= -0.25:
                in_ep, ep_peak_idx, ep_peak_price, trough = True, peak_idx, peak_price, i
        else:
            if sC[i] < sC[trough]:
                trough = i
            if sC[i] >= ep_peak_price:
                eps.append({"peak": ep_peak_idx, "trough": trough, "recovered": i})
                in_ep, peak_price, peak_idx = False, sC[i], i
    if in_ep:
        eps.append({"peak": ep_peak_idx, "trough": trough, "recovered": None})
    return eps


def episode_table(f: Features, runs: dict[str, dict], events: dict[str, list]) -> list[dict[str, Any]]:
    n = len(f.tC)
    rows = []
    for ep in crash_episodes(f.sC):
        p, tr = ep["peak"], ep["trough"]
        row: dict[str, Any] = {
            "peak_date": f.dates[p].date().isoformat(), "trough_date": f.dates[tr].date().isoformat(),
            "soxx_drawdown": f.sC[tr] / f.sC[p] - 1.0, "sample": "OOS" if f.dates[p] >= OOS_START_TS else "in_sample_design_reference",
            "strategies": {},
        }
        post_end = min(tr + 60, n - 1)
        for name, run in runs.items():
            V = run["V"]
            st = {"decline_pnl": V[tr] / V[p] - 1.0, "post_trough_60_pnl": V[post_end] / V[tr] - 1.0,
                  "post_trough_window_truncated": bool(tr + 60 > n - 1)}
            if name in events:
                ev = events[name]
                exits = [e for e in ev if e["kind"].startswith("exit") and p < e["idx"] <= tr]
                st["first_exit"] = ({"date": f.dates[exits[0]["idx"]].date().isoformat(),
                                     "soxx_drawdown_from_peak": f.sC[exits[0]["idx"]] / f.sC[p] - 1.0} if exits else None)
                after = [e for e in ev if e["kind"] in ("half_entry", "full_entry") and e["idx"] > tr]
                half = next((e for e in after if e["kind"] == "half_entry"), None)
                full = next((e for e in after if e["kind"] == "full_entry"), None)
                st["first_reentry_half"] = ({"date": f.dates[half["idx"]].date().isoformat(),
                                             "soxx_rise_from_trough": f.sC[half["idx"]] / f.sC[tr] - 1.0} if half else None)
                st["first_reentry_full"] = ({"date": f.dates[full["idx"]].date().isoformat(),
                                             "soxx_rise_from_trough": f.sC[full["idx"]] / f.sC[tr] - 1.0} if full else None)
                st["false_reentries_inside_decline"] = {
                    "half": sum(1 for e in ev if e["kind"] == "half_entry" and p < e["idx"] <= tr),
                    "full": sum(1 for e in ev if e["kind"] == "full_entry" and p < e["idx"] <= tr)}
            row["strategies"][name] = st
        rows.append(row)
    return rows


def top_days(f: Features, runs: dict[str, dict], a: int, z: int) -> dict[str, Any]:
    r = f.s_ret[a:z + 1]
    ok = np.where(np.isfinite(r))[0]
    order = ok[np.argsort(r[ok])]
    down, up = order[:20] + a, order[::-1][:20] + a
    out: dict[str, Any] = {"up_dates": [f.dates[i].date().isoformat() for i in up],
                           "down_dates": [f.dates[i].date().isoformat() for i in down], "held": {}}
    for name, run in runs.items():
        W = run["W"]
        out["held"][name] = {"up_days_held": int(sum(W[i - 1] > 1e-3 for i in up)),
                             "down_days_held": int(sum(W[i - 1] > 1e-3 for i in down))}
    return out


def c2_diagnostics(f: Features, events: list[dict], a: int, z: int) -> dict[str, Any]:
    ev = [e for e in events if a <= e["idx"] <= z]
    exits = [e for e in events if e["kind"].startswith("exit") and a <= e["idx"] <= z]
    quick_half = quick_full = 0
    for e in exits:
        nxt = [x for x in events if x["idx"] > e["idx"] and x["kind"] in ("half_entry", "full_entry")]
        if nxt and nxt[0]["idx"] - e["idx"] <= 5:
            quick_half += nxt[0]["kind"] == "half_entry"
        full = next((x for x in events if x["idx"] > e["idx"] and x["kind"] == "full_entry"), None)
        quick_full += bool(full and full["idx"] - e["idx"] <= 5)
    kinds: dict[str, int] = {}
    for e in ev:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    return {"event_counts": kinds, "exits": len(exits), "half_reentry_within_5_sessions_after_exit": quick_half,
            "full_reentry_within_5_sessions_after_exit": quick_full}


# ----------------------------------------------------------------------------
# windows
# ----------------------------------------------------------------------------
def events_in_folds(target_by_name: dict[str, Target], schedule: list[str], fold_pos, kinds) -> int:
    total = 0
    for name, (a, z) in zip(schedule, fold_pos):
        total += sum(1 for e in target_by_name[name].events if e["kind"] in kinds and a <= e["idx"] <= z)
    return total


def run_windows(data: dict[str, Any]) -> dict[str, Any]:
    wf = wf_mod()
    frames, treasury, split_days = data["frames"], data["treasury"], data["split_days"]
    f = build_features(frames["SOXL"], frames["SOXX"], split_days["SOXX"], treasury)
    dates = f.dates
    n = len(dates)
    soxx_df = pd.DataFrame({"close": f.signal_close})
    targets = build_targets(f, CAP)
    runs = {c: {name: run_target(f, t, c) for name, t in targets.items()} for c in COSTS}
    runs_zero = {name: run_target(f, t, 10.0, cash_yield=False) for name, t in targets.items()}
    cap_targets = build_targets(f, CAP_LOW, with_report_only=False)
    cap_runs = {name: run_target(f, cap_targets[name], 10.0) for name in ("B0", "B1", "C1", "C2", "C3")}

    result: dict[str, Any] = {"n_sessions": n, "first_date": dates[0].date().isoformat(),
                              "last_date": dates[-1].date().isoformat()}
    daily = pd.DataFrame(index=dates)

    def evaluate(window: str, oos_start: str, oos_end: str, families: bool, full_gates: bool):
        folds = make_folds(oos_start, oos_end)
        fold_pos = [positions(dates, x["test_start"], x["test_end"]) for x in folds]
        regimes = [wf.regime_label(soxx_df, x) for x in folds]
        for x in folds:
            assert x["train_end"] < x["test_start"]
        selections: dict[str, list[str]] = {}
        sel_tables: dict[str, Any] = {}
        if families:
            for fam, names in (("C1_WF", FAMILY_C1), ("C2_WF", FAMILY_C2), ("MIX_WF", FAMILY_MIX)):
                sched, tab = [], []
                for i, fold in enumerate(folds):
                    ch, rows = select_variant(runs[10.0], dates, fold, names)
                    sched.append(ch)
                    tab.append({"fold": i + 1, "chosen": ch, "candidates": rows})
                selections[fam], sel_tables[fam] = sched, tab
        row_names = ["B0", "B1", "C1", "C2", "C3"] + list(selections)
        a_all, z_all = fold_pos[0][0], fold_pos[-1][1]
        by_cost: dict[float, dict[str, dict]] = {}
        for c in COSTS if full_gates else (10.0,):
            rc: dict[str, dict] = {}
            for name in row_names:
                if name in selections:
                    rc[name] = stitched_run(f, targets, runs[c], selections[name], fold_pos, c)
                else:
                    rc[name] = runs[c][name]
            by_cost[c] = rc
        totals = {c: {name: slice_metrics(run, dates, a_all, z_all, name) for name, run in rc.items()}
                  for c, rc in by_cost.items()}
        fold_metrics = {name: [slice_metrics(run, dates, a, z, name) for (a, z) in fold_pos]
                        for name, run in by_cost[10.0].items()}
        window_out: dict[str, Any] = {
            "folds": [{k: v.date().isoformat() for k, v in x.items()} | {"regime": regimes[i]} for i, x in enumerate(folds)],
            "selection": sel_tables, "totals_10bp": totals[10.0],
            "fold_metrics": {k: [{kk: m[kk] for kk in ("total_return", "maximum_drawdown", "cagr")} for m in v]
                             for k, v in fold_metrics.items()},
            "gate_reference": {},
        }
        base_tot, base_folds = totals[10.0]["B0"], fold_metrics["B0"]
        for name in row_names:
            if name in ("B0", "B1"):
                continue
            g = g1_g2(totals[10.0][name], base_tot)
            g.update(gate_folds(fold_metrics[name], base_folds, regimes))
            window_out["gate_reference"][name] = g
        if full_gates:
            window_out["totals_stress"] = {str(c): totals[c] for c in (20.0, 50.0)}
            window_out["totals_zero_cash_yield"] = {}
            for name in row_names:
                if name in selections:
                    z_run = stitched_run(f, targets, runs_zero, selections[name], fold_pos, 10.0, cash_yield=False)
                else:
                    z_run = runs_zero[name]
                window_out["totals_zero_cash_yield"][name] = slice_metrics(z_run, dates, a_all, z_all, name)
            window_out["cap_0.517_defaults"] = {name: slice_metrics(r, dates, a_all, z_all, name) for name, r in cap_runs.items()}
            # neighbours (fixed parameters, 10 bp)
            nb_tot = {name: slice_metrics(runs[10.0][name], dates, a_all, z_all, name)
                      for name in FAMILY_C1 + FAMILY_C2 + ["C1_daily"]}
            window_out["neighbor_totals_10bp"] = nb_tot
            window_out["neighbor_g1_g2"] = {name: g1_g2(m, base_tot) for name, m in nb_tot.items()}
            gates = {}
            for name in GATE_ROWS:
                g = dict(window_out["gate_reference"][name])
                fam = FAMILY_C1 if name.startswith("C1") else FAMILY_C2 if name.startswith("C2") else None
                g20 = g1_g2(totals[20.0][name], totals[20.0]["B0"])
                c50, b50 = totals[50.0][name], totals[50.0]["B0"]
                g["G4_20bp_G1_G2"] = bool(g20["G1"] and g20["G2"])
                g["G4_50bp_direction"] = bool(c50["maximum_drawdown"] > b50["maximum_drawdown"] and
                                              c50["calmar"] is not None and b50["calmar"] is not None and
                                              c50["calmar"] > b50["calmar"])
                if fam is None:
                    g["G4_neighbors"], g["G4_neighbors_note"] = None, "not_applicable_no_neighbors_defined"
                else:
                    nb = [n_ for n_ in fam if n_ != name.replace("_WF", "")]
                    passing = sum(1 for n_ in nb if window_out["neighbor_g1_g2"][n_]["G1"] and window_out["neighbor_g1_g2"][n_]["G2"])
                    g["G4_neighbors_passing"], g["G4_neighbors_total"] = passing, len(nb)
                    g["G4_neighbors"] = bool(passing > len(nb) / 2)
                g["G4"] = bool(g["G4_20bp_G1_G2"] and g["G4_50bp_direction"] and g["G4_neighbors"] is not False)
                # G6: independent observations inside the OOS window
                if name.endswith("_WF"):
                    sched = selections[name]
                    if name.startswith("C1"):
                        count = events_in_folds(targets, sched, fold_pos, {"ep_start"})
                        exits = None
                    else:
                        count = events_in_folds(targets, sched, fold_pos, {"full_entry"})
                        exits = events_in_folds(targets, sched, fold_pos, {"exit_crash", "exit_drawdown"})
                else:
                    ev = targets[name].events
                    if name == "C1":
                        count, exits = sum(1 for e in ev if e["kind"] == "ep_start" and a_all <= e["idx"] <= z_all), None
                    else:
                        count = sum(1 for e in ev if e["kind"] == "full_entry" and a_all <= e["idx"] <= z_all)
                        exits = sum(1 for e in ev if e["kind"].startswith("exit") and a_all <= e["idx"] <= z_all)
                g["G6_independent_observations"], g["G6_exits"] = count, exits
                g["G6"] = bool(count >= 20)
                core_ok = bool(g["G1"] and g["G2"] and g["G3"] and g["G4"] and g["G5"])
                g["G1_to_G5_all_pass"] = core_ok
                g["verdict"] = ("S5_proposal_candidate_only" if core_ok and g["G6"] else
                                "review_only_insufficient_observations" if core_ok else "gate_failed")
                gates[name] = g
            window_out["gates"] = gates
        return window_out, by_cost, fold_pos, selections

    primary, by_cost, fold_pos, selections = evaluate("primary", *PRIMARY, families=True, full_gates=True)
    result["primary"] = primary
    a_all, z_all = fold_pos[0][0], fold_pos[-1][1]
    bundle = by_cost[10.0]

    # extras on primary OOS
    result["extras_primary_oos"] = {
        "extremes": {name: extremes(run, dates, a_all, z_all) for name, run in bundle.items()},
        "top_days": top_days(f, bundle, a_all, z_all),
    }
    events_map = {"C2": targets["C2"].events, "C3": targets["C2"].events}
    result["extras_primary_oos"]["c2_diagnostics"] = c2_diagnostics(f, targets["C2"].events, a_all, z_all)
    full_a = 200
    core = {k: runs[10.0][k] for k in ("B0", "B1", "C1", "C2", "C3")}
    result["extras_full_history"] = {
        "note": "continuous causal run over all data; episodes before 2021-08-05 are in-sample design reference",
        "crash_episodes": episode_table(f, core, events_map),
        "top_days": top_days(f, core, full_a, n - 1),
        "c2_diagnostics": c2_diagnostics(f, targets["C2"].events, full_a, n - 1),
        "extremes": {name: {k: v for k, v in extremes(run, dates, full_a, n - 1).items()} for name, run in core.items()},
    }
    aux1, _, _, _ = evaluate("aux1", *AUX1, families=True, full_gates=False)
    result["aux_oos_2013_2021"] = aux1
    last = dates[-1]
    if last >= pd.Timestamp(AUX2_START):
        a2, z2 = positions(dates, pd.Timestamp(AUX2_START), last)
        result["aux_oos_after_2026_08_05"] = {
            "range": [dates[a2].date().isoformat(), dates[z2].date().isoformat()], "sessions": z2 - a2 + 1,
            "defaults_10bp": {name: slice_metrics(runs[10.0][name], dates, a2, z2, name)
                              for name in ("B0", "B1", "C1", "C2", "C3")},
            "note": "partial fold, defaults only, report only"}
    else:
        result["aux_oos_after_2026_08_05"] = {"note": "no completed session after 2026-08-05"}

    # QQQ -> TQQQ auxiliary (defaults only, report only)
    ft = build_features(frames["TQQQ"], frames["QQQ"], split_days["QQQ"], treasury)
    tq_targets = {k: v for k, v in build_targets(ft, CAP, with_report_only=False).items()
                  if k in ("B0", "B1", "C1", "C2", "C3")}
    tq_runs = {k: run_target(ft, v, 10.0) for k, v in tq_targets.items()}
    aux_windows = {"primary": PRIMARY, "aux_2013_2021": AUX1, "aux_after_2026_08_05": (AUX2_START, ft.dates[-1].strftime("%Y-%m-%d"))}
    tq_out: dict[str, Any] = {}
    for label, (s_, e_) in aux_windows.items():
        try:
            a, z = positions(ft.dates, pd.Timestamp(s_), pd.Timestamp(e_))
            tq_out[label] = {k: slice_metrics(r, ft.dates, a, z, k) for k, r in tq_runs.items()}
        except RuntimeError as exc:
            tq_out[label] = {"note": str(exc)}
    result["aux_qqq_tqqq_defaults_report_only"] = tq_out
    result["_daily"] = (daily, dates, bundle, a_all, z_all)
    result["_causality"] = causality_real(frames, split_days, treasury)
    return result


def causality_real(frames, split_days, treasury) -> dict[str, Any]:
    full = build_targets(build_features(frames["SOXL"], frames["SOXX"], split_days["SOXX"], treasury), CAP)
    n = len(frames["SOXL"])
    cuts = [int(n * x) for x in (0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95)] + [n - 1]
    checked = []
    for T in cuts:
        part = build_targets(build_features(frames["SOXL"].iloc[:T], frames["SOXX"].loc[:frames["SOXL"].index[T - 1]],
                                            split_days["SOXX"], treasury), CAP)
        for name, tg in part.items():
            if not np.array_equal(tg.w, full[name].w[:T], equal_nan=True):
                raise RuntimeError(f"future information detected: {name} at cut {T}")
            if tg.stage is not None and not np.array_equal(tg.stage, full[name].stage[:T], equal_nan=True):
                raise RuntimeError(f"future information detected in stage: {name} at cut {T}")
        checked.append(int(T))
    return {"status": "passed", "truncation_lengths": checked, "variants_checked": list(full)}


# ----------------------------------------------------------------------------
# self-test (synthetic data, no network)
# ----------------------------------------------------------------------------
def synthetic_market(n: int = 760, seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2015-01-05", periods=n)
    r = rng.normal(0.0007, 0.011, n)
    for start in (260, 470, 640):
        r[start] = -0.075
        r[start + 1:start + 4] = rng.normal(-0.004, 0.006, 3)
        r[start + 4:start + 12] = rng.normal(0.006, 0.006, 8)
        r[start + 8] = 0.035
    vol = rng.lognormal(13, 0.3, n)
    vol[[268, 478, 648]] *= 3

    def frame(ret: np.ndarray, lev: float) -> pd.DataFrame:
        close = 100 * np.exp(np.cumsum(lev * ret))
        prev = np.r_[100.0, close[:-1]]
        open_ = prev * (1 + rng.normal(0, 0.004, n) * lev)
        high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.003, n)))
        low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.003, n)))
        early = np.zeros(n, bool)
        early[[100, 300]] = True
        return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "adjclose": close,
                             "volume": vol * (1 + 0.1 * lev), "is_early_close": early}, index=idx)

    return frame(r, 3.0), frame(r + rng.normal(0, 0.002, n), 1.0)


def self_test() -> None:
    wf = wf_mod()
    checks: dict[str, Any] = {}

    # calendar generator vs the transcribed 2018-09..2026-07 list
    lo, hi = "2018-09-01", "2026-07-31"
    gen = {d for d in FULL_CLOSURES if lo <= d <= hi}
    old = {d for d in wf.FULL_CLOSURES if lo <= d <= hi}
    assert gen == old, (sorted(gen ^ old))
    assert "2010-12-31" not in FULL_CLOSURES and "2011-12-30" not in FULL_CLOSURES  # Saturday New Year
    assert {"2012-10-29", "2012-10-30", "2018-12-05", "2025-01-09", "2010-12-24", "2010-07-05"} <= FULL_CLOSURES
    assert len(expected_sessions("2010-01-04", "2010-12-31")) == 252
    checks["calendar_matches_transcribed_list"] = True

    # C2 state machine scenarios (hand-built arrays)
    n = 90
    close = np.full(n, 100.0)
    close[:60] = 100 + np.arange(60) * 0.1
    close[60] = close[59] * 0.95
    for i, step in zip(range(61, 64), (1.005,) * 3):
        close[i] = close[i - 1] * step
    close[64] = close[63] * 1.03
    close[65:] = close[64] * (1 + 0.002 * np.arange(1, n - 64))
    prev = np.r_[close[0], close[:-1]]
    ret = close / prev - 1
    vol = np.full(n, 1000.0)
    vol[64] = 2000.0
    args = dict(close=close, close_prev=prev, ret=ret, sd_prev=np.full(n, 0.01), sma50=close * 0.5,
                ema10=close * 1.0, ema20=close * 0.9, vol=vol, vol_prev=np.r_[vol[0], vol[:-1]],
                vol_ok=np.ones(n, bool))
    stage, ev = c2_stage(**args, k=2.5, d=0.10, g=0.02, use_sma=True)
    assert stage[60] == 0 and list(stage[61:64]) == [0, 0, 0] and stage[64] == 1 and stage[65] == 2, stage[58:68]
    trans = [(stage[i - 1], stage[i]) for i in range(1, n) if stage[i] != stage[i - 1]]
    assert (0, 2) not in trans  # no direct out -> full path
    assert [e["kind"] for e in ev][:4] == ["start_full", "exit_crash", "half_entry", "full_entry"]
    args_ea = dict(args)
    args_ea["vol_ok"] = np.zeros(n, bool)
    stage_nv, _ = c2_stage(**args_ea, k=2.5, d=0.10, g=0.02, use_sma=True)
    assert stage_nv[64] == 0 and stage_nv[70] == 0  # volume condition fail-closed
    close2 = close.copy()
    close2[65:] = close2[60] * 0.99  # below rally_low right after half entry, but not a -k crash day
    prev2 = np.r_[close2[0], close2[:-1]]
    sd2 = np.full(n, 0.01)
    sd2[65:] = 0.05
    a2 = dict(args, close=close2, close_prev=prev2, ret=close2 / prev2 - 1, sd_prev=sd2, sma50=close2 * 0.5,
              ema10=close2, ema20=close2 * 0.9)
    stage2, ev2 = c2_stage(**a2, k=2.5, d=0.10, g=0.02, use_sma=True)
    assert stage2[64] == 1 and stage2[65] == 0 and "half_fail_ftd" in [e["kind"] for e in ev2]
    a3 = dict(a2, sd_prev=np.full(n, 0.01))  # same path with a -k crash day: half -> out as well
    stage3, ev3 = c2_stage(**a3, k=2.5, d=0.10, g=0.02, use_sma=True)
    assert stage3[64] == 1 and stage3[65] == 0 and "half_fail_crash" in [e["kind"] for e in ev3]
    dd_close = np.r_[np.linspace(100, 110, 60), 110 * (0.99 ** np.arange(1, 31))]
    dprev = np.r_[dd_close[0], dd_close[:-1]]
    sd, evd = c2_stage(dd_close, dprev, dd_close / dprev - 1, np.full(90, 0.01), dd_close * 0.5, dd_close, dd_close * 0.9,
                       np.full(90, 1000.0), np.full(90, 1000.0), np.ones(90, bool), 2.5, 0.10, 0.02, True)
    assert "exit_drawdown" in [e["kind"] for e in evd]
    checks["c2_state_machine"] = True

    # (2) signal at close t -> fill at t+1 open, (3) cost, (5) gap only at the open
    O = np.array([100, 100, 110, 90, 90, 90], float)
    C = np.array([100, 100, 121, 90, 90, 90], float)
    ok = np.ones(6, bool)
    days = np.ones(6)
    rate = np.zeros(6)
    tgt = np.array([0.5, 0.5, 0.0, 0.0, 0.0, 0.0])
    sim = simulate(O, C, ok, days, rate, tgt, 0.10, "band", 10.0, False)
    assert [tr["idx"] for tr in sim["trades"]] == [1, 3], sim["trades"]  # signal t=0 -> open t=1; signal t=2 (exit) -> open t=3
    first = sim["trades"][0]
    assert math.isclose(first["cost"], 0.0005) and math.isclose(first["dweight"], 0.5)
    assert math.isclose(sim["V"][1], 1 - 0.0005)  # filled at the t=1 open (100), flat intraday
    assert math.isclose(sim["V"][2], 0.5 * 121 / 100 + (1 - 0.5 - 0.0005))  # gap 100->110 and intraday 110->121 on 0.5
    # gap: at t=3 the position is marked to the open (C[2]=121 -> O[3]=90) before the exit fill at the open
    s_open = 0.5 * 121 / 100 * 90 / 121
    exit_tr = sim["trades"][1]
    assert math.isclose(exit_tr["notional"], s_open) and math.isclose(exit_tr["cost"], s_open * 0.001)
    assert math.isclose(sim["V"][3], (1 - 0.5 - 0.0005) + s_open - s_open * 0.001)
    checks["next_open_fill_cost_and_gap"] = True

    # (6) invalid open freezes the pending action
    ok2 = np.array([1, 1, 0, 1, 1, 1], bool)
    sim2 = simulate(O, np.full(6, 100.0), ok2, days, rate, np.array([0.0, 0.5, 0.5, 0.5, 0.5, 0.5]), 0.10, "band", 10.0, False)
    assert [tr["idx"] for tr in sim2["trades"]] == [3] and sim2["stale"] == [2]
    ok3 = np.array([1, 1, 1, 1, 1, 1], bool)
    O3 = O.copy()
    O3[2] = 0.0
    sim3 = simulate(O3, C, np.array([1, 1, 0, 1, 1, 1], bool), days, rate, np.array([0.0, 0.5, 0.5, 0.5, 0.5, 0.5]), 0.10)
    assert sim3["stale"] == [2] and 2 not in [tr["idx"] for tr in sim3["trades"]]
    checks["invalid_open_freeze"] = True

    # (4) folds: training ends before the test starts; selection ignores post-training data
    for window in (PRIMARY, AUX1):
        for fold in make_folds(*window):
            assert fold["train_end"] < fold["test_start"]
    assert len(make_folds(*PRIMARY)) == 10 and len(make_folds(*AUX1)) == 16
    assert make_folds(*PRIMARY)[0]["train_start"] == pd.Timestamp("2019-08-05")
    assert make_folds(*PRIMARY)[-1]["test_end"] == pd.Timestamp(PRIMARY[1])
    dates = pd.bdate_range("2019-01-01", "2023-12-29")
    rng = np.random.default_rng(3)

    def fake_run(scale: float) -> dict:
        r = rng.normal(0.0005 * scale, 0.01 * scale, len(dates))
        V = np.cumprod(1 + r)
        return {"V": V, "W": np.full(len(dates), 0.5), "trades": [], "stale": []}

    fake = {"B0": fake_run(1.0), **{f"X{i}": fake_run(0.5 + 0.2 * i) for i in range(5)}}
    fold = make_folds(*PRIMARY)[2]
    ch1, _ = select_variant(fake, dates, fold, [f"X{i}" for i in range(5)])
    a, z = positions(dates, fold["train_start"], fold["train_end"])
    tampered = {k: {**v, "V": np.r_[v["V"][:z + 1], v["V"][z + 1:] * rng.uniform(0.2, 5, len(v["V"]) - z - 1)]}
                for k, v in fake.items()}
    ch2, _ = select_variant(tampered, dates, fold, [f"X{i}" for i in range(5)])
    assert ch1 == ch2
    checks["folds_and_selection_causality"] = True

    # (1) no future information: >= 8 truncated histories give identical signals
    trade_df, signal_df = synthetic_market()
    full = build_targets(build_features(trade_df, signal_df), CAP)
    exits = [e for e in full["C2"].events if e["kind"].startswith("exit")]
    assert len(exits) >= 1 and np.isfinite(full["C1"].w).sum() > 100 and np.isfinite(full["C3"].w).sum() > 100
    cuts = [300, 340, 380, 430, 480, 540, 600, 660, 720]
    for T in cuts:
        part = build_targets(build_features(trade_df.iloc[:T], signal_df.iloc[:T]), CAP)
        for name, tg in part.items():
            assert np.array_equal(tg.w, full[name].w[:T], equal_nan=True), (name, T)
            if tg.stage is not None:
                assert np.array_equal(tg.stage, full[name].stage[:T], equal_nan=True), (name, T)
    checks["truncated_history_signals_equal"] = {"cuts": cuts, "variants": list(full)}
    print(json.dumps({"status": "passed", **checks}, ensure_ascii=False))


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def check_protocol() -> dict[str, str]:
    raw = PROTOCOL.read_bytes()
    now = {"raw_bytes_sha256": hashlib.sha256(raw).hexdigest(),
           "lf_normalized_sha256": hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()}
    side = dict(line.split("=", 1) for line in PROTOCOL_SIDECAR.read_text(encoding="utf-8").splitlines() if "=" in line)
    if side.get("raw_bytes_sha256") != now["raw_bytes_sha256"] or side.get("lf_normalized_sha256") != now["lf_normalized_sha256"]:
        raise RuntimeError("protocol changed after pre-registration; refusing to run")
    return now


def run_all(out_dir: Path) -> int:
    protocol_hash = check_protocol()
    data = load_inputs()
    res = run_windows(data)
    daily, dates, bundle, a_all, z_all = res.pop("_daily")
    causality = res.pop("_causality")
    for name, run in bundle.items():
        daily[f"{name}_equity"] = pd.Series(run["V"] / run["V"][a_all - 1], index=dates)
        daily[f"{name}_weight"] = pd.Series(run["W"], index=dates)
    daily.iloc[a_all:z_all + 1].to_csv(out_dir / f"{STEM}_daily.csv", index_label="date")
    trades = []
    for name, run in bundle.items():
        for tr in run["trades"]:
            if a_all <= tr["idx"] <= z_all:
                trades.append({"strategy": name, "date": dates[tr["idx"]].date().isoformat(),
                               "dweight": tr["dweight"], "target_weight": tr["target"], "cost_nav": tr["cost"]})
    pd.DataFrame(trades).to_csv(out_dir / f"{STEM}_trades.csv", index=False)
    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "classification": "historical_walk_forward_research_grade_D_C_not_untouched_future_test",
        "authority": {"order_authority": False, "quantity_authority": "none",
                      "activation": "requires S5 proposal, S6 Judge, S7 user approval, then forward shadow"},
        "protocol": {"file": PROTOCOL.name, **protocol_hash},
        "runner_sha256": sha256_file(Path(__file__).resolve()),
        "existing_scripts_imported_read_only": {BASE_SCRIPT.name: sha256_file(BASE_SCRIPT), WF_SCRIPT.name: sha256_file(WF_SCRIPT)},
        "inputs": {"end_date": data["end"], "sources_json_sha256": sha256_file(SOURCES_JSON),
                   "sources": data["sources"]["symbols"] and {
                       s: {k: v for k, v in i.items() if k in ("first_date", "last_date", "yahoo_single_source_count",
                                                               "mismatch_count_after_split_alignment",
                                                               "split_basis_explained_rows", "combined_csv")}
                       for s, i in data["sources"]["symbols"].items()},
                   "treasury": data["sources"].get("treasury")},
        "causality_check_real_data": causality,
        "constants": {"cap": CAP, "cap_sensitivity": CAP_LOW, "band": BAND, "costs_bps": COSTS,
                      "c1_variants": C1_VARIANTS, "c1_report_only": C1_REPORT_ONLY, "c2_variants": C2_VARIANTS},
        "results": res,
    }
    (out_dir / f"{STEM}_results.json").write_text(json.dumps(clean(output), ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"status": "passed", "results": f"{STEM}_results.json",
                      "verdicts": {k: v["verdict"] for k, v in res["primary"]["gates"].items()}}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--end", default=None, help="override last completed session (YYYY-MM-DD)")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=HERE)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.collect:
        return collect(args.end)
    if args.run:
        return run_all(args.output_dir)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
