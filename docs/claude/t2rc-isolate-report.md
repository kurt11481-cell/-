---
id: t2rc-isolate-report
title: 독립 대조(t2rc-oracle) — T1 격리 관심 종목은 대조 쪽에서도 매수 판정하지 않음 — Builder 보고
date: 2026-11-15
class: 일반(dev-run class general)
prompt: docs/claude/t2rc-isolate-builder-prompt.md
authority: 권한 표지 4종 줄 변경 없음 · 주문 경로 없음 · 정책·상태·일지 쓰기 없음 · 키움 호출 없음 · 예약 작업 등록 변경 없음
---

# t2rc-isolate Builder 보고

## 1. 바꾼 줄

`docs/claude/t2rc-oracle.py` (작업 트리 CRLF 유지 — 모든 줄이 `\r\n`로 끝남 확인)

| 줄 | 내용 |
|---|---|
| 19 | docstring 입력 설명에 "T1 result steps.bars.isolated (watch-only symbols the core isolated; checked, else ignored)." (ASCII) |
| 1260~1263 | `circuit_for_session(..., c7_facts=None, *, isolated=frozenset())` — 키워드 전용, 기본값 빈 집합. 위치 인자 11개 순서 그대로. docstring에 isolated 한 줄 |
| 1273~1274 | `detail[sym] = d` 바로 뒤, `ind is None` 검사 앞: `if sym in isolated: d["status"] = "ISOLATED"; continue` — 매수·매도 판정 없음 |
| 1333~1361 | 새 함수 `t1_isolated(t1, held, members)` → frozenset. 형식 조건 = decide `t1_isolated`(`manage-us-stock-strategy/scripts/auto_core_decide.py:183-207`): 비지 않은 list, 항목 키가 정확히 symbol·reason, symbol은 비지 않은 str이며 `s == s.strip().upper()`, reason은 str, 중복 없음. 더해서 모든 종목이 members(관심 명단 − 보유) 안, 보유·SOXX·GRID 아님. steps/bars/isolated 키가 없으면 빈 집합(옛 기록). 어긋나면 빈 집합(격리 무시). 본문 전체 try/except → 예외를 밖으로 던지지 않음 |
| 1364~1370 | 새 함수 `isolated_for_check(repo, day, held, members)` — `load_json(rel(repo, canon_inputs(day)["t1_result"]))`, 읽기·JSON 오류는 빈 집합 |
| 1582 | `cmd_check`: `members = ...`(1581) 바로 뒤 `isolated = isolated_for_check(repo, day, held, members)`. 입력 sha 대조 NOT_CHECKED 반환(1559~1561)보다 뒤 |
| 1613 | `circuit_for_session(...)` 호출 끝에 `isolated=isolated` |

바꾸지 않은 것: `ORACLE_VERSION`, verdict 규칙, `counts_for_c1`, C2·C3, `cmd_replay`(2236행 호출 그대로 — 격리 없이 지금과 같게 돎), `cmd_selftest`, C1 guard(1667~1676), `diagnostics`(1736~), `redeploy_candidates`(1894~). 출력 JSON에 새 키 없음. 권한 표지 4종이 든 줄은 만들거나 바꾸거나 지우지 않았다(diff 안에 그 글자 없음 — 줄 번호만 아래로 밀림).

`docs/claude/t2rc-check-run.ps1` (CRLF 유지)

| 줄 | 내용 |
|---|---|
| 16 | `$ExpectedOracleSha256 = "bc867a17a6c76f225cf254f9259e92064ef1bca6078556adc19bb4669d62a4f6"` (이전 41bc56df…0466) |

새 고정 해시 = 새 계산기의 LF 정규화 sha256 `bc867a17a6c76f225cf254f9259e92064ef1bca6078556adc19bb4669d62a4f6`. 값은 `test_t2rc_eq_none.py` 42~47행 고정 해시 테스트의 실패 메시지(actual=…)에서 얻었고, 핀 교체 뒤 같은 테스트가 통과한다(아래 3절).

## 2. 새 테스트 — `manage-us-stock-strategy/tests/test_t2rc_isolate.py`

계산기는 importlib로 읽기 전용 로드(28~32행). 자료는 합성 값·임시 폴더만. 저장소 workspace/outputs는 읽지 않는다(selftest도 repo = 빈 임시 폴더).

| 지시문 번호 | 테스트(파일:행) | 확인 |
|---|---|---|
| 1 | `T1IsolatedTest.test_valid_list_returns_set` :50, `test_old_records_without_keys_return_empty` :55 | 맞는 목록 → 그 frozenset. `{}`, steps 빈, bars 빈, isolated 없음 → 빈 집합 |
| 2 | `test_invalid_forms_are_ignored` :61, `test_soxx_grid_rejected_even_if_listed_as_members` :89 | 빈 list, list 아님(dict·str), 키 더 있음, reason 없음/str 아님, 소문자, 앞·뒤 공백, 빈 symbol, symbol 숫자, 항목 dict 아님, 중복, 보유, SOXX, GRID, 관심 명단 밖, 하나만 잘못, steps/bars가 dict 아님, t1이 dict 아님 → 모두 빈 집합. SOXX·GRID는 members에 있어도 거부 |
| 3 | `CircuitIsolatedTest` :104 — `test_buy_opens_without_isolation` :121, `test_isolated_symbol_not_opened` :126, `test_default_equals_empty_isolation` :138, `test_isolated_keyword_only_default_empty` :141 | `registry_status`·`compute_triggers`·`group_states`·`evidence`를 테스트 안에서 바꿔 끼워 X·Y 둘 다 매수 열림을 만든 뒤 `isolated={"X"}`: X 없음, `detail["X"]["status"] == "ISOLATED"`, buy·sell·triggers 키 없음, Y는 그대로 열림·OK. 인자 없음 결과 == `isolated=frozenset()` 결과. 키워드 전용·기본값 빈 집합·앞 11개 위치 인자 순서 |
| 4 | `RedeployIsolatedTest` :150 — `test_ok_symbol_is_candidate` :169, `test_isolated_symbol_left_out` :172 | 같은 조건에서 X 상태 OK면 후보 [X, Y], ISOLATED면 [Y] |
| 5 | `IsolatedForCheckTest` :176 — `test_valid_result` :188, `test_invalid_list_in_file_ignored` :193, `test_missing_file` :198, `test_broken_json` :202 | 임시 폴더 `workspace/outputs/auto-core/<day>/result.json`: 맞는 목록 → {X}, 보유 종목 목록 → 빈, 파일 없음 → 빈, 깨진 JSON → 빈 |
| 6 | `CmdCheckWiringTest` :208 — `test_isolated_passed_after_sha_check` :222, `test_replay_call_unchanged` :233 | 소스 확인 방식. 이유: 기록용 함수로 `cmd_check`를 끝까지 돌리려면 decision.json·달력·브로커 스냅숏·S7 검토·등록부·관심 명단·정책·상태·30분봉 페이지 전체 고정 자료가 필요해 무겁다. `inspect.getsource(cmd_check)`에서 INPUT_SHA_MISMATCH 반환 < members 정의 < `isolated_for_check` 호출 < `circuit_for_session(` 호출 순서와, 그 호출 두 줄 안의 `isolated=isolated`를 확인. `cmd_replay` 호출은 그대로이고 isolated 글자가 없음 |
| 7 | `SelftestTest.test_selftest_exit_zero` :242 | `cmd_selftest`가 0 |

변경을 빼면 실패하는 근거: 테스트 1·2·5는 `t1_isolated`·`isolated_for_check`가 없으면 AttributeError로 실패하고, 검증 조건 하나를 빼면 2의 해당 subTest가 실패한다. 테스트 3은 `isolated` 키워드가 없으면 TypeError, 격리 분기(1273~1274)를 빼면 `test_isolated_symbol_not_opened`가 실패한다. `cmd_check` 연결(1582·1613)을 빼면 테스트 6이 실패한다. (되돌린 계산기로 실제로 돌려 보지는 않았다 — 공유 stash를 쓰지 않는 규칙과 이 세션의 명령 제한 때문. 위는 테스트 코드와 바뀐 줄의 대응으로 확인한 것.)

## 3. 대상 테스트 결과

`python -m unittest discover -s manage-us-stock-strategy/tests -p "test_t2rc*.py"` (test_t2rc_isolate 17건 포함)

```
Ran 23 tests in 0.034s

OK
```

`python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core_rg1_oracle_parity.py"`

```
Ran 7 tests in 0.102s

OK
```

`python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core_t2rc_corefix.py"`

```
Ran 22 tests in 0.571s

OK
```

`git diff --ignore-cr-at-eol --stat` (새 테스트·이 보고는 아직 추적 전이라 stat에 없음 — `git status`에 `??`로 보임)

```
 docs/claude/t2rc-check-run.ps1 |  2 +-
 docs/claude/t2rc-oracle.py     | 52 +++++++++++++++++++++++++++++++++++++++---
 2 files changed, 50 insertions(+), 4 deletions(-)
```

## 4. 바꿀 것 4 — C1 guard 확인

격리 종목의 코어 `decision.json` `symbols[<종목>].status` 값 = **`UNK`** (reasons에 `BARS_ISOLATED`).

근거 사슬:
1. decide가 격리 종목 봉을 덮어씀: `bars[symbol] = {**loaded, "status": "ISOLATED", "errors": [T1_BARS_ISOLATED], "split_suspects": []}` — `manage-us-stock-strategy/scripts/auto_core_decide.py:670-674`.
2. 관심 종목마다 `judge(symbol, bars.get(symbol))` → `rules.evaluate_symbol(..., bars=symbol_bars, ...)` — `auto_core_decide.py:1081-1085`, `1096-1097`.
3. `evaluate_symbol`: `usable = bars ... status == "OK"` 거짓, `bars.get("status") != "OK"`이면 reason `BARS_ISOLATED` 추가, `series is None` → `result["status"] = "UNK"` — `manage-us-stock-strategy/scripts/auto_core_rules.py:539-548`.
4. 그 결과가 `decision["symbols"]`로 그대로 옮겨짐(status 키 포함) — `auto_core_decide.py:760`, `_symbol_view` `1294-1297`.

처리: 계산기 C1 guard의 `core_ok = cd.get("status") == "OK" and ...`(`docs/claude/t2rc-oracle.py:1673`)가 거짓이므로 격리 종목은 `gap`에 들어가지 않는다(1674~1675). 코어 값이 OK가 아니므로 지시대로 C1 guard는 **그대로 두었다**. `diagnostics`에는 기존 형식 `[종목, "status", "UNK", "ISOLATED"]` 한 줄로 보인다(1742~1743, 새 키 아님). 요건 표 계산은 상태 OK만 돌므로(1631) 격리 종목은 빠지고, 코어 쪽도 UNK 종목은 요건 UNK다.

## 5. 격리 없는 날 출력이 같다는 근거

- `isolated` 기본값 빈 frozenset — 분기 `if sym in isolated`가 한 번도 참이 아님. 테스트 3 `test_default_equals_empty_isolation`(:138)이 인자 없음 결과와 `isolated=frozenset()` 결과가 같음을 단언.
- T1 결과에 steps.bars.isolated가 없거나 잘못되면 `isolated_for_check`가 빈 집합(테스트 1·2·5) → 위와 같음.
- 출력 JSON에 새 키를 만들지 않음: `res[...]` 대입은 그대로이고(diff에 `res[` 줄 없음), 격리 종목은 기존 `circuit_detail`(1652)의 `status`와 `diagnostics`(1736~)에만 ISOLATED로 보인다.
- 계산기 결과 sha(`oracle_sha256`)는 계산기 파일 바뀜으로 달라진다 — 핀 교체(t2rc-check-run.ps1 16행)로 맞췄다. C3의 `confirmed_before`는 같은 계산기 sha의 앞선 기록만 세므로(`c3_record` 1720행 `r.get("oracle_sha256") == sha256_lf(...)`) 새 계산기 첫날부터 다시 센다 — 이는 기존 계산기 교체 때마다 같은 동작(선례 t2rc-eqnone4)이며 이번 변경이 새로 만든 것이 아니다.

## 6. 연결표

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| 독립 대조 결과 `workspace/outputs/auto-core/<날짜>/t2rc-check.json`·`LATEST_T2RC_CHECK.json`의 verdict(격리 날 거짓 MISMATCH 없음), 격리 종목은 기존 `circuit_detail`·`diagnostics`에 상태 ISOLATED | Windows 작업 InvestmentV2-T2rcCheck 화~토 08:40 KST(`docs/claude/t2rc-check-run.ps1:8-11`) → `t2rc-oracle.py` `cmd_check`(`docs/claude/t2rc-oracle.py:1492`~, 격리 읽기 1582행·전달 1613행) | 자동 운영 코어 결과 알림 trig_01D5KxMSJgbeRG1ZL5ox3Fna 화~토 08:50(`docs/claude/scheduled-prompts/auto-core-alert.txt:14` R\LATEST_T2RC_CHECK.json 받기, `:23` read.py에 LATEST_T2RC_CHECK 넘김, `:47` ⑫ 'VERDICT가 MISMATCH 또는 ERROR') | 격리 날 ⑫ 거짓 경보 없음 → Cowork 헛확인 없음. 진짜 차이와 형식이 틀린 격리 목록은 지금처럼 MISMATCH로 ⑫ | 대조 미실행·늦음은 사장실 결과 모음 trig_01GrAs6UCfspeTBK3mMncyrd·trig_01XChapmUEKxAcjKF9AFiERJ(`docs/claude/active-decisions.md:62`)이 올림(`docs/claude/scheduled-prompts/room-digest.txt:12` '독립 대조(윈도우) 화~토 08:40', `:28` '안 돎·늦음 … 실패'). 계산기 회귀는 새 테스트 `manage-us-stock-strategy/tests/test_t2rc_isolate.py:50,55,61,89`(1~2), `:121,126,138,141`(3), `:169,172`(4), `:188,193,198,202`(5) | 연결 |
| 계산기 고정 해시 `$ExpectedOracleSha256` | 이 diff(`docs/claude/t2rc-check-run.ps1:16`) | 같은 실행기 `docs/claude/t2rc-check-run.ps1:60-63` LF 정규화 계산, `:64-68` 해시가 다르면 `RUNNER_FAIL ORACLE_SHA_MISMATCH`·exit 3, 계산기 실행 안 함 | 새 계산기만 돈다 | 병합 전 `manage-us-stock-strategy/tests/test_t2rc_eq_none.py:42-47` 고정 해시 테스트(대상 테스트 `test_t2rc*.py`, 3절 통과) | 연결 |

원문 대조(이 세션에서 열어 확인): t2rc-check-run.ps1 8~11·16·60~68행, auto-core-alert.txt 14·23·47행, active-decisions.md 62행(두 trig id), room-digest.txt 12·28행, test_t2rc_eq_none.py 42~47행. ② 칸 실행기 설명은 8행에서 시작해 11행까지(지시문의 9~11행 범위 포함).

## 7. 지킨 것

- diff는 지시문 4개 파일뿐(oracle·runner 수정, 새 테스트·이 보고). 기존 테스트 수정·skip 없음.
- 계산기는 auto_core* 모듈을 import하지 않는다(새 함수는 `load_json`·`rel`·`canon_inputs`만 씀). decide 코드는 보고 근거로 읽기만 했다.
- `t2rc-check-run.ps1`, 저장소 자료에 대한 `check`·`replay`는 실행하지 않았다. 키움·예약 작업·정책·상태 파일 손대지 않음. 전체 테스트 미실행(대상 테스트만).
- 주문 경로 문자열 없음.
