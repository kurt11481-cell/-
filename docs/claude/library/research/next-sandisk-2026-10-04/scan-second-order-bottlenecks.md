# 다음 샌디스크 스캔 — 2차 병목 후보 (2026-10-04 KST)

> 조사 원본 — Next 샌디스크 수시 발굴 1회차(2026-10-04) 에이전트 보고서. 이 줄 외에는 원문 그대로. 등급 D, 가격·시총은 외부 참고값(키움 미대조). 판정·결론 기준은 `docs/claude/next-sandisk-scan-2026-10-04.md`(초안). 매매 근거 아님.

- 가격은 모두 **참고값**: Yahoo Finance 2026-10-02 종가 기준. YTD는 2025-12-31 종가 대비, '고점比'는 52주 고점 대비. 매매 판단 전에 키움 시세로 다시 확인해야 함.
- † = 시총 $5B 미만, (OTC) = 지표 종목(직접 후보에서 제외). 날짜는 별도 표기가 없으면 2026년.
- 인지도 기준(가격 기준으로만 판정): **혼잡** = YTD ≥ +100% 또는 고점比 -10% 이내 / **조정** = YTD > +25%이면서 고점比 ≤ -35% / **소외** = YTD ≤ +25% / 나머지는 **중간**.

## 1. 1차 병목별 4문항 요약

| 1차 병목 | ① 대체재 (공식 근거) | ② 상류: 새 병목이 되나? | ③ 풀리면 다음으로 막히는 곳 | ④ 아키텍처 전환 |
|---|---|---|---|---|
| DRAM·HBM | KV 캐시를 SSD로 넘기는 방식(NVIDIA ICMS, 2026 하반기 출시) [NVIDIA 01-05](https://nvidianews.nvidia.com/news/nvidia-bluefield-4-powers-new-class-of-ai-native-storage-infrastructure-for-the-next-frontier-of-ai). 수요가 NAND로 옮겨감: SNDK 데이터센터 매출 FY26 +437% [8-K 08-05](https://www.sec.gov/Archives/edgar/data/2023554/000162828026053346/sndkq4-26ex991xpressrelease.htm) | 장비·클린룸·기판. Intel CFO: "equipment, clean room space, and substrates" 투자 확대 [07-23](https://www.sec.gov/Archives/edgar/data/50863/000005086326000155/q226earningsrelease.htm) | 패키징·기판·테스트 → 전력 | SOCAMM(마이크론), MRDIMM(Rambus DDR5-9600 칩셋, RMBS +22%이지만 병목은 아님), CXL |
| NAND·eSSD | HDD도 부족해 테이프로 대체 가능. LTO 출하 1Q26 +57%였으나 원인은 40TB 신제품이라 대체 근거는 약함 [LTO Program 09-02](https://www.theregister.com/storage/2026/09/02/tape-still-isnt-dead-but-shipments-slipped-by-16-exabytes-in-2025/5293813) | NAND 장비·컨트롤러(SIMO +203%, 혼잡) | 확인 필요 | KV 캐시 SSD(ICMS 파트너: Dell·HPE·Pure(현 Everpure)·VAST 등) → P +109%, NTAP +111%로 혼잡 |
| HDD | QLC eSSD(샌디스크 경로, 이미 주가 반영) | 헤드·미디어·유리기판(Hoya, OTC, +3%). 부족하다는 공식 근거는 확인 필요 | 공급 대응: Toshiba가 FY2027까지 AI용 HDD 생산능력 2배(약 ¥600억) [TrendForce 10-02](https://www.trendforce.com/news/2026/10/02/news-toshiba-to-double-ai-data-center-hdd-capacity-by-fy2027-with-380m-expansion-as-ai-storage-demand-surges/) | HAMR(Mozaic) 전환 |
| CoWoS | OSAT(외주 패키징): ASE LEAP 매출 2026년 $3.5B 초과, 2027년 2배, EMIB와는 "zero-sum이 아님" [실적콜 요약 07-30](https://finmoconf.diveinvest.net/en/ase/2026-q2) | ABF 기판·T-glass. Nittobo는 3배 증설도 "부족"하다고 밝힘 [TrendForce 08-06](https://www.trendforce.com/news/2026/08/06/news-nittobo-raises-fy2027-net-profit-forecast-by-jpy-3b-no-further-t-glass-price-hikes-planned/) | 테스트(FormFactor 사상 최대 매출) | EMIB 병행, 패널 패키징(확인 필요) |
| InP 레이저·기판 | 실리콘포토닉스·구리 AEC(CRDO 등에 이미 반영) | InP 기판·인듐(중국이 공급 장악). Lumentum CEO: "InP 수급 갭이 DRAM·NAND보다 크다" [TrendForce 08-06](https://www.trendforce.com/news/2026/08/06/news-inp-shortage-emerges-as-ai-optical-interconnect-bottleneck/). MOCVD 장비(Aixtron, OTC, +115%) | 광섬유·커넥터(Corning 증설) | CPO·ELS. Lumentum이 ELS 첫 주문 수주 [8-K 08-11](https://www.sec.gov/Archives/edgar/data/1633978/000162828026055726/lite_ex991xq4fy26.htm) |
| 서버 CPU | Arm: 데이터센터 로열티 전년 대비 2배 이상 증가, Arm AGI CPU 출시 [6-K 07-29](https://www.sec.gov/Archives/edgar/data/1973239/000197323926000113/exhibit992fye27q130-junx26.htm) | Intel 3 공정 증설에 €50억, 기판·클린룸 투자 확대 [07-23](https://www.sec.gov/Archives/edgar/data/50863/000005086326000155/q226earningsrelease.htm) | DDR5 RDIMM(메모리 부족과 겹침) | 에이전틱 AI로 CPU 수요 증가(공식 수치는 확인 필요) |
| 가스터빈·변압기 | 왕복엔진·발전기. CAT 딜러 발전 부문 소매판매 +72%(3개월) [Ex99.2 08-04](https://www.sec.gov/Archives/edgar/data/18230/000001823026000040/ex992toformcat2q2026retail.htm). Wärtsilä 미국 데이터센터 누적 2.4GW, 790MW 건은 2028년 인도 [04-23](https://www.wartsila.com/media/news/23-04-2026-wartsila-continues-to-expand-its-data-center-footprint-with-new-790-mw-order-in-texas-the-next-data-center-alley-3744599) | 초내열합금 주조품(HWM 가스터빈 매출 +38%). 변압기는 수입 의존 약 80%, 전력용 변압기 30% 부족 [WoodMac 2025-08-13](https://www.woodmac.com/news/opinion/transformer-troubles-manufacturing-and-policy-constraints-hit-us-transformer-supply/) | 스위치기어, 가스 공급 | 800V DC(2027 Kyber, SST(고체 변압기) 검토, 파트너 Eaton·onsemi·Navitas 등) [NVIDIA](https://developer.nvidia.com/blog/nvidia-800-v-hvdc-architecture-will-power-the-next-generation-of-ai-factories/). 온사이트 발전 |
| 반도체 테스트 | 대체재 없음(테스트 횟수가 늘어남) | 프로브카드·소켓(FORM·COHU†, 혼잡) | 번인 테스트(AEHR†) | HBM·CPO 테스트. FormFactor: "HBM·CPO가 성장 견인" |
| 헬륨·포토레지스트 | 대체 원료 재인증에 약 1년이 걸려 단기 대체는 불가 [TrendForce 04-24](https://www.trendforce.com/news/2026/04/24/news-japan-photoresist-suppliers-flag-shortage-amid-40-middle-east-naphtha-reliance-risks-for-chipmakers/) | 카타르 헬륨은 일부만 재가동, 미국 시장은 여전히 빠듯함 [ChemAnalyst 09-30](https://www.chemanalyst.com/NewsAndDeals/NewsDetails/us-helium-market-remains-supply-constrained-amid-qatar-44769) | HBM 공정 화학품(BARC·SOH·임시접착제) | 확인 필요 |

## 2. 2차 병목 후보 10개

| # | 2차 병목 | 나온 질문 | 부족·수요 증거 (공식 출처 우선) | 공급 대응 시점 | 미국 상장 수혜 (시총·YTD·고점比, 참고값) | 인지도 |
|---|---|---|---|---|---|---|
| 1 | **가스터빈 대체 발전설비**(왕복엔진·대형 발전기·소형 터빈) | ①③ | GEV: 계약 물량 116GW(연말 125GW 이상 예상)인데 연간 생산은 20GW(3Q26) → 24GW(2028) → 30GW(2030). 약 5~6년치가 밀려 있음(계산) [GEV 07-22](https://www.sec.gov/Archives/edgar/data/1996810/000199681026000147/gevpressrelease2q26.htm). CAT 발전 매출 +29% [08-04](https://www.sec.gov/Archives/edgar/data/18230/000001823026000040/ex991toformcat2q2026earnin.htm). CMI 대기전력 수주 강세 [08-04](https://www.sec.gov/Archives/edgar/data/26172/000002617226000026/cmi2026q28-kex99.htm). GNRC 데이터센터 수주잔고 약 $1.6B [07-29](https://www.sec.gov/Archives/edgar/data/1474735/000143774926024731/ex_994826.htm) | 왕복엔진도 2028년 인도(Wärtsilä) | CAT $389B·+48%·-21% / CMI $73B·+4%·-28% / BKR $56B·+23%·-20% / GNRC $13B·+59%·-27% / FTAI $17B·-15%·-48% (FTAI Power $1.465B 계약 [07-29](https://www.sec.gov/Archives/edgar/data/1590364/000162828026050622/ftai6302026earningsrelease.htm)) / 지표: WRTBY(OTC) -11% | CAT 중간, **CMI·BKR·FTAI 소외** |
| 2 | **IGT(산업용 가스터빈) 고온부 초내열합금 주조·단조** | ② | HWM 가스터빈 매출 +38%, "고객들이 수요 전망을 다시 올리는 중", 2027년 설비투자 추가 증액 [08-06](https://www.howmet.com/press-release/2026-08-06/howmet-aerospace-reports-second-quarter-2026-results/). CRS: "IGT 신규 제작이 수요를 이끎" [07-30](https://www.sec.gov/Archives/edgar/data/17843/000001784326000028/a4q26earningspresentatio.htm) | 2027년 투자 → 2028년 이후(추정) | HWM $92B·+13%·-25% / CRS $19B·+23%·-38% / ATI $26B·+68%·-21% | **HWM·CRS 소외** |
| 3 | **중전압 배전·스위치기어** | ③④ | Powell 수주 $934M(+158%), 수주/매출 비율 3.0배, 수주잔고 $2.4B, 데이터센터 단일 건 $400M 초과 [08-03](https://www.sec.gov/Archives/edgar/data/80420/000008042026000103/ex991-powlq3xfy2026earning.htm). Eaton 미주 전기 부문 12개월 수주 +41%, 수주잔고 +33% [07-31](https://www.sec.gov/Archives/edgar/data/1551182/000155118226000027/etn06302026exhibit99.htm) | Powell 수주잔고 ≈ 연매출 1.9배(계산) | ETN $169B·+37%·-9% / POWL $7.1B·+85%·-40% / HUBB $25B·+7%·-16% | ETN 혼잡, **POWL 조정** |
| 4 | **T-glass(유리섬유 직물)·ABF 기판** | ② (CoWoS·서버 CPU 공통 상류) | Nittobo는 3배 증설도 "충분치 않다"고 밝힘 [08-06](https://www.trendforce.com/news/2026/08/06/news-nittobo-raises-fy2027-net-profit-forecast-by-jpy-3b-no-further-t-glass-price-hikes-planned/). Ibiden ¥5,000억 투자 [02-03](https://www.ibiden.com/company/2026/02/notice-regarding-capital-investment-plan-for-high-performance-ic-package-substrates.html). Intel도 기판 투자 확대 | FY2027(Ibiden 양산) ~ FY3/2029(Nittobo 3배) | 미국 상장 직접 수혜 없음. 간접 수혜: MKSI $19B·+75%·-38%("첨단 패키징 수주 급증" [08-05](https://www.sec.gov/Archives/edgar/data/1049502/000119312526335274/mksi-ex99_1.htm)) / TTMI $14B·+91%·-41%(데이터센터·네트워킹 +91% [08-06](https://www.sec.gov/Archives/edgar/data/1116942/000119312526336163/d132953dex991.htm)) / 지표: Ibiden(IBIDF) +264% | 일본은 혼잡, 미국 간접주는 조정 |
| 5 | **광섬유·광 커넥티비티** | ③④ | Corning 광통신 매출 +32%, 엔터프라이즈 +65%. NVIDIA와 미국 커넥티비티 생산능력 10배·광섬유 +50% 증설 합의, Amazon과 다년 공급계약 [07-28](https://www.sec.gov/Archives/edgar/data/24741/000002474126000253/glw-20260728xex99xq22026.htm) | 증설 시점은 확인 필요 | GLW $141B·+88%·-40% / 지표: PRYMY +46% | **조정** |
| 6 | **OSAT 2.5D 패키징·테스트** | ① | ASE: 장비가 거의 풀가동, 설비투자 +$2B [07-30](https://finmoconf.diveinvest.net/en/ase/2026-q2). Amkor 2분기 매출 사상 최대 $1.90B(+26%) [07-27](https://www.sec.gov/Archives/edgar/data/1047127/000104712726000043/amkr6302026erex-991.htm) | 2026~27 | ASX $124B·+195%·-1% / AMKR $14B·+42%·-42%(컴퓨팅 비중 22%뿐) | ASX 혼잡, AMKR 조정 |
| 7 | **프로브카드·테스트 소켓** | ②③ | FormFactor 매출 $258M(+32%) 사상 최대 [07-29](https://www.sec.gov/Archives/edgar/data/1039399/000103939926000030/ex9901-earningsreleasexq226.htm) | 확인 필요 | FORM $12B·+167%·-7% / TER $70B·+132% / COHU† +216% | 혼잡 |
| 8 | **데이터센터 냉각 설비·부품** | ④ | Modine 데이터센터 매출 +90%, "핵심 부품 부족"으로 생산 차질, 수주잔고 약 2배 [07-29](https://www.sec.gov/Archives/edgar/data/67347/000110465926088230/mod-20260729xex99d2.htm). Vertiv "일시적 공급망 정체" [07-29](https://www.sec.gov/Archives/edgar/data/1674101/000162828026050323/q22026exhibit991vrt07292026.htm). SPX 데이터센터 매출 생산능력을 약 $1.1B로 상향 [07-30](https://www.sec.gov/Archives/edgar/data/88205/000008820526000052/q22026pressrelease.htm) | Modine은 FY27 부품 물량 확보 협상 중. 부족한 부품 품목은 확인 필요 | NVT $27B·+66%·-8% / MOD $9.5B·+33%·-45% / SPXC $8.7B·-13%·-31% | NVT 혼잡, MOD 조정, **SPXC 소외** |
| 9 | **온사이트(BTM, 전력망 밖 자가발전)용 가스 공급** | ③④ | Williams가 BTM 프로젝트 5개에 $5.34B 합작투자(JV) 유치, BTM 수주잔고 6GW 이상 [07-13](https://www.sec.gov/Archives/edgar/data/107263/000119312526301533/d152507dex991.htm) | 프로젝트별(확인 필요) | WMB $86B·+17%·-12% / KMI $69B·+13% | 소외 |
| 10 | **헬륨·나프타 기반 공정소재** | ② | 일본 포토레지스트 5개사가 삼성·SK하이닉스에 공급 차질 경고 [04-24](https://www.trendforce.com/news/2026/04/24/news-japan-photoresist-suppliers-flag-shortage-amid-40-middle-east-naphtha-reliance-risks-for-chipmakers/). 카타르 헬륨은 일부만 재가동 | 카타르 정상화 시점은 확인 필요 | APD $62B·+12%(실적자료상 "헬륨 물량 개선" 수준 [07-30](https://www.sec.gov/Archives/edgar/data/2969/000000296926000034/exhibit99130jun26.htm)) / LIN $221B·+12% | 소외(단, 수혜와의 연결이 약함) |

## 3. 부족 근거는 강한데 주가가 덜 오른 후보 5개

| 종목 (시총·YTD·고점比) | 2차 병목 | 가장 중요한 증거 | 주요 위험 |
|---|---|---|---|
| **CMI** ($73B·+4%·-28%) | 가스터빈 대체(대기·주 발전기) | 8-K(08-04): "robust customer orders for standby power for data centers". 발전 부문(Power Systems) +19%, EBITDA 마진 24.5% | 매출 대부분이 트럭과 연동된 엔진·부품 사업. 2분기 EPS가 예상에 못 미쳤고 엔진 부문 마진이 12.5%로 떨어짐 [Benzinga 08-04](https://www.benzinga.com/markets/earnings/26/08/60920333/cummins-revenue-hits-record-but-higher-costs-drag-earnings) |
| **HWM** ($92B·+13%·-25%) | IGT 블레이드 | 가스터빈 +38%, 엔진 부문 EBITDA 마진 37.7%(+4.7%p) [08-06](https://www.howmet.com/press-release/2026-08-06/howmet-aerospace-reports-second-quarter-2026-results/) | 매출 주력은 항공. IGT 신규 수요는 터빈 제조사의 생산능력(GEV 2028년 24GW 등)에 묶여 있음 |
| **BKR** ($56B·+23%·-20%) | 소형 가스터빈(NovaLT) | NovaLT 76대(1.3GW) + Kodiak 1GW 수주. 산업·에너지기술(IET) 부문 수주 $7.1B(2배), IET 수주잔고 $37.1B로 사상 최대 [07-26](https://www.sec.gov/Archives/edgar/data/1701605/000170160526000021/earningsreleaseex991063020.htm) | 유전서비스 부문 매출 -5%. 대형 가스터빈 공급이 정상화되면 대체 수요가 둔화 |
| **POWL** ($7.1B·+85%·-40%) | 중전압 스위치기어 | 수주/매출 비율 3.0배, 수주잔고 $2.4B(+69%) [08-03](https://www.sec.gov/Archives/edgar/data/80420/000008042026000103/ex991-powlq3xfy2026earning.htm) | 초대형 수주에 의존해 분기 실적 변동이 큼. 석유화학·LNG 비중이 있음 |
| **GLW** ($141B·+88%·-40%) | 광섬유·커넥티비티 | NVIDIA와 커넥티비티 10배·광섬유 +50% 증설 합의 [07-28](https://www.sec.gov/Archives/edgar/data/24741/000002474126000253/glw-20260728xex99xq22026.htm) | $2B 규모 시장 직접 유상증자(ATM)로 지분 희석, 대규모 증설 뒤 공급과잉 가능성 [Fool 09-14](https://www.fool.com/investing/2026/09/14/why-corning-plunged-today/) |

**주의:** CMI·HWM·BKR(그리고 FTAI·GNRC)는 모두 같은 핵심 논지(가스터빈 부족)에 기대고 있음. 종목을 나눠도 같은 논지에 걸린 위험은 분산되지 않음. 고위험 대안으로는 FTAI(-15%·-48%)가 있으나 신사업 실행 위험이 큼.

## 4. 비교 기준 (YTD / 고점比)

MU +277%/-14 · SNDK +625%/-27 · STX +208%/-26 · WDC +141%/-48 · LITE +194%/-1 · COHR +83%/-23 · AXTI +425%/-40 · AAOI +232%/-51 · CRDO +52%/-29 · ALAB +111%/-30 · GEV +51%/-17 · BE +233%/-18 · VRT +56%/-34 · INTC +223%/-16.
참고로 MU의 FQ4 매출은 $54.2B, 매출총이익률 87% [09-30](https://www.sec.gov/Archives/edgar/data/723125/000072312526000018/a2026q4ex991-pressrelease.htm). 1차 병목은 이미 가격에 강하게 반영됨.

## 5. 리스크·미검증

- 2차 병목주 상당수가 5~6월 고점 이후 큰 폭으로 하락했음(7/1 이후 -15~-50%):
  - 7/28: AI 공급망 종목 동반 급락(밸류에이션 재조정, 금리 부담) [aizigoo](https://aizigoo.com/en/now/ai-infrastructure-stocks-july-2026-selloff-outlook)
  - 9/14: AI 연구소 CEO들의 '프런티어 개발 속도 조절' 발언 이후 반도체·AI주 하락 [tradersagency](https://tradersagency.com/blog/ai-and-chip-stocks-slide-after-amodei-urges-slower-frontier-ai-development-with-altman-and-musk-backing-him)
- 공급 대응이 상승 여력의 상한이 됨: Toshiba HDD 2배(FY2027), Nittobo 3배(FY3/2029), GEV 30GW(2030).
- 확인 필요:
  - HDD 헤드·미디어 부족에 대한 공식 근거
  - 2026년 방향성 전기강판(GOES) 부족에 대한 공식 근거(CLF 2분기 실적자료에는 언급 없음)
  - Modine이 말한 '핵심 부품'의 구체적 품목
  - Corning 증설 시점
  - ASE 수치의 IR 원문 확인
- 이 문서는 분석 자료이며 주문·수량 권한이 없음(Execution-Authority: NONE). 개별 매매 전에 키움 시세, 최신 뉴스, 기술적 근거를 따로 확인해야 함.
