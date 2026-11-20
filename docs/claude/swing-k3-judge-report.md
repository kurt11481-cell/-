---
id: swing-k3-judge-report
title: "스윙 실전 종목 상품 승인 넓히기(PLTR·CRWD) + 원본 상품 등록부 정리 — 독립 Judge 보고"
date: 2026-11-20
judge: "수동 경로 독립 Judge(읽기 전용, Builder와 다른 별도 세션). 착수 근거: 사장 직접 입력 2026-11-20 16:04:53 KST '지금 착수해줘'(active-decisions.md 165행 swing-k3-1120)"
target: "worktree .claude/worktrees/swing-k3 · 브랜치 worktree-swing-k3 · HEAD 0878e76 · 커밋 안 한 변경"
criteria: "메인 작업 트리 docs/claude/swing-k3-builder-prompt.md(바꿀 내용·지켜야 할 것·Judge 확인 항목 1~8) + worktree docs/claude/swing-k3-report.md·swing-k3-BLOCKED.md + 사장 결정 2건(registry_version 유지 카드 16:44:43 KST, test_auto_core_qqq_b.py 34행 허용 직접 입력 16:52:34 KST)"
location_note: "지시는 메인 작업 트리 docs/claude/swing-k3-judge-report.md였으나, 이 세션의 worktree 보호 훅이 메인 작업 트리 쓰기를 막아 Judge 세션 worktree(.claude/worktrees/dazzling-moore-78f859/docs/claude/)에 썼다. 커밋하지 않음."
verdict: PASS
---

# 판정: **PASS**

8개 확인 항목 모두 통과. 등록부 8종목 신원은 SEC 원문을 이 세션에서 직접 열어 보고와 대조했고, 대상 테스트·해시 검증을 worktree에서 다시 돌려 Builder 보고와 같은 결과를 얻었다. 권한 표지·주문 경로·schemas 변경 없음.

병합 때 지킬 것(결함 아님): ① `instrument_registry.json`과 `alert_policy.json`은 **한 커밋으로** 넣는다(해시가 서로 묶여 있어 하나만 들어가면 POLICY_REGISTRY_MISMATCH로 fail-closed). ② 병합 스크립트가 파일 해시를 다시 확인한다.

이 Judge가 한 일: 파일 읽기, 쓰기 없는 테스트 실행, SEC 공개 문서 읽기(일반 User-Agent, 개인 정보 없음), 이 보고 파일 1개 쓰기. 하지 않은 일: 대상 파일 수정·커밋·병합·dev-run/dev-merge·키움 호출·auto_core 실행·비밀 읽기.

## 항목별 근거

### 1. diff 범위 · 권한 표지 · 주문 경로 · schemas — 통과
- `git status --short`: 수정 6(auto_core_tickets.py · test_auto_core_qqq_b.py · test_portfolio_exposure.py · test_qqq_registration.py · alert_policy.json · instrument_registry.json) + 새 파일 3(test_swing_k3_registration.py · swing-k3-report.md · swing-k3-BLOCKED.md). 전부 허용 파일.
- 기존 테스트는 지정 행만: test_portfolio_exposure.py 107·112행, test_qqq_registration.py 77행(34행 상수 그대로), test_auto_core_qqq_b.py 34행(사장 허용 1줄).
- diff 전체(189+/11−)를 눈으로 읽음: order_authority·quantity_authority·execution_quantity·kill_switch·hard_ceiling 줄 변경 없음, 주문 경로 문자열 추가 없음(주문 경로 문자열 grep은 PC 안전 훅 kiwoom_order_block이 막아 diff 전문 육안 확인으로 대신함).
- `git diff --stat -- manage-us-stock-strategy/schemas` 빈 결과.
- 줄바꿈: 대상 7개 파일 모두 줄 수 = CRLF 수(등록부 410/410, 정책 932/932, auto_core_tickets.py 1313/1313, 새 테스트 153/153 등), 추적 파일 `i/lf w/crlf` 그대로. auto_core_tickets.py 비ASCII 바이트 0.

### 2. 등록부 8종목 신원 = SEC 원문 — 통과 (원문 직접 확인 2026-11-20 16:58~16:59 KST)

| 종목 | 원문 법인명 | 원문 증권 종류 | 원문 거래소 | 일치 |
|---|---|---|---|---|
| LITE | Lumentum Holdings Inc. | Common Stock, par value of $0.001 per share | Nasdaq Global Select Market | 일치 |
| PWR | Quanta Services, Inc. | Common Stock, $0.00001 par value | New York Stock Exchange | 일치 |
| MU | Micron Technology, Inc. | Common Stock, par value $0.10 per share | Nasdaq Global Select Market | 일치 |
| DELL | Dell Technologies Inc. | Class C Common Stock, par value of $0.01 per share | New York Stock Exchange | 일치 |
| AMD | ADVANCED MICRO DEVICES, INC. | Common Stock, $0.01 par value per share | The NASDAQ Global Select Market | 일치(대소문자만) |
| PLTR | Palantir Technologies Inc. | Class A Common Stock, par value $0.001 per share | The Nasdaq Stock Market LLC | 일치 |
| CRWD | CROWDSTRIKE HOLDINGS, INC. | Class A common stock, par value $0.0005 per share | The Nasdaq Stock Market LLC (Nasdaq Global Select Market) | 일치(대소문자만) |
| TQQQ | ProShares UltraPro QQQ (485BPOS f46020d1.htm: 표지 표 'UltraPro QQQ® TQQQ Nasdaq', 펀드 절 '… three times (3x) the daily performance of the Nasdaq-100® Index', SAI 'ProShares Trust is a Delaware statutory trust … open-end management investment company'; 제출 색인 S000024908 / C000074098, CIK 0001174610) | ETF 주식 | Nasdaq | 일치(3배·Nasdaq-100·시리즈 ID) |

URL은 등록부 `official_identity_source_url`·보고 2절과 같고, 그 URL을 그대로 열어 확인했다. 원문 인용 없이 들어간 종목 없음.

### 3. new_buy · watchlist · candidate_status — 통과
- 등록부 27개 항목 전부 `new_buy_instrument_approved` false(보고 3절 "21개 항목"은 변경 전 개수 — 표기만 틀림).
- 8종목 `watchlist_approved` false · `candidate_status` inactive · `short_sale_approved` false.
- 소비자 행 대조: screen_tactical_candidates.py 62~66(유니버스 active만) · run_tactical_opportunity_radar.py 45~47(유니버스 active+watchlist true만) — 유니버스에서 PLTR·CRWD inactive·false, 6종목은 없음 → 새 경로 없음. validate_decision_record.py 183~190 등록부·유니버스 값 일치(false=false). `portfolio_bucket`은 scripts에서 읽는 코드 0건.
- 새로 열리는 읽기 전용 경로(보고에 적힘, 확인): portfolio_decision_dashboard.py 1023~1045 `_instrument_mapping` — 위험 봉투 fallback에 8종목이 없어 이전엔 RISK_MAPPING_UNVERIFIED, 이제 등록부 값으로 계산. 주문·수량 권한 없음. PLTR·CRWD theme `user_defined_ai_agent`는 성장·AI·반도체 묶음 밖 — 지시문이 theme 유지를 정했고 표시용이라 판정 영향 없음, 참고.
- TQQQ에 confirmation_mode·research_instrument_type을 넣지 않음(레버리지 비교·초보자 보고 경로를 열지 않음) — 지시문 범위와 맞음.

### 4. required_canonical_sha256 = canonical_hash — 통과
`validate_registry_consistency` 직접 실행: VALIDATED, errors [], warnings []. canonical_hash `85fb33b34eb1713c32fa10f4d5cf04061a509963da4f02ba8b391a3509e8bba9` = alert_policy.json 177행. HEAD 등록부 해시 `8faed6da…a3e1` = 바꾸기 전 정책 값. registry_version `2026-09-02-lmt-instrument-registry-v1` 그대로(사장 결정), 픽스처 7행과 같음. 정책 사본 `decision_harness.instrument_registry`(BE·DRAM·MVLL·NBIL·NBIS·SOXL) 무변경.

### 5. CRWD 포함 — 통과
active-decisions.md 160행 `crwd-card-1120: CRWD 관심 카드 v1 수락 · 2026-11-20 15:59:32 KST` 있음.

### 6. 정책 문턱·목록 — 통과
hard_ceiling 1.9 · reduce 1.85 · target 1.55 · single_stock_nominal_cap 0.4 · add_default `card_add_stock_else_SOXL` · allowed_index_etfs [SOXL, TQQQ, DRAM, QQQ]. INDEX_ETFS·PARKING_ETFS·ONE_X_UNREGISTERED 무변경. APPROVED_BUY = 기존 10 + PLTR·CRWD. card_stock_core 앞 7종목 순서 그대로.

### 7. 대상 테스트 — 통과 (worktree 재실행, Python 3.15.2)

| 패턴 | 결과 |
|---|---|
| test_swing_k3_registration.py | Ran 8 · OK |
| test_portfolio_exposure*.py | Ran 154 · OK |
| test_qqq_registration.py | Ran 8 · OK |
| test_reconcile_broker_state.py | Ran 57 · OK |
| test_validate_decision_record.py | Ran 3 · OK |
| test_auto_core*.py | Ran 667 · failures 1 · skipped 1 (test_auto_core_decide …every_hash_matches, symbol='SOXL') |
| validate_schema_contracts.py | PASS · errors [] |

SOXL 실패는 메인 작업 트리(HEAD 0878e76, 대상 파일 무변경)에서도 같은 실패(Ran 70 · failures 1) → 기준선 실패. 새 실패 0. 새 테스트는 지시문 D a~f 모두 포함.

### 8. 연결표 원문 행 — 통과
auto_core_tickets.py 61·264 · auto_core_decide.py 1085·1185·1262 · portfolio_exposure.py 169·1207~1208·1211~1212·1216~1220 · reconcile_broker_state.py 108(113~122)·148 · validate_registry_consistency.py 38 — 모두 확인. 통합 점검 규칙 integrated-check-prompt-v3.12.18-2026-11-19.txt(현행, scheduled-prompts/README.md 12행) 134행 ② 승인 목록에 PLTR·CRWD 없음 · 324행 '상품 승인 없음' 자기 검사 확인. 그 행은 '끊김'으로 표시되고 메울 변경(규칙 1줄 + H1 + 독립 검토)과 승인 경로(`예약 작업 변경 승인: 보유·관심 종목 통합 점검`)가 붙어 있음.

## 남은 위험(범위 밖, 판정 영향 없음)
- CRWD 분할 기록 없음 → SPLIT_SUSPECTED로 CRWD 주문표 막힘(별도 경로).
- M6 `m6_listed` 이름 일치 통과 — 분할 기록 전 CRWD 비교 문서 또는 코드 좁히기 필요.
- 통합 점검 134행 목록은 병합 뒤 따로.
- 지금 S7 새 매수 멈춤이라 PLTR·CRWD 주문표는 당장 없음.

## 판정을 바꿀 조건
병합 전 worktree 파일이 이 검토 뒤 바뀜 · SEC 원문 정정(10-K/A·새 485BPOS) · 사장 결정 2건 원문이 전달 내용과 다름.

검토 완결: 원문 확인 8/8 항목(SEC 8/8 종목) · 미해결 0 · 자료 시점 2026-11-20 16:58~17:0x KST.
