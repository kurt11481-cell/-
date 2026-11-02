#!/usr/bin/env python3
"""strategy-1101 scoring, pre-registered 2026-11-02: reduce the 3x product to E 1.55 vs to E 1.89.

Contract: docs/claude/strategy1101-score-preregistration-2026-11-02.md up to its marker line (MARK;
results go below it, into section 11) + the .sha256 sidecar (body_sha256, runner_sha256, one fixed_at,
later amended_at lines). Both hashes are taken on UTF-8/LF-normalised text (a BOM, UTF-16 or CRLF
re-save does not break them). One run per round: the results file is created exclusively and section
11 must still show that round's placeholder line; round 2 links round 1's results by hash.

Question.  T0 = the first US session from 2026-11-02 on whose close the account's 3x holdings are
smaller than at the previous core snapshot (the first reduction after the 2026-11-01 decision).
From the same pre-trade holdings at the T0 close, build two hypothetical accounts by cutting only
the 3x products (all by the same factor, freed value to cash):
  (2)  'b19'  : the largest 3x size with core E <= 1.89  (10/31 decision B, 'just below 1.9')
  (2') 'b155' : the largest 3x size with core E <= 1.55  (11/01 decision strategy-1101)
Both are held unchanged (buy-and-hold, cash earns 0, no fees) to the window end.  Verdicts:
  decision  = (2') vs (2): difference of U = R - MDD (window return minus maximum drawdown,
              account terms) against a 1.0 %p band; a 1.55 win says whether its return was also
              higher or it traded return for a shallower drawdown
  simple    = (2') vs (4), (4) = SOXL/cash constant mix rebalanced every session at the
              window-average E of (2') (post-hoc baseline, constitution 2-1 / 29); a tie -> (4)
  execution = actual account (1) vs (2') on the same U gap, and the actual post-trade E vs 1.55
  cap_3x    = round 2 only: 3x share of the account <= 10% at the window end

E is the core's own measure (manage-us-stock-strategy/scripts/portfolio_exposure.py 195-338, split
guard 52-53, as of commit a3c7932 of 2026-10-30): E = max(N, V), N = sum(multiplier x weight), V = sample std of the fixed-weight
portfolio's close-to-close returns over the core window / sample std of SOXX's, cash return 0,
split-adjusted regular-session closes.  This file re-implements it (no core import) and must
reproduce the core's own E and V on the reference snapshots (gate), so a later core change cannot
move the hypothetical accounts; those use window 252 / minimum 60 and the pre-trade multipliers.

Inputs (read-only, under --root): workspace/outputs/exposure-review/*/portfolio-exposure-review.*.json,
workspace/outputs/regular-session-closes/history/*.close-history.json and .../corporate-actions.json.
The core keeps closes only for held, watchlist and configured symbols, so a symbol the hypothetical
accounts still hold can stop getting closes after a sale. Only then, and only for the missing sessions,
public Nasdaq daily closes saved under workspace/outputs/strategy1101-score-supplement/ (never in
docs/claude: the file name would show a holding) fill the gap after a level check against the core.
A needed symbol with closes missing in the window or in the 252 sessions before T0 stops the run (no
file written) until a supplement fetched after the window-end close covers them.
Output: ratios, E values, counts and verdicts only - never amounts, quantities, holdings names or
per-symbol weights (docs/claude goes to GitHub, 00-home line 28).  Run it in the cloud container
on staged copies.  No broker, no Kiwoom, no policy/state/journal writes, no orders.

Stops write nothing and start with a tag (pre-registration 7): STOP[wait] = run again later unchanged
(judge date, core closes not there yet, a split the core has not recorded); STOP[restage] = copy or fetch
the inputs again (reviews, histories, supplements, section 11 lines, contract files restored from git);
STOP[amend] = only an amendment can help; STOP[done] = the round was already run or closed. An
unexpected error prints 'STOP[amend]: unexpected <type>' without its message (--debug re-raises).

  --self-test           synthetic checks only (no contract, no account data)
  --check               inputs + E replication + T0 detection + symbols that need a supplement
                        (console only); no returns, no verdicts, no file
  --run --round {1,2}   contract + date guard, compute once, write the round's results JSON
                        (never overwrites) and print results_sha256 (UTF-8/LF, for section 11)
"""

from __future__ import annotations

import argparse
import contextlib
import glob
import hashlib
import io
import json
import math
import random
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

KST = timezone(timedelta(hours=9))
ROOT_DEFAULT = Path(__file__).resolve().parents[2]
PREREG = "docs/claude/strategy1101-score-preregistration-2026-11-02.md"
SIDECAR = "docs/claude/strategy1101-score-preregistration-2026-11-02.sha256"
RESULTS = {1: "docs/claude/strategy1101-score-results-r1.json",
           2: "docs/claude/strategy1101-score-results-r2.json"}
# The pre-registration is fixed up to this line; results are appended below it (section 11) without
# breaking the contract. Everything above it is hashed (body_sha256, LF line ends).
MARK = "<!-- strategy1101-score: 이 줄 아래는 고정 해시 밖 — 결과만 덧붙인다 -->"
PLACEHOLDER = {1: "- 1차: (2026-12-30 KST 이후)", 2: "- 2차: (2027-03-29 KST 이후)"}   # section 11 lines
EXPO_GLOB = "workspace/outputs/exposure-review/*/portfolio-exposure-review.*.json"
HIST_DIR = "workspace/outputs/regular-session-closes/history"
CORP = "workspace/outputs/regular-session-closes/corporate-actions.json"

# Parameters fixed by the pre-registration (sections 3-5). Never edit after seeing a result.
FIRST_SESSION = "2026-11-02"      # first US session after the 2026-11-01 21:34 KST decision
TARGET_19 = 1.89                  # (2)  'just below 1.9' (10/31 decision B)
TARGET_155 = 1.55                 # (2') strategy-1101
BAND = 0.010                      # 1.0 %p of the account, for return and drawdown differences
EXEC_E_TOL = 0.05                 # actual post-trade E within 1.55 +- 0.05 = 'as decided'
QTY_TOL = 0.005                   # 3x value at common prices down by more than 0.5% = a reduction
MIN_SESSIONS = 10                 # fewer window sessions after T0 = no verdict for that round
APPROX_MAX = 0.20                 # more approximate sessions than this share = no verdict for (1)
REPL_FROM = "2026-10-13"          # replication reference snapshots from this evaluation session
REPL_TOL = 0.005                  # max |E_calc - E_core| on the reference snapshots
REPL_MIN = 5                      # at least this many reference snapshots
CAP_3X = 0.10                     # structure target: 3x <= 10% of the account (round 2, report)
MULT_3X = 3.0                     # nominal multiplier >= 3 = a '3x product'
BENCH = "SOXX"
LEVER = "SOXL"                    # the 3x product of the simple baseline (4)
SPLIT_LOW, SPLIT_HIGH = 0.5, 2.0  # core split guard (portfolio_exposure.py 52-53)
GRID = 2000                       # 3x scale search grid before bisection
BIG_MOVE = 0.25                   # report: daily close moves above 25% in the window (split check)
WEIGHT_SUM_TOL = 1e-3
SUPP_DIR = "workspace/outputs/strategy1101-score-supplement"   # <SYM>.nasdaq-historical.json
SUPP_OVERLAP = 20                 # level check on the last 20 sessions that have both closes
SUPP_MIN_OVERLAP = 10             # fewer overlap sessions = STOP (cannot check the level)
SUPP_MEDIAN_TOL = 0.005           # median |Nasdaq / core - 1| on the overlap
SUPP_MAX_TOL = 0.03               # max |Nasdaq / core - 1| on the overlap
GAP_SHARE = 0.05                  # per symbol, missing window closes allowed (after any supplement)
WINDOW, MINIMUM = 252, 60         # core window and minimum returns, pinned for the hypothetical accounts
SPLIT_NEAR = 0.05                 # a day ratio within 5% of k or 1/k (k in SPLIT_KS) = an unrecorded split?
SPLIT_KS = (2, 3, 4, 5, 8, 10, 15, 20, 25, 50)
SPLIT_MARKET_TOL = 0.10           # SOXL: a day ratio more than 0.10 away from 1 + 3 x SOXX's = a jump
ROUNDS = {1: {"end": "2026-12-29", "judge_kst": "2026-12-30"},
          2: {"end": "2027-03-25", "judge_kst": "2027-03-29"}}


class Stop(RuntimeError):
    """Any Stop writes no result (pre-registration 7: stop = NO_CHANGE)."""


# ----------------------------------------------------------------------------- helpers

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sstd(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = math.fsum(values) / len(values)
    return math.sqrt(math.fsum((v - mean) ** 2 for v in values) / (len(values) - 1))


def mdd(path: list[float]) -> float:
    """Maximum drawdown of a value path as a positive fraction (0.25 = -25%), start included."""
    peak, worst = path[0], 0.0
    for v in path:
        peak = max(peak, v)
        worst = max(worst, 1.0 - v / peak)
    return worst


def rnd(x: float | None, k: int = 6) -> float | None:
    return None if x is None else round(float(x), k)


def _num(x: Any) -> float | None:
    """A finite number from a JSON field, else None."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _iso(x: Any) -> str:
    """A session date as YYYY-MM-DD (dates are compared as strings); anything else is a ValueError."""
    s = str(x)
    if len(s) != 10 or date.fromisoformat(s).isoformat() != s:
        raise ValueError("not a YYYY-MM-DD date")
    return s


def _read_json(path: Path, kind: str) -> Any:
    """A staged input as JSON (BOM/UTF-16/CRLF tolerated). An unreadable file stops the run without
    naming it - a file name can show a holding."""
    try:
        return json.loads(_norm(path.read_bytes()).decode("utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise Stop(f"STOP[restage]: a {kind} file is not readable JSON - copy it again and run again "
                   "(no amendment)") from None


# ----------------------------------------------------------------------------- data

class Snap:
    """One core exposure review (latest file of its evaluation session). Weights stay in memory."""

    def __init__(self, path: Path, rel: str, raw: dict[str, Any]) -> None:
        self.rel = rel
        self.sha = sha256_file(path)
        self.S: str = _iso(raw["evaluation_session"])
        a_ = (raw.get("snapshot") or {}).get("as_of")
        self.A: str | None = None if a_ is None else _iso(a_)
        x = raw.get("exposure") or {}
        self.status: str = x.get("status")
        self.E_core = _num(x.get("effective"))
        self.N_core = _num(x.get("nominal"))
        self.V_core = _num(x.get("sox_equivalent"))
        win_, min_ = _num(x.get("window_sessions")), _num(x.get("minimum_sessions"))
        self.window = None if win_ is None else int(win_)
        self.minimum = None if min_ is None else int(min_)
        eq = raw.get("equity") or {}
        self.equity_ok = eq.get("status") == "AVAILABLE"
        self.equity = _num(eq.get("closing_equity_usd"))
        self.cash_w = _num(eq.get("cash_weight"))
        rl = raw.get("review_lines") or {}
        self.lines_status = rl.get("status")
        self.l4 = next((bool(ln.get("triggered_in_current_drawdown")) for ln in rl.get("lines") or []
                        if ln.get("line_id") == "L4"), None)
        self.w: dict[str, float] = {}
        self.mult: dict[str, float] = {}
        self.pclose: dict[str, float] = {}
        for p in raw.get("positions") or []:
            m = float(p["nominal_multiplier"])
            if not math.isfinite(m):
                raise ValueError("multiplier")
            self.mult[p["symbol"]] = m
            if p.get("weight"):
                wv, cv = float(p["weight"]), float(p["close"])
                if not (math.isfinite(wv) and math.isfinite(cv)):
                    raise ValueError("weight or close")
                self.w[p["symbol"]] = wv
                self.pclose[p["symbol"]] = cv
        total = sum(self.w.values()) + (self.cash_w or 0.0)
        self.usable = (self.equity_ok and self.A is not None and self.cash_w is not None
                       and (bool(self.w) or abs(float(self.cash_w) - 1.0) <= WEIGHT_SUM_TOL)
                       and self.equity is not None and self.equity > 0
                       and all(v >= 0 for v in self.w.values())
                       and abs(total - 1.0) <= WEIGHT_SUM_TOL)


class Data:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.inputs: list[tuple[str, str]] = []
        corp_path = root / CORP
        self.splits: list[dict[str, Any]] = []
        if corp_path.exists():
            corp = _read_json(corp_path, "corporate-actions")
            self.inputs.append((CORP, sha256_file(corp_path)))
            try:
                for a in corp.get("actions", []):
                    if a.get("action_type") != "SPLIT":
                        raise Stop("STOP[amend]: corporate-actions.json holds an action type other than SPLIT")
                    ratio = float(a["new_shares"]) / float(a["old_shares"])
                    if not (math.isfinite(ratio) and ratio > 0):
                        raise ValueError("split ratio")
                    self.splits.append({"symbol": a["symbol"], "effective": _iso(a["effective_session"]),
                                        "ratio": ratio})
            except (KeyError, TypeError, ValueError, AttributeError, ZeroDivisionError):
                raise Stop("STOP[restage]: corporate-actions.json lacks a field the calculation reads - copy it "
                           "again and run again (no amendment)") from None
        self.closes: dict[str, dict[str, float]] = {}      # only symbols with at least one core close
        self.unverified: dict[str, set[str]] = {}
        self.supplied: dict[str, set[str]] = {}
        self.supp_span: dict[str, tuple[str, str]] = {}    # first and last date of each loaded supplement
        self.supp_ignored = 0
        hist = sorted((root / HIST_DIR).glob("*.close-history.json"))
        if not hist:
            raise Stop("STOP[restage]: no close histories - copy the core close history folder and run again")
        for f in hist:
            d = _read_json(f, "close history")
            try:
                sym = str(d["symbol"])
                series: dict[str, float] = {}
                unv: set[str] = set()
                for s in d["sessions"]:
                    t = _iso(s["session_date"])
                    c = float(s["close"])
                    if not math.isfinite(c) or c <= 0:
                        raise Stop("STOP[wait]: a core close history holds a non-finite or non-positive close - "
                                   "run again after the core has corrected it (no amendment)")
                    series[t] = c / self.factor(sym, t)
                    if not s.get("verified", False):
                        unv.add(t)
            except (KeyError, TypeError, ValueError, AttributeError):
                raise Stop("STOP[restage]: a close history file lacks a field the calculation reads - copy it "
                           "again and run again (no amendment)") from None
            self.inputs.append((f"{HIST_DIR}/{f.name}", sha256_file(f)))
            if series:
                self.closes[sym] = series
                self.unverified[sym] = unv
        if BENCH not in self.closes:
            raise Stop(f"STOP[restage]: no {BENCH} close history - copy the core close history folder and run again")
        # the calendar comes from the core histories only; a supplement fills dates already in it
        self.cal = sorted(set().union(*[set(v) for v in self.closes.values()]))
        self.cal_set = set(self.cal)
        sdir = root / SUPP_DIR
        for f in sorted(sdir.glob("*.nasdaq-historical.json")) if sdir.is_dir() else []:
            self.load_supplement(f)
        latest: dict[str, tuple[str, Path, Any]] = {}
        for p in glob.glob(str(root / EXPO_GLOB)):
            path = Path(p)
            raw = _read_json(path, "exposure review")
            S = raw.get("evaluation_session") if isinstance(raw, dict) else None
            if not S:
                continue
            if not isinstance(S, str):
                raise Stop("STOP[restage]: an exposure review file lacks a field the calculation reads - copy "
                           "it again and run again (no amendment)")
            key = path.name  # portfolio-exposure-review.<UTC timestamp>.json sorts by time
            if S not in latest or key > latest[S][0]:
                latest[S] = (key, path, raw)
        self.snaps: list[Snap] = []
        for S in sorted(latest):
            _, path, raw = latest[S]
            rel = path.relative_to(root).as_posix()
            try:
                snap = Snap(path, rel, raw)
            except (KeyError, TypeError, ValueError, AttributeError):
                raise Stop("STOP[restage]: an exposure review file lacks a field the calculation reads - copy "
                           "it again and run again (no amendment)") from None
            self.inputs.append((rel, snap.sha))
            self.snaps.append(snap)
        self.carry: dict[str, int] = {}

    def load_supplement(self, f: Path) -> None:
        """Fill only calendar sessions a core history lacks, after a level check (both raw, unadjusted).
        A file for a symbol without a core history is ignored and counted: there is no level to check
        it against and the calculation never reads such a symbol. Stop messages never name the symbol
        (they may be copied into section 11, which is public)."""
        sym = f.name.split(".")[0].upper()
        core = self.closes.get(sym)
        if core is None:
            self.supp_ignored += 1
            return
        raw = _read_json(f, "supplement")
        ser: dict[str, float] = {}
        try:
            rows = ((raw.get("data") or {}).get("tradesTable") or {}).get("rows") or []
            for r in rows:
                m, d, y = str(r["date"]).split("/")
                c = float(str(r["close"]).replace("$", "").replace(",", ""))
                if not math.isfinite(c) or c <= 0:
                    raise Stop("STOP[restage]: a supplement file holds a non-finite or non-positive close - "
                               "fetch it again (pre-registration 4-3)")
                ser[date(int(y), int(m), int(d)).isoformat()] = c
        except (KeyError, TypeError, ValueError, AttributeError):
            raise Stop("STOP[restage]: a supplement file is not in the Nasdaq historical format - fetch it again "
                       "(pre-registration 4-3)") from None
        both = sorted(t for t in ser if t in core)[-SUPP_OVERLAP:]
        if len(both) < SUPP_MIN_OVERLAP:
            raise Stop(f"STOP[restage]: a supplement file overlaps the core closes on {len(both)} sessions only - "
                       "fetch it again from the start date in pre-registration 4-3")
        dev = sorted(abs(ser[t] / (core[t] * self.factor(sym, t)) - 1.0) for t in both)
        if dev[len(dev) // 2] > SUPP_MEDIAN_TOL or dev[-1] > SUPP_MAX_TOL:
            raise Stop("STOP[restage]: a supplement file's level differs from the core closes - check that it "
                       "holds unadjusted daily closes of the same symbol and fetch it again")
        self.inputs.append((f"{SUPP_DIR}/{f.name}", sha256_file(f)))
        filled = {t for t in ser if t in self.cal_set and t not in core and t > min(core)}
        for t in filled:
            core[t] = ser[t] / self.factor(sym, t)
        self.supplied[sym] = filled
        self.supp_span[sym] = (min(ser), max(ser))

    def factor(self, sym: str, session: str) -> float:
        """Split adjustment: closes before the effective session are divided by the ratio."""
        f = 1.0
        for a in self.splits:
            if a["symbol"] == sym and session < a["effective"]:
                f *= a["ratio"]
        return f

    def price(self, sym: str, t: str, count: bool = True, strict: bool = True) -> float | None:
        """Close at t, else the latest close before t (carried, counted). strict=False returns None
        when there is no close at or before t (a symbol bought before its history starts)."""
        series = self.closes.get(sym)
        if series is None:
            if strict:
                raise Stop("STOP[amend]: no close history for a symbol the calculation needs")
            return None
        if t in series:
            return series[t]
        before = [s for s in series if s < t]
        if not before:
            if strict:
                raise Stop(f"STOP[amend]: no close at or before {t} for a symbol the calculation needs")
            return None
        if count:
            self.carry[sym] = self.carry.get(sym, 0) + 1
        return series[max(before)]

    def prev_session(self, t: str) -> str | None:
        i = self.cal.index(t) if t in self.cal else None
        return self.cal[i - 1] if i else None

    def next_session(self, t: str | None) -> str | None:
        later = [s for s in self.cal if t is not None and s > t]
        return later[0] if later else None

    def sessions_between(self, a: str, b: str) -> list[str]:
        """Calendar sessions s with a < s <= b."""
        return [s for s in self.cal if a < s <= b]


# ----------------------------------------------------------------------------- core E replica

class Window:
    """Return series for one evaluation session (core common_window rule), cached per symbol set."""

    def __init__(self, data: Data, syms: list[str], end: str, window: int, minimum: int) -> None:
        self.ok = False
        self.reason = None
        self.returns: dict[str, list[float]] = {}
        cal = data.cal
        if end not in cal:
            self.reason = "V_EVALUATION_SESSION_NOT_IN_CALENDAR"
            return
        span = cal[:cal.index(end) + 1]
        first = {}
        for s in syms:
            series = data.closes.get(s, {})
            f = next((x for x in span if x in series), None)
            if f is None:
                self.reason = f"V_HISTORY_MISSING:{s}"
                return
            first[s] = f
        start = max(first.values())
        win = [x for x in span if x >= start][-(window + 1):]
        for s in syms:
            if any(x not in data.closes[s] for x in win):
                self.reason = "V_HISTORY_GAP"
                return
        if len(win) - 1 < minimum:
            self.reason = "V_HISTORY_BELOW_MINIMUM"
            return
        for s in syms:
            vals = [data.closes[s][x] for x in win]
            r = []
            for i in range(1, len(vals)):
                ratio = vals[i] / vals[i - 1] if vals[i - 1] > 0 else float("nan")
                if not math.isfinite(ratio) or ratio <= SPLIT_LOW or ratio >= SPLIT_HIGH:
                    self.reason = f"SPLIT_GUARD:{s}:{win[i]}"
                    return
                r.append(ratio - 1.0)
            self.returns[s] = r
        self.bstd = sstd(self.returns[BENCH])
        if not self.bstd:
            self.reason = "V_BENCHMARK_STD_ZERO"
            return
        self.n = len(win) - 1
        self.ok = True

    def V(self, w: dict[str, float]) -> float | None:
        held = [(v, self.returns[s]) for s, v in w.items() if v != 0]
        port = [math.fsum(v * series[i] for v, series in held) for i in range(self.n)]
        sd = sstd(port)
        return None if sd is None else sd / self.bstd


class ExposureCalc:
    def __init__(self, data: Data) -> None:
        self.data = data
        self.cache: dict[tuple[str, tuple[str, ...], int, int], Window] = {}

    def window(self, syms: list[str], end: str, window: int, minimum: int) -> Window:
        key = (end, tuple(sorted(set(syms) | {BENCH})), window, minimum)
        if key not in self.cache:
            self.cache[key] = Window(self.data, list(key[1]), end, window, minimum)
        return self.cache[key]

    def parts(self, w: dict[str, float], mult: dict[str, float], end: str, window: int,
              minimum: int) -> tuple[float, float | None, str | None]:
        held = {s: v for s, v in w.items() if v != 0}
        N = math.fsum(mult[s] * v for s, v in held.items())
        win = self.window(list(held), end, window, minimum)
        if not win.ok:
            return N, None, win.reason
        return N, win.V(held), None

    def E(self, w: dict[str, float], mult: dict[str, float], end: str, window: int,
          minimum: int) -> float | None:
        N, V, _ = self.parts(w, mult, end, window, minimum)
        return None if V is None else max(N, V)


def scale_3x(calc: ExposureCalc, w: dict[str, float], cash: float, mult: dict[str, float], end: str,
             window: int, minimum: int, target: float) -> tuple[dict[str, float], float, float, bool]:
    """Largest common factor lam in [0, 1] on all 3x weights with E <= target (freed value -> cash).

    Returns (weights, cash, E, unreached). unreached = even lam = 0 keeps E above the target."""
    three = [s for s, v in w.items() if mult.get(s, 1.0) >= MULT_3X and v > 0]

    def at(lam: float) -> tuple[dict[str, float], float]:
        out = dict(w)
        freed = 0.0
        for s in three:
            freed += out[s] * (1.0 - lam)
            out[s] = out[s] * lam
        return {s: v for s, v in out.items() if v != 0}, cash + freed

    def e_of(lam: float) -> float:
        ww, _ = at(lam)
        e = calc.E(ww, mult, end, window, minimum)
        if e is None:
            raise Stop(f"STOP[amend]: E unavailable at {end} for the hypothetical account")
        return e

    if e_of(1.0) <= target:
        ww, cc = at(1.0)
        return ww, cc, e_of(1.0), False
    if not three:
        ww, cc = at(1.0)
        return ww, cc, e_of(1.0), True
    best = None
    for k in range(GRID, -1, -1):
        if e_of(k / GRID) <= target:
            best = k
            break
    if best is None:
        ww, cc = at(0.0)
        return ww, cc, e_of(0.0), True
    lo, hi = best / GRID, (best + 1) / GRID
    for _ in range(50):
        mid = (lo + hi) / 2
        if e_of(mid) <= target:
            lo = mid
        else:
            hi = mid
    ww, cc = at(lo)
    return ww, cc, e_of(lo), False


# ----------------------------------------------------------------------------- holdings

def reprice(data: Data, w: dict[str, float], cash: float, frm: str, to: str,
            count: bool = True, strict: bool = True) -> tuple[dict[str, float], float]:
    """Same holdings valued at another session's closes, renormalised (cash unchanged in value).
    strict=False keeps a symbol without a close at its old value (ratio 1)."""
    vals = {}
    for s_, v in w.items():
        a, b = data.price(s_, frm, count, strict), data.price(s_, to, count, strict)
        vals[s_] = v * b / a if a and b else v
    total = math.fsum(vals.values()) + cash
    return {s_: v / total for s_, v in vals.items()}, cash / total


def reprice_pre(data: Data, f: Snap, to: str) -> tuple[dict[str, float], float]:
    """The pre-trade holdings valued at the `to` (T0) closes. The starting price is the core close on the
    snapshot's own session, else the snapshot's own close (a symbol bought that day whose core history
    starts later) - so such a symbol ends in hold 6 (E not computable), not in a stop."""
    vals = {}
    for s, v in f.w.items():
        a = data.closes.get(s, {}).get(f.S)
        if a is None:
            a = f.pclose[s] / data.factor(s, f.S)
        if not a > 0:
            raise Stop("STOP[amend]: a snapshot holds a non-positive close for a weighted position")
        vals[s] = v * data.price(s, to) / a
    total = math.fsum(vals.values()) + float(f.cash_w)
    return {s: v / total for s, v in vals.items()}, float(f.cash_w) / total


def snap_by_asof(data: Data) -> dict[str, Snap]:
    """One usable snapshot per holdings date A: prefer evaluation session == A, else the earliest S."""
    out: dict[str, Snap] = {}
    for f in data.snaps:
        if not f.usable:
            continue
        cur = out.get(f.A)
        if cur is None or (f.S == f.A and cur.S != cur.A) or (cur.S != cur.A and f.S < cur.S):
            out[f.A] = f
    return out


def holdings_at(data: Data, rep: dict[str, Snap], t: str,
                strict: bool = True) -> tuple[dict[str, float], float, bool, Snap]:
    """Weights at the t close from the latest holdings known as of t; fresh = holdings dated t."""
    dates = [a for a in rep if a <= t]
    if not dates:
        raise Stop(f"STOP[restage]: no usable holdings snapshot at or before {t} - copy all exposure reviews")
    f = rep[max(dates)]
    w, c = reprice(data, f.w, float(f.cash_w), f.S, t, strict=strict)
    return w, c, f.A == t, f


def implied_units(data: Data, f: Snap) -> dict[str, float]:
    """Split-adjusted share units held (internal only, never written)."""
    if any(f.pclose.get(s, 0.0) <= 0 for s in f.w):
        raise Stop("STOP[amend]: a snapshot holds a non-positive close for a weighted position")
    return {s: v * f.equity / (f.pclose[s] / data.factor(s, f.S)) for s, v in f.w.items()}


def reductions(data: Data, rep: dict[str, Snap], start: str, end: str) -> list[tuple[str, str]]:
    """(A, previous A) for each holdings date start <= A <= end whose 3x value at the A closes is more
    than QTY_TOL below the previous holdings date's (units, so deposits and withdrawals do not count)."""
    dates = sorted(rep)
    out = []
    for k in range(1, len(dates)):
        A, Ap = dates[k], dates[k - 1]
        if A < start:
            continue
        if A > end:
            break
        now, prev = rep[A], rep[Ap]
        un, up = implied_units(data, now), implied_units(data, prev)
        three = {s for s in set(un) | set(up)
                 if max(now.mult.get(s, 1.0), prev.mult.get(s, 1.0)) >= MULT_3X}
        if not three:
            continue
        px: dict[str, float] = {}
        for s in three:   # one common price per symbol; the snapshot close if the history has none yet
            p_ = data.price(s, A, False, strict=False)
            if p_ is None:
                src = now if s in now.pclose else prev
                p_ = src.pclose[s] / data.factor(s, src.S)
            px[s] = p_
        v_now = math.fsum(un.get(s, 0.0) * px[s] for s in three)
        v_prev = math.fsum(up.get(s, 0.0) * px[s] for s in three)
        if v_prev > 0 and v_now < v_prev * (1.0 - QTY_TOL):
            out.append((A, Ap))
    return out


def detect_t0(data: Data, end: str) -> dict[str, Any]:
    rep = snap_by_asof(data)
    cuts = reductions(data, rep, FIRST_SESSION, end)
    if cuts:
        A, Ap = cuts[0]
        return {"t0": A, "pre": Ap, "exact": data.prev_session(A) == Ap, "rep": rep}
    return {"t0": None, "pre": None, "exact": None, "rep": rep}


# ----------------------------------------------------------------------------- verdicts

def utility_gap(dR: float, dD: float) -> float:
    """Difference of U = R - MDD (window return minus maximum drawdown, both in account terms).

    dR = R(x) - R(y) and dD = MDD(y) - MDD(x), so dU = U(x) - U(y) = dR + dD. One percentage point of
    return counts the same as one point of drawdown (no division: Calmar flips sign when returns are
    negative - pre-registration 5-1)."""
    return dR + dD


def verdict_decision(dU: float, dR: float, b: float = BAND) -> str:
    """x = (2') E 1.55, y = (2) E 1.89. The text after the dash says which kind of win it was."""
    if dU >= b:
        if dR >= b:
            return "1.55가 나았음 — 수익이 더 높음"
        return "1.55가 나았음 — 수익은 1.0%p 이상 높지 않았고 낙폭이 더 얕음"
    if dU <= -b:
        return "1.9가 나았음 — 낙폭을 빼고도 수익이 더 큼"
    return "차이 없음"


def verdict_simple(dU: float, b: float = BAND) -> str:
    """x = (2'), y = (4). A tie goes to the simpler (4) (constitution 29)."""
    if dU >= b:
        return "구조(②′)가 단순 대안(④)보다 나았음"
    return "단순 대안(④)이 같거나 나았음 — 더 단순한 쪽 우선(헌법 §29)"


def verdict_execution(dU: float, e_actual: float | None, b: float = BAND) -> tuple[str, str]:
    """x = (1) actual, y = (2'). Returns (E line, result line)."""
    if e_actual is None:
        e_line = "실행 E 확인 불가"
    elif abs(e_actual - TARGET_155) <= EXEC_E_TOL:
        e_line = "목표 E대로 줄임"
    else:
        e_line = f"목표 E와 다름(실제 E {e_actual:.2f})"
    if dU >= b:
        r_line = "실제가 ②′보다 나았음"
    elif dU <= -b:
        r_line = "실제가 ②′보다 못했음"
    else:
        r_line = "실행 차이 작음"
    return e_line, r_line


# ----------------------------------------------------------------------------- replication

def _ref(f: Snap) -> bool:
    """A core review the replication gate compares against: usable holdings and the core's own E, N, V."""
    return (f.usable and f.status in ("VERIFIED", "UNVERIFIED")
            and None not in (f.E_core, f.N_core, f.V_core, f.window, f.minimum))


def replicate(data: Data, calc: ExposureCalc, upto: str) -> dict[str, Any]:
    refs = [f for f in data.snaps if REPL_FROM <= f.S <= upto and _ref(f)]
    worst_e = worst_n = worst_v = 0.0
    failed = []
    for f in refs:
        N, V, why = calc.parts(f.w, f.mult, f.S, int(f.window), int(f.minimum))
        if V is None:
            failed.append(f.S)
            continue
        worst_e = max(worst_e, abs(max(N, V) - float(f.E_core)))
        worst_n = max(worst_n, abs(N - float(f.N_core)))
        worst_v = max(worst_v, abs(V - float(f.V_core)))
    ok = len(refs) >= REPL_MIN and not failed and worst_e <= REPL_TOL and worst_v <= REPL_TOL
    return {"reference_sessions": len(refs), "first": refs[0].S if refs else None,
            "last": refs[-1].S if refs else None, "max_abs_E_diff": rnd(worst_e, 7),
            "max_abs_N_diff": rnd(worst_n, 7), "max_abs_V_diff": rnd(worst_v, 7),
            "v_unavailable": len(failed), "pass": ok}


# ----------------------------------------------------------------------------- one round

def split_like(r: float, strict: bool) -> bool:
    """A day's close ratio that looks like a split nobody recorded: within SPLIT_NEAR of k or 1/k (a
    1:2 split on a +3% day gives 0.515, inside the core guard). Supplement closes are raw, so there any
    day outside the core guard counts as well. A real -45% or +60% day stays a real return."""
    if not math.isfinite(r) or r <= 0:
        return True
    if any(abs(r / x - 1.0) <= SPLIT_NEAR for k in SPLIT_KS for x in (k, 1.0 / k)):
        return True
    return strict and not SPLIT_LOW < r < SPLIT_HIGH


def need_quality(data: Data, syms: list[str], pre_span: list[str],
                 win: list[str]) -> dict[str, dict[str, Any]]:
    """Per symbol, in memory only, over the closes the calculation reads: pre_span (the 252 sessions
    before T0 - the E window at T0, which must have no gap) from the symbol's first core close on, and
    win = [T0] + window sessions.
      core      a core close at or before T0 (a supplement never fills before the first core close)
      miss_pre  closes missing in pre_span            miss  window closes missing
      ends      the first or last window close is missing
      jumps     split-like day moves over both (supplement days judged strictly; a SOXL day that SOXX's
                own day explains is a crash, not a split)
      covered   a loaded supplement's dates span every close still missing - a file fetched before the
                window-end close, or starting after a gap, does not cover it
      sup       supplemented closes read"""
    bench = data.closes.get(BENCH, {})

    def jump(s: str, ser: dict[str, float], sup: set[str], a: str, b: str) -> bool:
        r = ser[b] / ser[a]
        if s == LEVER and a in bench and b in bench and math.isfinite(r):
            return abs(r - (1.0 + MULT_3X * (bench[b] / bench[a] - 1.0))) > SPLIT_MARKET_TOL
        return split_like(r, a in sup or b in sup)

    out: dict[str, dict[str, Any]] = {}
    for s in syms:
        ser = data.closes.get(s, {})
        first = min(ser) if ser else None
        sup = data.supplied.get(s, set())
        need = [t for t in pre_span if first is not None and t >= first] + list(win)
        gaps = [t for t in need if t not in ser]
        pts = [t for t in need if t in ser]
        span = data.supp_span.get(s)
        out[s] = {"core": first is not None and first <= win[0],
                  "miss_pre": sum(1 for t in gaps if t < win[0]),
                  "miss": sum(1 for t in gaps if t >= win[0]),
                  "ends": win[0] not in ser or win[-1] not in ser,
                  "jumps": sum(1 for a, b in zip(pts, pts[1:]) if jump(s, ser, sup, a, b)),
                  "sup": sum(1 for t in need if t in sup),
                  "covered": bool(gaps) and span is not None and span[0] <= gaps[0] and span[1] >= gaps[-1]}
    return out


def cap_check(data: Data, rep: dict[str, Snap], T_end: str) -> dict[str, Any]:
    """Round 2: is the actual account's 3x share <= CAP_3X at the window end (yes/no and counts only)."""
    def share(t: str) -> tuple[float, bool]:
        w, _, fresh, f = holdings_at(data, rep, t, strict=False)
        return math.fsum(v for s, v in w.items() if f.mult.get(s, 1.0) >= MULT_3X), fresh

    days = [t for t in data.cal if FIRST_SESSION <= t <= T_end]
    end_share, fresh = share(T_end)
    return {"at_window_end": "예" if end_share <= CAP_3X else "아니오", "end_holdings_fresh": fresh,
            "sessions_checked": len(days), "sessions_above": sum(1 for t in days if share(t)[0] > CAP_3X)}


def compute_round(data: Data, rnd_no: int) -> dict[str, Any]:
    T_end = ROUNDS[rnd_no]["end"]
    if max(data.cal) < T_end:
        raise Stop(f"STOP[wait]: core closes end {max(data.cal)}, before the round end {T_end} - run again after "
                   "the next core run (no amendment)")
    if T_end not in data.cal_set:
        raise Stop(f"STOP[wait]: the core closes skip the round end session {T_end} - run again once the core "
                   "has filled it (no amendment)")
    # staging gates: a copy that misses exposure reviews must stop, not turn into a final hold
    if max((f.S for f in data.snaps), default="") < (data.prev_session(T_end) or T_end):
        raise Stop("STOP[restage]: the copied exposure reviews end before the session before the round end - "
                   "copy all of them and run again (no amendment)")
    rep = snap_by_asof(data)
    if not any(a < FIRST_SESSION for a in rep):
        raise Stop(f"STOP[restage]: no usable exposure review holds holdings dated before {FIRST_SESSION} - "
                   "copy all of them and run again (no amendment)")
    if sum(1 for f in data.snaps if REPL_FROM <= f.S < FIRST_SESSION and _ref(f)) < REPL_MIN:
        raise Stop(f"STOP[restage]: fewer than {REPL_MIN} reference exposure reviews from {REPL_FROM} - copy all "
                   "of them and run again (no amendment)")
    calc = ExposureCalc(data)
    out: dict[str, Any] = {"round": rnd_no, "window_end": T_end, "first_session": FIRST_SESSION,
                           "band": BAND}

    def hold(reason: str) -> dict[str, Any]:
        out["verdicts"] = {k: f"판정 보류({reason})" for k in ("decision", "simple", "execution")}
        return out

    if rnd_no == 2:                      # independent of T0: written even when the round is on hold
        out["cap_3x"] = cap_check(data, rep, T_end)
    det = detect_t0(data, T_end)
    if det["t0"] is None:
        out["replication"] = replicate(data, calc, T_end)
        return hold("줄이기 체결 없음")
    T0, pre = det["t0"], det["pre"]
    sessions = data.sessions_between(T0, T_end)
    win = [T0] + sessions
    i0 = data.cal.index(T0)
    pre_span = data.cal[max(0, i0 - WINDOW):i0]     # the 252 sessions before T0: the E window at T0
    out["window"] = {"t0": T0, "pre_snapshot": pre, "t0_exact": det["exact"],
                     "earliest_trade_session": data.next_session(pre), "sessions": len(sessions)}
    repl = replicate(data, calc, T0)
    out["replication"] = repl
    if not repl["pass"]:
        return hold("E 재현 실패")
    if len(sessions) < MIN_SESSIONS:
        return hold(f"창 {MIN_SESSIONS}거래일 미만")
    f_pre, f_t0 = rep[pre], rep[T0]
    mult_h = dict(f_pre.mult)            # the hypothetical accounts keep the pre-trade multipliers
    # closes the hypothetical accounts (2), (2') and the baseline (4) need, before T0 and in the window
    need_dec = sorted(set(f_pre.w) | {BENCH})
    q = need_quality(data, sorted(set(need_dec) | {LEVER}), pre_span, win)
    allow = int(GAP_SHARE * len(win))

    def bad(x: dict[str, Any]) -> bool:
        return x["miss_pre"] > 0 or x["ends"] or x["miss"] > allow

    out["need_closes"] = {
        "symbols": len(need_dec), "window_closes": len(win), "allowed_missing_per_symbol": allow,
        "missing": sum(q[s]["miss"] for s in need_dec),
        "missing_before_t0": sum(q[s]["miss_pre"] for s in need_dec),
        "symbols_missing_first_or_last": sum(q[s]["ends"] for s in need_dec),
        "symbols_without_core_history_to_t0": sum(not q[s]["core"] for s in need_dec),
        "split_like_moves": sum(q[s]["jumps"] for s in need_dec),
        "supplemented": sum(q[s]["sup"] for s in need_dec),
        "simple_baseline": {"core_history_to_t0": q[LEVER]["core"], "missing": q[LEVER]["miss"],
                            "missing_before_t0": q[LEVER]["miss_pre"],
                            "split_like_moves": q[LEVER]["jumps"], "supplemented": q[LEVER]["sup"]}}
    if any(not q[s]["core"] for s in need_dec):
        return hold("가상 계좌 종목에 T0까지 코어 종가 이력이 없음")
    if any(q[s]["core"] and bad(q[s]) and not q[s]["covered"] for s in q):
        raise Stop(f"STOP[restage]: a symbol the calculation needs lacks closes in the window or in the {WINDOW} "
                   "sessions before T0 - fetch its Nasdaq supplement after the window-end close (--check lists "
                   "it; a file fetched before then must be fetched again) and run again (no amendment)")
    if any(bad(q[s]) for s in need_dec):
        return hold("공개 종가로 채워도 빠진 종가가 남음")
    jumps = sum(q[s]["jumps"] for s in need_dec)
    if jumps:
        raise Stop(f"STOP[wait]: {jumps} split-like day move(s) on symbols the hypothetical accounts hold - wait "
                   "for the core to record the split (corporate-actions.json), copy it and run again "
                   "(no amendment)")
    simple_block = None
    if not q[LEVER]["core"]:
        simple_block = "④의 SOXL 코어 종가 이력 없음"
    elif bad(q[LEVER]):
        simple_block = "④의 SOXL 종가가 빠짐"
    elif q[LEVER]["jumps"]:
        simple_block = f"④의 SOXL에 분할로 보이는 하루 움직임 {q[LEVER]['jumps']}건"
    w_pre, c_pre = reprice_pre(data, f_pre, T0)
    e_pre = calc.E(w_pre, mult_h, T0, WINDOW, MINIMUM)
    if e_pre is None:
        return hold("실행 직전 계좌 E 계산 불가")
    out["exposure"] = {"E_pre_t0": rnd(e_pre, 4)}
    if e_pre <= TARGET_155:
        return hold("줄이기 직전 E가 이미 1.55 이하 — 두 가상 계좌가 같음")
    unit = calc.window([LEVER], T0, WINDOW, MINIMUM)
    if simple_block is None and not unit.ok:
        simple_block = "④의 SOXL 변동성 계산 불가"
    w19, c19, e19, un19 = scale_3x(calc, w_pre, c_pre, mult_h, T0, WINDOW, MINIMUM, TARGET_19)
    w155, c155, e155, un155 = scale_3x(calc, w_pre, c_pre, mult_h, T0, WINDOW, MINIMUM, TARGET_155)

    def hold_path(w: dict[str, float], c: float) -> list[float]:
        base = {s: data.price(s, T0) for s in w}
        return [1.0] + [c + math.fsum(v * data.price(s, t) / base[s] for s, v in w.items()) for t in sessions]

    p19, p155 = hold_path(w19, c19), hold_path(w155, c155)
    # (1) actual: weights at each close from the latest holdings known then; a missing close is
    #     carried (or, with no close at all, that position counts flat) and the session is approximate
    w_a, _, fresh_a, f_a = holdings_at(data, rep, T0, strict=False)
    e_actual = calc.E(w_a, f_a.mult, T0, WINDOW, MINIMUM)
    p1, approx, miss1 = [1.0], 0, 0
    prev_t, w_prev, fresh_prev = T0, w_a, fresh_a
    for t in sessions:
        r, gap = 0.0, False
        for s, v in w_prev.items():
            ser = data.closes.get(s, {})
            if prev_t in ser and t in ser:
                r += v * (ser[t] / ser[prev_t] - 1.0)
                continue
            gap = True
            miss1 += 1
            a_, b_ = data.price(s, prev_t, False, False), data.price(s, t, False, False)
            if a_ and b_:
                r += v * (b_ / a_ - 1.0)
        p1.append(p1[-1] * (1.0 + r))
        approx += (not fresh_prev) or gap
        w_prev, _, fresh_prev, _ = holdings_at(data, rep, t, strict=False)
        prev_t = t
    # (4) simple baseline: SOXL/cash, rebalanced every session at the window-average E of (2')
    e_missing, e_mean, k_lev, w4, p4 = 0, None, None, None, None
    if simple_block is None:
        e_path = []
        for t in win:
            wt, _ = reprice(data, w155, c155, T0, t, count=False)
            e = calc.E(wt, mult_h, t, WINDOW, MINIMUM)
            if e is None:
                e_missing += 1
            else:
                e_path.append(e)
        if not e_path:
            simple_block = "②′ E를 창에서 못 구함"
        else:
            e_mean = math.fsum(e_path) / len(e_path)
            k_lev = max(MULT_3X, unit.V({LEVER: 1.0}))
            w4 = min(1.0, e_mean / k_lev)
            p4 = [1.0]
            for a_, b_ in zip(win, sessions):
                p4.append(p4[-1] * (1.0 + w4 * (data.price(LEVER, b_) / data.price(LEVER, a_) - 1.0)))
    pb = [1.0] + [data.price(BENCH, t) / data.price(BENCH, T0) for t in sessions]
    paths = {"actual": p1, "b19": p19, "b155": p155, "cash": [1.0] * len(win), "soxx": pb}
    if p4 is not None:
        paths["simple"] = p4
    R = {k_: v[-1] - 1.0 for k_, v in paths.items()}
    D = {k_: mdd(v) for k_, v in paths.items()}
    if not all(math.isfinite(x) for x in [*R.values(), *D.values()]):
        raise Stop("STOP[amend]: a non-finite return or drawdown")
    pairs = {"decision": ("b155", "b19"), "simple": ("b155", "simple"), "execution": ("actual", "b155")}
    deltas = {n: (R[x] - R[y], D[y] - D[x]) for n, (x, y) in pairs.items() if x in R and y in R}
    dU = {n: utility_gap(dr, dd) for n, (dr, dd) in deltas.items()}
    approx_share = approx / len(sessions)
    held = set(w_pre) | {s for f in data.snaps if f.usable and T0 <= f.S <= T_end for s in f.w}
    used = sorted(held | {BENCH, LEVER})
    unverified = sum(1 for t in win if any(t in data.unverified.get(s, set()) for s in used))
    supp = sum(1 for t in pre_span + win for s in used if t in data.supplied.get(s, set()))
    big_moves = 0
    for s in used:
        ser = data.closes.get(s, {})
        pts = [t for t in win if t in ser]
        big_moves += sum(1 for a_, b_ in zip(pts, pts[1:]) if abs(ser[b_] / ser[a_] - 1.0) > BIG_MOVE)
    t5 = sessions[min(4, len(sessions) - 1)]
    w_5, _, _, f_5 = holdings_at(data, rep, t5, strict=False)
    e_actual5 = calc.E(w_5, f_5.mult, t5, WINDOW, MINIMUM)
    later_cuts = len(reductions(data, rep, data.next_session(T0), t5))
    filled_h = out["need_closes"]["missing"] + (q[LEVER]["miss"] if p4 is not None else 0)
    cav = []
    if not det["exact"]:
        cav.append("실행일 근사 — 줄이기 직전 보유 스냅샷이 바로 앞 세션이 아님")
    if (f_pre.window, f_pre.minimum) != (WINDOW, MINIMUM):
        cav.append("코어 창 설정이 252/60이 아님 — 가상 계좌는 고정한 252/60으로 계산")
    if approx:
        cav.append(f"① 근사 세션 {approx}/{len(sessions)} — 그날 보유 스냅샷이 없거나 종가가 빠져 앞 값으로 계산")
    if miss1:
        cav.append(f"① 빠진 종가 {miss1}건 — 앞 종가로 계산")
    if later_cuts:
        cav.append(f"실행일 뒤 5세션 안에 3배를 더 줄임 {later_cuts}번 — 5세션 뒤 실제 E도 함께 봄")
    if unverified:
        cav.append(f"종가 미검증 세션 {unverified}/{len(win)}")
    if supp:
        cav.append(f"공개 종가로 채운 종가 {supp}건 — 코어 종가가 끊긴 종목")
    if filled_h:
        cav.append(f"가상 계좌·④의 빠진 종가 {filled_h}건 — 앞 종가로 채움(종목마다 {allow}건까지)")
    if big_moves:
        cav.append(f"하루 25% 넘는 움직임 {big_moves}건 — 분할이 아닌 실제 움직임으로 계산함")
    if e_pre <= TARGET_19:
        cav.append("줄이기 직전 E가 이미 1.89 이하 — ②는 3배를 줄이지 않은 계좌")
    if un19 or un155:
        cav.append("가상 계좌 목표 E에 못 닿음 — 3배를 다 빼도 E가 목표보다 높음")
    if e_missing:
        cav.append(f"②′ E를 못 구한 세션 {e_missing}/{len(win)} — 나머지 세션 평균으로 ④를 맞춤")
    e_line, r_line = verdict_execution(dU["execution"], e_actual)
    execution = (f"{e_line} · {r_line}" if approx_share <= APPROX_MAX
                 else f"판정 보류(① 근사 세션 {approx}/{len(sessions)} > {int(APPROX_MAX * 100)}%) · {e_line}")
    out["exposure"] = {"E_pre_t0": rnd(e_pre, 4), "E_b19_t0": rnd(e19, 4), "E_b155_t0": rnd(e155, 4),
                       "b155_target_unreached": un155, "b19_target_unreached": un19,
                       "E_actual_t0_calc": rnd(e_actual, 4), "E_actual_t5_calc": rnd(e_actual5, 4),
                       "later_cuts_5_sessions": later_cuts,
                       "E_actual_t0_core": rnd(f_t0.E_core, 4) if f_t0.S == T0 else None,
                       "E_b155_window_mean": rnd(e_mean, 4), "E_b155_days_unavailable": e_missing,
                       "E_simple": rnd(w4 * k_lev, 4) if w4 is not None else None}
    out["paths"] = {k_: {"R_pct": rnd(R[k_] * 100, 3), "MDD_pct": rnd(D[k_] * 100, 3)} for k_ in paths}
    out["deltas_pctp"] = {n: {"dR": rnd(dr * 100, 3), "dD": rnd(dd * 100, 3), "dU": rnd(dU[n] * 100, 3)}
                          for n, (dr, dd) in deltas.items()}
    out["data_quality"] = {"actual_approx_sessions": approx, "actual_approx_share": rnd(approx_share, 4),
                           "actual_missing_close_returns": miss1, "unverified_close_sessions": unverified,
                           "supplemented_closes_used": supp, "big_daily_moves": big_moves}
    out["verdicts"] = {"decision": verdict_decision(dU["decision"], deltas["decision"][0]),
                       "simple": (verdict_simple(dU["simple"]) if "simple" in dU
                                  else f"판정 보류({simple_block})"),
                       "execution": execution}
    # pre-mortem / pre-celebration signals (strategy-revision 184-185), report only
    win_snaps = [f for f in data.snaps if T0 <= f.S <= T_end]
    l4_hit = any(f.l4 for f in win_snaps if f.l4 is not None)
    l4_eval = sum(1 for f in win_snaps if f.lines_status == "EVALUATED" and f.l4 is not None)
    core_e = sorted(float(f.E_core) for f in win_snaps
                    if f.A == f.S and f.status in ("VERIFIED", "UNVERIFIED") and f.E_core is not None)
    med = None
    if core_e:
        n_ = len(core_e)
        med = core_e[n_ // 2] if n_ % 2 else (core_e[n_ // 2 - 1] + core_e[n_ // 2]) / 2
    if R["soxx"] <= 0:
        sig_d = "해당 없음(SOXX 창 수익 0 이하)"
    elif len(core_e) < 0.5 * len(win):
        sig_d = "계산 불가(코어 E 있는 세션 절반 미만)"
    else:
        sig_d = "예" if R["actual"] > 0 and med <= TARGET_155 + EXEC_E_TOL else "아니오"
    sig = {"premortem_a_1_9_better": "예" if out["verdicts"]["decision"].startswith("1.9가 나았음") else "아니오",
           "premortem_b_public_closes_used": "예" if supp else "아니오",
           "precelebration_c_no_L4": ("아니오" if l4_hit else
                                      "예" if l4_eval >= 0.8 * len(win) else
                                      "계산 불가(L선 평가 세션 80% 미만)"),
           "precelebration_d_rally_at_E_1_60": sig_d,
           "core_E_window_median": rnd(med, 4), "core_E_sessions": len(core_e),
           "L_lines_evaluated_sessions": l4_eval}
    if rnd_no == 2:
        sig["premortem_e_3x_above_10"] = "예" if out["cap_3x"]["at_window_end"] == "아니오" else "아니오"
    out["signals"] = sig
    out["caveats"] = cav
    return out


# ----------------------------------------------------------------------------- contract and run

def _norm(raw: bytes) -> bytes:
    """Text as UTF-8 with LF line ends: a UTF-8 BOM is dropped and UTF-16 with a BOM is decoded, so a
    Windows editor re-save or a git autocrlf checkout does not change a hash."""
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        raw = raw.decode("utf-16").encode("utf-8")
    elif raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    return raw.replace(b"\r\n", b"\n")


def _split_doc(doc: bytes) -> tuple[bytes, list[str]]:
    """(body above the marker line, the lines below it). The marker must be a whole line, exactly once."""
    lines = _norm(doc).split(b"\n")
    hits = [i for i, ln in enumerate(lines) if ln.rstrip() == MARK.encode("utf-8")]
    if len(hits) != 1:
        raise Stop("STOP[restage]: the pre-registration must hold its marker line exactly once - restore the "
                   "fixed version from git")
    i = hits[0]
    return b"".join(ln + b"\n" for ln in lines[:i]), [ln.decode("utf-8", "replace") for ln in lines[i + 1:]]


def body_hash(doc: bytes) -> str:
    """sha256 of the normalised pre-registration above (not including) the marker line."""
    return sha256_bytes(_split_doc(doc)[0])


def runner_hash(path: Path) -> str:
    return sha256_bytes(_norm(path.read_bytes()))


def check_contract(root: Path) -> dict[str, Any]:
    doc_p, side_p = root / PREREG, root / SIDECAR
    if not doc_p.is_file() or not side_p.is_file():
        raise Stop("STOP[restage]: the pre-registration or its .sha256 sidecar is missing (not fixed) - copy both")
    lines = _norm(side_p.read_bytes()).decode("utf-8", "replace").splitlines()
    pairs = [(p[0], p[1]) for p in (ln.split() for ln in lines) if len(p) >= 2]
    keys = [k for k, _ in pairs]
    for key in ("body_sha256", "runner_sha256", "fixed_at"):
        if keys.count(key) != 1:
            raise Stop(f"STOP[restage]: the sidecar must hold exactly one {key}")
    field = dict(pairs)
    body = body_hash(doc_p.read_bytes())
    if field["body_sha256"] != body:
        raise Stop("STOP[restage]: the pre-registration changed above the marker after fixation (body_sha256 "
                   "mismatch) - restore the fixed version from git")
    runner = runner_hash(Path(__file__).resolve())
    if field["runner_sha256"] != runner:
        raise Stop("STOP[restage]: the calc file changed after fixation (runner_sha256 mismatch) - restore the "
                   "fixed version from git")
    amended = [v for k, v in pairs if k == "amended_at"]
    try:
        times = [datetime.fromisoformat(t) for t in [field["fixed_at"], *amended]]
    except ValueError:
        raise Stop("STOP[restage]: sidecar times must be ISO 8601 with a UTC offset") from None
    if any(t.tzinfo is None for t in times):
        raise Stop("STOP[restage]: sidecar times need a UTC offset")
    if any(t <= times[0] for t in times[1:]):
        raise Stop("STOP[restage]: an amendment must come after the original lock")
    return {"body_sha256": body, "runner_sha256": runner, "fixed_at": field["fixed_at"], "amended_at": amended}


def inputs_digest(data: Data) -> dict[str, Any]:
    lines = sorted(f"{sha} {rel}" for rel, sha in data.inputs)
    return {"files": len(lines), "sha256_of_sorted_list": sha256_bytes("\n".join(lines).encode())}


MANUAL_HOLD = "판정 보류(멈춤:"   # section 7 ⑤: a round closed by hand after seven days of stops


def round_guard(root: Path, rnd_no: int) -> dict[str, Any]:
    """Section 11 holds exactly one '- 1차:' and one '- 2차:' line, and this round's line must still be its
    placeholder (one run per round). Round 2 needs round 1 resolved first: its line closed by hand
    (section 7 ⑤ - round 1 counts as not run) or replaced by its result line, whose results file must be
    in the run folder with the first 8 characters of its sha256 (UTF-8/LF) in that line (section 9)."""
    _, tail = _split_doc((root / PREREG).read_bytes())
    lines = {n: [ln.rstrip() for ln in tail if ln.startswith(f"- {n}차:")] for n in (1, 2)}
    if len(lines[1]) != 1 or len(lines[2]) != 1:
        raise Stop("STOP[restage]: section 11 must hold exactly one '- 1차:' line and one '- 2차:' line")
    if lines[rnd_no][0] != PLACEHOLDER[rnd_no]:
        raise Stop(f"STOP[done]: section 11 no longer shows the round {rnd_no} placeholder line (already run or "
                   "closed by hand)")
    if rnd_no == 1:
        return {}
    first = lines[1][0]
    r1 = root / RESULTS[1]
    if first == PLACEHOLDER[1]:
        raise Stop("STOP[wait]: round 1 is not resolved - run round 1 first and copy its result line into "
                   "section 11 (or close it by hand, pre-registration 7)")
    if first.startswith("- 1차: " + MANUAL_HOLD):
        if r1.exists():
            raise Stop("STOP[restage]: round 1 results exist but section 11 says round 1 was stopped by hand - "
                       "copy round 1's result line (with its sha256 prefix) instead")
        return {"run": False}
    if not r1.is_file():
        raise Stop("STOP[restage]: section 11 shows a round 1 result - copy the round 1 results file into the "
                   "run folder and run again")
    sha = sha256_bytes(_norm(r1.read_bytes()))
    if sha[:8] not in first:
        raise Stop("STOP[restage]: the round 1 results file does not match the sha256 prefix in section 11")
    j = _read_json(r1, "round 1 results")
    t1 = ((j.get("window") or {}).get("t0")) if isinstance(j, dict) else None
    return {"run": True, "sha256": sha, "t0": t1}


def run_round(root: Path, rnd_no: int, now: datetime | None = None) -> dict[str, Any]:
    contract = check_contract(root)
    now = (now or datetime.now(KST)).astimezone(KST)
    judge = datetime.fromisoformat(ROUNDS[rnd_no]["judge_kst"] + "T00:00:00+09:00")
    if now < judge:
        raise Stop(f"STOP[wait]: round {rnd_no} may run from {ROUNDS[rnd_no]['judge_kst']} KST")
    out_path = root / RESULTS[rnd_no]
    if out_path.exists():
        raise Stop(f"STOP[done]: {RESULTS[rnd_no]} exists (one run per round, never overwritten)")
    link = round_guard(root, rnd_no)
    data = Data(root)
    result = compute_round(data, rnd_no)
    if rnd_no == 2:
        if link["run"]:
            link["t0_same"] = link["t0"] == (result.get("window") or {}).get("t0")
        result["round1"] = link
    earliest = (result.get("window") or {}).get("earliest_trade_session")
    fixed_day = datetime.fromisoformat(contract["fixed_at"]).astimezone(KST).date().isoformat()
    result["post_hoc_possible"] = bool(earliest and earliest <= fixed_day)
    if result["post_hoc_possible"]:
        result.setdefault("caveats", []).append(
            "줄이기가 고정한 날이나 그 전에 체결됐을 수 있음 — 체결이 고정 시각보다 먼저였다면 이 차수는 사후 등록")
    result["contract"] = contract
    result["inputs"] = inputs_digest(data)
    result["run_at_kst"] = now.isoformat(timespec="seconds")
    result["schema"] = "strategy1101-score-2"
    privacy_check(result)
    text = json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True, allow_nan=False) + "\n"
    with open(out_path, "x", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return result


def run_check(root: Path) -> dict[str, Any]:
    """Console only - never save this output under docs/claude: fetch_supplement_for names symbols."""
    data = Data(root)
    calc = ExposureCalc(data)
    last = max(data.cal)
    det = detect_t0(data, last)
    try:
        contract = check_contract(root)
    except Stop as exc:
        contract = {"status": f"not fixed or mismatch: {exc}"}
    rep = det["rep"]
    base = rep[det["pre"]] if det["pre"] else (rep[max(rep)] if rep else None)
    need = sorted((set(base.w) if base else set()) | {BENCH, LEVER})
    n_before = sum(1 for t in data.cal if base is not None and t < base.A)
    span = data.cal[max(0, n_before - WINDOW):] if base is not None else []
    fetch, remain = [], 0
    for s in need:           # gaps from the symbol's first core close on (a supplement cannot fill before)
        ser = data.closes.get(s)
        if not ser:
            continue
        gaps = [t for t in span if t >= min(ser) and t not in ser]
        if not gaps:
            continue
        sp = data.supp_span.get(s)
        if sp is not None and sp[0] <= gaps[0] and sp[1] >= gaps[-1]:
            remain += 1      # a supplement spans them and still lacks them: the run decides (hold or not)
        else:
            fetch.append(s)
    refs = [f for f in data.snaps if f.S >= REPL_FROM and f.usable]
    out = {"contract": contract, "inputs": inputs_digest(data), "closes_last_session": last,
           "reviews_last_session": max((f.S for f in data.snaps), default=None),
           "snapshots": len(data.snaps), "usable_snapshots": sum(f.usable for f in data.snaps),
           "reference_reviews_before_first_session": sum(1 for f in data.snaps
                                                         if REPL_FROM <= f.S < FIRST_SESSION and _ref(f)),
           "replication": replicate(data, calc, det["t0"] or last),
           "core_windows": sorted({f"{f.window}/{f.minimum}" for f in refs}),
           "t0": det["t0"], "pre_snapshot": det["pre"], "t0_exact": det["exact"],
           "earliest_trade_session": data.next_session(det["pre"]) if det["pre"] else None,
           # symbols the hypothetical accounts or (4) need that miss a close (from their first core close
           # on) in the 252 sessions before the base holdings date or after it -> save their Nasdaq
           # historical JSON under SUPP_DIR after the window-end close, run again
           "fetch_supplement_for": fetch,
           "symbols_a_supplement_spans_but_cannot_fill": remain,
           "need_symbols_without_core_history": sum(1 for s in need if s not in data.closes),
           "supplemented_symbols": len(data.supplied), "supplement_files_ignored": data.supp_ignored}
    privacy_check(out)
    return out


FORBIDDEN_KEYS = ("weight", "qty", "quantity", "equity", "usd", "amount", "units", "position", "cash_w")


def privacy_check(obj: Any, path: str = "") -> None:
    """Results may hold only ratios, E values, counts, dates, hashes and verdict text."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if any(bad in str(k).lower() for bad in FORBIDDEN_KEYS):
                raise Stop(f"STOP[amend]: forbidden output key {path}/{k}")
            privacy_check(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for v in obj:
            privacy_check(v, path)


# ----------------------------------------------------------------------------- self-test

def _write_fixture(root: Path, prices: dict[str, list[float]], sessions: list[str],
                   snaps: list[dict[str, Any]], splits: list[dict[str, Any]] | None = None) -> None:
    hist = root / HIST_DIR
    hist.mkdir(parents=True, exist_ok=True)
    for sym, vals in prices.items():
        hist.joinpath(f"{sym}.close-history.json").write_text(json.dumps({
            "symbol": sym, "sessions": [{"session_date": s, "close": f"{v:.6f}", "verified": True}
                                        for s, v in zip(sessions, vals) if v is not None]}), encoding="utf-8")
    (root / CORP).write_text(json.dumps({"actions": splits or []}), encoding="utf-8")
    for i, sn in enumerate(snaps):
        d = root / "workspace/outputs/exposure-review" / sn["S"]
        d.mkdir(parents=True, exist_ok=True)
        d.joinpath(f"portfolio-exposure-review.{sn['S'].replace('-', '')}T21{i:04d}Z.json").write_text(
            json.dumps(sn["raw"]), encoding="utf-8")


def _snap_raw(S: str, A: str, units: dict[str, float], cash: float, px: dict[str, float],
              mult: dict[str, float], E: float | None = None, N: float | None = None,
              V: float | None = None, status: str = "VERIFIED") -> dict[str, Any]:
    vals = {s: u * px[s] for s, u in units.items()}
    eq = math.fsum(vals.values()) + cash
    return {"evaluation_session": S, "snapshot": {"as_of": A},
            "equity": {"status": "AVAILABLE", "closing_equity_usd": f"{eq:.6f}", "cash_weight": cash / eq},
            "positions": [{"symbol": s, "nominal_multiplier": mult[s], "close": f"{px[s]:.6f}",
                           "weight": vals[s] / eq} for s in units],
            "exposure": {"status": status, "effective": E, "nominal": N, "sox_equivalent": V,
                         "window_sessions": 252, "minimum_sessions": 60}}


def _fill_e(root: Path) -> None:
    """Write the replica's E/N/V into the fixture's exposure files, as the core would."""
    data = Data(root)
    calc = ExposureCalc(data)
    for sn in data.snaps:
        p = root / sn.rel
        raw = json.loads(p.read_text(encoding="utf-8"))
        N, V, _ = calc.parts(sn.w, sn.mult, sn.S, 252, 60)
        raw["exposure"].update({"effective": None if V is None else max(N, V), "nominal": N,
                                "sox_equivalent": V})
        p.write_text(json.dumps(raw), encoding="utf-8")


def _expect_stop(fn: Any, text: str) -> None:
    try:
        fn()
    except Stop as exc:
        msg = str(exc)
        assert msg.startswith(("STOP[wait]: ", "STOP[restage]: ", "STOP[amend]: ", "STOP[done]: ")), msg
        assert text in msg, (text, msg)
        return
    raise AssertionError(f"no stop: {text}")


def self_test() -> None:
    rng = random.Random(20261102)

    def weekdays(a: date, b: date) -> list[str]:
        out, d = [], a
        while d <= b:
            if d.weekday() < 5:
                out.append(d.isoformat())
            d += timedelta(days=1)
        return out

    sessions = weekdays(date(2026, 4, 1), date(2027, 1, 15))
    mult = {"AAA": 1.0, "BBB": 1.0, "CCC": 1.0, LEVER: 3.0, BENCH: 1.0, "TQQ": 3.0}

    def gen(drift: float = 0.0, sess: list[str] | None = None,
            g: random.Random | None = None) -> dict[str, list[float]]:
        sess, g = sess or sessions, g or rng
        px = {s: [100.0] for s in ("AAA", "BBB", LEVER, BENCH)}
        for i in range(1, len(sess)):
            m = g.gauss(0, 0.018) + (drift if sess[i] >= "2026-11-03" else 0.0)
            px[BENCH].append(px[BENCH][-1] * (1 + m))
            px[LEVER].append(px[LEVER][-1] * (1 + 3 * m))
            px["AAA"].append(px["AAA"][-1] * (1 + 0.7 * m + g.gauss(0, 0.02)))
            px["BBB"].append(px["BBB"][-1] * (1 + 0.6 * m + g.gauss(0, 0.02)))
        return px

    def account(root: Path, px: dict[str, list[float]], core_px: dict[str, list[float]], three: float = 62000.0,
                sell: float = 0.4, sell_all: bool = False, sell_aaa: bool = False, deposit: bool = False,
                stale: tuple[str, ...] = (), sess: list[str] | None = None, snap_to: str = "2026-12-31",
                lev: str = LEVER, buy_ccc: bool = False, splits: list[dict[str, Any]] | None = None) -> Data:
        """Holdings sized at the 11/03 closes (3x 62%, 1x 25%, cash 8% by default); a 3x sale on 11/04."""
        sess = sess or sessions
        at = {k_: dict(zip(sess, v)) for k_, v in px.items()}
        ref = "2026-11-03"
        units = {"AAA": 15000.0 / at["AAA"][ref], "BBB": 10000.0 / at["BBB"][ref], lev: three / at[lev][ref]}
        snaps = []
        for s_ in sess:
            if s_ < "2026-10-13" or s_ > snap_to:
                continue
            u, c = dict(units), 8000.0
            if deposit and s_ >= "2026-11-02":     # a deposit: cash up, no sale -> not a reduction
                c += 5000.0
            if buy_ccc and s_ >= ref:               # a 1x symbol bought with cash on the pre-trade date
                u["CCC"] = 4000.0 / at["CCC"][ref]
                c -= 4000.0
            if s_ >= "2026-11-04":
                if sell_all:
                    c += math.fsum(u[k_] * at[k_]["2026-11-04"] for k_ in u)
                    u = {}
                else:
                    c += u[lev] * sell * at[lev]["2026-11-04"]
                    u[lev] *= 1.0 - sell
            if sell_aaa and s_ > "2026-11-20":
                c += u.pop("AAA") * at["AAA"]["2026-11-20"]
            A = "2026-11-05" if s_ in stale else s_
            snaps.append({"S": s_, "raw": _snap_raw(s_, A, u, c, {k_: at[k_][s_] for k_ in u}, mult)})
        _write_fixture(root, core_px, sess, snaps, splits)
        _fill_e(root)
        return Data(root)

    def nasdaq(root: Path, sym: str, vals: list[float], scale: float = 1.0, frm: str = "2026-09-01",
               upto: str = "9999-12-31", sess: list[str] | None = None) -> None:
        d_ = root / SUPP_DIR
        d_.mkdir(parents=True, exist_ok=True)
        rows = [{"date": f"{t[5:7]}/{t[8:10]}/{t[0:4]}", "close": f"${v * scale:,.2f}"}
                for t, v in zip(sess or sessions, vals) if frm <= t <= upto]
        d_.joinpath(f"{sym}.nasdaq-historical.json").write_text(
            json.dumps({"data": {"tradesTable": {"rows": rows[::-1]}}}), encoding="utf-8")

    def contract(root: Path) -> tuple[str, str]:
        """A pre-registration with the two section 11 lines and a matching sidecar: (doc, body hash)."""
        (root / "docs/claude").mkdir(parents=True, exist_ok=True)
        head = "# 사전 등록\n\n본문\n"
        doc = head + MARK + "\n## 11. 결과\n\n" + PLACEHOLDER[1] + "\n" + PLACEHOLDER[2] + "\n"
        good = sha256_bytes(head.encode("utf-8"))
        (root / SIDECAR).write_text(f"body_sha256 {good}\nrunner_sha256 {runner_hash(Path(__file__).resolve())}\n"
                                    "fixed_at 2026-11-02T12:00:00+09:00 (KST)\n", encoding="utf-8")
        (root / PREREG).write_bytes(doc.encode("utf-8"))
        return doc, good

    # 1 core replica: V equals a direct computation, N linear
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        px = gen()
        _write_fixture(root, px, sessions, [])
        data = Data(root)
        calc = ExposureCalc(data)
        end = "2026-10-30"
        w = {"AAA": 0.3, "BBB": 0.2, LEVER: 0.25}
        N, V, why = calc.parts(w, mult, end, 252, 60)
        idx = sessions.index(end)
        win = sessions[:idx + 1][-253:]
        q = {s: [float(f"{v:.6f}") for v in vals] for s, vals in px.items()}
        r = {s: [q[s][sessions.index(win[i])] / q[s][sessions.index(win[i - 1])] - 1
                 for i in range(1, len(win))] for s in px}
        port = [sum(w[s] * r[s][i] for s in w) for i in range(len(win) - 1)]
        assert why is None and abs(N - (0.3 + 0.2 + 0.75)) < 1e-12
        assert abs(V - sstd(port) / sstd(r[BENCH])) < 1e-12
        # 2 solver: largest scale with E <= target; unreachable -> 0; already below -> 1
        ww, cc, e, un = scale_3x(calc, w, 0.25, mult, end, 252, 60, 1.0)
        assert e <= 1.0 + 1e-12 and not un
        lam = ww.get(LEVER, 0.0) / 0.25
        bigger = dict(w)
        bigger[LEVER] = 0.25 * min(1.0, lam + 2e-3)
        assert calc.E(bigger, mult, end, 252, 60) > 1.0
        assert abs(sum(ww.values()) + cc - 1.0) < 1e-12
        ww0, cc0, e0, un0 = scale_3x(calc, w, 0.25, mult, end, 252, 60, 0.1)
        assert un0 and LEVER not in ww0 and abs(cc0 - 0.5) < 1e-12
        ww1, cc1, e1, un1 = scale_3x(calc, w, 0.25, mult, end, 252, 60, 5.0)
        assert not un1 and ww1 == w and cc1 == 0.25
        # an all-cash account: N = V = 0
        assert calc.E({}, {}, end, 252, 60) == 0.0
    # 3 drawdown by hand
    assert abs(mdd([1.0, 1.1, 0.99, 1.2, 0.9, 1.0]) - 0.25) < 1e-12 and mdd([1.0, 1.2, 1.3]) == 0.0
    # 4 verdict tables (band 1.0 %p): U = R - MDD, dU = dR + dD
    b = BAND
    W1, W2, W3, TIE = ("1.55가 나았음 — 수익이 더 높음",
                       "1.55가 나았음 — 수익은 1.0%p 이상 높지 않았고 낙폭이 더 얕음",
                       "1.9가 나았음 — 낙폭을 빼고도 수익이 더 큼", "차이 없음")
    assert abs(utility_gap(0.02, -0.005) - 0.015) < 1e-12 and abs(utility_gap(-0.03, 0.01) + 0.02) < 1e-12
    assert verdict_decision(b, b) == W1 and verdict_decision(b, 0.0) == W2 and verdict_decision(-b, 0.0) == W3
    assert verdict_decision(0.999 * b, 0.5 * b) == TIE and verdict_decision(-0.999 * b, -b) == TIE
    # a falling market: 1.55 lost 3.4 %p less and fell 7.6 %p less (Calmar would have said 1.9)
    assert verdict_decision(utility_gap(0.034, 0.076), 0.034) == W1
    # a rally with a small dip: gave up 24 %p of return for 2.8 %p less drawdown -> 1.9
    assert verdict_decision(utility_gap(-0.24, 0.028), -0.24) == W3
    # a trade-off: 0.4 %p less return for 2 %p less drawdown -> 1.55, the second label
    assert verdict_decision(utility_gap(-0.004, 0.02), -0.004) == W2
    # 0.5 %p more return (inside the band) and 1 %p less drawdown -> the second label too
    assert verdict_decision(utility_gap(0.005, 0.01), 0.005) == W2
    assert verdict_simple(b).startswith("구조") and verdict_simple(0.999 * b).startswith("단순")
    assert verdict_simple(-5 * b).startswith("단순")
    assert verdict_execution(0.0, 1.57) == ("목표 E대로 줄임", "실행 차이 작음")
    assert verdict_execution(-b, 1.70) == ("목표 E와 다름(실제 E 1.70)", "실제가 ②′보다 못했음")
    assert verdict_execution(b, None) == ("실행 E 확인 불가", "실제가 ②′보다 나았음")
    # split-like day moves: core closes need a split ratio, supplement closes any guard break
    assert split_like(1 / 3, False) and split_like(10.2, False) and split_like(0.49, False)
    assert split_like(0.515, False) and split_like(2.06, False)
    assert not split_like(0.45, False) and not split_like(1.8, False) and not split_like(2.6, False)
    assert split_like(0.45, True) and not split_like(0.9, True) and split_like(float("nan"), False)
    # 5 end-to-end: T0 detection, a deposit, stale snapshots, both outcomes
    for drift, expect in ((-0.012, "1.55가 나았음"), (+0.012, "1.9가 나았음")):
        with tempfile.TemporaryDirectory() as tmp:
            px = gen(drift)
            data = account(Path(tmp), px, px, deposit=True, stale=("2026-11-06", "2026-11-09"))
            det = detect_t0(data, "2026-12-29")
            assert det["t0"] == "2026-11-04" and det["pre"] == "2026-11-03" and det["exact"], det
            res = compute_round(data, 1)
            assert res["window"]["earliest_trade_session"] == "2026-11-04", res["window"]
            assert res["replication"]["pass"], res["replication"]
            v = res["verdicts"]["decision"]
            assert v.startswith(expect), (drift, v, res["deltas_pctp"], res["exposure"])
            assert res["exposure"]["E_pre_t0"] > TARGET_19, res["exposure"]
            assert res["data_quality"]["actual_approx_sessions"] == 2, res["data_quality"]
            assert res["exposure"]["E_b155_t0"] <= TARGET_155 + 1e-9
            assert res["exposure"]["E_b19_t0"] <= TARGET_19 + 1e-9
            assert res["exposure"]["E_simple"] is not None and not res["verdicts"]["simple"].startswith("판정 보류")
            assert res["need_closes"]["missing"] == 0 and res["need_closes"]["split_like_moves"] == 0
            assert res["need_closes"]["missing_before_t0"] == 0, res["need_closes"]
            sg = res["signals"]
            assert sg["premortem_a_1_9_better"] == ("예" if v.startswith("1.9가 나았음") else "아니오")
            assert sg["premortem_b_public_closes_used"] == "아니오"
            assert sg["precelebration_c_no_L4"].startswith("계산 불가")   # fixtures carry no L lines
            if res["paths"]["soxx"]["R_pct"] <= 0:
                assert sg["precelebration_d_rally_at_E_1_60"].startswith("해당 없음"), sg
            else:   # E after the cut ~1.36 and the account rose -> yes
                assert sg["precelebration_d_rally_at_E_1_60"] == ("예" if res["paths"]["actual"]["R_pct"] > 0
                                                                  and sg["core_E_window_median"] <= 1.60
                                                                  else "아니오"), sg
                assert sg["core_E_sessions"] == res["window"]["sessions"] + 1 - 2, sg   # two stale days
            privacy_check(res)
            json.dumps(res, allow_nan=False)
            # round 2 needs closes to 2027-03-25: these end earlier -> stop (run again later)
            _expect_stop(lambda: compute_round(data, 2), "before the round end")
    # 5b a 1x symbol sold on 11/20 loses its core closes: stop until a Nasdaq supplement is saved; with
    #    it the result matches the full-data result; a supplement at the wrong level stops
    px = gen(-0.012)
    cut = {**px, "AAA": [v if t <= "2026-11-20" else None for t, v in zip(sessions, px["AAA"])]}
    with tempfile.TemporaryDirectory() as tmp:
        full = compute_round(account(Path(tmp), px, px, sell_aaa=True), 1)
    with tempfile.TemporaryDirectory() as tmp:
        data = account(Path(tmp), px, cut, sell_aaa=True)
        _expect_stop(lambda: compute_round(data, 1), "fetch its Nasdaq supplement")
        assert run_check(Path(tmp))["fetch_supplement_for"] == ["AAA"]
    with tempfile.TemporaryDirectory() as tmp:
        nasdaq(Path(tmp), "AAA", px["AAA"])
        filled = compute_round(account(Path(tmp), px, cut, sell_aaa=True), 1)
        assert filled["verdicts"]["decision"] == full["verdicts"]["decision"], (filled["verdicts"], full["verdicts"])
        assert filled["need_closes"]["supplemented"] > 20, filled["need_closes"]
        assert filled["need_closes"]["symbols_missing_first_or_last"] == 0
        assert abs(filled["deltas_pctp"]["decision"]["dU"] - full["deltas_pctp"]["decision"]["dU"]) < 0.05
        assert any(c.startswith("공개 종가로 채운 종가") for c in filled["caveats"]), filled["caveats"]
        assert filled["signals"]["premortem_b_public_closes_used"] == "예"
        chk = run_check(Path(tmp))
        assert chk["fetch_supplement_for"] == [] and chk["supplemented_symbols"] == 1, chk
    with tempfile.TemporaryDirectory() as tmp:
        nasdaq(Path(tmp), "AAA", px["AAA"], scale=1.5)
        _expect_stop(lambda: account(Path(tmp), px, cut, sell_aaa=True), "level differs")
    # 5c gaps inside the window: up to 5% per symbol is carried, more stops until a supplement exists;
    #    a supplement that spans them but has no rows there -> hold
    holes = ("2026-11-12", "2026-11-13", "2026-11-16")
    with tempfile.TemporaryDirectory() as tmp:
        one = {**px, "BBB": [None if t == holes[0] else v for t, v in zip(sessions, px["BBB"])]}
        res = compute_round(account(Path(tmp), px, one), 1)
        assert res["need_closes"]["missing"] == 1 and res["need_closes"]["allowed_missing_per_symbol"] == 2
        assert not res["verdicts"]["decision"].startswith("판정 보류"), res["verdicts"]
        assert any(c.startswith("가상 계좌·④의 빠진 종가 1건") for c in res["caveats"]), res["caveats"]
    three_holes = {**px, "BBB": [None if t in holes else v for t, v in zip(sessions, px["BBB"])]}
    with tempfile.TemporaryDirectory() as tmp:
        data = account(Path(tmp), px, three_holes)
        _expect_stop(lambda: compute_round(data, 1), "fetch its Nasdaq supplement")
    with tempfile.TemporaryDirectory() as tmp:
        nasdaq(Path(tmp), "BBB", px["BBB"])
        sup = json.loads((Path(tmp) / SUPP_DIR / "BBB.nasdaq-historical.json").read_text(encoding="utf-8"))
        rows = sup["data"]["tradesTable"]["rows"]
        sup["data"]["tradesTable"]["rows"] = [r_ for r_ in rows
                                              if f"{r_['date'][6:]}-{r_['date'][:2]}-{r_['date'][3:5]}" not in holes]
        (Path(tmp) / SUPP_DIR / "BBB.nasdaq-historical.json").write_text(json.dumps(sup), encoding="utf-8")
        res = compute_round(account(Path(tmp), px, three_holes), 1)
        assert res["verdicts"]["decision"] == "판정 보류(공개 종가로 채워도 빠진 종가가 남음)", res["verdicts"]
        assert run_check(Path(tmp))["symbols_a_supplement_spans_but_cannot_fill"] == 1
    # 5d E before the cut already <= 1.55 -> both hypothetical accounts are the same -> hold
    with tempfile.TemporaryDirectory() as tmp:
        res = compute_round(account(Path(tmp), px, px, three=8000.0), 1)
        assert res["window"]["t0"] == "2026-11-04" and res["exposure"]["E_pre_t0"] <= TARGET_155, res
        assert res["verdicts"]["decision"] == "판정 보류(줄이기 직전 E가 이미 1.55 이하 — 두 가상 계좌가 같음)"
    # 5e everything sold for cash on 11/04: T0 found, (1) is flat cash, actual E 0
    with tempfile.TemporaryDirectory() as tmp:
        res = compute_round(account(Path(tmp), px, px, sell_all=True), 1)
        assert res["window"]["t0"] == "2026-11-04", res.get("window")
        assert res["paths"]["actual"] == {"R_pct": 0.0, "MDD_pct": 0.0}, res["paths"]["actual"]
        assert res["verdicts"]["execution"].startswith("목표 E와 다름(실제 E 0.00)"), res["verdicts"]
        assert res["verdicts"]["decision"].startswith("1.55가 나았음"), res["verdicts"]
    # 5f a supplement fetched before the window-end close (rows to 12/10) cannot cover the later gap:
    #    stop and fetch again - never a final hold
    with tempfile.TemporaryDirectory() as tmp:
        nasdaq(Path(tmp), "AAA", px["AAA"], upto="2026-12-10")
        data = account(Path(tmp), px, cut, sell_aaa=True)
        _expect_stop(lambda: compute_round(data, 1), "fetched before then must be fetched again")
        assert run_check(Path(tmp))["fetch_supplement_for"] == ["AAA"]
    # 5g a core outage just before T0 (a held symbol's 10/27 close missing): the E at T0 needs it ->
    #    stop until a supplement covers it; one that starts after the gap does not
    gap = {**px, "BBB": [None if t == "2026-10-27" else v for t, v in zip(sessions, px["BBB"])]}
    with tempfile.TemporaryDirectory() as tmp:
        data = account(Path(tmp), px, gap)
        _expect_stop(lambda: compute_round(data, 1), "fetch its Nasdaq supplement")
        assert run_check(Path(tmp))["fetch_supplement_for"] == ["BBB"]
        nasdaq(Path(tmp), "BBB", px["BBB"], frm="2026-11-02")
        _expect_stop(lambda: compute_round(Data(Path(tmp)), 1), "fetch its Nasdaq supplement")
        nasdaq(Path(tmp), "BBB", px["BBB"])
        res = compute_round(Data(Path(tmp)), 1)
        assert not res["verdicts"]["decision"].startswith("판정 보류"), res["verdicts"]
        assert res["need_closes"]["missing_before_t0"] == 0 and res["need_closes"]["supplemented"] == 1, res
    # 5h a 1x symbol bought on the pre-trade date whose core history starts at T0: its start price comes
    #    from the snapshot and the E at T0 cannot be computed -> hold 6, not a stop
    px_c = {**px, "CCC": [v * 0.5 for v in px["BBB"]]}
    core_c = {**px_c, "CCC": [None if t < "2026-11-04" else v for t, v in zip(sessions, px_c["CCC"])]}
    with tempfile.TemporaryDirectory() as tmp:
        res = compute_round(account(Path(tmp), px_c, core_c, buy_ccc=True), 1)
        assert res["window"]["t0"] == "2026-11-04", res.get("window")
        assert res["verdicts"]["decision"] == "판정 보류(실행 직전 계좌 E 계산 불가)", res["verdicts"]
    # 5i staging slips stop instead of ending the round: reviews cut short, none before 11/02, too few
    #    reference reviews; a round-end session the core skipped -> wait
    with tempfile.TemporaryDirectory() as tmp:
        account(Path(tmp), px, px)
        for keep, text in ((lambda f: f.S < "2026-12-15", "copied exposure reviews end"),
                           (lambda f: f.S >= FIRST_SESSION, "holdings dated before"),
                           (lambda f: f.S >= "2026-10-29", "reference exposure reviews")):
            data = Data(Path(tmp))
            data.snaps = [f for f in data.snaps if keep(f)]
            _expect_stop(lambda: compute_round(data, 1), text)
        data = Data(Path(tmp))
        for ser in data.closes.values():
            ser.pop("2026-12-29", None)
        data.cal.remove("2026-12-29")
        data.cal_set.discard("2026-12-29")
        _expect_stop(lambda: compute_round(data, 1), "skip the round end")
    # 6 no reduction -> hold; a split with a record is continuous, without a record the guard trips
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        px6 = gen()
        k = sessions.index("2026-09-15")
        px6[LEVER] = [v / 3.0 if i >= k else v for i, v in enumerate(px6[LEVER])]
        at = {s: dict(zip(sessions, v)) for s, v in px6.items()}
        units = {"AAA": 300.0, LEVER: 900.0}
        snaps = [{"S": s, "raw": _snap_raw(s, s, {**units, LEVER: 900.0 * (3 if s >= "2026-09-15" else 1)}, 5000.0,
                                           {kk: at[kk][s] for kk in units}, mult)}
                 for s in sessions if "2026-10-13" <= s <= "2026-12-31"]
        _write_fixture(root, px6, sessions, snaps)
        data = Data(root)
        calc = ExposureCalc(data)
        assert calc.parts({LEVER: 0.5}, mult, "2026-10-30", 252, 60)[2].startswith("SPLIT_GUARD")
        _write_fixture(root, px6, sessions, snaps, [{"symbol": LEVER, "action_type": "SPLIT",
                                                     "effective_session": "2026-09-15", "new_shares": 3,
                                                     "old_shares": 1}])
        _fill_e(root)
        data = Data(root)
        calc = ExposureCalc(data)
        assert calc.parts({LEVER: 0.5}, mult, "2026-10-30", 252, 60)[2] is None
        assert detect_t0(data, "2026-12-29")["t0"] is None
        res = compute_round(data, 1)
        assert res["verdicts"]["decision"] == "판정 보류(줄이기 체결 없음)"
    # 6b an unrecorded 1:4 split of a held 1x symbol inside the window -> stop and wait for the core's
    #    split record; with the record the result equals the one without a split
    k = sessions.index("2026-12-01")
    split4 = {**px, "AAA": [v / 4.0 if i >= k else v for i, v in enumerate(px["AAA"])]}
    with tempfile.TemporaryDirectory() as tmp:
        data = account(Path(tmp), px, split4)
        _expect_stop(lambda: compute_round(data, 1), "split-like day move")
    rec = [{"symbol": "AAA", "action_type": "SPLIT", "effective_session": "2026-12-01", "new_shares": 4,
            "old_shares": 1}]
    with tempfile.TemporaryDirectory() as tmp:
        with_rec = compute_round(account(Path(tmp), px, split4, splits=rec), 1)
    with tempfile.TemporaryDirectory() as tmp:
        plain = compute_round(account(Path(tmp), px, px), 1)
    assert with_rec["verdicts"] == plain["verdicts"], (with_rec["verdicts"], plain["verdicts"])
    assert abs(with_rec["deltas_pctp"]["decision"]["dU"] - plain["deltas_pctp"]["decision"]["dU"]) < 1e-3
    # 6c SOXX -17% in one day: SOXL at 0.49 moved with the market -> a real return, no hold; an unrecorded
    #    1:2 SOXL split on a calm day -> stop and wait for the record
    k = sessions.index("2026-12-02")
    crash = {s: list(v) for s, v in px.items()}
    for s, f_ in ((BENCH, 0.83), (LEVER, 0.49), ("AAA", 0.88), ("BBB", 0.9)):
        crash[s] = [v * f_ if i >= k else v for i, v in enumerate(crash[s])]
    with tempfile.TemporaryDirectory() as tmp:
        res = compute_round(account(Path(tmp), crash, crash), 1)
        assert not res["verdicts"]["decision"].startswith("판정 보류"), res["verdicts"]
        assert res["need_closes"]["simple_baseline"]["split_like_moves"] == 0, res["need_closes"]
        assert res["data_quality"]["big_daily_moves"] >= 1, res["data_quality"]
    half = {**px, LEVER: [v / 2.0 if i >= k else v for i, v in enumerate(px[LEVER])]}
    with tempfile.TemporaryDirectory() as tmp:
        data = account(Path(tmp), px, half)
        _expect_stop(lambda: compute_round(data, 1), "split-like day move")
    # 6e the 3x product is not SOXL and SOXL has no core history: the decision still runs and only (4) is
    #    on hold; a SOXL supplement file is ignored (no level to check) and --check does not ask for it
    pxt = gen(-0.006, None, random.Random(11))
    pxt["TQQ"] = pxt.pop(LEVER)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        nasdaq(root, LEVER, pxt["TQQ"])
        data = account(root, pxt, pxt, lev="TQQ")
        assert LEVER not in data.closes and data.supp_ignored == 1
        res = compute_round(data, 1)
        assert res["window"]["t0"] == "2026-11-04", res.get("window")
        assert res["verdicts"]["simple"] == "판정 보류(④의 SOXL 코어 종가 이력 없음)", res["verdicts"]
        assert not res["verdicts"]["decision"].startswith("판정 보류"), res["verdicts"]
        chk = run_check(root)
        assert chk["fetch_supplement_for"] == [] and chk["need_symbols_without_core_history"] == 1, chk
        assert chk["supplement_files_ignored"] == 1, chk
    # 7 contract: CRLF, BOM and UTF-16 re-saves keep it; results below the marker keep it; an edit above
    #   it, a missing or doubled marker, a changed calc file or a bad sidecar break it; then the date
    #   guard, the section 11 line guard, one real run per round and the round 1 link
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        account(root, px, px)
        (root / "docs/claude").mkdir(parents=True, exist_ok=True)
        head = "# 사전 등록\n\n본문\n"
        tail = "## 11. 결과\n\n" + PLACEHOLDER[1] + "\n" + PLACEHOLDER[2] + "\n"
        doc = head + MARK + "\n" + tail
        me = runner_hash(Path(__file__).resolve())
        good = sha256_bytes(head.encode("utf-8"))

        def side(extra: str = "", runner: str = me, bom: bool = False) -> None:
            txt = f"body_sha256 {good}\nrunner_sha256 {runner}\nfixed_at 2026-11-02T12:00:00+09:00 (KST)\n{extra}"
            (root / SIDECAR).write_bytes((b"\xef\xbb\xbf" if bom else b"") + txt.replace("\n", "\r\n").encode("utf-8"))

        def put(text: str) -> None:
            (root / PREREG).write_bytes(text.encode("utf-8"))

        side()
        put(doc)
        assert check_contract(root)["body_sha256"] == good
        for raw in (doc.replace("\n", "\r\n").encode("utf-8"), b"\xef\xbb\xbf" + doc.encode("utf-8"),
                    doc.replace("\n", "\r\n").encode("utf-16")):
            (root / PREREG).write_bytes(raw)
            assert check_contract(root)["body_sha256"] == good
        side(bom=True)
        assert check_contract(root)["fixed_at"] == "2026-11-02T12:00:00+09:00"
        put(doc.replace(PLACEHOLDER[2], PLACEHOLDER[2] + "\n- 메모"))
        assert check_contract(root)["body_sha256"] == good
        put(doc.replace("본문", "본문!"))
        _expect_stop(lambda: check_contract(root), "changed above the marker")
        put(head + tail)
        _expect_stop(lambda: check_contract(root), "marker line exactly once")
        put(head + MARK + "\n" + MARK + "\n" + tail)
        _expect_stop(lambda: check_contract(root), "marker line exactly once")
        put(doc)
        side(runner="0" * 64)
        _expect_stop(lambda: check_contract(root), "calc file changed")
        side("amended_at 2026-11-01T12:00:00+09:00\n")
        _expect_stop(lambda: check_contract(root), "after the original lock")
        side("fixed_at 2026-11-03T12:00:00+09:00\n")
        _expect_stop(lambda: check_contract(root), "exactly one fixed_at")
        side("amended_at 2026-11-05T12:00:00\n")
        _expect_stop(lambda: check_contract(root), "UTC offset")
        side("amended_at 2026-11-05T12:00:00+09:00\n")
        assert check_contract(root)["amended_at"] == ["2026-11-05T12:00:00+09:00"]
        side()
        _expect_stop(lambda: run_round(root, 1, now=datetime(2026, 12, 29, 23, 59, tzinfo=KST)), "may run from")
        _expect_stop(lambda: run_round(root, 2, now=datetime(2027, 3, 28, 23, 59, tzinfo=KST)), "may run from")
        put(doc.replace(PLACEHOLDER[1], "- 1차: 손으로 적음"))
        _expect_stop(lambda: run_round(root, 1, now=datetime(2026, 12, 30, 9, 0, tzinfo=KST)), "placeholder")
        assert not (root / RESULTS[1]).exists()
        put(doc.replace(PLACEHOLDER[2], PLACEHOLDER[2] + "\n" + PLACEHOLDER[2]))
        _expect_stop(lambda: round_guard(root, 1), "exactly one")
        put(doc)
        _expect_stop(lambda: round_guard(root, 2), "run round 1 first")
        manual = "- 1차: " + MANUAL_HOLD + " STOP[wait]: round 1 may run from 2026-12-30 KST)"
        put(doc.replace(PLACEHOLDER[1], manual))
        assert round_guard(root, 2) == {"run": False}
        put(doc)
        res = run_round(root, 1, now=datetime(2026, 12, 30, 9, 0, tzinfo=KST))
        saved = json.loads((root / RESULTS[1]).read_text(encoding="utf-8"))
        assert saved["contract"]["body_sha256"] == good and saved["verdicts"] == res["verdicts"]
        assert saved["window"]["t0"] == "2026-11-04" and saved["post_hoc_possible"] is False
        assert saved["inputs"]["files"] > 50 and saved["schema"] == "strategy1101-score-2"
        _expect_stop(lambda: run_round(root, 1, now=datetime(2026, 12, 31, 9, 0, tzinfo=KST)), "exists")
        _expect_stop(lambda: round_guard(root, 2), "run round 1 first")
        r1_raw = (root / RESULTS[1]).read_bytes()
        r1_sha = sha256_bytes(_norm(r1_raw))
        put(doc.replace(PLACEHOLDER[1], manual))
        _expect_stop(lambda: round_guard(root, 2), "stopped by hand")
        line1 = f"- 1차: {res['verdicts']['decision']} · 결과 sha256 {r1_sha[:8]}"
        put(doc.replace(PLACEHOLDER[1], line1))
        g = round_guard(root, 2)
        assert g == {"run": True, "sha256": r1_sha, "t0": "2026-11-04"}, g
        (root / RESULTS[1]).write_bytes(b"\xef\xbb\xbf" + r1_raw.replace(b"\n", b"\r\n"))   # a Windows re-save
        assert round_guard(root, 2)["sha256"] == r1_sha
        put(doc.replace(PLACEHOLDER[1], line1.replace(r1_sha[:8], "0" * 8)))
        _expect_stop(lambda: round_guard(root, 2), "does not match")
        put(doc.replace(PLACEHOLDER[1], line1))
        (root / RESULTS[1]).unlink()
        _expect_stop(lambda: round_guard(root, 2), "copy the round 1 results file")
        (root / RESULTS[1]).write_bytes(r1_raw)
        put(doc.replace(PLACEHOLDER[1], line1).replace(PLACEHOLDER[2], "- 2차: 손으로 적음"))
        _expect_stop(lambda: round_guard(root, 2), "placeholder")
        put(doc.replace(PLACEHOLDER[1], line1))
        assert check_contract(root)["body_sha256"] == good
        (root / PREREG).unlink()
        _expect_stop(lambda: check_contract(root), "missing (not fixed)")
    # 7b round 2 end to end: closes to 2027-04-02 and reviews to 2027-03-31; round 1 runs and its line is
    #    copied with the results hash prefix; round 2 links it and reports the 10% cap and signal (e)
    long_sessions = weekdays(date(2026, 4, 1), date(2027, 4, 2))
    pxl = gen(0.001, long_sessions, random.Random(7))
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        account(root, pxl, pxl, sess=long_sessions, snap_to="2027-03-31")
        doc2, good2 = contract(root)
        r1 = run_round(root, 1, now=datetime(2026, 12, 30, 9, 0, tzinfo=KST))
        s1 = sha256_bytes(_norm((root / RESULTS[1]).read_bytes()))
        line = f"- 1차: {r1['verdicts']['decision']} · 결과 sha256 {s1[:8]}"
        (root / PREREG).write_bytes(doc2.replace(PLACEHOLDER[1], line).encode("utf-8"))
        r2 = run_round(root, 2, now=datetime(2027, 3, 29, 9, 0, tzinfo=KST))
        assert r2["round1"] == {"run": True, "sha256": s1, "t0": "2026-11-04", "t0_same": True}, r2["round1"]
        assert r2["window"]["t0"] == "2026-11-04" and r2["window_end"] == "2027-03-25", r2["window"]
        assert not r2["verdicts"]["decision"].startswith("판정 보류"), r2["verdicts"]

        def share(S: str) -> float:
            f_ = next((root / "workspace/outputs/exposure-review" / S).glob("*.json"))
            raw = json.loads(f_.read_text(encoding="utf-8"))
            return math.fsum(p["weight"] for p in raw["positions"] if p["nominal_multiplier"] >= MULT_3X)

        days_ = [t for t in long_sessions if FIRST_SESSION <= t <= "2027-03-25"]
        cap = r2["cap_3x"]
        assert cap["sessions_checked"] == len(days_) and cap["end_holdings_fresh"] is True, cap
        assert cap["at_window_end"] == ("예" if share("2027-03-25") <= CAP_3X else "아니오"), cap
        assert cap["sessions_above"] == sum(1 for t in days_ if share(t) > CAP_3X), cap
        assert r2["signals"]["premortem_e_3x_above_10"] == ("예" if cap["at_window_end"] == "아니오" else "아니오")
        assert json.loads((root / RESULTS[2]).read_text(encoding="utf-8"))["round1"]["t0_same"] is True
        assert check_contract(root)["body_sha256"] == good2
        _expect_stop(lambda: run_round(root, 2, now=datetime(2027, 3, 30, 9, 0, tzinfo=KST)), "exists")
    # 8 privacy guard
    _expect_stop(lambda: privacy_check({"paths": {"actual": {"weight_SOXL": 0.3}}}), "forbidden output key")
    # 9 main: an unexpected error prints one tagged line without its message (it could name a holding)
    real = globals()["run_check"]

    def boom(root: Path) -> dict[str, Any]:
        raise KeyError("SECRET-SYMBOL")

    globals()["run_check"] = boom
    try:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main(["--check", "--root", "."])
    finally:
        globals()["run_check"] = real
    assert code == 3 and err.getvalue().startswith("STOP[amend]: unexpected KeyError"), err.getvalue()
    assert "SECRET" not in err.getvalue()
    # 10 unreadable or malformed inputs stop with a tag, without a traceback or a file name; a BOM is fine
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        account(root, px, px)
        f_ = next((root / "workspace/outputs/exposure-review/2026-10-30").glob("*.json"))
        keep = f_.read_bytes()
        f_.write_text("{", encoding="utf-8")
        _expect_stop(lambda: Data(root), "not readable JSON")
        f_.write_text(json.dumps({"evaluation_session": "2026-10-30", "positions": [{"symbol": "AAA"}]}),
                      encoding="utf-8")
        _expect_stop(lambda: Data(root), "lacks a field")
        f_.write_bytes(b"\xef\xbb\xbf" + keep)
        assert any(sn.S == "2026-10-30" for sn in Data(root).snaps)
        h_ = root / HIST_DIR / "BBB.close-history.json"
        h_.write_text(h_.read_text(encoding="utf-8").replace('"close"', '"klose"', 1), encoding="utf-8")
        _expect_stop(lambda: Data(root), "lacks a field")
    print("SELF-TEST PASS")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--self-test", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--run", action="store_true")
    ap.add_argument("--round", type=int, choices=(1, 2))
    ap.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    ap.add_argument("--debug", action="store_true", help="re-raise an unexpected error with its traceback")
    a = ap.parse_args(argv)
    if a.self_test:
        self_test()
        return 0
    if a.run and a.round is None:
        ap.error("--run needs --round")
    try:
        if a.check:
            print(json.dumps(run_check(a.root), ensure_ascii=False, indent=1))
            return 0
        res = run_round(a.root, a.round)
        print(json.dumps(res, ensure_ascii=False, indent=1))
        print("results_sha256", sha256_bytes(_norm((a.root / RESULTS[a.round]).read_bytes())))
        return 0
    except Stop as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:  # the message could name a holding; --debug shows it
        if a.debug:
            raise
        print(f"STOP[amend]: unexpected {type(exc).__name__} - run again with --debug to see where",
              file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
