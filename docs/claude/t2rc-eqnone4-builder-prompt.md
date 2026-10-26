# Builder 지시문: t2rc-eqnone4 (독립 대조 oracle의 equity 빈값 오류 수정 + 실행 파일 해시 고정값 갱신, 일반 변경)

사장 결정: "3 a" (사장실 스레드에 직접 입력, 2026-10-25 13:10Z), "안 A로 진행" (사장실 스레드에 직접 입력, 2026-10-26 11:00 KST). 앞선 t2rc-eq-none은 oracle 해시 고정 때문에, t2rc-eqnone3는 아래 "쓸 수 있는 명령" 때문에 BLOCKED였다(docs/claude/builder-blocked-diagnosis-2026-10-26.md). 이번 실행은 같은 수정을 **허용된 명령만으로** 끝내도록 절차를 바꾼 것이다. 수정 내용 자체는 eqnone3와 같다.
작업 위치: dev-run 헤드리스 Builder(워크트리). 커밋·푸시·병합은 하지 않는다. 비밀(.env*, 토큰, 계좌번호)은 읽지 않는다. 키움 도구·주문·정책·상태 파일은 건드리지 않는다. 줄바꿈은 파일의 기존 방식을 유지하고 일괄 변환하지 않는다.

## 쓸 수 있는 명령 (중요)
이 Builder는 승인 창이 없다. 아래 외의 셸 명령은 모두 거부되니 시도하지 않는다(시도해도 시간만 쓴다).
- 파일 읽기·검색·수정은 Read, Grep, Glob, Edit, Write 도구로 한다.
- 셸은 `python -m unittest ...` 한 가지 형태, 그리고 `git status`, `git diff`, `git log`만 된다. `cd`, `&&`, `;`, 파이프, heredoc(`python - <<`), `python -c`, PowerShell 스크립트, `sha256sum` 따위는 쓰지 않는다.
- **sha256은 직접 계산하지 않는다.** 시험 코드가 계산하게 하고, 시험 실패 메시지에 나온 실제 값을 읽어서 쓴다(아래 절차).

## 관찰된 결함 (사실)
- 2026-10-24 08:40 InvestmentV2-T2rcCheck가 종료 코드 1로 끝났다. 로그의 줄: docs/claude/t2rc-oracle.py 1734행 `w[sym] = q * ser.raw_c[ser.index[ev]] / eq` 에서 float / None.
- `weights_now(env)`(1726~1735행)는 `eq = fnum(s7["equity"]["closing_equity_usd"])`가 None이어도 그대로 나눈다. 같은 함수의 시리즈 없음 분기는 `return None, eq`로 안전하게 빠진다.
- 왜 equity가 비었는지는 확인 필요. 이 작업은 원인이 아니라 빈값에서 죽지 않게 만드는 것이다.
- 실행 파일 docs/claude/t2rc-check-run.ps1 16행 `$ExpectedOracleSha256`이 oracle을 LF 정규화 sha256으로 고정한다(61~63행이 계산하는 방식). 다르면 ORACLE_SHA_MISMATCH로 중단한다.

## 절차 (이 순서)
1. **읽기:** 위 파일들과 `weights_now` 호출부(1764·1902·2023행 부근)를 읽는다. 2023행 호출부는 `eq`가 None이면 2038·2054·2062·2066·2080행 산술에서 TypeError가 난다고 앞선 Builder가 읽었다. 직접 확인한다. 호출부 최소안: 2023행 바로 아래에서 `eq is None`이면 2017행 `NO_DATA` 분기와 같은 방식으로 일치 실패(`EQUITY_MISSING`)를 기록하고 반환한다. 기존 동작을 모르겠으면 고치지 말고 BLOCKED.md로 멈춘다.
2. **다른 해시 고정 위치 검색(Grep):** `6a74f813c918046b6e58b19087e1cee69b5984591a54639f84be0b47d0139d64`와 `t2rc-oracle`를 `manage-us-stock-strategy/tests/test_auto_core_rg1_oracle_parity.py`, `docs/claude/t2rc-register-task.ps1`, tools/, 그 밖의 tracked 파일에서 검색. allowed_paths 밖(특히 tools/**)에 현재 해시를 고정한 곳이 있으면 파일을 바꾸지 말고 BLOCKED.md에 "어느 파일 몇 행의 값을 어떤 값으로"를 적고 멈춘다. (앞선 Builder는 러너 16행 외에 없다고 읽었다. 기록용 merge 스크립트·과거 문서의 같은 값은 무시.)
3. **시험 파일을 먼저 쓴다 (oracle은 아직 고치지 않음):** `manage-us-stock-strategy/tests/test_t2rc_eq_none.py`
   - (a) 해시 일치 시험: oracle 파일 바이트를 읽어 `\r\n`을 `\n`으로 바꾼 뒤 hashlib.sha256으로 계산하고, ps1 16행의 `$ExpectedOracleSha256`(정규식으로 64자리 값 추출)과 `assertEqual(실제, 고정값)`으로 비교한다. 실패 메시지에 두 값이 모두 보이게 한다.
   - (b) `weights_now`에 equity=None인 env(보유 1종목, 시리즈 있음)를 주면 예외 없이 `(None, None)`을 돌려준다. 정상 equity일 때 계산 결과가 같다. import가 어려우면 소스를 읽는 정적 시험도 허용하고 이유를 보고에 쓴다.
   - (c) 2023행 호출부: equity None에서 TypeError가 나지 않는다(import가 어려우면 정적 시험).
4. **변경 전 해시 일치 확인:** `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_t2rc_eq_none*.py"` 실행. (a)가 통과하면 "현재 oracle 해시 = 16행 값"이 확인된 것이다(보고서에 적는다). (a)가 실패하면 BLOCKED.md로 멈춘다. (b)(c)는 이 시점에 실패하는 것이 정상이다.
5. **oracle 수정:** `docs/claude/t2rc-oracle.py`의 `weights_now`(와 위 호출부)만 최소로 고친다. 그 밖의 줄은 바꾸지 않는다.
6. **고정값 교체:** 같은 unittest 명령을 다시 실행한다. (a)가 실패하며 "실제" 값이 나온다. 그 64자리 값을 읽어 `docs/claude/t2rc-check-run.ps1` 16행 값만 Edit로 교체한다(다른 줄·주석은 그대로).
7. **재확인:** 같은 unittest 명령이 모두 통과해야 한다. 전체 스위트와 기준선 비교는 파이프라인이 한다. 직접 돌리지 않는다.

## 하지 않는 것
- 판정 기준·허용 오차·비교 항목 수를 줄이거나 바꾸는 일(검사 약화). `diffs`에 들어가는 항목을 빼는 일.
- tools/**, .claude/**, CLAUDE.md, 정책·상태 파일, register-task 스크립트, 이미 병합된 merge 스크립트 수정.
- 러너의 해시 비교 자체를 없애거나 약하게 하는 일. 오직 고정값 1개만 교체한다.
- 허용되지 않는 셸 명령으로 해시를 계산하거나 우회하려는 시도.

## 보고
`docs/claude/t2rc-eqnone4-report.md`: 바꾼 줄 전/후(oracle, 호출부, 고정값), 새 LF sha256과 얻은 방법(시험 실패 메시지), 변경 전 해시 일치 확인(절차 4), 호출부 3곳의 `w is None` 처리 확인 결과, 다른 해시 고정 위치 검색 결과, 시험 방법, 확인 필요.

## Judge 확인 항목
1. 파일 변경이 allowed_paths 안 네 개뿐이다.
2. oracle은 `weights_now`(와 필요 시 호출부 최소 수정) 외 판정·비교 로직 변경이 없고 검사 항목이 줄지 않았다(fail-closed 유지).
3. equity None에서 예외가 나지 않고, 시리즈 없음 분기와 같은 방식으로 처리된다. 호출부가 `w is None`일 때 불일치로 잘못 세거나 다시 예외를 내지 않는다.
4. t2rc-check-run.ps1은 16행 값만 바뀌었고 새 값이 바뀐 oracle의 LF 정규화 sha256과 정확히 같다(Judge가 직접 계산해 대조). 해시 비교 로직은 그대로다.
5. 다른 곳에 현재 해시 고정이 남아 있지 않다(검색 결과 확인).
6. 주문·권한 표지(`/api/us/ordr`, `ust2000`, `ust2001`, `order_submit`, `quantity_authority`, `kill_switch`)가 추가된 줄에 없다.

```dev-run
{"task_id": "t2rc-eqnone4", "class": "general", "builder_model": "sonnet", "builder_effort": "high",
 "max_turns": 100, "builder_timeout_min": 60,
 "allowed_paths": ["docs/claude/t2rc-oracle.py",
                   "docs/claude/t2rc-check-run.ps1",
                   "manage-us-stock-strategy/tests/test_t2rc_eq_none.py",
                   "docs/claude/t2rc-eqnone4-report.md"],
 "target_tests": ["test_t2rc_eq_none*.py"],
 "commit_message": "fix(t2rc): oracle weights_now returns None when equity is missing; repin runner"}
```
