# 다음 샌디스크 스캔 — 전력·비AI 뿌리 병목 (2026-10-04 KST)

> 조사 원본 — Next 샌디스크 수시 발굴 1회차(2026-10-04) 에이전트 보고서. 이 줄 외에는 원문 그대로. 등급 D, 가격·시총은 외부 참고값(키움 미대조). 판정·결론 기준은 `docs/claude/next-sandisk-scan-2026-10-04.md`(초안). 매매 근거 아님.

> 시세·시총: Yahoo Finance 2026-10-02(금) 종가 **참고값**(키움 미검증)[49]. YTD = 2025-12-31 종가 대비, 고점대비 = 52주 장중 고점 대비. 시총 = 종가 × SEC 공시 주식수(근사, "~"는 추정). 비교 기준: SPY +12.9%, SOXX +95.6%(고점 -10%), SNDK +625%. 리서치 스캔이며 매매 지시가 아님.

## 0. 결론 3줄

- 가격결정력이 지금 공급자 쪽으로 넘어간 곳: **실리콘 전력반도체**(인피니언 "할당 중", ST 올해 3차 인상, 리드타임 최대 52주)[1][2], **초합금·정밀주조**(ATI "수요가 가용 공급 초과", GE가 주조사 CPP를 $117.5억에 인수)[15][12], **우라늄 전환·농축**(미국 유일 전환공장, 전환 현물 $64.50/kgU)[20][19].
- 부족은 가장 확실하지만 미국 상장 순수 수혜주가 없는 곳: **대형 변압기·부싱**(리드타임 30~36개월, 수요 80%+ 수입)[6] → OTC 지표·GEV(혼잡)뿐. **병목 아님**: SiC 기판(중국발 공급과잉)[4]. SST는 배치가 2028년 말 이후[3].
- 덜 반영 후보: **CRS·SOLS·ON**(가격 전환 증거 있음) + **CW·CLF**(비AI 뿌리의 구조적 희소성, 가격 전환 증거는 약함). 공통 반론: 전력·원전 종목 다수가 4~7월 고점 뒤 30~45% 조정 중이라 "소외"가 아니라 "하락 추세"일 수 있음.

## 1. 구간별 (a) 부족 증거 · (b) 공급 대응 · (c) 가격결정력 · (f) 수요 뿌리

| 구간 | (a) 지금 부족한 증거 | (b) 증설 → 완화 시점 | (c) 가격결정력 | (f) 수요 뿌리 |
|---|---|---|---|---|
| ① 800V DC·SST·SiC/GaN·전력모듈 | 인피니언(8/5) "AI 전력 수요가 공급 초과, 할당 중", 고객과 다년 용량예약 진행, 4월 인상 효과 반영[1] · ST 4/26·6/28·8/23 3차 인상, 전력소자 리드타임 30주+(일부 52주), 인피니언 7월 +10~20%[2] · 온세미 CFO(9/16) "2차 가격 인상 중", 가동률 68%→83%[3] · **반대**: 중국 6인치 SiC 웨이퍼 $400~500→$200~300[4] | 인피니언 드레스덴 팹 램프[1] · 온세미: 800V 랙 12~18개월 내 램프, **SST 배치 2028년 말~2029년 초**[3] · 이튼-인피니언 SiC 기반 SST 협력(9/29)[5] → 완화 시점 확인 필요 | 실리콘 전력소자 제조사(인피니언·ST·온세미). SiC 기판은 구매자 우위 | AI DC 주도 + 자동차·산업 |
| ② 전력망(변압기·차단기·케이블) | NREL(DOE 연구소, 2026-05): 대형변압기 리드타임 30~36개월(초고압 최대 60개월), 부싱 최대 130주, OLTC 80~90주, 수요 80%+ 수입, 2025년 단가 2019년 대비 +50~70%, GOES 국내 생산은 클리프스 1곳·고급재 약 90% 수입[6] · 우드맥(2025-08-14): 전력변압기 30%·배전 10% 공급 부족, 제약은 2030년대까지[7] | 히타치에너지 VA $4.57억(2028), 지멘스에너지 NC(2027 초), 이튼 SC $3.4억(2027)[8] · 클리프스 GOES +25%는 2028[9] · GEV 전력망 장비 잔고 $406억[10] → **2028 이후 일부 완화** | 변압기 OEM(히타치·지멘스에너지·프롤렉GE=GEV·한국 업체). GOES는 수입재가 가격 상단을 정함(추정) | AI DC + 노후 교체(매년 약 170대 설계수명 도달[6]) + 전기화 → 비AI 비중 큼 |
| ③ 가스터빈 상류(블레이드·단조·초합금) | GE에어로(9/8) CPP $117.5억 인수, "필수 주조 능력" 확보 목적[12] · 스페이스X 블레이드·베인 자체 주조 발표, 정밀주조 가능 업체 세계 3~4곳[13] · 하우멧 Q2 가스터빈 매출 +38%, "extraordinary"[14] · ATI(8/6) "A&D 소재 수요가 가용 공급 초과", 잔고 $44억(+18%)[15] · 카펜터: 엔진사들이 "수요보다 생산능력이 문제"라고 함[16] | GEV 터빈 연 20GW(2026 3Q)→24GW(2028)→30GW(2030)[10] · 카펜터 애선스 +9,000t은 FY2028 초[16][18] · CPP 인수 종결 2027년 하반기[12] → **2028년 전후까지 타이트** | 주조사(하우멧·PCC·CPP)·초합금 용해사(ATI·카펜터). 고객이 공급사를 사들일 만큼 공급자 우위 | 상업항공·국방 주도 + 가스터빈(AI 전력) → **AI 단일 뿌리 아님** |
| ④ 원전 연료(농축·HALEU)·SMR | 카메코: 6/30 전환 현물 $64.50/kgU, 장기 $55.50[19] · 솔스티스 메트로폴리스 = 미국 유일 UF6 전환[20], Q2 원자력 매출 +27%(가격+물량)[21] · 센트러스(8/5) "공급 제약 지속, SWU 가격 상승 압력", 잔고 $45억, DOE HALEU $9억 계약[23] · 러시아산 LEU 수입 면제 2028-01-01 종료[24] | 우렌코USA +70만 SWU(2025~27), 추가 최대 210만 SWU는 미확정[25] · 센트러스 오크리지 신형 원심분리기 1호 2026년 말[23] · 솔스티스 2026년 UF6 1만t+, 증설안 "수개월 내" 발표[20][22] → **2028~2030년대 초** | 소수 과점: 농축(우렌코·오라노), 전환(카메코·오라노·솔스티스). SMR 개발사는 구속력 있는 고객 약정 부족[26] | 에너지 안보·러시아 제재 주도(비AI) + AI 전력 계약 보조 |
| ⑤ 수동부품(MLCC·저항·인덕터) | 무라타 4~6월 분기 수주 사상 최고, B/B 1.34, 데이터센터 매출 +81%[27] · 비셰이 Q2 수동부품 B/B 1.40, 잔고 6.1개월[28] · 야게오 7/1 MLCC·탄탈 등 광범위 인상(공식가 약 50%, 보도)[29] | 무라타 설비투자 2,550억 엔(DC용 소형·고용량)[27]; 증설 폭·시점 확인 필요. 무라타 스스로 "공급 제약 대비 선주문 가능성" 언급[27] | 무라타·삼성전기·야게오 | AI 서버 집중 |
| ⑥ 핵심광물·특수가스 | **헬륨**: 카타르(세계 약 1/3) 3월 피격·생산 중단, 현물 약 2배[30], 9월 현재도 감산 가동[32]; 러시아 헬륨 수출통제(4/14)[31]; 9/28 호르무즈 물동량 전쟁 전보다 크게 낮음, 카타르 LNG 불가항력 11~12월 초까지 연장[32] · **텅스텐**: APT 1월 $900~940→2월 중순 $1,650~1,900/mtu[33], 알몬티 "역사적 고점"[34] · **희토류**: 2025-04 7종 허가제 유지(미국향 이트륨 333t→17t)[35]; 10월 조치 유예 2026-11-10까지[36]; Ga·Ge·Sb 대미 금수 유예 2026-11-27까지[37]; 9/28 상무부 "대미 무역합의 2027-01-10까지 연장"(희토류 명시 없음, 확인 필요)[38] | 헬륨: 호르무즈 재개 전 해소 어려움, 날짜 미정[32] · 텅스텐: 알몬티 상동 가공공장 7/1 가동·램프 중[34], 신규 광산은 최대 10년[33] · 안티몬: 퍼페추아 착공, 생산 개시일 확인 필요[39] | 중국 정책·카타르/러시아가 가격 결정, 서방 상장사는 가격 수취자. MP는 Q2 가격보전 수입 $1,760만[40] → 시장가가 정부 하한 아래로 추정 | 지정학·국방 주도(비AI) |

## 2. (d) 미국 상장 수혜 종목 · (e) 인지도 — 참고값

| 구간 | 종목 | 시총 | YTD | 고점대비 | (e) 인지도(가격 기반 추정) |
|---|---|---|---|---|---|
| ① | ON 온세미 | $33.1B | +56.8% | -37.1% | 부분 반영. 투자자의 날(9/16) -9% 뒤 10/2까지 +27% 반등 |
| ① | STM | ~$50.9B | +120.7% | -29.7% | 혼잡 |
| ①⑤ | VSH 비셰이 | ~$5.2B | +163.5% | -45.0% | 혼잡 후 조정 |
| ② | HUBB 허벨 | $25.1B | +7.1% | -15.9% | 소외. 그리드 인프라 +12%[11], 희소성 증거는 약함 |
| ② | CLF 클리프스 | $6.5B | -14.8% | -32.2% | 소외 |
| ② | POWL 파월 | $7.1B | +84.5% | -40.2% | 혼잡 후 조정 |
| ③ | CRS 카펜터 | $19.3B | +23.4% | -37.9% | 소외(7월 CEO 사망·교체 후 조정[42]) |
| ③ | ATI | $26.2B | +67.7% | -21.0% | 부분 반영 |
| ③ | HWM 하우멧 | $92.2B | +12.8% | -25.4% | 인지도 높음, 9월 초 스페이스X·GE-CPP 발표 전후 -11%(9/4→9/8) |
| ④ | SOLS 솔스티스 | $9.2B | +18.8% | -36.5% | 소외(원자력이 냉매 사업에 가려짐) |
| ④ | BWXT | $12.4B | -22.0% | -44.2% | 소외. 잔고 $84억(+39.6%)[41], 정부 계약이라 가격결정력 제한 |
| ④ | CW 커티스라이트 | $20.2B | -1.0% | -32.5% | 소외 |
| ④ | CCJ 카메코 | $37.1B | -6.9% | -37.0% | 인지도 높음·조정 |
| ⑥ | APD 에어프로덕츠 | $61.8B | +12.4% | -11.8% | 소외. 7/30 실적 발표문에 카타르·헬륨 가격 언급 없음, 헬륨 매출 비중 확인 필요 |
| ⑥ | MP | $8.4B | -7.0% | -53.1% | 2025-10 급등 후 소외 |
| 비교 | GEV / BE / VRT / PWR | $263B / ~$82B / $97B / $102B | +51% / +233% / +56% / +60% | -17% / -18% / -34% / -14% | 혼잡(비교 기준) |

## 3. 최종 후보 — 부족 근거는 강한데 주가가 덜 오른 곳

등급: A = 가격 전환 증거 있음, B = 구조적 희소성은 있으나 가격 전환 증거 약함.

| # | 종목 | 등급 | 가장 중요한 증거 1개 | 주요 위험 1개 | 뿌리 |
|---|---|---|---|---|---|
| 1 | **CRS** 카펜터 | A | 엔진사들이 "수요보다 생산능력이 문제"라 하고, 대형 장기계약 갱신이 진행 중(향후 2년 재가격 기회)[16]; 분기 영업이익 $2.07억 사상 최고, SAO 이익률 37.8%(서차지 제외)[17] | 항공·국방 매출 집중(FY26 65.6%, 2차 출처[42]), 일부 고객 "수요 이하 주문"[16]; 애선스 증설 FY2028 | 항공·국방 + 가스터빈 |
| 2 | **SOLS** 솔스티스 | A- | 미국 유일 UF6 전환공장[20], Q2 원자력 매출 +27%가 가격·물량 동시 상승[21] | 원자력은 매출의 약 11%($1.25억/$11.48억)[21] — 주가 약세 요인은 냉매 전환·비용발 마진 압박[21][43] | 에너지 안보 |
| 3 | **ON** 온세미 | B+ | CFO "고객 대상 2차 가격 인상 중", 가동률 83%[3]; 업계는 할당 단계[1] | 인상이 "원가 상쇄" 성격이고 가동률 여유 → 메모리식 초과이익은 미확인; 자동차 수요 | AI DC + 자동차·산업 |
| 4 | **CW** 커티스라이트 | B | DOE, AP1000 최대 10기에 $175억 조건부 융자(6/23)[44], CW "올해 AP1000 수주 기대"[45]; AP1000 냉각재펌프 공급 실적(2016년 중국 16대 $4.5억+)[46] | 최종투자결정·수주 지연 시 공백. 단독 공급 여부·가격 전환은 확인 필요 | 원전·해군(비AI) |
| 5 | **CLF** 클리프스 | B- | NREL: 미국 유일 GOES 생산자, 대형변압기 리드타임 30~36개월[6] | 고급 GOES 약 90% 수입이 가격 상단을 막음[6]; 스테인리스·전기강판 매출은 Q2 $5.25억으로 회사 전체의 일부[47] — 주가는 자동차용 강판 중심 본업 경기에 좌우 | 전력망(비AI) |

**이미 반영된 혼잡 종목**: GEV·BE·VRT·PWR(비교 기준) · STM(+121%)·VSH(+164%)·무라타 MRAAY(+167%)·다이요유덴 TYOYY(+195%) — 전력반도체·수동부품은 상반기에 먼저 급등한 뒤 30~50% 조정 · ATI(+68%)·POWL(+85%)·LFUS(+81%) · CF(+49%, 호르무즈 비료 충격 반영).

**$5B 미만(별도 표시)**: LEU 센트러스(~$3.1B, YTD -42.6%, 고점 -70%) — SWU 부족의 가장 직접 수혜이나 9/9 $5억 증자(주식·선행워런트 약 251만 주 + 보통워런트 약 699만 주)[48] 뒤 -23%(9/9→10/2 종가) · ALM 알몬티(~$3.5B, +52.1%, -45.1%) — 텅스텐 · PPTA 퍼페추아(~$2.5B, -15.8%) — 안티몬, 생산 전 · NVTS(~$3.0B, +73.7%, -63.7%) — 800V GaN, 부족이 아닌 수요 기대 · KN(~$3.4B, +86.9%) — 특수 커패시터.

**OTC 지표 종목(매수 대상 아님)**: 인피니언 IFNNY(+66.1%, -29.3%) · 무라타 MRAAY · 히타치 HTHIY(+14.1%) · 지멘스에너지 SMEGF(+22.2%) · 프리즈미안 PRYMY(+45.8%) · 미쓰비시중공업 MHVYF(+0.4%).

## 4. 반론·미검증

- "덜 오름"의 상당 부분은 고점 이후 조정이다(CRS·ON·SOLS·CW 모두 고점 대비 -32~-38%). 추세 전환 확인 전에는 현금·기존 감시 종목 대비 우위를 단정할 수 없다.
- 샌디스크형 급등은 희소 품목이 매출 대부분일 때 나왔다. SOLS(원자력 약 11%)·CLF(전기강판 일부)·CW(잔고형)는 탄력이 약할 수 있다.
- 고객의 수직계열화(GE→CPP, 스페이스X 자체 주조)는 단기엔 희소성 증거지만, 장기적으로는 독립 주조·소재사의 가격결정력을 깎는 위험이다.
- 확인 필요: SWU 가격 수치(업계 지표는 유료라 공식 확인 불가), 무라타 증설 폭, 야게오 인상률(보도), CW 냉각재펌프 단독 공급 여부, LEU·ALM 증자 후 주식 수, 퍼페추아 생산 개시일, 희토류 유예 연장(2027-01-10)의 적용 범위.

## 참조

1. Infineon Q3 FY26 애널리스트 콜 발표문 (2026-08-05) https://www.infineon.com/row/public/documents/corporate/investors/presentations/2026/2026-08-05-q3-fy26-intro-statement-analyst-call-v01-00-en.pdf
2. TrendForce, ST 3차 인상·리드타임 52주 (2026-08-21) https://www.trendforce.com/news/2026/08/21/news-stmicroelectronics-plans-third-2026-price-hike-for-august-23-power-device-lead-times-reportedly-hit-52-weeks/
3. onsemi Investor Day 녹취 (2026-09-16) https://stockanalysis.com/stocks/on/transcripts/612251-investor-day-2026/
4. The Economy, 중국 SiC 웨이퍼 가격 (2026-06-28) https://economy.ac/news/2026/06/202606289269
5. Semiconductor Today, 이튼-인피니언 SST (2026-09-29) https://www.semiconductor-today.com/news_items/2026/sep/infineon-290926.shtml
6. NREL, 대형 전력변압기 공급망 격차 분석 (2026-05) https://docs.nlr.gov/docs/fy26osti/96742.pdf
7. Wood Mackenzie 보도자료 (2025-08-14) https://www.woodmac.com/press-releases/power-transformers-and-distribution-transformers-will-face-supply-deficits-of-30-and-10-in-2025/
8. POWER Magazine (2026-01-02) https://www.powermag.com/transformers-in-2026-shortage-scramble-or-self-inflicted-crisis/
9. Cleveland-Cliffs Q2 2026 콜 녹취 (2026-07) https://stockanalysis.com/stocks/clf/transcripts/651809-q2-2026/
10. GE Vernova Q2 2026 보도자료 (2026-07-22) https://www.gevernova.com/sites/default/files/gev_webcast_pressrelease_07222026.pdf
11. Hubbell Q2 2026 실적 (SEC, 2026-07-28) https://www.sec.gov/Archives/edgar/data/48898/000162828026049934/exhibit991_07282026.htm
12. GE Aerospace, CPP 인수 보도자료 (2026-09-08) https://www.geaerospace.com/news/press-releases/ge-aerospace-acquire-consolidated-precision-products-cpp-expanding-mission-critical
13. Turbomachinery Magazine (2026-09-11) https://www.turbomachinerymag.com/view/ge-aerospace-cpp-acquisition-spacex-turbine-blade-foundry
14. Howmet Q2 2026 실적 (2026-08-06) https://www.howmet.com/wp-content/uploads/sites/3/2026/08/Howmet-Aerospace-Reports-Second-Quarter-2026-Results.pdf
15. ATI Q2 2026 실적 (2026-08-06) https://www.prnewswire.com/news-releases/ati-announces-second-quarter-2026-results-302844440.html
16. Carpenter FY26 Q4 콜 녹취 (2026-08-04 게시) https://www.fool.com/earnings/call-transcripts/2026/08/04/carpenter-technology-crs-q4-2026-earnings-call-transcript/
17. Carpenter FY26 Q4 실적 (SEC, 2026-07-30) https://www.sec.gov/Archives/edgar/data/17843/000001784326000030/a4thqtr2026resultspressrel.htm
18. Zacks/Yahoo, 카펜터 증설 (2026-08) https://finance.yahoo.com/markets/stocks/articles/crss-brownfield-expansion-project-aid-141300914.html
19. Cameco Q2 2026 MD&A (2026-07) https://www.cameco.com/sites/default/files/documents/2026-Q2-MDA-FS-Notes_0.pdf
20. Solstice 보도자료, 전환 증산 (2026-02-10) https://www.solstice.com/us/en/resources/press-releases/2026/02/solstice-advanced-materials-announces-expansion-of-uranium-conversion-production-to-support-strong-nuclear-industry-customer-demand
21. Solstice Q2 2026 실적 (SEC, 2026-07-30) https://www.sec.gov/Archives/edgar/data/2064953/000206495326000085/exhibit991-earningsrelease.htm
22. Solstice Q2 2026 콜 녹취 (2026-08-04 게시) https://www.fool.com/earnings/call-transcripts/2026/08/04/solstice-advanced-materials-sols-q2-2026-earnings-call-transcript/
23. Centrus Q2 2026 실적 (SEC, 2026-08-05) https://www.sec.gov/Archives/edgar/data/1065059/000162828026053433/ex991-10q2026_08x05.htm
24. World Nuclear News, 러시아 LEU 면제 절차 (2024-05-23) https://world-nuclear-news.org/Articles/DOE-unveils-process-for-Russian-LEU-import-waivers
25. Urenco USA (2026-04-02) https://www.urenco.com/news/usa/2026/urenco-usa-reaches-half-way-point-of-current-u.s-capacity-expansion
26. Motley Fool, SMR 종목 (2026-09-27) https://www.fool.com/investing/2026/09/27/nuclear-stocks-have-crashed-in-2026-heres-the-1-th/
27. Murata FY2026 Q1 실적 발표 (2026-07-31) https://corporate.murata.com/-/media/corporate/about/newsroom/news/irnews/irnews/2026/0731d/26q1-e-speach.ashx
28. Vishay Q2 2026 실적 (2026-08-05) https://ir.vishay.com/news-releases/news-release-details/vishay-intertechnology-reports-second-quarter-2026-results
29. TrendForce, 야게오 인상 (2026-07-01) https://www.trendforce.com/news/2026/07/01/news-passive-component-prices-rise-as-yageo-reportedly-begins-broadest-capacitor-hike-in-years-on-july-1/
30. AGBI, 카타르 헬륨 (2026-03) https://www.agbi.com/industry/2026/03/qatar-lng-halt-sends-helium-prices-higher/
31. The Moscow Times, 러시아 헬륨 수출통제 (2026-04-14) https://www.themoscowtimes.com/2026/04/14/russia-introduces-helium-export-restrictions-amid-global-shortage-a92496
32. The National, 카타르 LNG 불가항력 연장 (2026-09-28) https://thenationalnews.com/business/energy/2026/09/28/qatar-extends-lng-force-majeure-as-hormuz-disruption-threatens-winter-supply
33. Fastmarkets, 텅스텐 2026 (2026, 2월 중순 가격 기준) https://www.fastmarkets.com/insights/tungsten-2026-geopolitics-sets-global-tone/
34. Almonty 보도자료 (SEC, 2026-07-14) https://www.sec.gov/Archives/edgar/data/1670061/000149315226033123/ex99-1.htm
35. TechTimes, 희토류 4월 통제 (2026-05-26) https://www.techtimes.com/articles/317208/20260526/china-rare-earth-export-controls-april-curbs-still-bite-after-beijing-summit.htm
36. Global Times, 중국 상무부 통제 유예 (2025-11) https://www.globaltimes.cn/page/202511/1347625.shtml
37. Yahoo Finance, Ga·Ge·Sb 금수 유예 (2025-11-10) https://finance.yahoo.com/news/china-suspends-ban-gallium-germanium-111120281.html
38. RawMaterials.net, 대미 무역합의 연장 (2026-09-28) https://rawmaterials.net/rare-earth-export-controls-china-confirms-extension-of-trade-arrangements-with-u-s/
39. Perpetua 건설 현황 (2026-08-31) https://www.prnewswire.com/news-releases/perpetua-resources-provides-construction-update-on-the-stibnite-gold-project-and-exploration-activities-302864546.html
40. MP Materials Q2 2026 실적 (2026-08-06) https://s25.q4cdn.com/570172628/files/doc_financials/2026/q2/Release-Q2-2026-MP-Earnings-FINAL.pdf
41. BWXT Q2 2026 실적 (2026-08-03) https://investors.bwxt.com/news-releases/news-release-details/bwx-technologies-reports-second-quarter-2026-results
42. TS2, 카펜터 CEO 사망·사업 구성 (2026-07, 2차) https://ts2.tech/en/carpenter-technology-nysecrs-drops-5-in-premarket-after-ceos-passing-highlights-challenges-for-aerospace-business/
43. Quiver, 솔스티스 하락 사유 (2026-05-06) https://www.quiverquant.com/news/Solstice+Advanced+Materials+falls+as+investors+focus+on+softer+full-year+revenue+outlook+and+margin+pressure
44. Cameco, DOE AP1000 공급망 융자 (2026-06-23) https://www.cameco.com/media/news/us-department-of-energy-to-jumpstart-nuclear-supply-chain-and-accelerate-deployment-of
45. Curtiss-Wright Q2 2026 콜 녹취 (2026-08) https://www.fool.com/earnings/call-transcripts/2026/08/12/curtiss-wright-cw-q2-2026-earnings-call-transcript/
46. Curtiss-Wright, AP1000 냉각재펌프 계약 (2016-01-05) https://curtisswright.com/news/press-releases/news-release-details/2016/Curtiss-Wright-Awarded-Contracts-in-Excess-of-450-Million-to-Provide-Reactor-Coolant-Pumps-for-AP1000-Nuclear-Power-Plants-in-China
47. Stainless Steel Club, 클리프스 스테인리스·전기강판 매출 (2026-08-01) https://www.stainless.club/industry-news/read/Cleveland-Cliffs-electrical-steel-revenues-rise-as-Butler-Works-expansion-advances.html
48. Centrus 증자 가격 확정 (2026-09-09) https://www.prnewswire.com/news-releases/centrus-announces-pricing-of-500-million-underwritten-public-offering-of-class-a-common-stock-and-warrants-302874493.html
49. 시세: Yahoo Finance 차트 데이터(2026-10-02 종가) / 주식 수: SEC EDGAR XBRL 최신 10-Q·10-K·20-F·40-F 표지(다종 주식·증자 종목은 가중평균 기본주식으로 근사)
