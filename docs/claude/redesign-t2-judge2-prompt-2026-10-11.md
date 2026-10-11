---
id: redesign-t2-judge2-prompt-2026-10-11
title: 재설계 T2 독립 Judge 2차 — 1차 FAIL 최소 수정(F-1~F-4)·조건 반영과 r2~r4 변경분
date: 2026-10-11
first_judge: docs/claude/redesign-t2-judge-report-2026-10-10.md (FAIL — F-1~F-4, 조건)
builder_rounds: docs/claude/redesign-t2-builder-r2-2026-10-10.md · redesign-t2-builder-r3-2026-10-11.md · redesign-t2-builder-r4-2026-10-11.md
builder_report: .claude/worktrees/t2-core/docs/claude/redesign-t2-builder-report-2026-10-10.md ("# r2" · "# r3" · "# r4" 절)
worktree: .claude/worktrees/t2-core (base cd6a56d, 미커밋)
authority: order_authority=false · execution_quantity=null · 주문표에만 quantity_authority="ORDER_TICKET_HUMAN_ENTRY"
consumers: Cowork(병합 판단·배포) · 관제판 redesign-t2
---

**[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(메인 체크아웃, worktree 아님) · 이유: 권한 변경의 독립 확인(2차)**

## 사용자 조작 (Windows PowerShell, 한 번 — r4 Builder가 끝난 뒤)
```
cd "E:\사업\##금동한\코덱스저장소"
claude --model opus --effort xhigh
```
첫 메시지로 이 한 줄만:
```
Read docs/claude/redesign-t2-judge2-prompt-2026-10-11.md and follow the Judge section exactly.
```
끝나면 Cowork에 "T2 Judge 2차 완료"만 보낸다.

## Cowork 사전 확인 (r3까지, 2026-10-11 01:0x KST — 참고, Judge는 다시 확인)
- r2: 대상 테스트 253 OK(리눅스 VM 재실행), 스크립트 비ASCII 0. r3 보고: 대상 268 OK, 전체 Ran 2889 · 실패 28줄(기준선과 같은 id).
- 바뀐 파일 집합은 1차와 같다(수정 7 + 새 파일 25, 새 경로 0).

## Judge
```
너는 독립 Judge다(1차 Judge와 같은 규칙). Builder 보고를 증거로 쓰지 말고 코드·diff·테스트로 직접 확인한다.
파일을 고치지 않는다. 유일하게 쓰는 파일은 docs/claude/redesign-t2-judge2-report-2026-10-11.md 하나(메인 체크아웃).
키움 조회·kiwoomcli·auto_core.py(daily·decide)·reconcile_broker_state.py auto/apply·register_auto_core_task.ps1 실행 금지(가짜 데이터 테스트만).
커밋·병합·작업 등록 금지. 정책·상태·일지 파일 쓰기 금지. 비밀 읽기·출력 금지.
이 세션은 "auto_core.py"가 들어간 명령이 막혀 있다: 문자열 검색은 Grep 도구로, 테스트는 -p "test_auto_core*".
대상: git -C .claude/worktrees/t2-core status / diff cd6a56d (CRLF 주의). 기준: 1차 지시문 docs/claude/redesign-t2-builder-prompt-2026-10-10.md,
1차 Judge 보고, r2·r3·r4 지시문(위 머리말 경로).

A. 1차 FAIL 해소 — 항목마다 PASS/FAIL + 근거(파일:줄) + 1차 탐침 재현
 F-1 연구 기록 OK가 아니면 지수 ETF 포함 모든 매수 차단, 매도는 그대로(1차 탐침 P3를 다시 돌려 SOXL 매수 0 확인).
 F-2 이른 HOLD/FAIL 날을 건너 재발행 원장·미분류 주문표가 이어짐(탐침 P1 재현: D 주문표·닫힌 키 → D+1 HOLD/예외 FAIL → D+2 분류·일지·키 유지).
 F-3 그 세션 EV4가 R-REC1에 들어감(탐침 P2 재현: 직전 기록 없음 + 총자산 ≤ 1차 선 → shock open, ⑤ ≠ ok, 매수 0).
 F-4 훼손 사실을 R-REC1 창(60세션)에서 모으고, RG1은 이벤트 뒤 모든 세션 기록이 있어야 판정, 기록 누락 중 SOXX ≤ −1σ60 날이 있을 때만 R-REC1 unk.

B. 1차 조건 반영 — 각각 PASS/FAIL
 "켜" 전 1~5(같은 run_day 재실행 멱등 · 매도 주문표의 S7 계획 전제 줄 · 불일치 결과는 원장 갱신 안 함 · 채점기 반환값 경고 · 등록부 kind·side 묶음),
 비교 모드 1·3(대조 엄격화: FAIL·이른 종료 날 연속 일수 0, N ≤ 0.03·R5 ≤ 1%p만 B2, b2_wide / decide의 S7 검토 출력이 auto-core/<날짜>/s7 아래).

C. r3·r4 — 각각 PASS/FAIL
 R3-1 세션이 끝난 주문표만 분류(세션 전이면 열린 채 G0 HOLD) · R3-2 주문일 창 = 발행 KST 날짜 ~ 세션 마감 KST 날짜(토→월 4일, 겨울 06:00,
 조기 폐장) · R3-3 새 세션 없는 날 = OK·no_new_session·주문표 0·일지 0·push 0·원장 이어받기·대조 연속 일수 유지·decision.json 기록,
 R2-5는 같은 run_day만 · R4-1 이미 귀속된 (ord_dt, ord_no) 제외 + 발행일 행은 발행 시각 이후만 + 이어받기·30일 정리 + 기록 모드에서만 원장 갱신 ·
 R4-2 입력 창 문구(개장 KST 날짜·시각).

D. Builder가 새로 고른 것 — 수용/거절과 이유
 r2 보고 r2-3의 1~13, r3 보고 r3-2의 1~9, r4 보고의 새로 고른 것. 특히: f6_ran의 뜻(F6 뒤 실패도 "확정 없음")과 FAIL 기록이 주문표를 내지 않는 것 ·
 결정 스키마 검사를 일지 쓰기 앞으로 · decision_sha256 정의(재실행에서 바뀌는 칸 제외)가 실제로 다른 판정을 같다고 보지 않는지 ·
 R3-3 날 대시보드에 세션 전 주문표 행을 남기는 것("주문표 0" = "새 발행 0" 해석) · 출처 뒤 읽을 수 없는 기록이 있으면 R3-3을 쓰지 않는 것.

E. 회귀 — 1차 PASS 항목(J1~J5, J7~J9, J11~J16, K2·K8)이 r2~r4로 깨지지 않았는가. 특히 J2 주문 경로 0, J3 체결 추정 0, J4 비교 모드 무쓰기,
 J5 기준값 불변(r2~r4가 새 문턱을 만들지 않음 — 0.03·1%p는 부록 B 대조 범주, 30일은 자료 보관), J14 보안, J16 새 사용자 단계 0.

F. 테스트(Windows, 직접): -p "test_auto_core*" · test_portfolio_review_journal* · test_decision_journal_cards* · test_run_portfolio_exposure_review* ·
 test_portfolio_status*. 전체 스위트는 test-runner로 돌리고 실패 id 집합을 원본 출력에서 직접 세어 기준선 28줄과 비교. 바뀐 기존 테스트의 단언 약화 여부
 (r2·r3가 바꿨다고 적은 고정 테스트 1개·픽스처 날짜·현금은 이유가 맞는지). 실자료 리플레이 스모크 1회(1차 K8과 같은 인자, 출력은 세션 임시 폴더).

G. "켜" 전 남는 것 — Builder "새로 찾은 사실"(r4 보고)과 이 판정에서 나온 것을 "병합 전 / 비교 모드 중 / 켜 전"으로 나눠 적는다.

보고 형식(한국어): 맨 위 판정 PASS | PASS-WITH-CONDITIONS | FAIL 한 줄 → A~F 판정표 → G 조건 → FAIL이면 최소 수정 목록 → 메모.
```
