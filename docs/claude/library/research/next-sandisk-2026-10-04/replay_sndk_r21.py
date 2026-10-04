#!/usr/bin/env python3
"""SNDK R2.1 리플레이 — Next 샌디스크 설계 3절·16절 재현용 (D급 근사).

사용법: 이 파일과 같은 폴더에 sndk.csv, soxx.csv를 두고 `python3 replay_sndk_r21.py`.
- 데이터: Yahoo 일봉(참고값, 키움 미대조). 키움 일봉으로 다시 계산하기 전까지 D급.
- 가정은 아래 상수에 모았다. 바꾸면 결과도 바뀐다(설계 문서 16절 가정과 같게 둘 것).
- 읽기 전용 계산. 파일을 쓰지 않는다. 매매 근거 아님.
"""
import csv
import datetime as T
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ── 가정 (설계 3절·16절) ─────────────────────────────────────────────
EARN = ["2025-05-07", "2025-08-14", "2025-11-06", "2026-01-29", "2026-04-30", "2026-08-05"]  # 장 마감 뒤 발표일
# S1(공식 테제)은 관대하게: FQ4 FY25 1점, FQ1 FY26부터 2점. S2(실적 가속)는 공식 실적 수치로 판정.
S1 = {"2025-05-07": 0, "2025-08-14": 1, "2025-11-06": 2, "2026-01-29": 2, "2026-04-30": 2, "2026-08-05": 2}
S2 = {"2025-05-07": 1, "2025-08-14": 2, "2025-11-06": 2, "2026-01-29": 2, "2026-04-30": 2, "2026-08-05": 2}
WEAKEST_MEMBER = 8          # 10/3 관심 5종목 점수 10·10·9·9·8 중 최저(고정 가정)
COMPETITORS = (9, 10)       # 명단 밖 최고 후보 점수(10/3 ETN 9) + 10점인 경우
IGNITION = "2025-08-14"     # N-렌즈 점화일(설계 3-2)
SEED_MIN = 6                # 씨앗 칸 진입 최소 점수
PROTECT_MAX_WEEKS = 13      # 유지 보호 상한(다음 실적 반응 재측정까지, 최대 13주)


def load():
    sn = [(r["date"], float(r["close"])) for r in csv.DictReader(open(os.path.join(HERE, "sndk.csv")))]
    sx = {r["date"]: float(r["close"]) for r in csv.DictReader(open(os.path.join(HERE, "soxx.csv")))}
    return [d for d, _ in sn], [c for _, c in sn], sx


DATES, CL, SX = load()
SXD = sorted(SX)
EMA = []
for _i, _c in enumerate(CL):
    EMA.append(_c if _i == 0 else _c * (2 / 51) + EMA[-1] * (1 - 2 / 51))   # EMA50
PEAK = max(CL)


def score(i):
    """R2.1 = S1 + S2 + S3(60세션 vs SOXX, 252세션 고점×0.85) + S4(사이클 업종 0) + S5(EMA50) + S7(실적 후 10세션)."""
    d = DATES[i]
    e = [x for x in EARN if x <= d][-1]
    j = DATES.index(e)
    k = SXD.index(d)
    s3a = int(i >= 60 and k >= 60 and CL[i] / CL[i - 60] - 1 > SX[d] / SX[SXD[k - 60]] - 1)
    s3b = int(CL[i] >= 0.85 * max(CL[max(0, i - 251): i + 1]))
    s5 = int(CL[i] > EMA[i])
    r = CL[min(j + 10, i)] / CL[j] - 1        # P0 = 발표일 종가(장후 발표), 10세션 전이면 최신 종가로 잠정
    s7 = 2 if r >= 0.05 else (1 if r >= 0 else 0)
    return dict(d=d, c=CL[i], S1=S1[e], S2=S2[e], S3=s3a + s3b, S5=s5, S7=s7,
                tot=S1[e] + S2[e] + s3a + s3b + s5 + s7)


def weekly(start):
    """주간 평가 = 그 주 마지막 거래일 종가(토요일 평가)."""
    out = []
    for i, d in enumerate(DATES):
        nxt = DATES[i + 1] if i + 1 < len(DATES) else None
        last_of_week = nxt is None or T.date.fromisoformat(nxt).isocalendar()[1] != T.date.fromisoformat(d).isocalendar()[1]
        if last_of_week and d >= start:
            out.append(score(i))
    return out


def next_earn_plus10(d):
    nx = [e for e in EARN if e > d]
    if not nx:
        return None
    j = DATES.index(nx[0])
    return DATES[min(j + 10, len(DATES) - 1)]


def retention(weeks, entered, comp, mode):
    """mode: none(현행) / 8w(8주 보호) / s7(다음 실적 반응 재측정까지, 최대 13주)."""
    base = entered["S1"] + entered["S2"]
    streak, until, used = 0, None, 0
    for w in weeks:
        if w["d"] <= entered["d"]:
            continue
        cond = comp >= w["tot"] + 2          # 교체 규칙 ③: 후보 ≥ 가장 약한 관심 + 2
        streak = streak + 1 if cond else 0
        if not cond:
            until = None
            continue
        tenure = (T.date.fromisoformat(w["d"]) - T.date.fromisoformat(entered["d"])).days
        if streak < 2 or tenure < 28:
            continue
        if mode != "none" and w["S1"] + w["S2"] >= base:
            if until is None:
                start = T.date.fromisoformat(w["d"])
                cap = (start + T.timedelta(weeks=8 if mode == "8w" else PROTECT_MAX_WEEKS)).isoformat()
                until = cap if mode == "8w" else min(cap, next_earn_plus10(w["d"]) or cap)
            if w["d"] < until:
                used += 1
                continue
        after = max(CL[DATES.index(w["d"]):])
        return f"밀려남 {w['d']} 종가 ${w['c']:,.0f}(점수 {w['tot']}), 그 뒤 최고가까지 {after / w['c']:.1f}배 / 보호 {used}주"
    return f"끝까지 유지 / 보호 {used}주"


def main():
    wk = weekly("2025-08-15")
    print("== 3-1 포착 (주간 평가) ==")
    for w in wk[:4]:
        print(f"{w['d']} ${w['c']:.2f} R2.1={w['tot']} (S1 {w['S1']} S2 {w['S2']} S3 {w['S3']} S5 {w['S5']} S7 {w['S7']}) "
              f"이후 고점까지 {PEAK / w['c']:.1f}배")
    print("최고 점수:", max(w["tot"] for w in wk), "| 점수 분포:", {s: sum(1 for w in wk if w["tot"] == s) for s in range(4, 11)})
    print("7점 이하 주:", [(w["d"], w["tot"]) for w in wk if w["tot"] <= 7])

    print("\n== 16-1 진입 ==")
    def first_two(cond):
        for a, b in zip(wk, wk[1:]):
            if a["d"] >= IGNITION and cond(a) and cond(b):
                return b
    e0 = first_two(lambda w: w["tot"] >= WEAKEST_MEMBER + 2)
    e2 = first_two(lambda w: w["tot"] >= WEAKEST_MEMBER + 1)
    e1 = next(w for w in wk if w["d"] >= IGNITION and w["tot"] >= SEED_MIN)
    for name, w in (("현행(최약 + 2, 2주 연속)", e0), ("점화 씨앗만 문턱 +1", e2), ("씨앗 전용 칸(점화 + 6점 이상)", e1)):
        print(f"{name}: " + (f"{w['d']} ${w['c']:.2f}, 이후 고점까지 {PEAK / w['c']:.1f}배" if w else "못 들어옴"))

    print("\n== 16-2 유지 (씨앗 칸 진입일부터 관심 종목으로 가정) ==")
    wk2 = weekly(e1["d"])
    for comp in COMPETITORS:
        for mode, name in (("none", "현행"), ("8w", "8주 보호"), ("s7", "다음 실적 재측정까지·최대 13주")):
            print(f"경쟁 후보 {comp}점 · {name}: {retention(wk2, wk2[0], comp, mode)}")


if __name__ == "__main__":
    main()
