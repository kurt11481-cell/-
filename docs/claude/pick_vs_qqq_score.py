#!/usr/bin/env python3
"""pick-vs-qqq: did the company's list and its actual buys beat QQQ bought the same day? (pre-registration draft)

Pre-registration: docs/claude/pick-vs-qqq-preregistration-2026-11-19.md (criteria in section 4 = constants below).
Read-only: reads committed versions of docs/claude/watchlist-registry.json (git history) + the working copy,
workspace/outputs/regular-session-closes/history/<SYM>.close-history.json, workspace/outputs/auto-core/<day>/decision.json
(outcomes[]) and manage-us-stock-strategy/scripts/auto_core_tickets.py (APPROVED_BUY at the basis date, git history).
Writes nothing. No authority, no orders, no quantities. Evidence weight 0.

While FIX_DATE is None (draft, not fixed) the script reports only how many weekly snapshots exist and never computes
a return, so nobody looks at the main sample before the user's fix card (design 3-A).

Usage (repo root): python docs/claude/pick_vs_qqq_score.py --as-of YYYY-MM-DD [--horizon-weeks 4] [--json] [--ledger-prices FILE]
Returns are computed only when --as-of is one of EVAL_DATES; any other day prints counts only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import statistics
import subprocess
from pathlib import Path

REL = "docs/claude/watchlist-registry.json"
TICKETS_REL = "manage-us-stock-strategy/scripts/auto_core_tickets.py"
CLOSES_DIR = "workspace/outputs/regular-session-closes/history"
CORE_DIR = "workspace/outputs/auto-core"
REPO = Path(__file__).resolve().parents[2]

# ---- Pre-registered constants (section 4). FIXED 2026-11-19 — do not edit; a change needs a new preregistration. ----
FIX_DATE: str | None = "2026-11-19"  # fixed by the user's card 2026-11-19 16:25:12 KST (cmsg_0137MRzn9nuDvvQmVxm6WeX95rcPuDmV8B15U2CzqeCmK4)
MIN_WEEKS = 26                       # main-sample cohorts with >= 1 L stock and both QQQ closes (H=4 only)
JUDGED_HORIZON = 4                   # H=12 is display only (no verdict)
EVAL_DATES = {"2026-12-19": "display", "2027-01-16": "display", "2027-04-10": "judge", "2027-10-09": "judge",
              "2028-04-08": "judge", "2028-10-14": "judge"}
INDEX_ETFS = ("SOXL", "TQQQ", "DRAM", "QQQ")  # auto_core_tickets.py 62행 — not a stock pick
P1_MEAN_EXCESS = 0.010               # mean (L - Q) per cohort >= +1.0%p
P2_SHARE_WIN = 0.60                  # share of cohorts with L > Q >= 60%
SECTOR_U_MINUS_Q = 0.010             # 'sector tilt' report: mean (U - Q) >= +1.0%p ...
SECTOR_L_MINUS_U_ABS = 0.005         # ... and |mean (L - U)| < 0.5%p
LIVE_MIN_BUYS = 30                   # practical line: complete buys only (horizon passed, all closes present)
LIVE_HORIZONS = (20, 60)             # sessions after the fill session
MATCH_DAYS = 3                       # forward snapshot = basis + 7*H days (+-3), same as wl-fwd-score
# 11/10 forecast ledger (G6): stock-pick-forward-2026-11-10.md plans, base = px_snapshot.json 2026-11-09 16:55Z
# (Yahoo intraday, not a close). Scored 2027-11-09, reference grade only.
LEDGER_BASE = {"NVDA": 176.74, "MSFT": 541.3, "AMZN": 268.36, "AVGO": 318.15, "QQQ": 676.58}
LEDGER_PLANS = {"NVDA+MSFT+AMZN": ("NVDA", "MSFT", "AMZN"), "MSFT+AMZN": ("MSFT", "AMZN"), "NVDA+AVGO": ("NVDA", "AVGO")}
LEDGER_DUE = "2027-11-09"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "--no-optional-locks", "-C", str(repo), *args], capture_output=True, timeout=120)


def load_documents(repo: Path, include_worktree: bool = True) -> list[dict]:
    docs = []
    log = _git(repo, "log", "--reverse", "--format=%H", "--", REL)
    for rev in log.stdout.decode().split() if log.returncode == 0 else []:
        shown = _git(repo, "show", f"{rev}:{REL}")
        if shown.returncode == 0:
            try:
                docs.append(json.loads(shown.stdout.decode("utf-8-sig")))
            except ValueError:
                pass
    if include_worktree:  # draft counts only; a fixed run reads committed versions only (pre-registration 3절)
        try:
            docs.append(json.loads((repo / REL).read_text(encoding="utf-8-sig")))
        except (OSError, ValueError):
            pass
    return docs


def snapshots(docs: list[dict]) -> dict[str, dict]:
    """{basis: {"rows": {code: close}, "members": {code: cardStatus}}}; row only when closeDate == basis (wl-fwd 1절)."""
    out: dict[str, dict] = {}
    for doc in docs:  # oldest first, a later version of the same basis wins
        run = doc.get("weeklyRun") or {}
        basis = run.get("basis")
        if not basis:
            continue
        rows: dict[str, float] = {}
        sources = [(c.get("code"), c) for c in doc.get("candidates") or []]
        sources += list((run.get("memberData") or {}).items())
        for code, item in sources:
            detail = (item or {}).get("detail") or {}
            if code and detail.get("closeDate") == basis and isinstance(detail.get("close"), (int, float)) \
                    and isinstance(item.get("score"), (int, float)):
                rows[code] = float(detail["close"])
        members = {m.get("code"): str(m.get("cardStatus") or "") for m in doc.get("members") or [] if m.get("code")}
        if rows:
            # closes: a later version of the same basis wins; list/card status: the FIRST version of that basis
            # (a card accepted later in the week must not enter that week's L — no look-ahead).
            first = out.get(basis, {}).get("members")
            out[basis] = {"rows": rows, "members": first if first is not None else members}
    return out


def _day(basis: str) -> dt.date:
    return dt.date(int(basis[:4]), int(basis[4:6]), int(basis[6:]))


def approved_at(repo: Path, day: dt.date, cache: dict) -> set[str] | None:
    """APPROVED_BUY of auto_core_tickets.py as committed on or before `day` (None if unreadable)."""
    if day in cache:
        return cache[day]
    rev = _git(repo, "log", "-1", "--format=%H", f"--before={day.isoformat()}T23:59:59+09:00", "--", TICKETS_REL)
    found = None
    sha = rev.stdout.decode().strip() if rev.returncode == 0 else ""
    if sha:
        shown = _git(repo, "show", f"{sha}:{TICKETS_REL}")
        m = re.search(r"^APPROVED_BUY\s*=\s*\(([^)]*)\)", shown.stdout.decode("utf-8", "replace"), re.M)
        if m:
            found = set(re.findall(r'"([A-Z.]+)"', m.group(1)))
    cache[day] = found
    return found


def load_closes(repo: Path, symbol: str) -> dict[str, float]:
    path = repo / CLOSES_DIR / f"{symbol}.close-history.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return {s["session_date"]: float(s["close"]) for s in data.get("sessions") or []
            if s.get("verified") is True and s.get("close") not in (None, "")}


def cohorts(snaps: dict[str, dict], qqq: dict[str, float], repo: Path, horizon: int, main_from: str,
            as_of: dt.date) -> tuple[list[dict], list[str]]:
    bases = sorted(snaps)
    cache: dict = {}
    weeks, missing_forward = [], []
    for base in bases:
        if base <= main_from:
            continue  # seen period (before or on the fix date): never in the main sample
        target = _day(base) + dt.timedelta(days=7 * horizon)
        fwd = [b for b in bases if abs((_day(b) - target).days) <= MATCH_DAYS]
        if not fwd:
            if target + dt.timedelta(days=MATCH_DAYS) < as_of:
                missing_forward.append(base)  # horizon passed but no weekly snapshot: counted, not silent
            continue
        now, later = snaps[base], snaps[fwd[0]]
        q0, q1 = qqq.get(_day(base).isoformat()), qqq.get(_day(fwd[0]).isoformat())
        approved = approved_at(repo, _day(base), cache)
        week = {"base": base, "forward": fwd[0], "Q": None, "L": None, "U": None, "L_codes": [], "notes": []}
        if q0 is None or q1 is None:
            week["notes"].append("QQQ 종가 없음")
        else:
            week["Q"] = q1 / q0 - 1
        if approved is None:
            week["notes"].append("상품 승인 목록 못 읽음 — L 없음")
        common = sorted(set(now["rows"]) & set(later["rows"]))
        rets = {c: later["rows"][c] / now["rows"][c] - 1 for c in common}
        if rets:
            week["U"] = statistics.fmean(rets.values())
        listed = [c for c, st in now["members"].items() if st.startswith("수락") and approved and c in approved]
        week["L_codes"] = listed
        missing = [c for c in listed if c not in rets]
        if missing:
            week["notes"].append("L 종목 이후 종가 없음: " + ",".join(missing))
        l_rets = [rets[c] for c in listed if c in rets]
        if l_rets:
            week["L"] = statistics.fmean(l_rets)
        weeks.append(week)
    return weeks, missing_forward


def summarize(weeks: list[dict], horizon: int) -> dict:
    usable = [w for w in weeks if w["L"] is not None and w["Q"] is not None]
    lq = [w["L"] - w["Q"] for w in usable]
    uq = [w["U"] - w["Q"] for w in weeks if w["U"] is not None and w["Q"] is not None]
    lu = [w["L"] - w["U"] for w in weeks if w["L"] is not None and w["U"] is not None]
    s = {"weeks": len(lq),
         "mean_L_minus_Q": statistics.fmean(lq) if lq else None,
         "share_L_gt_Q": (sum(x > 0 for x in lq) / len(lq)) if lq else None,
         "mean_U_minus_Q": statistics.fmean(uq) if uq else None,
         "mean_L_minus_U": statistics.fmean(lu) if lu else None}
    if horizon != JUDGED_HORIZON:
        s["verdict"] = "DISPLAY_ONLY"
    elif s["weeks"] < MIN_WEEKS:
        s["verdict"] = "INSUFFICIENT_SAMPLE"
    else:
        s["verdict"] = "PASS" if (s["mean_L_minus_Q"] >= P1_MEAN_EXCESS and s["share_L_gt_Q"] >= P2_SHARE_WIN) else "FAIL"
    s["sector_tilt"] = bool(s["mean_U_minus_Q"] is not None and s["mean_L_minus_U"] is not None
                            and s["mean_U_minus_Q"] >= SECTOR_U_MINUS_Q
                            and abs(s["mean_L_minus_U"]) < SECTOR_L_MINUS_U_ABS)
    return s


def live_buys(repo: Path, qqq: dict[str, float], main_from: str, as_of: dt.date) -> dict:
    """Practical line: filled core buy tickets after the fix date (auto-core <day>/decision.json outcomes[], filled rule =
    auto_core_tickets.py 480행). Base = average fill price; QQQ base = same-session close. Index ETFs excluded.
    The user's own orders without a ticket are not readable here (location 확인 필요) and are reported as such."""
    seen: dict[str, dict] = {}
    for path in sorted((repo / CORE_DIR).glob("*/decision.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        for o in data.get("outcomes") or []:
            state, filled = o.get("state"), o.get("filled_qty") or 0
            if o.get("side") != "buy" or not (state in ("filled", "partial") or (state == "changed" and filled > 0)):
                continue
            key = o.get("ticket_id") or f"{o.get('ticker')}:{o.get('session')}"
            seen[key] = o
    qdays = sorted(qqq)
    buys, skipped = [], {}
    def skip(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1
    for o in seen.values():
        sym, day, fill = o.get("ticker"), o.get("session"), o.get("average_fill_price")
        if not sym or not day or day.replace("-", "") <= main_from:
            continue
        if sym in INDEX_ETFS:
            skip("지수 ETF 제외")
            continue
        closes = load_closes(repo, sym)
        sdays = sorted(closes)
        if not isinstance(fill, (int, float)) or day not in qqq or day not in closes:
            skip("체결가·종가 이력 없음(확인 필요)")
            continue
        row = {"symbol": sym, "session": day}
        i, j = sdays.index(day), qdays.index(day)
        for h in LIVE_HORIZONS:
            if i + h < len(sdays) and j + h < len(qdays) and sdays[i + h] == qdays[j + h]:
                row[f"x{h}"] = closes[sdays[i + h]] / fill - qqq[qdays[j + h]] / qqq[day]
        buys.append(row)
    out = {"tickets_read": len(seen), "skipped": skipped,
           "note": "사장 직접 주문(주문표 없는 체결)은 이 줄에 없음 — 위치 확인 필요"}
    for h in LIVE_HORIZONS:
        xs = [b[f"x{h}"] for b in buys if f"x{h}" in b]
        out[f"complete_{h}"] = len(xs)
        out[f"mean_x{h}"] = statistics.fmean(xs) if len(xs) >= LIVE_MIN_BUYS else None
    out["status"] = "표본 부족" if out[f"complete_{LIVE_HORIZONS[0]}"] < LIVE_MIN_BUYS else "표본 충족(보고만)"
    return out


def ledger(prices: dict[str, float] | None) -> dict:
    if not prices:
        return {"due": LEDGER_DUE, "status": "가격 파일 없음 — 표시 없음"}
    q = prices.get("QQQ")
    res = {"due": LEDGER_DUE, "grade": "참고(장중 시세 기준, 판정 아님)"}
    for name, codes in LEDGER_PLANS.items():
        if q is None or any(c not in prices for c in codes):
            res[name] = None
            continue
        plan = statistics.fmean(prices[c] / LEDGER_BASE[c] - 1 for c in codes)
        res[name] = plan - (q / LEDGER_BASE["QQQ"] - 1)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon-weeks", type=int, default=4, choices=(4, 12))
    ap.add_argument("--from-basis", help="YYYYMMDD: also use only bases after this (new-weeks-only check, 5절)")
    ap.add_argument("--as-of", required=True, help="KST date YYYY-MM-DD; returns only on EVAL_DATES")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--repo", type=Path, default=REPO)
    ap.add_argument("--ledger-prices", type=Path, help="JSON {symbol: price} for the 11/10 ledger (reference)")
    args = ap.parse_args()
    snaps = snapshots(load_documents(args.repo, include_worktree=FIX_DATE is None))
    as_of = dt.date.fromisoformat(args.as_of)
    if FIX_DATE is None or args.as_of not in EVAL_DATES:
        why = "고정 전" if FIX_DATE is None else f"{args.as_of}는 평가일이 아님"
        result = {"status": "DRAFT_NOT_FIXED" if FIX_DATE is None else "NOT_EVAL_DATE", "snapshots": len(snaps),
                  "latest_basis": max(snaps) if snaps else None,
                  "note": f"{why}이라 수익률을 계산하지 않음(본 표본 안 봄)", "order_authority": False}
    else:
        main_from = max(FIX_DATE.replace("-", ""), args.from_basis or "")
        qqq = load_closes(args.repo, "QQQ")
        weeks, missing = cohorts(snaps, qqq, args.repo, args.horizon_weeks, main_from, as_of)
        prices = json.loads(args.ledger_prices.read_text(encoding="utf-8")) if args.ledger_prices else None
        result = {"status": "FIXED", "fix_date": FIX_DATE, "from_basis": args.from_basis, "as_of": args.as_of, "eval_kind": EVAL_DATES[args.as_of],
                  "horizon_weeks": args.horizon_weeks, "weeks": weeks, "missing_forward_snapshots": missing,
                  "summary": summarize(weeks, args.horizon_weeks), "live": live_buys(args.repo, qqq, main_from, as_of),
                  "ledger": ledger(prices),
                  "criteria": {"min_weeks": MIN_WEEKS, "P1_mean_L_minus_Q": P1_MEAN_EXCESS,
                               "P2_share_L_gt_Q": P2_SHARE_WIN, "live_min_buys": LIVE_MIN_BUYS},
                  "order_authority": False}
        if EVAL_DATES[args.as_of] == "display":
            result["summary"]["verdict"] = "DISPLAY_ONLY"
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return
    if result["status"] != "FIXED":
        print(f"pick-vs-qqq {result['status']} · 주간 판 {result['snapshots']}개(최근 {result['latest_basis']}) · {result['note']}")
        return
    pct = lambda v: "-" if v is None else f"{v * 100:+.2f}%"
    print(f"pick-vs-qqq H={result['horizon_weeks']}주 · 고정일 {FIX_DATE} · {result['as_of']}({result['eval_kind']})"
          f" · 주간 판 빠짐 {len(result['missing_forward_snapshots'])}")
    for w in result["weeks"]:
        print(f"  {w['base']}->{w['forward']} L{w['L_codes']} L {pct(w['L'])} U {pct(w['U'])} Q {pct(w['Q'])} "
              + ("; ".join(w["notes"]) if w["notes"] else ""))
    s = result["summary"]
    share = "-" if s["share_L_gt_Q"] is None else f"{s['share_L_gt_Q']:.0%}"
    print(f"  주 {s['weeks']} · L-Q 평균 {pct(s['mean_L_minus_Q'])} · L>Q 비율 {share} · "
          f"U-Q {pct(s['mean_U_minus_Q'])} · L-U {pct(s['mean_L_minus_U'])} -> {s['verdict']}"
          + (" · 분야 쏠림" if s["sector_tilt"] else ""))
    lv = result["live"]
    print(f"  실전 줄: 완결 {lv['complete_20']}건(20세션) · {lv['status']} · 뺀 것 {lv['skipped']} · {lv['note']}")
    print(f"  예측 장부({LEDGER_DUE}): {result['ledger']}")


if __name__ == "__main__":
    main()
