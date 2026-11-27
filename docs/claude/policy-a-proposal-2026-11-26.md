---
id: policy-a-proposal-2026-11-26
proposal_id: policy-a-1126
type: proposal
status: "안 1 착수 승인(2026-11-26 22:28:38 KST, 9절). 병합은 따로 사장 PowerShell"
as_of: 2026-11-26
class: "권한·한도 변경(K3) — 수동 경로"
consumers: "사장실 회사PC 스레드(카드·Builder·Judge 지시문) · 관제판 policy-bundle-a · active-decisions.md"
source_decision: "strategy-1101(2026-11-01 21:34 KST) 9절 3행 · policy-a-first-1126(2026-11-26 22:08:26 KST, 순번만)"
---

# 정책 묶음 A — 3배 상한·채우기 기본 상품 (K3 제안 policy-a-1126)

계좌 금액·수량은 적지 않는다(비율만). 시각은 KST. 이 문서는 주문 제안이 아니다(order 권한 없음, 수량은 사장 입력).

## 0. 결론

- **권장 = 안 1**: (가) '3배 상품 합계 ≤ 계좌의 10%'를 **3배 상품을 늘리는 매수에만 거는 막음**으로 정책·코어에 넣고(1배 매수·매도·줄이기는 그대로) (나) 채우기 기본 상품을 SOXL에서 **'카드 ADD 종목만(없으면 채우기 권고 없음)'**으로 바꾼다. 반등 알림 범위(1.9 → 1.55)는 이번에 넣지 않는다(3절 끝).
- 무엇을 하는 일인가: 이미 정한 3배 ≤ 10%(strategy-1101 · strategy-check-1105)를 자동 코어가 어기지 않게 하는 일이다. **수익을 올리는 일이 아니다.** 코어의 S7은 카드를 받지 않으므로(auto_core_decide.py 300~308행 — `--cards` 인자 없음) 병합 뒤 코어의 '채우기 매수 길'(auto_core_tickets.py 817행 S7_ADD_RECOMMENDATION)은 닫히고 '새 단서 길'만 남는다. 관문이 열리는 날 현금이 더 남을 수 있다(return-levers-review-2026-11-26.md 0절·4절 (가)).
- 앞 문서 셋(t3-proceeds-qqq-2026-11-08.md 55행 · active-decisions.md 152행 qqq-b-1115 · qqq-reg-b-proposal-2026-11-12.md)은 채우기 기본으로 'QQQ'를 예고하고 이 카드로 미뤘다. 이번 권장은 그와 다르다 — QQQ는 코어 카드 매수 길 밖이라(auto_core_tickets.py 61~64행, qqq-b-1115) 채우기 기본을 QQQ로 바꿔도 코어 주문표는 나오지 않고 표시만 둘이 된다(3절 안 2).
- 바꾸지 않는 것: 문턱 1.55·1.85·1.25, 절대 상한 1.9, 줄이기 순서(S7 ③), 종목 상한 0.4, 매도 주문표 규칙(SOXL 카드 TRIM 0.10 상시), 관문 R-REC1, 통합 점검 QQQ 줄, 주문·수량 권한 표지, 예약 작업.
- 경로: K3 **수동 경로**(정책 파일 stock-strategy-system/alert_policy.json은 개발 파이프라인이 손댈 수 없는 보호 경로 — tools/dev_pipeline/authority-paths.txt 8~9행). 사장 카드(범위·착수) → 같은 날 Builder(회사PC worktree) → 따로 읽기 전용 Judge → 사장 PowerShell 병합. **2026-12-10까지 병합이 안 되면 멈추고 cal-2027을 먼저 한다**(policy-a-first-1126).
- 기본 처분: 카드 무응답 = 지금대로(NO_CHANGE).

```
[지금] E 1.21 → 채우기 구간(1.25 아래)
   ↓
[S7 채우기 기본 = SOXL] → SOXL 0.07 → 0.20 권고
   ↓
[코어 매수 회로] 관문(R-REC1) 하나만 막는 중
   ↓  관문 열리면
[SOXL 매수 주문표 가능] ↔ 3배 ≤ 10% 결정과 부딪힘
   ↓  묶음 A 뒤
[3배 10% 넘는 매수 막힘 + SOXL 채우기 권고 없음]
```

## 1. 부딪히는 결정 (제안 전 색인 검색 — active-decisions.md 2026-11-26 행 번호, 행은 밀릴 수 있어 id로 찾는다)

| 결정 | 이 제안과의 관계 | 처리 |
|---|---|---|
| strategy-1101(136행) · strategy-revision-2026-11-01.md 9절 3행(193행) | 묶음 A를 채택한 결정. '그날 그 묶음 카드로 다시 승인' | 이 카드가 그 다시 승인 자리 |
| strategy-check-1105(148행) | 3배를 '그날 코어 표시 비중' 10%까지. 정책·코어 변경 없음이라 적힘 | 비중 정의를 그대로 씀. 코어 변경은 묶음 A가 이어받은 일(136행 '정책 묶음 A ... 그날 그 묶음 카드로 다시 승인') |
| soxl-trim-keep-1120(161행) | SOXL 카드 TRIM 0.10 상시 = 매도 쪽 | 매도 쪽은 그대로. 이 제안은 매수 쪽만 |
| fx-5a A-1·B-1(225행) '채우기 기본 대상 SOXL 유지' | (나)가 바꾸는 값 | strategy-1101(136행)에서 'fx-5a B-1 다시 열림 … 그 묶음 카드로 다시 승인'으로 다시 열렸고, 이 카드에서 정한다 |
| S7 승인 ③④(223행 둘째 칸) · 같은 행 셋째 칸 'SOXL·TQQQ는 E로 관리' | 줄이기 순서 끝 = SOXL, 목표 1.55, SOXL·TQQQ는 종목 상한 대신 E로 관리 | 줄이기 순서·목표·종목 상한 면제 그대로. 3배 합계 상한은 그 위에 더해지는 한도(한도 변경이라 K3) |
| t3-proceeds-qqq-1108(150행) + 'G2 ⓑ 지금대로 두고 기록만'(2026-11-19 17:27 KST) · qqq-b-1115(152행) | 판 돈 = QQQ, 통합 점검 161행 '재원 우선', QQQ는 카드 매수 길 밖, 'add_default SOXL→QQQ는 정책 묶음 A 차례' | QQQ 예고는 이 카드로 미룬 것이라 닫힌 결정이 아님 → 안 2로 보이고 권장은 안 1(까닭 0절·3절). 재원 우선·'카드 매수 길 밖'은 바꾸지 않음 |
| loop-1102(137행) · 관제판 policy-bundle-a verify 칸 | 알림 범위·문구를 묶음에서 뗄지 = 열린 질문(그날 사장 선택) | 3절 끝: 이번 묶음에서 뺌(권장), 사장이 넣으라 하면 따로 |
| policy-a-first-1126(194행) | 순번만 정함, 12/10 조건 | 이 문서 5절 일정 |
| 2027-03-31 '3배 0' 질문(strategy-1101) | 그날 0을 고르면 상한 값이 바뀜 | 값 0.10만 바꾸는 K3 1건이 그때 따로 필요(묶음 A가 키를 만들어 두므로 작음) |

## 2. 지금 사실 (이 세션에서 원문 확인)

| 사실 | 원문 |
|---|---|
| 채우기 기본 = `card_add_stock_else_SOXL`, 줄이기 순서 끝 = SOXL, 종목 상한 면제 = SOXL·TQQQ, 배수 SOXL 3·TQQQ 3·MVLL 2, 문턱 1.85·1.25·1.55·1.9 | stock-strategy-system/alert_policy.json 750·752·769·698·686~691행 |
| 채우기 상품은 줄이기 순서 끝(`reduce_order[-1]`)에서 정해지고, add_default가 `card_add_stock_else_<그 상품>`이 아니면 S7이 `S5_POLICY_SUPPLEMENT_INSTRUMENT_INCONSISTENT`로 멈춘다 → **정책 값만 바꾸면 S7이 멈춘다(코드 수정 필요)** | manage-us-stock-strategy/scripts/portfolio_exposure.py 139~141·172행 |
| 채우기 구간에서 카드 ADD가 없으면 채우기 후보 = 그 상품(SOXL) | portfolio_exposure.py 1483~1484행 |
| 늘리는 매수 막음 = 투영 E ≤ 1.55 · 종목 상한(SOXL·TQQQ 면제) · 현금뿐. **3배 합계 막음 없음** | portfolio_exposure.py 1229~1242행(projected_increase_reasons) · 1119~1124행(cap_limit) |
| 위 함수를 S7 채우기(add_recommendations)와 다른 곳 제안(_evaluate_proposal)이 함께 씀 | portfolio_exposure.py 1245·1258행 · 1609·1645행 부근 |
| 코어가 S7에 넘기는 매수 제안 = 그날 새 단서 종목 + (`reduce_order[-1]` = SOXL이고 근거 성립) | manage-us-stock-strategy/scripts/auto_core_decide.py 1105~1107행 |
| SOXL 목표 격자는 1.55/3 ≈ 0.516까지(상한 면제 ETF) | manage-us-stock-strategy/scripts/auto_core_tickets.py 697~707행 |
| 코어 매수 회로 = 새 단서, 또는 S7 채우기 종목 + 근거 성립 | auto_core_tickets.py 789·817행 |
| CARD_TRIM 목표(0.10)는 매도 쪽에서만 읽음 | auto_core_tickets.py 967~981행 |
| 실제: 11/25 종가 S7 = E 1.206 · ADD_ZONE · 채우기 권고 SOXL 0.0697 → 0.20(투영 E 1.548) | workspace/outputs/auto-core/2026-11-26/s7/2026-11-25/portfolio-exposure-review.20261125T224511770926Z.json |
| 실제: 코어 11/25 실행(평가 11/24, status OK) SOXL 매수 후보 S7_ADD_RECOMMENDATION, 막은 사유 `REQ5_RREC1:no` 하나 · 11/26 실행(HOLD) 같은 후보, 사유 대조 보류 2개 + REQ5 | workspace/outputs/auto-core/2026-11-25/decision.json · 2026-11-26/decision.json(candidates·blocked) |
| 코어의 S7 실행에는 카드 인자가 없다 → 코어 안에서 채우기 후보는 늘 SOXL | auto_core_decide.py 296~308행 |
| QQQ는 코어 신규 매수 승인 목록에 없고 '카드 매수 길 밖'(판 몫 보관 전용) | auto_core_tickets.py 61~64·264행 |
| `supplement`(줄이기 뜻)를 읽는 곳: 종가 수집 종목·S7 실행 종목·줄이기 3순위 — 그대로 둘 곳 | 코어 본체 스크립트 163행 · run_portfolio_exposure_review.py 527행 · portfolio_exposure.py 1165행 |
| 정책 키가 없거나 틀리면 ExposureError → 코어는 `UNEXPECTED_ERROR` FAIL 기록(그날 매도 주문표도 없음) | portfolio_exposure.py 185~188행 · auto_core_decide.py 485~487행 |
| 코어가 정책 값을 코드에 고정해 대조하는 표(목표·줄이기·절대 상한·종목 상한) | auto_core_tickets.py 57~59행 `POLICY_EXPECTED` |
| SOXL 채우기 동작을 시험하는 기존 테스트: add_default 고정 2개 + 동작 시험 5개 파일 이상 | test_qqq_registration.py 76행 · test_swing_k3_registration.py 91행 · test_portfolio_exposure.py 302~312행 · test_run_portfolio_exposure_review.py 195행 · test_auto_core_t2rc_corefix.py 210~212행 · test_auto_core_tickets.py 806행 · test_portfolio_exposure_fail_closed.py 409행 |

읽는 법: 관문이 열리고 대조·L6·연구 기록이 모두 OK인 날, 코어는 SOXL을 3배 약 20%까지 키우는 쪽의 주문표를 낼 수 있다(첫 장 크기는 걸음 규칙으로 작다 — return-levers 4절 어림 약 4%p, 실행 시험 아님). 한 장이면 3배가 10%를 넘고 다음 날 통합 점검 QQQ 줄이 꺼진다(161행은 3배 ≤ 10%일 때만 QQQ 줄을 씀).

## 3. 고칠 범위

### 안 1 (권장) — 3배 상한 + 채우기는 카드 종목만

(가) **3배 상한(3배를 늘리는 매수에만)**
- 정책: alert_policy.json portfolio_exposure_policy에 값 하나 — '배수 3 이상 상품의 비중 합 ≤ 0.10'(키 이름은 Builder가 정하고 Judge가 봄, 값 0.10 고정). 코드의 `POLICY_EXPECTED`(auto_core_tickets.py 57~59행)에는 넣지 않는다 — 2027-03-31에 0을 고르면 정책 값 하나만 바꾸면 되게.
- 코드: projected_increase_reasons에 '**늘리는 종목의 배수가 3 이상일 때만**, 투영 뒤 3배 상품 비중 합 > 0.10이면 막음 사유'를 더한다. 이 한 곳으로 S7 채우기·새 단서 제안·바꿔 사기(swap) 매수 다리가 함께 막힌다(우회 길 없음 — 재검토 확인). 종목 상한(cap_limit·cap_breaches 1119~1134행)에는 넣지 않는다 — 넣으면 줄이기 1순위 권고와 매도 주문표가 새로 생긴다.
- 비중 = 그날 S7 비중(평가 비중, 명목 아님 — strategy-check-1105 '그날 코어 표시 비중'). 두 분모가 같은지는 Judge가 대조.
- 결과: 3배가 10% 아래인 날은 10%까지 사는 주문표가 여전히 나올 수 있다(예: SOXL 새 단서 2종류인 날). **10%를 넘기는 3배 매수 주문표는 나오지 않는다.** 3배가 값 변동으로 10% 위에 있어도 1배 종목 매수는 이 막음에 걸리지 않는다.
- 매도 쪽은 바꾸지 않는다(카드 TRIM 0.10 · 2% 막음 · 걸음 1/2 그대로).

(나) **채우기 기본 = 카드 ADD 종목만**
- 정책: add_default를 `card_add_stock_else_SOXL` → '카드 ADD 종목만, 없으면 채우기 권고 없음' 값으로(이름은 Builder).
- 코드: `supplement`는 줄이기 뜻으로 그대로 두고(2절의 세 곳 불변), 채우기 기본은 config의 새 칸으로 뗀다. 바꾸는 곳은 portfolio_exposure.py 139~141행 일치 검사·1484행과 auto_core_decide.py 1107행뿐(재검토가 scripts·schemas를 grep해 다른 곳 없음 확인). 옛 값도 계속 받게 해 뒤로 맞게 한다.
- 결과: 코어의 S7은 카드를 받지 않으므로 코어에서는 '채우기 매수 길'이 닫히고, SOXL은 새 단서가 뜬 날만 매수 후보(그리고 (가)로 10%까지). 카드 ADD 채우기는 카드를 넣어 돌리는 S7 표시에서만 보인다. 관문 날 판 몫 현금 → QQQ는 지금처럼 통합 점검 QQQ 줄(161행, qqq-b-1115)이 사장에게 안내한다.

(공통) 테스트: (가)·(나) 각 길의 새 시험 + 2절 끝 행의 기존 테스트(add_default 고정 2개 + SOXL 채우기 동작 5개 파일 이상) 기대값 고침 — 고친 기대값 목록을 Judge가 하나씩 대조. 기준선과 같은 실패 수.

### 안 2 — 3배 상한 + 채우기 기본 = QQQ (앞 문서들이 예고한 값)
- 실제로 생기는 일: S7 표시에 'QQQ 채우기 권고'가 뜨지만 **코어 주문표는 나오지 않는다**. QQQ는 코어 신규 매수 승인 목록에 없고 '카드 매수 길 밖'이다(auto_core_tickets.py 61~64·264행, qqq-b-1115). 주문표까지 내려면 qqq-b-1115를 다시 열어야 한다.
- 그래서 얻는 것은 표시 하나이고, 통합 점검 QQQ 줄과 같은 내용이 두 곳에 뜬다. 통합 점검 쪽의 '재원 우선'(161행, 2026-11-19 사장이 고른 설계)을 S7 표시는 모른다.

### 안 3 — 안 함(지금대로)
- 관문이 열리는 날 SOXL 매수 주문표가 나올 수 있다. 사장이 그 주문표를 입력하지 않으면 되지만, 그날 통합 점검·코어 표시가 3배 10% 결정과 다르게 나온다.

### 알림 범위(1.9 → 1.55)는 이번에 넣지 않음 (권장)
- 지금 E 1.21이라 1.9 알림은 쓸 일이 없다. 예약 작업 변경(B 종류)이라 H1 시험·독립 검토·`예약 작업 변경 승인` 직접 입력이 따로 필요해 12/10을 위험하게 한다.
- 다시 볼 조건: E가 1.55 위로 올라가거나 사장이 요청할 때.

## 4. 하지 않음

- 문턱(1.55·1.85·1.25·1.9) · 줄이기 순서 · 종목 상한 0.4 · SOXL·TQQQ 종목 상한 면제 · 매도 주문표 규칙 · R-REC1 · 통합 점검 규칙(161행 포함) · 카드·등록부 · 결정 일지 · 상태 파일 · 예약 작업 · 주문·수량 권한 표지 변경 없음.
- 3배를 10% 아래로 '줄이는' 새 권고를 만들지 않는다(줄이기는 사장 직접 결정 — strategy-check-1105).
- 2027-03-31 '3배 0' 질문을 앞당기지 않는다.

## 5. 실행 경로·일정

1. 사장 카드(이 제안 policy-a-1126) — 같은 날(KST) 1회. 카드 id·고른 항목·누른 계정·시각을 결정 기록에(CLAUDE.md Change classes).
2. 같은 날 Builder(회사PC worktree, Opus): 지시문 docs/claude/policy-a-builder-prompt.md(승인 뒤 확정, 조언 형식 점검 뒤).
3. 따로 읽기 전용 Judge(Opus): docs/claude/policy-a-judge-prompt.md.
4. Judge PASS면 병합 스크립트를 만들고 사장이 PowerShell 한 줄로 병합(사장 결정). 병합 스크립트는 커밋 전에 새 시험(정책이 읽히는지 포함)을 돌려 실패하면 아무것도 바꾸지 않고 멈춘다 — 정책 키가 틀리면 다음 코어가 통째로 FAIL이 되므로(2절).
5. 병합 뒤 다음 07:45 코어에서 확인: 결과가 FAIL이 아님 · S7 파일에 새 상한 값이 읽힘. 'SOXL 채우기 권고 없음'은 E ≤ 1.25인 날에만 판별된다(지금은 해당). 확인되면 관제판 policy-bundle-a done.
- 기한 2026-12-10 병합. 넘기면 멈추고 cal-2027 먼저(policy-a-first-1126).
- **카드는 올린 날(KST) 안에 누른 것만 승인이다**(CLAUDE.md Change classes 'the same day, once'). 오늘 누르면 오늘 안에 Builder를 띄운다. 자정을 넘기면 다음 날 같은 제안으로 카드를 다시 올린다. 권한 자리는 비어 있다(layer-audit ④⑤ 2026-11-25 22:30 병합, active-decisions.md 100행 — 한 번에 1건).

## 6. 연결표 (analysis-linkage-map-2026-10-05.md 1절 8번)

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| 정책 3배 상한 값 | 사장 병합(PowerShell) | portfolio_exposure.py exposure_config 126~172행(새 줄은 Builder가 넣고 Judge가 행 대조) → projected_increase_reasons 1229~1242행 | S7 채우기·제안에서 3배 10% 넘는 매수 빠짐 → 코어 매수 주문표 없음(auto_core_tickets.py 789·817행) | 키가 없거나 틀리면 ExposureError(portfolio_exposure.py 185~188행) → 코어 실행 전체 FAIL 기록 `UNEXPECTED_ERROR`(auto_core_decide.py 485~487행, 그날 매도 주문표도 없음) → FAIL 뒤 사장실 알림 경로는 확인 필요 · 막는 장치 = 병합 스크립트가 커밋 전 새 시험 실행 | 끊김 — 메울 승인 = 이 카드(K3 수동 경로) |
| 채우기 기본 값 | 같음 | portfolio_exposure.py 139~141·1484행 · auto_core_decide.py 1105~1107행 | 카드 ADD가 없으면 채우기 매수 후보 없음 | 같음 | 끊김 — 메울 승인 = 이 카드 |
| 막음 사유(3배 상한) | 07:45 코어 S7 | auto_core_tickets.py 710~720행(best_target이 사유를 옮김) → decision.json blocked | 주문표 없음 + 사유 표시 | 코어 결과(기존 경로) | 연결(병합 뒤) |

## 7. 되돌리기

- 병합 커밋을 git revert(사장 결정) — 정책 값·코드·테스트가 함께 원래대로. 상태·일지·예약은 건드리지 않으므로 되돌릴 것이 없다.

## 8. 검토 기록

- 원문 확인(이 세션): CLAUDE.md 전체 · docs/claude/00-home.md · active-decisions.md 136·148·150·152·161·194·223·225행 · strategy-revision-2026-11-01.md 87~114·187~210행 · return-levers-review-2026-11-26.md 13~130·190~200행 · 관제판 tasks/policy-bundle-a(version 3) · alert_policy.json 680~780행 · portfolio_exposure.py 115~172·1119~1131·1229~1260·1460~1510·1595~1660행 · auto_core_decide.py 1080~1125행 · auto_core_tickets.py 180~192·697~720·780~830·955~990행 · tools/dev_pipeline/authority-paths.txt · qqq-reg-report.md(수동 경로 선례) · S7 11/25 파일 · decision.json 11/25·11/26 · (재검토 뒤 추가) auto_core_tickets.py 56~66·262~266행 · auto_core_decide.py 296~308·478~492행 · portfolio_exposure.py 182~190행 · `["supplement"]` grep(scripts) · t3-proceeds-qqq-2026-11-08.md 55행 · 기존 테스트 7곳(2절 끝 행).
- 내장 재검토(CLAUDE.md V5) = 조언(Fable, high) 1회 — 지적 8건: 결론 바뀜 0 · 정정 8(3배 막음은 3배 매수에만 · 안 2 '좋은 점'이 사실과 다름 → QQQ 주문표 안 나옴 · 앞 문서의 QQQ 예고를 밝힘 · fx-5a·S7 행 인용 정정 · 코어 S7은 카드를 안 받음 · supplement 그대로 둘 곳 · 고칠 테스트 7곳 · 연결표 ⑤ 경로 = 코어 FAIL · 같은 날 승인 안내) · 미반영 0. 원문으로 다시 확인: auto_core_tickets.py 57~64·264행, auto_core_decide.py 296~308·485~487행, portfolio_exposure.py 185~188행, supplement grep 4곳, 테스트 5곳 행, t3-proceeds-qqq 55행. (작업자 약 197k 토큰 · 5.8분)
- 확인 필요(Judge 항목으로 넘김): S7 비중과 코어 표시 비중의 분모가 같은지 · FAIL 기록 뒤 알림 경로 · 통합 점검이 읽는 S7 실행이 카드 인자를 주는지(통합 점검 지시문에 채우기 권고 문장은 grep 0건).
- 검토 완결: 원문 확인 위 목록 · 내장 재검토 1회(반영 8건) · 미해결 3(확인 필요, Judge로) · 자료 시점 2026-11-26 22:30 KST(S7 11/25 종가) · 바뀔 조건: 코드가 채우기·3배 매수 길을 다른 곳에서도 연다는 원문이 나오면 범위를 다시 잰다.

## 9. 결정 기록

- **2026-11-26 22:28:38 KST 사장 결정 카드 '안1 착수 (권장)'** — 질문 "정책 묶음 A(policy-a-1126)를 어떤 범위로 착수할까요?", 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX974dyb4vV33MkVCvzBsrPNp(이 스레드 '정책 묶음 A 진행하기'가 22시대에 올림, 바로 앞 제안 = 이 문서 sha256 0672069b…20fdd2), 고른 항목 A(첫째), 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH(프로젝트 주인 = 사장), 기록 출처 = 그 카드의 하네스 알림(decision-chosen). 고르지 않은 것: 안2 착수(채우기 QQQ) · 안 함(지금대로).
- 정한 것: 범위 = 3절 안 1, 착수 = 수동 경로 Builder와 독립 Judge(CLAUDE.md Change classes — 같은 날 1회). 반등 알림 범위는 넣지 않음(카드 안내문대로). 표시: 사장 직접 결정 · 위험을 알고 시험 생략 · 미검증(strategy-revision-2026-11-01.md 9절 3행).
- 정하지 않은 것: 병합(사장 PowerShell 한 줄, Judge PASS 뒤 따로).
- **2026-11-27 00:35:53 KST 사장 결정 카드 '보류'** — 질문 "정책 묶음 A(policy-a-1126)를 11/27에 병합할까요?", 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9Dd7cLj8CsL4HvQ3yrEBNT7, 고른 항목 B(둘째), 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH, 기록 출처 = 그 카드의 하네스 알림. 카드 안내문: "병합하지 않고 작업 공간에 그대로 둡니다. 12/10까지 다시 정하고, 그때도 안 되면 cal-2027을 먼저 합니다." 그때 상태: Builder 완료(worktree-policy-a, 기준 9e48ef2, 커밋 안 함) · 독립 Judge PASS(보고 sha256 9973796f…4176d2, Judge worktree keen-borg-7d091b) · 병합 스크립트 policy-a-merge-2026-11-27.ps1(2026-11-27에만 돎, 실행 안 됨). 정책·코어·예약 변경 없음. 다시 병합을 고르면 그날 날짜·기준 커밋으로 병합 스크립트를 새로 만든다(기준이 바뀌었으면 테스트부터 다시).
- 색인: active-decisions.md C절 policy-a-1126 행 · G절 fx-5a 행에 덧붙임.
