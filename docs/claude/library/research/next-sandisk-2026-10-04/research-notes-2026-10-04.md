---
id: next-sandisk-research-notes-2026-10-04
type: research
status: current
supersedes:
as_of: 2026-10-04
valid_until: 확인 필요
tickers: [ALL]
evidence_grade: D
summary: Next 샌디스크 조사 3건(샌디스크 사례·병목 지도·과거 사례 21건)의 Cowork 정리 기록 + 원 보고서 출처 목록 전체(그대로 옮김). 설계 docs/claude/next-sandisk-discovery-design-2026-10-04.md 1·2절·부록 B의 근거. 매매 근거 아님.
---

# Next 샌디스크 조사 기록 (2026-10-04)

- 성격: 2026-10-04 Cowork 세션에서 조사 에이전트 3개가 낸 보고서를 Cowork가 정리한 기록이다. 원 보고서를 글자 그대로 다시 저장하려던 시도는 자동 안전 점검으로 중단됐다. 그래서 본문 표는 Cowork가 정리했고, **각 절 끝의 출처 목록만 원 보고서에서 그대로 옮겼다.**
- 근거 등급 D. 가격·시총·수익률은 외부 참고값(키움 미대조). 숫자를 카드·N절로 옮길 때는 행마다 공식 원문과 대조한다.
- 설계 문서에 이미 있는 내용(샌디스크 가격 구간·분기 실적 표, 시범 병목 지도, 사이클 시계)은 반복하지 않는다. 여기에는 설계 문서에 없는 세부만 둔다.
- 같은 폴더: `replay_sndk_r21.py`(리플레이 계산), `sndk.csv`·`soxx.csv`(Yahoo 일봉, 참고값).

## A. 샌디스크 사례 — 설계 문서 1절에 없는 세부

### A-1. 밸류에이션 경로 (run-rate P/E = 최신 분기 EPS 가이던스 중간값 × 4, 계산값)

| 시점 | 종가 | 지표 |
|---|---|---|
| 상장 2025-02-24 | $48.60 | P/B 약 0.77, EV/매출 약 1.0 |
| 저점 2025-04-22 | $29.62 | 시총 약 $4.3B, P/B 약 0.47, EV/매출 약 0.66, P/E 의미 없음(EPS 0 근처) |
| 돌파 직전 2025-09-03 | $53.01 | P/B 약 0.85, EV/매출 약 1.1 |
| 2025-11-03 | 약 $207 | MS 추정 CY26 EPS의 21배 |
| 2026-01-30 | $576 | run-rate 약 11배 |
| 고점 2026-06-25 | $2,335 | 시총 약 $3,400억, run-rate 약 18.5배, BofA 2027E EPS 기준 약 12배, TTM 약 75배, P/B 약 22 |
| 폭락 저점 2026-07-29 | $1,016 | run-rate 약 8배 |
| 2026-10-02 | $1,720 | 선행 P/E 8.0, TTM P/E 23.3, EV/EBITDA 19.5, P/B 16.3(stockanalysis) |

- 사이클 업종의 역설: 바닥에서는 P/B 0.5 미만이고 P/E는 의미가 없었으며, 고점에서는 P/E 8~12배로 오히려 싸 보였다.

### A-2. 설계 1-1에 없는 주요 일자

- 2025-02-25 S&P 600 편입(당시 시총 약 $7B). WDC 3주당 SNDK 1주 분배.
- 2025-06 WDC 잔여 지분 19.9%(2,880만 주) 중 약 2,130만 주 매각. 2026-02-17 잔여 지분 교환 매각($3.17B, 장중 −5.7%).
- 2025-08-06 HBF MOU(SK하이닉스): 주가 반응 미미(+0.4%, 다음날 −3.3%). HBF 샘플 2026 하반기, 기기 2027 초, 2026-08-05 OCP 표준 사양 공개 — 주가를 움직인 요인은 아니었다.
- 2025-11-20 하루 −20.3%(엔비디아 실적 뒤 기술주 급반전, 2차).
- 2026-03 구글 TurboQuant(AI 메모리 압축) 발표 → −25.9% 조정.
- 2026-06-23 하루 −13.6%(KOSPI 급락, 2차), 6/25 마이크론 실적에 +22.0%. 6/23~7/30 사이 하루 ±10% 이상 13거래일.
- 2026-07 폭락 요인: 메타 유휴 컴퓨트 판매 보도, 삼성·SK하이닉스 증설 경고(7/2), TrendForce 3Q26 +10~15%로 급감속(7/3), SK하이닉스 설비투자 +50%(≥$31B), CXMT IPO($8.6B), 중국 DUV 진전 보도(2차), SK하이닉스 실적 미달.
- 2026-07-30 삼성 "공급 제약 수년 지속" 발언 + MSFT 설비투자 안도로 하루 +26.0%. 8/6 FQ4 발표 다음날 −6.8%. 8/13 인베스터데이 +13.7%(FY28~30 매출 성장 10%대 중후반, 총마진 약 80%, 잉여현금 100% 주주 환원, NBM이 FY27 비트의 약 1/2·FY28의 약 2/3). 9/18 S&P 100 편입 직전 +11.0%(9/21 발효).
- FQ4 FY26 발표 자료 기준: NBM 8개사·최소계약 $93.9B·보증 $16.5B(보도자료로는 '4월 이후 5건 추가'만 확인 — 확인 필요), 총 설비투자 $562M(매출의 6.3%), 재고 $2.70B.

### A-3. 원 보고서의 '확인 필요' 목록

- 2025년 9월 가격 인상의 공식 발표일(9/4 전후 보도, TrendForce는 9/5 신규 주문분부터 적용).
- FQ3·FQ4 FY25 컨센서스, 2025년 봄 공매도 비율, HDD 부족이 처음 공개된 시점.
- FQ1 FY27 가이던스 vs 컨센서스(LSEG $10.47B 기준 상회, 다른 보도 $11.16B 기준 하회 — 출처마다 다름).
- 6/23 KOSPI 급락, 중국 DUV 진전, 2026-09-04 +11.9% 상승 촉매(2차 출처만).
- S&P 100 편입 발표일과 제외 종목(보도 상이).
- 2026년 개별 가격 인상 통지는 찾지 못함(NBM 계약으로 전환된 것으로 보임).
- 다음 실적 10/29는 stockanalysis 예정일(공식 확인 필요).

## B. 병목 지도 — 설계 부록 B에 없는 세부

### B-1. 다음 병목 (2027~28)

| 후보 | 근거 | 시점 | 관련 종목 |
|---|---|---|---|
| DRAM·HBM4E | 2027 HBM 비트 +50~60%로도 부족, NVIDIA Rubin Ultra HBM 사양 하향 검토(8/4) | ~2028 | MU |
| CPO 외부광원(고출력 CW)·InP | LITE 고출력 레이저 부족·신공장 2028, scale-up용 CPO 2027 하반기 | 2027~28 | LITE·COHR·AXTI·SMTOY |
| 포토닉스 SOI | Soitec 포토닉스 SOI 점유 95%, 예치금 다년계약, 신공장 약 2029 | 2027~28 | Soitec·TSEM |
| ABF·T-glass·글라스 코어 | ABF 부족 2028까지, T-glass 캐파 3배로도 부족 | 2027~28 | IBIDF·AJNMY·NBCLF |
| 800V DC·SST | NVIDIA Kyber와 함께 2027 본격화, GEV SST 수주 2027 | 2027~ | IFNNY·ON·NVTS·GEV |
| 가스터빈·변압기 | 인도 2028~30, 슬롯 협의 2032 | ~2030 | GEV·SMERY·MHVYF·HTHIY |
| 프로브카드 | FormFactor 신공장 2028 초 | 2027 | FORM |
| 정책 이벤트 | 갈륨·게르마늄 유예 11/27, 희토류 휴전 1/10 만료 | 2026 말~27 | — |

### B-2. 부록 B에 없는 구간 세부

- 웨이퍼·소재: 헬륨 — 카타르 피격으로 세계 공급 약 30% 이탈, 가격 +40~100%, 9월 말에도 부분 재가동. 레지스트 — 호르무즈 나프타 → 용제 부족, 재인증 약 1년, 일본 3사 10/1부터 +15%(확인 필요). Soitec(SLOIF) $6.7B · +665% · −17%, 신에츠(SHECY) $70B · +25% · −22%, 도쿄오카(TOKCF) $6.5B · +44% · −25%.
- MLCC: Murata "장납기 주문 증가" 경계, 제품가 하락폭 축소(아직 인상 아님). MRAAY $100B · +167% · −29%, TTDKY $39B · +47% · −22%.
- 테스트: Advantest(ATEYY) $184B · +102% · 0%. 번인·소켓은 1차 근거 미수집.
- 첨단 패키징: BESI(BESIY) $18B · +48% · −38%. HBM 하이브리드본딩은 HBM5(2029~30)로 이연(SK하이닉스 Hot Chips, 2차).
- 전력 장비: Siemens Energy 가스터빈 69GW·리드타임 3년+·변압기 수주 +28%(8/10), MHI 35GW(전년 23GW, 8/13). SMERY $139B · +17% · −27%, MHVYF $83B · 0% · −28%, HTHIY $159B · +14% · −9%.
- 서버 CPU: 서버 CPU 가격 +10~20%, 리드타임 약 6개월(2026-04 보도).
- 부족 근거 약함: Credo 매출 +115%이나 부족 근거 없음, Vertiv "일시적 공급망 혼잡", Silicon Motion은 NAND 역풍, SiC는 과잉 뒤 반등 보도(원문 미확인).

### B-3. 원 보고서가 꼽은 소외 후보 (SanDisk 직전형)

| # | 종목(참고값: 시총 · 연초 대비 · 고점 대비) | 가장 중요한 증거 | 주요 리스크 |
|---|---|---|---|
| 1 | 스미토모전기 SMTOY(OTC) $50B · +60% · −28% (대안 JX금속 JXAMY) | InP 기판 리드타임·스팟가 상승, 캐파 3.1배(7/13). EML·CW 상위 3사 합계 55% | 자동차 와이어링 비중이 커서 AI 노출 희석 |
| 2 | Vishay VSH $5.9B · +163% · −45% | 수주/출하 1.32, 품번 1/3 가격 인상(8/5) | 원가 전가형 인상, 총마진 23%, $5B 하한 근접 |
| 3 | 미쓰비시중공업 MHVYF(OTC) $83B · 0% · −28% (대안 SMERY) | 백로그 35GW(전년 23GW), 신규 수주 수익성 개선(8/13) | 방산 혼재, 매출 인식 2028~30 |
| 4 | Hoya HOCPY(OTC) $52B · +3% · −18% | HDD 유리기판 유일 공급사, "3.5인치 기판 매출 크게 증가"(7/31, 2차) | 가격 인상 미공시, HDD 외 사업 비중 큼 |
| 5 | 아지노모토 AJNMY(OTC) $32B · +60% · −15% | ABF 필름 점유 90%+, +30% 인상(2차) | 식품 본업이 희석 |
| 6 | WDC $150B · +141% · −48% | "2026 생산 매진, LTA 2028~29" 보도(2/5) | 7월 메모리 디레버리징, NAND 완화 시 QLC SSD 대체 |
| 7 | 도쿄오카 TOKCF(OTC) $6.5B · +44% · −25% | 용제 부족 + 10/1 가격 인상 | 인상 1차 출처 미확인 |

- $5B 미만: Nittobo NBCLF(OTC) $4.1B · −45%(T-glass 약 90%, 추가 인상 없음), Navitas NVTS $3.3B · −64%(NVIDIA 800V 파트너, 실적 근거 약함).
- 혼잡(이미 반영): MU·SNDK, LITE·COHR(NVIDIA가 각각 $2B 투자), Advantest·TER·FORM, Ibiden·ASE, Soitec·AXTI.
- 주의: 이 표는 원 보고서의 판단이다. 시스템 판정은 설계 문서의 결정 3(OTC = 지표 종목 고정)과 N-렌즈 판정(부록 B-2)을 따른다.

### B-4. 원 보고서의 리스크·미검증

- NAND 2027 전망 상충(Micron 공급 제약 지속 vs TrendForce 2027 하반기 완화) — 저장장치 판단의 핵심 변수.
- 2차 출처: 아지노모토 +30%, Kingboard CCL, 레지스트 인상, Hoya IR 요약, Coherent·Seagate 콜 요약.
- Digitimes 원문은 403으로 확인 못 함(우회 안 함). 호르무즈·카타르 현 상태 확인 필요.

## C. 과거 사례 21건 — 설계 문서 2절에 없는 세부

### C-1. 5배 이상 사례

| 사례 | 시작 → 고점(배수) | 사전 조건 | 트리거 | 끝·고점 신호 |
|---|---|---|---|---|
| MU 2016~18 | $9.32 → $61.1(2018-05), 6.6배 | 2015년 −60%, DRAM 3사 과점, PC DRAM 공급 이전·수율 차질 | 2016-09 계약가 월 +7.4%, 4Q +30% 전망 | 증설(삼성·하이닉스·칭화), 선행 P/E 4.5배, MS 하향(2018-05-31) → 12월 −54% |
| NVDA 2022~24 | $112(2022-10-14) → 분할 환산 $1,356(2024-06-18), 12배 | 2년 저점, CoWoS 병목(수요의 약 80%만 충족, 해소까지 1.5년) | 2023-05-24 가이던스 $11B(컨센서스 $7.15B) | 끝나지 않음, −27%급 조정 반복 |
| SMCI 2023~24 | 2년 20배, 고점 2024-03 | AI 서버 수요 | 분기 매출 2배($3.66B) | S&P 편입 다음 날 증자, 총마진 11.3%, 감사인 사임 → −73% |
| VRT 2023~25 | 2022 저점 $8.21 → 2년 10배+ | 원가 상승으로 마진 붕괴 뒤 가격 인상, P/E 약 12.7 | 4Q22: 가격이 원가를 앞섬, 수주 > 매출 | DeepSeek 때 −26.8% 뒤 재상승 |
| CLS 2024~25 | 2024 +226%, 2025 +218%, 약 10배 | 하이퍼스케일러 설비투자(저평가 여부 확인 필요) | 2024-01-29 EPS가 가이던스 상단 초과 | 고점 2026-06-02, 가이던스 상향에도 −16% |
| AAOI 2024 | $6.87 → $44.03, 6.4배 | 2022년 $1.50 바닥 | 4Q 가이던스 $94~104M(3Q 실적 $65M) | 범용화로 2025년 −77%, 아마존 워런트는 고점 뒤 |
| CRDO 2024~26 | 2024년 4.6배, $33.3(2025-04) → $302.5(2026-06-22) 9배 | 최대 고객 주문 삭감으로 반토막(2023-02) | 2024-12 가이던스 급상향, 당일 +47% | 고객 집중(상위 2개 61%), 가이던스 상향에도 −43% |
| LITE 2025~26 | $45.7 → $1,085, 24배(진행 중) | 2022~23 소외 | 2025-08 "FY26 내내 수요 > 공급", 사상 최대 구매약정 | 2027년까지 매진, 공매도 비중 약 16%, 신규 팹 약 2028 |
| AXTI 2025~26 | $1.13 → $96(2026-05-01), 85배 | 초소형주, FY25 매출 −11%, 중국 수출통제 | 수출 허가 뒤 3Q 매출 $28M(가이던스 $19~21M) | $632.5M 증자·생산능력 3배, −61% 뒤 고점 회복 |
| SNDK 2025~26 | 약 $36(분사 기준가, 확인 필요) → $2,354(2026-06-22), 약 65배 | 분사, NAND −10%+ 감산 | 2025-03 "4/1부터 +10%" 인상 통지 | 선행 P/E 7.15배, 7/29 −57% |
| WDC·STX 2025~26 | WDC $30.4 → $594 19.5배, STX 1년 +646% | 2022년 각 −50%대, 의미 있는 증설 없음 | 2025-09 전 제품 가격 인상, 리드타임 약 1년 | 2027~28 물량 $20/TB 협상 중, STX 고점 대비 −22% |
| MU 2025~26 | $64.6 → 약 $1,255, 19배 | 설비투자 절제, HBM이 웨이퍼 잠식, 재고 3.3주 | 2025 하반기 DDR5 분기마다 +30~50% | 실적 대폭 상회에도 하락, 7월 −28.7%, 재고일수 증가·설비투자 상향 |
| BE 2025~26 | $16 → $346, 21배 | 데이터센터 전력 수요 | 오라클 최대 2.8GW 계약(+24%) | 컨센서스 목표가가 주가보다 34% 낮음 |

### C-2. 5배에 못 미쳤거나 무너진 사례 (SMCI는 C-1 표에 있음)

| 사례 | 결과 | 갖췄던 조건 | 결정적 결함 |
|---|---|---|---|
| WDC·STX 2016~17 | WDC 3.2배, STX 연 +15%/+12% | 과점, 저점 출발 | 큰 새 수요가 없음 |
| MU·WDC 2020~22 | MU 2.8배 뒤 −50%, WDC 2.7배 | 가격 상승 | 공급이 수요를 따라잡음(MS "Winter is coming", 2021-08-12) |
| MU 2023~24 | 3.1배 뒤 −58% | 삼성 감산, HBM | 범용 DRAM 약세(19배 상승은 이 조정 뒤에 옴) |
| AAOI 2016~18 | 11.7배 뒤 −86% | 클라우드 100G | 호실적에도 다음 분기 가이던스 미스로 −26% |
| NVDA 2018 | −50%+ | 크립토 수요 | 채널 재고, 가이던스 $2.7B vs 컨센서스 $3.4B |
| WOLF 2021~25 | 2025 상반기 −94%, 파산보호 | EV 수요, 르네사스 $2B 선급금 | 중국 증설로 SiC 웨이퍼 $1,500 → $500 이하, 르네사스 약 $1.7B 손실 |
| 광통신 2000~01 | CIEN 2000 +192% 뒤 2001 −78% | 인터넷 수요 | 이중발주("120 주문해 100 확보"), 시스코 $2.2B 재고상각 |

### C-3. 사전 DNA 체크리스트 (원 보고서의 정성 분류 — 통계 아님)

● = 명확, ◐ = 부분적.

| # | 특징 | 승자 13건 | 미달·붕괴 8건 | 판별력 |
|---|---|---|---|---|
| 1 | 큰 새 수요 | ●13 | ●7 ◐1 | 낮음(필요조건일 뿐) |
| 2 | 공급 확대에 18~24개월 이상 | ●6 ◐4 | 0~1 | 가장 높음(5배와 3배를 가름) |
| 3 | 병목 단계 과점 | ●4 ◐6 | ●4 ◐1 | 하락 깊이를 결정(비과점은 −73~−94%) |
| 4 | 바닥·소외 출발(분사·높은 공매도 포함) | ●11 ◐2 | ●6 | 상승폭을 키우는 요인 |
| 5 | 직전 감산·설비투자 축소 | ●3 ◐1 | ●1 ◐1 | 원자재형 부품에서 높음 |
| 6 | 공식 가격 반전(계약가·인상 통지) | ●5 ◐3 | ●2 ◐1 | 바닥 뒤 첫 인상만 의미 |
| 7 | 가이던스 쇼크(컨센서스 +30% 이상) | ●7 ◐6 | 고점에서도 발생 | 초기 트리거로 높음 |
| 8 | 경영진 "수요 > 공급"·리드타임 증가 | ●6 ◐1 | ●2 ◐1 | 후반부에는 이중발주 경고 |
| 9 | 고객 선급금·장기계약·워런트 | ●5 ◐3 | ●2 | 낮음(주로 사이클 중·후반) |
| 10 | 고객 집중(상위 고객 ≥ 40%) | ●1 ◐1 | ◐2 | 변동성을 양방향으로 증폭 |

- 보조 관찰: 주가가 데이터보다 먼저 움직였다(MU 2016 주가 바닥이 계약가 반등보다 먼저, AXTI는 매출 −11%일 때 30배 넘게 상승).

### C-4. 후회 패턴

| 패턴 | 사례 | 교훈 |
|---|---|---|
| 첫 2배에서 매도 | NVDA는 2023-05에 이미 +235%였지만 이후 약 3.6배 더, MU는 2017-07 "파티는 끝났다" 평가 뒤 약 2배 더 | 청산 근거는 밸류가 아니라 공급·가격 데이터 악화여야 함 |
| −30~−60% 조정에 이탈 | VRT −26.8%, CRDO −50% 뒤 9배, AXTI −61% 뒤 고점 회복, SNDK −57% 뒤 +69% | 가격·리드타임 지표가 그대로면 심리적 조정. 반례 SMCI·AAOI·WOLF는 회사·구조가 무너진 경우 |
| 낮은 P/E 보고 고점 매수 | MU 2018-01 선행 P/E 4.5배 → 고점 뒤 −54% | 사이클주의 낮은 P/E는 이익 고점 경고 |
| 종목 분산 ≠ 테제 분산 | 2026-06 동시 고점, 7/29 동시 −41~−61% | MU·SNDK·WDC/STX·DRAM ETF·SOXL 동시 보유는 사실상 하나의 베팅 |
| 고객 집중 무시 | CRDO 2023·2026, AAOI 2017 | 상위 고객 비중을 포지션 한도에 반영 |
| 구조적 공급 과잉에 물타기 | WOLF(선급금이 있었는데도 파산보호) | 중국 증설로 가격이 −60% 넘게 빠지면 "싸다"가 아니라 "깨졌다" |

### C-5. 한계

- 승자·실패 빈도는 직접 분류한 정성 판단이고, 생존 편향이 있다.
- 2026년 수치 상당수는 뉴스·시세 사이트 기준. 모건스탠리 7/6 보고서 원문은 확인하지 못함.
- 확인 필요: SNDK 분사 기준가($36 vs $38.50), CRDO·VRT 2025-01 고점가, AAOI·AXTI·BE 저점 날짜, CLS 저평가 여부, BE 2025년 트리거. 참고: CIEN은 2025년 +181%, 2026년 연초 대비 +67%로 약 4.7배.
- 일부 사이트(CNBC 일부, Seeking Alpha, Macrotrends 일부)는 접근 거부 — 우회하지 않음.

## 출처 목록 (원 보고서에서 그대로 옮김)

### A-출처 — 샌디스크 사례 보고서

**공식**
- O1 상장: https://investor.sandisk.com/news-releases/news-release-details/sandisk-celebrates-nasdaq-listing-after-completing-separation
- O2 분배 공지: https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2025-38
- O3 FQ3 FY25: https://www.sec.gov/Archives/edgar/data/2023554/000202355425000021/sndkq3fy25ex991-pressrelea.htm
- O4 FQ4 FY25: https://www.businesswire.com/news/home/20250814229961/en/Sandisk-Reports-Fiscal-Fourth-Quarter-2025-Financial-Results
- O5 FQ1 FY26: https://www.sec.gov/Archives/edgar/data/2023554/000162828025050180/sndkq1fy26ex991-pressrelea.htm
- O6 FQ2 FY26: https://www.sec.gov/Archives/edgar/data/2023554/000162828026004121/sndkq2fy26ex991-pressrelea.htm
- O7 FQ3 FY26: https://www.sec.gov/Archives/edgar/data/2023554/000162828026028879/sndkq3-26ex991xpressrelease.htm
- O8 FQ4 FY26: https://www.businesswire.com/news/home/20260805455789/en/Sandisk-Reports-Fiscal-Fourth-Quarter-2026-Financial-Results
- O9 FQ4 FY26 발표 자료: https://investor.sandisk.com/static-files/c75d1bee-c5c9-4e5a-8605-302c1aeac59b
- O10 인베스터데이: https://investor.sandisk.com/news-releases/news-release-details/sandisk-details-growth-strategy-and-long-term-financial-model
- O11 HBF MOU: https://investor.sandisk.com/news-releases/news-release-details/sandisk-collaborate-sk-hynix-drive-standardization-high
- O12 WDC 지분 교환 424(b)(7): https://investor.sandisk.com/static-files/2319dcd3-1ea8-4624-a024-e08be4e266fc
- O13 S&P 500 편입: https://press.spglobal.com/2025-11-24-Sandisk-Set-to-Join-S-P-500-Upwork,-First-Interstate-BancSystem,-PTC-Therapeutics-to-Join-S-P-SmallCap-600
- O14 S&P 600 편입: https://press.spglobal.com/2025-02-19-SanDisk-Set-to-Join-S-P-SmallCap-600
- O15 Nasdaq-100 편입: https://ir.nasdaq.com/news-releases/news-release-details/sandisk-corporation-join-nasdaq-100-indexr-beginning-april-20

**TrendForce**
- T1: https://www.trendforce.com/news/2025/03/07/news-sandisk-to-raise-nand-prices-over-10-from-april-1-signaling-market-rebound/
- T2: https://www.trendforce.com/news/2025/07/17/news-nand-flash-price-hikes-reportedly-set-for-q3-with-supply-shortage-likely-stretching-into-2026/
- T3: https://www.trendforce.com/news/2025/09/12/news-micron-freezes-prices-as-inference-ai-fuels-surge-in-ssd-demand-and-supply-shortages/
- T4: https://www.trendforce.com/news/2025/09/15/news-western-digital-raises-hdd-prices-amid-soaring-demand-shipping-delays-of-up-to-10-weeks/
- T5: https://www.trendforce.com/news/2025/09/17/news-sandisk-reportedly-sees-nand-shortage-until-2026-ongoing-price-opportunities-across-board/
- T6: https://www.trendforce.com/news/2025/10/30/news-hyperscalers-ramp-up-capex-amid-ai-boom-risks-lurk-microsoft-meta-alphabet-in-spotlight/
- T7: https://www.trendforce.com/presscenter/news/20251201-12807.html
- T8: https://www.trendforce.com/presscenter/news/20260105-12860.html
- T9: https://www.trendforce.com/presscenter/news/20260202-12911.html
- T10: https://www.trendforce.com/presscenter/news/20260303-12943.html
- T11: https://www.trendforce.com/presscenter/news/20260331-12995.html
- T12: https://www.trendforce.com/presscenter/news/20260703-13134.html

**언론·애널리스트**
- M1: https://finance.yahoo.com/news/sandisk-stock-soars-nvidia-ceo-211837162.html
- M2: https://blocksandfiles.com/2026/01/06/nvidia-standardizes-gpu-cluster-kv-cache-offload-to-nvme-ssds/
- M3: https://finance.yahoo.com/news/sandisk-surges-robust-ai-demand-155458803.html
- M4: https://finance.yahoo.com/news/sandisk-soars-earnings-beat-guidance-215633995.html
- M5: https://finance.yahoo.com/technology/ai/articles/sandisk-forecasts-upbeat-quarterly-revenue-211115527.html
- M6: https://www.investing.com/news/company-news/sandisk-q3-2026-slides-revenue-surges-251-margins-hit-78-93CH-4651673
- M7: https://finance.yahoo.com/news/sandisk-q2-earnings-beat-estimates-133500226.html
- M8: https://www.fool.com/earnings/call-transcripts/2026/04/30/sandisk-sndk-q3-2026-earnings-transcript/
- M9: https://finance.yahoo.com/news/sandisk-q2-earnings-call-highlights-005255530.html
- M10: https://www.investing.com/news/analyst-ratings/sandisk-price-target-raised-to-85-from-70-at-benchmark-on-pricing-power-93CH-4229427
- M11: https://www.investing.com/news/analyst-ratings/morgan-stanley-raises-sandisk-stock-price-target-to-96-on-ai-demand-93CH-4234953
- M12: https://www.investing.com/news/analyst-ratings/sandisk-stock-price-target-raised-to-230-from-96-at-morgan-stanley-93CH-4326653
- M13: https://www.investing.com/news/analyst-ratings/mizuho-sets-sandisk-stock-outperform-with-60-target-93CH-3917085
- M14: https://finance.yahoo.com/news/sandisk-rally-pushes-short-squeeze-161055515.html
- M15: https://sherwood.news/markets/western-digital-announces-additional-usd4-billion-in-share-buybacks-with/
- M16: https://www.tomshardware.com/pc-components/storage/sandisk-reportedly-jacks-up-flash-prices-by-50-percent-as-memory-makers-cash-in-on-ai-fueled-demand
- M17: https://seekingalpha.com/news/4492359-sandisk-shares-rise-on-ms-upgrade-strong-nand-demand-and-essd-surge-drive-optimism
- M18: https://invezz.com/news/2025/11/20/sandisk-stock-plunges-20-on-thursday-heres-what-triggered-the-big-sell-off/
- M19: https://finance.yahoo.com/news/western-digital-selling-sandisk-stock-140002864.html
- M20: https://sherwood.news/markets/sandisk-micron-dive-as-google-research-unveils-ai-algorithm-to-reduce-memory/
- M21: https://www.fool.com/investing/2026/03/26/why-shares-of-sandisk-fell-this-week/
- M22: https://www.fool.com/investing/2026/06/25/why-sandisk-stock-soared-today/
- M23: https://www.fool.com/investing/2026/07/07/why-sandisk-stock-jumped-34-in-june/
- M24: https://www.indmoney.com/blog/us-stocks/sandisk-stock-crash-explained-sndk-fall-ai-nand-analysis
- M25: https://finance.yahoo.com/markets/stocks/articles/sandisk-sinks-11-seagate-falls-160250009.html
- M26: https://www.fool.com/investing/2026/07/06/sandisk-stock-plunged-14-in-a-day-is-the-ai-memory/
- M27: https://finance.yahoo.com/markets/article/micron-samsung-sk-hynix-just-dragged-memory-stocks-into-a-bear-market-154549356.html
- M28: https://www.benzinga.com/markets/tech/26/07/60718731/sandisk-stock-extends-losses-as-ai-memory-trade-unravels
- M29: https://qz.com/cxmt-stock-shanghai-debut-ipo-memory-chip-072726
- M30: https://finance.yahoo.com/markets/article/sk-hynixs-record-profit-fails-to-impress-investors-130352334.html
- M31: https://invezz.com/news/2026/07/30/why-micron-sandisk-sk-hynix-and-other-memory-stocks-are-roaring-back-today/
- M32: https://finance.yahoo.com/markets/stocks/articles/sandisk-joins-p-100-monday-051301493.html
- M33: https://247wallst.com/investing/2026/10/02/seagate-tumbles-10-western-digital-drops-7-as-toshiba-moves-to-double-hard-disk-output/
- M34: https://www.tipranks.com/news/why-micron-and-sandisk-stocks-are-slipping-today-october-2-and-what-wall-street-sees-ahead
- M35: https://www.fool.com/investing/2026/10/01/micron-says-memory-supply-will-be-much-tighter-in-2028-sandisk-s-contracts-limit-how-much-it-can-gain/
- M36: https://www.fonearena.com/blog/488824/sandisk-sk-hynix-high-bandwidth-flash-specifications.html
- M39: https://www.webull.com/news/13814746696664064
- M40: https://www.fool.com/investing/2026/08/03/why-sandisk-stock-tumbled-47-in-july/

**가격 데이터**
- P1 Yahoo 일봉: https://query1.finance.yahoo.com/v8/finance/chart/SNDK
- P2 stockanalysis 통계: https://stockanalysis.com/stocks/sndk/statistics/

일봉 데이터(2025-02-13~2026-10-02, 411행)는 /tmp/claude-0/-home-claude/febf0f20-367f-5b1d-a106-667eac3da876/scratchpad/sndk.csv 에 저장되어 있습니다.

### B-출처 — 병목 지도 보고서

[1] Micron, 2026-09-30 https://s25.q4cdn.com/621799436/files/doc_financials/2026/q4/Q4-FY26-Prepared-Remarks.pdf
[2] TrendForce, 2026-09-30 https://www.trendforce.com/presscenter/news/20260930-13258.html
[3] 서울경제, 2026-10-01 https://en.sedaily.com/finance/2026/10/01/hbm-prices-to-more-than-double-next-year-as-shortage
[4] TrendForce, 2026-07-30 https://www.trendforce.com/presscenter/news/20260730-13158.html
[5] SanDisk, 2026-08-05 https://www.nasdaq.com/press-release/sandisk-reports-fiscal-fourth-quarter-2026-financial-results-2026-08-05
[6] Seagate 콜, 2026-07-28 https://www.investing.com/news/transcripts/earnings-call-transcript-seagate-beats-q4-2026-forecasts-as-shares-rebound-after-hours-93CH-4818284 · 교차확인 https://www.tomshardware.com/pc-components/hdds/seagate-to-start-qualifying-record-setting-50tb-hdds-in-2027-most-drives-are-sold-out-through-2028
[7] TrendForce, 2026-07-22 https://www.trendforce.com/news/2026/07/22/news-ai-data-center-demand-revives-hdd-demand-japanese-component-makers-tdk-hoya-resonac-expand-capacity/
[8] TSMC 콜, 2026-07-16 https://www.fool.com/earnings/call-transcripts/2026/07/16/tsm-tsm-q2-2026-earnings-call-transcript/
[9] TrendForce, 2026-04-30 https://www.trendforce.com/presscenter/news/20260430-13028.html
[10] SK hynix Hot Chips, 2026-09-01 https://ninescrolls.com/news/sk-hynix-rules-out-hybrid-bonding-for-hbm4e-775-micron-ceiling-keeps-mr-muf/
[11] Amkor, 2026-07-27 https://ir.amkor.com/news-releases/news-release-details/amkor-technology-reports-financial-results-second-quarter-2026
[12] AtlasPCB(Digitimes 인용), 2026-05-14 https://www.atlaspcb.com/news/news-ajinomoto-abf-substrate-price-increase-2026/
[13] BofA 요약, 2026-03-26 https://thebuildout.ai/intel/229c44f2-da57-4f46-b5fa-e5d03702236c
[14] TrendForce, 2026-08-06 https://www.trendforce.com/news/2026/08/06/news-nittobo-raises-fy2027-net-profit-forecast-by-jpy-3b-no-further-t-glass-price-hikes-planned/
[15] BigGo, 2026-07-07 https://finance.biggo.com/news/5339bae1-2900-4293-94f5-1944f85805e0
[16] TTM, 2026-08-05 https://finance.yahoo.com/markets/stocks/articles/ttm-technologies-inc-ttmi-q2-051114490.html
[17] Lumentum 콜, 2026-08-18 https://www.fool.com/earnings/call-transcripts/2026/08/18/lumentum-lite-q4-2026-earnings-call-transcript/
[18] Futurum(Coherent), 2026-08-14 https://futurumgroup.com/insights/coherent-q4-fy-2026-earnings-1-6t-transceivers-ramp-cpo-revenue-approaches/
[19] TrendForce, 2026-07-13 https://www.trendforce.com/news/2026/07/13/news-sumitomo-electric-to-raise-inp-substrate-expansion-scale-with-jpy-18-billion/
[20] AXT, 2026-08-04 https://www.semiconductor-today.com/news_items/2026/aug/axt-040826.shtml
[21] Credo, 2026-09-01 https://finance.yahoo.com/markets/stocks/articles/credo-technology-group-holding-ltd-050030303.html
[22] Digitimes(제목만), 2026-07-14 https://www.digitimes.com/news/a20260714PD223/sic-price-substrate-silicon-demand.html
[23] NVIDIA, 2025-05-20 https://developer.nvidia.com/blog/nvidia-800-v-hvdc-architecture-will-power-the-next-generation-of-ai-factories/
[24] GEV, 2026-07-23 https://www.turbomachinerymag.com/view/ge-vernova-gas-turbine-backlog-hits-116-gw-as-power-orders-more-than-double
[25] Siemens Energy, 2026-08-10 https://www.utilitydive.com/news/siemens-gas-turbine-backlog-nears-70-gw-as-company-expands-manufacturing/827390/
[26] MHI, 2026-08-13 https://www.utilitydive.com/news/mitsubishi-gas-turbine-backlog-earnings/827761/
[27] POWER(WoodMac 데이터), 2026-01-02 https://www.powermag.com/transformers-in-2026-shortage-scramble-or-self-inflicted-crisis/
[28] Vertiv, 2026-07-29 https://investors.vertiv.com/news/news-details/2026/Vertiv-Reports-Strong-Second-Quarter-2026-with-Diluted-EPS-Growth-of-53-Adjusted-Diluted-EPS-Growth-of-60-Raises-Full-Year-2026-Guidance-Across-All-Key-Metrics/default.aspx
[29] Advantest, 2026-07-29 https://www.advantest.com/document/en/investors/ir-library/result/JE_BIZ_260729_note.pdf
[30] FormFactor, 2026-07-29 https://finance.yahoo.com/markets/stocks/articles/formfactor-q2-earnings-call-highlights-220357627.html
[31] Soitec, 2026-08-31 https://www.globalbankingandfinance.com/soitec-locks-customers-multi-year-deals-ai-wafer-demand/
[32] Tom's Hardware, 2026-03-31 https://www.tomshardware.com/tech-industry/semiconductors/the-global-helium-shortage-is-a-direct-threat-to-chipmaking
[33] ChemAnalyst, 2026-09-30 https://www.chemanalyst.com/NewsAndDeals/NewsDetails/us-helium-market-remains-supply-constrained-amid-qatar-44769
[34] TrendForce, 2026-04-24 https://www.trendforce.com/news/2026/04/24/news-japan-photoresist-suppliers-flag-shortage-amid-40-middle-east-naphtha-reliance-risks-for-chipmakers/
[35] BigGo, 2026-09-24 https://finance.biggo.com/news/cad4ed4c-464b-4ee4-8233-9110fab547d6
[36] Murata, 2026-07-31 https://corporate.murata.com/-/media/corporate/about/newsroom/news/irnews/irnews/2026/0731d/26q1-e-speach.ashx
[37] Vishay, 2026-08-05 https://ir.vishay.com/news-releases/news-release-details/vishay-intertechnology-reports-second-quarter-2026-results · 콜 https://www.fool.com/earnings/call-transcripts/2026/08/12/vishay-vsh-q2-2026-earnings-call-transcript/
[38] Silicon Motion, 2026-07-30 https://siliconmotiontechnologycorporation.gcs-web.com/news-releases/news-release-details/silicon-motion-announces-results-quarterly-period-ended-june-30
[39] Reuters/Yahoo, 2025-11-10 https://finance.yahoo.com/news/china-suspends-ban-gallium-germanium-111120281.html
[40] Rinnovabili, 2026-09-25 https://www.rinnovabili.net/policy-and-affairs/environmental-policies/chinese-rare-earth-exports-trump-xi-truce/
[41] Intel, 2026-07-23 https://d1io3yog0oux5.cloudfront.net/_c348c7c46c1f6cb83c19e66e1c989d69/intel/db/887/9266/prepared_remarks/Q2+2026+Prepared+Remarks.pdf
[42] Tom's Hardware, 2026-04-24 https://www.tomshardware.com/pc-components/cpus/shifting-need-for-cpus-in-ai-workloads-drives-intensifying-shortages-price-hikes
[43] TrendForce, 2026-08-04 https://www.trendforce.com/presscenter/news/20260804-13166.html
[44] BigGo(Hoya IR 요약), 2026-07-31 https://finance.biggo.com/news/ir_7741.T_20260731_4f11eec74fb5
[45] TrendForce/Semiconductor Today, 2026-06-04 https://www.semiconductor-today.com/news_items/2026/jun/trendforce-040626.shtml
[46] TrendForce, 2026-02-05 https://www.trendforce.com/news/2026/02/05/news-wds-2026-production-fully-booked-ltas-reportedly-extend-to-2028-29-with-supply-talks-to-2030/
[47] Benzinga, 2026-07-28 https://www.benzinga.com/markets/tech/26/07/60732385/western-digital-stock-drops-what-is-going-on
[48] Futurum, 2026-03-02 https://futurumgroup.com/insights/nvidias-4b-optics-bet-signals-photonics-as-ais-next-bottleneck/
[49] Semiconductor Today(Lumentum), 2026-08-19 https://www.semiconductor-today.com/news_items/2026/aug/lumentum-190826.shtml
[50] TrendForce Insights, 2026-04-30 https://insights.trendforce.com/p/glass-fiber-cloth-shortage

### C-출처 — 과거 사례 보고서

**출처:** [1](https://www.fool.com/investing/2026/02/10/how-high-can-micron-go-in-the-memory-supercycle-he/) [2](https://www.trendforce.com/presscenter/news/20161003-9539.html) [3](https://www.fool.com/investing/2018/01/04/micron-stock-is-not-as-cheap-as-it-looks.aspx) [4](https://www.cnbc.com/2018/05/31/morgan-stanley-downgrades-micron-due-to-storm-clouds-on-the-horizon.html) [5](https://www.uncoveralpha.com/p/every-memory-cycle-ends-the-same) [6](https://www.macrotrends.net/stocks/charts/MU/micron-technology/stock-price-history) [7](https://www.cnbc.com/2023/05/24/nvidia-nvda-earnings-report-q1-2024.html) [8](https://www.cnbc.com/2023/05/25/nvidia-on-track-for-record-high-driven-by-ai-chip-demand.html) [9](https://www.aljazeera.com/economy/2024/6/19/nvidia-becomes-worlds-most-valuable-company-dethroning-microsoft) [10](https://www.tomshardware.com/news/tsmc-shortage-of-nvidias-ai-gpus-to-persist-for-15-years) [11](https://www.fool.com/investing/2025/03/07/nvidia-stock-down-27-from-peak-history-says-this/) [12](https://www.cnbc.com/2024/03/01/super-micro-joining-sp-500-after-20-fold-jump-in-stock-in-two-years.html) [13](https://www.aol.com/super-micro-stock-had-wild-193718721.html) [14](https://ir.supermicro.com/news/news-details/2024/Supermicro-Announces-Pricing-of-Public-Offering-of-Common-Stock/default.aspx) [15](https://www.benzinga.com/news/24/08/40230388/super-micro-shows-margin-weakness-despite-strong-ai-demand-analyst) [16](https://stocktwits.com/news-articles/markets/equity/super-micro-stock-tumbles-on-auditor-resignation/cJ2xRerRBP) [17](https://www.macrotrends.net/stocks/charts/VRT/vertiv-holdings/stock-price-history) [18](https://www.fool.com/investing/2023/03/02/heres-why-vertiv-is-a-no-brainer-growth-stock/) [19](https://www.trefis.com/stock/vrt/articles/616802/what-did-vertiv-say-before-its-stock-took-off/2026-09-28) [20](https://www.forbes.com/sites/petercohan/2025/01/23/vertiv-stock-soared-10462---project-stargate-may-send-it-higher/) [21](https://finance.yahoo.com/news/vertiv-holdings-co-vrt-stock-015637247.html) [22](https://www.globenewswire.com/news-release/2024/01/29/2819464/0/en/Celestica-Announces-Fourth-Quarter-2023-Financial-Results.html) [23](https://companiesmarketcap.com/celestica/stock-price-history/) [24](https://www.thestreet.com/investing/stocks/celestica-craters-by-10b-after-earnings) [25](https://www.macrotrends.net/stocks/charts/AAOI/applied-optoelectronics/stock-price-history) [26](https://www.sec.gov/Archives/edgar/data/1158114/000168316824007741/appliedopto_ex9901.htm) [27](https://finance.yahoo.com/news/applied-optoelectronics-stock-soars-amazon-113112413.html) [28](https://www.datacenterdynamics.com/en/news/shares-in-data-center-electric-cable-supplier-credo-halve-as-biggest-customer-cuts-orders/) [29](https://www.fool.com/investing/2024/12/03/why-credo-technology-rocketed-near-50-percent/) [30](https://www.macrotrends.net/stocks/charts/CRDO/credo-technology/stock-price-history) [31](https://companiesmarketcap.com/credo-technology/stock-price-history/) [32](https://finance.yahoo.com/markets/stocks/articles/credo-technology-crashed-3-months-115135647.html) [33](https://www.nasdaq.com/articles/lumentum-q4-revenue-and-margins-surge) [34](https://www.tikr.com/blog/lumentum-stock-soar-964-last-year-analysts-see-more-upside-in-2026) [35](https://www.investing.com/analysis/lumentums-1500-run-and-nvidias-2-billion-deal-what-comes-next-200678168) [36](https://www.tomshardware.com/tech-industry/semiconductors/lumentum-ceo-says-the-indium-phosphide-shortage-will-become-worse-than-memory) [37](https://companiesmarketcap.com/lumentum/stock-price-history/) [38](https://www.semiconductor-today.com/news_items/2025/nov/axt-101125.shtml) [39](https://photoncap.net/p/axt-inc-axti-deep-dive-the-hidden) [40](https://finance.yahoo.com/markets/stocks/articles/drove-axt-axti-600-date-175954268.html) [41](https://www.semiconductor-today.com/news_items/2026/aug/axt-040826.shtml) [42](https://stockanalysis.com/stocks/axti/history/) [43](https://www.trendforce.com/news/2025/03/07/news-sandisk-to-raise-nand-prices-over-10-from-april-1-signaling-market-rebound/) [44](https://finance.yahoo.com/markets/stocks/articles/sandisk-stock-more-5-900-142100788.html) [45](https://www.tikr.com/blog/sandisk-stock-has-dropped-35-since-june-heres-where-the-stock-could-go-in-2026) [46](https://stockanalysis.com/stocks/sndk/history/) [47](https://www.trendforce.com/news/2025/09/15/news-western-digital-raises-hdd-prices-amid-soaring-demand-shipping-delays-of-up-to-10-weeks/) [48](https://finance.yahoo.com/markets/stocks/articles/hard-disk-drive-prices-rising-130002179.html) [49](https://www.macrotrends.net/stocks/charts/WDC/western-digital/stock-price-history) [50](https://companiesmarketcap.com/seagate/stock-price-history/) [51](https://s25.q4cdn.com/621799436/files/doc_financials/2026/q4/Q4-FY26-Prepared-Remarks.pdf) [52](https://247wallst.com/technology-3/2026/07/17/micron-technology-record-dram-pricing-meets-a-stock-in-retreat/) [53](https://finance.biggo.com/news/4ced9a5c-8fa3-4a1b-91f6-39971e1a5a08) [54](https://www.fool.com/investing/2026/07/03/why-micron-stock-skyrocketed-last-month-but-is-plu/) [55](https://www.benzinga.com/markets/tech/26/08/60911521/micron-bear-case-earnings-memory-downturn) [56](https://stockanalysis.com/stocks/mu/history/) [57](https://finance.yahoo.com/markets/stocks/articles/mu-stock-drops-hours-micron-222532422.html) [58](https://businessmodelanalyst.com/micron-contracts-price-ceiling-customer-deposits/) [59](https://newsletter.semianalysis.com/p/memory-mania-how-a-once-in-four-decades) [60](https://www.tikr.com/blog/wall-street-is-behind-on-bloom-energy-stock-the-2-8-gw-oracle-signal-they-missed) [61](https://companiesmarketcap.com/bloom-energy/stock-price-history/) [62](https://www.streetinsider.com/Analyst+Comments/Memory+-+Winter+is+Coming:+Morgan+Stanley+Downgrades+Micron+(MU)+to+EW+as+Supply+is+Catching+Up+To+Demand,+Prefers+Samsung+(SSNLF)/18807172.html) [63](https://www.ksat.com/business/2023/04/07/samsung-cutting-memory-chip-production-as-profit-slides/) [64](https://www.fool.com/investing/2017/08/04/why-applied-optoelectronics-inc-stock-is-plunging.aspx) [65](https://www.fool.com/investing/2018/11/19/why-nvidia-stock-tumbled-today.aspx) [66](https://www.fool.com/investing/2025/07/15/why-wolfspeed-stock-plummeted-94-in-the-first-half/) [67](https://en.wikipedia.org/wiki/Wolfspeed) [68](https://electronics360.globalspec.com/article/22519/wolfspeed-bankruptcy-signals-turning-point-in-global-sic-market) [69](https://www.semiconductor-today.com/news_items/2025/jun/renesas-230625.shtml) [70](https://www.cio.com/article/266552/it-organization-what-went-wrong-at-cisco-in-2001.html) [71](https://companiesmarketcap.com/ciena/stock-price-history/) [72](https://www.fool.com/investing/2017/07/09/micron-stock-looks-cheap-because-the-party-cant-la.aspx) [73](https://www.fool.com/investing/2026/08/04/micron-trades-at-just-5-times-forward-earnings-her/) [74](https://www.schaeffersresearch.com/content/bgs/2026/01/06/s-p-500-s-top-stock-of-2025-western-digital)
