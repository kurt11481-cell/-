# t2rc-eqnone4 보고

## 바꾼 줄 (전/후)
- `docs/claude/t2rc-oracle.py` `weights_now`(1726행~): `eq = fnum(...)` 바로 아래에 2줄 추가.
  - 전: (없음) → 후: `if eq is None:` / `    return None, eq`. 시리즈 없음 분기(`return None, eq`)와 같은 형태다.
- `docs/claude/t2rc-oracle.py` `ticket_check`(2023행 `w, eq = weights_now(env)` 바로 아래): 2줄 추가.
  - 후: `if eq is None:` / `    out["match"] = False; out["should_exist"] = False; out["not_recomputed"].append("EQUITY_MISSING"); return out` (2017행 `NO_DATA` 분기와 같은 방식).
  - 이유: 이 줄 이후 2038·2054행 등이 `eq`로 곱하기·나누기를 하므로 None이면 TypeError가 난다(직접 읽어 확인).
- `docs/claude/t2rc-check-run.ps1` 16행 `$ExpectedOracleSha256`: `6a74f813c918046b6e58b19087e1cee69b5984591a54639f84be0b47d0139d64` → `41bc56df2981606f12653d10efa0f5f6339b1b19fbde6204b05aaca105370466`. 다른 줄은 그대로(해시 비교 로직 61~68행 포함).
- 줄바꿈: oracle 전체가 CRLF(모든 줄이 `\r`로 끝남, 2486→2490줄)로 유지됨을 Grep으로 확인.

## 새 LF sha256과 얻은 방법
`41bc56df2981606f12653d10efa0f5f6339b1b19fbde6204b05aaca105370466`. 직접 계산하지 않고, oracle 수정 후 `test_t2rc_eq_none`의 해시 시험이 실패하며 출력한 `actual=` 값을 읽어 16행에 넣었다. 이후 같은 시험이 통과했다.

## 변경 전 해시 일치 확인 (절차 4)
oracle 수정 전 시험 실행에서 해시 시험 (a)가 통과했다(출력 `.FEE..`의 첫 글자). 즉 변경 전 oracle의 LF sha256 = 16행의 `6a74f813…`. (b)(c)는 예상대로 실패(TypeError, 가드 없음).

## 호출부 3곳의 `w is None` 처리
- 1766행(`exposure_check`): `w is None`이면 `{"status": "PRICE_MISSING"}` 반환 → equity 없음은 PRICE_MISSING으로 보인다(fail-closed).
- 1902~1907행(보유 종목 매수 요건): `w is None`이면 `own_cap`이 True → 매수 요건 막힘(fail-closed). 예외 없음.
- 2023행(`ticket_check`): 위 가드 추가. eq가 None인 채로 아래 산술에 닿지 않는다. 일치 실패(`match` False)로 기록되어 약화가 아니라 실패로 보인다.

## 다른 해시 고정 위치 검색
`6a74f813…`·`t2rc-oracle` 전체 검색(md 제외). 현재 해시를 고정한 실행 위치는 `t2rc-check-run.ps1` 16행뿐. `test_auto_core_rg1_oracle_parity.py`는 경로만 쓰고 해시 고정 없음(27행). 그 밖의 같은 값은 과거 병합 스크립트(`close-confirm-e-merge-2026-10-21.ps1:19`, `rrec-ev4-remove-merge-2026-10-19.ps1:18`)와 기록 JSON(`c1-keep-2026-10-20/*`)이며 기록용이라 무시했다. tools/** 에는 없음.

## 시험 방법
새 파일 `manage-us-stock-strategy/tests/test_t2rc_eq_none.py` (6개):
- (a) oracle 바이트(CRLF→LF) sha256 = ps1 16행 값(실패 메시지에 두 값 표시).
- (b) importlib로 oracle을 읽고 `weights_now`에 equity None·빈 문자열 → `(None, None)`; 정상 equity는 결과 동일; 시리즈 없음 분기 `(None, 1000.0)` 유지.
- (c) `ticket_check`는 완전한 env 구성이 크므로 정적 시험(호출부 아래 가드의 `eq is None`, `EQUITY_MISSING`, `match False`, `return out` 확인).
- 실행: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_t2rc_eq_none*.py"` → 6개 OK. 전체 스위트는 돌리지 않음(파이프라인 몫).

## 확인 필요
- 로그의 equity 빈값 원인(왜 `closing_equity_usd`가 비었는지)은 이 작업 범위 밖이며 확인 필요.
- `ticket_check` 가드의 동작 시험은 정적 시험만 했다(실제 env 실행 없음).
