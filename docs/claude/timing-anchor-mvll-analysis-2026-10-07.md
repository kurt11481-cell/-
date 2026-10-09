---
id: timing-anchor-mvll-analysis-2026-10-07
type: analysis
status: analysis only (2026-10-07, 읽기 전용 — 상태·정책·코드는 바꾸지 않았다)
as_of: 2026-10-07
summary: portfolio_state.json의 timing_plan MVLL anchor_shares=396이 보유 278주와 달라 보이지만, 현재 정책의 타이밍 슬롯이 은퇴(positions={})해 이 값을 읽는 검사가 휴면 중이다. 권고는 NO_CHANGE(앵커는 이력으로 둔다). K0 문서 기록만.
consumers: [개발 관제판(남은 작업 항목 종료), docs/claude/s7-builder-report-2026-10-01.md §1c 후속, 타이밍 정책을 다시 켜는 미래 K3 세션, 통합 점검 조사 메모 docs/claude/integrated-check-statefile-binding-2026-10-07.md]
---

# MVLL timing_plan 앵커 396 — 영향 분석 (2026-10-07)

## 1. 결론
**고치지 않는다(NO_CHANGE).** 앵커 396은 "2026-07-31 기준 시작 수량"이라는 이력 값이고, 현재 이 값을 읽어 판정하는 코드 경로는 꺼져 있다. 278로 바꾸면 앵커 식별자·원천 리비전·기준일과 어긋나는 이력 변조가 되고, 상태 파일 쓰기 경로 규칙(대조 apply 또는 Builder+Judge)도 거쳐야 한다. 얻는 이익이 없다.

## 2. 근거 (읽기 전용 확인)
| 확인 | 결과 |
|---|---|
| 앵커를 읽는 코드 | `scripts/timing_engine.py` 하나(`timing_anchor_errors`, :47-51 앵커 유효성·정책 일치, :102-107 `보유 = 앵커 − 체결된 슬롯 합계`). 호출은 `evaluate_alerts.py:583` 한 곳 |
| 정책의 타이밍 슬롯 | `alert_policy.json` `holding_timing_rules.positions` = `{}` (작업 트리와 HEAD 모두). S7에서 슬롯 은퇴. 그래서 종목별 앵커 검사 루프가 돌지 않는다 |
| 현재 검증 결과 | `timing_anchor_errors(state, policy)` = 오류 0개 (읽기 전용 실행, 쓰기 없음) |
| 상태 쪽 현황 | MVLL anchor 396·완료 슬롯 0·보유 278 / SOXL anchor 99·완료 SOXL-R25(24주)·보유 75(99−24 일치) |
| 대조 도구의 접촉 | `kiwoom_broker_shadow.py` NEVER_TOUCHED_FIELDS에 `timing_plan` 포함(대조는 이 필드를 쓰지 않는다). 보유가 바뀌면 `TIMING_PLAN_TICKER_CHANGED` 경고만 붙는다(차단 아님) |
| 키움 승인 고정 범위 | `reconcile_broker_state.py`만 포함. `timing_engine.py`·`alert_policy.json`은 미포함 |

S7 보고서 §1c가 이미 같은 사실을 예고했다: 슬롯 은퇴 뒤 사용자가 수동으로 보유를 줄이면 앵커 등식은 영구히 맞지 않고, 그 상태 값은 "읽히지 않는 이력"으로 남는다.

## 3. 선택지 (NO_CHANGE → REMOVE/SIMPLIFY → REUSE → REPLACE → ADD 순)
| 안 | 내용 | 판정 |
|---|---|---|
| A. NO_CHANGE (권고) | 앵커 396을 이력으로 둔다. 이 문서로 사유 기록 | K0 |
| B. 앵커를 278로 변경 | 상태 파일 쓰기 필요. anchor_id·source_state_revision·broker_as_of와 불일치, 정책 부활 시 새 앵커 규칙과 충돌 | 불필요 + K2 이상(쓰기 경로 규칙 위반 위험) |
| C. timing_plan.positions.MVLL 제거 | 상태 구조 변경, 경고(`TIMING_PLAN_TICKER_CHANGED`) 소거 | K2~K3, 효과는 경고 1종 제거뿐 |
| D. 엔진이 은퇴 종목 앵커 검사를 명시적으로 건너뛰게 수정 | S7 보고서가 제안한 방식. 지금은 positions={}라 사실상 같은 효과 | 불필요, 정책 부활 시 재검토 |

## 4. 다시 열어야 하는 조건 (이때만 새 앵커를 정한다)
1. `holding_timing_rules.positions`를 다시 채우는 정책 변경(= K3, 사용자 승인·독립 Judge). 그때 새 `anchor_id`와 함께 현재 검증된 보유로 새 앵커를 정하고, 쓰기는 대조 apply("확인 <코드>") 또는 승인된 Builder 경로로만 한다.
2. 대조 경고 `TIMING_PLAN_TICKER_CHANGED`가 실제 판정을 막기 시작할 때(현재는 경고).

## 5. 남는 위험
- 경고 `TIMING_PLAN_TICKER_CHANGED`는 MVLL·SOXL 보유가 바뀔 때마다 계속 뜬다(소음, 무해).
- 정책을 다시 켜는 사람이 이 값을 현재 수량으로 착각할 수 있다. 4절 조건에 이 문서를 인용해 막는다.
- "확인 필요": 은퇴가 사용자 승인된 정책 결정인지(HEAD에 반영되어 있음)는 S7 승인 기록 원문으로 확인하지 않았다.
