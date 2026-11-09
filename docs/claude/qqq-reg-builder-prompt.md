---
id: qqq-reg-builder-prompt
title: "QQQ 자동 코어 정책 등록(qqq-reg) — 수동 경로 Builder 지시문"
date: 2026-11-09
class: "authority(K3 — approved products). 수동 경로: Builder Opus(worktree qqq-reg) → 별도 읽기 전용 Judge(Opus) → 병합은 사장 결정 + 사장 PowerShell"
source: "사장 결정 t3-proceeds-qqq-1108(2026-11-08 16:24:55 KST 카드) · 순서 변경 사장 직접 입력 2026-11-09 10:19:23 KST · 착수 = docs/claude/qqq-reg-proposal-2026-11-09.md 6절 결정 기록(카드 id·고른 항목·누른 계정·KST 시각). 착수 기록이 없으면 시작하지 말고 멈춘다"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 상태·일지·원장 쓰기 없음"
---

## 목표
SOXL 판 돈을 QQQ로 담기 전에(t3-proceeds-qqq-2026-11-08.md 3절), QQQ를 들어도 자동 코어의 노출 E가 '없음'이 되지 않게 QQQ를 정책에 1배 지수 ETF로 등록하고, 사기 전부터 정규장 종가 이력을 쌓는다. 범위는 docs/claude/qqq-reg-proposal-2026-11-09.md 2-1절 표 그대로다(6절에 '등록부까지'가 기록돼 있으면 아래 D도 한다).

## 바꿀 내용
### A. stock-strategy-system/alert_policy.json (`portfolio_exposure_policy`)
- `nominal_multipliers`에 `"QQQ": 1`을 `"LITE": 1` 바로 뒤, `"cash": 0` 앞에 넣는다(한 줄 객체 형식 유지).
- `allowed_index_etfs`를 `["SOXL", "TQQQ", "DRAM", "QQQ"]`로.
- 그 밖의 키·값·순서·줄바꿈·들여쓰기는 바꾸지 않는다. 특히 `add_default`·`card_stock_core`·`excluded_instruments`·`single_stock_*`·문턱·`instrument_registry_authority`는 그대로.

### B. workspace/policies/auto_core.json
- `symbols_extra`를 `["SOXX", "GRID", "SPY", "QQQ"]`로(기존 줄 형식 그대로 한 줄 추가). 다른 키 무변경.

### C. 새 테스트 manage-us-stock-strategy/tests/test_qqq_registration.py (이 파일만 새로)
기존 테스트의 가상 상태 만들기 도우미를 재사용한다(portfolio_exposure 테스트·test_auto_core_decide `Env` 중 맞는 것 — 고르기 전에 읽는다). 실제 저장소의 두 정책 파일을 읽어 확인하는 사례와, 가상 보유로 계산하는 사례를 둔다.
  a. 실제 alert_policy.json: `nominal_multipliers["QQQ"] == 1`, `"QQQ" in allowed_index_etfs`, `add_default == "card_add_stock_else_SOXL"`, `card_stock_core`가 바꾸기 전 값(BE·MU·NBIS·DELL·AMD·PWR·LITE)과 같다, `hard_ceiling_when_exposure_gte == 1.9`.
  b. 실제 auto_core.json: `symbols_extra == ["SOXX", "GRID", "SPY", "QQQ"]`.
  c. 가상 보유 {SOXL, QQQ, 현금}(QQQ 정규장 종가 60세션 이상 가상 이력)으로 portfolio_exposure 계산 → `unregistered_instrument_held` 비어 있음, E가 숫자이고 QQQ 기여 = QQQ 비중 × max(1, QQQ의 SOXX 대비 변동성 비율)과 같은 방식(코드가 쓰는 식을 읽고 그대로 기대값 계산).
  d. 같은 가상 보유에서 QQQ 매수 자격 판정(portfolio_exposure.py 1205~1215행 함수)에 `UNREGISTERED_INSTRUMENT`·`NOT_AN_S5_NEW_BUY_INSTRUMENT`가 없다.
  e. 대조: 가상 보유에 등록 안 된 기호(예 "XLE")를 넣으면 지금처럼 `UNREGISTERED:XLE`(바뀐 것이 QQQ 하나뿐임을 확인).
  f. `validate_registry_consistency`(실제 두 파일)가 바꾸기 전과 같은 status를 낸다(등록부 미변경이면 해시 그대로).
- QQQ에 종목 상한(single_stock_nominal_cap 0.4)이 걸리는지 코드로 확인해 보고서에 적는다(테스트 g로 현재 동작을 고정만 하고 바꾸지 않는다).

### D. (6절에 '등록부까지'가 기록된 경우만) workspace/policies/instrument_registry.json
- `instruments.QQQ` = SOXX·DRAM 항목 형식의 spot_etf 1배 항목(`new_buy_instrument_approved`는 다른 항목처럼 false, `candidate_status` "active"). 공식 신원(Invesco QQQ Trust, Series 1 · 거래소 · 추종 지수)은 SEC EDGAR 또는 Invesco 공식 페이지 원문으로 확인해 보고서에 URL·확인 시각을 적는다. 확인 못 하면 D를 하지 말고 BLOCKED.
- alert_policy.json `instrument_registry_authority.required_canonical_sha256`을 `validate_registry_consistency.canonical_hash`로 다시 계산한 값으로.

## 테스트
- 기존 테스트 파일은 한 줄도 바꾸지 않는다. 바뀌어야 통과하는 기존 테스트가 있으면 멈추고 docs/claude/qqq-reg-BLOCKED.md에 적는다.
- 실행은 글자 그대로: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_qqq_registration.py"`, 그리고 정책을 읽는 기존 테스트 `-p "test_portfolio_exposure*.py"`, `-p "test_auto_core*"`, `-p "test_validate_registry*.py"`(있는 것만). 스키마 감사 `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`. 앞에 환경 변수·옵션을 붙이지 않는다. 기준선에서 이미 실패하던 PLTR 등록부 해시 테스트는 무관 — 고치지 않는다.

## 지켜야 할 것 (어기면 Judge FAIL)
1. `auto_core.py` 실행·"auto_core.py"가 든 명령·reconcile apply·kiwoomcli·키움 호출 금지. 상태(portfolio_state.json)·런타임·일지·원장·예약 작업·대시보드 쓰기 없음.
2. 주문·권한 줄(order_authority·quantity_authority·execution_quantity·kill_switch·hard_ceiling) 무변경.
3. 허용 파일만: alert_policy.json · auto_core.json · tests/test_qqq_registration.py · docs/claude/qqq-reg-report.md (D면 instrument_registry.json 추가). 기존 줄바꿈 유지(이 파일들의 eol을 먼저 `git ls-files --eol`로 보고 그대로).
4. git commit·push·병합 없음(바뀐 파일은 worktree에 커밋하지 않은 채 둔다 — 병합 스크립트가 해시 확인 뒤 커밋한다, cd-guard 선례).

## 보고 docs/claude/qqq-reg-report.md
바뀐 줄(파일:행, 앞뒤 값), 테스트 결과, QQQ 종목 상한 적용 여부(코드 행), 코어가 QQQ를 관심 명단 밖이라 스스로 매수 주문표를 내지 않는다는 확인(auto_core_decide.py universe 행), 병합 뒤 첫 06:15 실행에서 확인할 것(history/QQQ 생성·`UNREGISTERED` 없음), 남은 위험.

## 연결표
qqq-reg-proposal-2026-11-09.md 4절 표를 그대로 따른다(이 Builder는 1·2행만 만든다).

## Judge 확인 항목
docs/claude/qqq-reg-judge-prompt.md
