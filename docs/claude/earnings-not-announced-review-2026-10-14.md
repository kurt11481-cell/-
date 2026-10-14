---
id: earnings-not-announced-review-2026-10-14
title: 실적일 "미공지(NOT_ANNOUNCED)" 확인 방법 재검토
date: 2026-10-14
class: K2 후보(통합 점검 로더 4단계 ㉯ + build 가드 + 기준표 1개) — p-earn r1 정책 문언 불변, 미공지를 덜 쓰는 쪽(매수만 더 막힘)
status: 결정 a(2026-10-14 11:04 KST "결정 earn-na: a") — 구현 초안·시험·독립 검토 완료, 예약 작업 교체는 10/15 07:20 첫 실행 확인 뒤(사용자 승인)
authority: order_authority=false · quantity_authority=none · execution_quantity=null
---

# 실적일 "미공지" 확인 방법 재검토

## 결론
- 처음 안(목록 페이지 + 보도자료 검색)은 PWR 사례를 막지 못한다 — 철회.
- 권장: 작년 같은 분기 발표일 기준 3주 창. 예상일(작년 발표일 + 364일) 21일 전부터는 회사 공지를 확인(VERIFIED)하기 전까지 미공지를 쓰지 않는다(→ 코어가 금지 구간으로 봄, 매수만 막힘).
- 시급성 정정: "비교 모드라 급하지 않음"은 틀렸다. 관제판 autocore-on — 첫 매수 예외(exc-1) 가장 이른 판정 10/16 07:45.

## 근거 (이번 대화에서 직접 확인, 2026-10-14 KST)
| # | 확인 | 결과 |
|---|---|---|
| 1 | WebFetch https://investors.quantaservices.com/news-events/press-releases (10:57) | 최신 항목 9/9 — 10/13 06:55 EDT 공지가 28시간 뒤에도 없음(오래된 사본) |
| 2 | 같은 페이지를 내장 브라우저로(11:00) | 맨 위에 "Oct 13, 2026 6:55am EDT · Third Quarter 2026 Earnings Release & Webcast Schedule" — 페이지는 최신, 가져오는 경로가 오래됨 |
| 3 | WebFetch https://investor.lumentum.com/financial-news-releases | "Loading..."만 보임 — 목록을 읽을 수 없음 |
| 4 | WebFetch https://investor.marvell.com/news-events/press-releases | 10/13 항목까지 최신 — 사이트마다 다름 |
| 5 | WebSearch "Quanta Services third quarter 2026 earnings release webcast schedule" (10:57) | 10/13 공지가 나오지 않음(2025년 3분기·2026년 2분기 공지만) |
| 6 | 코어 manage-us-stock-strategy/scripts/portfolio_exposure.py _not_announced_check | 미공지는 출처 종류·https·checked_at(평가 세션 16:00 ET 이후)만 본다 — 내용 확인은 통합 점검 몫 |
| 7 | 작년 같은 분기(공식) | PWR 2025-10-14 공지 → 2025-10-30 장 전 발표(investors.quantaservices.com PDF). NBIS 2025-10-22 공지 → 2025-11-11 장 전(nebius.com/newsroom) |
| 8 | 재사용 가능한 공식 자료 | docs/claude/redesign-t2-measurements-2026-10-10.json earnings_announcements_sec — SEC 8-K 2.02 날짜 2개 분기 × 7종목(AMD·BE·DELL·LITE·MRVL·MU·PWR). NBIS 없음(6-K) |

## 대안 비교
| 안 | 내용 | 10/14 PWR 막았나 | 매수 막힘 비용 | 복잡도 |
|---|---|---|---|---|
| b 현행 유지 | 단서 가드(st-1014 B)만 | saveticker에 보일 때만 | 없음 | 0 |
| (철회) 검색 추가 | ㉯에 검색 1회 | 못 막음(근거 5) | 없음 | 낮음 |
| c 직전 발표일 + 55일 | 결정론, 표 불필요 | 막음(76일째) | 큼 — 4분기→1분기 간격이 짧은 회사 때문에 기준을 짧게 잡아야 해서 분기마다 2~4주(추정) | 낮음 |
| a 작년 같은 분기 기준 3주 창(권장) | 결정론, 기준표 1개 | 막음(작년 10/30 + 364 = 10/29, 10/8부터) | 작음 — 공지가 예상일 21일 안에 나오는 회사만 그 사이 며칠 | 중간 |
| d IR 목록을 06:15 SAVE 브라우저로 실시간 읽기 | 근본 해결(근거 2) | 막음 | 없음 | 높음 — 사이트 7개 구조 다름, 공식 페이지 사본의 권한 문제 |
| 미공지 폐지 | 항상 금지 | 막음 | 거의 항상 매수 불가 | p-earn r1 결정(10/3)과 충돌 — 제외 |

## a안 동작(구현 시)
- 기준표 docs/claude/earnings-anchors.json: 종목별 직전 4개 분기 실적 발표일(SEC 8-K 2.02 또는 회사 보도자료 URL). 근거 8의 2026년 1·2분기 + 2025년 3·4분기를 원문으로 채움. 12개월 유효.
- build: 미공지 종목마다 예상일 E = 기준일 + 364일. E − 21일 ≤ 오늘 ≤ E + 10일이면 미공지를 뺀다(dropped 사유 earnings:<종목>(anchor)). 기준표를 못 읽었거나 그 종목의 E가 앞으로 120일 안에 없으면 뺀다(실패하면 막는 쪽).
- 바뀌는 것: 통합 점검 로더 4단계(기준표 올리기·build 몇 줄·㉯ 한 문장)와 writer 표기. 규칙 파일 v3.12.4·코어·정책 파일 불변.
- 오늘 기준 영향(추정): PWR만 빠짐(내일 VERIFIED 예정이라 실영향 없음). NBIS는 10/20경부터 Nebius 공지 확인 전까지 매수 막힘(작년 공지 10/22). DELL·MRVL·MU 기준일은 구현 때 SEC 원문으로 확인 필요.
- 적용 시점: 10/15 07:20 첫 실행 확인(writer 비교)이 끝난 뒤 교체 → 10/16 06:40부터. 10/16 07:45 첫 매수 판정에 들어감.
- 시험: 10/14 실데이터(PWR 빠짐·나머지 유지), 기준표 없음(미공지 전부 빠짐), 기준표에 없는 종목(빠짐), 예상일 지난 뒤 10일(빠짐)·11일(유지).
- 유지: 12개월 뒤 기준표가 비면 미공지가 모두 빠져 매수만 막힌다(보임). 관제판에 갱신 할 일 등록.

## 답이 없을 때
기본값 b(현행 유지). 그 경우 첫 매수 주문표의 Cowork 확인(exc-1)에서 그 종목 실적일을 회사 원문으로 직접 확인한다.

## 구현 (2026-10-14 11:1x~12:0x KST)
- 결정: 사용자 "결정 earn-na: a"(11:04).
- 가드 위치: 통합 점검 로더 4단계 finalize(사용자 PC에서 실행). build를 거친 기록을 검사·통과시킨 뒤, 미공지 항목에만 창 검사를 해서 빼고, 다시 스키마 검사 후 research-record.json으로 바꾼다. 쓰는 파일은 그날 폴더의 두 파일뿐(기존과 같음). build는 writer 표기만 바뀜.
- 창: E = 기준일 + 364일·+728일(기준일 = 기준표 + 오늘 기록·지난 450일 연구 기록의 VERIFIED 발표일). E − 21 ~ E + 21일이고 E ± 35일 안에 지난 VERIFIED 발표가 없으면 뺌. E가 오늘 − 21 ~ + 130일 안에 없으면 뺌(anchor-missing). 기준표를 못 읽으면 전부 뺌(anchors-unreadable, 푸시). 형식 오류는 그 종목만 뺌(anchor-error, 푸시). MVLL = MRVL 기준.
- 기준표 docs/claude/earnings-anchors.json (sha256 de7f46ec…38f8): PWR·BE·DELL·LITE·MRVL·MU = SEC data.sec.gov submissions의 8-K item 2.02 제출일 5개씩(2025-07~2026-09, 내장 브라우저로 JSON 직접 읽음, 11:2x), NBIS = nebius.com 보도자료 4개(Q3·Q4 2025, Q1·Q2 2026 — 날짜 공지문 원문).
- 로더 초안 docs/claude/scheduled-prompts/pending-earnna/integrated-check-daily.txt (v3.12.4-L+R2, sha256 d81ecd30…3659, 20,729 bytes). 규칙 파일 v3.12.4·코어·정책·스키마 불변.
- 시험: 합성 15건(10/14 실데이터 → PWR만 빠짐, PWR VERIFIED면 그대로, 기준표 없음 → 미공지 전부 빠짐, 새 종목 → 빠짐, NBIS 10/19 유지·10/20 빠짐, BE·PWR 발표 뒤 이력 있으면 유지·없으면 E+21까지 빠짐, MVLL 별칭, sha 불일치, 2027년 투영) + 형식 오류 8건(기준표 숫자·참·없는 날짜·목록 아님·깨진 JSON, 지난 기록 목록·문자열·없는 날짜) — 모두 죽지 않고 그 종목만 빠짐. 사용자 PC 실경로 건식 실행: 10/15 → PWR만, 10/21 → NBIS·PWR.
- 독립 검토(별도 에이전트): PASS-WITH-CONDITIONS — ① 형식 오류로 finalize가 죽으면 기록이 없어 지수 ETF까지 막힘 → try로 감싸 그 종목만 빼게 고침(위 형식 오류 8건) ② 기준표를 먼저 배치 → 배치 완료(현행 R1은 읽지 않아 영향 없음), 읽기 실패 시 푸시 추가 ③ 지난 날짜의 VERIFIED도 오래된 사본일 수 있음 → 코어가 이미 막음(portfolio_exposure.py earnings_blackout: buy_session > end → EARNINGS_DATE_STALE) ④ 기준표는 해시로 고정하지 않음 — 분기마다 추가해야 해서. 고칠 때는 git 이력·관제판으로 남긴다 ⑤ +728일 투영은 2027-07부터 끝남 → 그 전에 기준표 갱신(관제판 할 일).
- 남은 위험: 회사가 작년보다 21일 넘게 일찍 발표하면서 공지도 못 잡으면 막지 못함. 기준표에 없는 새 종목은 VERIFIED 전까지 매수만 막힘. 발표 뒤 VERIFIED를 못 잡은 분기는 E + 21일까지 매수만 막힘.
- 적용 순서: 10/15 07:20 st-1014 첫 실행 확인(writer R1 기대) → 통합 점검 예약 작업 지시문을 초안으로 교체(사용자 승인, 재서명) → scheduled-prompts 원문·README 갱신 → 10/16 06:40부터 적용, 10/16 07:45 판정에 반영. 되돌리기 = R1 원문(b166bad2…)으로 교체.
