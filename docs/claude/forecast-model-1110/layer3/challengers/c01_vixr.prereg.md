# 도전자 사전 등록 — c01_vixr

- 성격: 표시·채점 전용. 주문·정책·상태·자동 코어 입력·한도·권한 변경 0. 편입은 사장 카드로만 한다.
- 규칙: forecast-layer3-rule-2026-11-10.md (판정·한도·기본 처분은 그 문서 그대로이고 여기서 바꾸지 않는다)
- 발견: D1 — The four experts all read prices and rates; no outside information about the coming width
- 이 발견의 도전 횟수: 1번째 (한도 2회)
- 만든 길: menu · 종류: history (과거 구간도 계산한다. 몫과 폭 배율은 기존 전문가와 같은 방식으로 과거에서도 배운다. 그 몫은 과거 성적과 같은 정보라 주간 결과에 싣지 않는다)
- 계산 파일: challengers/c01_vixr.py (sha256 5be2fd0b774a980cd77239b2318e7cf5cbd680b4afc1e852d359515b3e98f9a6)
- 추가 자료: {"VIX": "_VIX", "SPX": "_GSPC"}
- 추가 자료를 읽는 시점: 모든 종목이 시작일 전날까지의 값만 읽는다
- 판정 구간: 20거래일 (나머지 구간은 기록만)
- 판정 쌍: 20일 = FM2+ 대 FM2 (등록한 날 표시 중인 판. 뒤에 표시가 바뀌어도 이 쌍으로 판정한다)
- 등록 시각: 2026-11-12 15:07:50 KST · 등록 때 자료 기준일: 2026-11-11
- 그림자 채점 시작(T0): 시작일이 2026-11-13 이후인 예측만 판정에 쓴다.
- 등록 심사(기술 점검, 실제 결과와 대조하지 않음): static ok, api ok, valid_output ok, deterministic ok, no_lookahead ok, runtime ok, units ok, full_grid ok

## 정의 (계산 파일 머리글 그대로)

```
vixr: market implied-volatility ratio expert (FM-2 layer 3 menu, finding D1). Display/score only.

Idea: VIX is the option market's price for the next 30 days of S&P 500 movement. Set against the
movement the S&P 500 actually delivered over the last year, it says whether the market expects more
or less than the last year gave. The asset's own one-year volatility is scaled by that ratio.
The four incumbent experts read prices and rates only; this one reads an option price.

Definition (every value is known before the start day's close):
  ratio_t = (VIX_t / 100) / (sd of the last 252 daily log returns of the S&P 500 up to t, times sqrt(252))
  R_k     = the last ratio_t with t strictly before day k (EXTRA_LAG = 1). A value up to 7 calendar days old is
            used as it is (weekends, holidays, a missing VIX day); when it is older there is no forecast.
            VIX's daily close is fixed 15 minutes after the US stock close, so the same-day value is not
            known at a US asset's close; every asset therefore reads the previous VIX day.
  w(h)    = mean over j = 1..h of 0.5 ** (j / 60)      (fm1 M1 weight of "now" against "long run")
  v_k     = s252_k * sqrt(w(h) * R_k ** 2 + 1 - w(h))                 (daily volatility for horizon h)
  z_k     = (h-day log return that started at k) / (v_k * sqrt(h))    for known outcomes, k = 260 .. i - h
  forecast = quantiles of z at the levels V.QL, times v_i * sqrt(h)
No forecast when R_i is missing or fewer than 250 z values exist.
Nothing was chosen by looking at scores: 252 and 60 are the fm1 constants B_WIN and HALF; 260 and the quantile
recipe are fm1 M1's; 250 (known outcomes needed, about one year) and 7 (calendar days after which a value is
stale, the harness default) were set by hand before any score of this expert was computed.
VIX is used as an input of a displayed range only, never as a trading or exposure rule.
```

## 고정한 것

- 위 계산 파일은 등록 뒤 고치지 않는다. 고치면 새 도전으로 세고 새 T0부터 다시 잰다.
- T0 전 구간의 성적표는 만들지 않는다. 판정은 T0 이후에 낸 예측만으로 한다.
