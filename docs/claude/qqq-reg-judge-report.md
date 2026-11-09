---
id: qqq-reg-judge-report
date: "2026-11-09"
role: "독립 Judge(읽기 전용)"
target: "worktree .claude/worktrees/great-rhodes-1951b3 · 브랜치 claude/great-rhodes-1951b3 · HEAD df9b2df · 커밋하지 않은 변경"
authority: "order_authority=false · quantity_authority=none · 키움·주문 도구 없음 · auto_core.py 실행 없음 · 커밋·push·병합 없음"
---

# qqq-reg Judge 보고 (2026-11-09 KST)

판정 기준: docs/claude/qqq-reg-judge-prompt.md 1~6 + 코디네이터 추가 확인 (1)~(5).
정정 적용: judge-prompt의 'worktree qqq-reg(worktree-qqq-reg)'는 great-rhodes-1951b3로 읽었다. 보고서는 Judge 자기 worktree(infallible-bell-dd930a)의 이 파일.
승인 범위: A 배수 QQQ 1·허용 ETF, B symbols_extra QQQ, C 새 테스트, D 등록부 QQQ + 정책 등록부 해시(카드 '착수 — 등록부까지' 10:30:03 KST). 보정 (가) test_portfolio_exposure.py 105~107행 기대값 "QQQ": 1 한 곳(재착수 카드 10:40:11 KST). 보정 (나) py -3.13.

## 1. diff 파일 = 허용 목록 (항목 1) — 통과

`git status --short`:
- M manage-us-stock-strategy/tests/test_portfolio_exposure.py (보정 가)
- M stock-strategy-system/alert_policy.json (A, D 해시)
- M workspace/policies/auto_core.json (B)
- M workspace/policies/instrument_registry.json (D)
- ?? docs/claude/qqq-reg-report.md (보고)
- ?? manage-us-stock-strategy/tests/test_qqq_registration.py (C)

허용 목록 밖 파일 없음. 커밋 없음(HEAD df9b2df 그대로).

QQQ 신원 근거(보고서 3절에 URL·시각 있음). Judge 직접 대조(2026-11-09 11:12 KST):
- https://data.sec.gov/submissions/CIK0001067839.json → HTTP 200, `cik` 0001067839, `name` "INVESCO QQQ TRUST, SERIES 1", accession 0001104659-25-123273 = form 485BPOS, filingDate 2025-12-19, primaryDocument tm2529177d1_485bpos.htm — 등록부의 `sec_cik`·`official_identity_source_url`·`official_identity_source_type`과 일치.
- 485BPOS 본문 URL은 Judge 요청에 HTTP 403(sec.gov 자동 요청 제한)이라 본문 문장(거래소·지수·전환 문구)은 직접 대조하지 못했다. 본문 문장은 Builder 인용(원본 sha256 b52b99ad…188e)에 의존 — 확인 필요 1건(결론을 바꾸지 않음: 이름·CIK·서류 종류·날짜는 1차 출처로 확인됨).

## 2. alert_policy.json·auto_core.json 바뀐 곳 (항목 2) — 통과

JSON 의미 비교(HEAD 대비, py -3.13 스크립트):
- alert_policy.json: `portfolio_exposure_policy.nominal_multipliers.QQQ` 추가(1, LITE 뒤·cash 앞) · `portfolio_exposure_policy.allowed_index_etfs` ['SOXL','TQQQ','DRAM'] → [...,'QQQ'] · `decision_harness.instrument_registry_authority.required_canonical_sha256` 750a0b4b…01e1dc → 8faed6da…a3e1. 그 밖 변경 0.
- auto_core.json: `symbols_extra` ['SOXX','GRID','SPY'] → [...,'QQQ']. 그 밖 변경 0.
- instrument_registry.json: `instruments.QQQ` 추가만. 그 밖 변경 0.
- 줄바꿈: 네 추적 파일 `i/lf w/crlf` — 텍스트 diff가 바뀐 줄만 보이고(+30/−5) 줄바꿈 전체 변경 없음. 새 테스트 CRLF. 들여쓰기·한 줄 객체 형식 유지.

## 3. 무변경 확인 (항목 3) — 통과

위 의미 비교에서 다음 키 변경 0: order_authority·quantity_authority·execution_quantity·kill_switch·hard_ceiling 관련 줄, 문턱(1.55·1.85·1.25·1.9), add_default "card_add_stock_else_SOXL", card_stock_core, excluded_instruments ["SOXX","SMH","USD"], sell_only_holdings ["MVLL"], single_stock_nominal_cap 0.4·single_stock_cap_exempt ["SOXL","TQQQ"]·single_stock_cap_applies_to.

## 4. 반례 탐색 (항목 4) — 통과(지적 2건)

- 다른 미등록 기호: 미등록 판정은 `nominal_multipliers`만 본다(portfolio_exposure.py:1363 `unregistered = sorted(... not in config["multipliers"])`, 1365 `UNREGISTERED:{symbol}`; 1207~1208 `UNREGISTERED_INSTRUMENT`). QQQ 한 키만 늘었으므로 다른 기호 fail-closed 그대로. 새 테스트 e가 XLE로 고정.
- 코어가 QQQ 매수 주문표를 스스로 낼 경로: 없음.
  - auto_core_tickets.py:61 `APPROVED_BUY`에 QQQ 없음 → auto_core_decide.py:1036 `buy_approved=symbol in tickets_module.APPROVED_BUY` False.
  - universe = 보유 ∪ 관심 명단 ∪ 기준 지수(auto_core_decide.py:618~625). QQQ는 보유 전엔 판정 대상 아님.
  - auto_core_decide.py:1137 `policy_instruments`(재배치 후보)에 QQQ가 들어가지만 redeploy_ranking(1214~1229)은 카드 자격(`checks[...].eligible`)이 있는 행만 고른다. checks는 docs/claude/card-evidence-registry.json(auto_core_inputs.py:31) 기준이고 QQQ 카드는 없다. Builder 보고 5절이 이것을 정확히 적었다.
- QQQ와 excluded_instruments·sell_only_holdings 겹침: 없음(위 값).
- sox_equivalent 이력 부족: 이 변경은 sox_equivalent 계산 코드를 건드리지 않는다. QQQ 보유 시 이력이 60세션 미만이면 기존 규칙(below_minimum_sessions)대로 V가 없어 E 없음 쪽으로 간다 — 매수 권고만이 아니라 노출 판정 전체가 fail-closed다(기존 동작, 이번 변경 무관). QQQ 수집 시작은 FIRST_COLLECTION_DAY 2026-04-01(auto_core.py:57·352)이라 병합 뒤 첫 수집에서 60세션은 넘는다(252세션 전 short_history 표시).
- 지적 A(기록만): auto_core_tickets.py:62 `INDEX_ETFS = ("SOXL","TQQQ","DRAM")`에 QQQ가 없다. QQQ를 들면 코어 주문표 쪽에서 QQQ는 단일 종목처럼 다뤄진다 — `single_nominal`(185~187)에 들어가 0.4 상한(252행) 비교 대상, 매수 요건 (1)은 실적 공백 판정(232~235행 else). 정책 쪽 동작(아래 6절)과 같은 방향이라 지금 충돌은 없다. 단계 B에서 코어가 QQQ 지시를 내게 하려면 APPROVED_BUY·INDEX_ETFS도 범위에 넣어야 한다.
- 지적 B(기록만): alert_policy.json:767 `single_stock_cap_applies_to` 문구(["stock","single_stock_leveraged_etf","unclassified","DRAM"])에는 지수 ETF가 없는데, 코드 cap_limit(portfolio_exposure.py:1119~1124)은 `single_stock_cap_exempt`에 없는 모든 등록 기호에 상한을 건다. 그래서 1배 지수 ETF인 QQQ에도 0.4가 걸린다. 정책 문구와 코드가 다른 곳이며 이번 변경이 만든 것은 아니다(바꾸지 않음 — 정책 묶음 A 또는 단계 B 안건).

## 5. 테스트·보고서 (항목 5, 추가 (5))

Judge 직접 재실행(2026-11-09 11:11~11:14 KST, `py -3.13` = Python 3.13, Builder worktree에서, 명령은 지시문 글자 그대로 `-m unittest discover -s manage-us-stock-strategy/tests -p <패턴>`):

| 대상 | 결과 | Builder 보고 |
|---|---|---|
| `test_qqq_registration.py` | Ran 8, OK | 8 OK — 일치 |
| `test_portfolio_exposure*.py` | Ran 154, OK | 154 OK — 일치 |
| `test_auto_core*` | Ran 595, OK (skipped=1), 133초 | 595 OK (skipped 1) — 일치 |
| `test_validate_registry*.py` | 해당 파일 없음(Ran 0) | 0 — 일치 |
| `validate_schema_contracts.py` | `{"status": "PASS", "errors": []}` | PASS — 일치 |

전체 스위트는 돌리지 않았다(지시). skipped 1건은 test_auto_core* 기존 건으로 Builder 기준선과 같다.

- 새 테스트 a~g: test_qqq_registration.py에 a·b·c·d·e·f(2건)·g = 8건, `skip` 없음(파일에 skip 데코레이터·skipTest 없음).
- 기존 테스트 변경: test_portfolio_exposure.py 107행 기대값에 `"QQQ": 1` 한 곳(보정 가 허용 범위 그대로). 그 밖 기존 테스트 무변경.
- 테스트 f 주의: 지시문 f는 "바꾸기 전과 같은 status"였다. 결과 VALIDATED = 기준선 VALIDATED(Builder 기준선 + Judge가 HEAD 등록부로 canonical_hash 750a0b4b…01e1dc = HEAD 정책값 재현).
- 보고서 필수 항목: 바뀐 줄(1절)·테스트 결과(2절)·종목 상한(4절)·코어 자체 매수 없음(5절)·06:15 확인 항목(6절)·남은 위험(7절) 모두 있음.

## 6. 연결표 원문 행 대조 (항목 6) — 통과

| 제안 4절 인용 | 저장소 원문(great-rhodes-1951b3) | 결과 |
|---|---|---|
| ③ portfolio_exposure.py:1363 | 1363 `unregistered = sorted(...)` | 일치 |
| ③ portfolio_exposure.py:1211 | 1211 `if symbol not in card_stock_core and not in allowed_index_etfs` (반환은 1212) | 일치 |
| ③ auto_core_decide.py:1137 | 1137 `policy_instruments = set(card_stock_core) | set(allowed_index_etfs)` | 일치 |
| ⑤ portfolio_exposure.py:1365 | 1365 `UNREGISTERED:{symbol}` | 일치 |
| ② auto_core.py:348~353 | 348 `symbols_extra` 읽기 ~ 353 collector | 일치 |
| ⑤ auto_core.py:153·174 | 153 `BAR_COLLECTION_FAILED`, 174 `CLOSE_HISTORY_FAILED` | 일치 |
| 2-1 alert_policy.json 699 | 699 `"unregistered_instrument"` | 일치 |

## 7. 코디네이터 추가 확인

(1) sha256 재계산(작업 트리 바이트) — 6개 모두 일치:
| 파일 | 계산값 | Builder 보고 |
|---|---|---|
| alert_policy.json | 06d06dc4353251c28cc38a3b41cb995d14d7657b2c03ea55f2fdcb134297d125 | 06d06dc4…d125 일치 |
| auto_core.json | 8adbe6d79c134acdc97b75005d603d2e67e51e6c3180b51a5e2be3cfd6f3eec0 | 8adbe6d7…eec0 일치 |
| instrument_registry.json | 49c9cb39134e50bbc895a68c751548ab65ffe747e449df956bc65814c0017ce2 | 49c9cb39…7ce2 일치 |
| test_portfolio_exposure.py | 679d6a24702d963cb3c51e35e715a75441381e8023327cd8b93419d102ba8197 | 679d6a24…8197 일치 |
| test_qqq_registration.py | 915babca324725c193ed2af67a27d01e30fb772c637776811cab5ec98aecebc5 | 915babca…ebc5 일치 |
| qqq-reg-report.md | 922af5768511f83b1b07e14f492ed6874478d286f092814217809b72ae342b12 | 922af576…2b12 일치 |

(2) 등록부 해시: `validation_common.canonical_hash`(바뀐 등록부) = 8faed6da38c53664f2bdaeea1d5c143baa9ccca137cd6f4d71f15c01dd14a3e1 = 정책 `decision_harness.instrument_registry_authority.required_canonical_sha256` — 일치. `validate_registry_consistency`(두 실제 파일) status VALIDATED, errors []. HEAD 등록부의 canonical_hash = 750a0b4b…01e1dc = HEAD 정책값(기준선도 일치였음).

(3) reconcile이 보유 종목의 등록부 identity를 봄 — 확인. reconcile_broker_state.py:102~116 `canonical_identity_errors(positive, registry_path)`: 등록부 `instruments`를 읽고(읽기 실패 시 "unreadable"로 fail-closed, 104~109), 보유(positive) 기호마다 `identity_status`가 "verified"로 시작하지 않으면 "missing or unverified" 오류(111~115). QQQ 항목 `identity_status` "verified_primary_source" → 통과 조건 만족. Builder 주장 맞음.

(4) QQQ 종목 상한: 걸린다. portfolio_exposure.py:1119~1124 `cap_limit` = cap / 배수 = 0.4/1 = 0.4(QQQ는 `single_stock_cap_exempt` ["SOXL","TQQQ"] 밖), 1237~1239 증가 권고 `SINGLE_STOCK_CAP`(Builder 보고 4절의 '1236~1237행'은 2줄 어긋남 — 내용은 같음), 1560 `single_stock_cap_applies` True; 코어 주문표 쪽도 auto_core_tickets.py:185·252 단일 종목 0.4 비교. 판 몫 관계 1줄: **판 몫을 QQQ에 담아 QQQ 평가액이 자본의 40%를 넘으면 그날부터 QQQ 신규·추가 매수 권고가 막히고 줄이기 순서 1순위(상한 초과분)로 잡히므로, 판 몫 QQQ 크기는 사실상 자본의 40% 이하로 묶인다(바꾸지 않음 — 단계 B 설계 안건).**

(5) 대상 테스트·스키마 감사 py -3.13 직접 재실행 — 5절 표.

## 8. 하지 않은 것

Builder worktree·본 저장소 쓰기 없음. 커밋·push·병합 없음. auto_core.py 실행 없음. 키움·주문 도구 없음. 전체 스위트 실행 없음. 쓴 파일은 이 보고서 하나(+ 세션 scratchpad의 임시 스크립트·SEC 응답).

## 9. 판정

항목 1~6과 추가 확인 (1)~(5) 모두 통과. 바뀐 내용은 승인 범위(A·B·C·D + 보정 가·나) 안이다.

지적(판정을 바꾸지 않음, 기록만):
1. 485BPOS 본문은 sec.gov 403으로 Judge가 직접 대조하지 못함(이름·CIK·서류 종류·날짜는 data.sec.gov로 확인) — 확인 필요.
2. auto_core_tickets.py:61~62 APPROVED_BUY·INDEX_ETFS에 QQQ 없음 — 단계 B에서 코어가 QQQ 지시를 내게 하려면 범위에 넣어야 함.
3. 정책 `single_stock_cap_applies_to` 문구와 코드 cap_limit이 달라 1배 지수 ETF QQQ에도 0.4 상한이 걸림 — 판 몫 QQQ 크기 상한 40%로 작동. 정책 묶음 A·단계 B 안건.
4. Builder 보고 4절 SINGLE_STOCK_CAP 행 번호 2줄 어긋남(1236~1237 → 실제 1237~1239).
5. 등록부 표시값(portfolio_bucket "tactical"·theme·subtheme)은 Builder 선택값 — 강제하는 스키마·코드 없음(Builder 보고와 같음).

결론을 바꿀 조건: 병합 전에 instrument_registry.json이나 alert_policy.json이 다른 작업으로 바뀌면(해시 06d06dc4…/49c9cb39… 불일치) 이 판정은 무효이고 해시를 다시 계산해 다시 본다.

VERDICT: PASS
