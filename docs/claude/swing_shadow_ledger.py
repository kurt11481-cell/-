#!/usr/bin/env python3
"""swing-shadow: shadow ledger for the 'small sleeve, prove it' swing path (pre-registration DRAFT, not fixed).

Pre-registration draft: docs/claude/swing-prereg-draft-2026-11-19.md (section 3 = the constants below).
Design: docs/claude/masterplan-recovery-amendment-2026-11-19.md section 12. Start variant (a)-T chosen by the user's
card 2026-11-19 21:37:45 KST ('기간 청산만'). Review: docs/claude/swing-prereg-review-2026-11-19.md (8 fixes, 2nd draft).

Read-only. Writes nothing. No orders, no quantities, no authority. Evidence weight 0. Returns only, never money.
Inputs: the signal ledger docs/claude/swing-signal-ledger.jsonl (append-only, committed; the judged sample reads only
this file), workspace/outputs/research-records/<KST day>/research-record.json (only to propose new ledger lines with
--new-lines) and workspace/outputs/regular-session-closes/history/<SYM>.close-history.json (verified closes).

Variant (a)-T:
  signal  = a '+' official fact with criterion_a true that is true in a record written no later than the session after
            the fact's event session (later = LATE, counted only). Same symbol + same event session = one signal.
  entry   = close of the first US session after the record's evaluation_session, and not before the record day.
  exit    = close HOLD_SESSIONS sessions later on the QQQ calendar. No price stop.
  yardstick (judged) = trade return - beta * QQQ return over the same closes, beta from BETA_LOOKBACK daily returns
            before entry (clipped to BETA_CLIP). Shown only: raw minus QQQ, cash, equal-weight population.
  cluster = same root with overlapping holding windows (CLUSTER_RULE 'overlap') or same entry ('same_entry').
  verdict = three-way at cluster checkpoints JUDGE_AT: PASS (mean >= MIN_MEAN_EXCESS, t >= PASS_T, double cost > 0,
            and the same with lost trades set to ADVERSE_EXCESS) / CLOSE (t < CLOSE_T, or the last checkpoint or
            DEADLINE passed without PASS) / CONTINUE. Display days show counts, statuses and data loss only.
  checkpoint log = docs/claude/swing-verdict-log.jsonl (append-only, by hand from --verdict-lines). A checkpoint
            already logged keeps its first result; data loss and the adverse re-count at a checkpoint use only
            trades dated up to that checkpoint's last exit. LATE uses the QQQ trading calendar (review 7, 2nd look).

--selftest checks the arithmetic on synthetic series (no real prices).
Usage (repo root): python docs/claude/swing_shadow_ledger.py --as-of YYYY-MM-DD [--json] | --new-lines
                   | --verdict-lines --as-of YYYY-MM-DD | --selftest
Ledger lines are appended only as printed by --new-lines (never typed by hand), so no field such as 'late' is lost.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RECORDS_DIR = "workspace/outputs/research-records"
CLOSES_DIR = "workspace/outputs/regular-session-closes/history"
LEDGER = "docs/claude/swing-signal-ledger.jsonl"
VERDICT_LOG = "docs/claude/swing-verdict-log.jsonl"   # append-only; first result at each checkpoint, by hand
ROOTS_ADDED = "docs/claude/swing-roots.jsonl"          # append-only {symbol, root, added_on}: names joining after FIX_DATE
CLOSE_FILLS = "docs/claude/swing-close-fills.jsonl"    # append-only {symbol, session_date, close, source}: judgment-day fills
IC_PROMPT = "docs/claude/scheduled-prompts/integrated-check-daily.txt"
BENCH = "QQQ"

# ---- Pre-registration constants (section 3). FIXED by the user's card 2026-11-19 22:35:51 KST '엄격 세트 (권장)'. ----
# Changing any value below = a new variant (section 3 row 12), except roots added via ROOTS_ADDED before a signal.
FIX_DATE: str | None = "2026-11-19"         # ledger lines whose record day is after FIX_DATE form the judged sample
VARIANT = "a_T_official_fact_hold"   # user card 2026-11-19 21:37:45 KST
POPULATION: tuple[str, ...] | None = ("MU", "DELL", "PWR", "LITE", "BE", "PLTR", "CRWD")
HOLD_SESSIONS: int | None = 20
COST_BP_ROUND_TRIP: float | None = 50.0
BETA_LOOKBACK = 120                  # daily returns before entry
BETA_MIN_OBS = 60                    # fewer -> NO_BETA (lost)
BETA_CLIP: tuple[float, float] | None = None
ROOT_OF: dict[str, str] = {"MU": "ai_dc_power", "DELL": "ai_dc_power", "PWR": "ai_dc_power", "LITE": "ai_dc_power",
                            "BE": "ai_dc_power", "PLTR": "software", "CRWD": "software"}  # must cover POPULATION
CLUSTER_RULE = "overlap"             # 'overlap' (default, review 3-5) | 'same_entry'
JUDGE_AT: tuple[int, ...] | None = (12, 24, 36, 48)    # clusters (card 2)
DEADLINE: str | None = "2032-11-19"         # last day; no PASS by then -> CLOSE
MIN_MEAN_EXCESS: float | None = 0.0
PASS_T: float | None = 2.3         # review 2: 2.3 for four looks
CLOSE_T: float | None = -1.0        # review 2: 0 (or -1)
MAX_DATA_LOSS: float | None = 0.10  # share of lost trades among those whose exit has passed; above -> no PASS
ADVERSE_EXCESS: float | None = -0.50  # lost trades booked at this excess in the second pass (e.g. -0.50)
SPLIT_RATIOS = (2, 3, 4, 5, 10, 1.5, 1 / 2, 1 / 3, 1 / 4, 1 / 5, 1 / 10, 2 / 3)
SPLIT_TOL = 0.02
LOST = ("NO_PRICE", "DATA_GAP", "SPLIT_SUSPECT", "BENCH_GAP", "NO_BETA", "MALFORMED")


def sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def load_closes(symbol: str, repo: Path = REPO) -> dict[str, float]:
    path = repo / CLOSES_DIR / f"{symbol}.close-history.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    out = {s["session_date"]: float(s["close"]) for s in data.get("sessions") or []
           if s.get("verified") is True and s.get("close") not in (None, "")}
    for f in _jsonl(repo / CLOSE_FILLS):          # fills only add missing sessions, never overwrite a verified close
        if f.get("symbol") == symbol and _valid_day(f.get("session_date")) and f.get("close") not in (None, ""):
            out.setdefault(f["session_date"], float(f["close"]))
    return out


def _jsonl(path: Path) -> list[dict]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            x = json.loads(line)
        except ValueError:
            continue
        if isinstance(x, dict):
            out.append(x)
    return out


def roots_added(repo: Path = REPO) -> list[dict]:
    return [x for x in _jsonl(repo / ROOTS_ADDED) if x.get("symbol") and x.get("root") and _valid_day(x.get("added_on"))]


def in_scope(symbol: str, record_day: str, added: list[dict]) -> bool:
    """Fixed population, or a name whose root was written down before the signal's record day."""
    if POPULATION is not None and symbol in POPULATION:
        return True
    return any(x["symbol"] == symbol and str(x["added_on"]) < str(record_day) for x in added)


def _valid_day(value) -> bool:
    try:
        dt.date.fromisoformat(str(value))
        return True
    except ValueError:
        return False


def next_session(day: str, calendar: list[str]) -> str:
    """Next trading session after day on the QQQ close calendar; weekday fallback past the calendar's end."""
    later = [d for d in calendar if d > day]
    return later[0] if later else _next_weekday(day)


def _next_weekday(day: str) -> str:
    d = dt.date.fromisoformat(day) + dt.timedelta(days=1)
    while d.weekday() >= 5:
        d += dt.timedelta(days=1)
    return d.isoformat()


def candidate_signals(repo: Path = REPO) -> list[dict]:
    """Signals proposed from research records (for --new-lines). One per (symbol, event_session)."""
    first: dict[tuple, dict] = {}
    calendar = sorted(load_closes(BENCH, repo))
    for path in sorted((repo / RECORDS_DIR).glob("*/research-record.json")):
        try:
            rec = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        day = rec.get("record_day_kst") or path.parent.name
        ev = rec.get("evaluation_session")
        for fact in rec.get("official_facts") or []:
            if fact.get("direction") != "+" or fact.get("criterion_a") is not True:
                continue
            key = (fact.get("symbol"), fact.get("event_session"))
            if key in first:
                continue
            line = {"signal_id": f"{key[0]}-{key[1]}", "fact_id": fact.get("fact_id"), "symbol": key[0],
                    "event_session": key[1], "record_day": day, "evaluation_session": ev,
                    "written_at": rec.get("written_at"), "record_sha256": sha256_file(path),
                    "ic_prompt_sha256": sha256_file(repo / IC_PROMPT)}
            # true only in a record later than the one for the session after the event session -> LATE (count only)
            line["late"] = not (_valid_day(ev) and _valid_day(key[1]) and ev <= next_session(key[1], calendar))
            first[key] = line
    return sorted(first.values(), key=lambda s: (s["record_day"], s["symbol"] or ""))


def verdict_log(repo: Path = REPO) -> dict[int, str]:
    """Checkpoint -> first recorded result. Later runs follow the record, never recompute a past checkpoint."""
    out: dict = {}
    for x in _jsonl(repo / VERDICT_LOG):
        try:
            key = "final" if x.get("clusters") == "final" else int(x["clusters"])
            out.setdefault(key, str(x["result"]))
        except (ValueError, KeyError, TypeError):
            continue
    return out


def ledger_signals(repo: Path = REPO) -> list[dict]:
    try:
        lines = (repo / LEDGER).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        if line.strip():
            try:
                out.append(json.loads(line))
            except ValueError:
                out.append({"signal_id": "?", "malformed_line": line[:80]})
    return out


def beta(sym: dict[str, float], bench: dict[str, float], entry: str) -> tuple[float | None, int]:
    """(beta, number of split-like days dropped). Raw closes: a split day would poison the regression."""
    days = sorted(d for d in bench if d < entry and d in sym)[-(BETA_LOOKBACK + 1):]
    all_pairs = [(sym[a], sym[b], bench[a], bench[b]) for a, b in zip(days, days[1:])]
    pairs = [(sb / sa - 1, qb / qa - 1) for sa, sb, qa, qb in all_pairs if not _split_like(sa, sb)]
    dropped = len(all_pairs) - len(pairs)
    if len(pairs) < BETA_MIN_OBS:
        return None, dropped
    xs = [q for _, q in pairs]
    mx, my = statistics.mean(xs), statistics.mean(r for r, _ in pairs)
    var = sum((x - mx) ** 2 for x in xs)
    if var == 0:
        return None, dropped
    b = sum((q - mx) * (r - my) for r, q in pairs) / var
    if BETA_CLIP is not None:
        b = min(max(b, BETA_CLIP[0]), BETA_CLIP[1])
    return b, dropped


def _split_like(a: float, b: float) -> bool:
    ratio = b / a
    return any(abs(ratio / s - 1) <= SPLIT_TOL for s in SPLIT_RATIOS)


def trade(sig: dict, closes: dict[str, float], bench: dict[str, float], hold: int, cost_bp: float,
          population: dict[str, dict[str, float]] | None = None) -> dict:
    ev, day = sig.get("evaluation_session"), sig.get("record_day")
    if sig.get("late"):
        return {**sig, "status": "LATE"}
    if not (_valid_day(ev) and _valid_day(day)) or not sig.get("written_at"):
        return {**sig, "status": "MALFORMED"}
    sessions = sorted(d for d in bench if d > ev and d >= day)
    if not sessions:
        return {**sig, "status": "PENDING_ENTRY"}
    entry = sessions[0]
    if str(sig["written_at"])[:10] > entry:            # record written after the entry session -> future info
        return {**sig, "status": "MALFORMED", "entry": entry}
    if entry not in closes:
        return {**sig, "status": "NO_PRICE", "entry": entry}
    if len(sessions) <= hold:
        return {**sig, "status": "OPEN", "entry": entry, "held": len(sessions) - 1}
    window = sessions[:hold + 1]
    exit_day = window[hold]
    if any(entry < d < exit_day and d not in bench for d in closes):
        return {**sig, "status": "BENCH_GAP", "entry": entry, "exit": exit_day}
    if exit_day not in closes:
        return {**sig, "status": "DATA_GAP", "entry": entry, "exit": exit_day}
    seen = [closes[d] for d in window if d in closes]
    if any(_split_like(a, b) for a, b in zip(seen, seen[1:])):
        return {**sig, "status": "SPLIT_SUSPECT", "entry": entry, "exit": exit_day}
    b, dropped = beta(closes, bench, entry)
    if b is None:
        return {**sig, "status": "NO_BETA", "entry": entry, "exit": exit_day}
    r = closes[exit_day] / closes[entry] - 1 - cost_bp / 10000
    q = bench[exit_day] / bench[entry] - 1
    out = {**sig, "status": "CLOSED", "entry": entry, "exit": exit_day, "ret": r, "qqq": q, "beta": b,
           "excess": r - b * q, "excess_raw": r - q,
           "beta_split_days_dropped": dropped}
    if population:
        rets = [c[exit_day] / c[entry] - 1 for c in population.values() if entry in c and exit_day in c]
        out["excess_vs_population"] = r - statistics.mean(rets) if rets else None
    return out


def clusters(trades: list[dict], root_of: dict[str, str], rule: str = "overlap") -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    closed = sorted((t for t in trades if t["status"] == "CLOSED"), key=lambda t: t["entry"])
    if rule == "overlap":
        open_group: dict[str, tuple] = {}
        for t in closed:
            root = root_of.get(t["symbol"], t["symbol"])
            key = open_group.get(root)
            if key is None or t["entry"] > max(x["exit"] for x in groups[key]):
                key = (t["entry"], root)
                open_group[root] = key
            groups.setdefault(key, []).append(t)
    else:
        for t in closed:
            groups.setdefault((t["entry"], root_of.get(t["symbol"], t["symbol"])), []).append(t)
    return [{"entry": e, "root": r, "n": len(ts), "excess": statistics.mean(t["excess"] for t in ts),
             "exit": max(t["exit"] for t in ts)} for (e, r), ts in sorted(groups.items())]


def stats(ex_by_entry: list[tuple[str, float]]) -> dict:
    """Mean, and the larger of the plain and the quarter-block (cluster-robust) standard errors."""
    ex = [e for _, e in ex_by_entry]
    n = len(ex)
    if n < 2:
        return {"n": n, "mean": ex[0] if ex else None, "se": None, "t": None}
    m = statistics.mean(ex)
    se_plain = statistics.stdev(ex) / math.sqrt(n)
    blocks: dict[str, float] = {}
    for entry, e in ex_by_entry:
        q = f"{entry[:4]}Q{(int(entry[5:7]) - 1) // 3 + 1}"
        blocks[q] = blocks.get(q, 0.0) + (e - m)
    se_block = math.sqrt(sum(v * v for v in blocks.values())) / n if len(blocks) > 1 else se_plain
    se = max(se_plain, se_block)
    return {"n": n, "mean": m, "se": se, "t": m / se if se > 0 else None}


def _fixed() -> bool:
    if None in (FIX_DATE, POPULATION, HOLD_SESSIONS, COST_BP_ROUND_TRIP, JUDGE_AT, DEADLINE, MIN_MEAN_EXCESS,
                PASS_T, CLOSE_T, MAX_DATA_LOSS, ADVERSE_EXCESS):
        return False
    return all(s in ROOT_OF for s in POPULATION)


def verdict(cl: list[dict], cl2: list[dict], lost_dates: list[str], matured_dates: list[str], as_of: str,
            recorded: dict | None = None) -> dict:
    """Three-way sequential verdict at the checkpoints reached (clusters ordered by exit).

    Data loss and adverse re-count at a checkpoint use only trades dated up to that checkpoint's last exit.
    A checkpoint already in the verdict log keeps its recorded result (a closed variant cannot come back)."""
    recorded = recorded or {}
    if recorded.get("final") == "CLOSE":
        return {"verdict": "CLOSE", "reason": "final close in the verdict log", "from_log": True}
    if not _fixed():
        return {"verdict": "NOT_FIXED"}
    order = sorted(cl, key=lambda c: c["exit"])
    order2 = sorted(cl2, key=lambda c: c["exit"])
    looks = []
    for k in JUDGE_AT:
        if k in recorded:
            looks.append({"clusters": k, "result": recorded[k], "from_log": True})
            if recorded[k] in ("PASS", "CLOSE"):
                return {"verdict": recorded[k], "looks": looks}
            continue
        if len(order) < k or order[k - 1]["exit"] > DEADLINE:   # a checkpoint after the deadline is never judged
            break
        cut_day = order[k - 1]["exit"]
        lost_k = [d for d in lost_dates if d <= cut_day]
        mat_k = [d for d in matured_dates if d <= cut_day]
        data_loss = len(lost_k) / len(mat_k) if mat_k else 0.0
        s = stats([(c["entry"], c["excess"]) for c in order[:k]])
        s2 = stats([(c["entry"], c["excess"]) for c in order2[:k]])
        adv = stats([(c["entry"], c["excess"]) for c in order[:k]] + [(d, ADVERSE_EXCESS) for d in lost_k])
        half = k // 2
        look = {"clusters": k, "mean": s["mean"], "t": s["t"], "double_cost_mean": s2["mean"],
                "adverse_t": adv["t"], "data_loss": data_loss,
                "g4_halves_positive_shown_only": half > 0
                and statistics.mean(c["excess"] for c in order[:half]) > 0
                and statistics.mean(c["excess"] for c in order[half:k]) > 0}
        if data_loss > MAX_DATA_LOSS:
            look["result"] = "CONTINUE_DATA_LOSS"
        elif (s["mean"] is not None and s["mean"] >= MIN_MEAN_EXCESS and (s["t"] or -9) >= PASS_T
              and (s2["mean"] or -1) > 0 and (adv["t"] or -9) >= PASS_T and (adv["mean"] or -1) >= MIN_MEAN_EXCESS):
            look["result"] = "PASS"
        elif s["t"] is not None and s["t"] < CLOSE_T:
            look["result"] = "CLOSE"
        else:
            look["result"] = "CONTINUE"
        looks.append(look)
        look["new_log_line"] = {"clusters": k, "result": look["result"], "cut_day": cut_day, "first_seen": as_of}
        if look["result"] in ("PASS", "CLOSE"):
            return {"verdict": look["result"], "looks": looks}
    if as_of > DEADLINE or len(order) >= JUDGE_AT[-1]:
        return {"verdict": "CLOSE", "reason": "last checkpoint or deadline without PASS", "looks": looks,
                "new_log_line": {"clusters": "final", "result": "CLOSE", "first_seen": as_of}}
    return {"verdict": "CONTINUE", "looks": [{k: v for k, v in x.items() if k in ("clusters", "result", "from_log", "new_log_line")} for x in looks]}


def run(as_of: str, today: str | None = None) -> dict:
    today = today or dt.date.today().isoformat()
    sigs = ledger_signals()
    added = roots_added()
    scoped = [s for s in sigs if in_scope(str(s.get("symbol")), str(s.get("record_day", "")), added)]
    base = {"variant": VARIANT, "as_of": as_of, "fixed": _fixed(), "ledger_lines": len(sigs),
            "no_root_counted_only": len(sigs) - len(scoped),
            "candidates_from_records": len(candidate_signals())}
    if not _fixed() or as_of > today:
        base["note"] = "not fixed or future date: counts only, no returns (pre-registration discipline)"
        return base
    cut = lambda c: {d: v for d, v in c.items() if d <= as_of}
    main = [s for s in scoped if str(s.get("record_day", "")) > FIX_DATE and str(s.get("record_day", "")) <= as_of]
    bench = cut(load_closes(BENCH))
    roots = {**{x["symbol"]: x["root"] for x in added}, **ROOT_OF}
    pop = {p: cut(load_closes(p)) for p in roots}

    def book(cost: float) -> list[dict]:
        return [trade(x, cut(load_closes(x["symbol"])), bench, HOLD_SESSIONS, cost, pop) for x in main]

    trades = book(COST_BP_ROUND_TRIP)
    status = {k: sum(1 for t in trades if t["status"] == k) for k in sorted({t["status"] for t in trades})}
    matured = [t for t in trades if t["status"] in LOST + ("CLOSED",)]
    lost = [t for t in matured if t["status"] in LOST]
    data_loss = len(lost) / len(matured) if matured else 0.0
    when = lambda t: t.get("exit") or t.get("entry") or t.get("record_day") or as_of
    lost_dates = [when(t) for t in lost]
    matured_dates = [when(t) for t in matured]
    cl = clusters(trades, roots, CLUSTER_RULE)
    cl2 = clusters(book(2 * COST_BP_ROUND_TRIP), roots, CLUSTER_RULE)
    # counts, statuses, data loss and the verdict only — no running mean on non-checkpoint days (review 9)
    return {**base, "trade_status": status, "clusters": len(cl), "data_loss": data_loss,
            "verdict": verdict(cl, cl2, lost_dates, matured_dates, as_of, verdict_log())}


def selftest() -> None:
    global FIX_DATE, POPULATION, HOLD_SESSIONS, COST_BP_ROUND_TRIP, ROOT_OF, JUDGE_AT, DEADLINE, MIN_MEAN_EXCESS
    global PASS_T, CLOSE_T, MAX_DATA_LOSS, ADVERSE_EXCESS
    names = ("FIX_DATE", "POPULATION", "HOLD_SESSIONS", "COST_BP_ROUND_TRIP", "ROOT_OF", "JUDGE_AT", "DEADLINE",
             "MIN_MEAN_EXCESS", "PASS_T", "CLOSE_T", "MAX_DATA_LOSS", "ADVERSE_EXCESS")
    saved = {k: globals()[k] for k in names}
    days, d = [], dt.date(2026, 1, 1)
    while len(days) < 200:
        if d.weekday() < 5:
            days.append(d.isoformat())
        d += dt.timedelta(days=1)
    bench = {x: 100 * (1.001 ** i) * (1 + 0.01 * ((-1) ** i)) for i, x in enumerate(days)}
    hi_beta = {x: 50 * (bench[x] / 100) ** 2 for x in days}           # about beta 2 to QQQ, no skill
    n = 0

    def ok(cond, what):
        nonlocal n
        assert cond, what
        n += 1
    e0 = days[150]
    sig = {"signal_id": "S", "symbol": "HB", "record_day": e0, "evaluation_session": days[149],
           "written_at": e0 + "T06:50:00+09:00", "late": False}
    t = trade(sig, hi_beta, bench, 10, 0)
    ok(t["status"] == "CLOSED" and t["entry"] == e0 and t["exit"] == days[160], t)
    ok(abs(t["beta"] - 2) < 0.15, t["beta"])
    ok(abs(t["excess"]) < abs(t["excess_raw"]) or abs(t["excess_raw"]) < 1e-9, "beta adjustment removes beta drift")
    ok(trade({**sig, "evaluation_session": None}, hi_beta, bench, 10, 0)["status"] == "MALFORMED", "no eval session")
    early = {**sig, "record_day": days[170]}
    ok(trade(early, hi_beta, bench, 10, 0)["entry"] == days[170], "never enter before the record day")
    ok(trade({**sig, "written_at": days[152] + "T06:50"}, hi_beta, bench, 10, 0)["status"] == "MALFORMED", "written late")
    ok(trade({**sig, "late": True}, hi_beta, bench, 10, 0)["status"] == "LATE", "late signal")
    gap = {k: v for k, v in hi_beta.items() if k != days[160]}
    ok(trade(sig, gap, bench, 10, 0)["status"] == "DATA_GAP", "gap on exit day")
    # split/crash tests use a calm series (daily moves well under the 2% split tolerance)
    calm_b = {x: 100 * (1.001 ** i) * (1 + 0.002 * ((-1) ** i)) for i, x in enumerate(days)}
    calm = {x: 50 * (calm_b[x] / 100) ** 2 for x in days}
    split = {k: (v * 2 / 3 if k >= days[155] else v) for k, v in calm.items()}
    ok(trade(sig, split, calm_b, 10, 0)["status"] == "SPLIT_SUSPECT", "3:2 split")
    crash = {k: (v * 0.55 if k >= days[155] else v) for k, v in calm.items()}
    ok(trade(sig, crash, calm_b, 10, 0)["status"] == "CLOSED", "a real -45% day is kept")
    split_hist = {k: (v / 4 if k >= days[100] else v) for k, v in calm.items()}   # 4:1 split inside the beta window
    tb = trade(sig, split_hist, calm_b, 10, 0)
    ok(tb["status"] == "CLOSED" and tb["beta_split_days_dropped"] == 1 and abs(tb["beta"] - 2) < 0.2,
       "a split day in the beta window is dropped from the regression")
    short_hist = {k: v for k, v in hi_beta.items() if k >= days[120]}
    ok(trade(sig, short_hist, bench, 10, 0)["status"] == "NO_BETA", "too little history")
    bgap = {k: v for k, v in bench.items() if k != days[155]}
    ok(trade(sig, hi_beta, bgap, 10, 0)["status"] == "BENCH_GAP", "bench gap")
    a = {"symbol": "MU", "status": "CLOSED", "entry": days[150], "exit": days[160], "excess": 0.1}
    b2 = {**a, "symbol": "DELL", "entry": days[152], "exit": days[162]}
    ok(len(clusters([a, b2], {}, "overlap")) == 2 and len(clusters([a, b2], {"MU": "r", "DELL": "r"}, "overlap")) == 1,
       "empty root map does not cluster; filled map does")
    FIX_DATE, POPULATION, HOLD_SESSIONS, COST_BP_ROUND_TRIP = "2026-01-01", ("MU",), 10, 20
    JUDGE_AT, DEADLINE, MIN_MEAN_EXCESS, PASS_T, CLOSE_T = (4, 8), "2030-01-01", 0.0, 2.3, 0.0
    MAX_DATA_LOSS, ADVERSE_EXCESS = 0.2, -0.5
    ROOT_OF = {}
    ok(verdict([], [], [], [], "2027-01-01")["verdict"] == "NOT_FIXED", "root map must cover population")
    ROOT_OF = {"MU": "r"}
    good = [{"entry": f"2027-{m:02d}-01", "exit": f"2027-{m:02d}-15", "excess": 0.05 + 0.001 * m} for m in range(1, 9)]
    ex = [c["exit"] for c in good]
    v = verdict(good, good, [], ex, "2027-12-31")
    ok(v["verdict"] == "PASS" and v["looks"][0]["g4_halves_positive_shown_only"] is True, "steady positive passes")
    ok(verdict(good, good, [good[0]["exit"]], ex + [good[0]["exit"]], "2027-12-31")["verdict"] != "PASS",
       "adverse lost trades block a pass")
    bad = [{**c, "excess": -c["excess"]} for c in good]
    ok(verdict(bad, bad, [], ex, "2027-12-31")["verdict"] == "CLOSE", "negative closes")
    many_lost = [good[0]["exit"]] * 8
    ok(verdict(good, good, many_lost, ex + many_lost, "2027-12-31")["verdict"] == "CLOSE",
       "data loss never passes; last look closes")
    ok(verdict(good[:3], good[:3], [], ex[:3], "2027-06-01")["verdict"] == "CONTINUE", "before first checkpoint")
    late_lost = ["2028-06-01"] * 8                                    # lost after the first checkpoint's cut day
    ok(verdict(good, good, late_lost, ex + late_lost, "2028-12-31")["verdict"] == "PASS",
       "loss at a checkpoint counts only trades up to its cut day")
    ok(verdict(good, good, [], ex, "2027-12-31", {4: "CLOSE"})["verdict"] == "CLOSE",
       "a recorded CLOSE stays closed even if today's numbers would pass")
    DEADLINE = "2027-03-01"                                           # 4th exit (2027-04-15) is after the deadline
    vd = verdict(good, good, [], ex, "2027-12-31")
    ok(vd["verdict"] == "CLOSE" and vd["looks"] == [] and vd["new_log_line"]["clusters"] == "final",
       "a checkpoint after the deadline is never judged; the final close is logged")
    DEADLINE = "2030-01-01"
    ok(verdict(good, good, [], ex, "2027-12-31", {"final": "CLOSE"})["verdict"] == "CLOSE",
       "a logged final close stays closed")
    POPULATION = ("MU",)
    added = [{"symbol": "CRWD", "root": "sw", "added_on": "2026-12-01"}]
    ok(in_scope("MU", "2026-11-20", added) and in_scope("CRWD", "2026-12-02", added)
       and not in_scope("CRWD", "2026-12-01", added) and not in_scope("NBIS", "2027-01-01", added),
       "a new name counts only if its root was written before the signal")
    cal = ["2026-11-24", "2026-11-25", "2026-11-27", "2026-11-30"]  # 11-26 Thanksgiving
    ok(next_session("2026-11-25", cal) == "2026-11-27" and next_session("2026-11-30", cal) == "2026-12-01",
       "LATE uses the trading calendar (holiday) with weekday fallback")
    globals().update(saved)                                            # back to the fixed constants
    ok(_fixed() and all(s in ROOT_OF for s in POPULATION), "the fixed constants are complete")
    ok("note" in run("2999-01-01", today="2026-11-19"), "future as_of computes nothing")
    print(f"selftest OK ({n} checks)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default=dt.date.today().isoformat())
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--new-lines", action="store_true", help="print candidate ledger lines not yet in the ledger")
    ap.add_argument("--verdict-lines", action="store_true", help="print checkpoint results not yet in the verdict log")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    if a.new_lines:
        have = {s.get("signal_id") for s in ledger_signals()}
        for line in candidate_signals():
            if line["signal_id"] not in have:
                print(json.dumps(line, ensure_ascii=False))
        return
    res = run(a.as_of)
    if a.verdict_lines:
        v = res.get("verdict") or {}
        for look in v.get("looks") or []:
            if "new_log_line" in look:
                print(json.dumps(look["new_log_line"], ensure_ascii=False))
        if "new_log_line" in v:
            print(json.dumps(v["new_log_line"], ensure_ascii=False))
        return
    print(json.dumps(res, ensure_ascii=False, indent=1) if a.json else "\n".join(f"{k}: {v}" for k, v in res.items()))


if __name__ == "__main__":
    main()
