---
id: kiwoom-block-fix3-report
title: "kiwoom-block fix3 Builder 요약 — 병합 뒤 깨지는 테스트 3건 수정 + 보고서 정정"
date: 2026-10-25
class: "권한(K3) 후속, 테스트·문서만. 다음: 별도 읽기 전용 Judge(테스트 실행 필수) → 병합은 사장 PowerShell 한 줄"
base: c9c0877 (worktree-kiwoom-block-fix3, 미커밋)
authority: "order_authority=false · quantity_authority=none · 키움 호출 0건 · 허용 확대 0건 · settings.json·훅·deny 변경 0건"
consumers: "kiwoom-block fix3 Judge · 사장(병합 결정)"
---

# 결론
1. **실패 3건을 재현했고 고쳤다.** c9c0877 그대로에서 `test_settings_json_p9`(26 != 23), `ProposedSettingsOnlyAdd.test_added_deny_entries_come_from_the_approved_list`(0 < 3), `ProposedSettingsOnlyAdd.test_only_the_hooks_key_is_added_and_other_keys_are_unchanged`('hooks')가 실패했다.
2. **수정 뒤 세 묶음 모두 OK다**: 훅 Ran 25(23 + 새 시험 2) · dev_pipeline Ran 126 · approval Ran 28. 새 실패 0, skip 0. 병합 전 상태(settings = 기준 7f98f28)도 스크래치 사본으로 통과를 확인했다.
3. **단언은 약해지지 않았다.** deny 삭제, 임의 줄 추가, 중복, `hooks` 삭제는 모두 최소 한 시험에서 실패한다(스크래치 사본 변이 17가지).
4. **문서 정정**: "한계"에 우회 계열 7개 추가(현재 훅 통과·bash에서 `--confirm` 됨을 실제 확인, 코드 보강은 NO_CHANGE). 28건 계산을 8건(2×4) + 20건(5×4)으로 고침(다시 셈). "병합 뒤 확인" 5번 추가.
5. 자세한 내용: docs/claude/kiwoom-block-builder-report.md 끝의 "fix3 반영" 절.

# 바뀐 파일과 sha256 (CRLF 그대로)
| 파일 | fix3 뒤 sha256 (바이트) |
|---|---|
| manage-us-stock-strategy/tests/test_dev_pipeline.py | eff5db3ac07e04e263095ec3d6a1133f7500c0499d3bd3b8389c8bce7ba3ac61 (97262) |
| manage-us-stock-strategy/tests/test_kiwoom_order_block_hook.py | 87c055b7d9c651239e359def8bb2e752c032425560c02dc26c300a588a9f0f5f (22208) |
| docs/claude/kiwoom-block-builder-report.md | 45eef8cb093b7481c5a71b1ed0c393b04822fc35fb36c12ec76179ee6434ce4a (62435) |
| docs/claude/kiwoom-block-fix3-report.md (새) | 이 파일 — 자기 자신은 적을 수 없음 |

변경 없음: `.claude/settings.json` 459cd04f…(제안 파일과 같음), `.claude/hooks/kiwoom_order_block.py` 2818d79f….

# 지시문보다 더 한 것
- 새 시험 `test_base_constant_has_the_base_shape` 1개(기준 상수가 deny 23·ask 8·키 3개인지). 상수가 실수로 바뀌는 것을 막는다. 빼려면 이 시험만 지우면 된다.
- 읽기 전용 확인으로 `test_auto_core*`·`test_reconcile_broker_state.py`·`test_portfolio_exposure_judge_fixes.py`도 돌렸다(아래).

# 다른 settings 단언 확인 (병합 뒤 상태)
2차 Judge가 "포함 여부만 보므로 영향 없음"이라고 한 세 곳(judge-2.txt 91행)을 이 워크트리(병합 뒤 settings)에서 돌렸다.
- `-p "test_reconcile_broker_state.py"` → Ran 56, OK. `-p "test_portfolio_exposure_judge_fixes.py"` → Ran 29, OK.
- `-p "test_auto_core*"` → Ran 529, FAILED (failures=1, skipped=1). 실패는 `test_auto_core_decide.RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches`(symbol='PLTR', `CARD_SECTION_CHANGED`·`CARD_NOT_ACCEPTED_IN_WATCHLIST`, 1339행)이다. settings와 관계없는 **카드 등록부 데이터 검사**이고, fix3가 바꾼 3개 파일은 이 검사가 읽는 파일이 아니다. 그래서 c9c0877에도 있는 기존 실패로 본다. fix3 범위 밖이라 고치지 않았다. PLTR 카드·등록부를 맞추는 일은 별도로 처리해야 한다(대화형 세션의 카드 수락 절차). settings 관련 단언(1603행 근처)은 실패 목록에 없다.

# 하지 않은 것
훅·settings·deny·CLAUDE.md·tools/**·키움 패키지 수정 0, 키움 도구·CLI 실행 0, 비밀 접근 0, 커밋·push·병합 0. docs/claude/_pending·관제판 갱신은 허용 파일 밖이라 하지 않았다. BLOCKED.md 없음.
