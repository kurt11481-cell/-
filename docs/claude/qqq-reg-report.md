worktree: .claude/worktrees/great-rhodes-1951b3 · 브랜치 claude/great-rhodes-1951b3 · HEAD df9b2df (2026-11-09 10:43 KST에 41f7b3f → df9b2df로 맞춤, 추적 파일 손실 없음)

---
id: qqq-reg-report
date: "2026-11-09"
status: "A·B·C·D 완료 — 커밋하지 않음(병합 스크립트가 해시 확인 뒤 커밋). BLOCKED 아님"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 상태·일지·원장·예약·대시보드 쓰기 없음 · auto_core.py 실행 없음"
---

# qqq-reg Builder 2차 — 보고 (2026-11-09 KST)

## 승인

- 착수 카드 '착수 — 등록부까지' (cmsg_0137MRzn9nuDvvQmVxm6WeX97AveXwLkxhJwQex9LrzAKq, 2026-11-09 10:30:03 KST)
- 재착수 카드 '재착수 — 보정판' (cmsg_0137MRzn9nuDvvQmVxm6WeX9Az8kTbVPfZDuEMxbs7s6UB, 고른 항목 A, 계정 user_01KuMGKfZu1SBYxtMmg4vAiH, 2026-11-09 10:40:11 KST)
- 기준 맞춤: 처음 HEAD가 41f7b3f라 멈췄다(1차 보고). 코디네이터 메모(2026-11-09 10:41 KST, "1번으로 진행")에 따라 `git switch -C claude/great-rhodes-1951b3 df9b2df`. 그 전에 이 보고서(미추적)를 scratchpad에 복사해 두었다. 추적 파일 변경은 없었다.

## 0. 결론

- 정책 2줄(배수·허용 ETF) + 수집 1줄 + 등록부 QQQ 1항목 + 등록부 해시 1줄 + 기존 테스트 기대값 1줄(보정 가) + 새 테스트 1파일.
- 테스트: 기준선과 같은 결과(실패 0), 새 테스트 8건 통과, 스키마 감사 PASS.
- QQQ 신원: sec.gov 원문으로 확인함(3절).

## 1. 바뀐 줄 (파일:행, 앞 → 뒤)

| 파일:행 | 앞 | 뒤 |
|---|---|---|
| stock-strategy-system/alert_policy.json:698 `nominal_multipliers` | `..., "PWR": 1, "LITE": 1, "cash": 0}` | `..., "PWR": 1, "LITE": 1, "QQQ": 1, "cash": 0}` |
| stock-strategy-system/alert_policy.json:747 `allowed_index_etfs` | `["SOXL", "TQQQ", "DRAM"]` | `["SOXL", "TQQQ", "DRAM", "QQQ"]` |
| stock-strategy-system/alert_policy.json:177 `required_canonical_sha256` | `750a0b4b…01e1dc` | `8faed6da38c53664f2bdaeea1d5c143baa9ccca137cd6f4d71f15c01dd14a3e1` (= `validate_registry_consistency.canonical_hash` 재계산) |
| workspace/policies/auto_core.json:9~10 `symbols_extra` | `"SPY"` | `"SPY",` + `"QQQ"` |
| workspace/policies/instrument_registry.json:206~229 | (없음) | `instruments.QQQ` 추가 (LMT 항목 다음, 마지막) |
| manage-us-stock-strategy/tests/test_portfolio_exposure.py:107 (보정 가) | `"PWR": 1, "LITE": 1})` | `"PWR": 1, "LITE": 1, "QQQ": 1})` |
| manage-us-stock-strategy/tests/test_qqq_registration.py | (없음) | 새 파일 |

- 다른 키·값·순서·들여쓰기 무변경(`git diff -U0`로 확인). 줄바꿈: 네 파일 모두 `i/lf w/crlf`이고 CRLF 그대로. 새 테스트도 CRLF.
- add_default·card_stock_core·excluded_instruments·single_stock_*·문턱·주문/권한 줄(order_authority·quantity_authority·execution_quantity·kill_switch·hard_ceiling) 무변경.

### 등록부 QQQ 항목 (D)
`instrument_type` spot_etf · `leverage_factor` 1.0 (`verified`) · `identity_status` verified_primary_source · `identity_verification_status` VERIFIED · `official_identity_source_type` SEC_485BPOS · `identity_verified_at` 2026-11-09T10:49:40+09:00 · `candidate_status` active · `new_buy_instrument_approved` false · `watchlist_approved` false · `short_sale_approved` false · `exchange` The Nasdaq Stock Market LLC · `underlying_index` Nasdaq-100 Index · `sec_cik` 0001067839.
- 형식: LMT(1차 출처 확인 항목) 형식을 따랐다. `portfolio_bucket` "tactical"(유일한 active ETF SOXL과 같은 값)·`theme` "broad_market_index"·`subtheme` "nasdaq_100_proceeds_parking"은 이 Builder가 고른 표시용 값이다. 이 칸을 강제하는 스키마·코드는 찾지 못했다(scripts·schemas grep). Judge 확인 항목.
- 등록부를 쓰는 코드 확인: reconcile_broker_state.py:102~114 `canonical_identity_errors`는 **보유 종목의 등록부 identity_status가 "verified"로 시작해야** 대조를 통과시킨다. D가 없으면 QQQ를 산 뒤 대조가 "missing or unverified"로 막혔을 것이다. 이번 항목은 이 조건을 만족한다.

## 2. 테스트 (Python 3.13, 보정 나)

- 인터프리터: `py -3.13` → `C:\Users\금동한\AppData\Local\Programs\Python\Python313\python.exe` 3.13.15, tzdata 2026c. (PATH의 `python`은 C:\Python315 3.15.2이고 tzdata가 없다.) 명령의 나머지는 지시문 글자 그대로.

| 명령 `-p` | 기준선(df9b2df, 바꾸기 전) | 바꾼 뒤 |
|---|---|---|
| `test_qqq_registration.py` | (파일 없음) | 8 OK |
| `test_portfolio_exposure*.py` | 154 OK | 154 OK (보정 가 1줄 포함) |
| `test_auto_core*` | 595 OK (skipped 1) | 595 OK (skipped 1) |
| `test_validate_registry*.py` | 0 (해당 파일 없음) | 0 (해당 파일 없음) |
| `validate_schema_contracts.py` | PASS | PASS |
| 등록부를 읽는 기존 테스트 10개(instrument_identity_authority, portfolio_decision_dashboard, portfolio_decision_order_intent, v2_1~v2_5 7개) | 모두 OK | 모두 OK |
| 전체 `test_*.py` | (기준선 미측정) | 3626 OK (skipped 3), 648.6초 |

- 지시문의 'PLTR 등록부 해시 테스트 기준선 실패'는 df9b2df에서 재현되지 않았다(기준선 등록부 status VALIDATED, 위 10개 OK).
- 새 테스트 사례: a 실제 alert_policy 값(QQQ 1·허용 ETF·add_default·card_stock_core 불변·hard_ceiling 1.9·권한 줄) · b 실제 auto_core symbols_extra · c 가상 {SOXL 10, QQQ 2, 현금 2000}, 260세션 가상 종가 → `unregistered_instrument_held` 비어 있음, E 숫자, N·V·E를 코드 정의대로 따로 계산해 일치, QQQ `nominal_contribution` = 비중×1 · d `increase_blockers("QQQ")`에 UNREGISTERED_INSTRUMENT·NOT_AN_S5_NEW_BUY_INSTRUMENT 없음(미보유 땐 빈 목록) · e XLE를 더하면 `UNREGISTERED:XLE` 하나만, E 없음 · f 실제 두 파일 `validate_registry_consistency` = VALIDATED(바꾸기 전과 같은 status), QQQ 등록부 항목 값 · g 종목 상한 현재 동작 고정.
- 지시문 c의 "QQQ 기여 = 비중 × max(1, SOXX 대비 변동성 비율)"은 코드 식과 다르다. 코드는 E = max(N, V), N = Σ배수×비중(portfolio_exposure.py:195~199·324~328), V = std(Σ비중×수익률)/std(SOXX 수익률)(249~259)로 포트폴리오 전체에서 한 번 계산한다. 테스트는 코드 식을 그대로 따랐다.

## 3. QQQ 신원 (sec.gov 원문, 보정 다 D)

- https://data.sec.gov/submissions/CIK0001067839.json (2026-11-09 10:50:03 KST 조회): `"cik":"0001067839"`, `"name":"INVESCO QQQ TRUST, SERIES 1"`. 같은 파일에서 accession 0001104659-25-123273 = 485BPOS, filingDate 2025-12-19.
- https://www.sec.gov/Archives/edgar/data/1067839/000110465925123273/tm2529177d1_485bpos.htm (2026-11-09 10:49:40 KST 조회, 원본 sha256 b52b99ad1b5cd0a618237e8dc1789ecc534843510766c331d005c0b14a1c188e):
  - 이름: "Invesco QQQ Trust SM , Series 1 (Exact Name of Registrant as Specified in Charter)"
  - 거래소: "Shares of the Trust are listed on The Nasdaq Stock Market LLC (the “Exchange”)." / "The Shares trade on the Exchange under the symbol “QQQ.”"
  - 지수: "seeks to track the investment results, before fees and expenses, of the Nasdaq-100 Index ®"
  - 1배 근거: "The Fund employs a “full replication” methodology … invests in all of the securities comprising the Underlying Index in proportion to their weightings". 일일 배수 목표 문장은 없다. 위험 절의 "To the extent that the Fund borrows money, it may be leveraged."는 차입 위험 설명이고 배수 목표가 아니다. → leverage_factor 1.0.
  - 전환: "Effective after market close on December 19, 2025, the Fund was reclassified as an open-end management investment company … Prior to the Reclassification, the Fund operated as a unit investment trust (“UIT”)."

## 4. QQQ 종목 상한

- 적용된다. portfolio_exposure.py:1119~1124 `cap_limit`: `single_stock_cap_exempt`(alert_policy.json:769 = ["SOXL", "TQQQ"])에 없으면 cap/배수 = 0.4/1 = 0.4. 1560행 `single_stock_cap_applies` True. 증가 권고는 1236~1237행 `SINGLE_STOCK_CAP`, 줄이기는 1151~1157행 1순위에 걸린다. 테스트 g로 현재 동작만 고정했고 바꾸지 않았다. 판 몫을 QQQ에 담을 때 QQQ 비중이 자본의 40%를 넘으면 상한 초과 경고·줄이기 권고가 난다 — 단계 B 설계 때 볼 것.

## 5. 코어가 QQQ 매수 주문표를 스스로 내지 않음

- auto_core_tickets.py:61 `APPROVED_BUY = ("BE", "MU", "NBIS", "DELL", "AMD", "SOXL", "TQQQ", "DRAM", "PWR", "LITE")`에 QQQ 없음 → auto_core_decide.py:1036 `buy_approved=symbol in tickets_module.APPROVED_BUY`가 False.
- 판정 대상 universe = 보유 ∪ 관심 명단 ∪ 기준 지수(auto_core_decide.py:618~625). QQQ는 관심 명단 밖이라 보유 전에는 판정 대상도 아니다.
- auto_core_decide.py:1137 재배치 후보 집합(card_stock_core ∪ allowed_index_etfs)에 QQQ가 들어가지만, 후보는 rows 가운데 카드 자격(checks eligible)이 있는 것만이다(1214~1229). QQQ는 카드가 없다. 기존 test_auto_core_t2rc_corefix 포함 595건 결과 동일.

## 6. 병합 뒤 첫 06:15 실행에서 확인할 것

1. workspace/outputs/regular-session-closes/history 아래 QQQ 종가 이력 생성(2026-04-01부터 — 252세션 전이라 short_history 표시 정상).
2. 코어 결과에 `BAR_COLLECTION_FAILED:QQQ`·`CLOSE_HISTORY_FAILED:QQQ`(auto_core.py:153·174) 없음.
3. 노출 검토에 `UNREGISTERED:QQQ` 없음(QQQ 보유 전이면 원래 없음 — 보유 뒤 첫 실행에서 다시 확인).
4. 등록부 대조(validate_registry_consistency)가 VALIDATED — 해시 8faed6da…a3e1.

## 7. 남은 위험

- 등록부 해시는 등록부 내용 전체에 걸린다. 병합 전에 다른 작업이 instrument_registry.json을 바꾸면 해시 줄을 다시 계산해야 한다(병합 스크립트의 해시 확인이 잡는다).
- 판 몫 → QQQ 지시는 아직 없다(단계 B, 끊김 — 제안서 4절 3행). 채우기 기본 SOXL도 그대로다(정책 묶음 A).
- 등록부 표시값(portfolio_bucket·theme·subtheme)은 Builder가 고른 값이다(1절).
- 전체 테스트 스위트는 바꾼 뒤에만 돌렸다. 바꾸기 전 전체 기준선은 없다(대상 명령은 모두 기준선 대비).

## 8. 하지 않은 것

커밋·push·병합 없음. dev-run·dev-merge·dev-queue·auto_core.py 실행 없음. 키움·주문 도구 없음. 상태·일지·원장·예약·대시보드·.claude 설정 쓰기 없음. 1차의 `.claude/worktrees/qqq-reg` 건드리지 않음.

## 9. 바뀐 파일 sha256 (작업 트리 바이트, CRLF)

| 파일 | sha256 |
|---|---|
| stock-strategy-system/alert_policy.json | 06d06dc4353251c28cc38a3b41cb995d14d7657b2c03ea55f2fdcb134297d125 |
| workspace/policies/auto_core.json | 8adbe6d79c134acdc97b75005d603d2e67e51e6c3180b51a5e2be3cfd6f3eec0 |
| workspace/policies/instrument_registry.json | 49c9cb39134e50bbc895a68c751548ab65ffe747e449df956bc65814c0017ce2 |
| manage-us-stock-strategy/tests/test_portfolio_exposure.py | 679d6a24702d963cb3c51e35e715a75441381e8023327cd8b93419d102ba8197 |
| manage-us-stock-strategy/tests/test_qqq_registration.py | 915babca324725c193ed2af67a27d01e30fb772c637776811cab5ec98aecebc5 |
| docs/claude/qqq-reg-report.md | (이 파일 — 자기 해시는 적지 않음) |

바꾸기 전 해시: alert_policy.json 98ef14e0…3e77a7 · auto_core.json 7cd5592f…3ae1 · instrument_registry.json f0c2a342…c2b802 · test_portfolio_exposure.py 526760cf…926db7.
