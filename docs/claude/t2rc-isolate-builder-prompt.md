---
id: t2rc-isolate-builder-prompt
title: 독립 대조(t2rc-oracle) — T1이 격리한 관심 종목은 대조 쪽에서도 매수 판정하지 않음(bar-isolate 짝 변경)
date: 2026-11-14
class: 일반(dev-run class general) — docs/claude/t2rc-oracle.py · docs/claude/t2rc-check-run.ps1(계산기 고정 해시) · 새 테스트. 선례 t2rc-eqnone4(2026-10-26, general, c1a6a6e)
source: docs/claude/code-review-2026-11-13.md 6절 · bar-isolate 병합 b8f0104(2026-11-14 09:15 KST) · docs/claude/bar-isolate-report.md 6절 연결표 3행(끊김 — 메울 변경 = 이 지시문)
authority: 권한 표지 4종 줄 변경 없음 · 주문 경로 없음 · 정책·상태·일지 쓰기 없음 · 키움 호출 없음 · 예약 작업 등록 변경 없음
approval: 사장 결정 카드 "급한 2건 + 실행기 점검 착수" 2026-11-13 14:40:53 KST(H-1 개발 큐)의 짝 변경. 병합은 사장 `.\tools\dev-merge.ps1 t2rc-isolate`
weekly_user_touch: 1 (병합 1번. 다른 dev-run이 돌고 있으면(_lock) 병합하지 않는다)
queue_order: runner-deps 병합 뒤에 큐에 올린다(새 테스트가 docs/claude 밖이라 같은 기준에서 돌면 나중 병합이 STOP_BASE_MOVED — devpipe.py 2028~2030행)
---

```dev-run
{"task_id": "t2rc-isolate", "class": "general", "builder_model": "opus", "builder_effort": "high", "max_turns": 70, "builder_timeout_min": 45, "allowed_paths": ["docs/claude/t2rc-oracle.py", "docs/claude/t2rc-check-run.ps1", "manage-us-stock-strategy/tests/test_t2rc_isolate.py", "docs/claude/t2rc-isolate-report.md"], "target_tests": ["test_t2rc*.py", "test_auto_core_rg1_oracle_parity.py", "test_auto_core_t2rc_corefix.py"], "commit_message": "fix(t2rc): the independent check treats a watch-only symbol isolated by T1 (steps.bars.isolated) as not buyable, like the core; invalid isolation is ignored; repin runner"}
```

## 목표

bar-isolate(b8f0104)부터 자동 코어 daily는 관심 종목(보유·설정 extra·노출 검토·decide 기준 종목이 아닌 것) 하나의 수집 실패를 그 종목만 격리하고 T1 결과 `steps.bars.isolated`에 적는다(`auto_core.py` 408~432행). 07:45 decide는 그 종목의 봉을 상태 `ISOLATED`로 덮어써 매수 요건 UNK·매수 주문표 없음·재배치 후보 제외가 된다(`auto_core_decide.py` `t1_isolated` 183~207행, 657~686행).

독립 대조(`docs/claude/t2rc-oracle.py`)는 30분봉 페이지를 직접 읽는다(`Series` 214행). `collect_30m.ps1`은 최신 날짜부터 페이지를 저장하므로(43~67행), 실패 전에 저장된 페이지에 평가 세션이 있을 수 있다. 그러면 대조 쪽만 그 종목 매수를 열어 `missing_in_core`(1569행) → verdict MISMATCH → 08:50 알림 ⑫ "독립 대조 MISMATCH"라는 거짓 경보가 난다.

고칠 것: `cmd_check`가 T1 결과(이미 대조 입력 `t1_result` — `canon_inputs`, 입력 sha 대조 1480~1501행)에서 격리 목록을 읽는다. 검증을 통과한 종목은 `circuit_for_session`에서 상태 `"ISOLATED"`로 두고 매수·매도 판정을 하지 않는다(지금 `NO_DATA` 분기와 같은 자리). `redeploy_candidates`(1848행~)는 상태 OK만 보므로 저절로 빠진다. 격리가 없는 날의 출력은 지금과 같다.

## 바꿀 것 — `docs/claude/t2rc-oracle.py`

1. `circuit_for_session`(1259행)에 키워드 인자 `isolated=frozenset()`을 더한다.
   - `sym in isolated`이면 `d["status"] = "ISOLATED"`로 두고 `continue`한다. 위치는 `detail[sym] = d` 바로 뒤, `ind is None` 검사 앞이다.
   - 위치 인자 순서·다른 호출(`cmd_replay` 2190행 등)은 바꾸지 않는다. 그 호출은 격리 없이 지금과 같게 돈다.
2. 새 함수 `t1_isolated(t1, held, members)` → `frozenset`.
   - `steps`·`bars`·`isolated` 키가 없으면 빈 집합(옛 기록).
   - 받아들이는 형식은 decide의 `t1_isolated`와 같다: 비지 않은 list, 항목마다 키가 정확히 `symbol`·`reason`인 dict, `symbol`은 앞뒤 공백 없는 대문자 비지 않은 str, `reason`은 str, 같은 종목 두 번 없음.
   - 더해서 모든 종목이 `members`(관심 명단 − 보유, 1536행)에 있고 `held`·`SOXX`·`GRID`가 아니어야 한다.
   - 하나라도 어긋나면 **격리를 무시하고 빈 집합**을 돌려준다. 그러면 지금처럼 비교하고, 차이가 있으면 MISMATCH로 보인다(안전 쪽). 예외를 밖으로 던지지 않는다.
3. 작은 도우미 `isolated_for_check(repo, day, held, members)`가 `canon_inputs(day)["t1_result"]`를 `rel(repo, …)`로 읽어 2를 부른다. 읽기·JSON 오류는 빈 집합이다.
   - `cmd_check`에서 입력 sha 대조와 `held`·`members`가 정해진 뒤(1536행 뒤) 한 번 부르고, 1566행 `circuit_for_session(...)` 호출에 `isolated=`로 넘긴다. sha가 어긋난 날은 지금처럼 그 전에 NOT_CHECKED로 끝난다.
4. C1 guard(1621~1630행)를 확인한다. 격리 종목은 대조 쪽 상태가 OK가 아니므로, 코어 `decision.json` `symbols[<종목>].status`가 OK면 `ORACLE_DATA_GAP`이 붙는다.
   - bar-isolate 코드(decide의 덮어쓰기 → UNK)에서 그 값이 실제로 무엇인지 읽어 보고에 적는다.
   - OK가 아니면 그대로 둔다. OK로 나온다면 격리 종목만 gap에서 빼되, 보고에 근거(파일:행)를 적는다. 판단이 안 서면 BLOCKED.md.
5. 맨 위 docstring의 입력 설명에 "T1 result steps.bars.isolated (watch-only symbols the core isolated; checked, else ignored)" 한 줄을 더한다(ASCII).
6. 출력 JSON에 **새 키를 만들지 않는다.** 격리 종목은 기존 `circuit_detail`(1606행)의 `status`와 `diagnostics`(1690행)에 `ISOLATED`로만 보인다. `ORACLE_VERSION`·verdict 규칙·`counts_for_c1`·C2·C3·`cmd_replay`·`selftest`는 바꾸지 않는다.

## 바꿀 것 — `docs/claude/t2rc-check-run.ps1`

- 16행 `$ExpectedOracleSha256`만 새 계산기의 LF 정규화 sha256으로 바꾼다(60~63행과 같은 계산. `test_t2rc_eq_none.py` 42~47행 고정 해시 테스트가 확인). 다른 줄은 바꾸지 않는다.

## 새 테스트 — `manage-us-stock-strategy/tests/test_t2rc_isolate.py`

계산기는 `test_t2rc_eq_none.py` 20~25행처럼 importlib로 읽기 전용으로 읽는다. 자료는 임시 폴더·합성 값만 쓴다. 저장소 `workspace/outputs`는 읽지 않는다.

1. `t1_isolated`: 맞는 목록 → 그 집합. `steps`·`bars`·`isolated` 없음 → 빈 집합.
2. `t1_isolated` 잘못된 경우마다 빈 집합: 빈 list, list 아님, 키 더 있음, 소문자, 공백, 중복, 보유 종목, SOXX, GRID, 관심 명단 밖.
3. `circuit_for_session`: 격리가 없으면 매수가 열리는 종목 X를 만든다(모듈의 `compute_triggers`·`evidence` 등을 테스트 안에서 바꿔 끼워도 된다).
   - `isolated={"X"}`이면 열림 목록에 X가 없고 `detail["X"]["status"] == "ISOLATED"`다.
   - 인자 없이 부른 결과와 `isolated=frozenset()`으로 부른 결과가 같다.
4. `redeploy_candidates`: 상태 ISOLATED인 종목은 후보에 없다.
5. `isolated_for_check`: 임시 폴더에 `workspace/outputs/auto-core/<day>/result.json`을 써서 맞는 목록 → 집합, 파일 없음·깨진 JSON → 빈 집합.
6. `cmd_check`가 `isolated_for_check` 결과를 `circuit_for_session`에 넘긴다. 테스트 안에서 `circuit_for_session`을 기록용 함수로 바꿔 끼워 확인하거나, 그게 무거우면 소스에서 `isolated=` 인자 전달을 확인한다(둘 중 하나, 보고에 이유).
7. `selftest` 명령 함수가 지금처럼 0으로 끝난다.

테스트 1~3·5는 이번 변경을 빼면 실패해야 한다.

## 지켜야 할 것 (어기면 Judge FAIL)

1. diff는 위 4개 파일뿐이다. 기존 테스트는 고치지 않는다. 기존 테스트가 실패하면 고치지 말고 BLOCKED로 보고한다.
2. 주문 경로 문자열(`/api/us/ordr`, `ust2000x`, `kiwoom_order`, `order_submit`, `place_order`, `kt1000x`)을 넣지 않는다.
   - `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch` 글자가 든 줄을 어느 파일에도 만들거나 바꾸거나 지우지 않는다. 계산기 802·1451·2160행과 docstring 25행도 그대로 둔다. 보고 머리말에도 쓰지 않는다('권한 표지 4종 줄 변경 없음'처럼 쓴다). 선례: bar-isolate 1회차 Judge FAIL(docs/claude/dev-runs/bar-isolate.md).
3. 계산기는 `manage-us-stock-strategy/scripts`(auto_core*)를 import하지 않는다(docstring 5행 원칙). 입력은 자료 파일뿐이다.
4. 실행하지 않는다: `t2rc-check-run.ps1`, 저장소 자료에 대한 `t2rc-oracle.py check`·`replay`. 키움·예약 작업·정책·상태 파일을 건드리지 않는다.
   - 테스트는 `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"` 형식 그대로만 돌린다(앞에 환경 변수나 플래그를 붙이지 않는다). 전체 테스트는 돌리지 않는다.
5. `t2rc-oracle.py`·`t2rc-check-run.ps1`은 git i/lf, 작업 트리 CRLF다. 줄바꿈을 지키고 일괄 변환하지 않는다. 고정 해시는 LF 정규화 바이트 기준이다.

## 보고 `docs/claude/t2rc-isolate-report.md`

- 바꾼 줄(파일:줄)과 새 테스트 목록, 새 고정 해시 값.
- 대상 테스트 결과 마지막 3줄과 `git diff --ignore-cr-at-eol --stat`.
- 바꿀 것 4의 확인 결과: 격리 종목의 코어 `symbols[…].status` 값과 근거(파일:행), gap 처리.
- 격리 없는 날 출력이 같다는 근거(새 키 없음, 테스트 3 두 번째 단언).
- 연결표(아래 절)를 옮기고 ②③⑤ 칸마다 파일:행 또는 trig id를 쓴다. 근거가 없으면 '끊김(메울 변경·승인 경로)'로 쓴다.
- 수량·금액·주문 표지 문자열을 적지 않는다.

## 연결표

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| 독립 대조 결과 `workspace/outputs/auto-core/<날짜>/t2rc-check.json`·`LATEST_T2RC_CHECK.json`의 verdict(격리 날 거짓 MISMATCH 없음), 격리 종목은 기존 `circuit_detail`·`diagnostics`에 상태 ISOLATED | Windows 작업 InvestmentV2-T2rcCheck 화~토 08:40 KST(`docs/claude/t2rc-check-run.ps1` 9~11행) → `t2rc-oracle.py` `cmd_check`(1447행~, 이번 변경) | 자동 운영 코어 결과 알림 trig_01D5KxMSJgbeRG1ZL5ox3Fna 화~토 08:50(`docs/claude/scheduled-prompts/auto-core-alert.txt` 14·23행 LATEST_T2RC_CHECK 받기·read.py, 47행 ⑫ 'VERDICT가 MISMATCH 또는 ERROR') | 격리 날 ⑫ 거짓 경보 없음 → Cowork 헛확인 없음. 진짜 차이와 형식이 틀린 격리 목록은 지금처럼 MISMATCH로 ⑫ | 대조 미실행·늦음은 사장실 결과 모음 trig_01GrAs6UCfspeTBK3mMncyrd·trig_01XChapmUEKxAcjKF9AFiERJ(`docs/claude/active-decisions.md` 62행)이 올림(`docs/claude/scheduled-prompts/room-digest.txt` 12행 '독립 대조(윈도우) 화~토 08:40', 28행 '안 돎·늦음·실패'). 계산기 회귀는 새 테스트 1~5(Builder가 보고에 파일:행) | 연결 |
| 계산기 고정 해시 `$ExpectedOracleSha256` | 이 diff(`docs/claude/t2rc-check-run.ps1` 16행) | 같은 실행기 60~63행 계산, 64~68행: 해시가 다르면 `RUNNER_FAIL ORACLE_SHA_MISMATCH`·exit 3, 계산기 실행 안 함 | 새 계산기만 돈다 | 병합 전 `manage-us-stock-strategy/tests/test_t2rc_eq_none.py` 42~47행 고정 해시 테스트(대상 테스트 `test_t2rc*.py`) | 연결 |

## Judge 확인 항목

1. diff가 4개 파일뿐이다. 기존 테스트 변경·skip이 없다. 출력 JSON에 새 키가 없다. 권한 표지 4종이 든 줄을 만들거나 바꾸거나 지우지 않았다.
2. `circuit_for_session`: `isolated` 키워드 기본값이 비어 있고, 위치 인자·다른 호출(2190행)이 그대로다. 격리 종목은 상태 ISOLATED이고 매수·매도 판정이 없다. 격리 아닌 종목의 처리는 같다.
3. `t1_isolated`의 형식 조건이 decide `t1_isolated`(b8f0104 `auto_core_decide.py` 183~207행)와 같고, 더해서 관심 명단(보유 제외)·SOXX·GRID 조건이 있다. 어긋나면 빈 집합(격리 무시)이다.
4. `cmd_check`가 입력 sha 대조 뒤에만 T1 결과를 읽고, 그 집합을 1566행 호출에 넘긴다. 계산기가 auto_core*를 import하지 않는다.
5. C1 guard: 보고가 코어 `symbols[…].status` 값을 근거와 함께 적었고, 처리가 그 값에 맞다.
6. 고정 해시가 새 계산기의 LF sha256과 같다(`test_t2rc_eq_none.py` 통과).
7. 새 테스트가 바뀐 동작을 잡는다. 격리 분기나 연결을 빼면 테스트 1~3·5 중 하나 이상이 실패한다. 대상 테스트가 전부 통과한다.
8. G9: 연결표 ②③⑤의 원문 행 대조 — t2rc-check-run.ps1 9~11·16·60~68행, auto-core-alert.txt 14·23·47행, active-decisions.md 62행, room-digest.txt 12·28행, test_t2rc_eq_none.py 42~47행, 새 테스트 파일:행. 칸마다 파일:행·trig id 또는 '끊김(메울 변경·승인 경로)'이 있어야 한다.
