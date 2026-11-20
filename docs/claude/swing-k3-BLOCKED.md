---
id: swing-k3-BLOCKED
date: 2026-11-20
status: "RESOLVED 2026-11-20 16:5x KST"
reason: "지시문 '테스트' 절: 허용 파일 밖 기존 테스트가 바뀌어야 통과 → 멈추고 여기 적음"
worktree: ".claude/worktrees/swing-k3 · 브랜치 worktree-swing-k3 · HEAD 0878e76 · 변경은 커밋하지 않은 채 그대로"
---

# swing-k3 BLOCKED — 허용 파일 밖 기존 테스트 2건

등록부·정책·코드·허용된 테스트 수정은 끝났고(보고 docs/claude/swing-k3-report.md), 대상 테스트를 돌린 결과 **허용 파일(머리말 allowed_files) 밖의 기존 테스트 2건**이 이번 변경 때문에 새로 실패한다. 지시문대로 그 파일은 고치지 않고 멈췄다.

## 1. manage-us-stock-strategy/tests/test_auto_core_qqq_b.py:34 — `test_1_lists`
- 원인: 22행 `OLD_APPROVED_BUY = ("BE", "MU", "NBIS", "DELL", "AMD", "SOXL", "TQQQ", "DRAM", "PWR", "LITE")`를 34행 `assertEqual(tickets.APPROVED_BUY, OLD_APPROVED_BUY)`로 통째 고정(QQQ 등록 때 'APPROVED_BUY는 안 바뀜' 고정). 이번 C절(PLTR·CRWD 추가)과 정면으로 부딪힌다.
- 실패 원문: `Tuples differ: (… 'PWR', 'LITE', 'PLTR', 'CRWD') != (… 'PWR', 'LITE')`
- 메울 변경(1줄, test_qqq_registration.py 77행과 같은 방식): 34행을 `self.assertEqual(tickets.APPROVED_BUY[:10], OLD_APPROVED_BUY)`로. 22행 상수와 35행 `assertNotIn("QQQ", …)`는 그대로.
- 기준선: 0878e76에서 통과(test_auto_core* 기준선 실패는 아래 4절의 SOXL 1건뿐).

## 2. manage-us-stock-strategy/tests/test_validate_decision_record.py:39 — `test_valid_watch_only_fixture_passes`
- 원인: 픽스처 manage-us-stock-strategy/tests/fixtures/decision-record.valid.test-only.json 7행 `"instrument_registry_version": "2026-09-02-lmt-instrument-registry-v1"`가 실제 등록부의 registry_version과 같아야 한다(validate_decision_record.py `instrument registry version mismatch`). 지시문 A절대로 registry_version을 `2026-11-20-swing-k3-instrument-registry-v1`로 바꿔 어긋남.
- 실패 원문: `'REJECTED' != 'WATCH_ONLY'` · errors `['instrument registry version mismatch', 'embedded deterministic gate status WATCH_ONLY does not match computed REJECTED', …]`
- 기준선: 0878e76에서 통과.
- 메울 길(둘 중 하나):
  - ⓐ registry_version을 옛 값으로 되돌린다(등록부 3행 1줄, 허용 파일 안). QQQ 등록(qqq-reg) 때도 버전을 올리지 않았다. 값이 행동을 바꾸는 곳은 이 검증 하나뿐이고, 등록부 변경 추적은 alert_policy 177행 해시가 맡는다. 되돌리면 필요한 해시도 다시 계산(같은 테스트 b가 확인).
  - ⓑ 픽스처 7행을 새 버전으로(허용 파일 밖 1줄 추가 허용 필요). 다른 두 사용처(test_v2_1_hardening.py·test_evaluate_outcome.py)는 버전을 비교하지 않아 통과 확인.

## 3. 결정이 필요한 것 (지시문 저자·사장)
- 1번: allowed_files에 `test_auto_core_qqq_b.py(34행만)` 추가 여부.
- 2번: ⓐ 버전 유지(허용 범위 안에서 해결) / ⓑ 픽스처 7행 허용 추가.
- 권장: 1번 추가 + 2번 ⓐ. 결정되면 같은 worktree에서 두 줄만 고치고 대상 테스트를 다시 돌린다.

## 4. 이번 변경과 무관한 실패(고치지 않음)
- test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches (symbol='SOXL') — 기준선(0878e76)에서도 실패.
- test_portfolio_decision_order_intent.OrderIntentOnlyTests.test_lmt_candidate_classification_is_verified_but_non_actionable (ERROR) — 기준선에서도 실패.
- test_portfolio_decision_dashboard…test_real_historical_grade_b_fixture_is_schema_valid_but_has_no_plan — 1503행 픽스처 `workspace/outputs/manual-portfolio-analysis/…/manual-portfolio-analysis.json`이 git에 없는 파일이라 새 worktree에 없음(`fixture.is_file()` False). 기준선은 이 worktree에서 따로 재지 않음 — 원인이 파일 부재라 이번 변경과 무관.

## 5. 진행 (2026-11-20 16:44 KST 이후)
- 결정: 사장 결정 카드 2026-11-20 16:44:43 KST '1줄 고침 + 이름 그대로'(cmsg_0137MRzn9nuDvvQmVxm6WeX9W7RfSGDrByRLbAHeUHHdoT, 코디네이터 전달).
- **2번 해소**: 등록부 3행 registry_version을 `2026-09-02-lmt-instrument-registry-v1`로 되돌림 → alert_policy.json 177행 required_canonical_sha256 = `85fb33b34eb1713c32fa10f4d5cf04061a509963da4f02ba8b391a3509e8bba9`(canonical_hash 재계산). test_validate_decision_record Ran 3 OK · test_swing_k3_registration Ran 8 OK · test_qqq_registration Ran 8 OK · test_reconcile_broker_state Ran 57 OK. 픽스처는 손대지 않음.
- **1번 미해소**: test_auto_core_qqq_b.py 34행 수정이 이 세션의 도구 권한 검사(자동 모드 분류기)에서 거부됨 — 결정이 코디네이터 전달로만 들어와 사장 직접 지시로 확인되지 않음. 사장 직접 입력으로 다시 지시하거나, 사장이 직접 34행을 `self.assertEqual(tickets.APPROVED_BUY[:10], OLD_APPROVED_BUY)`로 고치면 해소.
- **1번 해소**: 사장 직접 입력 2026-11-20 16:52:34 KST 'test_auto_core_qqq_b.py 34행 고쳐' → 34행 `self.assertEqual(tickets.APPROVED_BUY[:10], OLD_APPROVED_BUY)`. 다시 실행: test_auto_core* Ran 667 · failures 1(기준선 SOXL만) — 새 실패 0.
- **상태: 해소.** 남은 실패는 4절 기준선 2건뿐.
