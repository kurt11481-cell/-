# Builder 지시문: t2rc-eqnone2 (독립 대조 oracle의 equity 빈값 오류 수정 + 실행 파일 해시 고정값 갱신, 일반 변경)

사장 결정: "3 a" (사장실 스레드에 직접 입력, 2026-10-25 13:10Z). 앞선 "2 a"(12:01Z)로 올린 t2rc-eq-none은 oracle 해시 고정 때문에 BLOCKED(docs/claude/dev-runs/t2rc-eq-none.md, 코드 변경 없음)였다. 이번 실행은 같은 수정에 고정값 갱신을 함께 넣는다.
작업 위치: dev-run 헤드리스 Builder(워크트리). 커밋·푸시·병합은 하지 않는다. 비밀(.env*, 토큰, 계좌번호)은 읽지 않는다. 키움 도구·주문·정책·상태 파일은 건드리지 않는다. 줄바꿈은 파일의 기존 방식을 유지하고 일괄 변환하지 않는다.

## 관찰된 결함 (사실)
- 2026-10-24 08:40 InvestmentV2-T2rcCheck가 종료 코드 1로 끝났다. 로그의 줄: docs/claude/t2rc-oracle.py 1734행 `w[sym] = q * ser.raw_c[ser.index[ev]] / eq` 에서 float / None.
- `weights_now(env)`(1726~1735행)는 `eq = fnum(s7["equity"]["closing_equity_usd"])`가 None이어도 그대로 나눈다. 같은 함수의 시리즈 없음 분기는 `return None, eq`로 안전하게 빠진다.
- 왜 equity가 비었는지는 확인 필요. 이 작업은 원인이 아니라 빈값에서 죽지 않게 만드는 것이다.
- 실행 파일 docs/claude/t2rc-check-run.ps1 16행 `$ExpectedOracleSha256`이 oracle을 LF 정규화 sha256으로 고정한다. 다르면 ORACLE_SHA_MISMATCH로 중단한다(12~13행 주석: 계산기 변경은 새 해시와 Judge 확인이 필요).

## 바꿀 곳 (정확히 2곳)
1. `docs/claude/t2rc-oracle.py` `weights_now`: `eq`가 None이면 `return None, eq`로 빠진다(1~3줄). 그 밖의 줄은 바꾸지 않는다. 먼저 `weights_now` 호출부(1764·1902·2023행 부근)가 `w is None`을 처리하는지 읽고, 처리하지 못하는 호출부가 있으면 그 호출부만 시리즈 없음 때의 동작과 같게 최소로 고친다. 기존 동작을 모르겠으면 고치지 말고 BLOCKED.md로 멈춘다.
2. `docs/claude/t2rc-check-run.ps1` 16행 `$ExpectedOracleSha256`의 값만: 바뀐 oracle의 LF 정규화 sha256(CRLF를 LF로 바꾼 바이트의 sha256, 러너가 61~63행에서 계산하는 방식과 같게)으로 교체. 그 밖의 줄(주석 포함)은 바꾸지 않는다. 값은 oracle 수정을 끝낸 뒤 계산하고 보고서에 계산 방법과 값을 적는다.

## 먼저 확인 (읽기만)
- oracle의 해시를 고정해 비교하는 곳이 위 2곳 말고 또 있는지: `manage-us-stock-strategy/tests/test_auto_core_rg1_oracle_parity.py`, `docs/claude/t2rc-register-task.ps1`, tools/, 그 밖의 tracked 파일을 `6a74f813c918046b6e58b19087e1cee69b5984591a54639f84be0b47d0139d64`와 `t2rc-oracle`로 검색. 다른 곳(특히 tools/** 같은 보호 경로나 allowed_paths 밖)에 현재 해시를 고정한 곳이 있으면 파일을 바꾸지 말고 BLOCKED.md에 \"어느 파일 몇 행의 값을 어떤 값으로\"를 적고 멈춘다.
- 현재(변경 전) oracle의 LF 정규화 sha256이 16행 값과 같은지 확인해 보고서에 적는다(다르면 BLOCKED).

## 하지 않는 것
- 판정 기준·허용 오차·비교 항목 수를 줄이거나 바꾸는 일(검사 약화). `diffs`에 들어가는 항목을 빼는 일.
- tools/**, .claude/**, CLAUDE.md, 정책·상태 파일, register-task 스크립트, 이미 병합된 merge 스크립트 수정.
- 러너의 해시 비교 자체를 없애거나 약하게 하는 일. 오직 고정값 1개만 교체한다.

## 테스트
- 새 테스트 `manage-us-stock-strategy/tests/test_t2rc_eq_none.py`: (1) `weights_now`에 equity=None인 env(보유 1종목, 시리즈 있음)를 주면 예외 없이 `(None, None)`을 돌려준다(import가 어려우면 소스를 읽는 정적 시험도 허용, 이유를 보고에 쓴다). 정상 equity일 때 계산 결과가 같다. (2) `docs/claude/t2rc-check-run.ps1`의 `$ExpectedOracleSha256` 값이 `docs/claude/t2rc-oracle.py`의 LF 정규화 sha256과 같다.
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_t2rc_eq_none*.py"` 통과, 전체 스위트는 기준선 대비 새 실패 0.

## 보고
`docs/claude/t2rc-eqnone2-report.md`: 바꾼 줄 전/후(oracle, 고정값), 새 LF sha256과 계산 방법, 변경 전 해시 일치 확인, 호출부 3곳의 `w is None` 처리 확인 결과, 다른 해시 고정 위치 검색 결과, 시험 방법, 확인 필요.

## Judge 확인 항목
1. 파일 변경이 allowed_paths 안 네 개뿐이다.
2. oracle은 `weights_now`(와 필요 시 호출부 최소 수정) 외 판정·비교 로직 변경이 없고 검사 항목이 줄지 않았다(fail-closed 유지).
3. equity None에서 예외가 나지 않고, 시리즈 없음 분기와 같은 방식으로 처리된다. 호출부가 `w is None`일 때 불일치로 잘못 세거나 다시 예외를 내지 않는다.
4. t2rc-check-run.ps1은 16행 값만 바뀌었고 새 값이 바뀐 oracle의 LF 정규화 sha256과 정확히 같다(Judge가 직접 계산해 대조). 해시 비교 로직은 그대로다.
5. 다른 곳에 현재 해시 고정이 남아 있지 않다(검색 결과 확인).
6. 주문·권한 표지(`/api/us/ordr`, `ust2000`, `ust2001`, `order_submit`, `quantity_authority`, `kill_switch`)가 추가된 줄에 없다.

```dev-run
{"task_id": "t2rc-eqnone2", "class": "general", "builder_model": "sonnet", "builder_effort": "high",
 "max_turns": 100, "builder_timeout_min": 60,
 "allowed_paths": ["docs/claude/t2rc-oracle.py",
                   "docs/claude/t2rc-check-run.ps1",
                   "manage-us-stock-strategy/tests/test_t2rc_eq_none.py",
                   "docs/claude/t2rc-eqnone2-report.md"],
 "target_tests": ["test_t2rc_eq_none*.py"],
 "commit_message": "fix(t2rc): oracle weights_now returns None when equity is missing; repin runner"}
```
