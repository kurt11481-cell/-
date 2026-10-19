#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""t2rc-oracle.py - T2 B+ independent calculator (M1 of docs/claude/t2-rc-preregistration-2026-10-14.md 3).

Read-only. Never imports manage-us-stock-strategy/scripts (no auto_core* module): every rule below is written from
  - the integrated-check rule file docs/claude/integrated-check-prompt-v3.12.5-2026-10-14.txt (3) common rules C1-C8,
    persistence, aliases, card triggers; 2-3) exposure; buy-requirement line),
  - docs/claude/c-rule-replay-preregistration-2026-10-09.md 4 (formula table, readings (i)(ii)),
  - the design docs/claude/order-instruction-design-2026-10-06.md (1 circuit, 3 gates G0-G5, 5 regret table,
    7-1 quantity, 7-2 price) and its T2 transcription docs/claude/redesign-t2-builder-prompt-2026-10-10.md
    (D5-D7, F1-F5, appendix A-3/A-4),
  - docs/claude/recovery-gate-R-REC1-2026-10-09.md (R-REC1),
  - docs/claude/event-strategy-2026-10-13.md 11-1 and docs/claude/ev-rg1-hyper-builder-prompt.md R0-R8 (RG1: an official
    thesis-damage fact blocks until the card is accepted again; thesis-damage domains for RG1 only),
  - docs/claude/rrec-ev4-remove-decision-2026-10-19.md (user decision rrec-ev4 REMOVE: no account-line EV4 in R-REC1),
  - manage-us-stock-strategy/references/portfolio-exposure-review.md (R1 E = max(N, V), p-earn r1 blackout),
  - policy values read from stock-strategy-system/alert_policy.json.
Inputs are data files only (decision.json and the files its inputs point to, 30-minute pages, calendar).

Commands
  check  --day YYYY-MM-DD [--repo DIR] [--out FILE]   live comparison for one decide run (C1, C2 items)
  replay --replay-json FILE [--repo DIR] [--out FILE] circuit reproduction for a replay run (self-check)
  selftest                                            golden cases G-1 / G-S1 / G-2 and small synthetic rule checks
Exit: 0 = MATCH or NOT_CHECKED, 2 = MISMATCH, 1 = error.
Authority: order_authority false, quantity_authority "none", execution_quantity null. Writes only --out.
"""
import argparse
import datetime as dt
import glob
import hashlib
import json
import math
import os
import re
import sys
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP

ORACLE_VERSION = "t2rc-oracle-1.0"

# ---------------------------------------------------------------- constants (value · source)
SIGMA_WINDOW = 60          # sigma60, rule file 2) / design 7-2
EMA_FAST, EMA_MID, EMA_SLOW = 10, 20, 50   # rule file 2)
RSI_N = 14                 # rule file 2) Wilder
ATR_N = 14                 # rule file 2) Wilder
HL_WINDOW = 20             # rule file 2) previous 20 sessions, today excluded
C1_RSI_HI, C1_RSI_LO, C1_ATR_K = 70.0, 30.0, 2.0          # rule file 3) C1
C2_ATR_K, C2_POS_HI, C2_POS_LO, C2_VOL_K = 2.5, 0.35, 0.65, 1.2   # rule file 3) C2
C6_BAND = 0.015            # rule file 3) C6 / DL6 (user 2026-10-03 (ii))
EVENT_WINDOW = 5           # rule file 3) persistence: event type counts 5 sessions incl. the day
C7_SESSIONS = 2            # rule file 3) C7: within 2 sessions
C7_RECORD_DAYS = 10        # builder report R2-4: C7 reads the facts of the last 10 research-record days
SPLIT_GUARD = 0.45         # builder prompt F1 split suspicion
SPLIT_KS = (2, 3, 4, 5, 8, 10, 15, 20)
SPLIT_TOL = 0.03
BUY_LOC_K = 0.5            # design 7-2: buy cap = ref x (1 + 0.5 sigma), cents down
SELL_LOC_K = 1.0           # design 7-2: planned reduce floor = ref x (1 - sigma), cents up
FEE_BUFFER = Decimal("0.0025")   # design G4 / F4: qty x cap x (1 + 0.25%) <= order-available cash
DEADBAND = 0.02            # design 7-1 4: order amount < 2% of equity -> no ticket
REGRET_BUDGET = 0.03       # design 5: 3% of equity
STEPS = ((Decimal(0), "0"), (Decimal(1) / 3, "1/3"), (Decimal(1) / 2, "1/2"), (Decimal(1), "1"))
# step quantity = floor(delta x n / d) in integers (Judge2 2026-10-15 1: the 28-digit Decimal 1/3 gave k - 1 for delta 3k)
STEP_FRAC = {"0": (0, 1), "1/3": (1, 3), "1/2": (1, 2), "1": (1, 1)}
WEIGHT_STEP = Decimal("0.001")   # builder prompt F5 grid
EXPOSURE_TARGET = 1.55     # alert_policy target_exposure (read again from policy at run time)
V_WINDOW, V_MIN = 252, 60  # alert_policy sox_equivalent window_sessions / minimum_sessions
REQ_PRODUCTS = ("BE", "MU", "NBIS", "DELL", "AMD", "SOXL", "TQQQ", "DRAM", "PWR", "LITE")  # rule file 3) buy-req (2)
RREC_LOOKBACK = 60          # R-REC1 doc 1 / rule file 2-3 (4): most recent event within 60 sessions
RREC_CLOSE_SESSIONS = 20    # R-REC1 doc 2: time decay 20 sessions + RG2

# common-rule groups (rule file 3) "트리거 종류 이름"; group ids follow the kinds, not the core's code)
COMMON = {
    "C1-": ("overheat", "-"), "C1+": ("oversold", "+"),
    "C2-": ("overheat_fade", "-"), "C2+": ("oversold_rebound", "+"),
    "C3-": ("trend_break", "-"), "C3+": ("trend_recover", "+"),
    "C4-": ("false_breakout", "-"), "C4+": ("false_breakdown", "+"),
    "C5-": ("new_low", "-"), "C5+": ("new_high", "+"),
    "C6-": ("rebound_fail", "-"), "C6+": ("pullback_rebound", "+"),
    "C7-": ("good_news_drop", "-"), "C7+": ("bad_news_rise", "+"),
    "C8-": ("crash_alert", "alert"), "C8+": ("spike_alert", "alert"),
}
# card kinds -> (group, replaces the common alias of that group?)  rule file 3) "같은 종류 합치기"
CARD_KIND = {
    "ema_below": ("trend_break", False),            # V3: card-unique, does not replace C3-
    "ema20_below_twice": ("trend_break", True),     # S4 N6 U7 BE7 DL7 AM7 X7: alias of C3-
    "ema_below_unrecovered": ("trend_break", False),  # S5: card-unique
    "new_high_hold": ("new_high", True),            # U5 BE5 DL5 AM5 X5: alias of C5+
    "pullback_rebound": ("pullback_rebound", True), # U6 BE6 DL6 AM6 X6: alias of C6+
    "good_news_drop": ("good_news_drop", True),     # N5 U4 BE4 DL4 AM4 X4: alias of C7-
    "drop_alert": ("crash_alert", True),            # S6 N8 U8 ... X8: alias of C8-
    "close_at_or_below": ("stop_reference", False), # S8 N9: alert
}
INFO_KINDS = {"earnings_notice", "log_only", "display_only"}
C7_BAD_KINDS = {"guidance", "dilution", "contract", "customer_change"}
SELL_FACT_KINDS = {"kill", "dilution", "customer_change", "guidance"}   # builder F3: - facts that count as strong (sell)   # rule file 111 C7+ (가이던스 하향·희석·주요 계약 축소)
MULT_ONE_ASSUMED = {"PWR", "LITE", "MRVL"}   # rule file 99: unregistered approved stocks / underlying counted as 1x
EXEMPT_FROM_EARNINGS = {"SOXL", "TQQQ", "DRAM", "SOXX", "GRID"}   # rule file 133: index ETFs excluded from the earnings check
UNDERLYING = {"MVLL": "MRVL"}   # rule file 4 / 133: leveraged single-stock ETF -> underlying earnings
SOURCE_KINDS = {"SEC_FILING", "COMPANY_PRESS_RELEASE", "COMPANY_IR"}


# ---------------------------------------------------------------- io helpers
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_lf(path):
    """sha256 over LF-normalized bytes (the M2 runner pins the calculator this way)."""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fnum(x):
    if x is None or x == "":
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def stdev(xs):
    n = len(xs)
    if n < 2:
        return None
    m = sum(xs) / n
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def quantile_linear(xs, q):
    s = sorted(xs)
    if not s:
        return None
    pos = (len(s) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return s[lo]
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


# ---------------------------------------------------------------- calendar
class Calendar:
    def __init__(self, repo):
        act = load_json(os.path.join(repo, "workspace/policies/integrated_identity_session_activation.json"))
        sc = act["session_calendar"]
        self.hash = sc["active_calendar_hash"]
        path = os.path.join(repo, "workspace/calendar-authority/artifacts", self.hash,
                            "us-equities-core-session-v2.calendar.json")
        raw_sha = sha256_file(path)
        if raw_sha != self.hash:
            raise RuntimeError("CALENDAR_HASH_MISMATCH %s != %s" % (raw_sha, self.hash))
        art = load_json(path)
        self.sessions = []
        self.close_at = {}
        self.open_at = {}
        for s in sorted(art["sessions"], key=lambda r: r["session_date"]):
            d = s["session_date"]
            self.sessions.append(d)
            self.close_at[d] = s["core_close_at"]
            self.open_at[d] = s["core_open_at"]
        self.index = {d: i for i, d in enumerate(self.sessions)}

    def bar_labels(self, d):
        """ET bar-start labels HHMMSS of the regular session (09:30 .. close-30m)."""
        o = dt.datetime.fromisoformat(self.open_at[d])
        c = dt.datetime.fromisoformat(self.close_at[d])
        out = []
        t = o
        while t + dt.timedelta(minutes=30) <= c:
            out.append(t.strftime("%H%M%S"))
            t += dt.timedelta(minutes=30)
        return out

    def ny_close(self, d):
        return dt.datetime.fromisoformat(self.close_at[d])

    def next_session(self, d):
        i = self.index.get(d)
        if i is None or i + 1 >= len(self.sessions):
            return None
        return self.sessions[i + 1]

    def prev_session(self, d):
        i = self.index.get(d)
        if i is None or i == 0:
            return None
        return self.sessions[i - 1]

    def offset(self, d, k):
        i = self.index.get(d)
        if i is None or not (0 <= i + k < len(self.sessions)):
            return None
        return self.sessions[i + k]


# ---------------------------------------------------------------- daily bars from 30-minute pages
class Series:
    """Split-adjusted regular-session daily bars of one symbol up to `through` (inclusive)."""

    def __init__(self, repo, cal, symbol, through, corp_actions):
        self.symbol = symbol
        self.flags = []
        rows = {}
        pages = sorted(glob.glob(os.path.join(repo, "workspace/outputs/regular-session-closes/pages", symbol, "*.json")))
        for p in pages:
            try:
                doc = load_json(p)
            except Exception:
                self.flags.append("PAGE_UNREADABLE:" + os.path.basename(p))
                continue
            for r in doc.get("result_list") or []:
                tm = str(r.get("cntr_tm") or "")
                if len(tm) == 14:
                    rows[tm] = r   # later page (file name order) wins
        self.pages = len(pages)
        days = sorted({k[:8] for k in rows})
        first = None
        for d8 in days:
            d = "%s-%s-%s" % (d8[:4], d8[4:6], d8[6:])
            if d in cal.index:
                first = d
                break
        self.dates, self.o, self.h, self.l, self.c, self.v, self.complete = [], [], [], [], [], [], []
        if first is None:
            return
        for d in cal.sessions[cal.index[first]:]:
            if d > through:
                break
            labels = cal.bar_labels(d)
            d8 = d.replace("-", "")
            bars = [rows.get(d8 + lb) for lb in labels]
            last = bars[-1] if bars else None
            if last is None or fnum(last.get("cur_prc")) is None:
                self.dates.append(d); self.o.append(None); self.h.append(None); self.l.append(None)
                self.c.append(None); self.v.append(None); self.complete.append(False)
                continue
            ok = all(b is not None for b in bars)
            self.dates.append(d)
            self.c.append(fnum(last["cur_prc"]))
            if ok:
                self.o.append(fnum(bars[0].get("open_pric")))
                self.h.append(max(fnum(b.get("high_pric")) for b in bars))
                self.l.append(min(fnum(b.get("low_pric")) for b in bars))
                self.v.append(sum(fnum(b.get("trde_qty")) or 0.0 for b in bars))
            else:
                self.o.append(None); self.h.append(None); self.l.append(None); self.v.append(None)
            self.complete.append(ok)
        self.raw_c = list(self.c)
        # split adjustment from the official corporate-action record (prices x old/new before effective session)
        for a in corp_actions:
            if a.get("symbol") != symbol or a.get("action_type") != "SPLIT":
                continue
            eff = a["effective_session"]
            if eff > through:
                continue
            pf = a["old_shares"] / a["new_shares"]
            for i, d in enumerate(self.dates):
                if d < eff:
                    for arr in (self.o, self.h, self.l, self.c):
                        if arr[i] is not None:
                            arr[i] = arr[i] * pf
                    if self.v[i] is not None:
                        self.v[i] = self.v[i] / pf
            self.flags.append("SPLIT_ADJUSTED:%s:%s" % (symbol, eff))
        self.index = {d: i for i, d in enumerate(self.dates)}
        self.split_suspected = None
        for i in range(1, len(self.c)):
            a, b = self.c[i - 1], self.c[i]
            if a and b:
                ratio = b / a
                if abs(ratio - 1) >= SPLIT_GUARD:
                    for k in SPLIT_KS:
                        for target in (k, 1.0 / k):
                            if abs(ratio / target - 1) <= SPLIT_TOL:
                                self.split_suspected = self.dates[i]
        if self.split_suspected:
            self.flags.append("SPLIT_SUSPECTED:%s:%s" % (symbol, self.split_suspected))

    def history_check(self, repo):
        """Cross-check raw closes with the saved close history (display / data-definition evidence)."""
        p = os.path.join(repo, "workspace/outputs/regular-session-closes/history", self.symbol + ".close-history.json")
        if not os.path.exists(p):
            return {"status": "MISSING"}
        diffs = []
        for s in load_json(p).get("sessions") or []:
            i = self.index.get(s.get("session_date")) if hasattr(self, "index") else None
            if i is None:
                continue
            hv = fnum(s.get("close"))
            if hv is None or self.raw_c[i] is None or abs(hv - self.raw_c[i]) > 1e-9:
                diffs.append([s.get("session_date"), s.get("close"), self.raw_c[i]])
        return {"status": "OK" if not diffs else "DIFF", "diffs": diffs[:10], "n_diffs": len(diffs)}


# ---------------------------------------------------------------- indicators
def ema_series(c, n):
    out = [None] * len(c)
    seed = []
    e = None
    for i, x in enumerate(c):
        if x is None:
            e = None
            seed = []
            continue
        if e is None:
            seed.append(x)
            if len(seed) == n:
                e = sum(seed) / n
                out[i] = e
            continue
        e = e + (2.0 / (n + 1)) * (x - e)
        out[i] = e
    return out


def rsi_series(c, n=RSI_N):
    out = [None] * len(c)
    ag = al = None
    gains, losses = [], []
    for i in range(1, len(c)):
        if c[i] is None or c[i - 1] is None:
            ag = al = None; gains, losses = [], []
            continue
        d = c[i] - c[i - 1]
        g, lo = max(d, 0.0), max(-d, 0.0)
        if ag is None:
            gains.append(g); losses.append(lo)
            if len(gains) == n:
                ag, al = sum(gains) / n, sum(losses) / n
            else:
                continue
        else:
            ag = (ag * (n - 1) + g) / n
            al = (al * (n - 1) + lo) / n
        out[i] = 100.0 if al == 0 else 100.0 - 100.0 / (1.0 + ag / al)
    return out


def atr_series(h, l, c, n=ATR_N):
    out = [None] * len(c)
    a = None
    trs = []
    for i in range(1, len(c)):
        if None in (h[i], l[i], c[i - 1]):
            a = None; trs = []
            continue
        tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        if a is None:
            trs.append(tr)
            if len(trs) == n:
                a = sum(trs) / n
            else:
                continue
        else:
            a = (a * (n - 1) + tr) / n
        out[i] = a
    return out


class Ind:
    def __init__(self, s):
        self.s = s
        c = s.c
        n = len(c)
        self.ema10 = ema_series(c, EMA_FAST)
        self.ema20 = ema_series(c, EMA_MID)
        self.ema50 = ema_series(c, EMA_SLOW)
        self.rsi = rsi_series(c)
        self.atr = atr_series(s.h, s.l, c)
        self.ret = [None] + [(c[i] / c[i - 1] - 1) if (c[i] is not None and c[i - 1]) else None for i in range(1, n)]
        self.sigma = [None] * n
        self.hi20 = [None] * n
        self.lo20 = [None] * n
        self.vol20 = [None] * n
        self.pos = [None] * n
        for i in range(n):
            if i >= SIGMA_WINDOW:
                w = self.ret[i - SIGMA_WINDOW + 1:i + 1]
                if all(x is not None for x in w):
                    self.sigma[i] = stdev(w)
            if i >= HL_WINDOW:
                w = c[i - HL_WINDOW:i]
                if all(x is not None for x in w):
                    self.hi20[i], self.lo20[i] = max(w), min(w)
                wv = s.v[i - HL_WINDOW:i]
                if all(x is not None for x in wv):
                    self.vol20[i] = sum(wv) / HL_WINDOW
            if None not in (s.h[i], s.l[i], c[i]):
                self.pos[i] = 0.5 if s.h[i] == s.l[i] else (c[i] - s.l[i]) / (s.h[i] - s.l[i])

    def snapshot(self, i):
        s = self.s
        g = lambda arr: arr[i] if 0 <= i < len(arr) else None
        return {"session": s.dates[i], "close": g(s.c), "ema10": g(self.ema10), "ema20": g(self.ema20),
                "ema50": g(self.ema50), "rsi14": g(self.rsi), "atr14": g(self.atr), "sigma60": g(self.sigma),
                "close_high_20": g(self.hi20), "close_low_20": g(self.lo20), "average_volume_20": g(self.vol20),
                "volume": g(s.v), "regular_high": g(s.h), "regular_low": g(s.l), "close_position": g(self.pos)}


# ---------------------------------------------------------------- trigger state machines (one array per trigger)
def _cmp(a, b, op):
    if a is None or b is None:
        return None
    return a < b if op == "<" else a > b


def state_simple(n, cond):
    out = []
    for i in range(n):
        v = cond(i)
        out.append("unk" if v is None else ("hit" if v else "none"))
    return out


def state_run(n, rel, min_len, need_prior_opposite, pending_short=False):
    """rel(i): True (strictly on the side) / False / None. Hit while the current run is >= min_len.
    need_prior_opposite: C3 (rule 113 v3.12.5) - the run must start after an observed opposite-side close.
    pending_short: a shorter run is "pending" (S5: waiting whether it recovers within 2 sessions; not counted)."""
    out = []
    for i in range(n):
        v = rel(i)
        if v is None:
            out.append("unk"); continue
        if not v:
            out.append("none"); continue
        L = 0
        j = i
        prior = None
        while j >= 0:
            r = rel(j)
            if r is True:
                L += 1; j -= 1; continue
            prior = r   # False or None
            break
        if L < min_len:
            out.append("pending" if pending_short else "none"); continue
        if need_prior_opposite and prior is not False:
            out.append("unk"); continue   # "유지 중(성립일 확인 필요)" - not counted
        out.append("hit")
    return out


def state_breakout(ind, side):
    """C5-/C5+/X5: line fixed at the first session (= previous 20 closes, today excluded); 1st session pending,
    2nd consecutive session hit; state type while close stays beyond the line and EMA10 (rule file 3) C5, "신고가 돌파")."""
    s = ind.s
    n = len(s.c)
    out = []
    run_len = 0
    line = None
    for i in range(n):
        c, e10 = s.c[i], ind.ema10[i]
        if c is None or e10 is None:
            out.append("unk"); run_len = 0; line = None; continue
        beyond = (lambda L: c < L and c < e10) if side == "-" else (lambda L: c > L and c > e10)
        if run_len > 0 and line is not None and beyond(line):
            run_len += 1
        else:
            run_len = 0
            line = None
            L0 = ind.lo20[i] if side == "-" else ind.hi20[i]
            if L0 is None:
                out.append("unk"); continue
            if beyond(L0):
                run_len, line = 1, L0
        out.append("none" if run_len == 0 else ("pending" if run_len == 1 else "hit"))
    return out


def events_to_state(n, ev_side, ev_opp):
    """Event type (C2 C4 C6 C7): one count for EVENT_WINDOW sessions incl. the event day; re-event restarts;
    an opposite event of the same number on a later day resolves it that day."""
    out = []
    for t in range(n):
        last = None
        unknown = False
        for k in range(t, max(-1, t - EVENT_WINDOW), -1):
            v = ev_side[k]
            if v is True:
                last = k; break
            if v is None:
                unknown = True
        if last is not None:
            resolved = any(ev_opp[k] is True for k in range(last + 1, t + 1))
            out.append("none" if resolved else "hit")
        else:
            out.append("unk" if unknown else "none")
    return out


def c6_events(ind, side, band):
    s = ind.s
    c, e20 = s.c, ind.ema20
    n = len(c)
    ev = [None] * n
    for t in range(2, n):
        sp, s0, s1 = c[t - 2], c[t - 1], c[t]
        ep, e0, e1 = e20[t - 2], e20[t - 1], e20[t]
        if None in (sp, s0, s1, ep, e0, e1):
            continue
        if side == "-":   # prereg 2026-10-09 4 C6-
            ev[t] = (sp < ep and s0 > sp and e0 * (1 - band) <= s0 < e0 and s1 < s0 and s1 < e1)
        else:             # C6+
            ev[t] = (sp > ep and s0 < sp and e0 < s0 <= e0 * (1 + band) and s1 > s0 and s1 > e1)
    return ev


def c4_events(ind, side):
    c = ind.s.c
    n = len(c)
    ev = [None] * n
    for t in range(HL_WINDOW + 1, n):
        w = c[t - HL_WINDOW - 1:t - 1]   # c[t-21 .. t-2]
        if any(x is None for x in w) or c[t] is None or c[t - 1] is None:
            continue
        if side == "-":
            B = max(w); ev[t] = c[t - 1] > B and c[t] < B
        else:
            B = min(w); ev[t] = c[t - 1] < B and c[t] > B
    return ev


def c2_events(ind, side):
    s = ind.s
    n = len(s.c)
    ev = [None] * n
    for t in range(1, n):
        e, a, pos, vol, avg = ind.ema20[t - 1], ind.atr[t - 1], ind.pos[t], s.v[t], ind.vol20[t]
        if None in (e, a, pos, vol, avg):
            continue
        if side == "-":
            if s.h[t] is None:
                continue
            ev[t] = s.h[t] >= e + C2_ATR_K * a and pos <= C2_POS_HI and vol >= avg * C2_VOL_K
        else:
            if s.l[t] is None:
                continue
            ev[t] = s.l[t] <= e - C2_ATR_K * a and pos >= C2_POS_LO and vol >= avg * C2_VOL_K
    return ev


def c7_events(ind, cal, facts, side):
    """C7- (and card good_news_drop): official good news (criterion (a)) then within 2 sessions close < pre-announcement close.
    C7+: company official bad news then within 2 sessions close > pre-announcement close. Facts = validated official facts.
    Base = the last regular-session close strictly before announced_at (builder F3 announced_at); the window is the next 2
    sessions after that base; only the first session that meets the condition is the event day (Judge 2026-10-15 3-5).
    Without a parseable announced_at the base is the session before event_session (announcement before that open)."""
    s = ind.s
    n = len(s.c)
    if facts is None:   # no valid research record: C7 cannot be judged (builder F1: "없으면 unk")
        return [None] * n
    ev = [False] * n
    for f in facts:
        good = f["direction"] == "+" and f.get("criterion_a") is True
        # C7+: only company figures for a guidance cut, dilution or a major contract cut (rule file 111)
        bad = f["direction"] == "-" and f.get("kind") in C7_BAD_KINDS
        if (side == "-" and not good) or (side == "+" and not bad):
            continue
        b = None
        try:
            at = dt.datetime.fromisoformat(str(f.get("announced_at")).replace("Z", "+00:00"))
            if at.tzinfo is None:
                raise ValueError
            for k in range(n):
                d = s.dates[k]
                # strictly before (Judge2 2026-10-15 4, first Judge 3-5 "announced_at 앞"): a 16:00:00 announcement
                # takes the previous close as its base
                if d in cal.close_at and dt.datetime.fromisoformat(cal.close_at[d]) < at:
                    b = k
                else:
                    break
        except Exception:
            d = f.get("event_session")
            b = s.index[d] - 1 if d in s.index else None
        if b is None or b < 0:
            continue
        pre = s.c[b]
        for t in range(b + 1, min(n, b + 1 + C7_SESSIONS)):
            if s.c[t] is None or pre is None:
                if ev[t] is False:
                    ev[t] = None
                break
            if (side == "-" and s.c[t] < pre) or (side == "+" and s.c[t] > pre):
                ev[t] = True
                break
    return ev

def c8_threshold(entry, mult):
    if entry and entry.get("c8") and entry["c8"].get("one_day") is not None:
        return float(entry["c8"]["one_day"])
    return {1: 0.10, 2: 0.15, 3: 0.20}.get(int(mult) if mult else 1, 0.10)


def compute_triggers(ind, cal, entry, active_card, facts, mult):
    """Returns {trigger_id: (group, side, source, states[])} for one symbol."""
    s = ind.s
    n = len(s.c)
    c, e10, e20, e50 = s.c, ind.ema10, ind.ema20, ind.ema50
    out = {}
    card = []
    replaced = set()
    if entry and active_card:
        for t in entry.get("card_triggers") or []:
            kind = t.get("kind")
            if kind in INFO_KINDS:
                continue
            if kind in CARD_KIND:
                grp, repl = CARD_KIND[kind]
                card.append(t)
                if repl:
                    replaced.add(grp)
    # common rules
    def c1(i, side):
        # "RSI14 ≥ 70 또는 종가 ≥ EMA20(t-1) + 2×ATR14(t-1)": three-valued OR (a True part decides even if the other is unknown)
        if i < 1:
            return None
        r = ind.rsi[i]
        a = None if r is None else (r >= C1_RSI_HI if side == "-" else r <= C1_RSI_LO)
        if None in (c[i], e20[i - 1], ind.atr[i - 1]):
            b = None
        else:
            b = c[i] >= e20[i - 1] + C1_ATR_K * ind.atr[i - 1] if side == "-" else c[i] <= e20[i - 1] - C1_ATR_K * ind.atr[i - 1]
        if a is True or b is True:
            return True
        if a is None or b is None:
            return None
        return False
    out["C1-"] = ("overheat", "-", "common", state_simple(n, lambda i: c1(i, "-")))
    out["C1+"] = ("oversold", "+", "common", state_simple(n, lambda i: c1(i, "+")))
    ev2m, ev2p = c2_events(ind, "-"), c2_events(ind, "+")
    out["C2-"] = ("overheat_fade", "-", "common", events_to_state(n, ev2m, ev2p))
    out["C2+"] = ("oversold_rebound", "+", "common", events_to_state(n, ev2p, ev2m))
    if "trend_break" not in replaced:
        out["C3-"] = ("trend_break", "-", "common", state_run(n, lambda i: _cmp(c[i], e20[i], "<"), 2, True))
    out["C3+"] = ("trend_recover", "+", "common", state_run(n, lambda i: _cmp(c[i], e20[i], ">"), 2, True))
    ev4m, ev4p = c4_events(ind, "-"), c4_events(ind, "+")
    out["C4-"] = ("false_breakout", "-", "common", events_to_state(n, ev4m, ev4p))
    out["C4+"] = ("false_breakdown", "+", "common", events_to_state(n, ev4p, ev4m))
    out["C5-"] = ("new_low", "-", "common", state_breakout(ind, "-"))
    if "new_high" not in replaced:
        out["C5+"] = ("new_high", "+", "common", state_breakout(ind, "+"))
    ev6m, ev6p = c6_events(ind, "-", C6_BAND), c6_events(ind, "+", C6_BAND)
    out["C6-"] = ("rebound_fail", "-", "common", events_to_state(n, ev6m, ev6p))
    if "pullback_rebound" not in replaced:
        out["C6+"] = ("pullback_rebound", "+", "common", events_to_state(n, ev6p, ev6m))
    ev7m, ev7p = c7_events(ind, cal, facts, "-"), c7_events(ind, cal, facts, "+")
    if "good_news_drop" not in replaced:
        out["C7-"] = ("good_news_drop", "-", "common", events_to_state(n, ev7m, ev7p))
    out["C7+"] = ("bad_news_rise", "+", "common", events_to_state(n, ev7p, ev7m))
    T = c8_threshold(entry if active_card else None, mult)
    if "crash_alert" not in replaced:
        out["C8-"] = ("crash_alert", "alert", "common", state_simple(n, lambda i: None if ind.ret[i] is None else ind.ret[i] <= -T))
    out["C8+"] = ("spike_alert", "alert", "common", state_simple(n, lambda i: None if ind.ret[i] is None else ind.ret[i] >= T))
    # card triggers
    for t in card:
        kind, p = t["kind"], t.get("params") or {}
        tid = t["id"]
        grp = CARD_KIND[kind][0]
        side = t.get("side")
        if kind == "ema_below":
            ema = {10: e10, 20: e20, 50: e50}[int(p.get("ema", 10))]
            st = state_simple(n, lambda i, ema=ema: _cmp(c[i], ema[i], "<"))
        elif kind == "ema20_below_twice":
            st = state_run(n, lambda i: _cmp(c[i], e20[i], "<"), 2, False)
        elif kind == "ema_below_unrecovered":
            ema = {10: e10, 20: e20, 50: e50}[int(p.get("ema", 50))]
            # "EMA50 아래 마감 후 2세션 안에 회복 못 함": the close day + 2 more sessions below (reading; 확인 필요)
            st = state_run(n, lambda i, ema=ema: _cmp(c[i], ema[i], "<"), int(p.get("sessions", 2)) + 1, False, True)
        elif kind == "new_high_hold":
            st = state_breakout(ind, "+")
        elif kind == "pullback_rebound":
            evp = c6_events(ind, "+", float(p.get("band", C6_BAND)))
            st = events_to_state(n, evp, ev6m)
        elif kind == "good_news_drop":
            st = events_to_state(n, ev7m, ev7p)
        elif kind == "drop_alert":
            one = fnum(p.get("one_day"))
            five = fnum(p.get("five_day"))
            def cond(i, one=one, five=five):
                r = ind.ret[i]
                if r is None:
                    return None
                hit = one is not None and r <= -one
                if five is not None and i >= 5 and c[i] is not None and c[i - 5]:
                    hit = hit or (c[i] / c[i - 5] - 1) <= -five
                return hit
            st = state_simple(n, cond)
            side = "alert"
        elif kind == "close_at_or_below":
            price = fnum(p.get("price"))
            st = state_simple(n, lambda i, price=price: None if c[i] is None or price is None else c[i] <= price)
            side = "alert"
        else:
            continue
        out[tid] = (grp, side, "card", st)
    return out


def group_states(trig, i):
    g = {}
    for tid, (grp, side, src, st) in trig.items():
        v = st[i] if 0 <= i < len(st) else "unk"
        cur = g.get(grp)
        rank = {"hit": 3, "pending": 2, "unk": 1, "none": 0}
        if cur is None or rank[v] > rank[cur[1]]:
            g[grp] = (side, v, cur[2] + [tid] if cur else [tid])
        else:
            g[grp] = (cur[0], cur[1], cur[2] + [tid])
    return g


# ---------------------------------------------------------------- registry / research record
def section_sha(path, heading):
    """sha256 of the card section (LF-normalized) from its heading line to the next heading of the same or higher level."""
    try:
        txt = open(path, encoding="utf-8").read().replace("\r\n", "\n")
    except Exception:
        return None
    lines = txt.split("\n")
    level = len(heading) - len(heading.lstrip("#"))
    start = None
    for k, ln in enumerate(lines):
        if ln == heading:
            start = k; break
    if start is None:
        return None
    end = len(lines)
    for k in range(start + 1, len(lines)):
        m = re.match(r"^(#+) ", lines[k])
        if m and len(m.group(1)) <= level:
            end = k; break
    body = "\n".join(lines[start:end])
    # trailing-newline variants are accepted (the registry transcription does not fix that detail; any content
    # change still changes all three hashes)
    core = body.rstrip("\n")
    return {hashlib.sha256(x.encode("utf-8")).hexdigest() for x in (body, core, core + "\n")}


def registry_status(repo, reg, sym, role_held, watch_members):
    e = (reg.get("symbols") or {}).get(sym)
    if e is None:
        return None, "NOCARD" if role_held else "NO_REGISTRY_ENTRY"
    path = os.path.join(repo, e["card_doc"])
    h = section_sha(path, e["card_section"])
    if h is None:
        return e, "CARD_SECTION_UNREADABLE"
    if e["section_sha256"] not in h:
        return e, "CARD_SECTION_CHANGED"
    if not role_held:
        m = watch_members.get(sym)
        if m is None or not str(m.get("cardStatus") or "").startswith("수락"):
            return e, "WATCH_CARD_NOT_ACCEPTED"
    elif not e.get("accepted"):
        return e, "NOT_ACCEPTED"
    return e, "OK"


def card_active(t_active, held, member):
    return {"held": held, "member": member, "held_or_member": held or member}.get(t_active, False)


def ny_sixteen(cal, d):
    """16:00 New York time on session date d (F3: written after the evaluation session 16:00 ET; also on early-close days)."""
    if d not in cal.index:
        return None
    return dt.datetime.fromisoformat(cal.close_at[d]).replace(hour=16, minute=0, second=0, microsecond=0)


def research_record_ok(rr, day, eval_session, decide_at, cal):
    """Own minimal check of the research-record contract (builder F3 fields); the core's own status is not used."""
    why = []
    if not isinstance(rr, dict):
        return False, ["MISSING"]
    if rr.get("schema_version") != "auto-core-research-record-1.0":
        why.append("SCHEMA_VERSION")
    if rr.get("record_day_kst") != day:
        why.append("RECORD_DAY")
    if rr.get("evaluation_session") != eval_session:
        why.append("EVALUATION_SESSION")
    try:
        w = dt.datetime.fromisoformat(rr.get("written_at"))
        if w.tzinfo is None:
            raise ValueError
        if w < ny_sixteen(cal, eval_session):
            why.append("WRITTEN_BEFORE_16ET")
        if decide_at is not None and w > decide_at:
            why.append("WRITTEN_AFTER_DECIDE")
    except Exception:
        why.append("WRITTEN_AT")
    if not isinstance(rr.get("earnings"), dict) or not isinstance(rr.get("official_facts"), list):
        why.append("FIELDS")
    if rr.get("order_authority") is not False or rr.get("quantity_authority") != "none":
        why.append("AUTHORITY")
    return not why, why


def validate_facts(rr, reg, cal, eval_session, decide_at, prev_seen, damage_domains=None):
    """F3 validation; returns (valid facts with 'new' flag, dropped).
    damage_domains (ev-rg1-hyper, only load_rrec1_records passes it): a root_thesis_damage fact whose host is not sec.gov
    or the symbol's official domain but matches one of these hosts goes through the same remaining checks and, if it
    passes, is kept with damage_source THESIS_DAMAGE_DOMAIN (R-REC1 RG1 only); every other caller keeps the default and
    drops it as DOMAIN, as before."""
    keep, dropped = [], []
    if not isinstance(rr, dict):
        return keep, dropped
    written = rr.get("written_at")
    try:
        w = dt.datetime.fromisoformat(written)
    except Exception:
        w = None
    ny_close = ny_sixteen(cal, eval_session)
    for f in rr.get("official_facts") or []:
        why = None
        url = str(f.get("source_url") or "")
        m = re.match(r"^https://([^/]+)", url)
        host = m.group(1).lower() if m else None
        sym = f.get("symbol")
        doms = [d.lower() for d in (((reg.get("symbols") or {}).get(sym) or {}).get("official_domains") or [])] + ["sec.gov"]
        # ev-rg1-hyper (Judge 1 item 6): official and marked before the chain, so a marked fact passes every check below
        official = host is not None and any(host == d or host.endswith("." + d) for d in doms)
        marked = host is not None and not official and f.get("root_thesis_damage") is True and any(
            host == d or host.endswith("." + d) for d in [str(x).lower() for x in damage_domains or []])
        if host is None:
            why = "URL"
        elif not official and not marked:
            why = "DOMAIN"
        elif f.get("source_kind") not in SOURCE_KINDS:
            why = "SOURCE_KIND"
        elif w is None or ny_close is None or w < ny_close:
            why = "WRITTEN_BEFORE_CLOSE"
        elif decide_at is not None and w > decide_at:
            why = "WRITTEN_AFTER_DECIDE"
        elif f.get("event_session") not in cal.index:
            why = "EVENT_SESSION"
        if why:
            dropped.append([f.get("fact_id"), why]); continue
        g = dict(f)
        g["direction"] = "-" if str(f.get("direction")) in ("-", "−") else ("+" if str(f.get("direction")) == "+" else None)
        if g["direction"] is None:
            dropped.append([f.get("fact_id"), "DIRECTION"]); continue
        prev = cal.prev_session(eval_session)
        g["new"] = f.get("event_session") == eval_session or (f.get("event_session") == prev and f.get("fact_id") not in prev_seen)
        if marked:
            g["damage_source"] = "THESIS_DAMAGE_DOMAIN"
        keep.append(g)
    return keep, dropped


COMMON_ID = re.compile(r"^C\d[+-]$")


def evidence(sym, side, groups_t, groups_prev, entry, reg_status, facts, trig_t=None):
    strong, weak, new_strong, new_kinds, ids = [], set(), [], [], []
    if side == "buy":
        if entry is not None and reg_status == "OK":
            for se in entry.get("static_evidence") or []:
                if se.get("direction") != "+":
                    continue
                if se.get("strength") == "strong":
                    strong.append(se["id"]); ids.append(se["id"])
                elif se.get("strength") == "weak":
                    weak.add("static:" + se.get("e1_kind", "?")); ids.append(se["id"])
        want = "+"
    else:
        want = "-"
    for f in facts or []:
        if f.get("symbol") != sym or not f.get("new"):
            continue
        if side == "buy" and f["direction"] == "+" and f.get("criterion_a") is True:
            strong.append(f["fact_id"]); new_strong.append(f["fact_id"])
        if side == "sell" and f["direction"] == "-" and f.get("kind") in SELL_FACT_KINDS:
            strong.append(f["fact_id"]); new_strong.append(f["fact_id"])
    card_kinds, card_defined, prev_unknown = set(), set(), []
    for grp, (gside, state, members) in groups_t.items():
        if gside != want or state != "hit":
            continue
        weak.add(grp)
        ids.extend(t for t in members)
        if any(not COMMON_ID.match(t) and (trig_t or {}).get(t) == "hit" for t in members):
            card_kinds.add(grp)
        if any(not COMMON_ID.match(t) for t in members):
            card_defined.add(grp)
        prev = groups_prev.get(grp)
        # "new" = hit today and none/pending in the previous session; an unknown previous state is not counted as
        # new (fail closed for buys: a condition that held through a data gap must not reopen the circuit)
        if prev is None or prev[1] == "unk":
            prev_unknown.append(grp)
        elif prev[1] != "hit":
            new_kinds.append(grp)
    official = [x for x in strong if x in set(new_strong)]
    return {"strong": sorted(strong), "weak_kinds": sorted(weak), "new_strong": sorted(new_strong),
            "new_kinds": sorted(new_kinds), "prev_unknown_kinds": sorted(prev_unknown),
            "card_kinds": sorted(card_kinds), "card_defined_kinds": sorted(card_defined), "side": side,
            "official": sorted(official),
            "static_strong": sorted(x for x in strong if x not in set(new_strong)),
            "basis_met": len(strong) >= 1 or len(weak) >= 2,
            "new_basis_met": len(new_strong) >= 1 or len(new_kinds) >= 2}


# ---------------------------------------------------------------- exposure (N and V)
def compute_V(series_by_sym, weights, through, bench="SOXX"):
    syms = [s for s, w in weights.items() if w]
    allsyms = syms + [bench]
    dates = None
    for s in allsyms:
        ser = series_by_sym.get(s)
        if ser is None:
            return None, "NO_SERIES:" + s
        ds = {d for d, c in zip(ser.dates, ser.c) if c is not None and d <= through}
        dates = ds if dates is None else dates & ds
    dates = sorted(dates or [])
    if not dates or dates[-1] != through:
        return None, "NO_CLOSE_AT_SESSION"
    # common window: last V_WINDOW returns, contiguous in every series
    use = dates[-(V_WINDOW + 1):]
    for s in allsyms:
        ser = series_by_sym[s]
        i0, i1 = ser.index[use[0]], ser.index[use[-1]]
        if i1 - i0 != len(use) - 1:
            return None, "GAP:" + s
    if len(use) - 1 < V_MIN:
        return None, "SHORT"
    port, br = [], []
    for k in range(1, len(use)):
        a, b = use[k - 1], use[k]
        r = 0.0
        for s in syms:
            ser = series_by_sym[s]
            r += weights[s] * (ser.c[ser.index[b]] / ser.c[ser.index[a]] - 1)
        port.append(r)
        bs = series_by_sym[bench]
        br.append(bs.c[bs.index[b]] / bs.c[bs.index[a]] - 1)
    sb = stdev(br)
    return (stdev(port) / sb if sb else None), "OK"


# ---------------------------------------------------------------- earnings blackout (p-earn r1, reference doc)
def earnings_reading(cal, rec, eval_session, next_session, generated_at):
    if eval_session not in cal.index or next_session not in cal.index:
        return False, "EARNINGS_WINDOW_NOT_CHECKABLE"
    if not isinstance(rec, dict):
        return False, "EARNINGS_DATE_UNVERIFIED"
    st = rec.get("status")
    if st == "VERIFIED":
        ann = rec.get("announcement_session")
        if ann not in cal.index:
            return False, "EARNINGS_WINDOW_NOT_CHECKABLE"
        start = cal.offset(ann, -2)
        end = ann if rec.get("timing") == "BEFORE_OPEN" else cal.offset(ann, 1)
        if start is None or end is None:
            return False, "EARNINGS_WINDOW_NOT_CHECKABLE"
        if end < next_session:
            return False, "EARNINGS_DATE_STALE"
        if start <= next_session <= end:
            return False, "EARNINGS_BLACKOUT"
        return True, "OUTSIDE_EARNINGS_BLACKOUT"
    if st == "NOT_ANNOUNCED":
        if "announcement_session" in rec or "timing" in rec:
            return False, "EARNINGS_RECORD_CONTRADICTORY"
        url = str(rec.get("source_url") or "")
        if rec.get("source_kind") not in SOURCE_KINDS or not re.match(r"^https://[^/]+", url):
            return False, "EARNINGS_CHECK_SOURCE_INVALID"
        try:
            ch = dt.datetime.fromisoformat(rec.get("checked_at"))
            if ch.tzinfo is None:
                raise ValueError
        except Exception:
            return False, "EARNINGS_CHECK_SOURCE_INVALID"
        if generated_at is None:
            return False, "EARNINGS_CHECK_GENERATED_AT_INVALID"
        if ch > generated_at:
            return False, "EARNINGS_CHECK_FUTURE_TIMESTAMP"
        sixteen = dt.datetime.fromisoformat(cal.close_at[eval_session]).replace(hour=16, minute=0, second=0)
        if ch < sixteen:
            return False, "EARNINGS_CHECK_STALE"
        return True, "EARNINGS_NOT_ANNOUNCED_CHECKED"
    return False, "EARNINGS_DATE_UNVERIFIED"


# ---------------------------------------------------------------- R-REC1
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KST_UTC9 = dt.timezone(dt.timedelta(hours=9))   # ev-rg1-hyper R0: fixed UTC+9 (same as KST below)


def strict_day(x):
    """YYYY-MM-DD only (ev-rg1-hyper R0: accepted.date and event_session), else None."""
    if not isinstance(x, str) or not DAY_RE.match(x):
        return None
    try:
        return dt.date.fromisoformat(x).isoformat()
    except ValueError:
        return None


def offset_moment(x):
    """ISO date-time with a required offset, trailing Z read as +00:00 (the research-record date-time rule), else None."""
    if not isinstance(x, str):
        return None
    try:
        m = dt.datetime.fromisoformat(x.replace("Z", "+00:00"))
    except ValueError:
        return None
    return m if m.tzinfo is not None else None


def rg1_release_day(f):
    """ev-rg1-hyper R0 rel(f) = max(event_session, KST date of announced_at); None if either cannot be read."""
    es, m = strict_day(f.get("event_session")), offset_moment(f.get("announced_at"))
    if es is None or m is None:
        return None
    kst_day = m.astimezone(KST_UTC9).date().isoformat()
    return kst_day if kst_day > es else es


def rg1_uncleared(facts, w0, d, accepted_on):
    """ev-rg1-hyper R0 U(d): sorted fact ids with w0 <= event_session <= d not cleared by the card acceptance
    (cleared only when rel(f) <= accepted_on <= d - no retroactive release)."""
    a = strict_day(accepted_on)
    ids = []
    for f in facts:
        es = str(f.get("event_session"))
        if es < w0 or es > d:
            continue
        rel_day = rg1_release_day(f)
        if a is not None and rel_day is not None and rel_day <= a and a <= d:
            continue
        ids.append(str(f.get("fact_id")))
    return sorted(ids)


def rrec1(cal, ser, ind, eval_session, sym, bench_rg2, ev3a_dates, records, accepted_on=None):
    """Returns dict(status ok|no|unk, open, event, rg{}) for one candidate symbol (buy side).
    records: {evaluation_session: [facts]} of research records written before the decide run (RG1 coverage, EV3b).
    RG1 record coverage follows user decision rrec-rg1-bootstrap B (2026-10-13, docs/claude/rrec-rg1-builder-prompt.md):
    sessions before the first record inside the 60-session window are left out; after it every session needs a record;
    no record in the window -> unk. EV4 removed (rrec-ev4 REMOVE 2026-10-19). EV3(b) gap (builder report R2-4 (b)): after the
    first research record in the window, a session without a valid record whose SOXX 1-day return is <= -1 sigma60 or
    unknown makes the gate unknown (status unk, open None, EV3B_RECORD_GAP).
    ev-rg1-hyper (decision a, event-strategy-2026-10-13.md 11-1): records here come from load_rrec1_records (damage facts
    only). A damage fact of the 60-session window keeps RG1 "no" until the card is accepted again (accepted_on = the
    registry accepted.date; R0 rg1_uncleared), whatever the event day, a new event, the time decay or a close; the time
    decay does not close on a day RG1 is "no"; closed or no event with an uncleared fact -> status "no", open False,
    rg RG1 "no", reason RG1_THESIS_DAMAGE:<ids>. EV3b uses only facts without damage_source (R5)."""
    sx, ix = ser.get("SOXX"), ind.get("SOXX")
    cs, ci = ser.get(sym), ind.get(sym)
    if sx is None or ix is None or eval_session not in sx.index:
        return {"status": "unk", "reason": "SOXX_MISSING"}
    if cs is None or ci is None or eval_session not in cs.index:
        return {"status": "unk", "reason": "CANDIDATE_MISSING"}
    t = sx.index[eval_session]
    lo = max(0, t - RREC_LOOKBACK + 1)
    window = set(sx.dates[lo:t + 1])
    cover = sorted(d for d in records if d in window)
    first = cover[0] if cover else None
    # ev-rg1-hyper G-1-1 (3): one version per fact_id, the first in record order (the core's load_research setdefault)
    facts, seen_ids = [], set()
    for d in cover:
        for f in records[d]:
            if f.get("root_thesis_damage") is True and f.get("fact_id") not in seen_ids:
                seen_ids.add(f.get("fact_id"))
                facts.append(f)
    w0 = sx.dates[lo]
    pending = rg1_uncleared(facts, w0, eval_session, accepted_on)

    def damage_block(res, rg):
        # ev-rg1-hyper R3: closed or no event in the window, an uncleared damage fact still blocks (open stays False)
        if pending:
            res.update(status="no", rg=dict(rg, RG1="no"), reason="RG1_THESIS_DAMAGE:" + ",".join(pending))
        return res

    if first is not None:
        gaps = []
        for k in range(lo, t + 1):
            d = sx.dates[k]
            if d < first or d in records:
                continue
            r, sg = ix.ret[k], ix.sigma[k]
            if r is None or sg is None or r <= -1 * sg:
                gaps.append(d)
        if gaps:
            return {"status": "unk", "open": None, "reason": "EV3B_RECORD_GAP:" + ",".join(gaps)}
    events = []
    for k in range(lo, t + 1):
        d = sx.dates[k]
        kinds = []
        r, sg = ix.ret[k], ix.sigma[k]
        if r is not None and sg is not None and r <= -2 * sg:
            kinds.append("EV1")
        if sg is not None and ix.hi20[k] is not None and sx.c[k] is not None and sx.c[k] <= ix.hi20[k] * (1 - 3 * sg):
            kinds.append("EV2")
        if d in ev3a_dates:
            kinds.append("EV3a")
        if r is not None and sg is not None and r <= -1 * sg and any(
                f.get("root_thesis_damage") is True and "damage_source" not in f and f.get("event_session") == d for f in facts):
            kinds.append("EV3b")
        if d in cs.index:
            j = cs.index[d]
            rr, ss = ci.ret[j], ci.sigma[j]
            if rr is not None and ss is not None and rr <= -2 * ss:
                kinds.append("EV5")
        if kinds:
            events.append((k, d, kinds))
    if not events:
        return damage_block({"status": "ok", "open": False, "events": []}, {})
    ke, de, kinds = events[-1]
    c0, l0 = sx.c[ke], sx.l[ke]
    if c0 is None or l0 is None:
        return {"status": "unk", "open": True, "reason": "C0_L0_MISSING", "event": de}
    bs = ser.get(bench_rg2) if bench_rg2 else sx
    bi = ind.get(bench_rg2) if bench_rg2 else ix

    def rg12(k):
        d = sx.dates[k]
        rg = {}
        damage = bool(rg1_uncleared(facts, w0, d, accepted_on))   # ev-rg1-hyper R1: not compared with the event day
        need = [x for x in sx.dates[ke + 1:k + 1] if first is not None and x >= first]
        if damage or k - ke < 2:
            rg["RG1"] = "no"
        elif first is None or any(x not in records for x in need):
            rg["RG1"] = "unk"
        else:
            rg["RG1"] = "ok"
        if bs is None or bi is None or d not in bs.index or d not in cs.index:
            rg["RG2"] = "unk"
        else:
            jb, jc = bs.index[d], cs.index[d]
            if None in (bs.c[jb], bi.ema50[jb], cs.c[jc], ci.ema50[jc]):
                rg["RG2"] = "unk"
            else:
                rg["RG2"] = "ok" if (bs.c[jb] >= bi.ema50[jb] and cs.c[jc] >= ci.ema50[jc]) else "no"
        return rg

    reset = ke
    closed_at = None
    final = None
    for k in range(ke + 1, t + 1):
        c, e50 = sx.c[k], ix.ema50[k]
        if c is None or e50 is None:
            final = {"RG1": "unk", "RG2": "unk", "RG3": "unk", "RG4": "unk"}   # data gap -> unknown (fail closed)
            break
        if c < l0 or c < e50:
            reset = k   # DS1: recovery clock restarts (RG3 from the start)
        rg = rg12(k)
        lows = [sx.l[j] for j in range(ke + 1, k + 1)]
        if any(x is None for x in lows):
            rg["RG3"] = "unk"
        else:
            rg["RG3"] = "ok" if (k - 1 > reset and sx.c[k] > c0 and sx.c[k - 1] > c0 and all(x >= l0 for x in lows)) else "no"
        r, sg = ix.ret[k], ix.sigma[k]
        five = [ix.ret[j] for j in range(k - 4, k + 1)]
        if r is None or sg is None or any(x is None for x in five):
            rg["RG4"] = "unk"
        else:
            rg["RG4"] = "ok" if (abs(r) <= 2 * sg and stdev(five) <= 1.5 * sg) else "no"
        final = rg
        # ev-rg1-hyper R2: no time-decay close on a day RG1 is "no" (unknown does not stop it)
        if all(v == "ok" for v in rg.values()) or (k - reset >= RREC_CLOSE_SESSIONS and rg["RG2"] == "ok" and rg["RG1"] != "no"):
            closed_at = sx.dates[k]
            break
    if closed_at is not None:
        return damage_block({"status": "ok", "open": False, "event": de, "kinds": kinds, "closed_at": closed_at}, final)
    if final is None:   # event on the evaluation session itself
        final = rg12(ke)
        final.update({"RG3": "no", "RG4": "no"})
    st = "ok" if all(v == "ok" for v in final.values()) else ("unk" if "unk" in final.values() else "no")
    return {"status": st, "open": True, "event": de, "kinds": kinds, "c0": c0, "l0": l0, "rg": final,
            "ds1": sx.dates[reset] if reset != ke else None, "rg1_first_record": first}


# ---------------------------------------------------------------- price and quantity (design 7-1, 7-2, 5)
def loc_mult(sigma, side):
    """m = 1 + 0.5 sigma (buy, 4 decimals down) / 1 - sigma (sell, 4 decimals up): design 9-1 2-2 "키움 기준종가 x m",
    T2 Judge J8 (Judge 2026-10-15 3-8)."""
    s = Decimal(repr(sigma))
    if side == "buy":
        return (Decimal(1) + Decimal(str(BUY_LOC_K)) * s).quantize(Decimal("0.0001"), rounding=ROUND_FLOOR)
    return (Decimal(1) - Decimal(str(SELL_LOC_K)) * s).quantize(Decimal("0.0001"), rounding=ROUND_CEILING)


def loc_price(ref, sigma, side):
    x = Decimal(repr(ref)) * loc_mult(sigma, side)
    if side == "buy":
        return (x * 100).to_integral_value(rounding=ROUND_FLOOR) / 100
    return (x * 100).to_integral_value(rounding=ROUND_CEILING) / 100


CENT = Decimal("0.01")


def cents(x):
    return Decimal(repr(float(x))).quantize(CENT, rounding=ROUND_HALF_UP)


def regret_choice(delta, ref, up, down, r_max, equity, side, cand=None):
    """design 5 / builder F5: actions {0,1/3,1/2,1}; regret per scenario column vs the best row of that column; row max
    regret = max over the columns; choose r_max if its max regret <= 3% equity, else the smallest max regret at or below
    r_max (ties -> smaller). Amounts are compared in cents (Judge 2026-10-15 S7).
    Buy columns: up / down. Sell columns (redeployment bridge, Judge S1/S6): {up, down} x {cash, best candidate}; the
    candidate columns invest the whole sale proceeds q x ref in the candidate (pair scenario: both at their 90th pct /
    both at their 10th pct, design 5 "교체 쌍은 두 종목을 함께"); without a candidate only the two cash columns."""
    cols = [("up", up, None), ("down", down, None)]
    if side != "buy" and cand is not None:
        cols += [("cand_up", up, cand[0]), ("cand_down", down, cand[1])]
    rows = []
    for a, lab in STEPS:
        sn, sd = STEP_FRAC[lab]
        q = int(delta) * sn // sd
        row = {"r": lab, "a": a, "qty": q, "pnl": {}}
        for name, own, cr in cols:
            v = q * ref * own if side == "buy" else (-q * ref * own + (q * ref * cr if cr is not None else 0.0))
            row["pnl"][name] = cents(v)
        rows.append(row)
    best = {name: max(x["pnl"][name] for x in rows) for name, _, _ in cols}
    for x in rows:
        x["regret"] = {name: best[name] - x["pnl"][name] for name, _, _ in cols}
        x["max_regret"] = max(x["regret"].values())
        x["regret_up"], x["regret_down"] = x["regret"]["up"], x["regret"]["down"]
    budget = (Decimal(repr(float(equity))) * Decimal(str(REGRET_BUDGET))).quantize(CENT, rounding=ROUND_HALF_UP)
    feas = [x for x in rows if x["a"] <= r_max]
    top = max(feas, key=lambda x: x["a"])
    if top["max_regret"] <= budget:
        pick = top
    else:
        pick = min(feas, key=lambda x: (x["max_regret"], x["a"]))
    return pick, rows

def stress_returns(ind, i, n_sessions=SIGMA_WINDOW):
    """5-session returns ending at each of the last 60 sessions (reading: overlapping, ending t-59..t; 확인 필요)."""
    c = ind.s.c
    xs = []
    for k in range(i - n_sessions + 1, i + 1):
        if k - 5 < 0 or c[k] is None or c[k - 5] is None:
            return None
        xs.append(c[k] / c[k - 5] - 1)
    return quantile_linear(xs, 0.9), quantile_linear(xs, 0.1), xs


# ---------------------------------------------------------------- context build for one session
class Context:
    def __init__(self, repo, cal, through, symbols, corp):
        self.repo, self.cal, self.through = repo, cal, through
        self.ser, self.ind = {}, {}
        for s in symbols:
            ser = Series(repo, cal, s, through, corp)
            self.ser[s] = ser
            self.ind[s] = Ind(ser) if ser.dates else None


def circuit_for_session(ctx, eval_session, held, members, reg, watch_members, facts, s7_add, s7_reduce, mult_of, c7_facts=None):
    """Circuit open set (design 1 (1), builder D5/F4). Returns (open list, per-symbol detail)."""
    out, detail = [], {}
    universe = sorted(set(held) | set(members))
    for sym in universe:
        ind = ctx.ind.get(sym)
        is_held = sym in held
        is_member = sym in members
        entry, rstat = registry_status(ctx.repo, reg, sym, is_held, watch_members)
        d = {"role": "held" if is_held else "watch", "registry": rstat}
        detail[sym] = d
        if ind is None or eval_session not in ind.s.index:
            d["status"] = "NO_DATA"; continue
        if ind.s.split_suspected:
            d["status"] = "SPLIT_SUSPECTED"; continue
        i = ind.s.index[eval_session]
        src7 = facts if c7_facts is None else c7_facts
        sym_facts = None if src7 is None else [f for f in src7 if f.get("symbol") == sym]
        # card definitions apply only while the symbol is held / a member (registry active_when; rule file 3) "카드 정의는
        # 그 종목이 보유 또는 members일 때만"); an inactive card leaves the common rules in place
        active_entry = None
        if entry is not None:
            active_entry = dict(entry)
            active_entry["card_triggers"] = [t for t in entry.get("card_triggers") or []
                                             if card_active(t.get("active_when"), is_held, is_member)]
            if not active_entry["card_triggers"]:
                active_entry["c8"] = None
        trig = compute_triggers(ind, ctx.cal, active_entry, active_entry is not None, sym_facts, mult_of(sym))
        g_t, g_p = group_states(trig, i), group_states(trig, i - 1)
        d["status"] = "OK"
        d["triggers"] = {tid: v[3][i] for tid, v in sorted(trig.items())}
        d["indicators"] = ind.snapshot(i)
        ev_b = evidence(sym, "buy", g_t, g_p, entry, rstat, facts, d["triggers"])
        d["buy"] = ev_b
        buy_open = ev_b["new_basis_met"] or (sym in s7_add and ev_b["basis_met"])
        if buy_open:
            out.append({"symbol": sym, "side": "buy", "trigger": "NEW_EVIDENCE" if ev_b["new_basis_met"] else "S7_ADD"})
        if is_held:
            ev_s = evidence(sym, "sell", g_t, g_p, entry, rstat, facts, d["triggers"])
            d["sell"] = ev_s
            card_goal = entry is not None and (entry.get("card_action") == "EXIT" or
                                               (entry.get("card_action") == "TRIM" and entry.get("trim_target_weight") is not None))
            target = sym in s7_reduce or card_goal
            d["sell_target"] = target
            if target and ev_s["basis_met"]:
                out.append({"symbol": sym, "side": "sell", "trigger": "S7_REDUCE" if sym in s7_reduce else "CARD_" + str(entry.get("card_action"))})
    return out, detail


# ---------------------------------------------------------------- live check
KST = dt.timezone(dt.timedelta(hours=9))
CHECK_DEADLINE_KST = (8, 40)   # prereg 1 C1: decide result not there at 08:40 -> NOT_CHECKED
CLASSIFIED = {"filled", "partial", "unfilled", "not_entered", "changed"}   # builder F6 outcome states


def rel(repo, p):
    return os.path.join(repo, p) if p and not os.path.isabs(p) else p


def canon_inputs(day):
    a = "workspace/outputs/auto-core/%s/" % day
    return {"t1_result": a + "result.json", "broker_snapshot": a + "kiwoom_broker_snapshot.shadow.json",
            "reconcile": a + "reconcile.json", "registry": "docs/claude/card-evidence-registry.json",
            "research_record": "workspace/outputs/research-records/%s/research-record.json" % day,
            "watchlist": "docs/claude/watchlist-registry.json", "state": "stock-strategy-system/portfolio_state.json",
            "alert_policy": "stock-strategy-system/alert_policy.json",
            "recovery_gate_doc": "docs/claude/recovery-gate-R-REC1-2026-10-09.md"}


def symbols_of_list(xs):
    out = set()
    for x in xs or []:
        if isinstance(x, dict):
            s = x.get("symbol") or x.get("ticker")
            if s:
                out.add(s)
        elif isinstance(x, str):
            out.add(x)
    return out


def require(cond, why, bad):
    if not cond:
        bad.append(why)


def s7_schema(s7):
    bad = []
    if not isinstance(s7, dict):
        return ["S7_MISSING"]
    rec = s7.get("recommendations")
    require(isinstance(rec, dict) and isinstance(rec.get("add"), list) and isinstance(rec.get("reduce"), list), "recommendations.add/reduce", bad)
    require(isinstance(s7.get("pauses"), dict) and "add_recommendations" in s7["pauses"] and "new_buy_recommendations" in s7["pauses"], "pauses", bad)
    require(isinstance((s7.get("single_stock_cap") or {}).get("breaches"), list), "single_stock_cap.breaches", bad)
    require(isinstance(s7.get("peak_reviews"), list) and all(isinstance(p, dict) and "pause_add_recommendations" in p and "open_events" in p for p in s7.get("peak_reviews") or []), "peak_reviews", bad)
    require(isinstance(s7.get("exposure"), dict) and "effective" in s7["exposure"], "exposure.effective", bad)
    require(isinstance(s7.get("equity"), dict) and "closing_equity_usd" in s7["equity"], "equity", bad)
    require(isinstance(s7.get("fail_closed"), dict) and "active" in s7["fail_closed"], "fail_closed", bad)
    require(isinstance((s7.get("review_lines") or {}).get("lines"), list) and all(isinstance(l, dict) and "line_id" in l and "triggered_in_current_drawdown" in l for l in (s7.get("review_lines") or {}).get("lines") or []), "review_lines.lines", bad)
    require(all(isinstance(b, dict) and "symbol" in b and "block_new_buy" in b for b in (s7.get("single_stock_cap") or {}).get("breaches") or []), "single_stock_cap.breaches[]", bad)
    require(all(isinstance((s7.get("pauses") or {}).get(k), dict) and "paused" in s7["pauses"][k] for k in ("add_recommendations", "new_buy_recommendations")), "pauses.*.paused", bad)
    require("evaluation_session" in s7, "evaluation_session", bad)
    return bad


def snap_schema(snap):
    bad = []
    require(isinstance(snap.get("holdings"), list) and all("ticker" in h and "held_quantity" in h for h in snap.get("holdings") or []), "holdings", bad)
    require(isinstance(snap.get("cash"), dict) and "order_available_cash" in snap["cash"] and "foreign_currency_deposit" in snap["cash"], "cash.order_available_cash/foreign_currency_deposit", bad)
    require(isinstance(snap.get("open_orders"), list), "open_orders", bad)
    return bad


def select_s7(repo, day, ev, decide_at):
    """Independent choice: newest S7 review of this decide day for the evaluation session written before decision.json was
    written (decide re-runs S7 inside its run, so the review is later than decision.generated_at = run start)."""
    best = None
    for p in sorted(glob.glob(os.path.join(repo, "workspace/outputs/auto-core", day, "s7", ev, "portfolio-exposure-review.*.json"))):
        try:
            g = dt.datetime.fromisoformat(str(load_json(p).get("inputs", {}).get("generated_at")).replace("Z", "+00:00"))
        except Exception:
            continue
        if decide_at is None or g <= decide_at:
            if best is None or g > best[0]:
                best = (g, p)
    return best[1] if best else None


def load_research_history(repo, day, decide_at, reg, cal):
    """{evaluation_session: [validated facts]} from research records written before the decide run (RG1 coverage, EV3b)."""
    out, files = {}, []
    for p in sorted(glob.glob(os.path.join(repo, "workspace/outputs/research-records/*/research-record.json"))):
        try:
            r = load_json(p)
        except Exception:
            continue
        rd, ev = r.get("record_day_kst"), r.get("evaluation_session")
        if not isinstance(rd, str) or rd > day or ev not in cal.index:
            continue
        ok, _ = research_record_ok(r, rd, ev, decide_at, cal)
        if not ok:
            continue
        facts, _ = validate_facts(r, reg, cal, ev, decide_at, [])
        out[ev] = facts
        files.append([os.path.relpath(p, repo), sha256_file(p)])
    return out, files


def load_rrec1_records(repo, day, decide_at, reg, cal):
    """ev-rg1-hyper G-1-1: {evaluation_session: [root-thesis-damage facts]} for rrec1 only (C7 keeps load_research_history).
    (1) a record with any fact whose announced_at is missing or has no offset fails the research-record schema in the core
    (auto_core_inputs.check_record) and counts for nothing here (not as coverage either); (2) a damage fact counts only with
    announced_at <= the decide run, event_session <= the record's evaluation session and summary_ko <= 200 characters
    (check_record); records of one evaluation session are joined in record-day order (rrec1 keeps the first version of a
    fact_id). Thesis-damage-domain facts (registry thesis_damage_domains) come after the record's other facts, marked."""
    out = {}
    domains = reg.get("thesis_damage_domains") or []
    for p in sorted(glob.glob(os.path.join(repo, "workspace/outputs/research-records/*/research-record.json"))):
        try:
            r = load_json(p)
        except Exception:
            continue
        rd, ev = r.get("record_day_kst"), r.get("evaluation_session")
        if not isinstance(rd, str) or rd > day or ev not in cal.index:
            continue
        ok, _ = research_record_ok(r, rd, ev, decide_at, cal)
        if not ok:
            continue
        if any(not isinstance(f, dict) or offset_moment(f.get("announced_at")) is None for f in r.get("official_facts") or []):
            continue
        facts, _ = validate_facts(r, reg, cal, ev, decide_at, [], damage_domains=domains)
        kept = [f for f in facts if f.get("root_thesis_damage") is True
                and (decide_at is None or offset_moment(f.get("announced_at")) <= decide_at)
                and str(f.get("event_session")) <= ev and len(str(f.get("summary_ko") or "")) <= 200]
        out.setdefault(ev, []).extend([f for f in kept if "damage_source" not in f] + [f for f in kept if "damage_source" in f])
    return out


def mult_fn(policy):
    mults = policy.get("nominal_multipliers") or {}

    def f(s):
        if s in mults:
            return mults[s]
        return 1 if s in MULT_ONE_ASSUMED else None   # rule file 99: other unregistered -> N 확인 필요
    return f


def cmd_check(args):
    repo, day = args.repo, args.day
    res = {"schema": "t2rc-check-1.0", "oracle_version": ORACLE_VERSION, "oracle_sha256": sha256_lf(os.path.abspath(__file__)),
           "day_kst": day, "verdict": None, "counts_for_c1": False,
           "order_authority": False, "quantity_authority": "none", "execution_quantity": None}
    hist = bool(getattr(args, "ignore_input_sha", False))
    dpath = os.path.join(repo, "workspace/outputs/auto-core", day, "decision.json")
    if not os.path.exists(dpath):
        res.update(verdict="NOT_CHECKED", reason="DECISION_MISSING")
        return finish(res, args)
    dec = load_json(dpath)
    res["decision_sha256"] = sha256_file(dpath)
    res["decision"] = {k: dec.get(k) for k in ("evaluation_session", "buy_session", "status", "reasons", "mode", "decision_mode", "generated_at", "commit_sha")}
    try:
        decide_at = dt.datetime.fromisoformat(str(dec.get("generated_at")).replace("Z", "+00:00"))
    except Exception:
        decide_at = None
    notes = []
    if decide_at is None:
        res.update(verdict="NOT_CHECKED", reason="DECISION_GENERATED_AT_INVALID")
        return finish(res, args)
    deadline = dt.datetime.fromisoformat(day + "T%02d:%02d:00+09:00" % CHECK_DEADLINE_KST)
    result_at = max(decide_at, dt.datetime.fromtimestamp(os.path.getmtime(dpath), dt.timezone.utc))
    res["decision"]["result_written_at"] = result_at.isoformat()
    if result_at > deadline:
        notes.append("DECIDE_AFTER_0840")
    if not dec.get("symbols") or "candidates" not in dec:
        res.update(verdict="NOT_CHECKED", reason="DECIDE_ENDED_BEFORE_F1")
        return finish(res, args)
    cal = Calendar(repo)
    I = dec.get("inputs") or {}
    canon = canon_inputs(day)
    path_bad, sha_bad = [], []
    for k, cp in canon.items():
        v = I.get(k) or {}
        if k == "research_record" and not v.get("path"):
            # core ran without a record: the canonical file must be absent or written after the decide run
            p = rel(repo, cp)
            if os.path.exists(p):
                try:
                    w = dt.datetime.fromisoformat(load_json(p).get("written_at"))
                    if w <= decide_at:
                        path_bad.append(k)
                except Exception:
                    sha_bad.append(k)
            continue
        if str(v.get("path") or "").replace("\\", "/") != cp:
            path_bad.append(k); continue
        if not v.get("sha256"):
            sha_bad.append(k); continue
        p = rel(repo, cp)
        if not os.path.exists(p) or sha256_file(p) != v["sha256"]:
            sha_bad.append(k)
    if (I.get("calendar") or {}).get("sha256") != cal.hash:
        sha_bad.append("calendar")
    ev = dec["evaluation_session"]
    s7_path = select_s7(repo, day, ev, dt.datetime.fromtimestamp(os.path.getmtime(dpath), dt.timezone.utc))
    core_s7 = str((I.get("s7_review") or {}).get("path") or "").replace("\\", "/")
    if s7_path is None or os.path.relpath(s7_path, repo).replace("\\", "/") != core_s7:
        path_bad.append("s7_review")
    elif (I.get("s7_review") or {}).get("sha256") and sha256_file(s7_path) != I["s7_review"]["sha256"]:
        sha_bad.append("s7_review")
    res["input_sha_mismatch"], res["input_path_mismatch"] = sha_bad, path_bad
    res["historical_self_check"] = bool(hist and (sha_bad or notes))
    if notes and not hist:
        res.update(verdict="NOT_CHECKED", reason=",".join(notes))
        return finish(res, args)
    if sha_bad and not hist:
        res.update(verdict="NOT_CHECKED", reason="INPUT_SHA_MISMATCH")
        return finish(res, args)
    snap = load_json(rel(repo, canon["broker_snapshot"]))
    s7 = load_json(s7_path) if s7_path else None
    schema_bad = snap_schema(snap) + s7_schema(s7)
    if schema_bad:
        res.update(verdict="NOT_CHECKED", reason="INPUT_SCHEMA:" + ",".join(schema_bad))
        return finish(res, args)
    reg = load_json(rel(repo, canon["registry"]))
    wl = load_json(rel(repo, canon["watchlist"]))
    policy = load_json(rel(repo, canon["alert_policy"]))["portfolio_exposure_policy"]
    state = load_json(rel(repo, canon["state"]))
    rr = None
    if (I.get("research_record") or {}).get("path"):
        rr = load_json(rel(repo, canon["research_record"]))
    rr_ok, rr_why = research_record_ok(rr, day, ev, decide_at, cal)
    res["research_record"] = {"ok": rr_ok, "reasons": rr_why, "core_status": (I.get("research_record") or {}).get("status")}
    corp_p = os.path.join(repo, "workspace/outputs/regular-session-closes/corporate-actions.json")
    corp = (load_json(corp_p).get("actions") or []) if os.path.exists(corp_p) else []
    held = {h["ticker"]: h.get("held_quantity") for h in snap["holdings"] if (h.get("held_quantity") or 0) > 0}
    wm = {m["code"]: m for m in wl.get("members") or []}
    members = [c for c in wm if c not in held]
    prev_dec = None
    prev_day = None
    for pp in sorted(glob.glob(os.path.join(repo, "workspace/outputs/auto-core", "20??-??-??", "decision.json"))):
        dd = os.path.basename(os.path.dirname(pp))
        if dd < day:
            prev_day = dd   # newest decide day before today, found by the oracle (not the core's pointer)
    if prev_day:
        prev_dec = load_json(os.path.join(repo, "workspace/outputs/auto-core", prev_day, "decision.json"))
    res["previous_decision"] = {"oracle": prev_day, "core": (I.get("previous_decision") or {}).get("run_day_kst")}
    prev_seen = [x.get("fact_id") if isinstance(x, dict) else x for x in ((prev_dec or {}).get("facts_seen") or [])]
    facts = None
    dropped = []
    if rr_ok:
        facts, dropped = validate_facts(rr, reg, cal, ev, decide_at, prev_seen)
    res["facts"] = {"valid": None if facts is None else [f.get("fact_id") for f in facts], "dropped": dropped}
    history, hist_files = load_research_history(repo, day, decide_at, reg, cal)
    s7_add = symbols_of_list(s7["recommendations"]["add"])
    s7_reduce = symbols_of_list(s7["recommendations"]["reduce"])
    mult_of = mult_fn(policy)
    syms = sorted(set(held) | set(members) | {"SOXX", "GRID"})
    ctx = Context(repo, cal, ev, syms, corp)
    c7_facts = None
    if facts is not None:
        seen = {f.get("fact_id") for f in facts}
        c7_facts = list(facts)
        for sess in sorted(history)[-C7_RECORD_DAYS:]:
            for f in history[sess] or []:
                if f.get("fact_id") not in seen:
                    seen.add(f.get("fact_id")); c7_facts.append(f)
    opened, detail = circuit_for_session(ctx, ev, set(held), set(members), reg, wm, facts, s7_add, s7_reduce,
                                         lambda s: mult_of(s) or 1, c7_facts)
    core = {(c["symbol"], c["side"]) for c in dec.get("candidates") or []}
    mine = {(c["symbol"], c["side"]) for c in opened}
    res["c1"] = {"oracle_open": sorted([list(x) for x in mine]), "core_candidates": sorted([list(x) for x in core]),
                 "missing_in_core": sorted([list(x) for x in mine - core]), "extra_in_core": sorted([list(x) for x in core - mine]),
                 "match": mine == core and not path_bad,
                 "prev_unknown_kinds": {s: d.get("buy", {}).get("prev_unknown_kinds") for s, d in detail.items() if d.get("buy", {}).get("prev_unknown_kinds")}}
    res["diagnostics"] = diagnostics(dec, detail, ctx)
    env = {"ctx": ctx, "dec": dec, "snap": snap, "s7": s7, "policy": policy, "rr": rr if rr_ok else None, "reg": reg, "wm": wm,
           "facts": facts, "held": held, "members": members, "detail": detail, "cal": cal, "mult_of": mult_of,
           "decide_at": decide_at, "history": history, "state": state, "prev_dec": prev_dec, "repo": repo, "open": mine, "day": day,
           "rrec_records": load_rrec1_records(repo, day, decide_at, reg, cal)}
    cfg_p = os.path.join(repo, "workspace/policies/auto_core.json")
    env["core_cfg"] = load_json(cfg_p) if os.path.exists(cfg_p) else {}
    env["exposure"] = exposure_check(env)
    res["exposure"] = env["exposure"]
    req_rows, req_diffs = {}, []
    for sym, d in detail.items():
        if d.get("status") != "OK":
            continue
        mine_r = buy_requirements(env, sym)
        req_rows[sym] = mine_r
        core_row = next((r for r in dec.get("buy_requirements") or [] if r.get("code") == sym), None)
        for k in range(5):
            cs = core_row["c"][k]["s"] if core_row else None
            if cs != mine_r[k]:
                req_diffs.append([sym, "req%d" % (k + 1), cs, mine_r[k]])
    res["requirements"] = {"oracle": req_rows, "diffs": req_diffs}
    # tickets (prereg C2 / C3 items) and leaks (an oracle ticket that the core did not issue)
    tickets = dec.get("tickets") or []
    res["tickets"] = [ticket_check(env, t) for t in tickets]
    issued = {(t.get("ticker"), t.get("side")) for t in tickets}
    leaks = []
    for (sym, side) in sorted(mine - issued):
        chk = ticket_check(env, {"ticker": sym, "side": side})
        if chk.get("should_exist") and (chk["items"].get("qty") or {}).get("oracle", 0) > 0:
            leaks.append({"symbol": sym, "side": side, "qty": chk["items"]["qty"]["oracle"], "price": chk["items"]["price"]["oracle"]})
    res["ticket_leaks"] = leaks
    res["c2_item_match"] = bool(tickets) and all(x.get("match") for x in res["tickets"])
    res["circuit_detail"] = {s: {k: v for k, v in d.items() if k in ("role", "registry", "status", "buy", "sell", "sell_target")} for s, d in detail.items()}
    pages = []
    for s in syms:
        for p in sorted(glob.glob(os.path.join(repo, "workspace/outputs/regular-session-closes/pages", s, "*.json"))):
            pages.append(sha256_file(p))
    res["read_files"] = {"pages_count": len(pages), "pages_combined_sha256": hashlib.sha256("".join(pages).encode()).hexdigest(),
                         "corporate_actions": sha256_file(corp_p) if os.path.exists(corp_p) else None,
                         "s7_review": [os.path.relpath(s7_path, repo), sha256_file(s7_path)] if s7_path else None,
                         "previous_decision": sha256_file(os.path.join(repo, "workspace/outputs/auto-core", prev_day, "decision.json")) if prev_dec else None,
                         "research_history": hist_files,
                         "m6": [[os.path.relpath(p, repo), sha256_file(p)] for p in sorted(glob.glob(os.path.join(repo, "docs/claude/m6-relative-comparison-7stock*.md")))]}
    ok = res["c1"]["match"] and all(x.get("match") for x in res["tickets"]) and not leaks
    res["verdict"] = "MATCH" if ok else "MISMATCH"
    # C1 guard (Judge 2026-10-15 5): a symbol the oracle could not evaluate (no data, split suspected, no close on the
    # evaluation session) while the core evaluated it is not a confirmed "no circuit" -> the session is NOT_CHECKED
    gap = []
    for sym, d in sorted(detail.items()):
        cd = (dec.get("symbols") or {}).get(sym) or {}
        mi, ci = d.get("indicators") or {}, cd.get("indicators") or {}
        keys = ("close", "ema20", "sigma60")
        mine_ok = d.get("status") == "OK" and all(mi.get(k) is not None for k in keys if ci.get(k) is not None)
        core_ok = cd.get("status") == "OK" and ci.get("close") is not None
        if not mine_ok and core_ok:
            gap.append(sym)
    apply_gap_guard(res, gap)
    if hist and (sha_bad or notes):
        res["verdict"] = "INFO_" + res["verdict"]
        res["note"] = "self-check only, not a C1 session: " + ",".join(sha_bad + notes)
    res["counts_for_c1"] = res["verdict"] in ("MATCH", "MISMATCH") and dec.get("decision_mode") == "compare"
    res["c3"] = c3_record(repo, day, dec, res["tickets"], leaks)
    return finish(res, args)


def apply_gap_guard(res, gap):
    """C1 guard (Judge 2026-10-15 5, Judge2 2): with a gap a MATCH is not a confirmed "no circuit" -> NOT_CHECKED; a
    MISMATCH stays a MISMATCH (it counts for C1 and is pushed) with ORACLE_DATA_GAP added to the reason. Either way no
    ticket counts as matched (C2 items, C3)."""
    if not gap:
        return
    tag = "ORACLE_DATA_GAP:" + ",".join(gap)
    if res.get("verdict") == "MATCH":
        res["verdict"] = "NOT_CHECKED"
        res["reason"] = tag
    else:
        res["reason"] = (res["reason"] + ";" + tag) if res.get("reason") else tag
    res["c2_item_match"] = False
    for x in res.get("tickets") or []:
        x["match"] = False


def c3_record(repo, day, dec, checked, leaks=()):
    """Prereg C3 / M3: after T2 is on, the first ticket of each direction needs a recorded match before the alert may send
    the entry guide. confirmed_before = an earlier apply-mode check of this oracle recorded a matched ticket of that side.
    entry_allowed = no ticket of that side today, or confirmed before, or every ticket of that side today matched.
    The 08:50 alert reads only this block (missing or stale file -> entry not allowed)."""
    out = {}
    prev = []
    for p in sorted(glob.glob(os.path.join(repo, "workspace/outputs/auto-core", "20??-??-??", "t2rc-check.json"))):
        dd = os.path.basename(os.path.dirname(p))
        if dd >= day:
            continue
        try:
            r = load_json(p)
        except Exception:
            continue
        # count only a real result of this same calculator (not a self-check, not NOT_CHECKED or ERROR)
        if ((r.get("decision") or {}).get("decision_mode") == "apply" and r.get("day_kst") == dd
                and r.get("verdict") in ("MATCH", "MISMATCH") and not r.get("note") and not r.get("historical_self_check")
                and r.get("oracle_sha256") == sha256_lf(os.path.abspath(__file__))):
            prev.append((dd, r))
    for side in ("buy", "sell"):
        today = [x for x in checked if x.get("side") == side]
        before = [dd for dd, r in prev if (((r.get("c3") or {}).get(side) or {}).get("today_all_match") is True
                                           and any(t.get("side") == side and t.get("match") for t in r.get("tickets") or []))]
        # a day with a leak of that side (the oracle would have issued a ticket the core did not) does not confirm it
        all_match = bool(today) and all(x.get("match") for x in today) and not any(l.get("side") == side for l in leaks)
        out[side] = {"tickets_today": len(today), "tickets": [x.get("ticket_id") for x in today],
                     "matched": [x.get("ticket_id") for x in today if x.get("match")],
                     "today_all_match": all_match, "confirmed_before": before[:1],
                     "entry_allowed": (not today) or bool(before) or all_match}
    out["decision_mode"] = dec.get("decision_mode")
    return out


def diagnostics(dec, detail, ctx):
    diffs = []
    for sym, d in detail.items():
        cd = (dec.get("symbols") or {}).get(sym)
        if cd is None:
            diffs.append([sym, "symbol", "absent_in_core", d.get("status")]); continue
        if d.get("status") != "OK":
            diffs.append([sym, "status", cd.get("status"), d.get("status")]); continue
        ci = cd.get("indicators") or {}
        for k, v in (d.get("indicators") or {}).items():
            cv = ci.get(k)
            if isinstance(v, (int, float)) and isinstance(cv, (int, float)):
                if abs(v - cv) > 1e-6 * max(1.0, abs(cv)):
                    diffs.append([sym, "ind:" + k, cv, v])
            elif (v is None) != (cv is None) and k != "session":
                diffs.append([sym, "ind:" + k, cv, v])
        cst = {t["id"]: t.get("state") for t in cd.get("triggers") or []}
        for tid, st in (d.get("triggers") or {}).items():
            c = cst.get(tid)
            if c is None:
                diffs.append([sym, "trig:" + tid, "absent_in_core", st])
            elif c != st:
                diffs.append([sym, "trig:" + tid, c, st])
        for tid in cst:
            if tid not in (d.get("triggers") or {}) and cst[tid] not in ("info",):
                diffs.append([sym, "trig:" + tid, cst[tid], "absent_in_oracle"])
        ce = (dec.get("evidence") or {}).get(sym) or {}
        for side in ("buy", "sell"):
            mine, theirs = d.get(side), ce.get(side)
            if mine and theirs:
                for k in ("basis_met", "new_basis_met"):
                    if bool(mine[k]) != bool(theirs.get(k)):
                        diffs.append([sym, side + ":" + k, theirs.get(k), mine[k]])
    return {"n": len(diffs), "items": diffs[:200]}


def weights_now(env):
    ctx, ev, s7 = env["ctx"], env["dec"]["evaluation_session"], env["s7"]
    eq = fnum(s7["equity"]["closing_equity_usd"])
    w = {}
    for sym, q in env["held"].items():
        ser = ctx.ser.get(sym)
        if ser is None or ev not in ser.index or ser.raw_c[ser.index[ev]] is None:
            return None, eq
        w[sym] = q * ser.raw_c[ser.index[ev]] / eq
    return w, eq


def equity_cash_t2(cash, holdings):
    """(cash, basis) of the total assets behind V6 / EV4 - user decision t2-equity-cash (2026-10-13 09:21,
    docs/claude/redesign-t2-merge-decision-2026-10-12.md:90): Kiwoom order-available cash when T1's one cash check passes,
    otherwise the smallest known of order-available / withdrawable / foreign-currency deposit (never raises the total).
    The check, as the decision states it: order-available minus withdrawable is not below -$1, and above +$1 only when
    one holdings row shows a filled, unsettled sale (settled_quantity > held_quantity)."""
    vals = [fnum((cash or {}).get(k)) for k in ("order_available_cash", "withdrawable_cash", "foreign_currency_deposit")]
    known = [v for v in vals if v is not None]
    if not known:
        return None, "CASH_UNAVAILABLE"
    oa, wd = vals[0], vals[1]
    if oa is None or wd is None:
        return min(known), "MIN_FALLBACK:CASH_VALUE_MISSING"
    diff = Decimal(repr(oa)) - Decimal(repr(wd))
    if diff < -1:
        return min(known), "MIN_FALLBACK:BELOW_WITHDRAWABLE"
    sale = any(fnum(h.get("settled_quantity")) is not None and fnum(h.get("held_quantity")) is not None
               and fnum(h.get("settled_quantity")) > fnum(h.get("held_quantity"))
               for h in holdings or [] if isinstance(h, dict))
    if diff > 1 and not sale:
        return min(known), "MIN_FALLBACK:UNSETTLED_NOT_RECONCILED"
    return oa, "ORDER_AVAILABLE"


def exposure_check(env):
    ctx, ev, s7, mult_of = env["ctx"], env["dec"]["evaluation_session"], env["s7"], env["mult_of"]
    w, eq = weights_now(env)
    if w is None:
        return {"status": "PRICE_MISSING"}
    vals = sum(x * eq for x in w.values())
    cash = fnum(s7["equity"].get("cash_usd"))
    unreg = [s for s in w if mult_of(s) is None]
    N = None if unreg else sum(mult_of(s) * x for s, x in w.items())
    V, vs = compute_V(ctx.ser, w, ev)
    s7e = s7["exposure"]
    # V6 / EV4 total assets = sum(qty x close) + the t2-equity-cash cash (Judge2 2026-10-15 3)
    dep, dep_basis = equity_cash_t2(env["snap"].get("cash"), env["snap"].get("holdings"))
    return {"status": "OK", "equity_s7": eq, "equity_oracle": vals + (cash or 0.0), "total_assets_v6": (vals + dep) if dep is not None else None,
            "total_cash_v6": dep, "total_cash_basis": dep_basis,
            "N_oracle": N, "N_unregistered": unreg, "V_oracle": V, "V_status": vs,
            "N_s7": s7e.get("nominal"), "V_s7": s7e.get("sox_equivalent"), "E_s7": s7e.get("effective"),
            "E_oracle": max(N, V) if (V is not None and N is not None) else None}


def ev3a_dates(repo):
    out = set()
    p = os.path.join(repo, "docs/claude/recovery-gate-R-REC1-2026-10-09.md")
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8").read().splitlines():
            m = re.match(r"^- 이벤트 (\d{4}-\d{2}-\d{2})\(EV", ln)
            if m:
                out.add(m.group(1))
    return out


def s7_fresh(env):
    s7 = env["s7"]
    return s7.get("evaluation_session") == env["dec"]["evaluation_session"] and not s7["fail_closed"].get("active")


def req3_of(env, sym):
    """buy requirement (3): basis (card table N + new M); watch card missing / not accepted -> unk (확인 필요)."""
    d = env["detail"].get(sym) or {}
    if d.get("role") == "watch" and d.get("registry") in ("NO_REGISTRY_ENTRY", "WATCH_CARD_NOT_ACCEPTED"):
        return "unk"
    return "ok" if (d.get("buy") or {}).get("basis_met") else "no"


def req4_of(env, sym):
    """buy requirement (4): the M6 7-stock comparison card mentions the code."""
    for p in sorted(glob.glob(os.path.join(env["ctx"].repo, "docs/claude/m6-relative-comparison-7stock*.md"))):
        if sym in open(p, encoding="utf-8").read():   # rule file 134 "grep -c" (substring)
            return "ok"
    return "no"


def w_star(env, w, sym):
    """builder F5: largest weight on the 0.001 grid with projected N <= target and V <= target (1.55) and the single-stock
    nominal cap; None when no grid weight passes or a multiplier is missing."""
    ctx, ev, policy, mult_of = env["ctx"], env["dec"]["evaluation_session"], env["policy"], env["mult_of"]
    cap = float(policy.get("single_stock_nominal_cap", 0.4))
    exempt = set(policy.get("single_stock_cap_exempt") or [])
    target_E = float(policy.get("target_exposure", EXPOSURE_TARGET))
    m = mult_of(sym)
    best = None
    if w is not None and m is not None and all(mult_of(s) is not None for s in w):
        rest = sum(x for s, x in w.items() if s != sym)
        for k in range(1, 1001):
            wv = float(WEIGHT_STEP * k)
            if wv + rest > 1.0 + 1e-12:
                break
            ww = dict(w); ww[sym] = wv
            N = sum(mult_of(s) * x for s, x in ww.items())
            V, _ = compute_V(ctx.ser, ww, ev)
            if V is not None and N <= target_E and V <= target_E and (sym in exempt or m * wv <= cap):
                best = wv
    return best


def first_entry_target(env, sym, best):
    """held: W*; not held: floor(W*/2) on the grid (design 7-1 1, builder F5)."""
    if sym in env["held"]:
        return best
    return float((Decimal(repr(best)) / 2 / WEIGHT_STEP).to_integral_value(rounding=ROUND_FLOOR) * WEIGHT_STEP)




def redeploy_candidates(env, sym):
    """Sell redeployment candidates (Judge 2026-10-15 S5): another symbol of this run whose buy requirements (1), (3), (4)
    and (5) are ok today, a policy-approved product (card_stock_core or allowed_index_etfs - the sell-only MVLL is not),
    registry status OK and 60 stress returns; the symbol sold and every symbol with an open sell circuit today are left
    out. Requirement (2) (exposure / cash), S7 pauses and the after-sale exposure are not filters (the D+1 gates decide).
    Ranked (S3): more strong evidence, then more weak kinds, then the code."""
    ctx, ev, policy = env["ctx"], env["dec"]["evaluation_session"], env["policy"]
    approved = set(policy.get("card_stock_core") or []) | set(policy.get("allowed_index_etfs") or [])
    cands, skipped = [], []
    for c in sorted(env["detail"]):
        d = env["detail"][c]
        if c == sym or (c, "sell") in env["open"]:
            continue
        if c not in approved or d.get("status") != "OK" or d.get("registry") != "OK":
            continue
        reqs = buy_requirements(env, c)
        if any(reqs[k] != "ok" for k in (0, 2, 3, 4)):
            skipped.append([c, "REQ:" + "".join("x" if reqs[k] != "ok" else "." for k in range(5))]); continue
        ind = ctx.ind.get(c)
        st = stress_returns(ind, ind.s.index[ev]) if ind is not None and ev in ind.s.index else None
        if st is None:
            skipped.append([c, "NO_STRESS_RETURNS"]); continue
        b = d.get("buy") or {}
        cands.append({"symbol": c, "up": st[0], "down": st[1], "strong": len(b.get("strong") or []),
                      "weak_kinds": len(b.get("weak_kinds") or [])})
    cands.sort(key=lambda x: (-x["strong"], -x["weak_kinds"], x["symbol"]))
    return cands, skipped

def buy_requirements(env, sym):
    """Buy-requirement line (rule file 134) cells 1-5 as ok|no|unk."""
    ctx, dec, cal, s7, policy = env["ctx"], env["dec"], env["cal"], env["s7"], env["policy"]
    ev = dec["evaluation_session"]
    held = env["held"]
    d = env["detail"].get(sym) or {}
    evd = d.get("buy") or {}
    # (1) earnings blackout (p-earn r1); index ETFs exempt; MVLL -> underlying MRVL (rule file 133)
    if sym == "DRAM":
        # DRAM never substitutes MU during MU's blackout (portfolio-exposure-review.md R3 / p-earn r1)
        e = (env["rr"] or {}).get("earnings") or {}
        ok, _ = earnings_reading(cal, e.get("MU"), ev, cal.next_session(ev), env["decide_at"])
        r1 = "ok" if ok else "no"
    elif sym in EXEMPT_FROM_EARNINGS:
        r1 = "ok"
    else:
        e = (env["rr"] or {}).get("earnings") or {}
        rec = e.get(UNDERLYING.get(sym, sym))
        ok, _ = earnings_reading(cal, rec, ev, cal.next_session(ev), env["decide_at"])
        r1 = "ok" if ok else "no"
    # (2) exposure + order-available cash + product approval
    exp = env["exposure"]
    N = exp.get("N_oracle")
    E = fnum(s7["exposure"].get("effective"))
    cash = fnum(env["snap"]["cash"].get("order_available_cash"))
    r2 = (N is not None and N < 1.85 and s7_fresh(env) and E is not None and E < 1.85
          and not s7["pauses"]["new_buy_recommendations"].get("paused") and cash is not None and cash > 0 and sym in REQ_PRODUCTS)
    if sym in held:
        w, _ = weights_now(env)
        caps = {b.get("symbol") for b in s7["single_stock_cap"]["breaches"] if b.get("block_new_buy")}
        peaks = {p.get("symbol") for p in s7["peak_reviews"] if p.get("pause_add_recommendations") or p.get("open_events")}
        exempt = set(policy.get("single_stock_cap_exempt") or [])
        m = env["mult_of"](sym)
        own_cap = sym not in exempt and (m is None or w is None or m * w.get(sym, 0) > float(policy.get("single_stock_nominal_cap", 0.4)))
        r2 = r2 and not s7["pauses"]["add_recommendations"].get("paused") and sym not in caps and sym not in peaks and not own_cap
    # (3) basis (card table N + new M); watch card missing / not accepted -> 확인 필요
    r3 = req3_of(env, sym)
    # (4) M6 7-stock comparison card mentions the code
    r4 = req4_of(env, sym)
    # (5) R-REC1
    e = (env["reg"].get("symbols") or {}).get(sym) or {}
    rg = rrec1(cal, ctx.ser, ctx.ind, ev, sym, e.get("rg2_benchmark") or "SOXX", ev3a_dates(ctx.repo), env["rrec_records"],
               accepted_on=(e.get("accepted") or {}).get("date"))
    d.setdefault("rrec1", rg)
    return [r1, "ok" if r2 else "no", r3, r4, rg.get("status")]


def g2_buy(s7, E, sym, approved, req1, delta_positive, held):
    """G2 for a buy (moved out of gates_check unchanged so selftest S16 can call it, ev-rg1-hyper)."""
    # review lines L2 and below pause until a journal review: the pause itself is the gate (decision D1 = c,
    # ev-rg1-hyper). R4: pauses.new_buy carries REVIEW_LINE_OPEN for open pause lines (portfolio-exposure-review.md 27, 321)
    peaks = {p.get("symbol") for p in s7["peak_reviews"] if p.get("pause_add_recommendations") or p.get("open_events")}
    return (E is not None and E < 1.85 and sym in approved and req1 == "ok" and delta_positive
            and not s7["pauses"]["new_buy_recommendations"].get("paused")
            and not (sym in held and (s7["pauses"]["add_recommendations"].get("paused") or sym in peaks)))


def gates_check(env, sym, side, r_max, delta_positive):
    dec, snap, s7, policy = env["dec"], env["snap"], env["s7"], env["policy"]
    g = {}
    # G0: no open order; every ticket of the previous decide run classified in this run's outcomes (F6 broker reads are
    # not redone here - completeness only)
    prev_ids = [t.get("ticket_id") for t in ((env["prev_dec"] or {}).get("tickets") or []) if t.get("ticket_id")]
    outc = {o.get("ticket_id"): str(o.get("state") or o.get("outcome") or "") for o in dec.get("outcomes") or [] if isinstance(o, dict)}
    g["G0"] = (not snap["open_orders"]) and all(outc.get(i) in CLASSIFIED for i in prev_ids)
    # G1: T1 OK, reconcile OK, state = snapshot (qty equal, cash within $1), S7 fresh, own registry check OK
    t1 = load_json(rel(env["repo"], canon_inputs(env["day"])["t1_result"]))
    rc = load_json(rel(env["repo"], canon_inputs(env["day"])["reconcile"]))
    st = env["state"]
    st_h = {k: v for k, v in (st.get("holdings") or {}).items() if v}
    sn_h = {k: int(v) for k, v in env["held"].items()}
    cash_ok = abs((fnum(st.get("available_cash_usd")) or -1e9) - (fnum(snap["cash"].get("order_available_cash")) or 1e9)) <= 1.0
    reg_ok = (env["detail"].get(sym) or {}).get("registry") == "OK"
    g["G1"] = str(t1.get("status")) == "OK" and str(rc.get("status")) == "OK" and st_h == sn_h and cash_ok and s7_fresh(env) and reg_ok
    # G2 (buy): E < 1.85 (and so < 1.9), product approved in policy, earnings outside blackout, pauses, projected E <= 1.55
    if side == "buy":
        E = fnum(s7["exposure"].get("effective"))
        approved = set(policy.get("card_stock_core") or []) | set(policy.get("allowed_index_etfs") or [])
        reqs = buy_requirements(env, sym)
        g["G2"] = g2_buy(s7, E, sym, approved, reqs[0], delta_positive, env["held"])
    else:
        g["G2"] = True
    g["G3"] = r_max > 0 and (env["detail"].get(sym) or {}).get("registry") == "OK"
    return g


def r_max_of(evd, research_cap=None):
    """G3 (design 3 / builder F4) plus D18 (builder F3): when the strong evidence is only research-record official facts
    (no registry static strong evidence of the same side) and research_only_strong_r_cap is set, r_max <= that cap."""
    r = _r_max_base(evd)
    strong = evd.get("strong") or []
    if research_cap is not None and strong and not (evd.get("static_strong") or []):
        r = min(r, Fraction_text_to_decimal(research_cap))
    return r


def Fraction_text_to_decimal(txt):
    n, _, d = str(txt).partition("/")
    return Decimal(n) / Decimal(d or 1)


def fraction_text(r):
    return {Decimal(0): "0", Decimal(1) / 3: "1/3", Decimal(1) / 2: "1/2", Decimal(1): "1"}.get(r, str(r))


def _r_max_base(evd):
    strong = evd.get("strong") or []
    weak = evd.get("weak_kinds") or []
    r = Decimal(1) if strong else (Decimal(1) / 2 if len(weak) >= 2 else Decimal(0))
    if not strong and r > 0:
        # common rules only (no card-defined trigger of the counted kinds, no card-table or official evidence) -> <= 1/3.
        # User decision "t2rc-corefix: 5 = b" (2026-10-15): for a buy the card trigger must be hit today (design G3
        # "C끼리만 성립"); for a sell a card trigger defined in the counted kind is enough (the core reading, so a sell
        # step is not cut to 1/3 - "위험 감축을 늦추지 않는다", builder G2b)
        kinds = set(evd.get("card_defined_kinds") or []) if evd.get("side") == "sell" else set(evd.get("card_kinds") or [])
        non_common = [k for k in weak if k.startswith("static:") or k in kinds]
        if not non_common:
            r = min(r, Decimal(1) / 3)
    return r


def gate_match(g, side, want, cv):
    """Core ticket gate format (auto-core-ticket schema): G0 / G1 bool; G2 True for a sell, the target weight W* (number,
    0.001 grid) for a buy; G3 the r_max text "0" | "1/3" | "1/2" | "1"."""
    if g == "G2" and side == "buy":
        return isinstance(cv, (int, float)) and not isinstance(cv, bool) and want is not None and abs(cv - want) < 1e-9
    if isinstance(want, bool):
        return cv is want
    return cv == want


def ticket_check(env, t):
    """Recompute one ticket (prereg C2 items): qty (integer), LOC price (cents), buy requirements 1-5, gates G0-G3,
    order-available cash >= amount, and whether the ticket should exist at all. Sell quantity uses the design 5
    redeployment bridge: path 3 (sell -> next-day best candidate) when a candidate exists, else path 2 (sell -> cash);
    best candidate = the one whose chosen row has the smallest max regret (ties -> smaller quantity as the F5 step tie
    rule, then symbol). Candidates: registry + M6 + (3) and executable as a next-day buy (redeploy_candidates)."""
    ctx, dec, s7, policy = env["ctx"], env["dec"], env["s7"], env["policy"]
    sym, side = t.get("ticker"), t.get("side")
    ev = dec["evaluation_session"]
    out = {"ticket_id": t.get("ticket_id"), "ticker": sym, "side": side, "items": {}, "not_recomputed": []}
    ind = ctx.ind.get(sym)
    if ind is None or ev not in ind.s.index or ind.sigma[ind.s.index[ev]] is None:
        out["match"] = False; out["should_exist"] = False; out["not_recomputed"].append("NO_DATA"); return out
    i = ind.s.index[ev]
    ref = ind.s.raw_c[i]
    price = loc_price(ref, ind.sigma[i], side)
    out["items"]["price"] = {"oracle": str(price), "core": t.get("price"),
                             "match": t.get("price") is not None and Decimal(str(t.get("price"))) == price}
    w, eq = weights_now(env)
    cash_avail = fnum(env["snap"]["cash"].get("order_available_cash"))
    d = env["detail"].get(sym) or {}
    evd = d.get(side) or {}
    r_max = r_max_of(evd, (env.get("core_cfg") or {}).get("research_only_strong_r_cap"))
    mult_of = env["mult_of"]
    cur_w = (w or {}).get(sym, 0.0)
    best = None
    delta = 0
    if side == "buy":
        best = w_star(env, w, sym)
        if best is None:
            out["not_recomputed"].append("W_STAR_NONE")
            best = cur_w
        target = best if sym in env["held"] else float((Decimal(repr(best)) / 2 / WEIGHT_STEP).to_integral_value(rounding=ROUND_FLOOR) * WEIGHT_STEP)
        delta = int(math.floor((target - cur_w) * eq / ref))
        out["items"]["target_weight"] = {"w_star": best, "target": target, "current": cur_w}
    else:
        goals = []
        red = [x for x in s7["recommendations"]["reduce"] if isinstance(x, dict) and x.get("symbol") == sym]
        if red and red[0].get("target_weight") is not None:
            goals.append(float(red[0]["target_weight"]))
        e = (env["reg"].get("symbols") or {}).get(sym) or {}
        if e.get("card_action") == "EXIT":
            goals.append(0.0)
        elif e.get("card_action") == "TRIM" and fnum(e.get("trim_target_weight")) is not None:
            goals.append(fnum(e.get("trim_target_weight")))
        tw = min(goals) if goals else None   # two approved goals -> the lower weight (Judge S9)
        if tw is None:
            out["not_recomputed"].append("SELL_TARGET_WEIGHT")
        else:
            delta = int(env["held"].get(sym, 0) - math.floor(tw * eq / ref))
    qty, pick_r, up, dn = 0, None, None, None
    st = stress_returns(ind, i)
    if st is None:
        out["not_recomputed"].append("STRESS_RETURNS")
    elif delta > 0:
        up, dn, _ = st
        if side == "buy":
            pick, rows = regret_choice(delta, ref, up, dn, r_max, eq, side)
        else:
            cands, skipped = redeploy_candidates(env, sym)
            cand = cands[0] if cands else None
            pick, rows = regret_choice(delta, ref, up, dn, r_max, eq, side,
                                       (cand["up"], cand["down"]) if cand else None)
            path = {"path": "SELL_CASH_AND_CANDIDATE" if cand else "SELL_TO_CASH",
                    "candidate": cand, "ranked": [c["symbol"] for c in cands], "skipped": skipped}
            core_reg = t.get("regret") if isinstance(t.get("regret"), dict) else {}
            # information only (not a C2 item): what the core wrote about its columns, for the Judge
            path["core_columns"] = core_reg.get("columns")
            out["items"]["redeploy"] = path
        qty, pick_r = pick["qty"], pick["r"]
        out["items"]["regret_rows"] = [{"r": r["r"], "qty": r["qty"], "regret": {k: str(v) for k, v in r["regret"].items()},
                                        "max_regret": str(r["max_regret"])} for r in rows]
    if side == "buy" and cash_avail is not None:
        while qty > 0 and Decimal(qty) * price * (1 + FEE_BUFFER) > Decimal(repr(cash_avail)):
            qty -= 1   # G4: reduce to the verified order-available cash
    if qty > 0 and qty * ref < DEADBAND * eq:
        qty = 0        # deadband on the final quantity (design 7-1 4)
    out["items"]["qty"] = {"oracle": qty, "core": t.get("qty"), "match": qty == t.get("qty"), "delta": delta,
                           "r_max": str(r_max), "r": pick_r, "up": up, "down": dn}
    amount = Decimal(qty) * price
    cash_ok = side == "sell" or (cash_avail is not None and Decimal(repr(cash_avail)) >= amount * (1 + FEE_BUFFER))
    out["items"]["cash"] = {"match": cash_ok, "order_available": cash_avail, "amount": str(amount)}
    if side == "buy":
        reqs = buy_requirements(env, sym)
        core_row = next((r for r in dec.get("buy_requirements") or [] if r.get("code") == sym), None)
        out["items"]["requirements"] = {"req%d" % (k + 1): {"oracle": reqs[k], "core": core_row["c"][k]["s"] if core_row else None,
                                                             "match": core_row is not None and reqs[k] == core_row["c"][k]["s"]} for k in range(5)}
    else:
        reqs = ["ok"] * 5
    gates = gates_check(env, sym, side, r_max, delta > 0)
    cg = t.get("gates") or {}
    # core ticket gate format (auto-core-ticket schema, Judge 2026-10-15 extra A): G0 / G1 bool, G2 = True (sell) or the
    # target weight W* (buy), G3 = the r_max text
    want = {"G0": gates["G0"], "G1": gates["G1"],
            "G2": True if side == "sell" else (round(best, 3) if (gates["G2"] and best is not None) else None),
            "G3": fraction_text(r_max)}
    gm = {g: {"oracle": want[g], "core": cg.get(g), "match": gate_match(g, side, want[g], cg.get(g))}
          for g in ("G0", "G1", "G2", "G3")}
    out["items"]["gates"] = gm
    kill = bool((env.get("core_cfg") or {}).get("kill_switch"))
    out["should_exist"] = ((sym, side) in env["open"] and all(gates.values()) and qty > 0 and not kill
                           and all(reqs[k] == "ok" for k in (0, 1, 2, 3, 4)) and d.get("registry") == "OK")
    # (4) M6 is a ticket condition too (rule file 134 "막힘 = 매수 검토가 열리지 않음", Judge 2026-10-15 3-13)
    flat = [out["items"]["price"]["match"], out["items"]["qty"]["match"], out["items"]["cash"]["match"]]
    flat += [v["match"] for v in (out["items"].get("requirements") or {}).values()]
    flat += [v["match"] for v in gm.values()]
    out["match"] = all(flat) and out["should_exist"] and not out["not_recomputed"]
    return out


def finish(res, args):
    if res.get("schema") == "t2rc-check-1.0" and "c3" not in res:
        # not checked today: confirmed directions stay allowed, today's tickets count as unmatched (fail closed)
        dpath = os.path.join(args.repo, "workspace/outputs/auto-core", args.day, "decision.json")
        try:
            dec = load_json(dpath)
            unmatched = [{"ticket_id": t.get("ticket_id"), "side": t.get("side"), "match": False} for t in dec.get("tickets") or []]
            res["c3"] = c3_record(args.repo, args.day, dec, unmatched)
        except Exception:
            res["c3"] = None
    txt = json.dumps(res, ensure_ascii=False, indent=1, default=str)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(txt + "\n")
    else:
        print(txt)
    v = res.get("verdict")
    print("VERDICT %s" % v, file=sys.stderr)
    return 0 if v in ("MATCH", "NOT_CHECKED", "REPRODUCED", "INFO_MATCH") else 2


# ---------------------------------------------------------------- replay reproduction (self-check)
def cmd_replay(args):
    repo = args.repo
    rp = load_json(args.replay_json)
    cal = Calendar(repo)
    reg = load_json(os.path.join(repo, "docs/claude/card-evidence-registry.json"))
    wl = load_json(os.path.join(repo, "docs/claude/watchlist-registry.json"))
    policy = load_json(os.path.join(repo, "stock-strategy-system/alert_policy.json"))["portfolio_exposure_policy"]
    mults = policy.get("nominal_multipliers") or {}
    mult_of = lambda s: mults.get(s, 1)
    corp_p = os.path.join(repo, "workspace/outputs/regular-session-closes/corporate-actions.json")
    corp = load_json(corp_p).get("actions") or []
    wm = {m["code"]: m for m in wl.get("members") or []}
    end = rp["period"]["end"]
    allsyms = sorted(set(wm) | {"SOXX", "GRID", "MVLL", "SOXL", "NBIS"})
    ctx = Context(repo, cal, end, allsyms, corp)
    res = {"schema": "t2rc-replay-check-1.0", "oracle_version": ORACLE_VERSION, "oracle_sha256": sha256_lf(os.path.abspath(__file__)),
           "replay_sha256": sha256_file(args.replay_json), "registry_sha256_now": sha256_file(os.path.join(repo, "docs/claude/card-evidence-registry.json")),
           "registry_sha256_replay": rp.get("registry_sha256"), "portfolios": {},
           "order_authority": False, "quantity_authority": "none", "execution_quantity": None}
    allmatch = True
    for name, pf in rp["portfolios"].items():
        hold = {s: q for s, q in pf["holdings"].items() if q > 0}
        members = [c for c in wm if c not in hold]
        rows, mism = [], []
        for sess in pf["sessions"]:
            d = sess["session"]
            # S7 add list (replay approximation, D): held card/ETF instrument, E <= add threshold, not in earnings blackout.
            # NBIS has no earnings record in E-R1 -> blackout; MVLL is sell-only. Reduce list: E >= reduce threshold.
            w = {}
            eq = pf["cash"]
            for s, q in hold.items():
                ser = ctx.ser[s]
                c = ser.raw_c[ser.index[d]] if d in ser.index else None
                eq += q * (c or 0)
                w[s] = q * (c or 0)
            weights = {s: v / eq for s, v in w.items()}
            N = sum(mult_of(s) * x for s, x in weights.items())
            V, _ = compute_V(ctx.ser, weights, d)
            E = max(N, V) if V is not None else None
            s7_add = set()
            s7_reduce = set()
            th = policy.get("thresholds") or {}
            add_le = float(th.get("add_when_exposure_lte", 1.25)) if isinstance(th, dict) else 1.25
            red_ge = float(th.get("reduce_when_exposure_gte", 1.85)) if isinstance(th, dict) else 1.85
            if E is not None and E <= add_le:
                s7_add = {s for s in hold if s not in ("NBIS", "MVLL") and s in (set(policy.get("card_stock_core") or []) | set(policy.get("allowed_index_etfs") or []))}
            if E is not None and E >= red_ge:
                s7_reduce = set(hold)
            opened, _ = circuit_for_session(ctx, d, set(hold), set(members), reg, wm, [], s7_add, s7_reduce, mult_of)
            mine = {(c["symbol"], c["side"]) for c in opened}
            core = {(c["symbol"], c["side"]) for c in sess.get("candidates") or []}
            rows.append({"session": d, "oracle": sorted(map(list, mine)), "core": sorted(map(list, core)), "E_oracle": E, "E_core": sess.get("E")})
            if mine != core:
                mism.append(rows[-1])
        res["portfolios"][name] = {"sessions": len(rows), "oracle_open": [r for r in rows if r["oracle"]], "mismatches": mism}
        allmatch = allmatch and not mism
    res["verdict"] = "REPRODUCED" if allmatch else "MISMATCH"
    return finish(res, args)


# ---------------------------------------------------------------- selftest
def _rg1_world(n=70, events=(), ds1=(), dips=(), rebound=()):
    """ev-rg1-hyper selftest series (hand-set indicator values, no bars): close 100 / low 99 / ret +0.1% / sigma 2% /
    EMA50 99 / 20-session high 101; an event day closes 95 (low 94) with -5% (EV1, above the EV2 line 94.94); a DS1 day
    closes 98 (< EMA50, RG2 no); a dip day returns -2.5% (<= -1 sigma, > -2 sigma); a rebound day returns +3% (keeps the
    5-session sigma above 1.5 sigma60, RG4 no, while it is in the 5-session window). SOXX is also the candidate X."""
    class _N:
        pass
    s, i = _N(), _N()
    day, s.dates = dt.date(2026, 3, 2), []
    while len(s.dates) < n:
        if day.weekday() < 5:
            s.dates.append(day.isoformat())
        day += dt.timedelta(days=1)
    s.index = {d: k for k, d in enumerate(s.dates)}
    s.c, s.l = [100.0] * n, [99.0] * n
    i.ret, i.sigma, i.hi20, i.ema50 = [0.001] * n, [0.02] * n, [101.0] * n, [99.0] * n
    for k in events:
        s.c[k], s.l[k], i.ret[k] = 95.0, 94.0, -0.05
    for k in ds1:
        s.c[k], s.l[k] = 98.0, 97.5
    for k in dips:
        i.ret[k] = -0.025
    for k in rebound:
        i.ret[k] = 0.03
    return s, {"SOXX": s, "X": s}, {"SOXX": i, "X": i}


def _rg1_fact(fid, session, announced=None, **extra):
    f = {"fact_id": fid, "event_session": session, "root_thesis_damage": True,
         "announced_at": announced if announced is not None else session + "T16:05:00-04:00"}
    f.update(extra)
    return f


def _rg1_run(world, facts=(), accepted_on=None, t=None):
    s, ser, ind = world
    t = len(s.dates) - 1 if t is None else t
    records = {d: [] for d in s.dates[:t + 1]}
    for f in facts:
        records[f["event_session"]].append(f)
    return rrec1(None, ser, ind, s.dates[t], "X", "SOXX", set(), records, accepted_on=accepted_on)


def _next_day(d):
    return (dt.date.fromisoformat(d) + dt.timedelta(days=1)).isoformat()


def selftest_rg1_damage():
    """ev-rg1-hyper S1-S9: the same cases and expectations as manage-us-stock-strategy/tests/test_auto_core_rg1_damage.py
    (status, open, RG1)."""
    fails = []

    def want(name, got, status, opened, rg1):
        have = (got.get("status"), got.get("open"), (got.get("rg") or {}).get("RG1"))
        if have != (status, opened, rg1):
            fails.append("RG1 %s %s != %s" % (name, have, (status, opened, rg1)))

    w = _rg1_world(events=(60,))
    want("base", _rg1_run(w), "ok", False, None)
    d = w[0].dates
    # S1 damage on the event day itself (EV1): blocked; re-accepted on its KST date -> closes after it
    f1 = _rg1_fact("D1", d[60])
    want("S1", _rg1_run(w, [f1]), "no", True, "no")
    want("S1 re-accepted", _rg1_run(w, [f1], accepted_on=_next_day(d[60])), "ok", False, None)
    # S2 rebase: damage after event A, then a new event B
    w2 = _rg1_world(events=(50, 60))
    want("S2", _rg1_run(w2, [_rg1_fact("D2", w2[0].dates[52])]), "no", True, "no")
    # S3 time decay: event, damage, 20+ sessions without DS1 and RG2 ok -> stays open
    w3 = _rg1_world(events=(40,))
    want("S3", _rg1_run(w3, [_rg1_fact("D3", w3[0].dates[41])]), "no", True, "no")
    # S4 damage after a close
    w4 = _rg1_world(events=(50,))
    r4 = _rg1_run(w4, [_rg1_fact("D4", w4[0].dates[60])])
    want("S4", r4, "no", False, "no")
    if r4.get("reason") != "RG1_THESIS_DAMAGE:D4" or r4.get("closed_at") != w4[0].dates[52]:
        fails.append("RG1 S4 reason %s %s" % (r4.get("reason"), r4.get("closed_at")))
    # S5 no event in the window
    w5 = _rg1_world()
    r5 = _rg1_run(w5, [_rg1_fact("D5", w5[0].dates[60])])
    want("S5", r5, "no", False, "no")
    if r5.get("rg") != {"RG1": "no"} or r5.get("events") != []:
        fails.append("RG1 S5 %s" % r5)
    # S6 release boundary: after-close announcement (KST next day); offset rules
    f6 = _rg1_fact("D6", "2026-05-04")
    for acc, through, exp in (("2026-05-04", "2026-05-06", ["D6"]), ("2026-05-05", "2026-05-05", []),
                              ("2026-05-06", "2026-05-05", ["D6"]), (None, "2026-05-06", ["D6"]),
                              ("2026-5-5", "2026-05-06", ["D6"])):
        if rg1_uncleared([f6], "2026-03-02", through, acc) != exp:
            fails.append("RG1 S6 %s %s" % (acc, through))
    for announced, exp in (("", ["D6"]), ("2026-05-04T16:05:00", ["D6"]), ("2026-05-04T20:05:00Z", [])):
        if rg1_uncleared([_rg1_fact("D6", "2026-05-04", announced)], "2026-03-02", "2026-05-06", "2026-05-05") != exp:
            fails.append("RG1 S6 announced %r" % announced)
    # S6b no retroactive release: event 40, rebound 41-43 (RG4 no to 44), damage 43, RG2-RG4 ok 45-48 but RG1 no, DS1 from
    # 49 on, re-accepted at 55 -> open; re-accepted on the damage's own release day -> closes at 45
    w6 = _rg1_world(events=(40,), ds1=range(49, 70), rebound=(41, 42, 43))
    f6b = _rg1_fact("D6B", w6[0].dates[43])
    want("S6b", _rg1_run(w6, [f6b], accepted_on=w6[0].dates[55]), "no", True, "ok")   # RG1 cleared, RG2 no (DS1)
    want("S6b base", _rg1_run(w6, [f6b]), "no", True, "no")
    want("S6b early", _rg1_run(w6, [f6b], accepted_on=_next_day(w6[0].dates[43])), "ok", False, None)
    # S7 window edge: event_session = W[0] blocks, the session before is ignored
    w7 = _rg1_world()
    want("S7 edge", _rg1_run(w7, [_rg1_fact("D7", w7[0].dates[10])]), "no", False, "no")
    want("S7 out", _rg1_run(w7, [_rg1_fact("D7", w7[0].dates[9])]), "ok", False, None)
    # S9 thesis-damage-domain fact (marked): no EV3b on a -1 sigma day, RG1 no; the same fact unmarked opens EV3b
    w9 = _rg1_world(dips=(60,))
    r9 = _rg1_run(w9, [_rg1_fact("D9", w9[0].dates[60], damage_source="THESIS_DAMAGE_DOMAIN")])
    want("S9 marked", r9, "no", False, "no")
    r9b = _rg1_run(w9, [_rg1_fact("D9", w9[0].dates[60])])
    if r9b.get("event") != w9[0].dates[60] or "EV3b" not in (r9b.get("kinds") or []) or (r9b.get("rg") or {}).get("RG1") != "no":
        fails.append("RG1 S9 unmarked %s" % r9b)
    return fails


def selftest_g2_lines():
    """ev-rg1-hyper S16 (decision D1 = c): an L2 line already reviewed (no open event, no pause) does not block G2; an open
    L2 pause (pauses.new_buy REVIEW_LINE_OPEN) does."""
    fails = []

    def s7(paused):
        return {"review_lines": {"lines": [{"line_id": "L2", "triggered_in_current_drawdown": True}],
                                 "open_events": [{"line_id": "L2", "pause_new_buy_recommendations": True}] if paused else []},
                "pauses": {"new_buy_recommendations": {"paused": paused, "reasons": ["REVIEW_LINE_OPEN:L2"] if paused else []},
                           "add_recommendations": {"paused": paused}},
                "peak_reviews": []}
    if g2_buy(s7(False), 1.2, "MU", {"MU"}, "ok", True, {}) is not True:
        fails.append("S16 reviewed L2")
    if g2_buy(s7(True), 1.2, "MU", {"MU"}, "ok", True, {}) is not False:
        fails.append("S16 open L2")
    return fails


def cmd_selftest(args):
    fails = []
    # G-1 design 5 MVLL regret table: delta 236, ref 37.65, equity 30,255.36, up +29.6%, down -26.1%, r_max 1/2 -> 118
    pick, rows = regret_choice(236, 37.65, 0.296, -0.261, Decimal(1) / 2, 30255.36, "sell")
    exp = {"0": (0, 2319), "1/3": (869, 1553), "1/2": (1315, 1160), "1": (2630, 0)}
    for r in rows:
        eu, ed = exp[r["r"]]
        if abs(r["regret_up"] - eu) > 1 or abs(r["regret_down"] - ed) > 1:
            fails.append("G-1 row %s %.1f/%.1f != %s/%s" % (r["r"], r["regret_up"], r["regret_down"], eu, ed))
    if pick["qty"] != 118:
        fails.append("G-1 pick %s" % pick["qty"])
    # G-S1 sell, one table with cash and candidate columns (Judge 2026-10-15 S1/S6, hand arithmetic): MVLL numbers, r_max 1,
    # budget 907.66. Cash columns alone: row max 0:2319 . 1/3:1553 . 1/2:1315 . 1:2630 -> minimax 1/2 = 118 (118 x 37.65 x 0.296 = 1315.04).
    # Candidate B (+25% / -20%) adds columns whose regrets are smaller, so the row maxima stay the cash ones -> 118.
    pc, _ = regret_choice(236, 37.65, 0.296, -0.261, Decimal(1), 30255.36, "sell")
    pb, rb = regret_choice(236, 37.65, 0.296, -0.261, Decimal(1), 30255.36, "sell", (0.25, -0.20))
    if (pc["qty"], pb["qty"]) != (118, 118) or pb["max_regret"] != Decimal("1315.04") or len(rb[0]["regret"]) != 4:
        fails.append("G-S1 %s/%s %s" % (pc["qty"], pb["qty"], pb["max_regret"]))
    # G-S2 candidate columns change the step: delta 100, ref 10, equity 5000 (budget 150), up +10% / down -10%, r_max 1.
    #   cash only: row 1 max regret 100 <= 150 -> 100 shares.
    #   candidate +50% / -50%: cand-up pnl 4q (best row 1 = 400), cand-down pnl -4q (best row 0) ->
    #   row maxima 0:400 . 33:268 . 50:200 . 100:400 -> row 1 over budget -> minimax 50 (200.00)
    p1, _ = regret_choice(100, 10.0, 0.10, -0.10, Decimal(1), 5000.0, "sell")
    p2, _ = regret_choice(100, 10.0, 0.10, -0.10, Decimal(1), 5000.0, "sell", (0.50, -0.50))
    if (p1["qty"], p2["qty"]) != (100, 50) or p2["max_regret"] != Decimal("200.00"):
        fails.append("G-S2 %s/%s %s" % (p1["qty"], p2["qty"], p2["max_regret"]))
    # G-4 core ticket gate format (Judge 2026-10-15 extra A / 11-12)
    cases = [("G0", "buy", True, True, True), ("G0", "buy", True, "ok", False), ("G1", "sell", True, 1, False),
             ("G2", "sell", True, True, True), ("G2", "buy", 0.117, 0.117, True), ("G2", "buy", 0.117, 0.1170000000004, True),
             ("G2", "buy", 0.117, 0.118, False), ("G2", "buy", 0.117, True, False), ("G2", "buy", None, 0.117, False),
             ("G3", "sell", "1/2", "1/2", True), ("G3", "sell", "1/2", "1", False), ("G3", "buy", "1/3", 0.333, False)]
    for g, sd, want, cv, exp in cases:
        if gate_match(g, sd, want, cv) is not exp:
            fails.append("G-4 %s %s %r %r" % (g, sd, want, cv))
    # G-5 decision t2rc-corefix 5 = b: two common kinds, one of them holds a card trigger that is defined but not hit
    e5 = {"strong": [], "weak_kinds": ["trend_break", "oversold"], "card_kinds": [], "card_defined_kinds": ["trend_break"]}
    if r_max_of(dict(e5, side="buy")) != Decimal(1) / 3 or r_max_of(dict(e5, side="sell")) != Decimal(1) / 2:
        fails.append("G-5 %s %s" % (r_max_of(dict(e5, side="buy")), r_max_of(dict(e5, side="sell"))))
    # G-3 m to 4 decimals: SOXL 142.45, sigma 8.35% -> m 0.9165 -> 130.55542 -> 130.56; buy 164.22, sigma 8.45% ->
    # m = 1.04225 -> 1.0422 (down) -> 171.150084 -> 171.15; a sigma where the 4-decimal m matters: ref 100, sigma 0.033333
    # -> sell m 0.966667 -> 0.9667 (up) -> 96.67 (unrounded m would give 96.6667 -> 96.67 too); buy m 1.0166665 ->
    # 1.0166 -> 101.66 (unrounded 101.666665 -> 101.66); ref 250, sigma 0.0123456: buy m 1.0061728 -> 1.0061 -> 251.52
    # (unrounded 251.5432 -> 251.54)
    if loc_mult(0.0123456, "buy") != Decimal("1.0061") or loc_price(250.0, 0.0123456, "buy") != Decimal("251.52"):
        fails.append("G-3 m %s %s" % (loc_mult(0.0123456, "buy"), loc_price(250.0, 0.0123456, "buy")))
    # G-2 SOXL sigma 8.35%, ref 142.45 -> sell floor 130.56 (cents up); buy cap same way down
    if loc_price(142.45, 0.0835, "sell") != Decimal("130.56"):
        fails.append("G-2 sell %s" % loc_price(142.45, 0.0835, "sell"))
    if loc_price(164.22, 0.0845, "buy") != Decimal("171.15"):
        # design 7-2 example says $171.16 with sigma 8.45% at ref 164.22 (rounded sigma); exact = 171.158... -> cents down 171.15
        fails.append("G-2 buy %s" % loc_price(164.22, 0.0845, "buy"))
    # G-6 exact step quantity (Judge2 1): delta 165 -> 1/3 = 55, delta 3 -> 1, delta 297 -> 99 (rows 0 / 1/3 / 1/2 / 1)
    for dl, want in ((165, [0, 55, 82, 165]), (3, [0, 1, 1, 3]), (297, [0, 99, 148, 297])):
        _, rq = regret_choice(dl, 10.0, 0.10, -0.10, Decimal(1), 1e9, "buy")
        if [x["qty"] for x in rq] != want:
            fails.append("G-6 %s %s" % (dl, [x["qty"] for x in rq]))
    # G-7 C1 guard (Judge2 2): MATCH -> NOT_CHECKED; MISMATCH stays MISMATCH with the gap in the reason
    g1 = {"verdict": "MATCH", "tickets": [{"match": True}]}
    g2 = {"verdict": "MISMATCH", "reason": "CORE_BUG", "tickets": [{"match": True}]}
    apply_gap_guard(g1, ["A"]); apply_gap_guard(g2, ["A"])
    if (g1["verdict"], g2["verdict"], g2["reason"], g1["tickets"][0]["match"], g2["c2_item_match"]) != (
            "NOT_CHECKED", "MISMATCH", "CORE_BUG;ORACLE_DATA_GAP:A", False, False):
        fails.append("G-7 %s %s" % (g1, g2))
    # G-8 t2-equity-cash (Judge2 3): 10-13 snapshot (SOXL settled 75 > held 53) -> order-available 12,469.18;
    # same numbers without the sale row -> smallest 9,396.68; order-available below withdrawable -> smallest; missing -> smallest
    c13 = {"order_available_cash": 12469.18, "withdrawable_cash": 9396.68, "foreign_currency_deposit": 9396.68}
    h13 = [{"ticker": "SOXL", "held_quantity": 53.0, "settled_quantity": 75.0}]
    got = [equity_cash_t2(c13, h13)[0], equity_cash_t2(c13, [{"held_quantity": 53.0, "settled_quantity": 53.0}])[0],
           equity_cash_t2({"order_available_cash": 100.0, "withdrawable_cash": 102.0, "foreign_currency_deposit": 103.0}, [])[0],
           equity_cash_t2({"order_available_cash": 100.5, "withdrawable_cash": 100.0, "foreign_currency_deposit": 99.0}, [])[0],
           equity_cash_t2({"order_available_cash": 100.0, "foreign_currency_deposit": 90.0}, h13)[0], equity_cash_t2({}, h13)[0]]
    if got != [12469.18, 9396.68, 100.0, 100.5, 90.0, None]:
        fails.append("G-8 %s" % got)
    # G-9 C7 base strictly before announced_at (Judge2 4): announcement 16:00:00 on d1 -> base d0 close 100 -> d1 close 90 is
    # the C7- event (with "at or before" the base would be d1 = 90 and no event)
    class _O:
        pass
    s9, c9, i9 = _O(), _O(), _O()
    s9.dates = ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"]
    s9.c = [100.0, 90.0, 95.0, 95.0]
    s9.index = {d: k for k, d in enumerate(s9.dates)}
    c9.close_at = {d: d + "T16:00:00-05:00" for d in s9.dates}
    i9.s = s9
    f9 = [{"direction": "+", "criterion_a": True, "announced_at": "2026-11-03T16:00:00-05:00", "event_session": "2026-11-04"}]
    if c7_events(i9, c9, f9, "-") != [False, True, False, False]:
        fails.append("G-9 %s" % c7_events(i9, c9, f9, "-"))
    # synthetic C3 persistence (rule file 113 v3.12.5)
    rel_seq = [False, True, True, True, False, True]
    st = state_run(len(rel_seq), lambda i: rel_seq[i], 2, True)
    if st != ["none", "none", "hit", "hit", "none", "none"]:
        fails.append("C3 run %s" % st)
    st = state_run(3, lambda i: True, 2, True)
    if st != ["none", "unk", "unk"]:
        fails.append("C3 series start %s" % st)
    # event window: event on day 1, opposite on day 3 resolves
    st = events_to_state(7, [False, True, False, False, False, False, False], [False, False, False, True, False, False, False])
    if st != ["none", "hit", "hit", "none", "none", "none", "none"]:
        fails.append("event window %s" % st)
    st = events_to_state(8, [False, True, False, False, False, False, False, False], [False] * 8)
    if st != ["none", "hit", "hit", "hit", "hit", "hit", "none", "none"]:
        fails.append("event window 5 %s" % st)
    q = quantile_linear([1, 2, 3, 4], 0.9)
    if abs(q - 3.7) > 1e-12:
        fails.append("quantile %s" % q)
    fails.extend(selftest_rg1_damage())
    fails.extend(selftest_g2_lines())
    # rrec-ev4 REMOVE (2026-10-19): the account total is no longer an R-REC1 input. A total below the V6 first line and
    # below S7 hwm x 0.9 (2026-10-16: 23,695.43 < 25,626.55 and < 31,711.76 x 0.9) with no other event in the window
    # -> ok, open False (before the change: EV4 on the evaluation session, open)
    r_ev4 = _rg1_run(_rg1_world())
    if (r_ev4.get("status"), r_ev4.get("open"), r_ev4.get("events")) != ("ok", False, []):
        fails.append("EV4 removed %s" % r_ev4)
    # data anchors (only when the repository data is present): design 5 / 7-2 numbers recomputed from saved pages
    anchors, open_items = [], []
    repo = getattr(args, "repo", None)
    if repo and os.path.exists(os.path.join(repo, "workspace/outputs/regular-session-closes/pages/MVLL")):
        cal = Calendar(repo)
        corp = load_json(os.path.join(repo, "workspace/outputs/regular-session-closes/corporate-actions.json")).get("actions") or []
        s = Series(repo, cal, "MVLL", "2026-10-05", corp); ind = Ind(s); i = s.index["2026-10-05"]
        sig = ind.sigma[i]
        pop = sig * math.sqrt(59 / 60)
        up, dn, xs = stress_returns(ind, i)
        worst = min(ind.ret[k] for k in range(i - 59, i + 1))
        chk = [("MVLL 10/05 ref 37.65", abs(s.raw_c[i] - 37.65) < 0.005),
               ("MVLL sigma60 population 9.94% (design 7-2 used ddof 0; oracle uses sample = builder F1)", abs(pop - 0.0994) < 0.00005),
               ("MVLL 5-session 10th pct -26.1% (60 overlapping returns, linear)", abs(dn + 0.261) < 0.0005),
               ("MVLL worst 1-day -20.8%", abs(worst + 0.208) < 0.0005)]
        s2 = Series(repo, cal, "SOXL", "2026-10-08", corp); ind2 = Ind(s2); j = s2.index["2026-10-08"]
        chk.append(("SOXL 10/08 sigma60 8.35% (G-2, sample)", abs(ind2.sigma[j] - 0.0835) < 0.00005))
        for name, ok in chk:
            anchors.append([name, ok])
            if not ok:
                fails.append("anchor " + name)
        open_items.append("MVLL 10/05 5-session 90th pct linear %.2f%% != design 5 +29.6%% (only the 10th pct anchors the "
                          "60-overlapping-returns reading; F5 fixes linear interpolation) - 확인 필요" % (up * 100))
    print(json.dumps({"selftest": "PASS" if not fails else "FAIL", "fails": fails, "anchors": anchors, "open": open_items}, ensure_ascii=False))
    return 0 if not fails else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    default_repo = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    a = sub.add_parser("check"); a.add_argument("--day", required=True); a.add_argument("--repo", default=default_repo); a.add_argument("--out")
    a.add_argument("--ignore-input-sha", action="store_true", help="historical self-check only (verdict INFO_*)")
    b = sub.add_parser("replay"); b.add_argument("--replay-json", required=True); b.add_argument("--repo", default=default_repo); b.add_argument("--out")
    c = sub.add_parser("selftest"); c.add_argument("--repo", default=default_repo)
    args = ap.parse_args(argv)
    if args.cmd == "check":
        return cmd_check(args)
    if args.cmd == "replay":
        return cmd_replay(args)
    return cmd_selftest(args)


if __name__ == "__main__":
    sys.exit(main())
