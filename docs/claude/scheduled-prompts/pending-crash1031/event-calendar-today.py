"""event-calendar-today.py — deterministic helper for the '개장 전 이벤트 점검(일정표)' scheduled task.

Display/record only (CONTEXT_ONLY, workspace/policies/event_risk_policy.json). No orders, gates or budgets.
Reads docs/claude/event-calendar.json. Stdlib only.

  python3 event-calendar-today.py [--date YYYY-MM-DD] [--calendar PATH]
      -> JSON plan for that US/Eastern date (default: today in America/New_York):
         due (report today), preview (scheduled later today), legacy_today (handled by old one-shot tasks),
         window (NOT_ANNOUNCED rows whose estimate window covers today), watch_due, week (Mondays only),
         refresh_due, empty
  python3 event-calendar-today.py --check-record PATH [--date D]
      -> exit 0 when every due id appears in the record on a line with an allowed-domain URL or '확인 필요'
  python3 event-calendar-today.py --append ROWS.json [--backup-dir DIR]
      -> append-only calendar extension: {"horizon_end": "YYYY-MM-DD", "events": [...]}; validates, backs up, writes
  python3 event-calendar-today.py --reduce-window [--now SOXL_PREMARKET --base SOXL_BASE_CLOSE] [--date D]
                                   [--core-dir DIR] [--preopen-dir DIR]
      -> read-only 'rebound reduce' display for the user's decision crash-1031 (2026-10-31 20:24 KST: exposure E below
         1.9, the system says when): state none | wait | rebound | deadline | unknown, notify (push today or not),
         one Korean line for the record, a short push text, check (what needs a look, or null) and check_new (not
         already in the previous session's record). Reads workspace/outputs/auto-core and earlier
         workspace/outputs/pre-open/<date>-events*.md records only. No orders, quantities or prices are proposed.
"""
import argparse
import datetime as dt
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
import json
import os
import re
import sys
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CAL = os.path.join(HERE, "event-calendar.json")
ET = ZoneInfo("America/New_York")
KST = ZoneInfo("Asia/Seoul")
RUN_TIME_ET = "09:20"
REPORTABLE = {"VERIFIED", "REPORTED", "COMPUTED"}
STATUSES = REPORTABLE | {"NOT_ANNOUNCED"}
KINDS = {"macro_release", "central_bank", "earnings", "election", "options_expiration", "market_holiday"}
REQUIRED = ("id", "kind", "tier", "label", "event_date", "report_date", "status", "source_url", "checked_at")
DEFAULT_CORE = os.path.join(HERE, "..", "..", "workspace", "outputs", "auto-core")
DEFAULT_PREOPEN = os.path.join(HERE, "..", "..", "workspace", "outputs", "pre-open")
REDUCE_START = "2026-10-30"  # latest core session when the user decided (crash-response-proposal-2026-10-31.md 6 9 10)
REDUCE_E = 1.9               # hard ceiling (alert_policy.json hard_ceiling_when_exposure_gte)
REDUCE_BOUNCE = 0.10         # SOXL 10% above the lowest close of the last 21 sessions (core close_low_20 = prior 20
                             # sessions, auto_core_rules.py 240, plus the latest close) = rebound (unvalidated display rule)
REDUCE_EVERY = 5             # deadline after 5 sessions above 1.9; at most one rebound push and one deadline push per
                             # 5 sessions, read back from the earlier pre-open records (a missed run does not drop it)
REDUCE_BASE_TOL = 0.005      # the premarket quote's base close must match the core SOXL close within 0.5%
REDUCE_NOW_RANGE = (0.5, 1.5)
REDUCE_MAX_FOLDERS = 250     # newest run folders read back when counting the run of E >= 1.9
_LEAD = r"^[\s\u200b\ufeff\-*>`|_]*"  # tolerate list / quote / bold / table / code markers a writer may add
ALERT_RE = re.compile(_LEAD + r"(?:0-3\)\s*)?(?:줄이기\s*[:：]\s*)?줄이기\s*(적기|기한)\s*[(（]")  # not '적기 계속('
CHECK_RE = re.compile(_LEAD + r"줄이기\s*확인\s*필요\s*[:：]\s*(.*)$")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def today_et():
    return dt.datetime.now(ET).date()


def d(s):
    return dt.date.fromisoformat(s) if s else None


def plan(cal, day):
    evs = cal["events"]
    due, preview, legacy, window = [], [], [], []
    for r in evs:
        ed, rd = d(r["event_date"]), d(r.get("report_date"))
        if r["status"] == "NOT_ANNOUNCED":
            w = r.get("window")
            if w and d(w[0]) <= day <= d(w[1]):
                window.append(r)
            continue
        if r.get("legacy_trigger") and (rd == day or ed == day):
            legacy.append(r)
            continue
        if r["kind"] in ("market_holiday", "options_expiration"):
            if ed == day and r.get("time_et"):
                preview.append(r)
            continue
        if rd == day and r["status"] in REPORTABLE:
            due.append(r)
        elif ed == day:
            preview.append(r)
    # Follow-up: the next weekday after a CPI release, read the market's interpretation (2y Treasury change on the
    # release day vs the prior day, official Treasury daily par yield curve). Display only. Includes legacy rows.
    prev = day - dt.timedelta(days=3 if day.weekday() == 0 else 1)
    for r in evs:
        if r["kind"] == "macro_release" and r["id"].startswith("us-cpi-") and r.get("report_date") == prev.isoformat():
            ym = r["report_date"][:4] + r["report_date"][5:7]
            due.append({"id": r["id"] + "-followup", "kind": "macro_followup", "tier": r["tier"],
                        "label": r["label"] + " 시장 해석(발표일 2년물 금리 변화)", "event_date": r["event_date"],
                        "report_date": day.isoformat(), "status": "VERIFIED",
                        "result_url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
                                      "TextView?type=daily_treasury_yield_curve&field_tdr_date_value_month=" + ym,
                        "source_url": r.get("source_url"),
                        "note": "발표일(" + r["report_date"] + ")과 그 전 영업일의 2 Yr 값 차이(bp)로 판정표의 H/N/D"})
    watch_due = []
    for w in cal.get("watch", []):
        win = w.get("window")
        in_win = bool(win) and d(win[0]) <= day <= d(win[1])
        if day.weekday() == 0 or in_win:
            watch_due.append(w)
    week = []
    if day.weekday() == 0:
        end = day + dt.timedelta(days=4)
        week = [r for r in evs if day <= d(r["event_date"]) <= end]
    refresh_due = day.weekday() == 0 and day + dt.timedelta(days=30) > d(cal["horizon_end"])
    slim = lambda rows: [{k: r.get(k) for k in ("id", "kind", "tier", "label", "event_date", "time_et", "time_kst",
                                                  "report_date", "status", "result_url", "source_url", "window",
                                                  "legacy_trigger", "note") if r.get(k) is not None} for r in rows]
    out = {"date_et": day.isoformat(), "weekday": day.strftime("%a"), "due": slim(due), "preview": slim(preview),
           "legacy_today": slim(legacy), "window": slim(window), "watch_due": watch_due, "week": slim(week),
           "refresh_due": refresh_due, "horizon_end": cal["horizon_end"]}
    closed = any(r["kind"] == "market_holiday" and d(r["event_date"]) == day and not r.get("time_et") for r in evs)
    main_preview = [r for r in preview if r.get("tier") in ("A", "B")]
    out["market_closed"] = closed
    out["empty"] = closed or not (due or main_preview or window or watch_due or week or refresh_due)
    return out


def domain_ok(url, allowed):
    m = re.match(r"https?://([^/]+)", url or "")
    host = m.group(1).lower() if m else ""
    return any(host == a or host.endswith("." + a) for a in allowed)


def check_record(cal, day, path):
    text = open(path, encoding="utf-8").read().splitlines()
    missing = []
    for r in plan(cal, day)["due"]:
        ok = False
        for line in text:
            if r["id"] in line:
                urls = re.findall(r"https?://\S+", line)
                if "확인 필요" in line or any(domain_ok(u, cal["allowed_source_domains"]) for u in urls):
                    ok = True
                    break
        if not ok:
            missing.append(r["id"])
    print(json.dumps({"record": path, "date_et": day.isoformat(), "missing": missing}, ensure_ascii=False))
    return 0 if not missing else 1


def validate_row(r, allowed, known_ids):
    errs = []
    for k in REQUIRED:
        if k not in r:
            errs.append(f"{r.get('id')}: missing {k}")
    if errs:
        return errs
    if r["id"] in known_ids:
        errs.append(f"{r['id']}: duplicate id")
    if r["kind"] not in KINDS:
        errs.append(f"{r['id']}: bad kind")
    if r["status"] not in STATUSES:
        errs.append(f"{r['id']}: bad status")
    try:
        ed = d(r["event_date"])
        rd = d(r["report_date"]) if r["report_date"] else None
        if rd and rd < ed:
            errs.append(f"{r['id']}: report_date before event_date")
    except ValueError:
        errs.append(f"{r['id']}: bad date")
    for u in (r.get("source_url"), r.get("result_url")):
        if u and not domain_ok(u, allowed):
            errs.append(f"{r['id']}: domain not allowed {u}")
    if r["status"] != "COMPUTED" and not r.get("source_url"):
        errs.append(f"{r['id']}: source_url required")
    if r.get("time_et") and not re.fullmatch(r"\d{2}:\d{2}", r["time_et"]):
        errs.append(f"{r['id']}: bad time_et")
    return errs


def append(cal_path, rows_path, backup_dir):
    cal = load(cal_path)
    add = load(rows_path)
    new_h = add.get("horizon_end")
    if not new_h or d(new_h) <= d(cal["horizon_end"]):
        print(json.dumps({"ok": False, "error": "horizon_end must move forward"}))
        return 2
    known = {r["id"] for r in cal["events"]}
    errs, rows = [], add.get("events", [])
    for r in rows:
        errs += validate_row(r, cal["allowed_source_domains"], known)
        known.add(r.get("id"))
        if r.get("event_date") and d(r["event_date"]) <= d(cal["horizon_end"]):
            errs.append(f"{r.get('id')}: not after current horizon_end (append-only)")
    if errs or not rows:
        print(json.dumps({"ok": False, "errors": errs or ["no rows"]}, ensure_ascii=False))
        return 2
    for r in rows:
        if r.get("time_et") and ":" in r["time_et"]:
            h, m = map(int, r["time_et"].split(":"))
            x = dt.datetime.fromisoformat(r["event_date"]).replace(hour=h, minute=m, tzinfo=ET)
            r["time_kst"] = x.astimezone(KST).strftime("%Y-%m-%d %H:%M")
    os.makedirs(backup_dir, exist_ok=True)
    stamp = dt.datetime.now(KST).strftime("%Y%m%dT%H%M")
    with open(os.path.join(backup_dir, f"event-calendar-{stamp}.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(cal, f, ensure_ascii=False, indent=1)
    cal["events"] = sorted(cal["events"] + rows, key=lambda r: (r["event_date"], r["id"]))
    cal["horizon_end"] = new_h
    cal["updated_at"] = dt.datetime.now(KST).isoformat(timespec="minutes")
    tmp = cal_path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(cal, f, ensure_ascii=False, indent=1)
        f.write("\n")
    load(tmp)
    os.replace(tmp, cal_path)
    print(json.dumps({"ok": True, "added": [r["id"] for r in rows], "horizon_end": new_h}, ensure_ascii=False))
    return 0


def num(x):
    if isinstance(x, bool):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != float("inf") else None


def dig(obj, *keys):
    for k in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(k)
    return obj


def iso_day(s):
    if not isinstance(s, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return None
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return None


def prev_session(cal, day):
    closed = {d(r["event_date"]) for r in cal["events"] if r["kind"] == "market_holiday" and not r.get("time_et")}
    p = day - dt.timedelta(days=1)
    while p.weekday() >= 5 or p in closed:
        p -= dt.timedelta(days=1)
    return p


def s7_e(j):
    """S7 E of one core result, or None unless it belongs to that result's own evaluation session."""
    s, s7 = iso_day(dig(j, "evaluation_session")), dig(j, "exposure", "S7")
    if s is None or dig(s7, "session") != s.isoformat() or dig(s7, "fresh") is not True:
        return s, None
    return s, num(dig(s7, "E"))


def last_below(core_dir, session):
    """Latest session before `session` (and not before REDUCE_START) whose own core result shows E < 1.9, reading the
    dated run folders newest first and stopping at the first one found. None when there is none."""
    floor = d(REDUCE_START)
    try:
        names = sorted((n for n in os.listdir(core_dir) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", n)), reverse=True)
    except OSError:
        return None
    for name in names[:REDUCE_MAX_FOLDERS]:
        if name < REDUCE_START:
            break
        try:
            s, e = s7_e(load(os.path.join(core_dir, name, "decision.json")))
        except (OSError, ValueError):
            continue
        if s is not None and floor <= s < session and e is not None and e < REDUCE_E:
            return s
    return None


def run_of_sessions(cal, stop, session):
    """(count, first) of market sessions from max(REDUCE_START, session after `stop`) to `session`. Sessions whose E is
    unknown (core HOLD, missing run folder) do not end the run."""
    floor = d(REDUCE_START)
    stop = stop or floor - dt.timedelta(days=1)
    n, first, p = 0, session, session
    while p > stop and p >= floor:
        n, first = n + 1, p
        p = prev_session(cal, p)
    return max(n, 1), first


def check_kind(text):
    return re.split(r"[(:：]", text, maxsplit=1)[0].strip()


def read_records(cal, day, preopen_dir, first):
    """From the pre-open records of the previous REDUCE_EVERY - 1 sessions (today excluded, none before the run's first
    session): latest session holding a rebound / deadline line, and the check kinds of the previous session's record."""
    seen, prev_kinds = {"rebound": None, "deadline": None}, set()
    try:
        names = sorted(os.listdir(preopen_dir))
    except OSError:
        return seen, prev_kinds
    p = day
    for i in range(REDUCE_EVERY - 1):
        p = prev_session(cal, p)
        pat = re.compile(re.escape(p.isoformat()) + r"-events(-\d+)?\.md")
        for name in (n for n in names if pat.fullmatch(n)):
            try:
                with open(os.path.join(preopen_dir, name), encoding="utf-8", errors="replace") as f:
                    lines = f.read().splitlines()
            except OSError:
                continue
            for line in lines:
                m = ALERT_RE.match(line)
                key = {"적기": "rebound", "기한": "deadline"}.get(m.group(1)) if m else None
                if key and seen[key] is None and p >= first:
                    seen[key] = p.isoformat()
                c = CHECK_RE.match(line) if i == 0 else None
                if c:
                    prev_kinds.update(check_kind(x) for x in c.group(1).split(" · ") if x.strip())
    return seen, prev_kinds


def reduce_window(cal, day, core_dir, preopen_dir, now, base):
    out = {"mode": "reduce-window", "date_et": day.isoformat(), "state": "unknown", "notify": False, "push": None,
           "check": None, "check_new": False}
    expected = prev_session(cal, day)
    out["expected_session"] = expected.isoformat()

    def finish(checks):
        out["check"] = " · ".join(checks) or None
        if checks:
            _, prev_kinds = read_records(cal, day, preopen_dir, expected)
            out["check_new"] = any(check_kind(c) not in prev_kinds for c in checks)
        return out

    def unknown(why):
        out["line"] = f"줄이기 확인 불가({why})"
        return finish([why])

    try:
        latest = load(os.path.join(core_dir, "LATEST_DECISION.json"))
    except (OSError, ValueError):
        return unknown("코어 결과 파일을 읽지 못함")
    s7, session_s = dig(latest, "exposure", "S7"), dig(latest, "evaluation_session")
    e = num(dig(s7, "E"))
    out.update({"E": e, "session": session_s})
    if e is None:
        return unknown("코어가 노출 E를 계산하지 못함")
    if session_s != expected.isoformat():
        return unknown(f"코어 결과가 직전 세션 것이 아님: {session_s}, 기대 {expected.isoformat()}")
    if dig(s7, "fresh") is not True:
        return unknown("코어 노출 값이 최신 세션 것이 아님")
    if dig(s7, "session") != session_s:
        return unknown(f"코어 노출 값이 직전 세션 것이 아님: {dig(s7, 'session')}, 기대 {session_s}")
    session, md = expected, f"{expected:%m/%d}"
    e_s = f"{e:.4f}"
    if (float(e_s) < REDUCE_E) != (e < REDUCE_E):
        e_s = repr(e)
    if e < REDUCE_E:
        out.update(state="none", line=f"줄이기 해당 없음: 노출 E {e_s} < 1.9({md} 세션)")
        return out
    n, first = run_of_sessions(cal, last_below(core_dir, session), session)
    run = f"{first:%m/%d}부터 1.9 위 {n}세션째"
    out.update(sessions_above=n, run_start=first.isoformat())

    checks, rebound, why = [], False, None
    cent = Decimal("0.01")
    ind = dig(latest, "symbols", "SOXL", "indicators")
    close, low20 = num(dig(ind, "close")), num(dig(ind, "close_low_20"))
    if close is None or close <= 0:
        why = "SOXL 반등 계산 불가(코어에 SOXL 종가 없음)"
    elif dig(ind, "session") != session_s:
        why = f"SOXL 반등 계산 불가(코어 SOXL 지표 세션 {dig(ind, 'session')} ≠ {session_s})"
    if why:
        checks.append(why)
        price_s = cond = None
    else:
        c = Decimal(repr(close)).quantize(cent, ROUND_HALF_UP)
        low = Decimal(repr(min(close, low20) if low20 is not None and low20 > 0 else close)).quantize(cent, ROUND_HALF_UP)
        threshold = (low * (1 + Decimal(repr(REDUCE_BOUNCE)))).quantize(cent, ROUND_CEILING)  # shown value = cutoff
        cond = (f"반등 조건: {threshold} 이상(21세션 최저 종가 {low} +10%)이고 직전 종가 이상 — 알림용 미검증 기준, "
                "주문 가격 아님")
        out.update(soxl_close=float(c), low21=float(low), threshold=float(threshold))
        price, ref = None, None
        if now is not None:
            nv, bv = num(now), num(base)
            if nv is None or nv <= 0:
                why = "개장 전 값 버림: 쓸 수 없는 값"
            elif bv is None or bv <= 0:
                why = "개장 전 값 버림: 같은 조회의 전일 종가 없음"
            elif abs(bv / close - 1) > REDUCE_BASE_TOL:
                why = f"개장 전 값 버림: 조회한 전일 종가 {bv:g} ≠ 코어 {md} 종가 {c}"
            elif not REDUCE_NOW_RANGE[0] <= nv / close <= REDUCE_NOW_RANGE[1]:
                why = f"개장 전 값 버림: {nv:g} — {md} 종가 {c}의 0.5~1.5배 밖"
            else:
                price = Decimal(repr(nv)).quantize(cent, ROUND_HALF_UP)
                ref = Decimal(repr(bv)).quantize(cent, ROUND_HALF_UP)
            if why:
                checks.append(why)
        if price is None:
            price_s, why = f"SOXL {c}({md} 종가)", why or "개장 전 값 없음"
        else:
            bounce = ((price / low - 1) * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)
            price_s = f"SOXL {price}(개장 전 조회)"
            out.update(soxl_premarket=float(price), base_close=float(ref), bounce_pct=float(bounce))
            if price < ref:
                why = f"하락 출발 — 직전 종가 {ref}보다 낮음"
            elif price < threshold:
                why = "반등 조건 미달"
            else:
                rebound = True

    seen, _ = read_records(cal, day, preopen_dir, first)
    out["recent_alerts"] = seen
    if rebound and seen["rebound"] is None:
        out.update(state="rebound", notify=True,
                   line=f"줄이기 적기(반등·표시만, 주문 아님): {price_s} = 21세션 최저 종가 {low}의 +{bounce}%, "
                        f"직전 종가 {ref} 이상 · 노출 E {e_s} ≥ 1.9 — 사장 결정(10/31)대로 1.9 아래로 줄일 때"
                        f"(수량은 사장 입력 + 주문 전 점검, 반등 10%는 미검증 기준) · {run}",
                   push=f"줄이기 적기(표시만·주문 아님): SOXL 개장 전 21세션 최저 종가 대비 +{bounce}%·전일 종가 이상 · "
                        f"노출 E {e_s} ≥ 1.9 — 사장 결정대로 1.9 아래로 줄일 때(수량은 사장 입력 + 주문 전 점검)")
    elif rebound:
        out.update(state="rebound",
                   line=f"줄이기 적기 계속(알림 {d(seen['rebound']):%m/%d} 보냄 · 표시만): {price_s} = 21세션 최저 "
                        f"종가 {low}의 +{bounce}% · 노출 E {e_s} ≥ 1.9 · {run}")
    elif n >= REDUCE_EVERY and seen["rebound"] is None and seen["deadline"] is None:
        if cond:
            tail = f"지금 {price_s}" + ("" if why == "반등 조건 미달" else f" — {why}") + f" · {cond}"
        else:
            tail = why
        out.update(state="deadline", notify=True,
                   line=f"줄이기 기한(표시만): 노출 E {e_s} ≥ 1.9 · {run}, 최근 5세션 반등 알림 없음 — 반등을 더 "
                        f"기다릴지 지금 줄일지 사장 결정 · {tail}",
                   push=f"줄이기 기한(표시만): 노출 E {e_s} ≥ 1.9가 {first:%m/%d}부터 {n}세션째, 최근 5세션 반등 없음 — "
                        "더 기다릴지 지금 줄일지 사장 결정")
    else:
        last = max(s for s in (seen["rebound"], seen["deadline"], "") if s is not None)
        recent = f" · 최근 줄이기 알림 {d(last):%m/%d}" if n >= REDUCE_EVERY and last else ""
        body = f"{price_s} · {cond}" if cond else ""
        out.update(state="wait", line=f"줄이기 대기({why}): 노출 E {e_s} ≥ 1.9 · " + (body + " · " if body else "")
                                       + f"{run}{recent}")
    return finish(checks)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--calendar", default=DEFAULT_CAL)
    ap.add_argument("--check-record")
    ap.add_argument("--append")
    ap.add_argument("--backup-dir", default=os.path.join(HERE, "..", "..", "workspace", "outputs", "pre-open",
                                                         "_calendar-backup"))
    ap.add_argument("--reduce-window", action="store_true")
    ap.add_argument("--now")
    ap.add_argument("--base")
    ap.add_argument("--core-dir", default=DEFAULT_CORE)
    ap.add_argument("--preopen-dir", default=DEFAULT_PREOPEN)
    a = ap.parse_args()
    if a.append:
        return append(a.calendar, a.append, a.backup_dir)
    cal = load(a.calendar)
    day = d(a.date) if a.date else today_et()
    if a.check_record:
        return check_record(cal, day, a.check_record)
    if a.reduce_window:
        print(json.dumps(reduce_window(cal, day, a.core_dir, a.preopen_dir, a.now, a.base), ensure_ascii=False,
                         indent=1))
        return 0
    print(json.dumps(plan(cal, day), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
