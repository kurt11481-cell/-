---
id: dst-label2-builder-prompt
title: "종가 검증 인정 시차에 -05:00 추가 — 2026-11-02 겨울 세션 측정 뒤 (dst-label2)"
date: 2026-11-03
class: "authority(K3 — 종가 검증 인정 범위 확대, H2 표시). 개발 큐 authority: Builder Opus → Judge → 병합은 사장 승인 + -ApproveAuthority"
source: "사장 \"결정 dst-label: A\"(2026-10-28 08:32 KST, 사장실 스레드 직접 입력). 측정 docs/claude/dst-label-measure-2026-11-03.md"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태 파일 쓰기 없음"
weekly_user_touch: "0 (병합 결정 1번)"
---

## 재실행 사유
1차(dst-label, 2026-11-03 11:30 KST BLOCKED, docs/claude/dev-runs/dst-label.md): 지시문대로 바꾼 뒤 전체 스위트에서 새 실패 2건이 나왔다. `manage-us-stock-strategy/tests/test_score_spy_history.py`의 `test_e3_unverified_session_is_left_out`·`test_e4_only_unverified_sessions_is_invalid`가 2026-01-05(-05:00) 세션을 "미확인" 표본으로 쓰는데(27행 WINTER_SESSION), -05:00 인정으로 그 세션이 확인됨이 됐다. 이 파일이 허용 목록에 없어 Builder가 멈췄다. 이번에는 이 파일을 허용하고 두 테스트만 고친다(1차 Builder 권고안).

## 목표
`manage-us-stock-strategy/scripts/regular_session_close_history.py` 64행 `LABEL_VERIFIED_UTC_OFFSETS = ("-04:00",)` 때문에 2026-11-02(미국) 세션부터 모든 종목 종가가 `BAR_LABEL_TIMEZONE_UNVERIFIED_FOR_UTC_OFFSET`로 미확인이 되고, 노출 점검이 required_price_missing으로 매수를 막는다(11/03 자동 코어 HOLD). 11/02 세션 측정(docs/claude/dst-label-measure-2026-11-03.md)으로 겨울에도 키움 30분봉 표기가 미국 동부 현지 시각임을 확인했다. 그래서 "-05:00"을 인정 시차에 더한다. 이것이 fx-3 때 미리 증명해 둔 "한 줄 변경"이다(test_regular_session_close_history.py 143~165행).

## 바꿀 내용
1. `manage-us-stock-strategy/scripts/regular_session_close_history.py`
   - 64행: `LABEL_VERIFIED_UTC_OFFSETS = ("-04:00", "-05:00")`.
   - 61~63행 주석: "-04:00은 2026-04-01..09-30, -05:00은 2026-11-02 세션(측정 docs/claude/dst-label-measure-2026-11-03.md)에서 미국 동부 현지 시각 표기로 확인. 다른 시차는 측정 전까지 미확인"이라는 뜻으로 고친다(영어, 짧게).
   - 238~239행 판정 코드·사유 이름은 바꾸지 않는다. 다른 함수·상수 무변경.
2. `manage-us-stock-strategy/references/portfolio-exposure-review.md` 72행: "(only `-04:00` so far; remeasure after 2026-11-02)"를 "(`-04:00` and `-05:00`, measured 2026-11-02)" 뜻으로 고친다. 다른 줄 무변경.

## 테스트 (`manage-us-stock-strategy/tests/test_regular_session_close_history.py`)
- `test_early_close_uses_the_bar_before_the_early_close`(약 127~141행): 139~141행의 "미확인" 단언을 이제 맞는 기대로 바꾼다 — 이 테스트의 달력이 ACTIVE가 아니면 `SESSION_CALENDAR_NOT_ACTIVE`는 남을 수 있으니, `BAR_LABEL_TIMEZONE_UNVERIFIED_FOR_UTC_OFFSET`가 unverified_reasons에 **없음**(assertNotIn)으로 바꾸고 verified 단언은 실제 결과에 맞춘다. 주석도 고친다.
- `test_early_close_is_verified_when_the_winter_offset_is_added_to_the_verified_set`(약 143~165행): patch 없이도 verified=True가 되므로, 157~158행 "unmeasured" 단언을 "상수에 -05:00이 들어 있다"(`self.assertIn("-05:00", rsch.LABEL_VERIFIED_UTC_OFFSETS)`)와 patch 없는 결과 verified=True로 바꾼다. 테스트 이름·주석도 지금 상태에 맞게 고친다.
- 새 테스트 1개(같은 파일 끝): 측정하지 않은 시차는 여전히 미확인임을 증명한다. 예: `mock.patch.object(rsch, "LABEL_VERIFIED_UTC_OFFSETS", ("-04:00",))`로 되돌리면 같은 겨울 입력이 다시 `BAR_LABEL_TIMEZONE_UNVERIFIED_FOR_UTC_OFFSET`가 됨. (fail-closed 경로가 살아 있음을 지킨다.)
- `manage-us-stock-strategy/tests/test_score_spy_history.py`: `test_e3_unverified_session_is_left_out`·`test_e4_only_unverified_sessions_is_invalid` 두 함수 본문만, 히스토리를 만드는 호출부터 단언까지를 `with mock.patch.object(rsch, "LABEL_VERIFIED_UTC_OFFSETS", ("-04:00",)):` 안에 넣어 그 세션이 다시 미확인이 되게 한다(이 파일은 이미 `mock`과 `rsch`를 import한다 — 14·21행). 단언 문장은 한 글자도 바꾸지 않는다. 27행 WINTER_SESSION 주석은 "patched back to the summer-only set in e3/e4 so the session stays unverified" 뜻으로 고친다. 다른 함수 무변경.
- `manage-us-stock-strategy/tests/test_portfolio_exposure_fail_closed.py`는 시나리오로 사유를 직접 넣는 테스트라 바꾸지 않는다(허용 파일 아님).
- 실행: 아래 두 명령만, 글자 그대로(앞에 환경 변수 등을 붙이지 않는다 — 자동 거부됨).
  - `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_regular_session_close_history*"`
  - `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_portfolio_exposure*"`
  - `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_score_spy_history*"`
  전체 스위트·기준선 비교는 파이프라인이 한다. `test_kiwoom_order_block_hook.py`나 `.claude/` 아래 파일을 불러오는 테스트·명령은 실행하지 않는다(보호 경로에 .pyc가 생기면 STOP_PROTECTED).

## 지켜야 할 것 (어기면 Judge FAIL)
1. `auto_core.py`·`reconcile_broker_state.py apply`·`kiwoomcli` 실행 금지. 키움 호출·예약 작업 변경·상태/정책/일지/원장/종가 이력·페이지 쓰기 없음. "auto_core.py"가 든 명령 금지.
2. 인정 시차는 "-04:00", "-05:00" 두 개만. 다른 시차 추가·판정 우회·사유 삭제 금지. 달력 권한(ACTIVE) 검사, 페이지 해시·재구성 일치 검사, 연속성 검사 무변경.
3. 주문·권한 줄(order_authority·quantity_authority·execution_quantity·kill_switch) 변경 없음. 노출 한도·관문·매도 차단 변경 없음.
4. 판단이 안 되면 미확인(fail-closed).
5. 허용 파일만. 각 파일의 기존 줄바꿈 유지(작업 트리 CRLF, 저장소 LF — 편집 도구가 바꾸면 보고서에 `git diff --ignore-cr-at-eol --stat` 결과를 적는다).
6. git commit·push·병합 없음.

## 보고 docs/claude/dst-label2-report.md
바뀐 줄(파일:행), 대상 테스트 결과, 남은 위험. 반드시 포함: (a) 이 변경은 인정 범위 확대(H2) — 근거는 측정 문서의 세 기준, 공개 공식 종가 직접 대조는 확인 필요로 남음 (b) 다음 서머타임 시작(2027-03-14) 뒤 -04:00 세션은 그대로 인정, 다른 시차는 계속 미확인 (c) 병합 뒤 첫 06:15 실행(다음 날)에서 11/02 이후 세션이 verified로 바뀌는지 확인 필요 — 저장된 이력은 실행 때 페이지에서 다시 만들어지므로 따로 고칠 파일 없음(확인 필요). (d) 범위 밖 발견: `manage-us-stock-strategy/scripts/validate_integrated_authority_production.py` 108~109행이 개장·마감을 `-04:00`으로 고정 — 고치지 않고 위치만 적는다. 이 보고서 문장에는 주문·권한 표지 문자열을 그대로 적지 말고 "표지 없음"이라고만 쓴다.

## Judge 확인 항목
1. diff가 64행 상수와 61~63행 주석, 참조 문서 72행, test_regular_session_close_history.py(기존 2개 함수 단언 + 새 테스트 1개), test_score_spy_history.py(e3·e4를 patch로 감싸기 + 27행 주석, 단언 무변경)뿐이다.
2. 인정 시차가 정확히 ("-04:00", "-05:00")이고, 238~239행 판정·사유 이름 무변경.
3. 새 테스트가 "-05:00"을 빼면 다시 미확인이 됨을 증명한다(fail-closed 경로 유지).
4. 달력·해시·재구성·연속성 검사 무변경, 주문·권한 줄 변경 없음, 허용 파일만, 줄바꿈 유지, 새 실패 0(파이프라인 checks), 보고 (a)~(d).

```dev-run
{"task_id": "dst-label2", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 80, "builder_timeout_min": 45, "allowed_paths": ["manage-us-stock-strategy/scripts/regular_session_close_history.py", "manage-us-stock-strategy/references/portfolio-exposure-review.md", "manage-us-stock-strategy/tests/test_regular_session_close_history.py", "manage-us-stock-strategy/tests/test_score_spy_history.py", "docs/claude/dst-label2-report.md"], "target_tests": ["test_regular_session_close_history*.py", "test_portfolio_exposure*.py", "test_score_spy_history*.py"], "commit_message": "fix(closes): accept -05:00 bar labels after the 2026-11-02 winter-session measurement"}
```
