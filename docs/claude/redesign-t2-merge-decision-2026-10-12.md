---
id: redesign-t2-merge-decision-2026-10-12
title: 재설계 T2 병합 결정 기록 — Q1~Q4 · P-1 · P-2
date: 2026-10-12
basis: docs/claude/redesign-t2-builder-prompt-2026-10-10.md 7·8절 · redesign-t2-judge2-report-2026-10-11.md (PASS-WITH-CONDITIONS) · .claude/worktrees/t2-core/docs/claude/redesign-t2-policy-proposals.json
authority: order_authority=false · execution_quantity=null · 주문표에만 quantity_authority="ORDER_TICKET_HUMAN_ENTRY"
consumers: Cowork(r5 확인·배포·"켜" 전 회차) · 관제판 redesign-t2
---

## 사용자 결정 (2026-10-12 11:21 KST, Cowork 세션)

`결정 redesign-t2: Q1 a, Q2 b, Q3 c, Q4 a, P-1 적용, P-2 적용`

## 반영

| 항목 | 답 | 반영 |
|---|---|---|
| Q1 | a | 지시문 7절 K3-1~5·7~9를 그대로 채택(코드 변경 없음). K3-6(확률)·위원회는 코어에 없음 |
| Q2 | b | `reissue_buy_cap_not_above_first: false` — 미입력 뒤 같은 결정은 다음 날 관문을 다시 통과할 때만 다시 낸다(사용자 단계 없음). 매수 상한은 그날 기준가 산식(첫 상한 제한 없음). 연속 미입력 2회면 닫힘 |
| Q3 | c | 키 없음 — 1회 크기·하루 건수 관문 없음(E 1.55·종목 0.4배·첫 진입 ½·데드밴드만) |
| Q4 | a | `research_only_strong_r_cap: "1/2"` — 무인 연구 기록의 공식 사실 하나로만 생긴 강 근거는 단계 상한 ½(같은 방향 카드 정적 강 근거가 있으면 1) |
| P-1 | 적용 | worktree t2-core의 `workspace/policies/auto_core.json`(sha256 7fcb0efe5434…). 기존 키는 그대로(mode compare · kill_switch false · 3 · 06:15). symbols_extra에 GRID 추가, decision_mode compare · 5 · 07:45, Q2·Q4 키 |
| P-2 | 적용 | worktree t2-core의 `stock-strategy-system/alert_policy.json`(sha256 98ef14e0dfe1…): `nominal_multipliers` PWR 1 · LITE 1, `card_stock_core` + PWR · LITE. 다른 줄 변경 0(기준값 1.55·0.4 등 그대로). 테스트 2개는 Builder r5 |

## P-2와 테스트 2개 (Cowork 실측, 2026-10-12)

- 11:2x 첫 판단: P-2를 넣으면 테스트 2개가 실패해 "켜" 전 회차로 미루려 했다.
- 11:34 사용자 "매수 주문표 막힘을 해결하라" → 병합 전에 같이 고친다.
- 영향 범위: worktree 사본 두 개(P-2 없음/있음)로 리눅스 VM에서 전체 테스트 107모듈 · 2,892건을 돌려 실패 id를 대조했다.
  - VM 환경 실패 150건은 두 사본이 같다(.git·자료 없음·Windows 전용).
  - P-2로 새로 실패하는 것은 아래 2건뿐이다.
    1. `test_portfolio_exposure.PolicyValueTests.test_real_policy_carries_the_fixed_r2_values`: 실제 정책의 배수를 고정한 테스트. 정책을 바꾸는 변경에서 기대값을 함께 고치는 것이 설계된 절차다.
    2. `test_auto_core_tickets.BuyTicketTests.test_policy_unregistered_instrument_has_no_ticket`: 실제 정책에 PWR이 없다는 전제. 정책 사본 주입으로 바꿔 같은 단언을 유지한다.
- 처리:
  - 테스트 수정은 코드 수정이라 Builder r5(`docs/claude/redesign-t2-builder-r5-2026-10-12.md`, 테스트만)가 한다.
  - Cowork는 r5 diff를 확인한다: 테스트 파일 2개 + 보고만, 단언 약화 0, 변이 확인.
  - P-2 키 목록은 1차 Judge가 확인한 제안 그대로이고 운영 코드 변경이 0이다. 그래서 r5에는 별도 독립 Judge를 두지 않는다.
- 효과: 병합 뒤 PWR·LITE는 정책 등록 종목이 된다. `POLICY_UNREGISTERED_INSTRUMENT` 막힘이 없어지고, S7 계획 대상에도 들어간다.
- 남는 정상 관문(막힘이 아님): 카드 근거·연구 기록·실적 금지 구간·R-REC1(PWR 벤치마크 GRID, 10/13 06:15 첫 수집 — 4/1부터 받아 σ60 가능)·예산 E 1.55.

## 실측

- GRID 거래소: `overseas stocks exchange-types`(usa10098, 읽기 조회, 실전계좌·real) → stex_tp ND(NASDAQ) 1행, ETF. 06:15 수집이 이력 없는 GRID를 같은 조회로 찾는다.
- P-1 적용 뒤 worktree(VM): `load_config` CONFIG_OK · decision_mode compare, `validate_schema_contracts.py` PASS, `test_auto_core*` Ran 286 OK(skip 1), `test_portfolio_exposure*` Ran 125 OK(P-2 전).
- worktree 코드 31파일의 수정 시각은 모두 Judge 2차 보고(10/12 11:07 KST) 전이다(마지막 10/11 01:24 KST). 그 뒤 바뀐 것은 Cowork의 P-1·P-2 파일 둘(r5 전).

## 병합 방법

`docs/claude/redesign-t2-merge-2026-10-12.ps1`(ASCII, r5 뒤 사용자가 메인 체크아웃에서 한 번 실행):
0 확인(메인 브랜치·스테이징 없음·관련 경로 깨끗함, worktree 브랜치·HEAD cd6a56d, 바뀐 파일 목록 = 코드 32(r5 테스트 포함) + P-1 + P-2, 두 정책 파일 sha) → 1 worktree 커밋(코드 32파일) → 2 worktree 커밋(P-1·P-2) → 3 메인에 `--no-ff` 병합 → 4 스키마 감사·설정 검증·대상 테스트 5묶음 → 5 작업 2개 등록(InvestmentV2-AutoCore 06:15, InvestmentV2-AutoCoreDecide 07:45, 화~토). 실패하면 그 자리에서 멈추고 STOP 사유를 출력한다. r5 전에 실행하면 0단계에서 멈춘다(test_portfolio_exposure.py 변경 없음).
단계 0~3은 모의 저장소(PowerShell 7, 리눅스)에서 확인했다. 4·5는 Windows 전용이라 확인하지 못했다(확인 필요 — 실행 출력으로 판정).

## 다음 (지시문 8절)

r5 → Cowork 확인 → 병합 스크립트 → 4 예약 작업 변경(★ 승인 1번: 06:40 연구 기록 쓰기 · 알림 08:50 · 대시보드 · 카드 등록부 절차) → 5 CLAUDE.md 문구(★) → 6 외부 오라클 커밋 → 리플레이 → 7 비교 모드 5거래일 → "켜" 전 수정 회차(Judge 2차 G절 9건) → ★ "켜".

## r5 확인 (Cowork, 2026-10-12 13:0x KST)

- 바뀐 파일: r5 지시문 뒤 수정된 파일은 `test_auto_core_tickets.py` · `test_portfolio_exposure.py` · Builder 보고 셋뿐이다. 두 정책 파일 sha는 Cowork 반영값 그대로다(7fcb0efe… · 98ef14e0…). worktree 변경 = 코드 32 + 정책 2.
- 바이트코드 대조: r5 전 컴파일본(VM cpython-310 pyc)과 비교했다. 바뀐 함수는 다음뿐이고, 삭제는 0이다.
  - `test_real_policy_carries_the_fixed_r2_values`: 기대 배수 + PWR·LITE, card_stock_core 단언 추가
  - `test_policy_unregistered_instrument_has_no_ticket`: 정책 사본에서 PWR 제거, 단언 그대로
  - 새 `test_registered_instrument_is_not_blocked_by_policy_registration`: 막힘 사유 없음 + PWR 매수 주문표 1건
- VM 재실행(P-2 있음): `test_auto_core*` 287 OK(skip 1) · `test_portfolio_exposure*` 125 OK · `test_run_portfolio_exposure_review*` 24 OK · `test_portfolio_status*` 15 OK.
- 정책 독립성: P-2 전 정책 사본에서는 결과가 다음과 같다.
  - 주문표 테스트 2개는 모두 통과한다(실제 정책에 기대지 않음).
  - 고정 테스트는 실패한다(P-2 값을 고정하므로 맞음).
- Builder 전체 스위트(Windows): Ran 2908 · 실패 줄 28(기준선과 같은 개수). id 정렬 대조는 하지 않았다(Builder 보고).
  - 대신 Cowork의 P-2 전후 전체 대조에서 P-2 영향은 위 2건뿐이었고, 둘 다 고쳐졌다.
  - 병합 스크립트 4단계가 대상 테스트를 다시 돌린다.

## 배포 8절 4 — 예약 작업 변경 (2026-10-12 13:24~13:40 KST)

- 사용자 승인: `결정 redesign-t2: 예약 작업 변경 승인` (13:23).
- 통합 점검(trig_01YWzNq847nJfNgDUnnukBqP): 로더 v3.12.2-L+R1, sha256 ded151f3f2d2…(scheduled-prompts/integrated-check-daily.txt). 교체 응답 "prompt re-signed" 확인. 규칙 파일·해시(ee098920…) 불변.
- 결과 알림(trig_01D5KxMSJgbeRG1ZL5ox3Fna): v2, 화~토 08:50, sha256 1113744f09d7…(scheduled-prompts/auto-core-alert.txt). 교체 응답 "prompt re-signed" 확인.
- 통합점검 대시보드 Artifact 재게시(버전 16): "자동 운영 코어 판정" 칸(runs.core — 상태·모드·연구 기록·대조 연속 일수·주문표·코어 충족·근접·매수 요건 통과 종목), 주문 지시 칸에 "자동 운영 코어" 표시·옵션 "생략", 결과 문구. 표본 기록으로 한 번 그려 확인(jsdom, 구역 오류 0).
- 카드 등록부 절차: analysis-linkage-map 2절 표·library/INDEX.md에 한 줄(카드를 고치거나 수락하는 Cowork 세션이 같은 세션에서 등록부 갱신).
- 연구 기록 단계 모의 실행: 실적 3·공식 사실 1 통과, 형식 틀린 항목 3개 자동 제외, 스키마 검사 통과, 같은 날 두 번째 쓰기 "RR EXISTS". 실제 첫 실행은 10/13 06:40(확인 필요).

## 배포 8절 5 — CLAUDE.md (2026-10-12 13:3x KST)

- 사용자 승인: `결정 redesign-t2: CLAUDE.md 승인` (13:31). 제안 docs/claude/redesign-t2-claude-md-proposal-2026-10-12.md 3곳 그대로 반영(CRLF 유지, +10/−1줄, sha256 2d2f914cc31b…). 커밋은 사용자 PowerShell 한 줄(CLAUDE.md는 docs 자동 커밋 대상 밖).
- 커널 지침 2절 문구는 선택(제안 문서 끝) — "켜" 전에 붙이기를 권함.

## 첫 운영일 결정 (2026-10-13)

- `결정 runner-fix: 승인` (08:58) — run_auto_core.ps1 변수 충돌 수정(dev 파이프라인 runner-fix). 보고 docs/claude/redesign-t2-firstrun-report-2026-10-13.md.
- `결정 redesign-t2: 예약 작업 변경 승인(알림 v2.1)` (08:58) — 적용 09:05.
- `결정 t2-equity-cash: 나` (09:21) — 총자산·노출·EV4·V6의 USD 현금을 T1 F1 승인 정의(주문가능 fc_ord_alowa + T1 가드, 실패 시 fc_entra로 물러나 "확인 필요")로. 근거 docs/claude/redesign-t2-compare-b7-2026-10-13.md "재검토". 매수 관문 입력이라 권한·한도 변경(K3) → **"켜" 전 수정 회차(수동 경로: worktree Builder + 별도 Judge)에 10번째 항목으로 넣는다**(새 사람 단계 없음, CLAUDE.md 권한·한도 변경 1건 한도 = T2 안에서 처리). 같은 결정에 대조 모듈 분류 결함 2건 큐 승인 포함 → dev 파이프라인 cmp-fix(표시·분류 전용, 경로 때문에 authority).
- "켜" 전 수정 회차 목록: Judge 2차 G절 9건 + ⑩ 총자산 현금 정의(위) + ⑪ 통합 점검 규칙 1-1 ② 문구 "(정산 중 매도대금 포함)" 정정(예약 작업 변경 승인 필요).
- `결정 ust21100-fix: 승인` (10:33) — 계좌 읽기 브리지 ust21100 본문 수정(파이프라인 ust21100-fix). 보고 redesign-t2-firstrun-report-2026-10-13.md 10절.
- `결정 t2-equity-cash: 지금 진행` (13:00) — '켜' 전 회차 ⑩을 앞당겨 수동 경로로 진행(지시문 docs/claude/t2-equity-cash-builder-prompt.md, Builder worktree t2-equity-cash → 별도 Judge → 사용자 병합). ⑪ 규칙 문구 정정은 그대로 '켜' 전 회차.
- t2-equity-cash 병합 73e18b4(2026-10-13 14:1x, Judge PASS) — '켜' 전 회차 ⑩ 완료. ⑪ 남음.
- 2026-10-13 15:01 KST 사용자 "결정 cmp-fix3: 승인" — 대조 분류: 코어 RG1 unk + 연구 기록 공백(rg1_coverage) → 사전 등록 B4. 지시문 docs/claude/cmp-fix3-builder-prompt.md, dev 파이프라인 큐 등록(Cowork). 앞선 rrec-rg1-bootstrap 선택지 A·B·C는 철회(firstrun 보고 17-1절).
