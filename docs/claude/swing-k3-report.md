---
id: swing-k3-report
title: "스윙 실전 종목 상품 승인 넓히기(PLTR·CRWD) + 원본 상품 등록부 정리 — Builder 보고"
date: 2026-11-20
builder: "수동 경로 Builder (Claude Code, worktree .claude/worktrees/swing-k3, 브랜치 worktree-swing-k3, 기준 0878e76 = codex/master-recovery-expansion HEAD)"
instruction: "메인 작업 트리 docs/claude/swing-k3-builder-prompt.md (미커밋, 절대 경로로 읽음)"
commit: "없음 — 바뀐 파일은 worktree에 커밋하지 않은 채 둔다(병합 스크립트가 해시 확인 뒤 커밋)"
---

**CRWD 포함.** 근거: 메인 작업 트리 docs/claude/active-decisions.md 160행 `crwd-card-1120: CRWD 관심 카드 v1 수락(관심 유지) · 2026-11-20 15:59:32 KST`(착수 때 행 있음 확인). 범위 근거는 같은 파일 165행 `swing-k3-1120`(착수 2026-11-20 16:04:53 KST 사장 직접 입력 '지금 착수해줘').

신원 BLOCKED: **없음** — 8종목 모두 SEC EDGAR 원문을 열어 확인했다.
테스트 BLOCKED: **해소** — 허용 밖 테스트 2건: test_validate_decision_record는 버전 이름 유지로, test_auto_core_qqq_b.py 34행은 사장 결정·직접 입력으로 1줄 수정(4절, docs/claude/swing-k3-BLOCKED.md 5절).

## 1. 바뀐 줄

| 파일:행(worktree 기준) | 앞 | 뒤 |
|---|---|---|
| workspace/policies/instrument_registry.json:3 | `"registry_version": "2026-09-02-lmt-instrument-registry-v1"` | **바꾸지 않음** — 한때 `2026-11-20-swing-k3-instrument-registry-v1`로 바꿨다가 사장 결정 카드 2026-11-20 16:44:43 KST '1줄 고침 + 이름 그대로'로 원래 값 복귀(픽스처 decision-record.valid.test-only.json 7행과 일치) |
| 같은 파일 182(앞)→182~203(뒤) | CRWD 한 줄 객체(identity_status `user_supplied_pending_primary_verification`, leverage_factor_status `provisional_not_usable_for_live_policy`, portfolio_bucket `historical_research_registry`) | NOW 형식 여러 줄 객체: 신원 필드 + identity_status `verified_primary_source` · leverage_factor_status `verified` · portfolio_bucket `operational_reference`. watchlist_approved false · candidate_status inactive · new_buy false · short false · theme/subtheme 그대로 |
| 같은 파일 184(앞)→205~226(뒤) | PLTR 한 줄 객체(CRWD와 같은 미검증 값) | CRWD와 같은 방식 |
| 같은 파일 230(앞)→272~407(뒤) | QQQ가 마지막 항목 | QQQ 뒤에 LITE·PWR·MU·DELL·AMD·TQQQ 새 항목 6개 |
| stock-strategy-system/alert_policy.json:177 | `required_canonical_sha256`: `8faed6da…a3e1` | `85fb33b34eb1713c32fa10f4d5cf04061a509963da4f02ba8b391a3509e8bba9` (= validation_common.canonical_hash(새 등록부), 버전 복귀 뒤 재계산) |
| 같은 파일:698 | `nominal_multipliers` … `"LITE": 1, "QQQ": 1, …` | … `"LITE": 1, "PLTR": 1, "CRWD": 1, "QQQ": 1, …` (한 줄 형식 유지) |
| 같은 파일:746 | `card_stock_core`: BE·MU·NBIS·DELL·AMD·PWR·LITE | 끝에 PLTR·CRWD |
| manage-us-stock-strategy/scripts/auto_core_tickets.py:60~61 | 주석 `(PWR, LITE: user approval 2026-10-08).` · `APPROVED_BUY` 10개 | 주석 끝에 `; PLTR, CRWD: user approval 2026-11-20 swing-k3-1120` · `APPROVED_BUY` 끝에 `"PLTR", "CRWD"` (행 수 그대로, ASCII) |
| manage-us-stock-strategy/tests/test_portfolio_exposure.py:107 | 배수 dict … `"LITE": 1, "QQQ": 1}` | … `"LITE": 1, "PLTR": 1, "CRWD": 1, "QQQ": 1}` |
| 같은 파일:112 | card_stock_core 7종목 | 9종목(끝에 PLTR·CRWD) |
| manage-us-stock-strategy/tests/test_qqq_registration.py:77 | `section["card_stock_core"] == CARD_STOCK_CORE_BEFORE` | `section["card_stock_core"][:7] == CARD_STOCK_CORE_BEFORE` (34행 상수는 그대로) |
| manage-us-stock-strategy/tests/test_swing_k3_registration.py | 없음 | 새 파일(테스트 8개, 4절) |
| manage-us-stock-strategy/tests/test_auto_core_qqq_b.py:34 | `APPROVED_BUY == OLD_APPROVED_BUY` | `APPROVED_BUY[:10] == OLD_APPROVED_BUY` (사장 허용 추가 1줄, 4절) |
| docs/claude/swing-k3-report.md · swing-k3-BLOCKED.md | 없음 | 이 보고 · 막힘 기록(해소) |

건드리지 않은 것: 등록부의 다른 13개 항목·`authority` 블록·키 순서·들여쓰기, alert_policy의 `decision_harness.instrument_registry`(정책 사본)·add_default·allowed_index_etfs·문턱·single_stock_*·instrument_approval_gate, auto_core_tickets.py의 `ONE_X_UNREGISTERED`·INDEX_ETFS·PARKING_ETFS·AUTHORITY, schemas/. 줄바꿈: 다섯 파일 모두 작업 트리 CRLF 그대로(등록부 410줄 = CRLF 410, alert_policy 932 = 932, auto_core_tickets 1313 = 1313), 새 테스트 파일도 CRLF.

## 2. 종목별 신원 출처 (SEC EDGAR 원문, 확인 시각 = 내려받은 시각)

모두 `https://www.sec.gov/files/company_tickers_exchange.json`(티커→CIK)과 `https://data.sec.gov/submissions/CIK<10자리>.json`(최신 10-K 찾기)으로 문서를 찾은 뒤, 문서 표지의 'Securities registered pursuant to Section 12(b) of the Act' 표를 읽었다.

| 종목 | 법인명(10-K 표지) | 증권 종류 | 거래소 | 원문 URL(문서) | 확인 시각(KST) |
|---|---|---|---|---|---|
| LITE | Lumentum Holdings Inc. | Common Stock, par value of $0.001 per share | Nasdaq Global Select Market | https://www.sec.gov/Archives/edgar/data/1633978/000162828026057358/lite-20260627.htm (10-K FY 2026-06-27, 제출 2026-08-17) | 2026-11-20 16:09:04 |
| PWR | Quanta Services, Inc. | Common Stock, $0.00001 par value | New York Stock Exchange | https://www.sec.gov/Archives/edgar/data/1050915/000105091526000006/pwr-20251231.htm (10-K FY 2025-12-31, 제출 2026-02-19) | 2026-11-20 16:09:01 |
| MU | Micron Technology, Inc. | Common Stock, par value $0.10 per share | Nasdaq Global Select Market | https://www.sec.gov/Archives/edgar/data/723125/000072312526000023/mu-20260903.htm (10-K FY 2026-09-03, 제출 2026-10-09) | 2026-11-20 16:09:01 |
| DELL | Dell Technologies Inc. | Class C Common Stock, par value of $0.01 per share | New York Stock Exchange | https://www.sec.gov/Archives/edgar/data/1571996/000157199626000008/dell-20260130.htm (10-K FY 2026-01-30, 제출 2026-03-16) | 2026-11-20 16:09:03 |
| AMD | ADVANCED MICRO DEVICES, INC. (등록부에는 Advanced Micro Devices, Inc.) | Common Stock, $0.01 par value per share | The NASDAQ Global Select Market | https://www.sec.gov/Archives/edgar/data/2488/000000248826000018/amd-20251227.htm (10-K FY 2025-12-27, 제출 2026-02-04) | 2026-11-20 16:09:00 |
| PLTR | Palantir Technologies Inc. | Class A Common Stock, par value $0.001 per share | The Nasdaq Stock Market LLC | https://www.sec.gov/Archives/edgar/data/1321655/000132165526000011/pltr-20251231.htm (10-K FY 2025-12-31, 제출 2026-02-17) | 2026-11-20 16:09:02 |
| CRWD | CROWDSTRIKE HOLDINGS, INC. (등록부에는 CrowdStrike Holdings, Inc.) | Class A common stock, par value $0.0005 per share | The Nasdaq Stock Market LLC (Nasdaq Global Select Market) | https://www.sec.gov/Archives/edgar/data/1535527/000153552726000010/crwd-20260131.htm (10-K FY 2026-01-31, 제출 2026-03-05) | 2026-11-20 16:09:02 |
| TQQQ | ProShares UltraPro QQQ, a series of ProShares Trust (CIK 0001174610, 시리즈 S000024908, 클래스 C000074098 — `company_tickers_mf.json`) | ETF 주식(ProShares Trust = Delaware statutory trust, 1940 Act 개방형 투자회사로 등록 — 원문 SAI 'GENERAL INFORMATION ABOUT THE TRUST') | Nasdaq (원문 표지 표 'UltraPro QQQ® TQQQ Nasdaq') | https://www.sec.gov/Archives/edgar/data/1174610/000117461026000755/f46020d1.htm (485BPOS 제출 2026-09-25; 그 제출 색인 0001174610-26-000755-index.htm에 S000024908·C000074098 있음 확인) | 2026-11-20 16:09:43 |

TQQQ 레버리지 원문: 같은 485BPOS의 펀드 절 "ProShares UltraPro QQQ® (the “Fund”) seeks daily investment results … three times (3x) the daily performance of the Nasdaq-100® Index" → leverage_factor 3.0 · daily_target_multiple 3.0 · underlying_index Nasdaq-100 Index · confirmation_proxy QQQ.

CRWD 분할(신원과 무관, 원문 확인): 8-K 2026-06-03(https://www.sec.gov/Archives/edgar/data/1535527/000153552726000022/crwd-20260603.htm, 2026-11-20 16:10:02 KST 확인) Item 8.01 — 이사회가 Class A 보통주 4:1 분할(주식 배당 방식) 승인, 기준일 2026-06-25 마감 보유자에게 2026-07-01 장 마감 뒤 1주당 3주 추가, 분할 반영 거래는 그 다음(원문 'trading is expected to begin on a split-adjusted basis on Jul…'). 신원 필드(법인·증권 종류·거래소)는 분할로 바뀌지 않는다.

쓴 원문 조회는 SEC 공개 파일 읽기뿐(User-Agent는 일반 연구용 문구, 개인 정보 없음). 키움·주문 도구 호출 없음.

## 3. 등록부 필드 소비자 표와 고른 값

| 필드 | 읽는 코드(원문 행) | 무엇을 여나 | 고른 값과 이유 |
|---|---|---|---|
| identity_status | reconcile_broker_state.py 113~122(`startswith("verified")`) · screen_tactical_candidates.py 81·87 · run_tactical_opportunity_radar.py 238·314 · validate_decision_record.py 274 · build_holding_strategy_review.py 163 | 대조의 보유 신원 확인, 레이더·검토의 '신원 미확인' 사유 해제 | `verified_primary_source` — 이번 목표(LITE 매일 경고 해소). 레이더·스크린은 아래처럼 관심 명단 쪽 값이 따로 막는다 |
| watchlist_approved | screen_tactical_candidates.py 85(**전술 유니버스** 후보 값) · run_tactical_opportunity_radar.py 46·314(**유니버스** 값) · validate_decision_record.py 178~195(등록부 값 = 유니버스 값이어야 함) · validate_registry_consistency.py 14·46(정책 사본과 같아야 함 — 8종목은 사본에 없음) | 레이더·스크린 생존 후보, 결정 기록 검증 | **false (8종목 모두)** — 레이더·스크린은 유니버스 값을 읽으므로 등록부 true는 새 경로를 열지 않지만, validate_decision_record 186~190은 등록부·유니버스 불일치를 오류로 낸다. 유니버스(workspace/policies/tactical_candidate_universe.json, 이번 범위 밖)에서 PLTR·CRWD는 false이고 나머지 6종목은 없음 → false가 일치하는 닫힌 값 |
| candidate_status | 등록부 값을 읽는 코드 없음(grep: screen_tactical_candidates.py 65·run_tactical_opportunity_radar.py 46은 **유니버스** 후보 값을 읽음; materialize/validate_kiwoom_session_aware_* 의 candidate_status는 다른 문서 필드) | 없음 | **inactive (8종목 모두)** — 닫힌 쪽. PLTR·CRWD는 지금 값 그대로 |
| portfolio_bucket | 저장소 .py·.ps1 어디에도 읽는 코드 없음(grep 0건) | 없음 | **operational_reference** (8종목) — 기존 값 중 '운영 참조'(NBIL)를 재사용. 실행 경로 영향 없음. PLTR·CRWD를 `historical_research_registry`에서 바꾼 이유: 이제 승인 상품의 운영 신원 기록이라 '옛 연구 기록'이 사실과 다름 |
| new_buy_instrument_approved | validate_decision_record.py 278 · screen_tactical_candidates.py 94 · validate_registry_consistency.py 14 | 결정 기록·스크린의 신규 매수 표시 | **false (등록부 21개 항목 모두)** — 지시문대로 |
| leverage_factor · leverage_factor_status · theme | portfolio_decision_dashboard.py 1023~1045 `_instrument_mapping`(위험 봉투에 대체 매핑이 없을 때 등록부 값으로 NORMAL_STOCK/LEVERAGED_PRODUCT, theme ∈ {ai_infrastructure, leveraged_semiconductor, semiconductor}면 성장·AI·반도체 묶음) — portfolio_decision_order_intent.py 210·286·379도 같은 함수 | 읽기 전용 대시보드·주문 의향 문서의 위험 지표. 지금까지 8종목은 `RISK_MAPPING_REQUIRED`/`RISK_MAPPING_UNVERIFIED`로 막혔고 이제 계산된다 | 신원 원문에 맞춘 값: 주식 1.0 `verified`, TQQQ 3.0 `verified`. theme: MU·AMD `semiconductor`, LITE·PWR·DELL `ai_infrastructure`(BE·NBIS 선례) → 묶음에 **들어가는 쪽**(집중도 계산이 더 보수적). PLTR·CRWD는 기존 theme 그대로(user_defined_ai_agent, 묶음 밖). TQQQ `leveraged_broad_market_index`(묶음 밖, 3배라 LEVERAGED_PRODUCT). 주문 권한 없음(order_authority false 유지) |
| confirmation_proxy · daily_target_multiple (TQQQ) | resolve_leveraged_quote.py 119~158(`confirmation_mode`가 DIRECTION_ONLY/DAILY_MULTIPLE일 때만 비교) · render_beginner_portfolio_report.py 273(research_instrument_type 3종만 허용) | 비교 표시만(product_close_substitution false) | 지시문 4필드(leveraged_etf·3·3·QQQ)만. `confirmation_mode`·`confirmation_role`·`research_instrument_type`은 **넣지 않음** — 넣으면 레버리지 비교·초보자 보고 경로가 TQQQ에 새로 열린다(SOXL 값 SECTOR_LEVERAGED_ETF는 TQQQ에 틀림). 빠진 채면 비교는 NOT_APPLICABLE, 보고는 ISSUER_PRODUCT_MISMATCH로 닫힌다 |
| shadow_acceptance.py 219~242 | MVLL·SOXL의 확인 필드만 해시 | 없음 | 영향 없음 |
| holding_baseline_operationalization.py 41 · complete_holding_event_coverage.py 78 | 등록부 경로를 '보호 입력(쓰기 금지)'으로만 사용 | 없음 | 영향 없음 |

## 4. 테스트

**상태: 해소 — 기준선 실패 외 새 실패 0.** (BLOCKED 경과는 docs/claude/swing-k3-BLOCKED.md)

결정 반영: 사장 결정 카드 2026-11-20 16:44:43 KST '1줄 고침 + 이름 그대로'(cmsg_0137MRzn9nuDvvQmVxm6WeX9W7RfSGDrByRLbAHeUHHdoT) + 사장 직접 입력 2026-11-20 16:52:34 KST 'test_auto_core_qqq_b.py 34행 고쳐'(cmsg_0137MRzn9nuDvvQmVxm6WeX9CqjhBx6xMe3o6X1ALGzPum).
- manage-us-stock-strategy/tests/test_auto_core_qqq_b.py:34 `assertEqual(tickets.APPROVED_BUY, OLD_APPROVED_BUY)` → `assertEqual(tickets.APPROVED_BUY[:10], OLD_APPROVED_BUY)` (22행 상수·35행 그대로, CRLF 유지)
- 등록부 registry_version 원래 값 유지(1절 표) · 픽스처 무변경

실행 형식 `python -m unittest discover -s manage-us-stock-strategy/tests -p "<패턴>"`(앞에 변수·옵션 없음). 기준선 = 같은 worktree 수정 전(0878e76).

| 패턴 | 기준선 | 최종 |
|---|---|---|
| test_swing_k3_registration.py | (없음) | Ran 8 · OK |
| test_portfolio_exposure*.py | Ran 154 · OK | Ran 154 · OK |
| test_qqq_registration.py | Ran 8 · OK | Ran 8 · OK |
| test_auto_core*.py | Ran 667 · failures 1 · skipped 1 | Ran 667 · failures 1(같은 SOXL) · skipped 1 |
| test_reconcile_broker_state.py | Ran 57 · OK | Ran 57 · OK |
| (추가) test_validate_decision_record.py | Ran 3 · OK | Ran 3 · OK |
| (추가) test_v2_1_hardening.py · test_evaluate_outcome.py | 29 · 3 OK | 29 · 3 OK |
| (추가) test_portfolio_decision_order_intent.py | Ran 73 · errors 1(lmt) | Ran 73 · errors 1(같은 것) |
| (추가) test_instrument_identity_authority.py | Ran 24 · OK | Ran 24 · OK |
| (추가, 중간 실행만) test_portfolio_decision_dashboard.py | 미측정 | Ran 306 · failures 1 — git에 없는 workspace/outputs 픽스처 부재(1503행), 변경과 무관 |
| validate_schema_contracts.py | — | exit 0 · PASS · errors [] |

기준선 실패(고치지 않음): test_auto_core_decide RegistryTests …every_hash_matches (symbol='SOXL') · test_portfolio_decision_order_intent …test_lmt_candidate_classification_is_verified_but_non_actionable.

`git diff --ignore-cr-at-eol --stat` (미추적 새 파일 test_swing_k3_registration.py·이 보고·BLOCKED 제외):
```
 .../scripts/auto_core_tickets.py                   |   4 +-
 .../tests/test_auto_core_qqq_b.py                  |   2 +-
 .../tests/test_portfolio_exposure.py               |   4 +-
 .../tests/test_qqq_registration.py                 |   2 +-
 stock-strategy-system/alert_policy.json            |   6 +-
 workspace/policies/instrument_registry.json        | 182 ++++++++++++++++++++-
 6 files changed, 189 insertions(+), 11 deletions(-)
```

## 5. 병합 뒤 첫 06:15 실행에서 확인할 것
1. 코어 result.json `warnings`에 `POST_APPLY_CHECK_ERROR:LITE: canonical instrument registry record is missing or unverified` 줄이 없다(reconcile_broker_state.py 113~122 — LITE가 이제 등록부에 `verified_primary_source`).
2. `POST_APPLY_ALERT_ENGINE_CHECK_FAILED`가 남으면 남은 오류 원문을 그대로 적는다(신원 외 원인 — 예: 보유 종목 평균단가 누락 — 은 이번 변경과 무관하게 남을 수 있다).
3. 등록부 해시: validate_registry_consistency가 VALIDATED(정책 177행 = 새 canonical_hash). 병합 스크립트가 두 파일을 함께 넣지 않으면 POLICY_REGISTRY_MISMATCH → 실행 검토 fail-closed가 되므로 두 파일은 한 커밋으로.
4. 노출 검토(portfolio_exposure) — PLTR·CRWD를 보유하지 않으면 변화 없음. 보유하면 `unregistered_instrument_held`에 나오지 않고 1배로 E에 들어간다.

## 6. 남은 위험·확인 결과
- **CRWD 코어 주문표 없음(분할 기록 전까지)**: 2026-07-01 4:1 분할 공식 기록이 corporate-actions.json에 없어 auto_core_bars.py 154~166이 `SPLIT_SUSPECTED:CRWD:<세션>`을 내고 CRWD 지표가 모두 unknown → 매수 주문표 없음. 분할 기록은 이 범위 밖(별도 경로, Cowork).
- **M6 CRWD 가짜 통과**: auto_core_rules.py 996~1003 `m6_listed`는 `docs/claude/m6-relative-comparison-7stock*.md` 본문에 기호 문자열이 있으면 통과(`symbol in text`). 2026-10-17 문서에서 CRWD는 108행 자료 출처 줄(`… PLTR(raw)·CRWD(adjusted) 300봉 …`) 한 번뿐이고 비교 줄은 없다(grep -c CRWD = 1; PLTR = 11). 그래서 코어 매수 요건 ④는 CRWD를 '통과(m6-relative-comparison-7stock-2026-10-17.md)'로 표시한다 — 실제 비교 근거 없음. 지금은 위 SPLIT_SUSPECTED가 먼저 막지만, 분할 기록이 들어가면 ④가 근거 없이 통과한다. 고칠 길: M6 CRWD 비교 문서를 쓰거나 m6_listed를 표 행 일치로 좁히기(코드 변경 — 개발 큐) — 이 범위 밖, 보고만.
- **코어가 PLTR·CRWD 매수 주문표를 낼 수 있는 조건**: auto_core_decide.py 1085 `buy_approved=symbol in APPROVED_BUY`(이제 참) + 같은 함수의 매수 요건 ①(실적 금지 구간 — card_stock_core 진입으로 portfolio_exposure.py 1216~1220 earnings_blackout 대상; 실적 자료가 없으면 `EARNINGS_DATE_UNVERIFIED`로 막힘, 새 테스트 c가 확인. PLTR·CRWD는 docs/claude/earnings-anchors.json에 있음) · ③ 카드(card-evidence-registry.json 수락) · ④ M6 · ⑤ R-REC1, 그리고 S7 노출 띠. 지금은 S7 하드 상한 띠로 새 매수 멈춤이라 당장 주문표 없음. 재배치 순위: auto_core_decide.py 1185 `policy_instruments = card_stock_core ∪ allowed_index_etfs` → 1262 `redeploy_ranking` 후보에 PLTR·CRWD가 들어간다(매도 후회 다리의 순위 표시).
- **ONE_X_UNREGISTERED**(auto_core_tickets.py 66, 사용 177~178): 정책 배수에 없는 기호에만 쓰인다. PWR·LITE는 이미 정책 배수에 있어(alert_policy.json 698) 이 목록의 PWR·LITE는 지금 쓰이지 않고, 실제로 쓰이는 것은 MRVL뿐. 바꾸지 않음(지시문).
- **통합 점검 134행 승인 목록**: 이번 변경에 포함 안 됨 — 병합 뒤 `예약 작업 변경 승인: 보유·관심 종목 통합 점검` 경로로 따로(연결표 4행 '끊김').
- **위험 지표 매핑 새로 열림(읽기 전용)**: 3절 leverage/theme 행 — 대시보드·주문 의향 문서에서 8종목 위험 지표가 계산되기 시작한다. 주문·수량 권한은 없다.

## 7. 연결표 (analysis-linkage-map-2026-10-05.md 1절 8번) — 원문 행 대조 결과

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행(이 worktree에서 확인) | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| APPROVED_BUY(PLTR·CRWD) | 이 Builder → 사장 PowerShell 병합 | auto_core_tickets.py 61(정의)·264(`if symbol not in APPROVED_BUY` → '상품 승인 없음') · auto_core_decide.py 1085(`buy_approved=`) | 매수 요건 통과 날 PLTR·CRWD 매수 주문표 | 새 테스트 d · 코어 result.json | 연결(병합 뒤) |
| 정책 배수·card_stock_core | 같음 | portfolio_exposure.py 169(card_stock_core 읽기)·1207~1208(배수 없으면 UNREGISTERED)·1211~1212(card_stock_core/index 아니면 NOT_AN_S5…)·1216~1220(실적 금지 구간) · auto_core_decide.py 1185·1262 | 보유 때 E에 1배 · 매수 자격 · 실적 판정 대상 · 재배치 후보 | 06:15 노출 검토 unregistered_instrument_held · 새 테스트 c | 연결(병합 뒤) |
| 원본 상품 등록부 8종목 신원 | 같음 | reconcile_broker_state.py 108~122(canonical_identity_errors)·148(alert_engine_check에서 호출) · validate_registry_consistency.py 38(해시 비교) | LITE 매일 경고 사라짐 · 새로 산 종목 신원 인식 | 06:15 코어 result.json warnings · 새 테스트 b·e | 연결(병합 뒤) — 지금 끊김(11/06~) |
| 통합 점검 134행 승인 목록 | 병합 뒤 이 프로젝트(예약 작업 변경) | integrated-check-prompt 134행 ② · 324행 자기 검사 — **이 worktree에서 원문 미확인**(지시문 인용) | 통합 점검 '상품 승인 없음' 막힘 해제 | 324행 자기 검사 · 코어 vs 통합 점검 ② 비교 | 끊김 — 메울 변경: 규칙 1줄 + H1 + 독립 검토 · 승인 경로: 사장 직접 입력 `예약 작업 변경 승인: 보유·관심 종목 통합 점검` |

행 번호 주의: portfolio_exposure.py의 '등록 안 됨'은 1207~1208, card_stock_core/index 검사는 1211~1212, 실적 판정은 1216~1220(지시문의 1211·1216은 각 if 줄과 일치). reconcile_broker_state.py의 호출 위치는 148(`errors.extend(canonical_identity_errors(...))`).

## 8. 지킨 것
- 실행하지 않음: auto_core.py·"auto_core.py"가 든 명령·reconcile apply·kiwoomcli·키움 호출·run_auto_core.ps1·dev-run/dev-merge/dev-queue. 상태·런타임·일지·원장·예약·대시보드 쓰기 없음. .claude 설정·비밀 읽기 없음.
- 권한 표지 줄(order_authority·quantity_authority·execution_quantity·kill_switch·hard_ceiling) 변경 없음, 주문 경로 문자열 추가 없음, schemas/ 변경 없음.
- git commit·push·병합 없음. worktree 생성만(`git worktree add -b worktree-swing-k3 .claude/worktrees/swing-k3 0878e76`).
