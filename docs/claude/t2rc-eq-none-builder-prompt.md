# Builder 지시문: t2rc-eq-none (독립 대조 oracle의 equity 빈값 오류 수정, 일반 변경)

사장 결정: "2 a" (사장실 스레드에 직접 입력, 2026-10-25 12:01Z) = 독립 대조 InvestmentV2-T2rcCheck의 10/24 오류(종료 코드 1)를 일반 변경으로 개발 큐에 올린다. 근거: docs/claude/schedule-dashboard-redesign-2026-10-25.md 1-3절·7절.
작업 위치: dev-run 헤드리스 Builder(워크트리). 커밋·푸시·병합은 하지 않는다. 비밀(.env*, 토큰, 계좌번호)은 읽지 않는다. 키움 도구·주문·정책·상태 파일은 건드리지 않는다. 줄바꿈은 파일의 기존 방식(CRLF면 CRLF)을 유지하고 일괄 변환하지 않는다.

## 관찰된 결함 (사실, 읽은 곳 표시)
- 2026-10-24 08:40 InvestmentV2-T2rcCheck가 종료 코드 1로 끝났다. 로그의 줄: `t2rc-oracle.py` 1734행 `w[sym] = q * ser.raw_c[ser.index[ev]] / eq` 에서 `float / None`. (Windows 작업 결과 조회와 로그를 읽은 값. 로그 원문 경로는 이 지시문 작성 때 다시 열어 보지 못함 — 확인 필요.)
- `docs/claude/t2rc-oracle.py` `weights_now(env)`(1726~1735행)는 `eq = fnum(s7["equity"]["closing_equity_usd"])`가 None이어도 그대로 나눈다. 같은 함수의 시리즈 없음 분기는 `return None, eq`로 안전하게 빠진다.
- 왜 equity가 비었는지(예: 10/22~10/24 잔고 불일치로 코어가 보류된 기간과의 관계)는 **확인 필요**. 이 작업은 원인이 아니라 빈값에서 죽지 않게 만드는 것이다.

## 목표
equity가 None(또는 숫자로 못 바꾸는 값)이어도 oracle이 예외로 죽지 않고, 시리즈 없음 분기와 같은 방식(fail-closed: 해당 가중치를 계산하지 않음)으로 처리하게 한다. 판정을 느슨하게 하지 않는다.

## 바꿀 곳
1. `docs/claude/t2rc-oracle.py` `weights_now`: `eq`가 None이면 `return None, eq`로 빠진다(1~3줄 변경). 그 밖의 줄은 바꾸지 않는다.
2. 먼저 확인: `weights_now`를 부르는 곳(1764·1902·2023행 부근)이 `w is None`일 때 어떻게 처리하는지 읽는다. 어느 호출부가 `w is None`을 처리하지 못해 다시 예외가 난다면 그 호출부만 최소로 고친다(처리 결과는 "확인 필요" 상태로 표시되고 불일치로 세지지 않거나 오류로 분명히 표시되는 쪽 — 기존 시리즈 없음 때의 동작과 같게). 기존 동작을 모르겠으면 고치지 말고 BLOCKED.md로 멈춘다.
3. 파일 안의 자체 시험(2397행 부근 equity_cash_t2 시험 블록 포함)이 있으면 새 실패 없이 통과해야 한다.

## 하지 않는 것
- 판정 기준·허용 오차·비교 항목 수를 줄이거나 바꾸는 일(검사 약화). `diffs`에 들어가는 항목을 빼는 일.
- `tools/**`, `.claude/**`, `CLAUDE.md`, 정책·상태 파일, `t2rc-check-run.ps1`·병합 스크립트 수정(보호 경로 또는 allowed_paths 밖).
- oracle 해시 고정값을 다른 파일에서 고치는 일. **먼저 확인**: `oracle_sha256`을 고정해 두고 비교하는 곳이 있는지(`docs/claude/t2rc-check-run.ps1`, `manage-us-stock-strategy/tests/test_auto_core_rg1_oracle_parity.py` 등을 읽기만 한다). oracle 파일이 바뀌면 그 비교가 깨져 새 실패나 실행 중단이 생기는 구조라면, 파일을 바꾸지 말고 BLOCKED.md에 "어느 파일의 어느 값이 바뀐 해시로 갱신돼야 하는지"를 적고 멈춘다.

## 테스트
- 새 테스트 `manage-us-stock-strategy/tests/test_t2rc_eq_none.py`: `weights_now`에 `equity=None`인 가짜 env(보유 1종목, 시리즈 있음)를 줘서 예외 없이 `(None, None)`을 돌려줌을 확인(파일을 import해 실행하는 방식이 어려우면 소스를 읽어 확인하는 정적 시험도 허용 — 그 이유를 보고에 쓴다). 정상 equity일 때 기존 계산 결과가 같음도 확인.
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_t2rc_eq_none*.py"` 통과, 전체 스위트는 기준선 대비 새 실패 0.

## 보고
`docs/claude/t2rc-eq-none-report.md`: 바꾼 줄 전/후, 호출부 3곳의 `w is None` 처리 확인 결과, oracle 해시 고정 비교가 있는지와 결과, 시험 방법, 확인 필요.

## Judge 확인 항목
1. 파일 변경이 allowed_paths 안 세 개뿐이다.
2. `weights_now` 외 판정·비교 로직 변경이 없고, 검사 항목이 줄지 않았다(fail-closed 유지).
3. equity None에서 예외가 나지 않고, 결과가 시리즈 없음 분기와 같은 방식으로 처리된다.
4. 호출부가 `w is None`일 때 불일치로 잘못 세거나 다시 예외를 내지 않는다.
5. oracle 해시 고정 비교가 있다면 그 처리가 보고에 있고 안전하게 멈췄거나 영향이 없음이 확인된다.
6. 주문·권한 표지(`/api/us/ordr`, `ust2000`, `ust2001`, `order_submit`, `quantity_authority`, `kill_switch`)가 추가된 줄에 없다.

```dev-run
{"task_id": "t2rc-eq-none", "class": "general", "builder_model": "sonnet", "builder_effort": "high",
 "max_turns": 80, "builder_timeout_min": 45,
 "allowed_paths": ["docs/claude/t2rc-oracle.py",
                   "manage-us-stock-strategy/tests/test_t2rc_eq_none.py",
                   "docs/claude/t2rc-eq-none-report.md"],
 "target_tests": ["test_t2rc_eq_none*.py"],
 "commit_message": "fix(t2rc): oracle weights_now returns None when equity is missing"}
```
