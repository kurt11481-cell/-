# 검증 2 — N-렌즈 v1 판정: HWM · CRS · SOLS · BKR · POWL

> 조사 원본 — Next 샌디스크 수시 발굴 1회차(2026-10-04) 에이전트 보고서. 이 줄 외에는 원문 그대로. 등급 D, 가격·시총은 외부 참고값(키움 미대조). 판정·결론 기준은 `docs/claude/next-sandisk-scan-2026-10-04.md`(초안). 매매 근거 아님.

- 기준일: 2026-10-04 (KST) · 증거 기준: 회사 공식 자료(SEC 8-K/10-Q/10-K, 회사 보도자료, 실적 원고). 업계 통계는 쓰지 않았다.
- 표기: **확인 필요 = 근거가 부족하다는 뜻. 상태 계산에서는 '아니오'로 셈한다.**
- 상태 규칙: 관찰 = G 2개 예 / 씨앗 = G 3개 모두 예 / 점화 = 씨앗이면서 I 3개 중 2개 예 / 제외 = X1 또는 X2 / 미달 = G 1개 이하.
- 시장 숫자는 **참고값**이다: Yahoo Finance 차트 데이터, 2026-10-02 종가 기준(키움 데이터 아님). 시총 = 종가 × 최근 10-Q/10-K 표지의 발행주식 수.
- Execution-Authority: NONE. 이 판정은 매매 근거가 아니다.

## 요약

| 티커 | G1/G2/G3 | I1/I2/I3 | X | 상태 | 다음 실적 |
|---|---|---|---|---|---|
| HWM | 예/아니오(경계)/예 | 아니오/아니오/예 | 없음 | **관찰** | 2026-10-29(목) 장전 |
| CRS | 예/아니오/예 | 아니오/아니오/예 | 없음 | **관찰** | 2026-10-22(목) 장전 |
| SOLS | 예/확인 필요/예 | 아니오/아니오/아니오 | 없음 | **관찰** | 2026-11-04(수) 장전 |
| BKR | 예/아니오/확인 필요 | 아니오/아니오/아니오 | 없음 | **미달** | 2026-10-27(화) 장후 |
| POWL | 예/아니오/아니오 | 아니오/확인 필요/아니오 | 없음 (X4 주의) | **미달** | 확인 필요(공지 없음) |

씨앗·점화·제외는 없다. 5종목 모두 G2(공급을 빨리 못 늘림)에서 막혔다. 자사 증설이 18개월 안에 가동되거나, 그 일정을 확인하지 못했기 때문이다.

---

## 1. HWM — Howmet Aerospace

| 항목 | 판정 | 근거 (출처·날짜·수치) |
|---|---|---|
| G1 | 예 | [10-Q 2Q26](https://www.sec.gov/Archives/edgar/data/4281/000000428126000025/hwm-20260630.htm) 2026-08-06: 가스터빈 매출 $321M(전년 $233M, +38%), 엔진 부문 $1,373M(+32%) |
| G2 | 아니오(경계) | [2Q 원고](https://www.fool.com/earnings/call-transcripts/2026/08/13/howmet-aerospace-hwm-q2-2026-earnings-call-transcript/) 2026-08-06: 이미 약정한 증설 장비가 "second half of 2026"부터 2~3년 동안 계속 들어온다 → 18개월 안 가동. 다만 일본 신공장은 "essentially fully spoken for", 지금 새로 약정하면 "earliest August of '28" |
| G3 | 예 | 같은 원고: "market share in excess of 50% globally for turbine blades in the IGT market". [10-K](https://www.sec.gov/Archives/edgar/data/4281/000000428126000012/hwm-20251231.htm) 2026-02-12: 승인·인증 요건 때문에 대체 공급처를 바로 찾기 어렵다 |
| I1 | 아니오 | 10-Q: "Product price increases are in excess of… cost pass through". 그러나 10-K상 2024·2025년에도 "favorable product pricing"이 이어졌다 → 직전 4분기에 하락·보합 없음 |
| I2 | 아니오 | [8-K](https://www.sec.gov/Archives/edgar/data/4281/000110465926091610/tm2622325d1_ex99-1.htm) 2026-08-06: 3Q 매출 가이던스 중간값 $2,575M ÷ 2Q 매출 $2,547M = 1.01배. EPS($1.35 > $1.33)·마진(32.2% > 32.1%)은 높음. 연간 가이던스는 $10.05B로 +$400M 상향 |
| I3 | 예 | 원고: 신공장 "already essentially fully spoken for", "customers really just want whatever we can make" |
| X1~X4 | 해당 없음 | X1 가격 하락 없음 · X2 공시통제 유효(10-Q), 감사인 PwC · X3 자사주 매입 연초 이후 $800M · X4 RTX·GE Aerospace가 각 ~11%(합 ~22%, 10-K) |
| 순도 | — | 2Q26 매출 중 엔진 부문 53.9%, 가스터빈 12.6% |
| 수요 뿌리 | — | 항공(신규기·엔진 스페어)·국방 + AI 데이터센터 전력(IGT) |
| 다음 실적 | 10-29 | [회사 공지 2026-10-01](https://www.howmet.com/press-release/2026-10-01/howmet-aerospace-to-host-webcast-and-announce-third-quarter-2026-results/) |
| 시장(참고) | — | 시총 ≈ $92.2B · 연초 대비 +12.8% · 52주 종가 고점($292.65, 08-18) 대비 −21.0% |
| **상태** | **관찰** | G 2/3 |

메모: GE Aerospace(HWM 고객, 매출 ~11%)가 경쟁사 CPP를 $11.75B에 인수한다고 발표했다([8-K 2026-09-08](https://www.sec.gov/Archives/edgar/data/40545/000095014226002501/eh260827362_ex9902.htm), 종결 2027년 하반기, "airfoil demand growing >30%"). 주조가 병목이라는 확인인 동시에, 고객이 생산을 내재화할 위험이기도 하다. 원고 요약본(Motley Fool)의 가스터빈 $341M은 10-Q의 $321M과 달라 10-Q 수치를 썼다.

## 2. CRS — Carpenter Technology

| 항목 | 판정 | 근거 |
|---|---|---|
| G1 | 예 | [3Q FY26 보도자료](https://www.sec.gov/Archives/edgar/data/17843/000001784326000018/a3rdqtrfy2026results.htm) 2026-04-29: "customers prioritize security of supply… we continue to advance long-term agreements". [원고](https://www.fool.com/earnings/call-transcripts/2026/07/30/carpenter-technology-crs-q4-2026-earnings-call-transcript/) 07-30: 대형 장기계약 갱신 진행 중. (A&D 매출(서차지 제외) +17%, 출하량 +22.6%는 매출 +20% 기준에 미달 → 장기계약 경로로 '예') |
| G2 | 아니오 | [4Q 보도자료](https://www.sec.gov/Archives/edgar/data/17843/000001784326000030/a4thqtr2026resultspressrel.htm) 2026-07-30·원고: 애선스 브라운필드 증설이 FY2028 초(≈2027-07) 완공, FY28 동안 생산을 늘려 이익에 기여 → 18개월 안 공급 추가 |
| G3 | 예 | [10-K](https://www.sec.gov/Archives/edgar/data/17843/000001784326000034/crs-20260630.htm) 2026-08-12: 고부가 제품의 주요 경쟁사는 10곳 미만, "require the materials to be qualified prior to supplying". 원고: "qualification cycles are long" |
| I1 | 아니오 | 10-K: FY26 실적은 "price increases"를 반영. 3Q·4Q에도 장기계약·현물 모두 가격 인상 → 바닥 없음. 앞으로 2년간 대형 장기계약 재가격 기회는 있다(원고) |
| I2 | 아니오 | 분기 매출 가이던스 없음. 1Q FY27 영업이익 가이던스 $195–200M < 4Q 실적 $206.9M. FY27 영업이익 $850–880M(+21~25%)은 이번에 처음 제시 |
| I3 | 예 | 원고: "accelerated ordering with extending lead times", 엔진사 "demand is less of a concern than the capacity" |
| X1~X4 | 해당 없음 | X2 내부통제 유효(10-K, PwC) · X3 자사주 매입($1.0B 추가 승인 08-12) · X4 매출 10% 이상 고객 없음 |
| 순도 | — | A&D가 서차지 제외 매출의 66.1%(4Q FY26). 엔진용 비중은 공개되지 않음(확인 필요) |
| 수요 뿌리 | — | 항공·국방 |
| 다음 실적 | 10-22 | [GlobeNewswire 2026-10-01(StockTitan 사본)](https://www.stocktitan.net/news/CRS/carpenter-technology-announces-conference-call-and-2fwkwgh77hon.html) |
| 시장(참고) | — | 시총 ≈ $19.3B · 연초 대비 +23.4% · 52주 고점($619.25, 07-06) 대비 −37.3% |
| **상태** | **관찰** | G 2/3 |

메모: CEO Malloy가 07-24 별세했고 Thene이 CEO로 복귀했다([8-K](https://www.sec.gov/Archives/edgar/data/17843/000119312526320951/d115412dex991.htm)). Thene은 08-25에 109,283주를 매도했다([8-K](https://www.sec.gov/Archives/edgar/data/17843/000001784326000038/crs-20260825.htm)).

## 3. SOLS — Solstice Advanced Materials

| 항목 | 판정 | 근거 |
|---|---|---|
| G1 | 예 | [2Q26 보도자료](https://www.sec.gov/Archives/edgar/data/2064953/000206495326000085/exhibit991-earningsrelease.htm) 2026-07-30: 원자력 매출 $125M(+27%, 가격·물량 모두 기여). [2026-02-10 보도자료](https://www.solstice.com/us/en/news-events/press-releases/2026/02/solstice-advanced-materials-announces-expansion-of-uranium-conversion-production-to-support-strong-nuclear-industry-customer-demand): 장기 고객 수주잔고 $2B 이상 |
| G2 | 확인 필요 | 02-10: 병목 해소로 2026년 UF6 10kt 초과 생산(2024 계획 대비 ~+20%), 신규 증설은 EPC 초기 분석 단계. [원고](https://www.fool.com/earnings/call-transcripts/2026/07/30/solstice-advanced-materials-sols-q2-2026-earnings-call-transcript/) 07-30: 10kt 이상으로 추가 병목 해소 검토 중(시점 미정). 경쟁사 일정은 확인 못 함. [10-K](https://www.sec.gov/Archives/edgar/data/2064953/000206495326000008/sols-20251231.htm): 장기 수급은 "balanced"로 전망 |
| G3 | 예 | 10-K 2026-02-19: "the only U.S.-based supplier". 02-10: "the only UF6 conversion facility in the United States" |
| I1 | 아니오 | 원자력 가격이 4Q25·1Q26·2Q26 세 분기 연속 유리(+39%/+27%/+27%) → 바닥 이후 첫 인상이 아님. 3Q25 원자력 −2%의 가격 요인은 공개되지 않음 |
| I2 | 아니오 | 3Q 매출 가이던스 $990–1,030M(중간값 $1,010M) ÷ 2Q $1,148M = 0.88배. 연간 가이던스는 상향(07-30) 후 재확인([08-27](https://www.sec.gov/Archives/edgar/data/2064953/000110465926102503/tm2620579d9_ex99-1.htm)) |
| I3 | 아니오 | 원자력에 대해 매진·할당 발언 없음. 10-K는 장기 수급 균형으로 전망. '일부 제품은 수주가 생산능력을 넘었다'는 회사 전체 문구는 품목을 특정하지 않음 |
| X1~X4 | 해당 없음 | X2 공시통제 유효([10-Q](https://www.sec.gov/Archives/edgar/data/2064953/000206495326000087/sols-20260630.htm)). 8-K/A(07-09)는 오타 정정뿐 · X3 Element 합병(약 1.26억 주 발행 예정)은 08-27 해지 → 희석 없음, $500M 자사주 매입 승인 · X4 10% 이상 고객 없음 |
| 순도 | — | 2Q26 매출 중 원자력 10.9% |
| 수요 뿌리 | — | 에너지 안보(원전 연료 국내 전환). 회사 전체로는 데이터센터 냉매·반도체 소재도 있음 |
| 다음 실적 | 11-04 | [회사 공지 2026-10-01](https://www.solstice.com/us/en/news-events/press-releases/2026/10/solstice-advanced-materials-to-announce-third-quarter-2026-financial-results-on-november-4-2026) |
| 시장(참고) | — | 시총 ≈ $9.2B · 연초 대비 +18.8% · 52주 고점($88.60, 06-30) 대비 −34.9% |
| **상태** | **관찰** | G 2/3 |

메모: Metropolis 소송은 09-29 합의 원칙에 도달했다(회사는 중대한 영향이 없다고 밝힘, [보도자료](https://www.solstice.com/us/en/news-events/press-releases/2026/09/solstice-advanced-materials-plaintiffs-announce-agreement-in-principle-to-settle-longstanding-litigation-related-to-metropolis-works-operations)).

## 4. BKR — Baker Hughes

| 항목 | 판정 | 근거 |
|---|---|---|
| G1 | 예 | [2Q26 보도자료](https://www.sec.gov/Archives/edgar/data/1701605/000170160526000021/earningsreleaseex991063020.htm) 2026-07-26: IET 수주 $7,088M(+101%), IET 수주/매출 2.2배, IET 수주잔고 $37.1B. NovaLT 76대(~1.3GW) 수주 |
| G2 | 아니오 | [원고](https://www.alphaspread.com/security/nasdaq/bkr/investor-relations/earnings-call/q2-2026) 07-27: 첫 NovaLT 증설이 2027 상반기 가동, 2028 말까지 가스터빈 능력 2배. "available 2027 delivery slots"(Frame 5 등) |
| G3 | 확인 필요 | [10-K](https://www.sec.gov/Archives/edgar/data/1701605/000170160526000007/bkr-20251231.htm): IET 경쟁사로 Siemens Energy·Solar·MHI 등을 나열. 점유율·인증 장벽에 대한 공식 언급 없음 |
| I1 | 아니오 | IET EBITDA에서 가격이 3Q25·4Q25·1Q26·2Q26 연속 플러스 → 바닥 이후 첫 인상이 아님 |
| I2 | 아니오 | 원고: 3Q 매출 가이던스 $6.87B ÷ 2Q $6.742B = 1.02배, EBITDA $1.205B < 2Q $1.231B. 연간은 소폭 상향, IET 수주 가이던스는 $17.5–19.5B로 상향. 09-09 Chart 포함해 갱신([8-K](https://www.sec.gov/Archives/edgar/data/1701605/000119312526385823/d539011dex991.htm)) |
| I3 | 아니오 | 일부 터빈은 2027 납기 슬롯이 남아 있다. NovaLT 신규 슬롯은 2028 말부터. 매진·할당은 명시되지 않음("strong pricing dynamics"만 언급) |
| X1~X4 | 해당 없음 | X2 내부통제 유효(10-K). 8-K/A(10-01)는 Chart 재무제표를 정례 제출한 것 · X3 Chart는 전액 현금 인수(채권 조달) · X4 10% 이상 고객 공시 없음 |
| 순도 | — | 2Q26 매출 중 가스장비(GTE) 22.6%, IET 48.8%. Power Systems 2025 매출 ~$1B(약 3.6%, CFO 발언) |
| 수요 뿌리 | — | 에너지 안보(LNG) + AI 데이터센터 전력 |
| 다음 실적 | 10-27 | 장 마감 후 보도자료, 10-28 웹캐스트. [GlobeNewswire 2026-09-28(StockTitan 사본)](https://www.stocktitan.net/news/BKR/baker-hughes-announces-dates-for-third-quarter-earnings-release-and-popg9dk946dn.html) |
| 시장(참고) | — | 시총 ≈ $55.6B · 연초 대비 +23.0% · 52주 고점($69.67, 04-30) 대비 −19.6% |
| **상태** | **미달** | G 1/3 |

## 5. POWL — Powell Industries

| 항목 | 판정 | 근거 |
|---|---|---|
| G1 | 예 | [FQ3 보도자료](https://www.sec.gov/Archives/edgar/data/80420/000008042026000103/ex991-powlq3xfy2026earning.htm) 2026-08-03: 수주 $934M(+158%), 수주/매출 3.0배(회계연도 누적 2.2배), 수주잔고 $2.4B(+69%) |
| G2 | 아니오 | 같은 자료·[원고](https://www.fool.com/earnings/call-transcripts/2026/08/10/powell-industries-powl-q3-2026-earnings-call-transcript/) 08-04: Jacintoport 야드(33.5만 sq ft) FY26 말 완공, 오하이오·휴스턴 임차 공장 추가, 30만 sq ft 신규 임차는 FY27 2~3분기 가동 |
| G3 | 아니오 | [10-K](https://www.sec.gov/Archives/edgar/data/80420/000008042025000152/powl-20250930.htm): "Our industry is highly competitive", 수주는 경쟁입찰 |
| I1 | 아니오 | 보도자료는 "strong and stable pricing environment"(보합)라고만 함. 공식 인상 발표 없음. CEO는 "some opportunity for price"라고만 언급 |
| I2 | 확인 필요 | 분기·연간 수치 가이던스를 내지 않음(정성 코멘트만) |
| I3 | 아니오 | 매진·할당·리드타임 증가 발언 없음. 경영진은 "delivery speed"를 가치 요인으로 언급 |
| X1~X4 | 해당 없음 (X4 주의) | X2 내부통제 유효(FY25, PwC) · X3 3:1 주식분할(희석 아님) · X4 FY25에 10% 이상 고객 없음. 다만 단일 데이터센터 수주 >$400M이 수주잔고의 약 17% |
| 순도 | — | 사실상 매출 전부가 전력 배전장비. FQ3 매출 중 유틸리티+상업·기타산업(데이터센터 포함) 52.9%. 데이터센터 단독 비중은 공개되지 않음([10-Q](https://www.sec.gov/Archives/edgar/data/80420/000008042026000107/powl-20260630.htm)) |
| 수요 뿌리 | — | 전력망 + AI 데이터센터 + LNG |
| 다음 실적 | 확인 필요 | FQ4 일정 공지 없음(10-04 기준). 참고로 작년 FQ4 발표는 [2025-11-18](https://www.sec.gov/Archives/edgar/data/80420/000008042025000145/powl-20251118.htm) |
| 시장(참고) | — | 시총 ≈ $7.1B · 연초 대비 +84.5%(분할 조정) · 52주 고점($322.05, 05-11) 대비 −39.1% |
| **상태** | **미달** | G 1/3 |

---

## 판정 메모

1. **G2는 문구 그대로 적용했다.** 의미 있는 신규 능력이 공식 일정상 18개월 안에 가동되면 '아니오'로 봤다. HWM은 경계 사례다. 18개월 안에 들어오는 증설분은 이미 선판매됐고("fully spoken for"), 새로 약정하는 능력은 빨라야 2028-08이다. **'선판매된 증설은 G2에서 뺀다'로 해석하면 HWM은 G2 예 → 씨앗이 된다(I는 1/3이라 점화는 아님).** 이 해석은 사용자가 정할 일이다.
2. **I1은 '바닥 후 첫 인상'으로만 셌다.** 가격 인상이 이어지고 있어도(HWM·CRS·SOLS·BKR) 직전 4분기에 하락·보합이 없으면 '아니오'다. POWL은 지금 '보합'이다. 공식 인상 발표가 나오면 I1 후보가 된다.
3. **사용자가 준 출발점과 원문 대조:** BKR 2Q 발표일 07-26(일)은 원문과 같다. CRS 원고 07-30/08-04는 같은 원고가 두 번 게시된 것이다. HWM 가스터빈 +38%는 10-Q로 확인했다(금액은 $321M).

## 출처·한계

- 원문은 SEC EDGAR, 회사 사이트(howmet.com, solstice.com)에서 직접 받았다. 원고는 제3자가 받아 적은 실적 원고다(Motley Fool: HWM·CRS·SOLS·POWL, AlphaSpread: BKR).
- 막힌 사이트는 우회하지 않았다: investors.bakerhughes.com(403), ir.carpentertechnology.com(403), globenewswire.com(빈 응답), investing.com(403), stooq.com(JS 검증), ir.powellind.com(502). CRS·BKR 실적일은 GlobeNewswire 원문을 StockTitan이 옮긴 사본으로 확인했다.
- 웹 검색 한도를 다 써서 URL 직접 조회로 진행했다. 업계 점유율 통계(G3 보조)는 조사하지 못했다.
