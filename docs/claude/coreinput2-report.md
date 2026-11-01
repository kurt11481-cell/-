---
id: coreinput2-report
title: "자동 코어 입력 문서 보호 2차(coreinput2) — Builder 보고"
date: 2026-11-01
source: docs/claude/coreinput2-builder-prompt.md
---

## 결과
- 07:45 decide가 읽는 docs/claude 입력 4종이 미커밋·없음·링크·git 실패·가드 오류이면 매수 주문표를 막는다. 가드가 막은 날은 재배치 후보도 빠지므로 매도는 후보 없는 날과 같은 계산이 된다. 그래서 매도 regret 열·단계·수량·swap_pair가 달라지거나 REGRET_ZERO, LOT_ZERO, DEADBAND로 그날 매도 주문표가 안 나올 수 있다.
- 대상 테스트 `test_auto_core*`: 580건 실행, 실패 1건, 건너뜀 1건. 실패는 지시문에 적힌 기준선 실패 `RegistryTests.test_real_registry_is_schema_valid_and_every_hash_matches`(symbol='PLTR') 하나뿐이다.
- 건너뜀 1건은 새 테스트 파일 밖의 기존 테스트다(새 파일에는 skip 없음, 1차 보고와 같은 건수). 어느 테스트인지는 실행 출력에 나오지 않아 특정하지 못했다. 기준선과의 비교는 파이프라인 checks가 한다.
- 스키마 감사 PASS. 전체 스위트는 지시문대로 돌리지 않았다.

## 바뀐 줄
| 파일:행 | 내용 |
|---|---|
| `manage-us-stock-strategy/scripts/auto_core_inputs.py:200-205` | `_guard_label` 새 함수(repo 상대 posix, repo 밖이면 파일 이름, 마지막 경로 조각은 링크를 따라가지 않음) |
| `manage-us-stock-strategy/scripts/auto_core_inputs.py:208-251` | `core_input_guard` 새 함수 |
| `manage-us-stock-strategy/scripts/auto_core_decide.py:10-12` | 모듈 설명 2줄 추가 |
| `manage-us-stock-strategy/scripts/auto_core_decide.py:398, 446, 513-514` | `input_committed_check` 인자. None이면 `registry_committed_check` 사용 |
| `manage-us-stock-strategy/scripts/auto_core_decide.py:535` | `_no_new_session`에 check·repo 전달 |
| `manage-us-stock-strategy/scripts/auto_core_decide.py:569-582` | R-REC1 읽기를 m6_docs 바로 뒤로 이동, 가드 호출, `decision["inputs"]["core_input_guard"]`, 알림 |
| `manage-us-stock-strategy/scripts/auto_core_decide.py:693-694` | `evaluate_session(..., input_block=guard["reasons"])` |
| `manage-us-stock-strategy/scripts/auto_core_decide.py:708, 865` | 판정 대조 설명 두 곳을 `_committed_explained`로 묶음 |
| `manage-us-stock-strategy/scripts/auto_core_decide.py:825-837, 842` | `_committed_explained` 새 함수, `_no_new_session` 인자 |
| `manage-us-stock-strategy/scripts/auto_core_decide.py:973, 987-991, 1146` | `input_block` 키워드, 설명, `ctx["input_block"]` |
| `manage-us-stock-strategy/scripts/auto_core_tickets.py:740-742` | 기존 재배치 후보 대입 뒤에서 input_block이 있으면 `redeploy_candidate = None` |
| `manage-us-stock-strategy/scripts/auto_core_tickets.py:822-824` | `_plan_buy` 사유에 research 사유 바로 뒤로 input_block 추가 |
| `manage-us-stock-strategy/tests/test_auto_core_input_guard.py` | 새 파일, 30건(사례 a~l + 읽기 순서, 실제 매도 주문표 2건, 후보가 매도를 좌우하는 경우 1건 등) |

기존 테스트·스키마·`m6_listed`·EV3 정규식·`registry_committed`·06:15 T1 파일은 바꾸지 않았다.

## 가드 검사 목록과 사유 문자열
검사 목록: `docs_dir / RECOVERY_GATE_DOC.name`, `watchlist_path`, `m6_documents`와 같은 glob(`M6_PREFIX + "*.md"`, 같은 정렬)의 파일 전부. `explained_path`는 가드 목록이 아니라 `_committed_explained`가 따로 검사한다(연속 일수 표시에만 쓰임, 매수를 막지 않음).

| 문자열 | 언제 |
|---|---|
| `CORE_INPUT_MISSING:<경로>` | R-REC1 문서 없음 |
| `CORE_INPUT_UNCOMMITTED:<경로>` | 미추적·수정됨, git 실패, check 예외, 심볼릭 링크. 왜 그런지는 `details[<경로>]`에 적힘(`REGISTRY_UNCOMMITTED`, `REGISTRY_GIT_UNAVAILABLE`, 예외 이름, `SYMLINK`) |
| `CORE_INPUT_GUARD_ERROR:<예외 이름>` | 가드 안의 예상 못 한 예외. 이때 status BLOCKED이고 decide는 FAIL이 아니다 |
| `EXPLAINED_FILE_UNCOMMITTED` | 설명 파일이 링크·미커밋·check 예외. `compare.explained_errors` 맨 앞, `explained = []` |
| 알림 code `CORE_INPUT_UNCOMMITTED` | reasons가 직전 기록과 다를 때만 1건, push true |

알림 한 줄(B절 그대로): "자동 코어 입력 문서 미커밋 — 매수 주문표 막힘·재배치 후보 빠짐(매도는 후보 없는 날처럼 계산): <경로들> — Cowork 커밋 확인". `test_i_first_day_pushes_once`가 글자 그대로 확인한다.

관심 명단 파일이 없을 때는 지시문대로 사유를 만들지 않는다. 파일이 없으면 비보유 종목만 빠지고 보유 종목 매수 경로는 남는다(`load_watchlist` UNREADABLE = 관심 종목 없음, `auto_core_inputs.py:148-157`). 이 경로는 1차 보고와 같고 이번에 바꾸지 않았다.

## 읽기·검사 순서
registry 읽기 → watchlist 읽기 → M6 읽기 → R-REC1 읽기 → 가드(R-REC1, 관심 명단, M6 순서로 check) → 연구 기록 대기(최대 08:30) → 나머지. `test_guard_runs_before_the_research_wait`가 이 순서를 확인한다. 가드는 `_no_new_session` 분기 뒤에 있어서, 새 세션이 없는 날은 돌지 않는다. 그날은 주문표가 새로 나오지 않는다.

## 참고 diff와 다른 곳
| 지시문 항목 | 참고 diff | 이번 실행 | 파일:행 |
|---|---|---|---|
| 1 알림 한 줄 | 이전 문구 | B절 새 문자열(경로 잇는 방식은 같음) | `auto_core_decide.py:580` |
| 2 decide 주석 | "A reason blocks buys only (never gates or card_check)." | "A reason blocks every buy and drops the redeployment candidate; it never enters a gate or card_check." | `auto_core_decide.py:572-573` |
| 3 설명 문장 | "a sell can change or lose its ticket" 수준의 설명, 테스트 이름 2개가 매도를 남겨 둔다는 뜻으로 읽힘 | `core_input_guard` docstring, `evaluate_session` docstring, 테스트 머리말을 지시문의 뜻(regret 열·단계·수량·swap_pair, 주문표 없음 가능)으로 넓힘. 테스트 이름 2개를 `test_j_input_block_drops_the_candidate_and_sells_as_on_a_day_without_candidates`, `test_a_sell_that_needs_no_candidate_gets_its_ticket_with_its_hold_range`로 변경(단언은 그대로) | `auto_core_inputs.py:215-217`, `auto_core_decide.py:987-991`, 테스트 파일 |
| 4 보고 파일 | coreinput-report.md | coreinput2-report.md, 남은 위험 7 교체 | 이 파일 |
| 5 테스트 | `LINE` 이전 문구, 사례 l 없음 | `LINE`을 새 문자열로, `test_l_first_day_line_names_the_candidate_and_not_the_old_wording` 추가 | `AlertTests` |

위 5가지 밖에서 동작이 달라진 곳은 없다. 사유 문자열·검사 목록·읽기 순서·후보 None 위치·설명 파일 검사는 참고 diff와 같다.

## 반드시 적을 것
- (a) 이 변경은 매수 관문을 조이기만 하고 완화하는 곳이 없다. 재배치 후보 None 때문에 매도 regret 열·단계·수량·swap_pair가 달라지거나 그날 매도 주문표가 안 나올 수 있다(후보 없는 날과 같은 계산 — REGRET_ZERO·LOT_ZERO·DEADBAND). 가드 사유 자체는 gate0·gate1·card_check·`_plan_sell` 사유에 들어가지 않는다. `test_candidate_issues_one_third_and_a_guard_block_ends_in_regret_zero`가 후보가 있으면 1/3 단계로 발행되고 input_block이 있으면 REGRET_ZERO로 발행되지 않으며 그 결과가 `redeploy_ranked=[]`와 같음을 고정한다.
- (b) 커밋된 편집은 막지 못한다. `git update-index --assume-unchanged/--skip-worktree`도 막지 못한다.
- (c) 병합 뒤 첫 새 세션 판정에서 `inputs.core_input_guard.status` OK 확인이 필요하다.
- 주문·권한 줄: 표지 없음.

## 남은 위험
1. 정상 작업도 막힐 수 있다: 23:30 문서 자동 커밋 뒤부터 07:45 사이에 관심 명단이나 M6 문서를 고치고 커밋하지 않으면 그날 매수가 막히고 push가 온다. 의도한 동작이다. 예약 작업의 LLM 프롬프트가 이 문서들을 쓰는 시점은 이번 실행에서 살피지 않았다(확인 필요, 1차 보고에서 이어짐).
2. 알림이 한 번 더 올 수 있다: 직전 기록이 가드까지 가지 못한 날(새 세션 없음, T1 없음 등 조기 종료)이면 `inputs.core_input_guard`가 없어, 같은 사유가 이어져도 다음 날 다시 push된다. 놓치는 쪽이 아니라 더 알리는 쪽이다.
3. 같은 날 재실행: 1차 보고에 따르면 `decision_identity_hash`가 inputs 전체를 쓰므로 `core_input_guard`도 해시에 든다. 기록 모드에서 병합 전 기록이 있는 날 병합 후 재실행하거나, 같은 날 입력 문서를 바꾼 뒤 재실행하면 기존 `_rerun` 경로(HOLD, 주문표 없음)로 간다. 이 경로는 바꾸지 않았다.
4. 문서가 UTF-8로 깨진 경우: R-REC1 또는 M6 본문 읽기 예외는 지금처럼 decide FAIL이 된다(매도 주문표도 없음). 읽기 시점만 F6 앞으로 옮겨졌고, 가드는 읽기 뒤에 돌기 때문에 이 경우를 잡지 못한다.
5. 읽기와 가드 사이의 아주 짧은 틈에 생긴 편집은 놓칠 수 있다(가드의 sha256은 가드 시점 값이다).
6. 새 테스트 파일은 LF다. 다른 테스트 파일은 CRLF다. 고친 기존 파일 3개는 CR 없는 줄이 0건이라 CRLF가 유지됐다(383, 1324, 1308줄).
7. 알림 문구 정정됨. 1차의 문구 불일치는 이번 실행으로 해소됐다.
