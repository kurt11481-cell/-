# 손실한도·전략 전면 재검토 — S3 급락 탈출·회복 재진입 신호 아이디어 (2026-09-30)

- 성격: 전략 아이디어 조사 + 간이 과거 재현(D등급: 가상 계산, in-sample, 검증 아님). 정책·상태 파일 수정 없음. `order_authority=false`, `quantity_authority=none`.
- 사용자 요청: "시장 급락은 곧 매수 찬스이고 자산 증식의 최대 기회. 급락 시그널이 나오자마자 급락 초기에 매도해 현금 보유, 회복 시그널이 나오자마자 회복 초기에 매수할 수 있는 아이디어 찾기."
- 선행 문서: `loss-limit-review-s0-dollar-comparison-2026-09-30.md`, `loss-limit-review-s1-decisions-2026-09-30.md`

## 0. 결론

1. "급락 초기 매도 → 회복 초기 매수"를 그대로 기계화한 규칙(②)은 급락마다 빨리 나가고(고점 대비 -8~-10.5%) 비교적 빨리 들어왔지만(바닥 대비 +8~+21%), 15.7년간 탈출이 57번(진짜 25%+ 급락은 6번)이라 가짜 신호 비용이 커서 연수익이 보유의 절반(20.2% vs 39.9%)이었다.
2. 가장 균형이 좋았던 것은 변동성 비중조절(①): 변동성이 커지면 비중을 줄이고 잦아들면 되돌린다. 연수익은 보유와 비슷(39.5%)하면서 하루 -10% 이상 손실일이 156일 → 54일, 최악의 하루 -38.6% → -21.3%.
3. 반등 자체는 컸다(바닥 후 60거래일 보유 +52~+204%). 문제는 바닥을 실시간으로 알 수 없다는 것: SOXX 상위 20개 상승일 중 11개가 최악의 20일 전후 10거래일 안에 있었다.
4. 어떤 신호도 손실선(1차 -10%, 최대 -20%)을 대신하지 못했다(1.9배 상한 기준 최대 낙폭 -56~-78%). 신호는 "먼저 줄이는 장치", 손실선은 "최종 안전장치"로 함께 써야 한다.
5. 결정 2 보완: 장기 데이터의 최악의 날은 2020-03-16(SOXX -15.2%, SOXL -38.6%)이다. 1.9배(SOXL 63.3%)면 그날 하루 -24.4%로 최대 선(-20%)을 하루 만에 넘는다. SOXX×1.9 가상 계산으로는 -28.9%, 2020-03-12(-20.9%)까지 2일. 이 기간 하루 만에 최대 선을 넘지 않는 경계는 SOXL 기준 약 1.55배(SOXL 51.8%), SOXX 가상 기준 약 1.3배다.

## 1. 외부 근거 (아이디어 출처)

| 계열 | 급락 신호 | 회복 신호 | 근거 | 우리 데이터로 구현 |
|---|---|---|---|---|
| 추세 필터 | 지수 종가 < 이동평균 | 종가 > 이동평균 | Gayed & Bilello(2016) "Leverage for the Long Run": S&P 500 종가가 이동평균(10~200일 검토) 위면 주식(레버리지 가능), 아래면 T-bill. 1928-10~2015-10. 구체 수치는 원문 확인 필요(원문 PDF 조회 차단) | 가능(키움 가격) |
| 변동성 비중조절 | 최근 변동성 ↑ → 비중 ↓ | 변동성 ↓ → 비중 ↑ | Moreira & Muir(2017, Journal of Finance) "Volatility-Managed Portfolios": 변동성이 높을 때 위험을 줄이는 포트폴리오가 큰 알파·샤프 개선 | 가능 |
| 팔로스루 데이(FTD) | — | 반등 시도 4일째 이후 지수 +1~1.25% 이상, 거래량 전일 대비 증가 | IBD(William O'Neil). 기준 상승률은 "움직이는 목표" | 가능(ETF 거래량으로 대리) |
| 브레드스 스러스트 | — | NYSE 상승종목 비율 10일 EMA가 0.40 미만 → 10일 안에 0.615 초과 | Zweig Breadth Thrust | 데이터 출처 확인 필요(NYSE 등락 종목 수) |
| 90% 데이 | 90% 하락일(하락 거래량·하락 포인트 각 90% 이상) 2회 이상 | 90% 상승일(또는 드물게 80% 상승일 연속 2일) | Paul Desmond(2002, NYSE 1933~2002) | 데이터 출처 확인 필요(NYSE 상승·하락 거래량) |
| VIX 기간구조 | VIX/VIX3M > 1(역전, 스트레스) | < 1 | 실무 지표. 2010년 이후 역전은 거래일의 약 7.6%(출처 페이지 기준, 확인 필요) | 외부 데이터(참고용) |

## 2. 간이 과거 재현 (D등급)

- 데이터: Yahoo(yfinance) 조정 OHLCV 2010-01-04~2026-09-29(9/30 장중 봉 제외). 저장소 Nasdaq 기반 로컬 데이터와 4개 날짜 상대가격 비율 1.0000 일치. 외부 가격이므로 참고용.
- 평가 구간: 2011-01-03~2026-09-29(15.7년). 신호는 SOXX 종가로 판단 → 다음 날 시가에 SOXL 매매(밤사이 갭 포함). 수수료 체결당 10bp. 현금 이자·세금 제외.
- 파라미터는 실행 전에 관례값으로 정했고 이 데이터로 조정하지 않았다.

### 2-1. 전체 성과 (SOXX 신호 → SOXL)

| 규칙 | 급락 신호 | 회복 신호 | 연수익 | 최대 낙폭 | 최악의 하루 | 하루 -10% 이하 | 평균 노출 | 연간 진입 |
|---|---|---|---|---|---|---|---|---|
| 보유(비교) | — | — | 39.9% | -90.5% | -38.6% | 156일 | 100% | — |
| ① 변동성 비중조절(VOL) | SOXL 20일 변동성 ↑ | 변동성 ↓ | 39.5% | -77.0% | -21.3% | 54일 | 81.9% | 연속 조절 |
| ② 급락 탈출 + FTD 재진입 | 하루 -4% 또는 20일 고점 대비 -10% | 반등 4일째 이후 +2% & 거래량 증가 | 20.2% | -82.2% | -30.5% | 69일 | 68.4% | 3.7 |
| ③ 200일선 | 종가 < 200일선 | 종가 > 200일선 | 29.9% | -83.9% | -30.5% | 100일 | 77.5% | 3.4 |
| ④ 50일선 | 종가 < 50일선 | 종가 > 50일선 | 19.8% | -75.1% | -30.5% | 75일 | 66.6% | 8.9 |
| ⑤ EMA10/20 | EMA10 < EMA20 | EMA10 > EMA20 | 21.4% | -76.8% | -30.5% | 75일 | 65.4% | 5.4 |
| ⑥ VIX 기간구조 | VIX/VIX3M > 1 | ≤ 1 | 28.7% | -92.8% | -30.5% | 117일 | 92.4% | 6.0 |

1.9배 상한 준수형(들어갈 때 SOXL 63.3% + 현금, 매일 비중 유지 가정):

| 규칙 | 연수익 | 최대 낙폭 | 최악의 하루 | 하루 -10% 이하 | 하루 -20% 이하 |
|---|---|---|---|---|---|
| 보유 | 36.2% | -73.6% | -25.2% | 39일 | 1일 |
| ① 변동성 비중조절 | 29.7% | -58.1% | -13.7% | 9일 | 0일 |
| ② 급락 탈출 + FTD | 17.8% | -64.5% | -19.9% | 13일 | 0일 |
| ③ 200일선 | 25.4% | -66.5% | -19.9% | 23일 | 0일 |
| ⑤ EMA10/20 | 18.6% | -58.6% | -19.9% | 14일 | 0일 |

참고(같은 규칙, QQQ 신호 → TQQQ, 100% 노출): 보유 40.6%/-81.7%, ① 37.6%/-57.3%, ③ 28.7%/-60.1%, ② 23.7%/-72.8%, ⑥ 31.1%/-87.6%. 순위 경향은 같다.

### 2-2. 급락 구간별 (SOXX 고점 대비 -25% 이상 6회, 100% 노출)

하락 구간 손익 / 바닥 후 60거래일 손익:

| 구간 | 보유 | ① 변동성 | ② 급락+FTD | ③ 200일선 | ⑤ EMA10/20 | ⑥ VIX |
|---|---|---|---|---|---|---|
| 2011-02~08 (-30.5%) | -71 / +52 | -65 / +26 | -51 / -5 | -48 / 0 | -48 / -11 | -45 / -21 |
| 2018-03~12 (-25.3%) | -67 / +109 | -56 / +55 | -46 / +62 | -38 / +25 | -56 / +55 | -61 / +69 |
| 2020-02~03 (-34.3%) | -80 / +183 | -45 / +45 | -39 / +17 | -63 / +11 | -31 / +50 | -22 / +55 |
| 2021-12~2022-10 (-45.8%) | -90 / +80 | -67 / +45 | -61 / +48 | -68 / -10 | -61 / +9 | -93 / +66 |
| 2024-07~2025-04 (-41.4%) | -88 / +204 | -77 / +89 | -82 / +126 | -83 / +24 | -76 / +94 | -85 / +106 |
| 2026-06~07 (-29.0%) | -69 / +60 | -32 / +34 | -23 / +4 | -69 / +60 | -34 / -15 | -69 / +60 |

- ② 첫 탈출(신호일 종가 기준): 6번 모두 고점 대비 -7.9~-10.5%. 바닥 후 첫 재진입: +7.6~+20.9%. ③ 200일선은 탈출 -9.8~-22.1%, 재진입 +19.1~+38.0%, 2026-06 급락은 탈출하지 못함.
- 하락 구간 안의 헛재진입(가짜 회복 신호): ② 15회, ③ 19회, ⑤ 18회, ⑥ 29회. 긴 하락장(2022, 2024~25)에서 효과 대부분을 잃은 이유.
- 전체 탈출 횟수: ② 57회, ③ 52회, ⑤ 84회, ⑥ 94회(15.7년, 진짜 급락 6회).
- 상위 20개 상승일 보유 여부: ② 5/20, ③ 10/20, ④ 7/20, ⑤ 8/20, ⑥ 11/20. 상위 20개 하락일 보유 여부: ② 10/20, ③ 11/20, ⑤ 8/20. 첫 급락일은 신호 자체라 피하기 어렵다.
- 최고의 날: 2025-04-09 +18.6%(최악 중 하나인 2025-04-03 -10.1%의 4거래일 뒤), 2020-03-13 +10.7%(2020-03-12 -11.0% 다음 날).

## 3. 해석

- 사용자 전제("급락 후 반등이 최대 기회")는 데이터와 맞다. 바닥 후 60거래일 보유 수익이 +52~+204%였다.
- 그러나 바닥은 실시간으로 확인되지 않는다. 회복 신호는 항상 바닥보다 늦고(② +8~+21%), 그 사이 가장 큰 상승일이 지나간다.
- 긴 하락장은 "가짜 회복 신호"를 여러 번 만든다. 재진입 규칙이 빠를수록 헛재진입이 늘어난다(빠른 재진입과 헛재진입은 같은 동전의 양면).
- 3배 레버리지는 하락 구간의 반복 손실을 키운다. ①처럼 전부 팔지 않고 비중을 줄이는 방식이 이 약점을 가장 덜 탔다.
- 한계: in-sample, 2011~2026은 반도체 강세장(SOXX 연 25.6%)이라 보유에 유리한 구간. 약세·횡보 10년이면 신호 규칙이 상대적으로 나아질 수 있다. 현금 이자를 넣으면 신호 규칙이 조금 유리해진다. 매매가 잦으면 양도세가 매년 실현된다. 모든 수치는 확인·검증 전 참고치다.

## 4. S4 검증 후보 제안

| 후보 | 내용 | 역할 |
|---|---|---|
| ① 변동성 비중조절 | 비중 = 1.9배 상한 × min(1, 과거 변동성 중앙값 ÷ 최근 20일 변동성). 매일이 아니라 주 1회 또는 변화 10%p 이상일 때만 조정하는 변형도 검증 | 평소 비중 결정(기본) |
| ② 급락 탈출 + FTD 재진입 보완형 | 고정 -4% 대신 변동성 대비 하락폭(예: 하루 -2.5σ) 사용, 긴 하락장 헛재진입을 줄이는 조건(예: 50일선 회복 동반) 추가 | 급락 초기 추가 축소·회복 초기 복귀 |
| ③ 200일선 | 단순 비교 기준 | 기준선 |
| 손실선 A·D | 1차 -10%에서 1.0배 이하, 최대 -20%에서 전부 현금 | 최종 안전장치(신호와 별개) |

- 브레드스 스러스트·90% 데이는 역사가 긴 회복 확인 신호지만 NYSE 등락 데이터 출처가 필요하다(확인 필요). SAVE 시장 메모의 참고 항목으로 먼저 쓰는 것이 부담이 적다.
- VIX 기간구조(⑥)는 이 재현에서 보유보다 최대 낙폭이 컸다(2022 완만한 하락장·2026-06 급락에서 신호 없음) → 단독 사용 비추천, 참고용.
- 급락 중 분할매수(역발상)는 사용자 전제와 맞지만 손실 예산(10%/20%)과 정면 충돌한다. 한다면 예산과 분리된 별도 현금으로만 가능하다.

## 5. 저장소 기존 연구와의 관계

- 기존 1년 재현(`stock-strategy-system/backtests/SOXL_EMA_POLICY_BACKTEST_2026-08-05.md`, 2025-08-05~2026-08-04)의 롱/현금 전환 연구 규칙도 +11.40%로 보유 +449.84%에 크게 뒤졌다. 강세장에서 신호 규칙이 뒤처지는 경향이 이번 장기 재현과 같다.
- 기존 walk-forward 게이트는 2018-08 이전 SOXL/SOXX 이력이 없어 실패 처리됐다. 이번에 Yahoo로 2010년 이후 이력을 받을 수 있음을 확인했다. 원 프로토콜은 Nasdaq 주 + Yahoo 교차확인이므로 S4에서 같은 방식으로 다시 받아야 한다.

## 6. 규칙 정의 (재현용)

- 가중치 w는 종가 t까지의 정보로 정하고, t+1 시가에 체결. 일간 수익 = (1 + w(t−1)·밤사이 갭) × (1 + w(t)·장중 수익) − 1 − 0.001 × |w(t) − w(t−1)|.
- ① VOL: w = min(1, 확장 중앙값(σ20) ÷ σ20), σ20 = SOXL 일간 수익률 20일 표준편차 × √252, 중앙값은 최소 120개 관측부터.
- ② CRASH_FTD: 보유 중 SOXX 하루 수익률 ≤ -4% 또는 종가 ≤ (최근 진입 이후, 최근 20거래일 최고 종가) × 0.90이면 탈출. 탈출 후 최저 종가를 추적(더 낮은 종가면 반등 일수 초기화), 첫 상승 종가를 반등 1일로 세고, 반등 4일째 이후 SOXX 하루 +2% 이상이면서 거래량이 전일보다 많으면 재진입.
- ③/④ SOXX 종가 > SMA200/SMA50이면 보유. ⑤ EMA10 > EMA20이면 보유. ⑥ VIX/VIX3M ≤ 1이면 보유.
- 급락 구간: SOXX 종가가 이전 고점 대비 -25% 이하로 내려간 구간(고점일~최저 종가일).

## 7. S4 검증 후보 등록 (2026-10-01, 사용자 결정)

- 사용자: "①과 보완한 ②를 다음 검증 후보로 올리고, Claude Code에 넘길 작업 지시문을 준비해줘"
- 등록 후보: C1 변동성 비중조절(①), C2 급락 탈출·2단계 재진입(②의 보완형: 고정 -4% 대신 변동성 대비 -2.5σ, 회복 확인(FTD) 때 절반만 복귀, 50일선·EMA10>EMA20 확인 뒤 전체 복귀), C3 결합(C1 × C2 단계 배수). 기준선 B0(SOXL 63.3% 유지), 참고 B1(200일선).
- 사전 등록 규칙·게이트·실행 방법: `docs/claude/s4-signal-walk-forward-builder-prompt-2026-10-01.md`
- 게이트를 통과해도 "S5 제안 후보"일 뿐이다. 활성화는 S5 제안 → S6 Judge → S7 사용자 승인 → forward shadow 뒤.

## 부록: 재현 스크립트 (세션 작업 공간에서 실행한 원본)

(2026-10-01 보완: 처음 저장 때 이 부록이 빠져 있었다. 아래는 S3 간이 재현에 쓴 원본이며 S4 구현 기준은 아니다. S4는 사전 등록 문서를 따른다.)

```python
# bt.py
"""D-grade research replay: crash-exit / recovery-entry signals on SOXX->SOXL (and QQQ->TQQQ).
Signals use data up to close t; weights apply from the open of t+1 (overnight gap included).
Cost 10 bp per unit weight traded; cash yield 0; taxes excluded. Parameters are conventional
defaults declared before running, not tuned.
"""
import pandas as pd, numpy as np, sys

px = pd.read_pickle('px.pkl')
END = '2026-09-29'          # drop partial 2026-09-30 bar
START = '2011-01-03'        # common evaluation start after SMA200 warm-up
COST = 0.001

def frame(t):
    x = px[t][['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
    return x.loc[:END]

def signals(sig, lev, vix, vix3m):
    c, v = sig['Close'], sig['Volume']
    out = {}
    out['BH'] = pd.Series(1.0, index=c.index)
    out['MA200'] = (c > c.rolling(200).mean()).astype(float)
    out['MA50'] = (c > c.rolling(50).mean()).astype(float)
    e10, e20 = c.ewm(span=10, adjust=False).mean(), c.ewm(span=20, adjust=False).mean()
    out['EMA10_20'] = (e10 > e20).astype(float)
    # volatility-managed: exposure = min(1, expanding median vol / current 20d vol) of leveraged ETF
    lr = lev['Close'].pct_change()
    vol20 = lr.rolling(20).std() * np.sqrt(252)
    med = vol20.expanding(min_periods=120).median()
    out['VOL'] = (med / vol20).clip(upper=1.0).reindex(c.index)
    # VIX term structure: out when VIX/VIX3M > 1
    ratio = (vix['Close'] / vix3m['Close']).reindex(c.index).ffill()
    out['VTS'] = (ratio <= 1.0).astype(float)
    # crash exit + follow-through re-entry (literal idea)
    r1 = c.pct_change()
    w = np.ones(len(c)); state_in = True
    low = None; rally_day = 0; entry_i = 0
    cv, vv, r1v = c.values, v.values, r1.values
    for i in range(len(c)):
        if i < 21:
            w[i] = 1.0; continue
        if state_in:
            # reference high: max close over the last 20 sessions, but only since the latest entry
            ref_hi = cv[max(entry_i, i - 19): i + 1].max()
            if r1v[i] <= -0.04 or cv[i] <= 0.90 * ref_hi:
                state_in = False; low = cv[i]; rally_day = 0
        else:
            if cv[i] < low:
                low = cv[i]; rally_day = 0
            elif rally_day == 0 and cv[i] > cv[i - 1]:
                rally_day = 1
            elif rally_day > 0:
                rally_day += 1
            if rally_day >= 4 and r1v[i] >= 0.02 and vv[i] > vv[i - 1]:
                state_in = True; entry_i = i
        w[i] = 1.0 if state_in else 0.0
    out['CRASH_FTD'] = pd.Series(w, index=c.index)
    return out

def run(w, lev, m):
    """w decided at close t (index aligned to lev); returns daily portfolio returns."""
    w = (w.reindex(lev.index).ffill().fillna(0.0) * m)
    o, c = lev['Open'], lev['Close']
    g = o / c.shift(1) - 1          # overnight t-1 close -> t open
    i = c / o - 1                   # intraday t open -> t close
    wp = w.shift(1).fillna(0.0)     # weight held overnight into day t (decided at close t-1)
    wpp = w.shift(2).fillna(0.0)    # weight held before the open-t rebalance
    # from close t-1 to open t we hold the weight decided at close t-2 (i.e. before rebalance at open t)
    r = (1 + wpp * g) * (1 + wp * i) - 1 - COST * (wp - wpp).abs()
    return r, wp

def stats(r, wp):
    r = r.loc[START:]; wp = wp.loc[START:]
    eq = (1 + r).cumprod()
    n = len(r)
    cagr = eq.iloc[-1] ** (252 / n) - 1
    mdd = (eq / eq.cummax() - 1).min()
    entries = ((wp > 0) & (wp.shift(1).fillna(0) == 0)).sum()
    return dict(CAGR=cagr * 100, MDD=mdd * 100, worst=r.min() * 100,
                d10=int((r <= -0.10).sum()), d20=int((r <= -0.20).sum()),
                expo=wp.mean() * 100, trips_yr=entries / (n / 252), total=(eq.iloc[-1] - 1) * 100)

def episodes(c, thr=-0.25):
    c = c.loc[START:]
    peak = c.cummax(); dd = c / peak - 1
    eps = []; i = 0; idx = c.index
    while i < len(c):
        if dd.iloc[i] <= thr:
            # find peak date before i
            pk_val = peak.iloc[i]; pk_date = c.loc[:idx[i]][c.loc[:idx[i]] == pk_val].index[-1]
            j = i
            while j < len(c) and c.iloc[j] < pk_val:
                j += 1
            seg = c.loc[pk_date:idx[min(j, len(c) - 1)]]
            tr_date = seg.idxmin()
            eps.append((pk_date, tr_date, seg.min() / pk_val - 1, idx[j] if j < len(c) else None))
            i = j + 1
        else:
            i += 1
    return eps

def episode_timing(w, c, eps):
    rows = []
    for pk, tr, depth, rec in eps:
        seg = w.loc[pk:tr]
        ws = w.loc[:pk]
        in_at_peak = ws.iloc[-1] > 0
        exit_dates = seg.index[(seg == 0) & (seg.shift(1).fillna(ws.iloc[-1]) > 0)]
        ex = exit_dates[0] if len(exit_dates) else None
        post = w.loc[tr:]
        ent_dates = post.index[(post > 0) & (post.shift(1).fillna(0) == 0)]
        en = ent_dates[0] if len(ent_dates) else None
        in_at_trough = w.loc[tr] > 0
        rows.append(dict(peak=pk.date(), trough=tr.date(), depth=round(depth * 100, 1),
                         out_before_peak=not in_at_peak,
                         exit=ex.date() if ex is not None else None,
                         exit_dd=round((c.loc[ex] / c.loc[pk] - 1) * 100, 1) if ex is not None else None,
                         in_at_trough=bool(in_at_trough),
                         reentry=en.date() if (en is not None and not in_at_trough) else None,
                         reentry_gain=round((c.loc[en] / c.loc[tr] - 1) * 100, 1) if (en is not None and not in_at_trough) else None))
    return rows

if __name__ == '__main__':
    pairs = [('SOXX', 'SOXL'), ('QQQ', 'TQQQ')]
    vix, vix3m = frame('^VIX'), frame('^VIX3M')
    for s, l in pairs:
        sig, lev = frame(s), frame(l)
        sigs = signals(sig, lev, vix, vix3m)
        print(f'===== {s} -> {l}  ({START} ~ {END})')
        for m in (1.0, 0.633):
            print(f'-- exposure when in: {m}')
            for k, w in sigs.items():
                r, wp = run(w, lev, m)
                st = stats(r, wp)
                print(f"{k:10s} CAGR {st['CAGR']:6.1f}%  MDD {st['MDD']:6.1f}%  worst {st['worst']:6.1f}%  d<=-10% {st['d10']:3d}  d<=-20% {st['d20']:2d}  expo {st['expo']:5.1f}%  entries/yr {st['trips_yr']:4.1f}")
        # underlying reference
        rr = sig['Close'].pct_change().loc[START:]
        eq = (1 + rr).cumprod()
        print(f"{s} 1x BH  CAGR {(eq.iloc[-1]**(252/len(rr))-1)*100:.1f}%  MDD {((eq/eq.cummax()-1).min())*100:.1f}%")
        if s == 'SOXX':
            eps = episodes(sig['Close'])
            print('episodes (SOXX dd<=-25%):', [(str(a.date()), str(b.date()), round(c * 100, 1)) for a, b, c, _ in eps])
            for k in ['MA200', 'MA50', 'EMA10_20', 'VTS', 'CRASH_FTD']:
                print('  --', k)
                for row in episode_timing(sigs[k].loc[START:], sig['Close'], eps):
                    print('   ', row)
            # best days vs drawdown state and strategy exposure
            c = sig['Close'].loc[START:]; r1 = c.pct_change(); dd = c / c.cummax() - 1
            best = r1.nlargest(20)
            print('top20 best SOXX days in dd<=-20%:', int((dd.loc[best.index] <= -0.20).sum()), ' within 10 sessions of a top20 worst day:',
                  int(sum(any(abs((r1.index.get_loc(b) - r1.index.get_loc(wd))) <= 10 for wd in r1.nsmallest(20).index) for b in best.index)))
            for k in ['MA200', 'MA50', 'EMA10_20', 'VTS', 'CRASH_FTD']:
                w = sigs[k].shift(1).reindex(c.index).fillna(0)   # weight held on that day (decided prior close)
                print(f'   {k:10s} in-market on top20 best days: {int((w.loc[best.index] > 0).sum())}/20, on top20 worst days: {int((w.loc[r1.nsmallest(20).index] > 0).sum())}/20')
```

```python
# bt2.py (구간별 분석)
from bt import *
sig, lev = frame('SOXX'), frame('SOXL')
vix, vix3m = frame('^VIX'), frame('^VIX3M')
sigs = signals(sig, lev, vix, vix3m)
eps = episodes(sig['Close'])
names = ['BH','VOL','MA200','EMA10_20','CRASH_FTD','VTS']
R = {}
for k in names:
    r, wp = run(sigs[k], lev, 1.0); R[k] = (r.loc[START:], wp.loc[START:])
print('decline phase (SOXX peak->trough) strategy return % | rebound 60 sessions after trough %')
for pk, tr, depth, rec in eps:
    row = [f'{pk.date()}~{tr.date()} ({depth*100:.1f}%)']
    idx = R['BH'][0].index
    t_i = idx.get_loc(tr); end = idx[min(t_i + 60, len(idx) - 1)]
    for k in names:
        r = R[k][0]
        dec = (1 + r.loc[pk:tr].iloc[1:]).prod() - 1
        reb = (1 + r.loc[tr:end].iloc[1:]).prod() - 1
        row.append(f'{k}:{dec*100:.0f}/{reb*100:.0f}')
    print(' | '.join(row))
print('exits (in->out) over period and entries inside decline phases:')
for k in names[1:]:
    w = sigs[k].loc[START:]
    if k == 'VOL':
        continue
    exits = int(((w == 0) & (w.shift(1) == 1)).sum())
    inside = 0
    for pk, tr, depth, rec in eps:
        s = w.loc[pk:tr]
        inside += int(((s == 1) & (s.shift(1) == 0)).sum())
    print(f'  {k:10s} exits {exits:3d}  re-entries during declines {inside}')
# yearly returns table
yr = {k: (1 + R[k][0]).groupby(R[k][0].index.year).prod() - 1 for k in names}
df = pd.DataFrame(yr) * 100
print(df.round(0).to_string())
```
