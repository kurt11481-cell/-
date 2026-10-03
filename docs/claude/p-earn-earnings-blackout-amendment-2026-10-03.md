# p-earn 실적 금지 구간 개정안 (K3) — 2026-10-03

- 관제판 작업: `p-earn`. 성격: K3(Production 의미). 상태: **수정안 작성 완료 · Judge 미실행 · 정책·코드 미변경**.
- 근거 결정: 2026-10-02 사용자 결정 1(`docs/claude/integrated-stock-cards-v1-2026-10-02.md` 8절 1번, "사용자 결정 (2026-10-02)" 절).
- 2026-10-03 사용자 선택: **D1** 확인하지 못한 경우는 막기 유지(fail-closed). **D2** 금지 구간 영문 정의 문구를 같이 명확화(동작 변화 없음).
- 기준값(2026-10-03 Cowork 확인, HEAD `25ec82bf1c72`):

| 파일 | git blob (HEAD) | raw sha256 앞 16자 | 작업 트리 |
|---|---|---|---|
| `stock-strategy-system/alert_policy.json` | `0a40505894935dbc05bd2b13fc4214f2cadc18d3` | `8e0965147600b85b` (CRLF 958줄, LF 단독 0) | HEAD와 같음 |
| `manage-us-stock-strategy/scripts/portfolio_exposure.py` | `87d2920c471bca205aa113334c3728e6f7e631f4` | `585803c220bfcf1d` | 같음 |
| `manage-us-stock-strategy/tests/test_portfolio_exposure.py` | `0b5cbfba49febd913820801622fe35c9868c91c6` | `3da8d3a35788bc60` | 같음 |
| `manage-us-stock-strategy/references/portfolio-exposure-review.md` | `9326aa60b0f6c76fa83c78c5f20888fb0f15a55a` | `0ea1429e2e60772b` | **수정됨**(미커밋 K0 9줄, "Token order", 165줄 아래) |
| `docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md` | `d8e436d885a7b5f42afc35723d1c69143668a2aa` | `4b1ebaddabd363f7` | 같음 |
| `workspace/policies/event_risk_policy.json` | `e94b42e2f19591a1069243d0d41cc9838107aa04` | `45a7e4e38f5accad` | 같음 |

## 결론 (먼저)

1. **확인된 "미공지"는 금지 구간이 아니다.** 공지된 실적일의 금지 구간(발표 세션 2세션 전 ~ 결과 뒤 첫 세션)은 그대로다.
2. **확인하지 못한 경우는 지금처럼 막는다**(기록 없음·오래된 확인·상태 모름·지난 실적일 기록만 있음). 화면에는 "실적일 확인 필요"로 보인다(D1).
3. **정책 문구만 바꾸면 동작은 안 바뀐다.** 실제로 막는 주체는 `portfolio_exposure.py`의 `earnings_blackout()`이고 정책 키를 읽지 않는다. 그래서 정책 2곳 + 함수 1개 + 테스트 + 문서 2곳을 한 K3 묶음으로 바꾼다.
4. 권한은 그대로다: 표시 전용, `order_authority=false`, `quantity_authority=none`. 금지 구간 밖이라는 사실은 매수 근거가 아니다(E1).

## 1. 현재 상태와 영향 범위

| # | 위치 | 현재 | 결정 1과 관계 |
|---|---|---|---|
| C1 | `alert_policy.json:813` `portfolio_exposure_policy.earnings_date_unverified` | `"treat_as_blackout"` | 충돌. 이 키를 읽는 코드는 없다(scripts grep 0건) — 문서 역할 |
| C2 | `alert_policy.json:539` `holding_timing_rules.new_buy_activation.earnings_blackout_single_stocks` (`:812` `earnings_blackout_ref`가 가리킴) | `"2 completed sessions before scheduled earnings through the first completed session after results"` | 충돌 없음. 시작 세션이 1세션 늦게도 읽힌다(카드 8절 10번). 이 값을 읽는 코드 없음 |
| C3 | `portfolio_exposure.py:759-785` `earnings_blackout()` | 기록 없음·`status != "VERIFIED"` → `EARNINGS_DATE_UNVERIFIED`, 지난 날짜 → `EARNINGS_DATE_STALE`, 달력 밖 → `EARNINGS_WINDOW_NOT_CHECKABLE`, 모두 금지 | **실제 차단 주체.** 구간은 발표 세션 index−2부터(사용자 표현 "2세션 전"과 같음), AFTER_CLOSE·시각 모름은 index+1까지, BEFORE_OPEN은 발표 세션까지 |
| C4 | `portfolio_exposure.py:871-892` `increase_blockers()` | `card_stock_core`(BE·MU·NBIS·DELL·AMD)의 늘리는 권고(add·new_buy_within_band·swap_buy_leg) 생략, MU가 금지면 DRAM 생략 | C3 결과를 그대로 씀 |
| C5 | `test_portfolio_exposure.py:413-450` | 옛 동작 고정(`blockers("MU", None) == ["EARNINGS_DATE_UNVERIFIED"]`, `blockers("DRAM", None)` 금지 등) | 고쳐야 함 |
| C6 | S5 확정안 R3(`loss-limit-review-s5-policy-proposal-2026-10-01.md:34`), 9절 S6 Judge 요구 7(`:574`) | "실적일 미확인은 금지 구간으로 본다" | 이력 문서. 본문은 두고 개정 메모만 추가 |
| C7 | `references/portfolio-exposure-review.md:26` R3 줄 | "an unverified earnings date is a blackout" | 운영 문서. 고쳐야 함 |
| C8 | `run_portfolio_exposure_review.py:464` `--earnings` 도움말 | `{"earnings": {"SYM": {"status": "VERIFIED", ...}}}` | 새 상태 형식 추가 |
| C9 | 통합 점검 지시문 v3.8(64·65줄), 카드 묶음 v1·v2, PWR·LITE 카드 | 이미 결정 1을 따름. 매수 요건 ① 칸에 "확인 필요" 표시가 있음 | 변경 없음 |

실제 영향:

- **지금까지:** 노출 점검은 1회(10/1 세션, `workspace/outputs/exposure-review/2026-10-01/portfolio-exposure-review.20261002T044548628715Z.json`). 줄이기 구간(MVLL·SOXL urgent reduce)이라 늘리는 권고 후보가 없었고 `omitted = []` → 옛 규칙이 실제로 막은 사례는 없다.
- **앞으로:** MVLL 매도 뒤 E가 내려가 늘리는 권고가 생기면, `--earnings` 입력이 없거나 VERIFIED가 아닌 종목은 모두 `EARNINGS_DATE_UNVERIFIED`로 빠진다. 10/2 확인 기준 5종목 모두 다음 실적일 미공지 → 전부 빠지고, MU 때문에 DRAM도 빠진다. 표시 전용이라 주문에는 영향이 없지만 매수 검토 화면에서 사라진다. → 10/15 이후 첫 신규 매수 검토 전에 적용해야 한다.
- PWR·LITE는 `card_stock_core` 밖이라 이 규칙보다 먼저 `NOT_AN_S5_NEW_BUY_INSTRUMENT`로 빠진다(상품 승인 문제, 범위 밖).

## 2. 개정 규칙 (R3 실적 금지 구간, 개정)

1. **공지된 실적일**(`VERIFIED`): 발표 세션 기준 2세션 전 정규장 세션부터 결과 뒤 첫 정규장 세션까지 개별 주식 신규 매수·추가 권고를 내지 않는다. 장 시작 전 발표면 발표 세션까지. 발표 시각을 모르면 장 마감 후로 본다. (동작 변화 없음)
2. **확인된 미공지**(`NOT_ANNOUNCED`): 다음 실적일이 공지되지 않았다는 사실만으로는 막지 않는다(결정 1). 아래 조건을 **모두** 채운 기록만 "확인된 미공지"다(허용 목록 방식):
   - `status == "NOT_ANNOUNCED"`(정확히 이 문자열. 다른 값은 모름으로 본다)
   - `source_kind` ∈ {`COMPANY_IR`, `COMPANY_PRESS_RELEASE`, `SEC_FILING`}
   - `source_url`이 `https://`로 시작
   - `checked_at`(UTC 오프셋이 있는 ISO 시각)이 평가 세션 날짜 16:00 America/New_York 이후이고, 점검 결과 생성 시각(`generated_at`)보다 늦지 않다. 조기 폐장일도 16:00을 쓴다(더 엄격한 쪽).
3. **확인 못 함 = 막기 유지**(D1): 기록 없음, `earnings` 입력 없음, 상태가 `VERIFIED`·`NOT_ANNOUNCED`가 아님, 2번 조건 중 하나라도 빠짐, 지난 실적일 기록만 있음(`EARNINGS_DATE_STALE`) → 금지로 두고 "실적일 확인 필요"로 표시한다.
4. 공지 날짜가 승인 달력 밖이거나 구간을 계산할 수 없으면 금지(`EARNINGS_WINDOW_NOT_CHECKABLE`, 유지).
5. MU가 1·3·4번으로 금지면 DRAM으로 대체하지 않는다(유지). MU가 확인된 미공지면 DRAM도 막지 않는다.
6. 금지 구간 밖은 매수 근거가 아니다(E1). 표시 전용·주문 권한 없음·수량 권한 없음(유지).

2번과 3번을 나누는 이유: 결정 1은 "공지되지 않았다"는 현실 상태에 대한 것이다. 확인 기록이 없다는 것은 그 상태를 모른다는 뜻이므로 CLAUDE.md "Missing or stale data stays visible and fails closed"를 따른다. 회사들은 발표 2주 이상 전에 날짜를 공지한 선례가 있다(Dell 약 2주 전, Bloom 22일 전 — 카드 묶음 5-1·5-2 다음 이벤트 칸). 그래서 평가 세션 마감 뒤 확인이면 다음 세션 판단에 충분하다고 본다(가설: 공지 뒤 2세션 안에 발표한 사례는 확인하지 않음 — Judge J4).

## 3. 정책 diff (`stock-strategy-system/alert_policy.json`, CRLF 유지, 다른 줄 바이트 무변경)

```diff
@@ holding_timing_rules.new_buy_activation (539줄, D2)
-      "earnings_blackout_single_stocks": "2 completed sessions before scheduled earnings through the first completed session after results"
+      "earnings_blackout_single_stocks": "from the second regular session before the announcement session through the first regular session after results (before-open results: through the announcement session; unknown timing: treated as after-close)"
@@ portfolio_exposure_policy (812~814줄)
     "earnings_blackout_ref": "holding_timing_rules.new_buy_activation.earnings_blackout_single_stocks",
-    "earnings_date_unverified": "treat_as_blackout",
+    "earnings_date_not_announced": "not_a_blackout_only_with_official_check_after_evaluation_session_close",
+    "earnings_check_missing_stale_or_unknown": "treat_as_blackout",
     "blackout_substitution_prohibited": {"MU": ["DRAM"]},
@@ portfolio_exposure_policy.policy_version
-    "policy_version": "2026-10-01-s5-r2",
+    "policy_version": "2026-10-03-s5-r2-p-earn",
```

- 바꾸지 않는 것: 최상위 `policy_version`·`strategy_version`(상태와 일치 요구), `deployment_gate` 해시, 다른 섹션·키, `workspace/policies/*`, `portfolio_state.json`.
- `portfolio_exposure_policy.policy_version` 문자열은 scripts·tests·schemas에서 참조 0건(grep, 10/03).

## 4. 코드·테스트·문서 변경 (Builder 범위, 승인 뒤)

| 파일 | 변경 |
|---|---|
| `scripts/portfolio_exposure.py` | `earnings_blackout()`에 2번 허용 조건 추가. 새 결과 코드: 통과 `EARNINGS_NOT_ANNOUNCED_CHECKED`, 오래된 확인 `EARNINGS_CHECK_STALE`, 출처·시각 형식 결함 `EARNINGS_CHECK_SOURCE_INVALID`, 미래 시각 `EARNINGS_CHECK_FUTURE_TIMESTAMP`. 기존 코드(`EARNINGS_DATE_UNVERIFIED`·`EARNINGS_DATE_STALE`·`EARNINGS_WINDOW_NOT_CHECKABLE`·`EARNINGS_BLACKOUT`·`OUTSIDE_EARNINGS_BLACKOUT`)와 VERIFIED 구간 계산은 그대로. 평가 세션·생성 시각을 넘기는 데 필요한 최소 인자만 추가. docstring 갱신 |
| `scripts/run_portfolio_exposure_review.py` | `--earnings` 도움말에 NOT_ANNOUNCED 형식 추가(동작 변경 없음) |
| `tests/test_portfolio_exposure.py` | 5절 사례 |
| `stock-strategy-system/alert_policy.json` | 3절 diff |
| `references/portfolio-exposure-review.md` | 26줄 R3 문구 + `--earnings` 입력 형식 몇 줄. 작업 트리의 미커밋 K0 9줄은 Builder 전에 사용자가 먼저 커밋 |
| `docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md` | 본문 유지, R3 아래 개정 메모 1줄("p-earn 개정: 확인된 미공지는 금지 구간 아님, 확인 못 함은 금지 유지. 이 문서 R3·9절 요구 7의 '미확인 = 금지'를 대체") |

`--earnings` 입력 형식(값은 형식 예시일 뿐 실제 날짜·주소 아님):

```json
{"earnings": {
  "MU":   {"status": "NOT_ANNOUNCED", "source_kind": "COMPANY_IR", "source_url": "https://<회사 IR 주소>", "checked_at": "<평가 세션 16:00 ET 이후 ISO 시각>"},
  "DELL": {"status": "VERIFIED", "announcement_session": "<공지된 발표 세션 YYYY-MM-DD>", "timing": "AFTER_CLOSE"}
}}
```

## 5. 테스트 사례 (Builder 필수)

1. NOT_ANNOUNCED + 조건 모두 충족 → `(False, "EARNINGS_NOT_ANNOUNCED_CHECKED")`. MU `blockers == []`, DRAM `blockers == []`.
2. `checked_at` = 평가 세션 15:59 ET → 금지(`EARNINGS_CHECK_STALE`). 16:00 ET 정각 → 통과(경계).
3. `checked_at` > `generated_at` → 금지(`EARNINGS_CHECK_FUTURE_TIMESTAMP`).
4. `checked_at` 오프셋 없음·파싱 불가, `source_kind` 목록 밖·빈 값, `source_url` 없음·`http://` → 금지(`EARNINGS_CHECK_SOURCE_INVALID`).
5. status `"not_announced"`(소문자)·`"TBD"`·`"UNVERIFIED"`, 키 없음, `earnings=None` → 금지(`EARNINGS_DATE_UNVERIFIED`). 이때 DRAM은 `BLACKOUT_SUBSTITUTION_PROHIBITED:MU`.
6. 기존 VERIFIED 구간 표(오프셋 3 통과, 2·1·0·−1 금지, BEFORE_OPEN 경계), `EARNINGS_DATE_STALE`, 달력 밖 `EARNINGS_WINDOW_NOT_CHECKABLE` — 기대값 그대로 통과.
7. 계약 테스트: 디스크의 `alert_policy.json` `portfolio_exposure_policy`에 새 두 키가 3절 값 그대로 있고 `earnings_date_unverified` 키가 없다.
8. 끝단 사례: MU ADD 카드(유효) + 확인된 미공지 → `omitted` 사유에 실적 관련 코드가 없다.

실행: 대상 파일 먼저 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_portfolio_exposure.py"`, 그다음 전체(서브에이전트, 기준 실패 수와 비교해 새 실패만 보고), `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`.

## 6. 진행 순서 (K3)

| 단계 | 누가·어디서 | 끝 기준 |
|---|---|---|
| 1 | 사용자: 이 문서와 Judge 지시문 커밋(Windows 터미널) | 커밋 해시 |
| 2 | Judge 1(수정안 심사): 별도 Claude Code 세션, worktree `judge-p-earn`, 파일 수정 없음 | "p-earn Judge 판정" PASS |
| 3 | 사용자 승인: Cowork 대화에 승인 문구 | 승인 기록(이 문서 9절) |
| 4 | Builder: Claude Code worktree `p-earn-impl`(그 전에 references 미커밋 9줄 커밋) | 대상 테스트 통과, 새 실패 0 |
| 5 | Judge 2(구현 심사): 별도 세션 | PASS |
| 6 | 사용자 병합(Windows 터미널), Cowork 읽기 전용 확인 | 병합 커밋 |

- 배포 영향: `alert_policy.json` 원시 바이트가 바뀌므로 예약 런타임 배포 때 provenance manifest를 다시 만든다(관제판 `p-deploy`와 같은 일, 급하지 않음). 이 저장소 병합만으로는 예약 런타임에 영향이 없다(`s7-builder-report-2026-10-01.md:189`).
- 수동 CA 영수증: `reviewed_receipt_sha256`가 비어 있어(`alert_policy.json:414`) 정책 해시 변경 영향 없음.

## 7. 범위 밖 · 발견

- **F1** `event_risk_policy.json` `approved_existing_rules[0].source_path`가 `timing_policy.watch_only_new_buy_activation.earnings_blackout_single_stocks`인데 실제 키는 `holding_timing_rules.new_buy_activation.earnings_blackout_single_stocks`다(옛 경로로 보임, 이 경로를 읽는 코드는 확인 안 함). 승인 정책(`workspace/policies`) 수정이라 별도 K3. 이번엔 기록만.
- **F2** 2027년 달력: 공지 날짜가 승인 달력(2026년) 밖이면 `EARNINGS_WINDOW_NOT_CHECKABLE`로 막힌다. 2027년 1~2월 발표 날짜가 공지되기 전(시점 확인 필요)에 2027 달력 연결이 필요하다. 별도 작업.
- **F3** `--earnings` 파일은 Cowork가 공식 출처를 보고 만든다. 자동 생성기는 만들지 않는다(필요하면 별도 K2).
- **F4** VERIFIED 기록에는 출처·확인 시각 요구가 없다(현행 유지). 맞출지는 나중 판단.

## 8. Judge 질문

- **J1** 결정 1 반영: 확인된 미공지만 통과하고 그 밖은 모두 금지인가.
- **J2** fail-open 점검(`references/development-change-review.md` "Fail-open patterns" 5종) — 특히 Missing evidence treated as permission, Stale treated as current, Unknown mapped to known, Deny-list gates.
- **J3** D2 문구가 현행 코드 구간(index−2 ~ index+1, BEFORE_OPEN은 index)과 동작상 같은가.
- **J4** "평가 세션 16:00 ET 이후 확인" 기준이 충분한가(공지 뒤 2세션 안 발표 위험).
- **J5** 범위: 권한·수량·다른 게이트·최상위 버전·`deployment_gate` 무변경, 고정(pinned) 스크립트 미포함.
- **J6** S5 확정안 본문을 두고 개정 메모만 붙이는 방식이 문서 충돌을 남기지 않는가.

## 9. 진행 기록

- 2026-10-03 Cowork: 영향 범위 확인, 사용자 선택 D1(막기 유지)·D2(문구 명확화 포함), 수정안·Judge 지시문(`p-earn-judge-prompt-2026-10-03.md`) 작성. Judge 미실행, 정책·코드 미변경.
