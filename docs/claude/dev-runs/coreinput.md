# dev-run coreinput — NEEDS_APPROVAL

- 시각(UTC): 2026-11-01T09:00:08Z → 2026-11-01T09:55:52Z
- 기준 커밋(base): `9a7e16bd281b51f1a33e95242f79ae0a135fa6c2` · 메인 브랜치: `codex/master-recovery-expansion`
- 등급(class): authority (사유: AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_decide.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_inputs.py, AUTHORITY_PATH:manage-us-stock-strategy/scripts/auto_core_tickets.py, AUTHORITY_PATH:manage-us-stock-strategy/tests/test_auto_core_input_guard.py)
- 상태: **NEEDS_APPROVAL** · 재시도: 1
- 테스트: 기준선 Ran 3443 · 실패 283 → 변경 후 Ran 3472 · 새 실패 0 · skipped 3->3 · 스키마 감사 PASS->PASS
- diff_hash: `9874005c1f53cc0ee057edaa8e7ca72628a88b13fccf4348d43e9c9107972dfd`
- Judge 파일 sha256: `454892427a9b5b3e39648fe0025ff9a54ff3c87fa56bc6991f34b34179cd5199`
- 사유: 없음
- 다음: `user decision, then .\tools\dev-merge.ps1 coreinput -ApproveAuthority`

## 바뀐 파일

- `docs/claude/coreinput-report.md`
- `manage-us-stock-strategy/scripts/auto_core_decide.py`
- `manage-us-stock-strategy/scripts/auto_core_inputs.py`
- `manage-us-stock-strategy/scripts/auto_core_tickets.py`
- `manage-us-stock-strategy/tests/test_auto_core_input_guard.py`

## Judge 보고 원문 (1회차 FAIL)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | 가드 `auto_core_inputs.py:208-248`, 읽은 직후 검사 `auto_core_decide.py:566-573`, 매수 차단 `auto_core_tickets.py:822-824`, 후보 제외 `auto_core_tickets.py:740-742`. TODO나 하드코딩 없음 |
| G2 범위 | PASS | `changed-files.txt:1-5`가 allowed_paths 5개와 일치, `checks.json:117-118` status OK |
| G3 주문·체결 추정 | PASS | `diff.patch`에 주문 경로, 키움 호출, 가격 기반 체결 추정 없음 |
| G4 쓰기·fail-closed | PASS | 가드는 읽기만 함(`auto_core_inputs.py:221-243`). R-REC1 없음은 `:227-229`에서 차단. 정책·상태·일지 쓰기 경로 없음 |
| G5 비밀 | PASS | 기록은 경로, 사유, sha256뿐(`auto_core_inputs.py:247-248`) |
| G6 테스트 | PASS | 기존 테스트 무변경, 새 파일에 skip 없음, 3443→3471건, `new_failures` 빈 배열, skip 3건 유지(`checks.json:6,411-416`). 발행이 갈리는 사례의 테스트는 G8-4 수정에 포함 |
| G7 class | PASS | 주문 단계, 도구, 예산, 상한, 승인 상품, 대조 불변 조건, 정지 스위치 무변경. class는 이미 authority(`checks.json:107`) |
| G8-1 허용 파일·무변경 | PASS | 스키마, 정책, 기존 테스트가 `changed-files.txt`에 없음 |
| G8-2 입력 목록 | PASS | 5개 파일 grep 결과 빠진 docs/claude 입력 없음. 등록부는 `auto_core_inputs.py:141`, 카드 문서는 `:172-178`로 보호됨. event-calendar는 채점 전용 |
| G8-3 fail-closed | PASS | 미커밋, 링크, git 실패, 예외는 `auto_core_inputs.py:231-246`에서 차단. 문서 본문 읽기 예외의 decide FAIL은 기존 동작(`auto_core_decide.py:567-569`). 4개 입력의 git 추적 여부는 색인 읽기가 권한 거부되어 제안서 44행 기록으로만 확인 |
| G8-4 반례 탐색 | **FAIL** | 가드가 막은 날 후보가 None이 되면 그날 매도 주문표가 사라질 수 있음(`auto_core_tickets.py:742,1085-1092,364-373`). 손계산: 자산 10000, 예산 300, delta 60, 기준가 100, r_max 1/3, up 0.30, down −0.05, 후보 up 0.50·down −0.02. 후보가 있으면 1/3 단계 20주 발행, 없으면 0단계로 `REGRET_ZERO`, 주문표 없음. LOT_ZERO·DEADBAND도 같은 경로로 생길 수 있음(`:1094-1099`). 지시문 지킬 것 2의 "매도 주문표 발행 여부 불변"과 어긋남. 나머지 반례(읽기 시점, hold_eval, `_limit_daily`, `_no_new_session`, 등록부 주입, None 대입 순서)는 문제없음 |
| G8-5 보고·테스트 | **FAIL** | 테스트 a~k 존재, 새 실패 0건. 그러나 보고 (a)의 "표시만 바꿀 수 있고"(`diff.patch:304`)와 "매도는 막지 않는다"(`:263`)가 G8-4 때문에 사실과 다름. 코드 설명 `auto_core_decide.py:11,985`도 같음. 관심 명단이 없어도 보유 종목 매수 경로는 남는데(`auto_core_inputs.py:182-188`, `auto_core_tickets.py:269`), 보고는 "이미 막는다"고 적음(`diff.patch:298`) |

```json
{"verdict": "FAIL", "class_ok": true, "items": [
{"id": "G1", "result": "PASS", "evidence": "auto_core_inputs.py:208-248; auto_core_decide.py:566-573; auto_core_tickets.py:740-742,822-824"},
{"id": "G2", "result": "PASS", "evidence": "changed-files.txt:1-5; checks.json:117-118"},
{"id": "G3", "result": "PASS", "evidence": "diff.patch 전체"},
{"id": "G4", "result": "PASS", "evidence": "auto_core_inputs.py:221-243,227-229"},
{"id": "G5", "result": "PASS", "evidence": "auto_core_inputs.py:247-248"},
{"id": "G6", "result": "PASS", "evidence": "checks.json:6,411-416; tests/test_auto_core_input_guard.py"},
{"id": "G7", "result": "PASS", "evidence": "diff.patch; checks.json:107"},
{"id": "G8-1", "result": "PASS", "evidence": "changed-files.txt:1-5"},
{"id": "G8-2", "result": "PASS", "evidence": "auto_core_inputs.py:141,172-178; auto_core_compare.py:34; auto_core_decide.py:62-63"},
{"id": "G8-3", "result": "PASS", "evidence": "auto_core_inputs.py:231-246; auto_core_decide.py:567-569; 추적 여부는 coreinput-proposal-2026-11-01.md:44 기록만 확인(git 색인 읽기 권한 거부)"},
{"id": "G8-4", "result": "FAIL", "evidence": "auto_core_tickets.py:742,1085-1092,1094-1099,364-373: 재배치 후보 None으로 choose_step이 0이 되면 REGRET_ZERO로 매도 주문표가 사라짐. 지시문 지킬 것 2와 어긋남"},
{"id": "G8-5", "result": "FAIL", "evidence": "diff.patch:263,298,304; auto_core_decide.py:11,985: 보고와 설명이 매도 영향과 관심 명단 차단 범위를 사실보다 좁게 적음"}
], "min_fixes": [
"코드 동작은 바꾸지 않는다. 지시문 C절이 redeploy_candidate None을 요구하므로 공개와 테스트 고정으로 처리하고, 이 동작의 수용 여부는 사장 병합 결정에서 판단한다.",
"docs/claude/coreinput-report.md의 결과 줄과 (a)를 고친다: 가드가 막은 날 재배치 후보가 빠지면 후보 없는 날과 같은 계산으로 REGRET_ZERO, LOT_ZERO, DEADBAND가 되어 그날 매도 주문표가 안 나올 수 있다고 적고, '표시만'과 '매도는 막지 않는다'를 뺀다.",
"auto_core_decide.py:11과 :985-986, auto_core_inputs.py 가드 설명, 새 테스트 파일 머리말의 표현을 고친다: 가드 사유는 매도 게이트에 들어가지 않지만 후보 제외로 매도 결과가 달라질 수 있다.",
"tests/test_auto_core_input_guard.py에 테스트를 더한다: 후보가 있으면 1/3 단계로 발행되고 input_block이 있으면 REGRET_ZERO로 발행되지 않으며, 그 결과가 redeploy_ranked=[]와 같음을 고정한다.",
"docs/claude/coreinput-report.md의 관심 명단 없음 문장을 고친다: 파일이 없으면 비보유 종목만 빠지고 보유 종목 매수 경로는 남는다. 문서가 새로 여는 관문은 없다."
]}
```

VERDICT: FAIL

## Judge 보고 원문 (2회차 PASS)

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| G1 목표 구현 | PASS | 가드 전체 구현 `auto_core_inputs.py:208-250`, 호출과 기록 `auto_core_decide.py:569-581`, 매수 차단 `auto_core_tickets.py:823`, 후보 제거 `auto_core_tickets.py:741-742`. 빈 껍데기, 하드코딩, TODO 없음 |
| G2 범위 | PASS | `changed-files.txt:1-5`는 허용 5개 파일뿐이고 `checks.json:130-131`은 reasons 없음, status OK. 부수 변경 없음 |
| G3 주문·체결 추정 | PASS | diff에 주문 경로, 키움 호출, 가격 기반 체결 추정 없음. 재배치 매수 표시는 `auto_core_tickets.py:1305` buy_is_ticket False로 주문표가 아님 |
| G4 쓰기·fail-closed | PASS | 가드는 읽기만 함(`auto_core_inputs.py:237`, `:245`). 정책·상태·일지 쓰기 경로 추가 없음. 없음·링크·git 실패·예외는 모두 차단(`:229-243`, `:246-248`) |
| G5 비밀 | PASS | details에는 사유 코드와 예외 이름만, 경로는 repo 상대 경로만 들어감(`auto_core_inputs.py:200-205`, `:238-243`) |
| G6 테스트 | PASS | 기존 테스트 무변경, 새 파일에 skip·expectedFailure 없음. `checks.json:429` new_failures 없음, 실행 3443→3472(+29). 스키마 PASS(`checks.json:431`) |
| G7 class | PASS | 주문 단계, 도구, 예산, 상한, 승인 상품, 대조 불변 조건, 정지 스위치, quantity_authority 모두 변경 없음. class_ok=true. 실행 class는 authority(`checks.json:120`)라 병합에는 사장 결정이 필요 |
| G8-1 파일 범위 | PASS | diff는 허용 5개 파일뿐이고 스키마·정책·기존 테스트 무변경(`changed-files.txt:1-5`) |
| G8-2 입력 목록 | PASS | 가드 3종 `auto_core_inputs.py:225`, 설명 파일 `auto_core_decide.py:824-836`. 5개 파일 grep에서 빠진 판정 입력 없음. `event-calendar.json`은 채점(`score_decision_journal.py:53`)에서만 씀. `.git` index 읽기는 작업 폴더 밖이라 권한 거부됨. 입력 파일이 worktree에 있고, 시작 시점 git status의 미추적 2건에 없고, `checks.json:27-109` ignored에도 없어 추적 파일로 판단 |
| G8-3 fail-closed | PASS | 미커밋·없음·링크·git 실패·가드 오류 모두 매수 차단, decide는 FAIL 아님(`auto_core_inputs.py:223-250`, 테스트 b~g). 모두 커밋이면 주문표·blocked·reasons가 같음(테스트 a) |
| G8-4 반례 탐색 | PASS | 검사는 세 문서 읽기 직후이고 대기보다 앞섬(`auto_core_decide.py:567-574`, `:582`). 사유는 gate·card_check·`_plan_sell`에 안 들어감(`auto_core_tickets.py:805`). `hold_eval`은 ctx를 복사해 차단이 유지됨(`auto_core_decide.py:1167`). `_limit_daily`는 줄이기만 함(`auto_core_tickets.py:1215-1225`). `_no_new_session`은 새 주문표 없음(`auto_core_decide.py:882`). M6 삭제는 조이기만 함(`auto_core_rules.py:986-993`), 사본·이름 바꾸기는 차단. None일 때 등록부 주입 사용(`auto_core_decide.py:446`, 테스트 k). 후보 None은 기존 대입 뒤(`auto_core_tickets.py:735-742`) |
| G8-5 테스트·보고 | PASS | 사례 a~k 존재, 새 실패 0, 보고 (a)~(c) 포함, 주문·권한 표지 없음(`docs/claude/coreinput-report.md:51-54`) |
| 병합 결정 공개 사항 | PASS | 가드가 막은 날 후보가 빠져 매도 주문표가 안 나올 수 있음(`docs/claude/coreinput-report.md:51`). 지시문 C절과 사례 j가 요구한 계산이고 테스트로 고정됨. 그런 날 알림의 "매도 그대로"는 실제와 다름(`auto_core_decide.py:579`). 지시문 B절의 문구 그대로이고 보고 남은 위험 7에 적혀 있어, 코드 수정 대상이 아니라 사장 병합 판단 사항 |

```json
{"verdict": "PASS", "class_ok": true, "items": [{"id": "G1", "result": "PASS", "evidence": "auto_core_inputs.py:208-250; auto_core_decide.py:569-581; auto_core_tickets.py:741-742,823"}, {"id": "G2", "result": "PASS", "evidence": "changed-files.txt:1-5; checks.json:130-131"}, {"id": "G3", "result": "PASS", "evidence": "diff.patch 주문 경로 없음; auto_core_tickets.py:1305"}, {"id": "G4", "result": "PASS", "evidence": "auto_core_inputs.py:229-248"}, {"id": "G5", "result": "PASS", "evidence": "auto_core_inputs.py:200-205,238-243"}, {"id": "G6", "result": "PASS", "evidence": "test_auto_core_input_guard.py skip 없음; checks.json:429,431"}, {"id": "G7", "result": "PASS", "evidence": "diff.patch 권한·한도 변경 없음; checks.json:120"}, {"id": "G8-1", "result": "PASS", "evidence": "changed-files.txt:1-5"}, {"id": "G8-2", "result": "PASS", "evidence": "auto_core_inputs.py:225; auto_core_decide.py:824-836; score_decision_journal.py:53; checks.json:27-109; .git index 읽기는 권한 거부로 간접 확인"}, {"id": "G8-3", "result": "PASS", "evidence": "auto_core_inputs.py:223-250; test_auto_core_input_guard.py 사례 a~g"}, {"id": "G8-4", "result": "PASS", "evidence": "auto_core_decide.py:446,567-582,882,1167; auto_core_tickets.py:735-742,805,1215-1225; auto_core_rules.py:986-993"}, {"id": "G8-5", "result": "PASS", "evidence": "test_auto_core_input_guard.py 사례 a~k; docs/claude/coreinput-report.md:51-54; checks.json:429"}], "min_fixes": []}
```

VERDICT: PASS

(이 파일은 tools/dev_pipeline/devpipe.py가 씁니다. 판정 근거는 workspace/outputs/dev-runs/coreinput/ 의 원본 기록입니다.)
