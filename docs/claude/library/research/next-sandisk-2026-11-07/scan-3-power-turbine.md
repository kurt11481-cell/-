# 다음 샌디스크 스캔 3 — 전력·변압기·가스터빈 상류·온사이트 발전 (2026-11-07 KST)

**쓰는 법**: 조사용 자료이고 매매 권고가 아니다(order_authority=false). 주가·시총은 stockanalysis.com 캐시 스냅샷으로 **참고값**이다. 종목마다 기준 시각이 10/23~10/30으로 다르고, 일부는 장중 가격이며, 여러 회사는 실적 발표 **전** 가격이다. 연초 대비 수익률(YTD)은 어느 페이지에도 나오지 않아 전부 **확인 필요**로 둔다. 52주 고점 대비 수치는 내가 직접 계산했다.

## 0. 한 줄 결론
- **부족이 가장 강하게 입증된 곳**은 가스터빈과 그 상류 주조다. GEV 가스 백로그+슬롯은 122GW이고, HWM 경영진은 주요 터빈 고객의 2031년 생산능력이 매진됐다고 말했다. 그 다음이 배전·스위치기어다(POWL 수주 +158%, ETN 전력 백로그 +46%).
- **10월에 업종 전체가 크게 빠졌다.** HWM −37%, CRS −56%, POWL −52%, CW −42%, ON −47%(52주 고점 대비). 그래서 "덜 오른" 후보는 많다. 다만 이번 하락의 원인은 이 조사에서 **확인하지 못했다**.
- **800V DC·SST·SiC/GaN은 아직 '부족' 단계가 아니다.** NVIDIA 공식 일정이 2027년(Kyber)이고, Navitas는 본격 확대를 2027년 말~2028년 초로 본다. 2027-06-30 이내에 점화될 가능성은 낮다.
- **EO 14420은 광범위한 수입 금지가 아니다.** 대상은 제재 대상국 등 '대상 외국 실체'와 69kV 이상 대량전력계통이다. 국내 업체의 수혜 규모는 **확인 필요**다.

## 1. 구간별 증거

### (1) 800V DC·SST·SiC/GaN
| 항목 | 내용 |
|---|---|
| (a) 부족 증거 | **약함.** NVIDIA는 800VDC 전면 생산이 "2027년 Kyber와 함께" 시작된다고 밝혔고, SST는 아직 "평가 중"이다([NVIDIA 블로그 2025-05-20, 07-31 갱신](https://developer.nvidia.com/blog/nvidia-800-v-hvdc-architecture-will-power-the-next-Generation-of-ai-factories)). Navitas 3분기 매출은 $14.0M(전년 대비 +38%), 4분기 가이던스는 $16.0M이다. 회사는 백로그가 2027년 중반까지 차 있고 수주/출하 비율이 1을 크게 넘는다고 밝혔다([NVTS 11/03](https://www.globenewswire.com/news-release/2026/11/03/3394777/0/en/navitas-semiconductor-announces-third-quarter-2026-financial-results.html)). onsemi의 AI 데이터센터 매출은 전년 대비 +175%다([ON 11/02](https://finviz.com/news/413565/onsemi-reports-third-quarter-2026-results)). POWI 3분기 매출은 전년 대비 +6%에 그쳤고 보도자료에 800VDC 언급이 없다([POWI 8-K 11/04](https://www.sec.gov/Archives/edgar/data/0000833640/000083364026000152/powi-20261104xexx991.htm)). Wolfspeed 매출은 $155M으로 전년 $196.8M보다 줄었고 비GAAP 총마진은 −13%다([WOLF 8-K 11/04](https://www.sec.gov/Archives/edgar/data/0000895419/000089541926000075/ex991q1-27.htm)). |
| (b) 공급 일정 | Navitas는 800V '사이드카' 랙이 2027년 상반기에 늘어나고, 네이티브 800V는 2027년 말~2028년 초에 가속된다고 본다([TIKR 정리](https://www.tikr.com/blog/navitas-is-73-off-its-high-tuesdays-report-has-to-put-the-power-wall-in-revenue), 2차 출처). Enphase SST의 대량 공급은 2028년 목표다([pv-magazine 헤드라인](https://pv-magazine-usa.com/?p=20319), 본문은 확인 필요). |
| (c) 가격결정력 | 아직 수요자 쪽(NVIDIA·전원 공급장치 업체)에 있다. NVIDIA 파트너 목록에 10곳 이상의 실리콘 업체가 올라 있어 희소성이 낮다. |
| (e) 인지도 | NVTS는 고점 대비 −74%다. 기대가 꺼진 상태이고 혼잡하지 않다. |

### (2) 변압기·스위치기어·배전 + EO 14420
| 항목 | 내용 |
|---|---|
| (a) 부족 증거 | **ETN**: 매출 $8.9B(+28%, 유기 +19%), Electrical Americas 12개월 이동평균 수주 +39%, 전력 부문 백로그 +46%(Global +121%)([ETN 8-K 11/03](https://www.sec.gov/Archives/edgar/data/0001551182/000155118226000037/etn09302026exhibit99.htm)). **HUBB**: Electrical Solutions 유기 성장 +22%, 데이터센터 매출 +80% 초과. 2027년 가격 인상을 11월부터 앞당겨 적용한다([HUBB 8-K 10/27](https://www.sec.gov/Archives/edgar/data/0000048898/000162828026067421/exhibit991_10272026.htm), [Utility Dive](https://www.utilitydive.com/news/data-center-purchases-of-electrical-equipment-up-80-since-2025-hubbell/873134/)). **POWL**(FY26 3분기, 8/3 발표): 수주 $934M(+158%), 백로그 $2.4B(+69%), 수주/출하 비율 3.0배, 데이터센터 온사이트 발전용 $400M 초과 메가 수주([POWL 8-K](https://www.sec.gov/Archives/edgar/data/0000080420/000008042026000103/ex991-powlq3xfy2026earning.htm)). **NVT**: 연간 가이던스를 상향해 보고 기준 성장률 48~49%([Finsee](https://finsee.ai/earnings/nvt/2026/q3/en/), 2차 출처). 업계 전반: 대용량 변압기 리드타임은 최대 4년(PwC)이고, 2019~2025년 승압변압기 수요는 +274%다(WoodMac)([pv-magazine 2026-05-11](https://pv-magazine-usa.com/2026/05/11/u-s-transformer-market-faces-severe-supply-constraints-as-lead-times-extend-to-four-years/)). |
| (b) 공급 일정 | Hitachi Energy 사우스보스턴 공장은 **2028년** 가동, Siemens 샬럿 공장은 시점 미공개(같은 pv-magazine 기사). HUBB는 증설 투자를 분기 $25M에서 $50M으로 늘리고 2027년에 $200M을 투자한다. POWL Jacintoport 야드 확장은 FY2026 말 완료 예정이다. **해석: 2027-06-30 이전에 공급이 풀린다는 근거는 없다.** |
| (c) 가격결정력 | 공급자 쪽이다. HUBB는 가격 인상을 앞당겼다. 다만 ETN 보도자료에는 가격 관련 수치가 없다. |
| EO 14420 | 2026-08-26 서명. DOE 시행규칙 기한은 약 **2026-12-24**이지만 "필요에 따라"라는 단서가 있어 한꺼번에 나오지 않을 수 있다. FAR 권고 기한은 **2027-02-22**. RFI 의견 마감은 10/09였다. 대상은 69kV 이상 대량전력계통과 '대상 외국 실체'(22 CFR 126.1의 제재 대상국 등)다([Willkie](https://www.willkie.com/publications/2026/09/executive-order-14420-restricts-foreign-equipment-in-the-us-bulk-power-system), [DWT](https://www.dwt.com/blogs/energy--environmental-law-blog/2026/09/doe-bulk-power-rfi-guidance)). 한국·멕시코산 변압기가 규제 대상이라는 근거는 **없다**. |

### (3) 가스터빈과 상류 주조·초합금
| 항목 | 내용 |
|---|---|
| (a) 부족 증거 | **GEV**: 가스 백로그+슬롯 예약이 122GW(백로그 64GW + 슬롯 58GW, 슬롯은 확정 주문이 아님)이고, 연말 130GW 이상을 예상한다. Power 수주 +178%, 전체 백로그 $197B([GEV 10/28 8-K](https://www.sec.gov/Archives/edgar/data/0001996810/000199681026000162/gevpressrelease3q26.htm)는 직접 열리지 않아 [Turbomachinery 10/29](https://www.turbomachinerymag.com/view/ge-vernova-q3-2026-gas-power-backlog-122-gw-trench-acquisition)로 확인). **HWM**: 가스터빈 매출 +45%, 2025년 대비 2배 목표를 3년 안으로 앞당김, 2030년 약 $2.5B 가능성 제시. "주요 터빈 고객의 2031년 생산능력이 매진됐다", "GE용 증설 설치에 2년이 걸린다"는 발언도 있었다([Zacks 콜 요약](https://www.zacks.com/stock/news/3019674/hwm-q3-earnings-call-highlights-a-longer-gas-turbine-runway), 2차 출처이며 실적 원고 원문은 확인 필요). **ATI**: specialty energy 매출 $80.4M(전년 $53.9M), 장기공급계약과 가격 인상, EBITDA 가이던스 상향([ATI 10/29](https://s27.q4cdn.com/226628310/files/content_files/FINAL-Q3-2026-Press-Release-10-28-26-_1_.pdf)). **CRS**: "가격이 계속 강해지고 있다", SAO 마진 37.7%. 다만 **에너지 최종용도 매출은 $42.5M에서 $32.9M로 줄었다**([CRS 10/22](https://s21.q4cdn.com/563831349/files/doc_earnings/2027/q1/earnings-result/Press-Release-Q127.pdf)). 따라서 CRS를 터빈 수혜주로 보기는 약하다. **CW**: 매출 +10%, 원자력 중심, 백로그 $4.6B([CW 11/04](https://www.sec.gov/Archives/edgar/data/0000026324/000162828026070580/ex991_cwxq326xearnings.htm)). 가스터빈과의 연결은 약하다. |
| (b) 공급 일정 | HWM은 신규 공장 7곳과 검토 중 3곳을 제시했지만 완공 날짜는 밝히지 않았다. CRS 브라운필드 확장은 FY2029 이익 목표에 기여한다고만 했다. 공급이 풀리는 시점은 **2027-06-30 이후**로 보인다. |
| (c) 가격결정력 | 1순위는 OEM(GEV, 슬롯 예약)이고, 그 다음이 단일 공급원 주조(HWM)와 초합금(ATI·CRS)이다. |

### (4) 온사이트 발전 대체재
| 항목 | 내용 |
|---|---|
| (a) 증거 | **BKR**: IET 잔여이행의무(RPO) 사상 최대 $39.4B, 수주/출하 비율 1.7, 미국 테크 기업용 1.1GW 수주(NovaLT·Frame 5 터빈 43기)와 데이터센터용 약 500MW 수주, Horizon 2 수주 목표 "$50B 이상"([BKR 10/27](https://s21.q4cdn.com/548121662/files/doc_earnings/2026/q3/earnings-result/Q3-2026-Earnings-Release.pdf)). **CAT**: 백로그 $78B(전년 대비 거의 2배), 발전 매출 +30%([Manufacturing Dive 10/29](https://www.manufacturingdive.com/news/caterpillar-posts-highest-sales-quarter-ever-data-centers-q3-2026/873176/)). **BE**: 매출 +138%, 연간 가이던스 $4.4~4.6B로 상향([BE 10/22](https://bloomenergy.com/news/bloom-energy-reports-record-third-quarter-2026-financial-results-and-raises-full-year-2026-guidance/)). **CMI**: Power Systems 매출 +15%, 마진 25.4%. 다만 **전사 매출 가이던스는 약 10%로 하향**했다([CMI 8-K 11/05](https://www.sec.gov/Archives/edgar/data/0000026172/000002617226000035/cmi2026q38-kex99.htm)). |
| (b) 공급 일정 | BE는 5GW 이후 확장을 말했지만 시점은 밝히지 않았다. CAT은 엔진·터빈 증설 중이라고만 했고 날짜가 없다. |
| (c) 가격결정력 | BE는 가격 강세가 마진에 기여했다고 밝혔다. 나머지는 확인 필요. |

## 2. 종목 지표 (참고값, 고점 대비는 내가 계산)
| 티커 | 시총 | 가격(기준일) | 52주 고점 대비 | 비고 |
|---|---|---|---|---|
| GEV | $225.9B | $857.87 (10/30) | 확인 필요 | 52주 +48.4% |
| CAT | $327.9B | $713.38 (10/28) | −33.5% | |
| ETN | $143.7B | $369.97 (10/30) | −22.6% | |
| VRT | $93.5B | $242.94 (10/28) | −36.1% | |
| HWM | $77.7B | $194.90 (10/27 장중) | −37.1% | |
| CMI | $71.9B | $522.13 (10/26) | −29.2% | |
| BE | $65.0B | $219.69 (10/27 장중) | −37.5% | 52주 +100% |
| BKR | $54.3B | $54.66 (10/28) | −22.4% | |
| ON | $27.9B | $71.67 (10/30) | −46.9% | |
| HUBB | $23.3B | $441.00 (10/27 장중) | −22.0% | |
| NVT | $22.7B | $140.12 (10/28) | −24.1% | |
| ATI | $22.4B | $164.54 (10/26) | −32.4% | |
| CW | $17.3B | $469.50 (10/26 장중) | −41.9% | |
| CRS | $13.7B | $276.50 (10/27 장중) | −55.8% | |
| POWL | $5.7B | $157.07 (10/26) | −52.1% | 2026-04-06 3:1 분할, 고점이 분할 조정가인지 확인 필요 |
| **$5B 미만** POWI | $2.6B | $46.98 (10/23) | −48.5% | |
| **$5B 미만** NVTS | $2.3B | $8.74 (10/27 장중) | −74.4% | TIKR 기준 YTD +12% |
| **$5B 미만** WOLF | $1.2B | $23.38 (10/26) | −71.1% | Chapter 11 졸업 후 |

**OTC 지표 종목**(이 조사에서 수치 미확인): Hitachi(HTHIY), Siemens Energy(SMNEY), ABB(ABBNY), Schneider(SBGSY).

## 3. 부족 근거는 강한데 덜 오른 후보 (가설, 매수 권고 아님)
| # | 티커 | 가장 중요한 증거 1개 | 주요 위험 |
|---|---|---|---|
| 1 | **HWM** | 터빈 고객의 2031년 생산능력이 매진됐다는 발언, 가스터빈 매출 +45% | 2차 출처(원고 원문 미확인), 항공 사이클, 밸류에이션 |
| 2 | **POWL** | 수주/출하 비율 3.0배, 백로그 $2.4B(+69%) | 덩어리 수주, 실적 후 급락 이력, FY26 4분기 실적 발표일 확인 필요 |
| 3 | **ATI** | specialty energy 매출 +49%, 장기계약 기반 가격 인상 | 신규 초합금 램프 비용, 항공 의존 |
| 4 | **BKR** | IET RPO $39.4B, 데이터센터 1.1GW 수주 | GTE 매출 −7%, Chart 인수 부채 |
| 5 | **HUBB** | 데이터센터 매출 +80%, 가격 인상 앞당김 | 유틸리티 부문 유기 성장 +5%로 둔화 |
| 6 | **NVT** | 연간 성장률 가이던스 37~39%에서 48~49%로 상향 | 2차 출처, 백로그 최신치 확인 필요 |
| 7 | **ON** | AI 데이터센터 매출 +175% | 자동차 비중, 800V 본격화는 2027년 이후 |
| 8 | **CRS** | 가격 강세, 마진 37.7% | 에너지 매출 감소. 터빈 수혜주가 아니라 항공주로 봐야 함 |
| 별도($5B 미만) | NVTS | 백로그 2027년 중반까지, 수주/출하 비율 1 초과 | 매출 $14M, 손익분기에는 분기 매출 $30M대 후반 필요, 2027-06 이내 점화 가능성 낮음 |

**혼잡 종목**(이미 반영된 쪽, 포지셔닝 자료는 없으므로 가설): **GEV**(52주 +48%, $226B), **BE**(52주 +100%), **CAT**($328B, 백로그 2배가 널리 알려짐), **VRT**($93.5B, 800V 대표주), **ETN**($144B).

## 4. 2027-06-30까지의 공식 일정상 촉매
| 시점 | 촉매 | 확실성 |
|---|---|---|
| 2026-11 (날짜 확인 필요) | POWL FY26 4분기 실적 | 중 |
| ~2026-12-24 | EO 14420 DOE 시행규칙 | 기한은 공식이나 단계적 발표 가능 |
| 2026년 4분기 | GEV 백로그 $200B 초과, 가스 130GW 이상 (회사 예상) | 중 |
| 2027-01~02 | 4분기 실적과 2027 가이던스 (HWM은 2027 매출 약 $11.5B 제시) | 높음 |
| 2027-02-22 | EO 14420 FAR 권고 기한 | 공식 |
| 2027년 상반기 | NVTS 800V 사이드카 램프 (경영진 예상) | 낮음~중 |
| 2027년 (구체 월 미공개) | NVIDIA Kyber와 800VDC 본격 생산 | 2027-06 이내인지 확인 필요 |
| 2028 | Hitachi 미국 변압기 공장 가동, Enphase SST 대량 공급 (공급 해소) | 범위 밖 |

## 5. 위험·미검증
- 주가 스냅샷은 기준일이 서로 다르고 실적 발표 전 가격이 섞여 있다. 키움 데이터는 사용하지 않았다. YTD와 GEV 52주 고점은 확인 필요다.
- 10월 급락의 원인(AI 설비투자 우려인지, 금리인지)은 확인하지 못했다. 원인에 따라 "덜 오름"이 "thesis 훼손"일 수 있다.
- GEV와 HWM 8-K 원문은 SEC 접근 오류로 열지 못했고 2차 기사로 대체했다.
- **이 판단을 바꿀 증거 1줄**: 4분기 실적에서 GEV 슬롯이 확정 주문으로 전환되는 속도가 꺾이거나, HWM이 2027 가스터빈 가이던스를 낮추면 터빈 상류 후보는 철회한다.
