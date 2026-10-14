# c6-fix2 Builder 보고 (2026-10-14)

지시문: docs/claude/c6-fix2-builder-prompt.md · 규칙: tools/dev_pipeline/builder-rules.md
결과: 완료(BLOCKED 없음). 커밋·병합 없음, 작업 트리에만 남김.

## 바꾼 줄

`manage-us-stock-strategy/scripts/auto_core_rules.py` (`raw_common`, 이 3줄만 추가)
- 331행: 주석 `# Rule line 110 "rebounded/pulled-back session" = s closes above/below its prior close (prereg 79 (ii)).`
- 335행: `raw["C6-"]`의 `_all(...)`에 `_cmp(p_close, "gt", pp_close)` (c_{t−1} > c_{t−2}, 엄격)
- 339행: `raw["C6+"]`의 `_all(...)`에 `_cmp(p_close, "lt", pp_close)` (c_{t−1} < c_{t−2}, 엄격)

정의 대조(이 세션에서 원문 확인):
- 사전 등록 docs/claude/c-rule-replay-preregistration-2026-10-09.md 75행(C6− `c_s > c_{s−1}`)·76행(C6+ `c_s < c_{s−1}`)·79행 (ii).
- 리플레이 stock-strategy-system/backtests/c_rule_replay_2026-10-09.py 163행 `c[t - 1] > c[t - 2]`, 166행 `c[t - 1] < c[t - 2]`.
- 같은 종가(평평)는 엄격 부등호라 충족 아님. c_{t−2}가 없으면 `_cmp`가 None → `_all`이 None(unk, 기존 방식).
- CONSTANTS·다른 규칙·_event_state·card_raw·docstring 불변. card_raw의 `pullback_rebound`(502~503행)는 `common["C6+"]`를 그대로 써서 카드 별칭이 자동으로 따라온다.

## 새 테스트 (manage-us-stock-strategy/tests/test_auto_core_rules.py, `CommonRuleBoundaryTests`)

1. 171행 `test_c6_minus_needs_the_rebound_session_to_close_up`: 98.0→98.50→98.40 hit(기존 예시), 98.60→98.50→98.40(반등 아님) none, 98.50→98.50→98.40(평평) none.
2. 178행 `test_c6_plus_needs_the_pullback_session_to_close_down`: 102.0→101.50→101.60 hit(기존 예시), 101.40→101.50→101.60(눌림 아님) none, 101.50→101.50→101.60(평평) none.
3. 185행 `test_c6_missing_close_two_sessions_back_is_unknown`: c_{t−2}=None이면 raw C6−·C6+ 모두 None.
4. 192행 `test_c6_mu_shape_falling_session_is_not_a_rebound`: 지시문의 MU 종가·EMA20(10-05~10-13)을 그대로 넣고, 앞 23세션은 종가 1200 / EMA20 1000(EMA 위로 1.5% 밴드 밖)으로 채움. 10-07 raw C6+ True, 10-12 raw C6− False, 전체에서 C6+ 충족은 10-07 하나·C6− 충족 0, 마지막 세션 C6+ 상태 hit(반대쪽 C6− 해소 없음), C6− 상태 none.

## 고정 자료를 바꾼 3곳 (값만, 이유: 수정 뒤에는 "눌림" 세션이 실제로 내려야 함)

| 파일:행 | 전 | 후 | 이유 |
|---|---|---|---|
| test_auto_core_compare_fix.py:205 | `[100.5, 100.8, 101.0, 100.9, 100.85]` | `[100.5, 100.3, 101.0, 100.9, 100.85]` | t−3 눌림 세션(100.8)이 전일(100.5)보다 높아 C6+가 더 이상 안 걸림. 100.3으로 내려 t−2 C6+ 발화 유지 |
| test_auto_core_decide.py:482 `_soxl_two_new_cues` | `closes + [100.05, 100.3, 100.5]` | `closes + [99.85, 100.3, 100.5]` | C5+와 C6+는 수정 뒤 같은 세션에 함께 새로 충족될 수 없음(C5+ 새 충족 c_{t−1} > max(c_{t−21..t−2}) ≥ c_{t−2} vs C6+ c_{t−1} < c_{t−2}). t−2를 EMA20 아래로 내려 두 번째 새 종류를 C3+(trend_recover)로 |
| test_auto_core_tickets.py:615 `soxl_two_new_cues` | 같음 | 같음 | 위와 같은 도우미 값 |

검사 문장 변경은 1개뿐: test_auto_core_tickets.py:634 `["new_high", "pullback_rebound"]` → `["new_high", "trend_recover"]`. 테스트 뜻(새 근거 2종류로 SOXL 매수가 열리고, 연구 기록이 없으면 막힘)은 그대로다. 같은 도우미를 쓰는 test_auto_core_compare_fix.py:300(T5 불변 two_new_cues)·test_auto_core_equity_cash.py:229는 고치지 않았고 통과한다.

## 테스트 결과 (2026-10-14, 이 worktree)

- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core_rules.py"`: 44개 OK.
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*"`: 383개 OK(skipped=1). 383 = 지시문 379 + 새 4개. skip 1개는 test_auto_core_replay.py:186 `skipUnless(PAGES.is_dir() ...)`(저장된 30분 페이지가 main checkout에만 있음, worktree 환경 — 이번 변경과 무관).
- 스키마 감사 `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`: PASS, errors [].

## 골든·불변

- test_auto_core_risk1r.py `UnchangedTicketTests.test_tickets_without_risk_1r_hash_as_before`(196행 `assertEqual(measured, GOLDEN)`) 통과 → 골든 해시 불변. GOLDEN(36행)은 고치지 않았다.
- test_auto_core_compare_fix.py `test_t5_decide_record_unchanged_except_margins`(299행)·`test_t5_margins_differ_only_for_hit_event_groups`(317행) 통과.

## 범위·안전

- 바꾼 파일: auto_core_rules.py, test_auto_core_rules.py, test_auto_core_compare_fix.py, test_auto_core_decide.py, test_auto_core_tickets.py, 이 보고서 — 모두 allowed_paths 안.
- `git ls-files --eol`: 고친 5개 파일 모두 `w/crlf` 유지.
- 상수·관문 기준값 불변, 조건만 더함(충족은 줄기만 함). 키움 호출·주문 경로·권한 표지·정책/상태 쓰기 없음. 커밋·git add 없음.
