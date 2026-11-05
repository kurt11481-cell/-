# 코어 경고 2건 원인과 정리안 (post-apply-policy-mismatch) — 2026-11-05

- 성격: 읽기 진단 + 제안서. 정책·상태·코드 파일은 바꾸지 않았다. 관제판 작업 `post-apply-policy-mismatch`.
- 부딪히는 결정: active-decisions G절 **D4 원가 손실 한도 폐지(2026-10-01)** — 이 경고가 검사하는 규칙이 바로 D4로 폐지된 규칙이다. 원가 손실 한도는 닫힌 질문(top-guideline-review-2026-11-01.md 59·88행)이라 BE·LITE에 새 원가 손실 규칙을 넣는 안은 내지 않는다.

## 1. 결론

두 경고는 **같은 원인 하나**에서 나오고, **표시(소음) 문제다. 주문표·판정에는 영향이 없다.**
원인은 `stock-strategy-system/alert_policy.json`(마지막 커밋 6fdcf90, 2026-10-12 13:05 KST, 작업 트리 변경 없음)의 옛 보유 위험 규칙 목록이 지금 보유와 다르기 때문이다.

| | 정책 파일 `holding_risk_rules.positions` | 실제 보유(11/05 06:15 KST 대조) |
|---|---|---|
| 종목 | SOXL · MVLL · NBIS (+ 소액 예외 NBIL) | BE · LITE · SOXL |

MVLL·NBIS를 판 뒤(10/22 체결, recon-hold-2026-10-23.md)와 BE·LITE를 산 뒤 정책 목록이 갱신되지 않았다. 그 목록의 규칙 자체(SOXL −20%·MVLL −60%·NBIS −10%, 원가 기준)는 10/01 D4로 판정 규칙에서 내려간 것이다(loss-limit-review-s5-policy-proposal-2026-10-01.md 280·593·617행).

## 2. 경고별 원인 (원문 위치)

1. **POLICY_POSITIONS_MISMATCH** — `reconcile_broker_state.py` 80~84행: 보유 종목 집합과 정책 목록 집합이 한쪽이라도 다르면 참. 보유 BE·LITE가 목록에 없고, 목록 MVLL·NBIS가 보유가 아님.
2. **POST_APPLY_ALERT_ENGINE_CHECK_FAILED** — 같은 파일 86~91행이 `evaluate_alerts.leveraged_state_integrity_errors`(evaluate_alerts.py 489~545행)를 돌려 오류가 1건이라도 있으면 FAIL → `kiwoom_broker_shadow.py` 470~471행이 경고를 붙임. 11/05 오류 9건(workspace/outputs/auto-core/2026-11-05/reconcile.json, 생성 2026-11-05 06:15:11 KST):
   - BE·LITE에 보유 위험 규칙도 소액 예외도 없음 / MVLL·NBIS가 보유가 아님(위와 같은 원인)
   - MVLL·NBIS 수량·평균 단가 없음 4건(같은 원인의 반복)
   - BE 신원 미확인·공식 출처 없음, LITE 신원 기록 없음 — 정책 파일 안의 `decision_harness.instrument_registry` 사본 기준. 원본 등록부 `workspace/policies/instrument_registry.json`에도 LITE 없음, BE는 `verified_by_existing_active_policy`(공식 출처 칸 비어 있음).

## 3. 실제 위험인가 — 아니다(표시 문제)

- 설계상 막지 않는 경고: `auto_core_reconcile.py` 1071~1075행 주석 "flags without blocking a record". 11/03·11/04·11/05 reconcile status 모두 OK, 대조 반영(apply) 정상.
- 코어 판정·주문표가 이 규칙을 읽지 않음: 11/05 decision.json(status OK, decision_mode compare)에 holding_risk·MVLL·NBIS 언급 0건. 주문표 상수는 `auto_core_tickets.py` 57~65행(노출 목표·상한, LITE는 1배 미등록 목록으로 셈).
- 이 규칙을 쓰던 옛 일일 알림 엔진(evaluate_alerts·orchestrator·portfolio_decision_dashboard)은 지금 예약 작업 지시문 어디에서도 부르지 않음(docs/claude/scheduled-prompts/*.txt 검색 0건).
- 처음 나온 날: 2026-10-23 reconcile.json(10/22까지는 없음). 그 뒤 대조가 돈 날마다 같은 내용.
- **진짜 위험은 하나뿐**: 매일 같은 경고 9줄이 나와 새 이상이 생겨도 묻힌다(관제판 why 칸과 같음). 그리고 누군가 옛 엔진을 손으로 돌리면 BE에서 규칙 없음 오류가 난다(portfolio_decision_dashboard.py 517행 — 예약 경로 아님).

## 4. 정리안

| 안 | 내용 | 경로 | 판단 |
|---|---|---|---|
| **A (추천)** | 코드에서 대조 뒤 검사가 **폐지된 원가 손실 목록과의 대조**를 경고로 올리지 않게 하고(D4 근거, 정보 칸에만 남김), 종목 신원은 정책 파일 사본이 아니라 원본 등록부 기준으로 본다. 다른 검사(수량·스냅샷 신선도·소액 예외 한도·타이밍 기준)는 그대로. | 개발 큐(scripts 수정, 일반 경로) + Judge. 정책 파일 안 건드림 | 경고 9줄 → 신원 미등록(LITE) 같은 진짜 남은 일만 남음 |
| B | 정책 파일 `holding_risk_rules`를 D4에 맞게 정리(MVLL·NBIS 제거, 엔진 범위 변경) | K3·권한(정책 파일). shadow_acceptance·provenance 해시 영향 조사 필요(s5 제안서 299·572행) | 무겁고 영향 범위 확인 필요 |
| C | 현행 유지 — 비서·통합점검이 이 두 경고를 '알려진 잔재(D4)'로 분류만 | 문서·지시문 | 경고는 계속 남음 |

하지 않음: BE·LITE에 원가 손실 규칙 추가(닫힌 질문), 정책·상태 파일 직접 수정, 경고 숨기기만 하는 지시문 변경.

결론을 바꿀 조건: 코어 판정·주문표 또는 예약 작업이 `holding_risk_rules`를 읽는 경로가 새로 발견되면 위험으로 다시 분류한다.

## 5. 남는 별건 (A와 함께 보면 됨)

- LITE는 원본 종목 신원 등록부에 기록이 없다(BE는 공식 출처 칸 빈칸). LITE는 11/02 Marvell 합병 8-K가 있어 신원 기록을 새로 쓸 때 함께 본다(관련 기억 lite-marvell-merger-1104).

## 6. 사장 결정 (2026-11-05)

- 2026-11-05 13:20:36 KST, 사장 결정 카드 "A 코드 정리 (추천)" 선택(카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9KmPV2aNmo9gsrpx86fTyWZ, 질문 "매일 나오는 코어 경고 2건을 어떻게 정리할까요?", 계정 = 사장).
- 실행: 개발 큐 `postapply-d4`(authority — reconcile_broker_state.py가 보호 경로, Builder Opus → Judge → 병합은 사장 결정 + -ApproveAuthority). 지시문 docs/claude/postapply-d4-builder-prompt.md.
