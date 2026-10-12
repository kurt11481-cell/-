---
id: board-redesign-alignment-2026-10-12
type: review-record (관제판 데이터·예약 알림 1건 정정 — 코드·정책·상태·주문 변경 없음)
as_of: 2026-10-12 14:10 KST (Cowork)
trigger: 사용자 "시스템 재설계에 따른 관제판 개발 작업 목록 점검 — 재설계 현황 및 지침과 맞지 않는 개발작업 점검 및 수정하라"
basis: automation-redesign-2026-10-10.md(3·4·10절) · CLAUDE.md(29ad21d) · redesign-t2-merge-decision-2026-10-12.md · tools/dev_pipeline/README.md · 관제판 tasks 열린 28개
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: 관제판(PM54MdPfrgYt4LfFxQT9Tu) · redesign-t4(흡수 목록) · 10/13 09:20 예약 "PWR 1차 지시서 사전 준비" · dev-dashboard-protocol.md
---

# 관제판 재설계 정합 점검 (2026-10-12)

## 결론
- 열린 28개 중 22개가 재설계(2026-10-10)·CLAUDE.md와 어긋나 있었다. 모두 관제판에서 고쳤다(batch 1회, 원자 적용).
- 내일(10/13) 바로 문제를 만들 것 2개를 먼저 막았다: ① p-s7-routine이 10/13 "지금 할 일"에 옛 PowerShell 루틴으로 뜰 뻔함 ② 10/13 07:30 예약 "PWR 1차 지시서 사전 준비"가 폐지된 주문별 위원회·철회된 R-RI1을 쓰고, 코어 decide(07:45)보다 먼저 돎 → 09:20으로 옮기고 지시문 정정.
- 6개(c-cien-fq4·c-nextsndk-v2·e-new·h55-haiku·redesign-t1·redesign-t5)는 그대로 둠.

## 어긋남 유형과 고친 작업
| 유형 | 지침 근거 | 작업 → 바꾼 것 |
|---|---|---|
| A. 사람 일상 단계가 남음 | Goal(일상 개입 0, 읽기 전용은 Cowork가 함) | p-s7-routine(옛 startPrompt 삭제, T1 "켜" 때 은퇴) · r-cashflow-hold(수동 증거 첨부 → 코어 기록 뒤 자동) · swap-soxl-pwr(사용자 "PWR 1차 판정" 입력·Windows 대조 단계 삭제) · c-hwm-review(키움 수동 대조 → 코어 exposure 읽기) · fx-3(측정은 코어 수집 결과) |
| B. 주문별 위원회·철회 규칙 | Council 줄(정책·한도·권한만) · R-RI1 10/9 철회 | swap-soxl-pwr · 10/13 예약 지시문(위원회 Lite·R-RI1 삭제) |
| C. 옛 변경 경로(worktree 수동 Builder) | Change classes A5 · dev_pipeline README | fx-3(2단계 = 파이프라인) · c-nextsndk-seed · p-s44(worktree 칸 삭제) |
| D. 기본 처분 없음·사용자에게 매번 물음 | Default disposition | e-filing-k4(미달 = NO_CHANGE, 질문 삭제) · c-nextsndk-1107(씨앗 0이면 기록·알림만, 씨앗 있으면 제안 모드 A6 그대로) · r-rec1 · p-s44 |
| E. 끝났거나 흡수된 것을 가리키는 재개 조건 | 10/10 흡수 기록 · T2 병합 | fx-6(fx-3 2단계 11/3 > 기한 10/23 → 의존 T1만) · r-rec1(② 모듈 = T2 코드화로 대체, fx-6 뒤) · redesign-t2(병합 스크립트 startPrompt → 09:05 점검 뒤) · f-trading-infra-gap·f-ifixai-audit·f-openshell(1단계는 이미 승인 → T5 결정 전으로) · f-ponytail-audit(P6 → T4 입력) · redesign-t3b(⑧ 권한 경로 추가 시점 도래) |
| F. 단순화 먼저(REMOVE 전 ADD 금지) | 커널 7절 · 재설계 T4 | p-k132g·s-cbm-pilot·s-library → paused, T4에서 유지·폐기 판단. s-cbm-pilot: 파이프라인 Builder는 --strict-mcp-config·mcp__* 금지라 cbm(MCP)을 못 씀 |
| G. 빈 작업 | — | redesign-t4에 흡수 목록 채움 |
| H. 일지 자동화로 뜻이 바뀐 기준 | T2 일지 자동(core_decision 매일) | f-evo-loop "원장 30건" → 확인 필요 표시(제안: order_ticket·ticket_outcome·사용자 결정만 셈) |

## 고치지 않고 남긴 것 (확인 필요 · 별도 결정)
1. CLAUDE.md "Transition: Kiwoom acceptance pin … Until that change is merged" 줄은 낡음 — pin-scope 파일 status RETIRED(2026-10-10, T1). CLAUDE.md는 보호 경로라 T4 묶음(redesign-t4 ⑥)에 넣음.
2. 권한·한도 변경 T1·T2가 동시에 진행 중(CLAUDE.md 한도 1건). 사용자 결정(10/10·10/12)으로 진행 중이므로 "켜"는 T1 먼저 → T2 순서로 하나씩(redesign-t2 note).
3. ~~SAVE 메모 종목 목록에 PWR·LITE 없음~~ — 오판(14:40 정정): 근거였던 s-library verify가 낡았음. SAVE 예약 작업은 v2.1(10/9)부터 상태 파일 보유 + 명단 파일 members에서 읽는다.
4. "일지 30건" 기준을 쓰는 다른 결정(후회 수치 채점·옵션 가격 산식 검증, 2026-10-05·10-07)도 H와 같은 문제 — 셈 기준 정의 필요.
5. 재개 가능(기한 지남) 2건: e-filing-k4(10/10)·h55-haiku(10/10). 둘 다 읽기 전용이라 다음 Cowork 세션이 처리(사용자 할 일 아님).
6. 외부자료 원장 "사람 수락 뒤 등록"(e-new, external-pdf-intake 5·6단계)과 11/7 월간 발굴 세션 열기(c-nextsndk-1107)는 남는 정기 사용자 손 — 자동화 여부는 별도 검토.

## 바꾼 파일·데이터
- 관제판 tasks 22개 + log lg-20261012-1410-align + meta board(v150).
- 예약 알림 trig_013TBdNZRXF7JsRuZjPSPv42: 실행 10/13 07:30 → 09:20 KST, 지시문 정정(사용자 컴퓨터 서명 갱신됨).
- docs/claude/dev-dashboard-protocol.md 3절: 변경 2등급·파이프라인·기본 처분·위원회 규칙 한 단락.

## 판단 재검토 (14:40, 사용자 요청)
| # | 처음 판단 | 재검토 결과 | 조치 |
|---|---|---|---|
| 1 | CLAUDE.md pin 문구 → T4 | 유지. 문구가 "Until that change is merged" 조건부라 T1 병합(510961a) 뒤 실제 효력 없음. 지금 고치면 CLAUDE.md(docs/claude 밖)라 자동 커밋이 안 돼 사용자 커밋 1번이 추가되고, 메인 체크아웃에 커밋 안 된 CLAUDE.md가 남으면 개발 파이프라인 메인 체크아웃 보호에 걸릴 수 있음 | 없음(redesign-t4 ⑥) |
| 2 | T1·T2 동시 → "켜" 순서 | 유지. 순서는 규칙 맞추기보다 기술 의존: T2 decide는 T1이 기록한 상태를 읽으므로 T1 "켜"가 먼저여야 함. 비교 기간도 T1 3일 < T2 5일이라 자연 순서 | 없음 |
| 3 | SAVE 종목 목록 고정 | 오판 | s-library note·verify 정정 |
| 4 | "일지 30건" 셈 → 사용자 확인 | 원래 뜻을 지키는 셈은 변경이 아니므로 기본 처분으로 정함: 행동 있는 결정 1건당 1(card_decision·card_user_decision·order_ticket), core_decision·ticket_outcome·s5_activation은 세지 않음. 10/12 기준 5건. 후회 수치 채점(10/5)·옵션 산식 검증(10/7) 30건에도 같은 셈 | f-evo-loop verify |
| 5 | 기한 지남 2건 → 다음 세션 | 미루지 않고 지금 처리. e-filing-k4: 10/10 기록도 onlyInSearch·onlyInFeed 미기록(피드 자체는 유효) → 지금 지시문으로는 표본이 안 쌓임 → 기본 처분 NO_CHANGE로 닫고 T4 입력. h55-haiku: 10/10 실행 보고가 그 세션에만 있어 대조 불가 → 기본 처분 NO_CHANGE(Haiku 유지)로 닫음 | 두 작업 done |
