---
id: cyber-lead-1128
type: proposal
status: current (사장 결정 2026-11-28 13:26 KST — PANW·NET·NTSK 등록, 8절)
as_of: 2026-11-28 10:20 KST (주간 재채점 11/28 실행 전 명단 기준)
summary: "사장 지시 '다음 주도주 사이버 보안주를 미리 발굴' — 커뮤니티 글 4건은 가설로만 쓰고, SEC 실적 보도자료로 후보를 거른 뒤 관심 명단 '채점 후보(candidates)' 등록 제안. 매수·주문·관심 편입 판단 아님."
consumers: "사장 결정 카드 → 등록 세션(watchlist-registry.json candidates) → 관심 명단 주간 재채점(trig_01MuMHqXHrRAeNVZt2ZjzRxu, 토 10:20) → 교체 규칙 → 새 관심 카드 → (별도) 상품 승인 K3"
source_decision: "사장 직접 입력 2026-11-28 09:59:52 KST(cmsg_0137MRzn9nuDvvQmVxm6WeX9PQrMjJpPwD92jkQzj8sR2m)"
---

# 사이버 보안 주도주 후보 — 관심 명단 채점 후보 등록 제안 (2026-11-28)

## 0. 결론
- **PANW(팔로알토)·NET(클라우드플레어) 2종목을 관심 명단 '채점 후보'에 넣자**(권장). 둘 다 이번 분기 실적이 끝났고(다음 실적 2월 예상, 확인 필요), 공식 자료에서 매출 성장 가속 + 연간 가이던스 상향이 함께 확인된 유일한 두 종목이다.
- RBRK(루브릭)·NTSK(넷스코프)는 **다음 주 실적(11/30·12/2) 뒤 공식 수치로 다시 본다.** 지금 넣으면 넣자마자 낡은 수치가 된다.
- 기대 효과를 낮춰 잡는다: 등록은 '매주 같은 잣대로 재는 눈'을 만드는 일이다. 관심 5칸은 유지 보호 ⑧ 때문에 바로 비지 않을 수 있어 관심 편입은 늦을 수 있다(1절).
- 이것은 '채점 후보' 등록이다. 관심 편입·매수 승인·상품 승인이 아니다(active-decisions.md 229·248행 '관심 편입 ≠ 매수 승인'). 매수 시점 규칙은 다루지 않는다(같은 시각 '추세 전환 대비 매수 전략 보완' 스레드 범위).
- 기본값(답 없음): **NO_CHANGE** — 명단 그대로(CLAUDE.md Default disposition).

부딪히는 결정(지침 3절 검색 결과):
- 관심 명단 D1~D4(active-decisions.md 229행): 관심 5칸·주 1건 교체. → 이 제안은 members를 바꾸지 않는다. 후보 목록만.
- 주간 재채점 규칙(248행) · 지시문 5행 "후보 목록은 Cowork·사용자만 바꾼다" → 등록 경로는 사장 결정(10/10·10/17 선례: scn27h1-sector-discovery-2026-10-10.md 99·101행, history 2026-10-17 candidates-add).
- swing-k3-1120(176행): 스윙 상품 승인은 PLTR·CRWD뿐. 새 종목 상품 승인은 하지 않음 — 이 제안도 하지 않는다.
- crwd-zs-acq-1124(186행): ZS는 CRWD 인수 대상 → 후보에서 뺀다(4절).

## 1. 지금 명단 상태 (원문 확인 2026-11-28 10:1x KST, docs/claude/watchlist-registry.json)
- 관심(members) 5칸 꽉 참. 지금 점수(11/21 주간 실행 weeklyRun.memberData): MU 4(보호 중) · PLTR 5 · CRWD 6 · DELL 6 · PWR 6. (members의 score 칸 8·9·10·7·6은 편입 당시 점수라 비교에 쓰지 않는다.) 사이버 분야(N1)는 CRWD 1개.
- 채점 후보에 사이버는 S(센티넬원) 4점 1개.
- 분야당 관심 최대 2(지시문 5행 ④) → 사이버가 관심에 더 들어갈 수 있는 자리는 1칸.
- 교체 조건(지시문 5행 ③, 163행 기준선 = 최약 + 2): 지금 기준선 = MU 4 + 2 = 6점, 2주 연속, 대상 관심 종목 편입 28일 이상. MU는 보호 중(2027-02-20까지)이라 다음 대상은 PLTR(편입 11/07 → 12/05에 28일).
- 유지 보호 ⑧(지시문 5행): 대상 관심 종목의 S1+S2가 편입 때 이상이고 철회 기준 공식 확인이 없으면 교체 대신 '조정 중'으로 보호한다. 11/21 값으로 보면 다섯 종목 모두 S1+S2가 편입 때와 같아, 교체 대상이 되면 보호로 들어갈 가능성이 높다(코드와 11/21 값으로 추론 — 11/28 실행 기록 뒤 다시 확인 필요). 빈 칸이 생기면 6점 이상 최고점 후보가 들어오는데 지금은 AMD 7점이 앞이다.
- 오늘 10:20 주간 재채점(v3.6 첫 실행)이 예정돼 있으므로 이 문서는 명단 파일을 건드리지 않는다.

## 2. 커뮤니티 글 4건 — 가설 (지침 8절: 커뮤니티 = 가설, 증거 아님)
| 글(에펨코리아, 번역 게시) | 시각(게시판 표기) | 주장 |
|---|---|---|
| PBA "NET 사이버 보안 섹터가 주도 테마로 자리" | 2026-11-28 07:30 | NET 신규 매수($285.58, 쌍바닥·EMA20 회복·U&R). 돌파·쌍바닥 종목: NTSK·OKTA·S·RBRK. "다음 주 실적이 주도주 지위를 가를 것" |
| Oliver Kell "PANW 일부 물량 매수" | 2026-11-28 07:45 | PANW 일부 매수, 다음 주 추가 상승(Follow-through) 시 비중 확대 |
| Venu "사이버 보안 섹터 새 주도주 징후" | 2026-11-28 06:47 | OKTA 50일선 깃발 · PANW 비슷 · NTSK 컵 돌파 · SAIL IPO 베이스 돌파 시도 · TENB 2단계 |
| PBA "NTSK" | 2026-11-27 03:52 | 약세장에서 버팀, 반등장 오면 크게 오를 것. 최대 7~12% 담을 생각 |
- 공통점: 시장 조정 중 같은 업종 여러 종목이 동시에 상대 강세 → '주도 업종 후보' 가설. 차트 판단은 우리 점수표 S3(주도 신호)·S5(추세)가 키움 일봉으로 따로 잰다. 글의 가격·매수 기록은 쓰지 않는다.
- 반대 가설(10/10 발굴 문서 sector-nonai.md 70행): 이 업종은 고PER 장기 자산이라 금리 급등에 가장 약하다. 2026-02·04월 'AI가 보안을 대체' 우려로 급락한 전례.

## 3. 공식 자료로 거른 결과 (SEC 8-K 실적 보도자료 원문, 2026-11-28 10:0x KST 열람)
| 종목 | 최근 분기(발표일) | 매출 YoY | 직전 분기 YoY | 가속? | 연간 가이던스 | 수요 수치(S1 근거 후보) | 다음 실적 | 판정 |
|---|---|---|---|---|---|---|---|---|
| **PANW** | FQ1'27(11/18) | +39% | +34%(FQ4'26) | 예(인수 효과 섞임 ⚠) | 매출 $14.10~14.20B → **$14.52~14.57B 상향** | NGS ARR +66% $9.73B · RPO +35% $21.0B | 2월 예상(확인 필요) | **등록 권장** |
| **NET** | Q3'26(11/05) | +39% | +36%(Q2) | **예** | 매출 $2,864~2,870M → **$2,963~2,964M 상향** | 현재 RPO +37% | 2월 예상(확인 필요) | **등록 권장** |
| FTNT | Q3'26(10/28) | +20% | +26% | 아니오 | 매출 $8.02~8.18B → $8.125~8.215B 상향 | 제품 +37% · 빌링 +29% | 2월 예상 | 보류(성장 둔화) |
| RBRK | FQ2'27(8/27) | +38% | 확인 필요 | 확인 필요 | 전 지표 상향 | 구독 ARR +33% $1.66B | **11/30(보도 제목, 확인 필요)** | 실적 뒤 재검토 |
| NTSK | FQ2'27(9/02) | +29% | 확인 필요 | 확인 필요 | 확인 필요 | ARR +27% $899M | **12/02(보도 제목)** | 실적 뒤 재검토 · 시총 $5B 이상 확인 필요 |
| OKTA | FQ2'27(8/26) | +11% | 확인 필요 | — | FY27 +10~11% | cRPO +14% | 12/01(회사 공지) | 보류(저성장) |
| SAIL | FQ2'27(9/09) | +17% | 확인 필요 | — | FY27 매출 +18~19% | ARR +25% | 12/08 장 전(회사 공지) | 보류(저성장) |
| S | (이미 후보, 4점) | +21% | — | — | 상향(8/27) | ARR +22% | 12/03 장 후(회사 공지) | 그대로 |
| VRNS · RPD · CHKP | Q3(11/03 · 11/04 · 6-K) | VRNS +17%(매출 $189.5M) · RPD ARR $820M | — | — | — | — | — | 제외(저성장·소형, CHKP는 외국 발행사 6-K) |
| AKAM · GEN · FFIV · CVLT | — | — | — | — | — | — | — | 미검토(시총·성장 확인 필요) |
| ZS | FQ1'27(11/23) | +20% | — | — | — | ARR +21% | — | **제외 — CRWD 인수 대상**(인수가에 묶임, CRWD와 같은 뿌리) |
| TENB · QLYS | Q3(10/28 · 11/09) | +9.5% · +11% | — | — | 상향 | — | — | 제외(저성장, TENB 시총 $4.5B 10월 기준 미달 — 확인 필요) |
| CYBR | — | — | — | — | — | — | — | PANW 인수 완료(PANW 8-K 2026-11-18 주석 'our acquisition of CyberArk Software Ltd.'), SEC 티커 목록에 없음 |

PANW·NET 예비 점수(공식 자료로 셀 수 있는 칸만, 지시문 5행 R2.1):
- PANW: S1 = 사람이 고르는 유일한 칸. 보도자료 두 건에 유기(organic) 수치가 없어(원문 'organic' 0건) **'약'(1)으로 제안** — 수요 수치는 있으나 인수 효과와 분리 안 됨. S2 2는 python이 보고 수치(39 > 34, 연간 상향)로 계산하며 손으로 바꿀 수 없다(지시문 140행·5행 '루프가 바꾸지 않는다'). 인수 효과는 note에만 적는다. → 공식 칸 3점.
- NET: S1 2(현재 RPO +37%, 매출 가속) · S2 2 · 나머지 같음.
- NET: S1 강(2, 현재 RPO 35%→37%·매출 36%→39%) · S2 2 → 공식 칸 4점. S4(예상 PER ≤ 매출 YoY)는 PER을 null로 두므로 0.
- 가격 칸(S3 0~2·S5 0~1·S7 0~2)은 12/05 주간 실행이 키움 일봉으로 계산한다. 기준선 6점(1절)에 닿는 것은 PANW 가격 칸 3점 이상·NET 2점 이상이면 가능하지만, 관심 편입은 보호 ⑧과 빈 칸 순서(1절)에 달려 있다.

## 4. 등록 방법 (사장 카드 '등록' 뒤, 같은 회사PC 스레드 1세션)
1. 시점: 명단 파일 weeklyRun.date가 2026-11-28로 바뀐 것(오늘 주간 기록 끝)을 확인한 뒤, 같은 날 23:30 문서 커밋 전에만 편집한다. 카드 답이 다른 날 오면 다음 토요일 주간 기록 뒤로 미룬다(명단 파일을 커밋 없이 고치면 다음 자동 코어 실행의 매수 주문표가 모두 막힘 — 00-home.md 표). 편집 전 sha256 기록·저장 직전 재확인(CLAUDE.md 'Shared docs'). CRLF 유지.
2. (카드에서 '키움 조회 포함'을 고를 때만) kiwoom_query 일봉 읽기(options profile 실전계좌·mode real, confirm·주문 도구 없음)로 PANW·NET 기준 종가 1개씩 → inputs.close · inputs.mcapUsd = 발행주식 수 × 종가(PANW 821.0M주, SEC dei 2026-11-11 / NET은 10-Q 표지 A+B 합, 못 찾으면 8-K 가중평균 약 379M주로 근사 표기).
   - 키움 조회를 빼면: 점수는 매겨지지만 시총이 없어 '입장불가'로 남는다(지시문 154·160·165행, 알림 없음 304행). 그 경우 12/05 실행이 적은 detail.close·closeDate로 mcapUsd·close를 채우는 2차 편집을 같은 날 커밋 창에서 한다.
3. candidates 2행은 S 행(10/10 선례)과 같은 틀로 쓴다(빠지면 주간 실행 오류 또는 조용히 0점 — 지시문 130·139·140·146·289행):
   - 최상위: code · sector "N1 사이버보안 — 사용자 결정 2026-11-28 추가(F5 사용자 예외, 발굴 A1~A3 밖)" · score · items{S1,S2,S3,S4,S5,S7 정수 6칸, 가격 칸 0} · s1Basis(최상위, SEC URL 포함) · aboveStreak 0 · note(인수 효과·출처).
   - inputs: mcapUsd · close · guideRaised true(불리언) · s1 "약"(PANW) / "강"(NET).
   - detail: bm "SOXX" · yoy/prevYoy(PANW 39/34, NET 39/36) · pe null · reactDate "20261119"(PANW, 11/18 장 후 — 콜 4:30pm ET) · "20261106"(NET, 11/05 장 후 — 콜 5:00pm ET).
   - history: action candidates-add · in "PANW,NET" · by "user" 1줄(사장 카드 id·시각).
4. 주간 지시문은 바꾸지 않는다. 후보 추가는 279행 검증에 걸리지 않는다(검증은 그 실행이 읽은 파일 기준).
5. `_pending/cyber-lead-1128-reg.txt` + 결정 색인 1줄. 같은 날 주간 실행의 _pending 목록과 같은 파일이 겹칠 때 23:30 작업 처리는 확인 필요 — 등록 세션이 커밋 반영을 다음 날 확인한다.
- 부하: 주간 실행 키움 일봉 +2회. WebFetch 14회는 DUE 종목만 쓰므로 PANW·NET은 2월 실적 전까지 영향 없음.
- 2차 등록(RBRK·NTSK) 때 주의: sector 글자에 '스토리지'·'메모리'가 들어가면 사이클 의심 판단 보류(지시문 167행). NTSK는 일봉이 모자라면 가격 실패(104행) — 상장일 확인 필요.

## 5. 연결표 (analysis-linkage-map-2026-10-05.md 29~38행)
| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| 이 문서(후보 거르기 표) | 이 스레드, 2026-11-28 | 사장 결정 카드(이 스레드) | 등록 세션이 candidates 2행 추가 | 카드 무응답 → NO_CHANGE(CLAUDE.md Default disposition), 이 스레드가 열린 채 남음 | 연결 |
| watchlist-registry.json candidates PANW·NET | 등록 세션(카드 뒤, 4절) | 주간 재채점 trig_01MuMHqXHrRAeNVZt2ZjzRxu · watchlist-weekly-rescore.txt 5행(교체 규칙)·154·165행(시총·자격)·139~146행(채점) | 점수 → 빈 칸 채우기·교체(관심 편입) → 새 관심 카드 초안(미수락) | 주간 판단 보류 알림(327행). 단 후보의 가격 실패·입장불가는 알림이 없다(304·315행) → **이 스레드가 12/05 첫 실행 출력에서 PANW·NET 줄(입장불가 여부·S1·S2)을 확인**(12/05 알림 설정) | 연결 + 첫 실행은 사람 확인 1회 |
| 관심 편입 뒤 카드 수락 | 사장 결정 카드 | card-review-auto(active-decisions.md 65행), CLAUDE.md 'card-evidence-registry' 줄 | 매수 요건 행 생성(관심 member만) | 통합 점검 카드 낡음 줄 | 연결(기존 길) |
| 매수 주문표까지 | 사장 K3 상품 승인(별도) | 상품 승인 목록 APPROVED_BUY(manage-us-stock-strategy/scripts/auto_core_tickets.py 61·264행, swing-k3-1120 = active-decisions.md 176행) | 승인 상품만 주문표 | 상품 승인 없는 종목은 주문표가 안 나옴(통합 점검 표시 행은 확인 필요) | **끊김(메울 승인: 관심 편입·카드 수락 뒤 사장 K3 상품 승인 — 이 제안은 요청하지 않음)** |
| 다음 주 실적: RBRK 11/30 · NTSK 12/02 (OKTA 12/01 · SAIL 12/08은 저성장 보류) | 회사 공시 | 후보가 아닌 종목은 주간 재채점·통합 점검·공시 피드 어디도 안 봄. (S는 이미 후보라 주간 DUE 확인 86~87행이 읽음) | RBRK·NTSK 2차 등록 제안 | **이 스레드가 12/04 알림을 지금 걸어** SEC 8-K를 다시 연다 | 끊김 → 이 자리에서 메움(알림). 2차 등록은 다시 사장 카드 |

## 6. 바뀔 조건
- PANW 유기 성장(CyberArk 제외)이 직전 분기보다 낮으면 S2 가속 1점은 인수 효과 → 등록 세션에서 S2 1로 적는다.
- 다음 주 실적에서 RBRK·NTSK가 매출 가속 + 가이던스 상향이면 2차 등록 제안, 반대로 업종 다수가 가이던스를 낮추면 '주도 업종' 가설은 약해진다(등록 철회 제안 없이 주간 점수가 반영).
- 10년물 급등(SCN T1) 같은 금리 충격이면 이 업종이 먼저 깎인다(sector-nonai.md 70행).

## 7. 출처 (이 세션에서 연 원문)
- PANW 8-K 2026-11-18 https://www.sec.gov/Archives/edgar/data/1327567/000132756726000030/ex991q127earningsrelease.htm · 2026-09-01 …/000132756726000019/ex991q426earningsrelease.htm
- NET 8-K 2026-11-05 https://www.sec.gov/Archives/edgar/data/1477333/000147733326000060/q326exhibit991.htm · 2026-08-06 …/000147733326000053/q226exhibit991.htm
- FTNT 8-K 2026-10-28 https://www.sec.gov/Archives/edgar/data/1262039/000126203926000024/ftntq3-2026ex991.htm · 2026-07-29 …/000126203926000018/ftntq2-2026ex991.htm
- ZS 8-K 2026-11-23 https://www.sec.gov/Archives/edgar/data/1713683/000119312526470942/d255961dex991.htm
- RBRK 8-K 2026-08-27 https://www.sec.gov/Archives/edgar/data/1943896/000194389626000055/rubrikinc-991pressrelease7.htm
- NTSK 8-K 2026-09-02 https://www.sec.gov/Archives/edgar/data/2063196/000119312526380188/ntsk-ex99_1.htm
- OKTA 8-K 2026-08-26 https://www.sec.gov/Archives/edgar/data/1660134/000166013426000068/okta-7312026_ex991.htm
- SAIL 8-K 2026-09-09 https://www.sec.gov/Archives/edgar/data/2030781/000162828026061015/sailpointinc-20260731x991x.htm
- TENB 8-K 2026-10-28 https://www.sec.gov/Archives/edgar/data/1660280/000166028026000050/q32026financialresults-ear.htm · QLYS 8-K 2026-11-09 https://www.sec.gov/Archives/edgar/data/1107843/000110784326000043/qlys-20261109xex991.htm
- 실적 일정: OKTA https://finance.yahoo.com/markets/stocks/articles/okta-announce-third-quarter-fiscal-130000166.html · S https://www.financialcontent.com/article/bizwire-2026-11-12-sentinelone-announces-date-of-fiscal-third-quarter-2027-financial-results-conference-call-and-participation-in-upcoming-investor-conference · SAIL https://www.sailpoint.com/press-releases/sailpoint-fiscal-q3-2027-earnings-call · RBRK·NTSK는 검색 제목만(확인 필요)
- SEC 발행주식 수: data.sec.gov companyconcept dei/EntityCommonStockSharesOutstanding (PANW 821.0M · FTNT 734.7M · SAIL 570.9M)
- 저장소: watchlist-registry.json · scheduled-prompts/watchlist-weekly-rescore.txt 5·154·165·279·327행 · active-decisions.md 176·186·229·248행 · scn27h1-sector-discovery-2026-10-10.md 26·99·101행 · library/research/scn27h1-discovery-2026-10-10/sector-nonai.md 37~70행

검토 완결: 원문 확인 15/18(실적 일정 RBRK·NTSK, NET 주식 수 미확인) · 내장 재검토 1회(조언(Fable) 8건 — 결론 바뀜 1(기대 효과·교체 대상) · 정정 7 · 미반영 0, 작업자 약 183k 토큰·7분) · 미해결 3 · 자료 시점 SEC 8-K ~2026-11-23, 명단 파일 2026-11-28 10:1x KST · 바뀔 조건 6절

## 8. 사장 결정과 반영 (2026-11-28)
- **13:26 KST 사장 직접 입력**(cmsg_0137MRzn9nuDvvQmVxm6WeX9TNB5FHty7QsptAHndJRfE9): "panw, net, ntsk 를 사이버보안 채점 후보로 등록해줘". 카드(cmsg_0137MRzn9nuDvvQmVxm6WeX9DNGUptrdJ7AvvYnLjcyavo)의 2종목 안에 NTSK를 더한 글 답. 키움 조회 언급이 없어 **'등록만(키움 조회 없음)'**으로 처리.
- 반영 13:3x KST: 주간 재채점 11/28 기록(weeklyRun.date 2026-11-28, action none, _pending/watchlist-weekly-2026-11-28.txt) 뒤 watchlist-registry.json candidates에 3행 + history candidates-add(by user) 1줄. 그 밖 변경 없음(편집 전 sha256 247bebfdc923 → 뒤 ab74ee27390d, 편집 전 파일 대비 추가만).
- 초기 점수(공식 칸만): PANW 3(S1 약·S2 2) · NET 4(S1 강·S2 2) · NTSK 3(S1 약 — ARR 29%→27% 둔화, S2 2 — 매출 28%→29%, FY27 매출 가이던스 $879~883M → $888~892M 상향, 8-K 2026-06-03·09-02). reactDate PANW 20261119 · NET 20261106 · NTSK 20260903(모두 장 후 발표).
- NTSK는 12/02 실적 예정이라 주간 DUE 확인(지시문 86~87행)이 12/05에 새 분기를 읽는다. 시총 $5B·일봉 253개는 확인 필요 — 못 미치면 주간 python이 자격 없음·가격 실패로 둔다.
- 남은 일: 12/05 첫 주간 실행 뒤 detail.close·closeDate로 inputs.mcapUsd·close 2차 편집(그 전까지 세 종목 입장불가). RBRK는 11/30 실적 뒤 12/04 재검토.

## 9. 이번 주 수동 채점 (2026-11-28 14:3x KST)
- 사장 직접 입력 14:28 KST "PANW·NET·NTSK 세종목을 요번주만 주간 재채점에 포함해서 지금 채점 해줘" + 14:29 KST 결정 카드 '키움 읽기 조회 허용'(cmsg_0137MRzn9nuDvvQmVxm6WeX99ataAFkPb5ZLZQnu1e5rHZ). 예약 지시문·예약 실행은 건드리지 않고, 같은 계산(watchlist-weekly-rescore.txt 98~149행)을 이 스레드에서 돌렸다.
- 키움 일봉(overseas candles stock-daily, 수정주가, pages 3, 300봉, 최신 20261127) 4건: PANW · NET(NYSE) · NTSK · SOXX. SOXX 60세션 −20.2%.

| 종목 | 종가(11/27) | 252세션 고점 대비 | 60세션 | EMA50 대비 | 실적 반응 10세션 | S1 | S2 | S3 | S4 | S5 | S7 | 합계 | 시총 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PANW | 369.00 | −12.1% | +12.3% | +4.2% | +8.6%(잠정, 반응일 11/19 뒤 5세션) | 1 | 2 | 2 | 0 | 1 | 2 | **8** | $302.9B |
| NET | 296.10 | −18.0% | +8.6% | −1.9% | +12.5% | 2 | 2 | 1 | 0 | 0 | 2 | **7** | $106.1B |
| NTSK | 28.75 | 0.0%(신고가) | +109.1% | +33.4% | +27.2% | 1 | 2 | 2 | 0 | 1 | 2 | **8** | $11.7B |
- 시총 = 주식 수 × 11/27 종가: PANW 821.0M(SEC dei 11/11) · NET 358.4M(10-Q 표지 10/22 A+B) · NTSK 408.6M(10-Q 표지 8/25 A+B). 셋 다 $5B 이상·$1T 미만 → 입장 조건 충족.
- 기준선 = 최약 MU 4 + 2 = 6 → 세 종목 모두 aboveStreak 1로 적음(사장 결정 '이번 주 포함'). 이번 주 관심 편입·교체는 하지 않음(정기 실행 10:20 끝).
- 12/05 정기 실행에서 2주 연속이 성립할 수 있다. 다만 MU는 보호 중이고, 다음 대상 PLTR(5점, 12/05에 편입 28일)은 S1+S2가 편입 때 이상이면 교체 대신 보호가 시작된다(유지 보호 ⑧) — 실제 결과는 12/05 실행이 정함(확인 필요). 사이버 칸은 CRWD 포함 최대 2.
- 주의: PANW S7은 잠정(10세션 전). NTSK는 12/02 실적 뒤 S1·S2·S7이 다시 잰다. PER(S4)은 비워 0점.
- 명단 파일 sha256 ab74ee27390d → cc6fe60a1ee4, 세 행과 history candidates-score 1줄만 바뀜.

## 10. 관심 명단 교체 기록 — CRWD·MU → PANW·NTSK (2026-11-28 15시대 KST)

- 사장 결정: 2026-11-28 14:50 KST 결정 카드 'PANW·NTSK를 넣으면서 관심 명단에서 어떤 종목을 뺄까요?' → 'CRWD·MU 빼기'(사장이 직접 누름, cmsg_0137MRzn9nuDvvQmVxm6WeX9JUxZkfJ9ZXBo9wPrqrsKW3). 발단 사장 직접 입력 14:47 KST "그때 까지 기다리면 너무 늦어. 추세 전환을 가정했을때 이미 가격이 많이 오른 후 일수 있다. panw, ntsk를 바로 매수 후보로 올릴 방법 찾아".
- 바뀐 것(명단 파일 sha256 cc6fe60a1ee4 → 33eaf0eef4b7): members MU → PANW(1번 칸), CRWD → NTSK(5번 칸). MU·CRWD는 후보 끝으로(점수·detail은 11/28 주간 memberData 값, MU capExempt 유지). history swap 2줄(by "user" — 실행당 1건 한도에 세지 않음). weeklyRun: MU 보호 ended(사용자 결정 관심 제외), memberData·weakest를 새 명단으로 맞춤(최약 PLTR 5, 기준선 7), userEdit 기록 1칸. N1 분야 관심 2종목이 차서 NET·S·CRWD 후보는 sectorFull.
- 새 카드: docs/claude/watch-card-PANW-2026-11-28.md(v1, 초안 — 사장 수락 카드로 묻는다), docs/claude/watch-card-NTSK-2026-11-28.md(임시판 — 12/02 실적 뒤 다시 써서 묻는다). 두 카드 모두 미수락이라 매수 요건 ③은 아직 '확인 필요'.
- 관심 편입은 매수 승인이 아니다. 매수 주문표가 나오려면 아래가 모두 필요하다.

| # | 관문 | PANW | NTSK | 누가·어떻게 |
|---|---|---|---|---|
| 1 | 관심 명단 편입 | 끝(11/28) | 끝(11/28) | 사장 결정 카드 14:50 |
| 2 | 관심 카드 수락 + card-evidence-registry 등록 | 초안 끝, 수락 대기 | 12/02 실적 뒤 | 사장 수락 카드 → 같은 세션 등록 |
| 3 | M6 상대 비교 문서에 코드 포함 | 없음 | 없음 | 새 판 문서 + 사장 수락(코어 보호 입력 — 다음 코어 실행 전 커밋) |
| 4 | 신규 매수 상품 승인(APPROVED_BUY 61행) | 없음 | 없음 | 권한 변경 — 사장 직접 입력·Judge·PowerShell 승인. 권한 자리 순번은 정책 묶음 A → cal-2027(앞당기려면 사장 직접 지시) |
| 5 | 실적 기준표(earnings-anchors.json) | 없음(다음 FQ2 FY27 미공지) | 없음(12/02 예정, 확인 필요) | 통합 점검·Cowork |
| 6 | 공통 관문 R-REC1(RG1~RG4) | 막힘 | 막힘 | 시장 조건 — 사람이 열 수 없음 |

- 주의: 6번이 11/28 코어 기준 모든 매수를 막고 있어, 1~5를 다 해도 R-REC1이 닫히기 전에는 주문표가 나오지 않는다. 1~5는 '열리는 날 바로 살 수 있게' 미리 하는 준비다.
- 주의: CRWD는 상품 승인(3815698)·수락 카드가 있던 종목이다. 관심에서 빠져 CRWD 카드 트리거(held_or_member)는 더 켜지지 않는다. 다시 넣으면 수락 카드 재사용 조건(명단에서 빠진 적 없음)을 못 맞추므로 새 판 카드가 필요하다. MU 보호(~2027-02-20)는 끝났다.
- 가격 이력: 관심 종목은 코어가 정규장 종가 이력을 모은다(auto_core.py 170행 isolatable_symbols). PANW·NTSK 이력은 다음 코어 실행 뒤 생기는지 확인 필요.

## 11. 수락·등록 기록 — PANW 카드·M6·실적 기준표 (2026-11-28 15시대 KST)

- 사장 결정: 2026-11-28 15:08:45 KST 결정 카드 'PANW 카드·M6 비교·실적 기준표를 수락해 매수 요건을 채울까요?' → '셋 다 수락'(cmsg_0137MRzn9nuDvvQmVxm6WeX946DGuukX1vAdn9WFQxrcyY).
- 등록: watch-card-PANW-2026-11-28.md 머리말 status만 수락으로(절 해시 18ef59cd305a…, 본문 불변) · card-evidence-registry.json PANW 새 항목(스키마 검사 통과, 기존 항목 불변 — 텍스트 덧붙임, CRLF 유지) · watchlist-registry.json PANW cardStatus '수락(2026-11-28 …)'·history accept 1줄 · m6-relative-comparison-7stock-2026-11-28.md(초안 m6-cyber-draft-2026-11-28.md는 기록용, 코어가 읽지 않음) · earnings-anchors.json PANW(2025-11-19~2026-11-18, 5개)·NTSK(2025-12-11~2026-09-02, 4개) 8-K 2.02 날짜.
- 코어 예상(다음 실행, 23:30 커밋 뒤): ① PANW는 E = 2025-11-19 + 364일 = 2026-11-18(실제 발표일과 같은 날)이라, 기준표의 11/18이 '그 분기 발표'로 읽히는지에 따라 12/09까지 통과·막힘이 갈림(확인 필요), NTSK는 예상일 2026-12-10(전년 12/11 + 364일) ± 21일 안이고 그 분기 발표가 아직 없어 금지 구간 — 매수만 막힘(실제 12/02 예정) · ③ PANW 통과 예상(카드 표 2, r_max 1/2), NTSK 확인 필요(카드 미수락) · ④ 통과 · ② 상품 승인 없음 · ⑤ R-REC1 막힘. 실제 값은 다음 코어 실행에서 확인 필요.
- 주의: 23:30 커밋 전에 코어가 돌면 REGISTRY_UNCOMMITTED가 전 종목 주문표를 막는다(지금은 R-REC1로 어차피 막힘).
