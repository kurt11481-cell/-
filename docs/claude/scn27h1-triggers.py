# SCN-27H1 트리거 갱신 (docs/claude/market-scenario-27h1-2026-10-09.md 3절) — 읽기 전용, FRED 공개 자료만, 파일을 만들지 않는다.
# 실행: 클라우드 컨테이너에서 python3 -I scn27h1-triggers.py (사용자 PC에서는 FRED 접속이 막힘). 출력 첫 줄을 결론·보고에 1줄로 쓴다.
import csv, io, subprocess, datetime as dt
TODAY = dt.date.today()
def fred(sid, days):
    start = (TODAY - dt.timedelta(days=days)).isoformat()
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start}"
    try:
        out = subprocess.run(["curl", "-sSL", "-m", "40", url], capture_output=True, text=True, timeout=70).stdout
    except Exception:
        return []
    rows = []
    for r in list(csv.reader(io.StringIO(out)))[1:]:
        try: rows.append((r[0], float(r[1])))
        except Exception: pass
    return rows
def stale(rows, days):
    return (not rows) or (TODAY - dt.date.fromisoformat(rows[-1][0])).days > days
def st(fire, near):
    return "발동" if fire else ("근접" if near else "정상")
res = {}
# T1 금리: 10년물 종가 >= 3년 저점 + 200bp (근접 +150bp)
y = fred("DGS10", 1096)
if stale(y, 7): res["T1"] = ("미확인", "DGS10 없음/오래됨")
else:
    low = min(y, key=lambda x: x[1]); last = y[-1]; rise = round((last[1] - low[1]) * 100)
    res["T1"] = (st(last[1] >= low[1] + 2.0, last[1] >= low[1] + 1.5),
                 f"10년물 {last[1]:.2f}% ({last[0]}) · 3년 저점 {low[1]:.2f}% ({low[0]}) 대비 +{rise}bp · 발동선 {low[1]+2:.2f}%")
# T2 연준: 마지막 인하(2025-12-11 반영) 뒤 인상 누적 >= 6회 (근접 >= 4회)
f = fred("DFEDTARU", (TODAY - dt.date(2025, 12, 1)).days)
if stale(f, 7): res["T2"] = ("미확인", "DFEDTARU 없음/오래됨")
else:
    hikes = sum(1 for i in range(1, len(f)) if f[i][0] >= "2025-12-12" and f[i][1] > f[i-1][1])
    res["T2"] = (st(hikes >= 6, hikes >= 4), f"마지막 인하 뒤 인상 {hikes}회 · 목표 상단 {f[-1][1]:.2f}% ({f[-1][0]}) · 발동 6회")
# T3 신용: BBB OAS >= 6개월 저점 + 30bp 이고 S&P 500이 52주 고점 -5% 안 (근접: BBB +20bp 또는 HY +30bp)
b = fred("BAMLC0A4CBBB", 400); h = fred("BAMLH0A0HYM2", 400); sp = fred("SP500", 500)
if stale(b, 7) or stale(sp, 7): res["T3"] = ("미확인", "BBB OAS 또는 SP500 없음/오래됨")
else:
    bl = min(b[-126:], key=lambda x: x[1]); br = round((b[-1][1] - bl[1]) * 100)
    hi = max(sp[-252:], key=lambda x: x[1]); dd = 100 * (sp[-1][1] / hi[1] - 1)
    hr = None; th = "HY 미확인"
    if not stale(h, 7):
        hl = min(h[-126:], key=lambda x: x[1]); hr = round((h[-1][1] - hl[1]) * 100)
        th = f"HY {h[-1][1]:.2f}% (6개월 저점 {hl[1]:.2f}% {hl[0]} 대비 +{hr}bp)"
    res["T3"] = (st(br >= 30 and dd >= -5, br >= 20 or (hr is not None and hr >= 30)),
                 f"BBB {b[-1][1]:.2f}% (6개월 저점 {bl[1]:.2f}% {bl[0]} 대비 +{br}bp, 발동 +30bp) · {th} · S&P 500 52주 고점 대비 {dd:.1f}%")
# T4 유가·물가: WTI 5거래일 연속 >= $100 그리고 CPI 전년비 2개월 연속 상승 (근접: WTI >= $95 또는 최근 20거래일 중 $100 이상)
w = fred("DCOILWTICO", 60); c = fred("CPIAUCSL", 500)
if stale(w, 10): res["T4"] = ("미확인", "WTI 없음/오래됨")
else:
    five = len(w) >= 5 and all(v >= 100 for _, v in w[-5:])
    yoy = [(c[-k][0], 100 * (c[-k][1] / c[-k-12][1] - 1)) for k in (3, 2, 1)] if len(c) >= 15 else []
    up2 = len(yoy) == 3 and yoy[2][1] > yoy[1][1] > yoy[0][1]
    near = w[-1][1] >= 95 or any(v >= 100 for _, v in w[-20:])
    s4 = "미확인" if (five and not yoy) else st(five and up2, near)
    ct = " → ".join(f"{d[:7]} {v:.2f}%" for d, v in yoy) if yoy else "CPI 미확인"
    res["T4"] = (s4, f"WTI ${w[-1][1]:.2f} ({w[-1][0]}) · 최근 20거래일 중 $100 이상 {sum(1 for _, v in w[-20:] if v >= 100)}일 · CPI 전년비 {ct}")
# T5 이익: 수동 (FactSet Earnings Insight)
res["T5"] = ("수동", "FactSet Earnings Insight 최신호에서 forward 12M EPS 분기 변화·CY27 성장률 확인")
# T6 4분기 반등 전제: S&P 500 종가 < 7,500 (근접 < 7,650)
if stale(sp, 7): res["T6"] = ("미확인", "SP500 없음/오래됨")
else:
    v = [x for _, x in sp]
    res["T6"] = (st(sp[-1][1] < 7500, sp[-1][1] < 7650), f"S&P 500 {sp[-1][1]:,.2f} ({sp[-1][0]}) · 100일선 {sum(v[-100:])/100:,.0f} · 발동 7,500 미만 (FRED 참고값)")
fires = [k for k, x in res.items() if x[0] == "발동"]
warn = [k for k, x in res.items() if x[0] in ("근접", "미확인")]
status = "🔴 재검토" if fires else ("🟠 주의" if warn else "🟢 정상")
print(f"시나리오 SCN-27H1: {status} ({TODAY} 갱신 · 발동 {','.join(fires) or '없음'} · 근접/미확인 {','.join(warn) or '없음'})")
for k in ("T1", "T2", "T3", "T4", "T5", "T6"):
    print(f"  {k} [{res[k][0]}] {res[k][1]}")
print("  표시 전용 — 근거 강도 0 · 예산·상한·게이트·권한 불변 · 자동 매매 없음 · 출처 FRED(fred.stlouisfed.org)")
