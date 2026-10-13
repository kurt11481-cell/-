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
"""
import argparse
import datetime as dt
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--calendar", default=DEFAULT_CAL)
    ap.add_argument("--check-record")
    ap.add_argument("--append")
    ap.add_argument("--backup-dir", default=os.path.join(HERE, "..", "..", "workspace", "outputs", "pre-open",
                                                         "_calendar-backup"))
    a = ap.parse_args()
    if a.append:
        return append(a.calendar, a.append, a.backup_dir)
    cal = load(a.calendar)
    day = d(a.date) if a.date else today_et()
    if a.check_record:
        return check_record(cal, day, a.check_record)
    print(json.dumps(plan(cal, day), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
