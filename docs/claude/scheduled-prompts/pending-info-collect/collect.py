#!/usr/bin/env python3
"""info-monitoring 외부 정보 수집기 v0.1 (2026-11-07) — 표준 라이브러리만, python3 -I 로 실행.

권한: CONTEXT_ONLY. 공개 자료를 받아 기록하고 '점검 열기' 할 일을 낼 뿐이다.
주문·수량·정책·상태·자동 코어·통합점검 규칙·노출 판정과 연결이 없다.
계좌 금액·수량은 받지도 쓰지도 않는다.

명령:
  (D = YYYY-MM-DD 또는 today — today는 KST 날짜)
  numbers  --day D [--offline DIR]   FRED(HY·BBB·CCC·NFCI)·재무부 TGA·CFTC(나스닥100·S&P500 미니) 받기
                                     + v0.6 순유동성(FRED WALCL·WDTGAL·RRPONTSYD, 3년+ 이력)·세 지표 3년 백분위(표시 전용)
  finviz   --day D [--tickers A,B | --tickers-file F]  종목 화면 숫자 일부(robots.txt 허용 경로, 25종목 이하, 2초 간격,
                                     목록을 안 주면 tickers.txt) + v0.7 기준 QQQ 한 줄(명단 밖)·FINVIZ_STREAK·FINVIZ_GAP
                                     + v0.8 finviz 첫 화면 시장 폭 6칸 → data/breadth.jsonl(미국 세션 날짜당 1줄, 표시 전용)
                                       ·BREADTH_STREAK·BREADTH_GAP·BREADTH_STOPPED
  roster   --day D --status checked|changed|skipped  월요일 tickers.txt 대조 결과 기록(v0.7) — 2주 연속 skipped면 ROSTER_SKIP_STREAK
  x-add    --day D --file F.json     Chrome으로 읽은 X 글 저장(글 id 중복 제거, 빈 목록 = 못 읽음 → 연속 실패 +1)
  signals  --day D                   데이터 점검 문턱(D1·D2) 판정 + 심리 단서 D3(v0.5, 새로 켜짐) + 순유동성 D4(v0.6, 새로 켜짐)
                                     → 새로 걸리면 pending-checks.json
  done     --id D1 --reason TEXT     점검 끝 기록(다시 걸리려면 해제선 아래로 내려왔다가 다시 넘어야 함)
  daily    --day D                   daily/D.md 쓰기
  x-seen                             계정별 저장된 글 id(새 글만 읽기 위해)
  usage    --since D                 4주 쓸모 집계(G7)
  rules                              문턱 문장 출력
종료 코드: 0 정상 · 2 일부 STALE(같은 자료 2회 연속이면 STALE_STREAK 줄) · 3 오류 · 10 열린 데이터 점검 있음(signals)
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import html
import io
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
STATE = ROOT / "state.json"
PENDING = ROOT / "pending-checks.json"
DAILY = ROOT / "daily"
# 시나리오 확률 점검(v2.2)이 회사 전략 점검을 끝내면 한 줄씩 덧붙이는 파일 — 쓰는 쪽은 그 점검 하나, 여기는 읽기만.
# 줄 모양: {"id": "D1", "since": "YYYY-MM-DD(KST)", "concluded_kst": "...", "result": "그대로|바꾸자", "reason": "..."}
CLOSED_FILE = Path("/mnt/project-files/scenario-odds/out/data-checks-closed.jsonl")
VERSION = "v0.8"

FRED_SERIES = {
    "BAMLH0A0HYM2": "HY 스프레드(%)",
    "BAMLC0A4CBBB": "BBB 스프레드(%)",
    "BAMLH0A3HYC": "CCC 스프레드(%)",
    "NFCI": "금융 여건 NFCI",
}
CFTC_MARKETS = {"NQ": "NASDAQ MINI", "ES": "E-MINI S&P 500 -"}
# v0.6 유동성·신용(liquidity-1124, 사장 결정 카드 2026-11-24 21:56 KST '(나)') — 표시 전용 + D4 점검 열기.
# 설계 원본 /mnt/project-files/liquidity-1124/liquidity-credit-design-2026-11-24.md 2-1·6-1절. 매매 규칙·노출·한도·코어와 연결 없음.
LIQ_SERIES = {
    "WALCL": "연준 총자산(수요일 수준, 백만$)",
    "WDTGAL": "TGA(수요일 수준, 백만$)",      # WTREGEN(주 평균)은 쓰지 않는다 — 수요일 수준끼리만 뺀다
    "RRPONTSYD": "역레포(일간, 십억$)",       # 단위 주의: 십억$ → ×1000 해서 백만$
}
FRED_LOOKBACK_DAYS = 1300   # v0.6: 3년(1095일) 백분위 + 156주 굴림 4주 변화(160주)를 위한 여유. v0.5까지 420일
LIQ_PCT_DAYS = 1095         # '3년 굴림 백분위'의 날짜 창
TGA_LOOKBACK_DAYS = 1300    # 재무부 일일 TGA 이력(v0.5까지 최근 20행 → 3행만 보관)
STALE_DAYS = {"NFCI": 14, "WALCL": 14, "WDTGAL": 14}  # 주간 계열(목요일 발표 수요일 값) 14일, 나머지 6일
RRP_START = "2013-09-23"    # 역레포 일간 계열 시작 — 그 전 빈칸은 0(설계 2-2)
# v0.7: daily 표가 쓰는 칸만 받는다(README 8행 '소비자 없는 자료는 모으지 않는다'). 가격은 키움, 재무는 SEC.
FINVIZ_FIELDS = (
    "Forward P/E", "Earnings", "Target Price", "Recom", "Short Float", "Insider Trans",
    "RSI (14)", "Perf Week", "Perf Month",
)
FINVIZ_BENCH = "QQQ"        # v0.7: 한 달 성과 비교용 기준 지수(tickers.txt 밖 — 월요일 명단 대조가 지우지 않게)
FINVIZ_MAX = 25
# v0.8 시장 폭(breadth-1128, 사장 결정 카드 2026-11-28 14:55:35 KST 'A 매일 무료 기록') — 표시 전용·근거 강도 0.
# 알림·판정·코어 입력 없음. 판정 자료로 쓰려면 먼저 문턱을 사전 등록(등록 전 날짜 값은 보고 전용).
BREADTH_URL = "https://finviz.com/"   # 첫 화면(robots.txt가 막지 않음 — 막는 곳은 /export·/screener?* 등)
BREADTH_STOP = "2027-06-30"           # README 1절 예외: 이 날짜까지 읽는 점검이 없으면 수집 멈춤(이 날 뒤로는 받지 않는다)
BREADTH_SETTLE = (16, 15)             # 미국 동부 16:15 전(장중·마감 직후)에는 그날 세션을 기록하지 않는다
BREADTH_H13 = "확인 전"                # H1-3(06:20 KST 값 = 마감 확정치?) 결과. 통과하면 새 판에서 "통과"로 — 그 전 줄은 확정치 아님
BREADTH_KEYS = ("adv", "dec", "nh", "nl", "sma50_pct", "sma200_pct")   # 6칸(같은지 비교·표시)
EARN_SOON_DAYS = 7          # v0.7: 실적일이 이 일수 안으로 들어오는 날 줄을 낸다
_MONTHS = {m: i + 1 for i, m in enumerate(("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"))}
X_ACCOUNTS = ("MgnStnlyDerivs", "neilsethinew", "markminervini")  # v0.3: 사장 11/18 07:49 KST 추가
_X_CANON = {a.lower(): a for a in X_ACCOUNTS}  # 화면 주소의 대소문자가 달라도 같은 계정으로

# 데이터 점검 문턱 — 매매 규칙이 아니라 '회사 전략 점검을 여는 알림'이다(미검증 숫자).
RULES = {
    "D1": {"series": "BAMLH0A0HYM2", "label": "HY 스프레드",
           "trigger_bp": 75, "rearm_bp": 50, "window_days": 183, "need": 2,
           "step_bp": 25},  # v0.4: 닫힌 뒤(해제 전) 지난 점검 때보다 +25bp 더 벌어지면 다시 1회(미검증)
    "D2": {"series": "NFCI", "label": "금융 여건 NFCI",
           "trigger": 0.0, "rearm": -0.10, "need": 2},
}
RULES_TEXT = ("데이터 점검(점검 열기용, 매매 규칙 아님·미검증): "
              "D1 HY 스프레드가 183일 저점 +75bp 이상인 관측일 2개 연속(관측일 기준) → 회사 전략 점검 1회, "
              "+50bp 아래로 내려온 뒤에만 다시 걸림, 단 이미 걸린 뒤 해제 전에도 지난 점검 때 값보다 +25bp 이상 더 벌어진 관측일 2개 연속이면 단계 재알림 1회(v0.4) · "
              "D2 NFCI가 0 이상인 주 2개 연속 → 1회, -0.10 아래로 내려온 뒤에만 다시 걸림 · "
              "D3(v0.5, 심리) FINRA 신용 잔고 1년 변화율 누적 백분위·CFTC 나스닥100 레버리지 펀드 순포지션 비율 156보고 백분위가 "
              "상위 20%/하위 20%로 새로 켜진 첫 세션(같은 단서 앞 사건에서 60세션 이상) → 회사 전략 점검 1회. 표시·점검 열기용, 등급·매매 규칙 아님 · "
              "D4(v0.6, 순유동성) 주간 순유동성(연준 총자산 WALCL − TGA WDTGAL − 역레포 RRPONTSYD×1000, 같은 수요일)의 4주간 변화가 "
              "156주간 굴림 백분위 하위 20%에 새로 들어감(전주 밖 → 이번 주 안) → 회사 전략 점검 1회, 이미 열린 D4가 있으면 열지 않음. "
              "점검 열기용, 매매 규칙 아님·미검증 문턱")
LIQ_D4 = {"k": 4, "win": 156, "bot": 0.20, "fresh_days": 10}  # 4주 = 캡처의 20영업일, 20% = 심리 선례(설계 2-2) — 미검증

# finviz 종목 화면만 이 이름을 쓴다. FRED는 이 이름을 연결 거부(11/07 실측: 30초 뒤 끊김)하고
# 파이썬 기본 이름(Python-urllib)은 0.2초에 200 — 공식 API(FRED·CFTC·재무부)는 기본 이름 그대로 쓴다.
FINVIZ_UA = "Mozilla/5.0 (investment-v2 info-monitoring; manual-rate)"


# ── 받기 ──
def fetch(url: str, ua: str | None = None, timeout: float = 30.0, tries: int = 2) -> str:
    headers = {"User-Agent": ua} if ua else {}
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001 — 1번만 다시(5초 뒤), 그래도 안 되면 STALE
            if i + 1 >= tries:
                raise
            time.sleep(5)
    raise RuntimeError("unreachable")


def read_bytes_source(name: str, url: str, offline: Path | None, timeout: float = 30.0) -> bytes:
    if offline is not None:
        return (offline / name).read_bytes()
    for i in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as r:  # 파이썬 기본 이름(브라우저 흉내 아님)
                return r.read()
        except Exception:  # noqa: BLE001
            if i == 1:
                raise
            time.sleep(5)
    raise RuntimeError("unreachable")


def read_source(name: str, url: str, offline: Path | None, ua: str | None = None) -> str:
    if offline is not None:
        return (offline / name).read_text(encoding="utf-8")
    return fetch(url, ua)


# ── 순수 계산 (시험 대상) ──
def parse_fred(text: str, sid: str) -> list[tuple[str, float]]:
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        v = (row.get(sid) or "").strip()
        d = (row.get("observation_date") or "").strip()
        if d and v not in ("", "."):
            out.append((d, float(v)))
    return out


def fred_summary(obs: list[tuple[str, float]], window_days: int = 183) -> dict:
    if not obs:
        return {"ok": False}
    last_d, last_v = obs[-1]
    cut = (dt.date.fromisoformat(last_d) - dt.timedelta(days=window_days)).isoformat()
    win = [o for o in obs if o[0] >= cut]
    lo = min(win, key=lambda o: o[1])
    yr_cut = (dt.date.fromisoformat(last_d) - dt.timedelta(days=365)).isoformat()
    yr = [o[1] for o in obs if o[0] >= yr_cut]

    def ago(n):
        return obs[-1 - n] if len(obs) > n else None
    return {"ok": True, "date": last_d, "value": last_v,
            "low": {"date": lo[0], "value": lo[1]},
            "above_low_bp": round((last_v - lo[1]) * 100),
            "chg5": None if ago(5) is None else round((last_v - ago(5)[1]) * 100),
            "chg21": None if ago(21) is None else round((last_v - ago(21)[1]) * 100),
            "yr_min": min(yr), "yr_max": max(yr)}


def parse_cftc(text: str) -> list[dict]:
    rows = json.loads(text)
    out = []
    for r in rows:
        try:
            lev = int(r["lev_money_positions_long"]) - int(r["lev_money_positions_short"])
            am = int(r["asset_mgr_positions_long"]) - int(r["asset_mgr_positions_short"])
            out.append({"date": r["report_date_as_yyyy_mm_dd"][:10], "lev_net": lev, "am_net": am,
                        "oi": int(r["open_interest_all"]), "market": r["market_and_exchange_names"]})
        except (KeyError, ValueError, TypeError):
            continue
    out.sort(key=lambda x: x["date"])
    return out


def parse_tga(text: str) -> list[dict]:
    data = json.loads(text).get("data", [])
    out = []
    for r in data:
        # 일일 재무부 보고서(DTS): 'Closing Balance' 행의 open_today_bal 칸이 그날 마감 잔액이다.
        if "Closing Balance" in r.get("account_type", ""):
            v = r.get("open_today_bal")
            if v not in (None, "null", ""):
                out.append({"date": r["record_date"], "musd": float(v)})
    out.sort(key=lambda x: x["date"])
    return out


def parse_finviz(text: str) -> dict:
    cells = re.findall(r'<td[^>]*snapshot-td2[^>]*>(.*?)</td>', text, re.S)
    vals = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in cells]
    pairs = {}
    for k, v in zip(vals[0::2], vals[1::2]):
        if k in FINVIZ_FIELDS and k not in pairs:
            pairs[k] = v
    return pairs


_BREADTH_BOX = re.compile(
    r'data-boxover-html="Total &lt;b&gt;(?P<name>[^&]+)&lt;/b&gt; issues on NYSE, Nasdaq and AMEX">(?P<body>.*?)market-stats_bar"', re.S)
_BREADTH_P = re.compile(r"<p[^>]*>\s*([0-9.]+)%\s*\((\d+)\)\s*</p>.*?<p[^>]*>\s*\((\d+)\)\s*([0-9.]+)%\s*</p>", re.S)


def parse_breadth(text: str) -> dict | None:
    """finviz 첫 화면 시장 폭 상자 4개(NYSE·Nasdaq·AMEX 합계). 하나라도 없거나 값이 이상하면 None.
    New High·New Low = finviz 정의 '오늘 52주 신고가·신저가를 만든 종목'(/help/screener, 11/28 확인 — 장중 고가·저가 기준인지는 확인 필요)."""
    boxes = {}
    for m in _BREADTH_BOX.finditer(text):
        p = _BREADTH_P.search(m.group("body"))
        if p:
            boxes[m.group("name").strip()] = (float(p.group(1)), int(p.group(2)), int(p.group(3)), float(p.group(4)))
    need = {"Advancing / Declining": ("adv", "dec"), "New High / New Low": ("nh", "nl"),
            "Above SMA50 / Below SMA50": ("sma50_above", "sma50_below"), "Above SMA200 / Below SMA200": ("sma200_above", "sma200_below")}
    out = {}
    for name, (lk, rk) in need.items():
        if name not in boxes:
            return None
        lp, ln, rn, rp = boxes[name]
        if not (0 <= lp <= 100 and 0 <= rp <= 100):
            return None
        out[lk], out[rk] = ln, rn
        if lk.startswith("sma"):
            out[lk.replace("_above", "_pct")] = lp
    if out["adv"] + out["dec"] == 0 or out["sma50_above"] + out["sma50_below"] == 0:
        return None
    return out


def _et_offset(utc: dt.datetime) -> int:
    """미국 동부 시차(서머타임 = 3월 둘째 일요일 07:00 UTC ~ 11월 첫 일요일 06:00 UTC). zoneinfo 없이(tzdata 없는 곳 대비)."""
    y = utc.year
    mar1 = dt.date(y, 3, 1)
    start = dt.datetime(y, 3, 1 + (6 - mar1.weekday()) % 7 + 7, 7)
    nov1 = dt.date(y, 11, 1)
    end = dt.datetime(y, 11, 1 + (6 - nov1.weekday()) % 7, 6)
    naive = utc.replace(tzinfo=None)
    return -4 if start <= naive < end else -5


def breadth_session(utc: dt.datetime) -> str | None:
    """이 시각에 finviz 첫 화면이 보여 주는 미국 세션 날짜. 장중·마감 직후(평일 09:30~16:15 ET)는 None.
    주말은 직전 금요일. 휴장일은 그날 날짜가 나오고 값이 직전과 같아진다(repeat 표시 — 달력은 쓰지 않음)."""
    et = utc.replace(tzinfo=None) + dt.timedelta(hours=_et_offset(utc))
    d, hm = et.date(), (et.hour, et.minute)
    if d.weekday() >= 5:
        return (d - dt.timedelta(days=d.weekday() - 4)).isoformat()
    if hm >= BREADTH_SETTLE:
        return d.isoformat()
    if hm < (9, 30):
        back = 3 if d.weekday() == 0 else 1
        return (d - dt.timedelta(days=back)).isoformat()
    return None


def weekdays_between(a: str, b: str) -> int:
    """a와 b 사이(둘 다 빼고)의 평일 수."""
    d, e, n = dt.date.fromisoformat(a) + dt.timedelta(days=1), dt.date.fromisoformat(b), 0
    while d < e:
        n += d.weekday() < 5
        d += dt.timedelta(days=1)
    return n


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def earn_days(val: str | None, day: str) -> int | None:
    """finviz Earnings 칸('Nov 24 AMC')이 수집일에서 며칠 뒤인지(음수 = 지난 실적일). 연도가 없어 수집일에 가장 가까운 해로 추정.
    finviz는 다음 실적일이 정해지기 전까지 지난 실적일을 그대로 보여 준다."""
    m = re.match(r"^([A-Z][a-z]{2}) (\d{1,2})\b", (val or "").strip())
    if not m or m.group(1) not in _MONTHS:
        return None
    d0 = dt.date.fromisoformat(day)
    best = None
    for y in (d0.year - 1, d0.year, d0.year + 1):
        try:
            c = dt.date(y, _MONTHS[m.group(1)], int(m.group(2)))
        except ValueError:
            continue
        n = (c - d0).days
        if best is None or abs(n) < abs(best):
            best = n
    return best


def earn_lines(prior: list[dict], rows: dict, day: str) -> list[str]:
    """값이 앞 기록과 바뀐 종목, 실적일이 7일 안으로 들어온 종목(표시 전용 — 날짜 확인은 EDGAR 8-K·IR).
    종목마다 그 종목의 Earnings 값이 있는 가장 최근 앞 기록과 비교한다. 날짜는 finviz가 보여 주는 미국 날짜(AMC는 KST 다음 날 새벽)."""
    out = []
    for t, row in rows.items():
        cur = (row or {}).get("Earnings")
        if not cur:
            continue
        prev = prev_day = None
        for r in reversed(prior):
            v = ((r.get("rows") or {}).get(t) or {}).get("Earnings")
            if v:
                prev, prev_day = v, r.get("day")
                break
        n = earn_days(cur, day)
        if prev is not None and prev != cur:
            tag = "날짜로 읽히지 않음" if n is None else ("다음 실적일로 보임" if n >= 0 else "지난 날짜로 보임")
            out.append(f"- {t} 실적일 값 바뀜: {prev} → {cur} ({tag}, 연도는 수집일로 추정)")
        if n is not None and 0 <= n <= EARN_SOON_DAYS:
            pn = earn_days(prev, prev_day) if (prev and prev_day) else None
            was_soon = prev == cur and pn is not None and 0 <= pn <= EARN_SOON_DAYS
            if not was_soon:
                out.append(f"- {t} 실적일 {EARN_SOON_DAYS}일 안으로 들어옴: {cur} (D-{n}, 연도는 수집일로 추정)")
    return out


AMOUNT_RE = re.compile(r"(계좌|잔고|보유\s*수량|평가\s*금액)")
X_CLASSES = ("P후보", "R0", "시나리오 증거", "참고", "버림")


def _our_note(v, n: int) -> str:
    """우리가 쓰는 칸(요지·소비자)에 계좌 말이 들어가면 비운다 — 계좌 금액·수량은 쓰지 않는다."""
    s = re.sub(r"\s+", " ", str(v or "")).strip()[:n]
    return "" if AMOUNT_RE.search(s) else s


def clean_post(p: dict) -> dict | None:
    pid = str(p.get("id", "")).strip()
    acc = _X_CANON.get(str(p.get("account", "")).lstrip("@").strip().lower(), "")
    text = re.sub(r"\s+", " ", str(p.get("text", ""))).strip()
    if not re.fullmatch(r"\d{6,25}", pid) or not acc or not text:
        return None
    return {"id": pid, "account": acc, "text": text[:600], "shown": str(p.get("shown", ""))[:40],
            "url": f"https://x.com/{acc}/status/{pid}",
            "class": p.get("class") if p.get("class") in X_CLASSES else "미분류",
            "summary": _our_note(p.get("summary"), 200),
            "consumer": _our_note(p.get("consumer"), 80)}


def eval_d1(obs: list[tuple[str, float]], st: dict, rule: dict) -> tuple[dict, tuple[str, str] | None]:
    """관측일별로 저점 대비 bp를 다시 계산해 연속 횟수를 센다. 같은 관측일은 한 번만."""
    st = dict(st or {})
    st.setdefault("armed", True)
    st.setdefault("streak", 0)
    seen = st.get("last_obs", "")
    fired = None
    for i, (d, v) in enumerate(obs):
        if d <= seen:
            continue
        cut = (dt.date.fromisoformat(d) - dt.timedelta(days=rule["window_days"])).isoformat()
        win = [o[1] for o in obs[: i + 1] if o[0] >= cut]
        bp = round((v - min(win)) * 100)
        if not st["armed"]:
            if bp < rule["rearm_bp"]:
                st["armed"] = True
                st["streak"] = 0
            elif rule.get("step_bp") and bp >= st.get("ref_bp", rule["trigger_bp"]) + rule["step_bp"]:
                # v0.4 단계 재알림: 이미 걸려 닫힌 뒤(해제 전)에도 지난 점검 값보다 step_bp 더 벌어지면 다시 연다.
                st["streak"] += 1
                if st["streak"] >= rule["need"]:
                    ref = st.get("ref_bp", rule["trigger_bp"])
                    fired = (d, f"{rule['label']} {v:.2f}% · 183일 저점 대비 +{bp}bp ({d}) · 지난 점검 때(+{ref}bp)보다 "
                                f"+{rule['step_bp']}bp 이상 더 벌어짐 · 단계 재알림 {rule['need']}관측일 연속")
                    st["ref_bp"] = bp
                    st["streak"] = 0
            else:
                st["streak"] = 0
        elif bp >= rule["trigger_bp"]:
            st["streak"] += 1
            if st["streak"] >= rule["need"]:
                fired = (d, f"{rule['label']} {v:.2f}% · 183일 저점 대비 +{bp}bp ({d}) · {rule['need']}관측일 연속")
                st["armed"] = False
                st["ref_bp"] = bp
                st["streak"] = 0
        else:
            st["streak"] = 0
        st["last_obs"] = d
        st["last_bp"] = bp
    return st, fired


def eval_d2(obs: list[tuple[str, float]], st: dict, rule: dict) -> tuple[dict, tuple[str, str] | None]:
    st = dict(st or {})
    st.setdefault("armed", True)
    st.setdefault("streak", 0)
    seen = st.get("last_obs", "")
    fired = None
    for d, v in obs:
        if d <= seen:
            continue
        if not st["armed"]:
            if v < rule["rearm"]:
                st["armed"] = True
                st["streak"] = 0
        elif v >= rule["trigger"]:
            st["streak"] += 1
            if st["streak"] >= rule["need"]:
                fired = (d, f"{rule['label']} {v:.3f} ({d}) · 0 이상 {rule['need']}주 연속")
                st["armed"] = False
                st["streak"] = 0
        else:
            st["streak"] = 0
        st["last_obs"] = d
        st["last_value"] = v
    return st, fired


# ── v0.6 유동성·신용 (표시 전용 + D4) ──
def window_pct(obs: list[tuple[str, float]], days: int = LIQ_PCT_DAYS) -> tuple[float | None, int, str | None]:
    """마지막 값의 날짜 창(기본 3년) 백분위 = 창 안 값 가운데 마지막 값 이하인 몫(자기 포함). 반환 (pct, 창 안 개수, 창 첫 날짜)."""
    if not obs:
        return None, 0, None
    cut = (dt.date.fromisoformat(obs[-1][0]) - dt.timedelta(days=days)).isoformat()
    win = [o for o in obs if o[0] > cut]
    last = obs[-1][1]
    return sum(1 for o in win if o[1] <= last) / len(win), len(win), win[0][0]


def chg_block(obs: list[tuple[str, float]], k: int, days: int = LIQ_PCT_DAYS) -> dict | None:
    """k관측 변화와 그 변화의 날짜 창 백분위."""
    ch = [(obs[i][0], obs[i][1] - obs[i - k][1]) for i in range(k, len(obs))]
    if not ch:
        return None
    p, n, _ = window_pct(ch, days)
    return {"chg": round(ch[-1][1], 4), "pct": round(p, 3), "n": n}


def three_year(obs: list[tuple[str, float]], days: int = LIQ_PCT_DAYS) -> dict:
    """공통 칸: 값 · 3년 백분위 · 5·20관측 변화와 그 3년 백분위. 해석 문장은 넣지 않는다."""
    if not obs:
        return {"ok": False}
    p, n, first = window_pct(obs, days)
    return {"ok": True, "date": obs[-1][0], "value": obs[-1][1], "pct3y": round(p, 3), "n3y": n, "win_first": first,
            "c5": chg_block(obs, 5, days), "c20": chg_block(obs, 20, days)}


def rrp_at(rrp: list[tuple[str, float]], d: str, back_days: int = 7) -> float | None:
    """역레포(십억$) d일 값, 없으면(휴일) 7일 안 직전 영업일 값. 계열 시작 전 = 0."""
    import bisect
    keys = [x[0] for x in rrp]
    k = bisect.bisect_right(keys, d) - 1
    if k >= 0 and (dt.date.fromisoformat(d) - dt.date.fromisoformat(keys[k])).days <= back_days:
        return rrp[k][1]
    if d < RRP_START:
        return 0.0
    return None


def net_liquidity_weekly(walcl, wdtgal, rrp) -> list[tuple[str, float]]:
    """주간 순유동성(판정용, 백만$) = WALCL − WDTGAL − RRPONTSYD×1000, 같은 수요일. 어느 하나라도 없으면 그 주는 뺀다."""
    tga = dict(wdtgal)
    out = []
    for d, v in walcl:
        if d not in tga:
            continue
        r = rrp_at(rrp, d)
        if r is None:
            continue
        out.append((d, v - tga[d] - r * 1000))
    return out


def net_liquidity_daily(walcl, tga_rows, rrp) -> dict | None:
    """일간 순유동성(표시용, 판정에 안 씀) = 마지막 WALCL − 재무부 일일 TGA − 그날 역레포."""
    if not walcl or not tga_rows:
        return None
    t = tga_rows[-1]
    r = rrp_at(rrp, t["date"])
    if r is None:
        return None
    return {"date": t["date"], "walcl_date": walcl[-1][0], "value": walcl[-1][1] - t["musd"] - r * 1000}


def d4_series(nl: list[tuple[str, float]], rule: dict = None) -> list[tuple[str, float, float, float]]:
    """[(수요일, 4주간 변화의 156주간 굴림 백분위, 4주간 변화 백만$, 4주간 변화율)] — 백분위를 낼 수 있는 주만."""
    rule = rule or LIQ_D4
    k = rule["k"]
    ch = [(nl[i][0], nl[i][1] - nl[i - k][1]) for i in range(k, len(nl))]
    base = {nl[i][0]: nl[i - k][1] for i in range(k, len(nl))}
    pct = pct_rolling(ch, rule["win"])
    return [(d, pct[d], c, c / base[d] if base[d] else 0.0) for d, c in ch if d in pct]


def eval_d4(nl, st: dict, rule: dict = None) -> tuple[dict, tuple[str, str] | None]:
    """D4: 하위 20%에 '새로' 들어간 주(전주 밖 → 이번 주 안). 첫 실행은 상태만 적고 열지 않는다(이미 켜진 것은 표시만).
    같은 주는 한 번만 본다. 반환 (새 상태, (수요일, 이유) 또는 None) — 여러 주가 새로 들어오면 마지막 켜짐."""
    rule = rule or LIQ_D4
    st = dict(st or {})
    first = "last_obs" not in st
    fired = None
    for d, p, c, r in d4_series(nl, rule):
        if d <= st.get("last_obs", ""):
            continue
        on = p <= rule["bot"]
        if on and not first and st.get("prev") == "off":
            fired = (d, f"순유동성(연준 총자산 − TGA − 역레포) 4주간 변화가 156주간 굴림 백분위 {p:.2f}로 하위 20%에 새로 들어감"
                        f"(수요일 {d} · 4주간 변화율 {r * 100:+.1f}%) · 점검 열기용, 매매 규칙 아님·미검증 문턱")
        st["prev"] = "on" if on else "off"
        st["last_obs"] = d
        st["last_pct"] = round(p, 3)
    if first:
        st["seeded"] = st.get("last_obs")
    return st, fired


def liq_compute(hy_obs, tga_rows, walcl, wdtgal, rrp) -> dict:
    """numbers 기록용 유동성 칸(표시 전용). 계산 못 한 칸은 ok False."""
    nl = net_liquidity_weekly(walcl, wdtgal, rrp)
    seq = d4_series(nl) if nl else []
    out = {"hy": three_year(hy_obs), "tga": three_year([(r["date"], r["musd"]) for r in tga_rows]),
           "nl_w": three_year(nl), "nl_d": net_liquidity_daily(walcl, tga_rows, rrp)}
    if seq:
        d, p, c, r = seq[-1]
        out["d4"] = {"date": d, "pct": round(p, 3), "chg": round(c), "chg_rate": round(r, 4), "on": p <= LIQ_D4["bot"]}
    return out


# ── 파일 ──
def load_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def append_jsonl(p: Path, rec: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_jsonl(p: Path) -> list[dict]:
    out = []
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for line in lines:
        if line.strip():
            try:
                out.append(json.loads(line))
            except ValueError:  # 깨진 줄 하나 때문에 전체가 멈추지 않게(다른 쪽이 쓰는 닫힘 파일 포함)
                print("JSONL_BAD_LINE", p.name)
    return out


def today_kst() -> str:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)).date().isoformat()


def now_kst() -> str:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M KST")


# ── 심리 단서 (psych-1123, v0.5) — 표시와 D3 점검 열기 전용. 정의 원본 = /mnt/project-files/psych-strategy-1123/psych-grade/
# psych-grade-prereg-2026-11-23.md 3-1·3-3·6절(고정). 아래 계산 함수는 고정된 psych_grade.py의 같은 이름 함수와 같은 규칙이다.
# 매매 판정·노출·한도·코어·예약과 연결 없음. 증거 강도 0.
FINRA_URL = "https://www.finra.org/sites/default/files/2021-03/margin-statistics.xlsx"
PSYCH_CFTC_CODE = "209742"
PSYCH_H = 60                      # 사건 간격(세션)
PSYCH_TOP, PSYCH_BOT = 0.80, 0.20
PSYCH_S1_MIN_HIST = 60            # S1 누적 백분위 최소 이력(1년 변화율 개수)
PSYCH_S2_WIN = 156                # S2 굴림 창(보고 수)
PSYCH_S2_EXCLUDE = (("2010-01-01", "2010-12-05"), ("2013-10-01", "2013-11-30"),
                    ("2018-12-22", "2019-03-31"), ("2025-10-01", "2026-01-31"))
PSYCH_CLUES = ("S1-", "S1+", "S2-", "S2+")
PSYCH_NAME = {"S1-": "S1− 신용 과열", "S1+": "S1+ 신용 정리", "S2-": "S2− 선물 과매수", "S2+": "S2+ 선물 과매도"}
# 등급은 2026-11-23 등급표 결과(심리 지표 신뢰 기준 2절) — 다시 계산하지 않는다.
PSYCH_GRADE = {"S1-": "판정 불가(표본 부족)", "S1+": "판정 불가(표본 부족)",
               "S2-": "판정 불가", "S2+": "3(5%p 넘는 효과 없음 확인 — 근거로 인용 안 함)"}
PSYCH_NASDAQ_MIN = "2002-01-01"
# 수집 시작 전에 3-3 정의로 잡힌 마지막 사건 시작일(사전 등록 6절) — 시작 때 같은 정의로 계산한 값과 같아야 한다(시험).
PSYCH_START_ANCHORS = {"S1-": "2025-10-01"}


def parse_finra_xlsx(data: bytes) -> list[tuple[str, float]]:
    """FINRA margin-statistics.xlsx → [(YYYY-MM, 신용 잔고(Debit Balances))] 오름차순. 모양이 다르면 빈 목록."""
    import xml.etree.ElementTree as ET
    import zipfile
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        strings = ["".join(t.text or "" for t in si.iter("{%s}t" % ns["m"]))
                   for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns)]
        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    cells: dict[str, str] = {}
    for c in sheet.iter("{%s}c" % ns["m"]):
        v = c.find("m:v", ns)
        if v is None or v.text is None:
            continue
        cells[c.get("r")] = strings[int(v.text)] if c.get("t") == "s" else v.text
    if "Debit Balances" not in cells.get("B1", "") or cells.get("A1") != "Year-Month":
        return []
    out = []
    r = 2
    while f"A{r}" in cells:
        key = cells[f"A{r}"]
        if re.fullmatch(r"\d{4}-\d{2}", key) and f"B{r}" in cells:
            out.append((key, float(cells[f"B{r}"])))
        r += 1
    return sorted(out)


def parse_cftc_psych(text: str) -> list[tuple[str, float]]:
    """CFTC TFF 나스닥100 미니(209742) → [(보고 기준일, (레버리지 펀드 매수−매도)÷미결제약정)] 오름차순."""
    out = []
    for r in json.loads(text):
        try:
            if r.get("cftc_contract_market_code") != PSYCH_CFTC_CODE:
                continue
            oi = int(r["open_interest_all"])
            if oi <= 0:
                continue
            out.append((r["report_date_as_yyyy_mm_dd"][:10],
                        (int(r["lev_money_positions_long"]) - int(r["lev_money_positions_short"])) / oi))
        except (KeyError, ValueError, TypeError):
            continue
    return sorted(out)


def parse_nasdaq(text: str) -> list[tuple[str, float]]:
    return [(d, v) for d, v in parse_fred(text, "NASDAQCOM") if d >= PSYCH_NASDAQ_MIN]


def month_add(key: str, n: int) -> str:
    """'YYYY-MM' 또는 'YYYY-MM-DD'에 n달을 더해 'YYYY-MM-01'."""
    y, m = int(key[:4]), int(key[5:7]) + n
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 12
        y -= 1
    return "%04d-%02d-01" % (y, m)


def s1_usable(key: str) -> str:
    return month_add(key, 2)                       # M월 값 → M+2월 1일 당일 또는 그 뒤 첫 세션


def s2_usable(key: str) -> str:
    d = dt.date.fromisoformat(key)                  # 보고 기준일이 든 주의 다음 주 화요일
    return (d + dt.timedelta(days=8 - d.weekday())).isoformat()


def finra_yoy(finra: list[tuple[str, float]]) -> list[tuple[str, float]]:
    val = dict(finra)
    out = []
    for ym, v in finra:
        prev = "%04d-%s" % (int(ym[:4]) - 1, ym[5:7])
        if prev in val:
            out.append((ym, v / val[prev] - 1))
    return out


def pct_expanding(series: list[tuple[str, float]], min_hist: int) -> dict[str, float]:
    out = {}
    for k in range(len(series)):
        if k + 1 < min_hist:
            continue
        hist = [x for _, x in series[: k + 1]]
        out[series[k][0]] = sum(1 for x in hist if x <= series[k][1]) / len(hist)
    return out


def pct_rolling(series: list[tuple[str, float]], win: int) -> dict[str, float]:
    out = {}
    for k in range(len(series)):
        if k + 1 < win:
            continue
        hist = [x for _, x in series[k + 1 - win: k + 1]]
        out[series[k][0]] = sum(1 for x in hist if x <= series[k][1]) / len(hist)
    return out


def first_on_or_after(sess: list[str], d: str) -> int | None:
    import bisect
    k = bisect.bisect_left(sess, d)
    return k if k < len(sess) else None


def states_from(sess, pmap, cond, usable):
    """값 key는 usable(key) 당일 또는 그 뒤 첫 세션부터 다음 key가 쓰이기 전날까지. 계산 불가 = None."""
    st = [None] * len(sess)
    keys = sorted(pmap)
    for n, key in enumerate(keys):
        a = first_on_or_after(sess, usable(key))
        if a is None:
            continue
        if n + 1 < len(keys):
            b = first_on_or_after(sess, usable(keys[n + 1]))
            b = len(sess) if b is None else b
        else:
            b = len(sess)
        for i in range(a, b):
            st[i] = cond(pmap[key])
    return st


def event_chain(sess, st, last_start, exclude=()):
    """사전 등록 3-3. 반환 = [(세션 번호, 셈 여부)]. 사건 = 계산 가능한 꺼짐 바로 다음의 켜짐 가운데
    바로 앞 사건(셈 여부와 상관없이)에서 60세션 이상 떨어진 것. 계산 불가 뒤 첫 켜짐은 사건이 아니다."""
    out, prev_off, last_ev = [], False, -10 ** 9
    for i, s in enumerate(st):
        if s is None:
            prev_off = False
            continue
        if s and prev_off and i - last_ev >= PSYCH_H and i <= last_start:
            out.append((i, not any(a <= sess[i] <= b for a, b in exclude)))
            last_ev = i
        prev_off = not s
    return out


def psych_build(sess, finra, cftc):
    """네 단서의 세션별 상태 + 최신 백분위. 반환 (states{clue: [True/False/None]}, info)."""
    s1p = pct_expanding(finra_yoy(finra), PSYCH_S1_MIN_HIST)
    s2p = pct_rolling(cftc, PSYCH_S2_WIN)
    hi = lambda p: p >= PSYCH_TOP
    lo = lambda p: p <= PSYCH_BOT
    states = {"S1-": states_from(sess, s1p, hi, s1_usable), "S1+": states_from(sess, s1p, lo, s1_usable),
              "S2-": states_from(sess, s2p, hi, s2_usable), "S2+": states_from(sess, s2p, lo, s2_usable)}
    # 표시 값 = 마지막 세션에 쓸 수 있는(usable 날짜가 지난) 가장 최근 값. 아직 쓸 수 없는 최신 보고는 보이지 않는다.
    k1 = max((k for k in s1p if s1_usable(k) <= sess[-1]), default=None)
    k2 = max((k for k in s2p if s2_usable(k) <= sess[-1]), default=None)
    yoy = dict(finra_yoy(finra))
    info = {"s1_key": k1, "s1_pct": s1p.get(k1), "s1_yoy": yoy.get(k1),
            "s2_key": k2, "s2_pct": s2p.get(k2), "s2_val": dict(cftc).get(k2)}
    return states, info


def psych_missing(day_last: str, finra, cftc) -> dict[str, bool]:
    """마지막 세션에 쓸 값을 못 받았나(못 받은 주·달은 계산 불가 — 사전 등록 3-1). True = 못 받음."""
    d = dt.date.fromisoformat(day_last)
    need_m = month_add(d.isoformat(), -2)[:7]
    s1_miss = (not finra) or finra[-1][0] < need_m
    # 보고 기준일 r의 쓸 수 있는 날 = 다음 주 화요일(= 화요일 기준일 + 7일). 그 날짜가 지난 가장 최근 화요일 기준일을 받았어야 한다.
    cutoff = d - dt.timedelta(days=7)
    tue = cutoff - dt.timedelta(days=(cutoff.weekday() - 1) % 7)
    s2_miss = (not cftc) or dt.date.fromisoformat(cftc[-1][0]) < tue - dt.timedelta(days=1)
    return {"S1": s1_miss, "S2": s2_miss}


def s2_cadence_ok(cftc) -> bool:
    """최근 8개 보고가 주 1회(5~8일 간격)인가. 아니면(주 2회 공개 등) S2의 D3는 멈춘다(사전 등록 6절)."""
    ds = [dt.date.fromisoformat(d) for d, _ in cftc[-8:]]
    return len(ds) >= 8 and all(5 <= (b - a).days <= 8 for a, b in zip(ds, ds[1:]))


def psych_eval(px, finra, cftc, prev_state: dict | None):
    """한 번 계산: 단서 상태·표시 값·새 사건. prev_state = state.signals.D3(없으면 시작 기준을 지금 계산해 적고 새 사건 없음).
    반환 (record, new_state, new_events[{clue, session}])."""
    sess = [d for d, _ in px]
    states, info = psych_build(sess, finra, cftc)
    last = len(sess) - 1
    miss = psych_missing(sess[-1], finra, cftc)
    cad = s2_cadence_ok(cftc)
    if miss["S1"]:
        for c in ("S1-", "S1+"):
            states[c][last] = None
    if miss["S2"] or not cad:
        for c in ("S2-", "S2+"):
            states[c][last] = None
    new_state = {"clues": {}, "seeded": (prev_state or {}).get("seeded"), "queue": list((prev_state or {}).get("queue", []))}
    events = []
    for c in PSYCH_CLUES:
        st = states[c]
        excl = PSYCH_S2_EXCLUDE if c.startswith("S2") else ()
        cs = ((prev_state or {}).get("clues") or {}).get(c)
        if cs is None:   # 시작 기준: 지금까지의 사건 사슬(간격 기준에 넣음). 이미 켜진 단서는 열지 않는다(표시만).
            ch = event_chain(sess, st, last, excl)
            last_ev = sess[ch[-1][0]] if ch else None
            anchor = PSYCH_START_ANCHORS.get(c)   # 사전 등록 6절이 적은 값 — 사슬보다 늦으면 그것을 쓴다(S2−는 6절의 10-20이 '켜진 시작일'을 잘못 옮긴 값이라 사슬 2026-09-08을 그대로 씀, 심리 스레드 11/23 확인)
            if anchor and (last_ev is None or anchor > last_ev):
                last_ev = anchor
            cs = {"prev": "none" if st[last] is None else ("on" if st[last] else "off"),
                  "last_ev": last_ev, "last_eval": sess[last]}
            new_state["seeded"] = new_state["seeded"] or sess[last]
        else:
            cs = dict(cs)
            idx = {d: i for i, d in enumerate(sess)}
            start = idx.get(cs.get("last_eval"), -1) + 1
            last_ev = idx.get(cs.get("last_ev"), -10 ** 9) if cs.get("last_ev") else -10 ** 9
            prev = cs.get("prev", "none")
            halted = c.startswith("S2") and not cad
            for i in range(start, len(sess)):
                s = st[i]
                if s is None:
                    prev = "none"
                    continue
                if s and prev == "off" and i - last_ev >= PSYCH_H:
                    counted = not any(a <= sess[i] <= b for a, b in excl)
                    last_ev = i
                    if counted and not halted:
                        events.append({"clue": c, "session": sess[i]})
                prev = "off" if not s else "on"
            cs = {"prev": prev, "last_ev": sess[last_ev] if last_ev >= 0 else cs.get("last_ev"),
                  "last_eval": sess[last]}
        new_state["clues"][c] = cs
    rec = {"session": sess[last], "clues": {}, "missing": miss, "s2_cadence_ok": cad, "info": info}
    for c in PSYCH_CLUES:
        st = states[c]
        s = st[last]
        n = None
        if s:
            i = last
            while i > 0 and st[i - 1]:
                i -= 1
            n = last - i
            rec["clues"][c] = {"on": True, "n_sessions": n, "since": sess[i]}
        else:
            rec["clues"][c] = {"on": None if s is None else False}
    return rec, new_state, events


def psych_load():
    """저장된 원자료 → (px, finra, cftc, 상태 설명). 하나라도 없으면 None."""
    out = {}
    for key, name in (("nasdaq", "nasdaqcom.csv"), ("finra", "finra.xlsx"), ("cftc", "cftc_psych.json")):
        p = latest_raw(name)
        if p is None:
            return None, f"원자료 없음({name})"
        out[key] = p
    px = parse_nasdaq(out["nasdaq"].read_text(encoding="utf-8"))
    finra = parse_finra_xlsx(out["finra"].read_bytes())
    cftc = parse_cftc_psych(out["cftc"].read_text(encoding="utf-8"))
    if not px or not finra or not cftc:
        return None, "원자료 모양 이상(나스닥·FINRA·CFTC 중 빈 것)"
    return (px, finra, cftc), None


def psych_reason(rec: dict, ev: dict) -> str:
    c = ev["clue"]
    inf = rec["info"]
    if c.startswith("S1"):
        what = f"FINRA 신용 잔고 1년 변화율 누적 백분위 {inf['s1_pct']:.2f}({inf['s1_key']} 값)"
    else:
        what = f"CFTC 나스닥100 레버리지 펀드 순포지션 비율 156보고 백분위 {inf['s2_pct']:.2f}(기준일 {inf['s2_key']})"
    return f"{PSYCH_NAME[c]} 새로 켜짐(첫 세션 {ev['session']}) · {what} · 표시·점검 열기용, 등급 {PSYCH_GRADE[c]}"


def psych_fetch_status(day: dt.date, finra, cftc, px) -> dict[str, str]:
    """numbers의 상태 칸 — 쓸 수 있는 날까지 못 받은 달·주가 없는지."""
    miss = psych_missing(day.isoformat(), finra, cftc)
    return {"FINRA": "STALE" if miss["S1"] else "OK",
            "CFTC_LEV": "STALE" if miss["S2"] else "OK",
            "NASDAQCOM": "STALE" if (not px) or (day - dt.date.fromisoformat(px[-1][0])).days > 6 else "OK"}


# ── 명령 ──
def cmd_numbers(a) -> int:
    day = dt.date.fromisoformat(a.day)
    off = Path(a.offline) if a.offline else None
    raw_dir = DATA / "raw" / a.day
    rec = {"day": a.day, "at": now_kst(), "version": VERSION, "fred": {}, "cftc": {}, "tga": None, "status": {}}
    start = (day - dt.timedelta(days=FRED_LOOKBACK_DAYS)).isoformat()
    raw_dir.mkdir(parents=True, exist_ok=True)
    got: dict[str, list] = {}
    for sid in list(FRED_SERIES) + list(LIQ_SERIES):
        try:
            txt = read_source(f"{sid}.csv", f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start}", off)
            (raw_dir / f"{sid}.csv").write_text(txt, encoding="utf-8")
            obs = parse_fred(txt, sid)
            got[sid] = obs
            s = fred_summary(obs) if sid in FRED_SERIES else (
                {"ok": True, "date": obs[-1][0], "value": obs[-1][1]} if obs else {"ok": False})
            stale = (not s["ok"]) or (day - dt.date.fromisoformat(s["date"])).days > STALE_DAYS.get(sid, 6)
            rec["fred"][sid] = s
            rec["status"][sid] = "STALE" if stale else "OK"
        except Exception as e:  # noqa: BLE001 — 자료마다 독립
            rec["status"][sid] = f"STALE({type(e).__name__})"
    for key, name in CFTC_MARKETS.items():
        try:
            q = urllib.request.quote(f"market_and_exchange_names like '%{name}%'")
            url = (f"https://publicreporting.cftc.gov/resource/gpe5-46if.json?$where={q}"
                   f"&$order=report_date_as_yyyy_mm_dd%20DESC&$limit=8")
            txt = read_source(f"cftc_{key}.json", url, off)
            (raw_dir / f"cftc_{key}.json").write_text(txt, encoding="utf-8")
            rows = parse_cftc(txt)
            rec["cftc"][key] = rows[-4:]
            stale = (not rows) or (day - dt.date.fromisoformat(rows[-1]["date"])).days > 14
            rec["status"][f"CFTC_{key}"] = "STALE" if stale else "OK"
        except Exception as e:  # noqa: BLE001
            rec["status"][f"CFTC_{key}"] = f"STALE({type(e).__name__})"
    try:
        # v0.6: 마감 잔액 행만, 3년+ 이력(약 900행·110 KB) — 3년 백분위·변화를 위해. 기록(numbers.jsonl)에는 마지막 3행만.
        tga_start = (day - dt.timedelta(days=TGA_LOOKBACK_DAYS)).isoformat()
        flt = urllib.request.quote(f"account_type:eq:Treasury General Account (TGA) Closing Balance,record_date:gte:{tga_start}")
        url = ("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/"
               f"operating_cash_balance?fields=record_date,account_type,open_today_bal&filter={flt}"
               "&page%5Bsize%5D=1500&sort=-record_date")
        txt = read_source("tga.json", url, off)
        (raw_dir / "tga.json").write_text(txt, encoding="utf-8")
        rows = parse_tga(txt)
        got["TGA"] = rows
        rec["tga"] = rows[-3:] if rows else None
        stale = (not rows) or (day - dt.date.fromisoformat(rows[-1]["date"])).days > 6
        rec["status"]["TGA"] = "STALE" if stale else "OK"
    except Exception as e:  # noqa: BLE001
        rec["status"]["TGA"] = f"STALE({type(e).__name__})"
    # v0.5 심리 단서 자료(psych-1123): FINRA 신용 잔고(월)·CFTC 나스닥100 레버리지 펀드(209742)·나스닥 종합(FRED) — 표시·D3 전용
    p_px, p_finra, p_cftc = [], [], []
    try:
        b = read_bytes_source("finra.xlsx", FINRA_URL, off)
        p_finra = parse_finra_xlsx(b)
        if p_finra:
            (raw_dir / "finra.xlsx").write_bytes(b)
        else:
            rec["status"]["FINRA"] = "STALE(모양 다름)"
    except Exception as e:  # noqa: BLE001
        rec["status"]["FINRA"] = f"STALE({type(e).__name__})"
    try:
        sel = "report_date_as_yyyy_mm_dd,cftc_contract_market_code,lev_money_positions_long,lev_money_positions_short,open_interest_all"
        q = urllib.request.quote(f"cftc_contract_market_code='{PSYCH_CFTC_CODE}'")
        txt = read_source("cftc_psych.json", f"https://publicreporting.cftc.gov/resource/gpe5-46if.json?$select={sel}"
                          f"&$where={q}&$order=report_date_as_yyyy_mm_dd%20ASC&$limit=5000", off)
        p_cftc = parse_cftc_psych(txt)
        if p_cftc:
            (raw_dir / "cftc_psych.json").write_text(txt, encoding="utf-8")
        else:
            rec["status"]["CFTC_LEV"] = "STALE(빈 자료)"
    except Exception as e:  # noqa: BLE001
        rec["status"]["CFTC_LEV"] = f"STALE({type(e).__name__})"
    try:
        txt = read_source("nasdaqcom.csv", f"https://fred.stlouisfed.org/graph/fredgraph.csv?id=NASDAQCOM&cosd={PSYCH_NASDAQ_MIN}", off)
        p_px = parse_nasdaq(txt)
        if p_px:
            (raw_dir / "nasdaqcom.csv").write_text(txt, encoding="utf-8")
        else:
            rec["status"]["NASDAQCOM"] = "STALE(빈 자료)"
    except Exception as e:  # noqa: BLE001
        rec["status"]["NASDAQCOM"] = f"STALE({type(e).__name__})"
    for k, v in psych_fetch_status(day, p_finra, p_cftc, p_px).items():
        rec["status"].setdefault(k, v)
    try:  # v0.6 유동성 칸(표시 전용) — 계산 실패는 다른 자료를 막지 않는다
        rec["liq"] = liq_compute(got.get("BAMLH0A0HYM2", []), got.get("TGA", []), got.get("WALCL", []),
                                 got.get("WDTGAL", []), got.get("RRPONTSYD", []))
    except Exception as e:  # noqa: BLE001
        rec["liq"] = {"error": type(e).__name__}
    append_jsonl(DATA / "numbers.jsonl", rec)
    bad = [k for k, v in rec["status"].items() if v != "OK"]
    st = load_json(STATE, {})
    streak = st.setdefault("stale_streak", {})
    for k, v in rec["status"].items():
        streak[k] = 0 if v == "OK" else streak.get(k, 0) + 1
    save_json(STATE, st)
    print("numbers", a.day, "OK" if not bad else "STALE " + ",".join(bad))
    for k, n in streak.items():
        if notify_count(n):
            print("STALE_STREAK", k, n)  # 2회 연속 → 이 스레드에 1줄, 그 뒤 3일(6회)마다
    prune_raw(day)
    return 0 if not bad else 2


def read_tickers(path: Path) -> list[str]:
    """tickers.txt: 한 줄에 종목 하나, # 뒤는 주석."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        t = line.split("#", 1)[0].strip().upper()
        if t:
            out.append(t)
    return out


def cmd_finviz(a) -> int:
    src = a.tickers if a.tickers else ",".join(read_tickers(Path(a.tickers_file) if a.tickers_file else ROOT / "tickers.txt"))
    tickers = [t.strip().upper() for t in src.split(",") if t.strip()]
    tickers = [t for t in tickers if re.fullmatch(r"[A-Z.]{1,6}", t)][:FINVIZ_MAX]
    off = Path(a.offline) if a.offline else None
    prior = [r for r in read_jsonl(DATA / "finviz.jsonl") if r.get("day", "") < a.day]
    out = {"day": a.day, "at": now_kst(), "version": VERSION, "rows": {}, "bench": {}, "status": {}}
    jobs = [(t, "rows") for t in tickers] + ([(FINVIZ_BENCH, "bench")] if FINVIZ_BENCH not in tickers else [])
    for i, (t, where) in enumerate(jobs):
        try:
            txt = read_source(f"finviz_{t}.html", f"https://finviz.com/quote.ashx?t={t}", off, FINVIZ_UA)
            row = parse_finviz(txt)
            out[where][t] = row
            out["status"][t] = "OK" if row else "STALE(empty)"
        except Exception as e:  # noqa: BLE001
            out["status"][t] = f"STALE({type(e).__name__})"
        if off is None and i + 1 < len(jobs):
            time.sleep(2)
    append_jsonl(DATA / "finviz.jsonl", out)
    bad = [k for k, v in out["status"].items() if v != "OK"]
    print("finviz", a.day, len(tickers), "OK" if not bad else "STALE " + ",".join(bad))
    try:   # 시장 폭 쪽 예외가 아래 v0.7 종목 화면 알림·저장을 막지 않게
        b_bad = breadth_step(a, off)
    except Exception as e:  # noqa: BLE001
        print("breadth", a.day, f"STALE({type(e).__name__})")
        b_bad = True
    # v0.7 0-나: 연속 실패·빠진 날 알림(같은 날 여러 번 돌려도 그날 첫 실행 전 값에서 다시 계산)
    st = load_json(STATE, {})
    fz = st.setdefault("finviz", {})
    if fz.get("last_day") != a.day:
        fz["base"] = fz.get("streak", 0)
        fz["last_day"] = a.day
        before = None
    else:
        before = fz.get("streak", 0)
    fz["streak"] = 0 if not bad else fz.get("base", 0) + 1
    if notify_count(fz["streak"]) and fz["streak"] != before:
        print("FINVIZ_STREAK", fz["streak"], ",".join(bad))
    if prior:
        last_day = max(r["day"] for r in prior)
        gap = (dt.date.fromisoformat(a.day) - dt.date.fromisoformat(last_day)).days
        if gap >= 2:
            print("FINVIZ_GAP", f"마지막 기록 {last_day} 뒤 {gap - 1}일 빠짐")
    save_json(STATE, st)
    return 0 if not (bad or b_bad) else 2


def breadth_step(a, off: Path | None) -> bool:
    """v0.8: finviz 첫 화면 1회 → 시장 폭 6칸을 미국 세션 날짜당 1줄(data/breadth.jsonl). 못 받았으면 True.
    시각은 실제 시계(오프라인 시험은 그날 06:20 KST로 본다). 이미 기록한 세션이면 받지 않는다(주말 회차가 금요일 실패를 다시 시도)."""
    st = load_json(STATE, {})
    bz = st.setdefault("breadth", {})
    if a.day > BREADTH_STOP:
        if not bz.get("stopped"):
            print("BREADTH_STOPPED", f"{BREADTH_STOP} 지나 시장 폭 수집 멈춤(README 1절 예외 기한 — 읽는 점검이 생겼으면 새 판에서 기한을 고친다)")
            bz["stopped"] = a.day
            save_json(STATE, st)
        return False
    if off is None and a.day != today_kst():
        print("breadth", a.day, "SKIP(과거 날짜 — 실제 받기는 오늘 날짜로만)")
        return False
    now = (dt.datetime.fromisoformat(a.day + "T06:20") - dt.timedelta(hours=9)).replace(tzinfo=dt.timezone.utc) if off is not None else _utc_now()
    sess = breadth_session(now)
    hist = read_jsonl(DATA / "breadth.jsonl")
    if sess is None:
        print("breadth", a.day, "SKIP(미국 장중 — 기록 안 함)")
        return False
    if any(r.get("session") == sess for r in hist):
        print("breadth", a.day, sess, "SKIP(이미 기록)")
        return False
    if off is None:
        time.sleep(2)                          # finviz 2초 간격(README 1절)
    try:
        rec = parse_breadth(read_source("finviz_home.html", BREADTH_URL, off, FINVIZ_UA))
        status = "OK" if rec else "STALE(empty)"
    except Exception as e:  # noqa: BLE001
        rec, status = None, f"STALE({type(e).__name__})"
    if bz.get("last_day") != a.day:          # 같은 날 여러 번 돌려도 그날 첫 실행 전 값에서 다시 계산(v0.7 finviz와 같은 방식)
        bz["base"], bz["last_day"], before = bz.get("streak", 0), a.day, None
    else:
        before = bz.get("streak", 0)
    bz["streak"] = 0 if rec else bz.get("base", 0) + 1
    if rec:
        prev = hist[-1] if hist else None
        line = {"session": sess, "day": a.day, "at": now_kst() if off is None else a.day + " 06:20 KST", "version": VERSION,
                "src": "finviz 첫 화면", **rec, "h13": BREADTH_H13,
                "repeat": bool(prev) and all(prev.get(k) == rec[k] for k in BREADTH_KEYS)}
        append_jsonl(DATA / "breadth.jsonl", line)
        print("breadth", a.day, sess, "OK" + (" (직전 세션과 6칸 모두 같음 — 휴장일 또는 갱신 안 됨)" if line["repeat"] else ""))
        if prev and prev.get("session", "") < sess:
            n = weekdays_between(prev["session"], sess)
            if n:
                print("BREADTH_GAP", f"마지막 기록 세션 {prev['session']} 뒤 평일 {n}일 빠짐(과거 값은 다시 못 받음)")
    else:
        print("breadth", a.day, sess, status)
    if notify_count(bz["streak"]) and bz["streak"] != before:
        print("BREADTH_STREAK", bz["streak"], status)
    save_json(STATE, st)
    return not rec


def cmd_roster(a) -> int:
    """월요일 명단 대조 결과 기록(v0.7). checked = 일치, changed = tickers.txt를 고침, skipped = 회사PC 연결 안 돼 넘어감."""
    st = load_json(STATE, {})
    ro = st.setdefault("roster", {})
    last = ro.get("last_day")
    same_week = bool(last) and abs((dt.date.fromisoformat(a.day) - dt.date.fromisoformat(last)).days) < 6
    if not same_week:
        ro["skip_streak"] = (ro.get("skip_streak", 0) + 1) if a.status == "skipped" else 0
    elif a.status != "skipped":
        ro["skip_streak"] = 0
    ro["last_day"], ro["last_status"] = a.day, a.status
    if a.status != "skipped":
        ro["last_checked"] = a.day
    save_json(STATE, st)
    print("roster", a.day, a.status, "skip_streak", ro["skip_streak"])
    if a.status == "skipped" and ro["skip_streak"] >= 2:
        print("ROSTER_SKIP_STREAK", ro["skip_streak"], f"마지막 대조 성공 {ro.get('last_checked', '없음')}")
    return 0


def cmd_x_add(a) -> int:
    posts = load_json(Path(a.file), [])
    have = {r["id"] for r in read_jsonl(DATA / "x.jsonl")}
    new = 0
    for p in posts if isinstance(posts, list) else []:
        c = clean_post(p)
        if c and c["id"] not in have:
            c["day"] = a.day
            c["at"] = now_kst()
            append_jsonl(DATA / "x.jsonl", c)
            have.add(c["id"])
            new += 1
    st = load_json(STATE, {})
    xs = st.setdefault("x", {})
    xs["last_ok"] = a.day if posts else xs.get("last_ok")
    xs["fail_streak"] = 0 if posts else xs.get("fail_streak", 0) + 1
    save_json(STATE, st)
    print("x-add", a.day, "new", new, "fail_streak", xs["fail_streak"])
    if notify_count(xs["fail_streak"]):
        print("X_STREAK", xs["fail_streak"])
    return 0 if posts else 2


def notify_count(n: int) -> bool:
    """연속 실패 알림: 2회째 1번, 그 뒤 6회(하루 2번 실행 = 3일)마다 1번."""
    return n == 2 or (n > 2 and (n - 2) % 6 == 0)


RAW_KEEP_DAYS = 35


def prune_raw(day: dt.date) -> None:
    """원자료는 35일만 둔다(판정은 최근 183일 자료를 매번 새로 받음 — 지난 원자료는 다시 쓰지 않음)."""
    for d in (DATA / "raw").glob("*"):
        try:
            if (day - dt.date.fromisoformat(d.name)).days > RAW_KEEP_DAYS:
                for f in d.iterdir():
                    f.unlink()
                d.rmdir()
        except (ValueError, OSError):
            continue


def cmd_x_seen(a) -> int:
    """계정별로 이미 저장한 글 id(최근 40개) — Chrome에서 새 글만 본문을 읽기 위해."""
    rows = read_jsonl(DATA / "x.jsonl")
    for acc in X_ACCOUNTS:
        ids = [r["id"] for r in rows if r.get("account") == acc][-40:]
        print(acc, " ".join(ids) if ids else "-")
    return 0


def cmd_usage(a) -> int:
    """4주 쓸모 집계(G7): 계정별 글 수·분류, 데이터 점검 연 횟수·끝낸 횟수. 쓸모 0이면 '내리자' 후보."""
    since = a.since
    rows = [r for r in read_jsonl(DATA / "x.jsonl") if r.get("day", "") >= since]
    for acc in X_ACCOUNTS:
        mine = [r for r in rows if r.get("account") == acc]
        cls = {}
        for r in mine:
            cls[r["class"]] = cls.get(r["class"], 0) + 1
        used = sum(v for k, v in cls.items() if k in ("P후보", "시나리오 증거")) + sum(1 for r in mine if r.get("consumer"))
        print("X", acc, "글", len(mine), "분류", json.dumps(cls, ensure_ascii=False), "쓸모", used, "" if used else "→ 내리자 후보")
    pend = [x for x in load_json(PENDING, []) if x.get("since", "") >= since]
    print("DATA_CHECK 연 횟수", len(pend), "끝낸 횟수", sum(1 for x in pend if x.get("done")))
    fv = [r for r in read_jsonl(DATA / "finviz.jsonl") if r.get("day", "") >= since]
    print("finviz 실행", len(fv), "(쓸모는 카드·점검 기록에서 사람이 셈 — 확인 필요)")
    return 0


def latest_raw(name: str) -> Path | None:
    days = sorted((d for d in (DATA / "raw").glob("*") if (d / name).exists()), key=lambda d: d.name)
    return days[-1] / name if days else None


def latest_numbers() -> dict | None:
    rows = read_jsonl(DATA / "numbers.jsonl")
    return rows[-1] if rows else None


def cmd_signals(a) -> int:
    rec = latest_numbers()
    if not rec:
        print("signals: numbers 없음")
        return 3
    st = load_json(STATE, {})
    sig = st.setdefault("signals", {})
    pend = load_json(PENDING, [])
    close_from_file(pend)
    fired_any = False
    for rid, rule in RULES.items():
        p = latest_raw(f"{rule['series']}.csv")
        if p is None:
            print("DATA_CHECK_SKIP", rid, "원자료 없음")
            continue
        if p.parent.name != a.day:
            print("DATA_CHECK_OLD", rid, "원자료", p.parent.name)
        obs = parse_fred(p.read_text(encoding="utf-8"), rule["series"])
        fn = eval_d1 if rid == "D1" else eval_d2
        first = rid not in sig
        new_st, fired = fn(obs, sig.get(rid, {}), rule)
        sig[rid] = new_st
        reason = None
        if fired and (dt.date.fromisoformat(a.day) - dt.date.fromisoformat(fired[0])).days <= 10:
            reason = fired[1]
        elif first and not new_st.get("armed", True):
            # 첫 실행: 과거에 넘었고 아직 해제선 아래로 안 내려옴 = 점검 기록 없이 문턱 위 → 한 번 연다.
            now_v = f"+{new_st.get('last_bp')}bp" if rid == "D1" else f"{new_st.get('last_value')}"
            reason = (f"첫 실행: {rule['label']}가 이미 문턱 위에 머묾(지금 {now_v}, {new_st.get('last_obs')})"
                      + (f" — 규칙이 처음 걸린 관측일 {fired[0]}" if fired else ""))
        if reason and not any(x["id"] == rid and not x.get("done") for x in pend):
            pend.append({"id": rid, "reason": reason, "obs": new_st.get("last_obs"), "since": a.day,
                         "at": now_kst(), "done": None})
            print("DATA_CHECK", rid, reason)
            fired_any = True
    # v0.5 D3 심리 단서 새로 켜짐(사전 등록 6절) — 점검 열기만, 등급과 무관, 매매 규칙 아님
    fired_any |= signals_d3(a, st, sig, pend)
    # v0.6 D4 순유동성 4주간 변화 하위 20% 새로 켜짐(liquidity-1124) — 점검 열기만, 매매 규칙 아님
    try:  # D4 원자료 이상 값 하나로 signals 전체(D1~D3 기록)가 멈추지 않게
        fired_any |= signals_d4(a, sig, pend)
    except Exception as e:  # noqa: BLE001
        print("DATA_CHECK_SKIP D4 계산 실패", type(e).__name__)
    save_json(STATE, st)
    save_json(PENDING, pend)
    open_ = [x for x in pend if not x.get("done")]
    if open_ and not fired_any:
        for x in open_:
            print("DATA_CHECK_OPEN", x["id"], x["reason"], "since", x["since"])
    return 10 if open_ else 0


def signals_d3(a, st: dict, sig: dict, pend: list) -> bool:
    """심리 단서 4개를 계산해 data/psych.jsonl에 적고, 새로 켜진 단서가 있으면 D3 점검을 연다(이미 열린 D3가 있으면 줄 세움)."""
    loaded, err = psych_load()
    if loaded is None:
        print("DATA_CHECK_SKIP D3", err)
        append_jsonl(DATA / "psych.jsonl", {"day": a.day, "at": now_kst(), "ok": False, "error": err})
        return False
    try:
        rec, new_st, events = psych_eval(*loaded, sig.get("D3"))
    except Exception as e:  # noqa: BLE001
        print("DATA_CHECK_SKIP D3 심리 계산 실패", type(e).__name__)
        append_jsonl(DATA / "psych.jsonl", {"day": a.day, "at": now_kst(), "ok": False, "error": type(e).__name__})
        return False
    first = "D3" not in sig
    queue = list(new_st.get("queue", []))
    for ev in events:
        queue.append({"clue": ev["clue"], "session": ev["session"], "reason": psych_reason(rec, ev)})
    fired = False
    if queue and not any(x["id"] == "D3" and not x.get("done") for x in pend):
        reason = " / ".join(q["reason"] for q in queue)[:600]
        pend.append({"id": "D3", "reason": reason, "obs": queue[0]["session"], "since": a.day, "at": now_kst(), "done": None})
        print("DATA_CHECK", "D3", reason)
        queue, fired = [], True
    elif queue:
        print("D3 줄 세움(앞 D3 점검이 아직 열려 있음):", ", ".join(q["clue"] for q in queue))
    new_st["queue"] = queue
    sig["D3"] = new_st
    if first:
        print("D3 시작 기준 기록:", {c: v["last_ev"] for c, v in new_st["clues"].items()})
    st_line = "OK"
    miss = [k for k, v in rec["missing"].items() if v]
    if miss or not rec["s2_cadence_ok"]:
        st_line = "실패(" + ", ".join([f"{k} 못 받음" for k in miss] + ([] if rec["s2_cadence_ok"] else ["S2 공개 주기 이상 — S2 D3 멈춤"])) + ")"
    rec.update({"day": a.day, "at": now_kst(), "ok": st_line == "OK", "status": st_line, "new_events": events})
    append_jsonl(DATA / "psych.jsonl", rec)
    if not rec["s2_cadence_ok"]:
        print("DATA_CHECK_SKIP D3 S2", "CFTC 보고 주기 이상(주 1회가 아님) — S2의 D3는 멈춤, 새 정의는 사장 카드로(사전 등록 6절)")
    return fired


def signals_d4(a, sig: dict, pend: list) -> bool:
    """주간 순유동성의 4주간 변화가 156주간 굴림 하위 20%에 새로 들어가면 D4 1건(이미 열린 D4가 있으면 열지 않음)."""
    obs = {}
    for sid in LIQ_SERIES:
        p = latest_raw(f"{sid}.csv")
        if p is None:
            print("DATA_CHECK_SKIP D4 원자료 없음", sid)
            return False
        obs[sid] = parse_fred(p.read_text(encoding="utf-8"), sid)
    nl = net_liquidity_weekly(obs["WALCL"], obs["WDTGAL"], obs["RRPONTSYD"])
    if len(d4_series(nl)) < 2:
        print("DATA_CHECK_SKIP D4 이력 부족(156주간 굴림 백분위를 낼 수 없음)")
        return False
    first = "D4" not in sig
    new_st, fired = eval_d4(nl, sig.get("D4"))
    sig["D4"] = new_st
    if first:
        print("D4 시작 기준 기록:", new_st.get("last_obs"), "켜짐" if new_st.get("prev") == "on" else "꺼짐",
              f"백분위 {new_st.get('last_pct')}")
        return False
    if not fired:
        return False
    late = (dt.date.fromisoformat(a.day) - dt.date.fromisoformat(fired[0])).days
    if late > LIQ_D4["fresh_days"]:
        print("DATA_CHECK_SKIP D4 늦게 앎(수요일", fired[0], f"· {late}일 지남) — 열지 않음, 지난 주 자료를 못 받았는지 확인 필요")
        return False
    if any(x["id"] == "D4" and not x.get("done") for x in pend):
        print("D4 새로 켜졌으나 앞 D4 점검이 아직 열려 있어 열지 않음:", fired[0])
        return False
    pend.append({"id": "D4", "reason": fired[1], "obs": fired[0], "since": a.day, "at": now_kst(), "done": None})
    print("DATA_CHECK", "D4", fired[1])
    return True


def close_from_file(pend: list) -> None:
    """시나리오 점검이 남긴 닫힘 기록으로 열린 항목을 닫는다(id와 since가 같을 때만)."""
    for c in read_jsonl(CLOSED_FILE):
        if not isinstance(c, dict) or c.get("result") not in ("그대로", "바꾸자"):
            continue
        for x in pend:
            if x["id"] == c.get("id") and x["since"] == c.get("since") and not x.get("done"):
                x["done"] = {"at": str(c.get("concluded_kst", ""))[:40],
                             "reason": f"{c['result']}: {str(c.get('reason', ''))}"[:300], "by": "scenario-odds"}
                print("DATA_CHECK_CLOSED", x["id"], x["since"], c["result"])


def cmd_done(a) -> int:
    pend = load_json(PENDING, [])
    hit = False
    for x in pend:
        if x["id"] == a.id and not x.get("done"):
            x["done"] = {"at": now_kst(), "reason": a.reason[:300]}
            hit = True
    save_json(PENDING, pend)
    print("done", a.id, "OK" if hit else "없음")
    return 0 if hit else 3


def fmt(v, nd=2):
    return "—" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def psych_daily_lines(day: str) -> list[str]:
    """심리 단서 표(표시 전용 — 증거 강도 0, 매수 근거·예산·한도 상향에 쓰지 않고 매도를 막지 않는다)."""
    rows = [r for r in read_jsonl(DATA / "psych.jsonl") if r.get("day") == day]
    L = ["", "## 심리 단서 (표시 전용 · 증거 강도 0 · 매매 근거 아님 — 심리 지표 신뢰 기준 2026-11-23)", ""]
    if not rows:
        return L + ["- 심리 수집 상태: 없음(이번 실행에 signals를 못 돌림)"]
    r = rows[-1]
    if not r.get("ok", False) and "clues" not in r:
        return L + [f"- 심리 수집 상태: 실패({r.get('error')})"]
    inf = r["info"]
    L += [f"심리 수집 상태: {r['status']} · 기준 세션 {r['session']}(나스닥 종합 마지막 값 날짜)", "",
          "| 단서 | 상태 | 켜진 지 | 등급 | 값 |", "|---|---|---|---|---|"]
    for c in PSYCH_CLUES:
        cl = r["clues"][c]
        if cl["on"] is None:
            state, since, grade = "계산 불가(자료 못 받음)", "—", "—"
        elif cl["on"]:
            n = cl["n_sessions"]
            state, since = "켜짐", f"{n}세션({cl['since']}~)"
            grade = PSYCH_GRADE[c] if n <= PSYCH_H else "등급 해당 없음(60세션 지남)"
        else:
            state, since, grade = "꺼짐", "—", "—"
        if c.startswith("S1"):
            val = (f"신용 잔고 1년 변화 {inf['s1_yoy']*100:+.1f}% · 누적 백분위 {inf['s1_pct']:.2f}({inf['s1_key']} 값)"
                   if inf.get("s1_pct") is not None else "—")
        else:
            val = (f"레버리지 펀드 순포지션/미결제약정 {inf['s2_val']*100:+.1f}% · 156보고 백분위 {inf['s2_pct']:.2f}(기준일 {inf['s2_key']})"
                   if inf.get("s2_pct") is not None else "—")
        L.append(f"| {PSYCH_NAME[c]} | {state} | {since} | {grade} | {val} |")
    if r.get("new_events"):
        L += ["", "- 오늘 새로 켜짐: " + ", ".join(f"{e['clue']}({e['session']})" for e in r["new_events"]) + " → D3 점검 열기 대상"]
    return L


def _pct(v) -> str:
    return "—" if v is None else f"{v * 100:.0f}"


def liq_daily_lines(rec: dict) -> list[str]:
    """유동성·신용 표(v0.6) — 표시 전용, 해석 문장 없음. 금액 줄(백만$)은 bp 표와 따로."""
    L = ["", "## 유동성·신용 (v0.6 · 표시 전용 · 증거 강도 0 · 매매 근거 아님 — 백분위는 3년 창, 갈래 판정에 안 씀)", ""]
    liq = rec.get("liq") or {}
    if not liq or "error" in liq:
        return L + [f"- 유동성 계산 상태: 실패({liq.get('error', '이번 실행 기록 없음')})"]
    L += ["| 지표 | 날짜 | 값 | 3년 백분위 | 5관측 변화 (백분위) | 20관측 변화 (백분위) |", "|---|---|---|---|---|---|"]

    def row(name, b, unit_val, unit_chg, mult):
        if not b or not b.get("ok"):
            L.append(f"| {name} | — | 계산 불가(자료 못 받음) | — | — | — |")
            return
        def c(x):
            return "—" if not x else f"{x['chg'] * mult:+,.0f}{unit_chg} ({_pct(x['pct'])})"
        L.append(f"| {name} | {b['date']} | {unit_val(b['value'])} | {_pct(b['pct3y'])} | {c(b.get('c5'))} | {c(b.get('c20'))} |")

    hy = liq.get("hy") or {}
    hy_name = f"HY 스프레드 — 3년 창({(hy.get('win_first') or '')[:7]}~) 한정" if hy.get("ok") else "HY 스프레드"
    row(hy_name, hy, lambda v: f"{v:.2f}%", "bp", 100)
    row("재무부 현금 TGA(일일, 백만$)", liq.get("tga"), lambda v: f"{v:,.0f}", "", 1)
    row("순유동성 주간(판정용, 수요일 수준, 백만$)", liq.get("nl_w"), lambda v: f"{v:,.0f} (≈{v / 1e6:.2f}조$)", "", 1)
    nd = liq.get("nl_d")
    if nd:
        L.append(f"| 순유동성 일간(표시용, 판정에 안 씀, 백만$) | {nd['date']} | {nd['value']:,.0f} (≈{nd['value'] / 1e6:.2f}조$) · 연준 총자산 {nd['walcl_date']} 값 | — | — | — |")
    d4 = liq.get("d4")
    if d4:
        L += ["", f"- D4 기준(점검 열기용, 매매 규칙 아님): 순유동성 4주간 변화 {d4['chg_rate'] * 100:+.1f}% (수요일 {d4['date']}) · "
                  f"156주간 굴림 백분위 {_pct(d4['pct'])} · {'하위 20% 안(켜짐)' if d4['on'] else '하위 20% 밖(꺼짐)'} — 새로 들어갈 때만 D4가 열림"]
    L.append("- 순유동성 = 연준 총자산(WALCL) − TGA(WDTGAL, 수요일 수준) − 역레포(RRPONTSYD×1000). 발표: 연준 H.4.1 목요일 16:30 ET(연방 공휴일이면 다음 영업일) → 다음 KST 실행부터 반영")
    return L


def cmd_daily(a) -> int:
    rec = latest_numbers() or {}
    hist = read_jsonl(DATA / "numbers.jsonl")
    def last_good(kind, key):
        for r in reversed(hist):
            v = (r.get(kind) or {}).get(key) if kind != "tga" else r.get("tga")
            if v and (kind == "tga" or (v.get("ok") if kind == "fred" else True)):
                return v
        return None
    st = load_json(STATE, {})
    pend = [x for x in load_json(PENDING, []) if not x.get("done")]
    fv = [r for r in read_jsonl(DATA / "finviz.jsonl") if r.get("day") == a.day]
    xs = [r for r in read_jsonl(DATA / "x.jsonl") if r.get("day") == a.day]
    bl = [r for r in read_jsonl(DATA / "breadth.jsonl") if r.get("day") == a.day]
    L = [f"# 외부 정보 수집 {a.day} ({VERSION})", "",
         "상태: " + " · ".join(f"{k} {v}" for k, v in (rec.get("status") or {}).items())
         + (f" · X 이번 실행 못 읽음 (연속 실패 {st.get('x', {}).get('fail_streak', 0)})" if st.get('x', {}).get('fail_streak', 0)
            else f" · X OK{'' if xs else ' (오늘 새 글 없음)'}")
         + f" · finviz {'OK' if fv else '없음'}"
         + f" · 시장 폭 {'OK' if bl else '새 기록 없음'}"
         + (f" · **시장 폭 {st['breadth']['streak']}일 연속 못 받음**" if (st.get("breadth") or {}).get("streak", 0) >= 2 else "")
         + "".join(f" · **{k} {n}회 연속 STALE**" for k, n in (st.get("stale_streak") or {}).items() if n >= 2)
         + (f" · **finviz {st['finviz']['streak']}일 연속 STALE**" if (st.get("finviz") or {}).get("streak", 0) >= 2 else "")
         + ((f" · 명단 대조 {st['roster'].get('last_status')} {st['roster'].get('last_day')}"
             + (f" (**{st['roster']['skip_streak']}주 연속 넘어감**)" if st['roster'].get('skip_streak', 0) >= 2 else "")) if st.get("roster") else " · 명단 대조 기록 없음"), "",
         "권한: CONTEXT_ONLY — 숫자는 공식 원자료, 글은 가설. 매매 판정에 쓰지 않는다.", ""]
    L += ["## 데이터 점검", ""]
    L += [f"- **열림 {x['id']}**: {x['reason']} (since {x['since']}) → 회사 전략 점검 대상" for x in pend] or ["- 열린 점검 없음"]
    L += ["", "## 공식 숫자 (자료마다 마지막으로 받은 값 — 날짜 칸이 오래됐으면 STALE)", "", "| 자료 | 날짜 | 값 | 183일 저점 대비 | 5관측 | 21관측 | 1년 범위 |", "|---|---|---|---|---|---|---|"]
    for sid, name in FRED_SERIES.items():
        s = last_good("fred", sid) or {}
        if s.get("ok"):
            unit = "bp" if sid != "NFCI" else "×0.01"
            L.append(f"| {name} | {s['date']} | {s['value']} | +{s['above_low_bp']}{unit} | {fmt(s['chg5'])} | {fmt(s['chg21'])} | {s['yr_min']}~{s['yr_max']} |")
    for key in CFTC_MARKETS:
        rows = last_good("cftc", key)
        if rows:
            seq = " → ".join(f"{r['date'][5:]} {r['lev_net']:+,}" for r in rows)
            L.append(f"| CFTC {key} 레버리지 펀드 순포지션(계약) | {rows[-1]['date']} | {rows[-1]['lev_net']:+,} | — | {seq} | 자산운용사 {rows[-1]['am_net']:+,} | — |")
    if last_good("tga", None):
        t = last_good("tga", None)[-1]
        L.append(f"| 재무부 현금 TGA(백만$) | {t['date']} | {t['musd']:,.0f} | — | — | — | — |")
    L += liq_daily_lines(rec)
    L += psych_daily_lines(a.day)
    L += ["", "## 시장 폭 (finviz 첫 화면 · NYSE·Nasdaq·AMEX 합계 · 표시 전용 · 근거 강도 0 — 판정·알림에 쓰지 않음, 문턱 사전 등록 전 값은 보고 전용)", ""]
    if bl:
        b = bl[-1]
        L.append(f"- 미국 {b['session']} 세션({b['at']} 읽음): 상승 {b['adv']:,} · 하락 {b['dec']:,} · 52주 신고가 {b['nh']:,} · 신저가 {b['nl']:,}"
                 f" · 50일선 위 {b['sma50_pct']}% · 200일선 위 {b['sma200_pct']}%"
                 + (" · 직전 세션과 6칸 모두 같음(휴장일 또는 갱신 안 됨 — 확인 필요)" if b.get("repeat") else "")
                 + (" · 06:20 값이 마감 확정치인지 확인 전(H1-3)" if b.get("h13") != "통과" else ""))
    else:
        last = (read_jsonl(DATA / "breadth.jsonl") or [None])[-1]
        L.append("- 이번 실행에 새 세션 없음" + (f"(마지막 기록 미국 {last['session']} 세션)" if last else "(기록 없음)"))
    L += ["", "## X (사장 Chrome, 읽기만)", ""]
    if xs:
        L += ["| 계정 | 글 | 요지 | 분류 | 소비자 |", "|---|---|---|---|---|"]
        for r in xs:
            L.append(f"| @{r['account']} | [{r['id']}]({r['url']}) | {(r.get('summary') or r['text'][:160]).replace('|', '/')} | {r['class']} | {r.get('consumer', '')} |")
    else:
        L.append("- 새 글 없음 또는 Chrome 연결 안 됨")
    L += ["", "## finviz (보유·관심 종목, 참고 — 가격 = 키움, 재무 = SEC)", ""]
    if fv:
        last = fv[-1]
        cols = ("Forward P/E", "Target Price", "Recom", "Short Float", "Insider Trans", "RSI (14)", "Perf Week", "Perf Month", "Earnings")
        L += ["| 종목 | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 1)]
        for t, row in last["rows"].items():
            L.append(f"| {t} | " + " | ".join(row.get(c, "—") for c in cols) + " |")
        for t, row in (last.get("bench") or {}).items():
            L.append(f"| {t} (기준 지수) | " + " | ".join(row.get(c, "—") for c in cols) + " |")
        L += ["", "Perf Month = finviz 정의(최근 한 달 가격 변화). 종목 고르기 실력 점수(pick-vs-qqq)와 별개의 참고 표시이고 그 점수에 넣지 않는다.", ""]
        prior = [r for r in read_jsonl(DATA / "finviz.jsonl") if r.get("day", "") < a.day]
        el = earn_lines(prior, last["rows"], a.day)
        if el:
            L += ["실적일 알림(finviz 칸 기준 · 표시 전용 · 지난 날짜를 다음 날짜가 정해질 때까지 보여 주므로 날짜 확인은 EDGAR 8-K·IR):", ""] + el
    else:
        L.append("- 이번 실행에 없음")
    # v0.7: 06:20 실행이 통째로 빠졌거나 월요일 대조 기록이 없으면 daily(19:20도 돎)에서 하루 한 번 알린다
    al = st.setdefault("alerts", {})
    day_d = dt.date.fromisoformat(a.day)
    ro = st.get("roster") or {}
    msgs = []
    if not fv:
        msgs.append(("FINVIZ_MISSING", f"{a.day} finviz 기록 없음"))
    if (day_d.weekday() == 0 and ro.get("last_day") != a.day) or (ro.get("last_day") and (day_d - dt.date.fromisoformat(ro["last_day"])).days > 7):
        msgs.append(("ROSTER_NOT_RECORDED", f"{a.day} 월요일 명단 대조 기록 없음(마지막 {ro.get('last_day', '없음')} {ro.get('last_status', '')})"))
    for key, text in msgs:
        if al.get(key) != a.day:
            print(key, text)
            al[key] = a.day
    if msgs:
        save_json(STATE, st)
    DAILY.mkdir(parents=True, exist_ok=True)
    (DAILY / f"{a.day}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("daily", a.day, "OK")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("numbers", "finviz", "x-add", "signals", "daily"):
        p = sub.add_parser(name)
        p.add_argument("--day", required=True)
        if name in ("numbers", "finviz"):
            p.add_argument("--offline")
        if name == "finviz":
            p.add_argument("--tickers")
            p.add_argument("--tickers-file")
        if name == "x-add":
            p.add_argument("--file", required=True)
    p = sub.add_parser("roster")
    p.add_argument("--day", required=True)
    p.add_argument("--status", required=True, choices=["checked", "changed", "skipped"])
    sub.add_parser("x-seen")
    p = sub.add_parser("usage")
    p.add_argument("--since", required=True)
    p = sub.add_parser("done")
    p.add_argument("--id", required=True, choices=sorted(list(RULES) + ["D3", "D4"]))
    p.add_argument("--reason", required=True)
    sub.add_parser("rules")
    a = ap.parse_args(argv)
    if a.cmd == "rules":
        print(RULES_TEXT)
        return 0
    if hasattr(a, "day"):
        if a.day == "today":  # 예약 실행의 시계는 UTC — 날짜는 도구가 KST로 정한다
            a.day = today_kst()
        dt.date.fromisoformat(a.day)
    return {"numbers": cmd_numbers, "finviz": cmd_finviz, "x-add": cmd_x_add, "signals": cmd_signals,
            "done": cmd_done, "daily": cmd_daily, "x-seen": cmd_x_seen, "usage": cmd_usage, "roster": cmd_roster}[a.cmd](a)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        print("ERROR", type(e).__name__, str(e)[:200])
        sys.exit(3)
