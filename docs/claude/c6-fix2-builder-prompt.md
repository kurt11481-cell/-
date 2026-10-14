---
id: c6-fix2-builder-prompt
title: (재실행 c6-fix -> c6-fix2) 코어 C6± 반등·눌림(전일 대비 방향) 조건 추가 — 규칙 문구에 코드를 맞춤
date: 2026-10-14
class: 권한 경로(auto_core*.py, tests/test_auto_core*.py) — dev-run class authority(경로 때문). 의미: 일반 변경(규칙 파일·상수·관문 기준값 불변, 조건 1개를 더해 충족을 좁히기만 함)
decision: 사용자 "결정 c6-fix: 진행"(2026-10-14 13:31 KST, Cowork 대화) — 같은 내용의 재실행
evidence: docs/claude/c6-fix-review-2026-10-14.md · docs/claude/redesign-t2-day2-check-2026-10-14.md 18행 · docs/claude/redesign-t2-judge-report-2026-10-10.md 82행(K1 7)
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 키움 호출 없음 · 정책·상태 쓰기 없음
weekly_user_touch: 0 (병합 1번: .\tools\dev-merge.ps1 c6-fix2 -ApproveAuthority — 경로 때문에 붙는 플래그)
---

```dev-run
{"task_id": "c6-fix2", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 80, "builder_timeout_min": 45, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_rules.py", "manage-us-stock-strategy/tests/test_auto_core_rules.py", "manage-us-stock-strategy/tests/test_auto_core_compare_fix.py", "manage-us-stock-strategy/tests/test_auto_core_decide.py", "manage-us-stock-strategy/tests/test_auto_core_tickets.py", "docs/claude/c6-fix2-report.md"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(auto-core rules): C6 rebound/pullback session must close up/down vs the prior close (rule file line 110, prereg 79 (ii))"}
```

## 재실행 사유 (Cowork 2026-10-14 14:0x KST)

c6-fix 1회차(workspace/outputs/dev-runs/c6-fix)는 BLOCKED: 지시문이 "C5+·C6+ 두 종류 새 충족" 뜻을 지키라고 했는데, 수정 뒤에는 그 짝이 불가능하다(Builder 판단이 맞다, 지시문 결함). 규칙 수정·새 테스트 4개·compare_fix 고정 자료는 1회차에서 통과했다. id는 한 번만 쓸 수 있어 c6-fix2로 다시 돌린다. 이전 worktree/브랜치(worktree-c6-fix)는 건드리지 않는다.

## 목표

`auto_core_rules.raw_common`의 C6±를 규칙 파일 문구대로 고친다. 규칙(docs/claude/integrated-check-prompt-v3.12.2-2026-10-09.txt 110행, v3.12.4 같은 문장): "EMA20 아래에 있던 종가가 EMA20 아래 1.5% 이내까지 **반등한** 세션 다음 세션에 …" ↔ "… **눌린** 세션 …". 지금 코드(330~337행)는 반등·눌림 세션 s = t−1이 전일보다 올랐는지/내렸는지를 보지 않아 규칙보다 자주 충족된다(실자료: MU 2026-10-12 C6−가 10-09 −0.72% 하락일을 "반등"으로 셈).
정의는 사전 등록 docs/claude/c-rule-replay-preregistration-2026-10-09.md 75~76행과 79행 (ii), 리플레이 stock-strategy-system/backtests/c_rule_replay_2026-10-09.py 162~167행과 같게 한다(엄격 부등호).

## 바꿀 내용 (auto_core_rules.py, 이것만)

- `raw["C6-"][i]`의 `_all(...)`에 `_cmp(p_close, "gt", pp_close)` 1개 추가 (c_{t−1} > c_{t−2}).
- `raw["C6+"][i]`의 `_all(...)`에 `_cmp(p_close, "lt", pp_close)` 1개 추가 (c_{t−1} < c_{t−2}).
- 같은 종가(평평)는 반등·눌림이 아니다(엄격). 자료가 없으면 `_cmp`가 None → 기존처럼 unk.
- CONSTANTS·다른 규칙·_event_state·card_raw·모듈 docstring의 정의 외 문장은 바꾸지 않는다. card_raw의 pullback_rebound는 공통 C6+ 배열을 그대로 쓰므로 카드 별칭(U6·BE6·DL6 등)은 자동으로 따라온다.
- 330행 근처에 한 줄 주석: 규칙 110행 "반등한/눌린 세션" = s의 종가가 전일보다 높음/낮음(사전 등록 79 (ii)).

## 테스트

새 테스트(test_auto_core_rules.py, 기존 `series(...)` 도우미 사용):
1. C6−: c_{t−1} ≤ c_{t−2}(반등 아님)이면 none, 같은 종가도 none. 기존 `fail` 예시(98.0 → 98.50 → 98.40)는 hit 그대로.
2. C6+: c_{t−1} ≥ c_{t−2}(눌림 아님)이면 none, 같은 종가도 none. 기존 `rebound` 예시(102.0 → 101.50 → 101.60)는 hit 그대로.
3. c_{t−2}가 None이면 그 세션 raw는 None.
4. MU 실자료 모양(종가·EMA20을 직접 넣음, 평가 세션 마지막):
   종가 10-05~10-13 = 1063.71, 1045.44, 1087.84, 1035.47, 1028.00, 988.96, 953.19
   EMA20 같은 세션 = 1035.27, 1036.24, 1041.15, 1040.61, 1039.41, 1034.60, 1026.85
   기대: 10-07 raw C6+ True, 10-12 raw C6− False(수정 전 True), 마지막 세션 C6+ 상태 hit(5세션 창, 반대쪽 해소 없음). 앞은 EMA 위로 충분히 떨어진 값으로 채워 다른 C6 충족이 없게 한다.

고칠 기존 테스트(수정만 넣으면 3개가 실패한다. 고정 자료의 "눌림" 세션이 실제로는 올랐기 때문):
- test_auto_core_compare_fix.py `EventDayMarginTests.test_card_alias_of_an_event_rule_uses_its_firing_session`: 종가 `[100.0]*60 + [100.5, 100.8, 101.0, 100.9, 100.85]`의 t−3 세션(100.8)이 전일보다 높다. t−3을 100.3으로 바꾼다(`[100.5, 100.3, 101.0, 100.9, 100.85]`). 검사 문장은 그대로다.
- test_auto_core_decide.py `_soxl_two_new_cues`와 test_auto_core_tickets.py `soxl_two_new_cues`: 마지막 줄을 `return closes + [99.85, 100.3, 100.5]`로 바꾼다(t−2를 EMA20 아래로). 그러면 마지막 세션에 새로 충족되는 + 종류가 C5+(new_high)와 C3+(trend_recover)가 된다. 두 도우미는 같은 값을 쓴다.
- 이에 맞춰 **검사 문장 1개만** 바꾼다: test_auto_core_tickets.py 634행 `["new_high", "pullback_rebound"]` → `["new_high", "trend_recover"]`. 이 테스트의 뜻(새 근거 2종류로 SOXL 매수가 열리고, 연구 기록이 없으면 막힌다)은 그대로다. 다른 검사 문장은 바꾸지 않는다.
- 이유(c6-fix 1회차 BLOCKED, 맞는 판단): 수정 뒤에는 C5+와 C6+가 같은 세션에 함께 새로 충족될 수 없다. C5+ 새 충족은 c_{t−1} > max(c_{t−21..t−2}) ≥ c_{t−2}, C6+ 충족은 c_{t−1} < c_{t−2}가 필요해서 서로 모순이다.
- 같은 도우미를 쓰는 test_auto_core_compare_fix.py 300행(T5 불변 two_new_cues)과 test_auto_core_equity_cash.py 229행은 고치지 않는다. 그대로 통과해야 한다.
- Cowork 사본 실측(2026-10-14 14:0x KST): 위 고정 자료 3곳 + 검사 문장 1개 + rules 수정만 넣고 test_auto_core*.py 379개를 돌렸을 때 새 실패 0(남은 2건은 사본 환경 문제로 수정 전에도 같음).

골든·불변 테스트(test_auto_core_risk1r GOLDEN, test_auto_core_compare_fix T5 불변)는 바뀌면 안 된다. Cowork 사본 실측에서 risk1r 8개 해시는 수정 전후가 같았다. 바뀌면 골든을 고치지 말고 보고서에 원인과 함께 적는다(그 회차는 실패로 둔다).

## 지켜야 할 것

- allowed_paths 밖은 건드리지 않는다. 규칙 파일·카드·등록부·정책·상태·스키마 불변.
- 상수 값·관문 기준값(D16) 불변. 조건을 더하기만 하므로 충족은 줄기만 한다(새 충족 0).
- 키움 호출·주문 경로·권한 표지 없음. auto_core.py를 실행하는 명령은 쓰지 않는다(테스트는 `-p "test_auto_core*"`).
- CRLF 파일의 줄 끝을 바꾸지 않는다.

## 보고 `docs/claude/c6-fix2-report.md`

바꾼 줄(파일:행), 새 테스트 목록, 고정 자료를 바꾼 3곳과 이유(바꾼 값), 대상 테스트 결과, 골든 해시 불변 확인.

## 참고 (Cowork 사전 측정, 2026-10-14)

- 8종목 × 135세션(2026-04-01~10-13) 원시 충족: C6− 8→7, C6+ 24→20. 보유 MVLL·NBIS·SOXL은 같다.
- decide 경로 리플레이(auto_core_replay, 2026-07-10~10-13, P-R1·P-R2): 주문표·막힘·후보는 수정 전후 같음. 근거만 다름: DELL 10-08 매수 DL6 빠짐(basis 그대로 충족), MU 10-12·10-13 매도 C6− 빠짐(basis true→false, MU는 관심 종목이라 표시만), MU 매수에 U6 생김.

## Judge 확인 항목

1. 범위: allowed_paths 안. auto_core_rules.py 변경은 C6± 두 조건 + 주석 1줄뿐.
2. 정의: 규칙 110행·사전 등록 75~76·79 (ii)·리플레이 162~167행과 같은 방향·엄격 부등호. C6−와 C6+가 대칭(규칙 104행).
3. 고정 자료 수정 3곳은 값만 바뀌고, 검사 문장 변경은 test_auto_core_tickets.py 634행의 기대 종류 짝(pullback_rebound → trend_recover) 1개뿐이다. 테스트 뜻(사건일 여유값 / 새 근거 2종류로 매수가 열리고 연구 기록이 없으면 막힘)이 유지된다. compare_fix 300행·equity_cash 229행은 바뀌지 않고 통과한다.
4. 새 테스트가 반등 아님·눌림 아님·평평·None·MU 모양을 덮는다.
5. 골든·불변 테스트 불변. 권한 표지·주문 경로·정책/상태 쓰기·키움 호출 없음. 대상·전체 테스트 새 실패 0.
