# p-earn 실적 금지 구간 개정안 (K3) — 2026-10-03, r1

- 관제판 작업: `p-earn`. 성격: K3(Production 의미). 상태: **완료(2026-10-03) — r1 사용자 승인, Builder, Judge 2 PASS, 병합 `7c68ec9`. 남은 후속은 7절 F1~F9**.
- 근거 결정: 2026-10-02 사용자 결정 1(`docs/claude/integrated-stock-cards-v1-2026-10-02.md` 8절 1번, "사용자 결정 (2026-10-02)" 절 — 미커밋, 읽은 시점 sha256 앞 16자 `11a3220a68501f5e`).
- 2026-10-03 사용자 선택: **D1** 확인하지 못한 경우는 막기 유지(fail-closed). **D2** 처음에는 금지 구간 영문 문구 명확화를 포함했으나, Judge 필수 수정 1 뒤 **이번 묶음에서 제외하고 S7 2단계로 이관**(안 (a)). `holding_timing_rules`는 건드리지 않는다.
- 기준값(2026-10-03 Cowork 확인, r0 대상 HEAD `25ec82bf1c72`, Judge 1 대상 `9f0912e` = r0 문서 2개 추가뿐):

| 파일 | git blob (HEAD) | raw sha256 앞 16자 | 작업 트리 |
|---|---|---|---|
| `stock-strategy-system/alert_policy.json` | `0a40505894935dbc05bd2b13fc4214f2cadc18d3` | `8e0965147600b85b` (CRLF 958줄, LF 단독 0) | HEAD와 같음 |
| `manage-us-stock-strategy/scripts/portfolio_exposure.py` | `87d2920c471bca205aa113334c3728e6f7e631f4` | `585803c220bfcf1d` | 같음 |
| `manage-us-stock-strategy/tests/test_portfolio_exposure.py` | `0b5cbfba49febd913820801622fe35c9868c91c6` | `3da8d3a35788bc60` | 같음 |
| `manage-us-stock-strategy/references/portfolio-exposure-review.md` | `9326aa60b0f6c76fa83c78c5f20888fb0f15a55a` | `0ea1429e2e60772b` | **수정됨**(미커밋 K0 9줄 "Token order", 165줄 아래) |
| `docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md` | `d8e436d885a7b5f42afc35723d1c69143668a2aa` | `4b1ebaddabd363f7` | 같음 |
| `workspace/policies/event_risk_policy.json` | `e94b42e2f19591a1069243d0d41cc9838107aa04` | `45a7e4e38f5accad` | 같음 |
| `docs/claude/integrated-stock-cards-v1-2026-10-02.md` | 없음(미추적) | `11a3220a68501f5e` | Builder 전 커밋 |
| `docs/claude/integrated-check-prompt-v3.8-draft-2026-10-03.txt` | 없음(미추적) | `a23a8a43494683ef` | Builder 전 커밋 |

## 결론 (먼저)

1. **확인된 "미공지"는 금지 구간이 아니다.** 공지된 실적일의 금지 구간(발표 세션 2세션 전 ~ 결과 뒤 첫 세션)은 그대로다.
2. **확인하지 못한 경우는 지금처럼 막는다**(기록 없음·오래된 확인·상태 모름·모순 기록·생성 시각 없음·지난 실적일 기록만 있음). 화면에는 "실적일 확인 필요"로 보인다(D1).
3. **정책 문구만 바꾸면 동작은 안 바뀐다.** 실제로 막는 주체는 `portfolio_exposure.py`의 `earnings_blackout()`이고 정책 키를 읽지 않는다. 그래서 정책 1구역(`portfolio_exposure_policy`) + 함수 1개 + 테스트 + 문서 2곳을 한 K3 묶음으로 바꾼다.
4. `holding_timing_rules`는 바꾸지 않는다 → 그림자 검증 의미 지문(`shadow_acceptance.py:223-229`)과 integrated shadow 코호트에 영향 없음.
5. 권한은 그대로다: 표시 전용, `order_authority=false`, `quantity_authority=none`. 금지 구간 밖이라는 사실은 매수 근거가 아니다(E1).

## 1. 현재 상태와 영향 범위

| # | 위치 | 현재 | 결정 1과 관계 |
|---|---|---|---|
| C1 | `alert_policy.json:813` `portfolio_exposure_policy.earnings_date_unverified` | `"treat_as_blackout"` | 충돌. 이 키를 읽는 코드는 없다(`git grep`, `*.py` 0건) — 문서 역할 |
| C2 | `alert_policy.json:539` `holding_timing_rules.new_buy_activation.earnings_blackout_single_stocks` (`:812` `earnings_blackout_ref`가 가리킴) | `"2 completed sessions before scheduled earnings through the first completed session after results"` | 충돌 없음. 시작 세션이 1세션 늦게도 읽힌다(카드 8절 10번). 읽는 코드 없음. **이번에 바꾸지 않음**(D2 → S7 2단계, 4절 F5) |
| C3 | `portfolio_exposure.py:759-785` `earnings_blackout()` | 기록 없음·`status != "VERIFIED"` → `EARNINGS_DATE_UNVERIFIED`, 지난 날짜 → `EARNINGS_DATE_STALE`, 달력 밖 → `EARNINGS_WINDOW_NOT_CHECKABLE`, 모두 금지 | **실제 차단 주체.** 구간은 발표 세션 index−2부터, BEFORE_OPEN은 발표 세션까지, 그 밖의 timing(없음 포함)은 index+1까지(Judge J3 확인) |
| C4 | `portfolio_exposure.py:871-892` `increase_blockers()`, 제안 경로 `:1293` | `card_stock_core`(BE·MU·NBIS·DELL·AMD)의 늘리는 권고(add·new_buy_within_band·swap_buy_leg)와 제안 생략, MU가 금지면 DRAM 생략 | C3 결과를 그대로 씀 |
| C5 | `test_portfolio_exposure.py:413-450` | 옛 동작 고정 | 고쳐야 함 |
| C6 | S5 확정안(`loss-limit-review-s5-policy-proposal-2026-10-01.md`) `:34` R3, `:397` 5절 diff `earnings_date_unverified`, `:574` 9절 S6 Judge 요구 7, `:579` 테스트 사례 "실적일 미확인" | "실적일 미확인은 금지 구간" | 이력 문서. 본문은 두고 r2 절 머리(`:10`)에 개정 메모 1줄로 네 곳을 모두 가리킨다 |
| C7 | `references/portfolio-exposure-review.md:26` R3 줄 | "an unverified earnings date is a blackout" | 운영 문서. 고쳐야 함 |
| C8 | `run_portfolio_exposure_review.py:464` `--earnings` 도움말, `:418` `generated_at` 생성 | `{"earnings": {"SYM": {"status": "VERIFIED", ...}}}` | 새 형식 추가, `generated_at`을 리뷰에 명시 인자로 넘김 |
| C9 | 통합 점검 지시문 v3.8(64·65줄), 카드 묶음 v1·v2, PWR·LITE 카드 | 이미 결정 1을 따름 | 이번 변경 없음(① 칸 확인 시각 조건은 F6 후속) |

실제 영향:

- **지금까지:** 노출 점검 출력은 10/1 세션 2개(`workspace/outputs/exposure-review/2026-10-01/` 04:27Z·04:45Z). 둘 다 줄이기 구간이라 `add`·`omitted`·`proposals`가 모두 빈 목록 → 옛 규칙이 실제로 막은 사례는 없다.
- **앞으로:** MVLL 매도 뒤 E가 내려가 늘리는 권고가 생기면, `--earnings` 입력이 없거나 VERIFIED가 아닌 종목은 모두 `EARNINGS_DATE_UNVERIFIED`로 빠진다. 10/2 확인 기준 5종목 모두 다음 실적일 미공지 → 전부 빠지고, MU 때문에 DRAM도 빠진다. 표시 전용이라 주문에는 영향이 없지만 매수 검토 화면에서 사라진다. → 10/15 이후 첫 신규 매수 검토 전에 적용해야 한다.
- PWR·LITE는 `card_stock_core` 밖이라 이 규칙보다 먼저 `NOT_AN_S5_NEW_BUY_INSTRUMENT`로 빠진다(상품 승인 문제, 범위 밖).

## 2. 개정 규칙 (R3 실적 금지 구간, 개정)

1. **공지된 실적일**(`VERIFIED`): 발표 세션 기준 2세션 전 정규장 세션부터 결과 뒤 첫 정규장 세션까지 개별 주식 신규 매수·추가 권고를 내지 않는다. 장 시작 전(BEFORE_OPEN) 발표면 발표 세션까지. 그 밖의 timing(없음·알 수 없는 값 포함)은 장 마감 후로 본다. (현행 코드와 같음, 동작 변화 없음)
2. **확인된 미공지**(`NOT_ANNOUNCED`): 다음 실적일이 공지되지 않았다는 사실만으로는 막지 않는다(결정 1). 아래 조건을 **모두** 채운 기록만 통과한다(허용 목록 방식). 점검 순서와 결과 코드:
   1. 세션 확인: `buy_session`과 평가 세션(`evaluation_session`, 명시 인자)이 있고 승인 달력 안에 있어야 한다. 아니면 `EARNINGS_WINDOW_NOT_CHECKABLE`(현행처럼 세션 확인을 먼저).
   2. 모순 없음: 기록에 `announcement_session` 또는 `timing` 키가 있으면 `EARNINGS_RECORD_CONTRADICTORY`.
   3. 출처: `source_kind` ∈ {`COMPANY_IR`, `COMPANY_PRESS_RELEASE`, `SEC_FILING`}, `source_url`이 문자열이고 `https://` 뒤에 호스트가 있음. 아니면 `EARNINGS_CHECK_SOURCE_INVALID`. `checked_at`이 문자열이 아니거나 파싱 불가·UTC 오프셋 없음도 같은 코드.
   4. 생성 시각: 리뷰 생성 시각 `generated_at`을 **명시 인자**로 받는다(모듈은 시계를 읽지 않는다). 없음·파싱 불가·오프셋 없음이면 `EARNINGS_CHECK_GENERATED_AT_INVALID`.
   5. 미래 시각: `checked_at > generated_at`이면 `EARNINGS_CHECK_FUTURE_TIMESTAMP`.
   6. 신선도: `checked_at`이 평가 세션 날짜 16:00 `ZoneInfo("America/New_York")`(EDT·EST 자동) 이전이면 `EARNINGS_CHECK_STALE`. 조기 폐장일도 16:00을 쓴다(더 엄격한 쪽).
   7. 모두 통과하면 `(False, "EARNINGS_NOT_ANNOUNCED_CHECKED")`.
   - `status`는 정확히 `"NOT_ANNOUNCED"`여야 한다. 다른 값은 3번으로 간다.
3. **확인 못 함 = 막기 유지**(D1): 기록 없음, `earnings` 입력 없음, 상태가 `VERIFIED`·`NOT_ANNOUNCED`가 아님 → `EARNINGS_DATE_UNVERIFIED`. 지난 실적일 기록만 있음 → `EARNINGS_DATE_STALE`. 2번의 어느 단계에서 걸려도 금지. 화면에는 "실적일 확인 필요".
4. 공지 날짜가 승인 달력 밖이거나 구간을 계산할 수 없으면 금지(`EARNINGS_WINDOW_NOT_CHECKABLE`, 유지).
5. MU가 1·3·4번(또는 2번의 단계)으로 금지면 DRAM으로 대체하지 않는다(유지). MU가 확인된 미공지면 DRAM도 막지 않는다.
6. 금지 구간 밖은 매수 근거가 아니다(E1). 표시 전용·주문 권한 없음·수량 권한 없음(유지).

2번과 3번을 나누는 이유: 결정 1은 "공지되지 않았다"는 현실 상태에 대한 것이다. 확인 기록이 없다는 것은 그 상태를 모른다는 뜻이므로 CLAUDE.md "Missing or stale data stays visible and fails closed"를 따른다.

**남는 위험(Judge J4, 확인 필요):** 확인한 뒤에 날짜가 공지되고 그 발표가 매수 세션부터 2세션 안이면 금지 구간 안의 매수 권고가 표시될 수 있다. 공지 리드타임 근거는 DELL 약 2주, BE 22일, AMD 27일(카드 묶음, 미커밋 문서라 Judge NOT VERIFIED), MU·NBIS는 근거 없음. 표시 전용이라 주문 영향은 없고, 사용자가 매수 전에 통합 점검의 실적일 공지 알림(v3.8 ⑥)을 함께 본다. 이 위험은 승인 때 수용 여부를 명시한다.

## 3. 정책 diff (`stock-strategy-system/alert_policy.json`, CRLF 유지, 다른 줄 바이트 무변경)

```diff
@@ portfolio_exposure_policy.policy_version (704줄만)
-    "policy_version": "2026-10-01-s5-r2",
+    "policy_version": "2026-10-03-s5-r2-p-earn",
@@ portfolio_exposure_policy (812~814줄)
     "earnings_blackout_ref": "holding_timing_rules.new_buy_activation.earnings_blackout_single_stocks",
-    "earnings_date_unverified": "treat_as_blackout",
+    "earnings_blackout_window_reading": "starts at the second regular session before the announcement session; ends at the first regular session after results (before-open: the announcement session); any other timing is treated as after-close",
+    "earnings_date_not_announced": "not_a_blackout_only_with_official_check_after_evaluation_session_close",
+    "earnings_check_missing_stale_or_unknown": "treat_as_blackout",
     "blackout_substitution_prohibited": {"MU": ["DRAM"]},
```

- 바꾸지 않는 것: `holding_timing_rules` 전체(539줄 포함 — 그림자 의미 지문 대상), `holding_risk_rules`, 최상위 `policy_version`(`:4`)·`strategy_version`(상태와 일치 요구), `portfolio_review_lines.policy_version`(`:834`, 같은 문자열이지만 그대로), 권한 필드(`:709-711`), `deployment_gate`(`:30-51`), 다른 섹션·키, `workspace/policies/*`, `portfolio_state.json`, `workspace/state/*`.
- `portfolio_exposure_policy.policy_version` 문자열은 scripts·tests·schemas에서 참조 0건(grep, 10/03).
- `earnings_blackout_window_reading`은 539줄의 모호함(카드 8절 10번)을 지문 밖에서 풀어 적는 읽기 규칙이다. 539줄 문구 자체의 수정은 S7 2단계(F5).

## 4. 코드·테스트·문서 변경 (Builder 범위, 승인 뒤)

| 파일 | 변경 |
|---|---|
| `scripts/portfolio_exposure.py` | `earnings_blackout()`에 2절 2번 단계를 그 순서대로 추가. `generated_at`은 명시 인자(`build_exposure_review` → `increase_blockers` → `earnings_blackout`, 제안 경로 `:1293` 포함). 기존 코드(`EARNINGS_DATE_UNVERIFIED`·`EARNINGS_DATE_STALE`·`EARNINGS_WINDOW_NOT_CHECKABLE`·`EARNINGS_BLACKOUT`·`OUTSIDE_EARNINGS_BLACKOUT`)와 VERIFIED 구간 계산은 그대로. 파싱 예외는 넓은 except로 삼키지 말고 해당 금지 코드로 보낸다. docstring 갱신 |
| `scripts/run_portfolio_exposure_review.py` | `:418`에서 만든 `generated_at`을 `build_exposure_review`에 넘김, `--earnings` 도움말에 NOT_ANNOUNCED 형식 추가 |
| `tests/test_portfolio_exposure.py` | 5절 사례 |
| `stock-strategy-system/alert_policy.json` | 3절 diff |
| `references/portfolio-exposure-review.md` | 26줄 R3 문구, `--earnings` 입력 형식, 구간 읽기 규칙. 작업 트리의 미커밋 K0 9줄은 Builder 전에 사용자가 먼저 커밋 |
| `docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md` | 본문 유지. r2 절 머리(`:10`) 아래 개정 메모 1줄: "p-earn 개정(날짜): 확인된 미공지는 금지 구간 아님, 확인 못 함은 금지 유지. `:34`·`:397`·`:574`·`:579`의 '실적일 미확인 = 금지'를 대체 — `docs/claude/p-earn-earnings-blackout-amendment-2026-10-03.md`" |

`--earnings` 입력 형식(값은 형식 예시일 뿐 실제 날짜·주소 아님):

```json
{"earnings": {
  "MU":   {"status": "NOT_ANNOUNCED", "source_kind": "COMPANY_IR", "source_url": "https://<회사 IR 주소>", "checked_at": "<평가 세션 16:00 ET 이후, 오프셋 있는 ISO 시각>"},
  "DELL": {"status": "VERIFIED", "announcement_session": "<공지된 발표 세션 YYYY-MM-DD>", "timing": "AFTER_CLOSE"}
}}
```

## 5. 테스트 사례 (Builder 필수)

1. NOT_ANNOUNCED + 조건 모두 충족 → `(False, "EARNINGS_NOT_ANNOUNCED_CHECKED")`. MU `blockers == []`, DRAM `blockers == []`.
2. 16:00 경계, 두 계절 모두:
   - EDT 평가 세션(기존 EVAL 2026-09-30): 15:59 EDT(19:59Z) → `EARNINGS_CHECK_STALE`, 16:00 EDT(20:00Z) → 통과.
   - EST 평가 세션(2026-11-02 이후 정규장 세션, 달력에서 고름): 15:59 EST(20:59Z) → `EARNINGS_CHECK_STALE`, 16:00 EST(21:00Z) → 통과. 고정 오프셋(−04:00) 구현은 이 사례에서 실패해야 한다.
3. `checked_at > generated_at` → `EARNINGS_CHECK_FUTURE_TIMESTAMP`.
4. `generated_at` 없음·`None`·파싱 불가·오프셋 없음 → `EARNINGS_CHECK_GENERATED_AT_INVALID`.
5. `checked_at` 오프셋 없음·파싱 불가·숫자·`null`, `source_kind` 목록 밖·빈 값, `source_url` 없음·`http://`·호스트 없는 `"https://"` → `EARNINGS_CHECK_SOURCE_INVALID`(예외가 새지 않는다).
6. NOT_ANNOUNCED에 `announcement_session` 또는 `timing` 키 → `EARNINGS_RECORD_CONTRADICTORY`.
7. NOT_ANNOUNCED인데 `buy_session` 또는 `evaluation_session` 없음·달력 밖 → `EARNINGS_WINDOW_NOT_CHECKABLE`.
8. status `"not_announced"`(소문자)·`"TBD"`·`"UNVERIFIED"`, 키 없음, `earnings=None` → `EARNINGS_DATE_UNVERIFIED`. 이때 DRAM은 `BLACKOUT_SUBSTITUTION_PROHIBITED:MU`.
9. 기존 VERIFIED 구간 표(오프셋 3 통과, 2·1·0·−1 금지, BEFORE_OPEN 경계), `EARNINGS_DATE_STALE`, 달력 밖 `EARNINGS_WINDOW_NOT_CHECKABLE` — 기대값 그대로. 추가: VERIFIED `timing` 없음·알 수 없는 값은 AFTER_CLOSE와 같은 끝 세션.
10. 계약 테스트(디스크의 `alert_policy.json`): `portfolio_exposure_policy`에 새 세 키가 3절 값 그대로, `earnings_date_unverified` 없음, `portfolio_exposure_policy.policy_version` = `2026-10-03-s5-r2-p-earn`, `portfolio_review_lines.policy_version` = `2026-10-01-s5-r2` 그대로.
11. 끝단 사례: MU ADD 카드(유효) + 확인된 미공지 → add 경로 `omitted` 사유에 실적 코드 없음. 제안 경로(`:1293`, `new_buy_within_band` MU) 통과 사례와 `EARNINGS_CHECK_STALE` 사례.
12. 지문 불변: Builder 변경 전후 `shadow_acceptance.semantic_fingerprint(ROOT)`가 같다. `test_v2_6_7_session_aware_kiwoom_priority.py`(특히 `:505-515`)가 통과한다.

실행: 대상 파일 먼저 `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_portfolio_exposure.py"`와 `-p "test_v2_6_7_session_aware_kiwoom_priority.py"`, 그다음 전체(서브에이전트, 기준 실패 수와 비교해 새 실패만 보고), `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`.

## 6. 진행 순서 (K3)

| 단계 | 누가·어디서 | 끝 기준 | 상태 |
|---|---|---|---|
| 1 | 사용자: r0 문서 커밋 | `9f0912e` | 완료 |
| 2 | Judge 1(수정안 심사), worktree `judge-p-earn` | CONDITIONAL_PASS | 완료, 필수 수정 6건 r1 반영 |
| 3 | 사용자 승인: Cowork 대화에 승인 문구 | 9절 기록 | 완료 |
| 4 | 사용자 커밋(r1, 근거 문서 2개, references K0 9줄, Builder 지시문) → Builder: Claude Code worktree `p-earn-impl`(`p-earn-builder-prompt-2026-10-03.md`) | 대상 테스트 통과, 새 실패 0, 지문 불변 | 완료(새 실패 0) |
| 5 | Judge 2(구현 심사): 별도 세션(`p-earn-judge2-prompt-2026-10-03.md`) | PASS | 완료 PASS, 필수 수정 없음 |
| 6 | 사용자 커밋·병합(Windows 터미널), Cowork 읽기 전용 확인 | 병합 커밋 | 완료: 커밋 `40949cf`, 병합 `7c68ec9` |

- 배포 영향: `alert_policy.json` 원시 바이트가 바뀌므로 예약 런타임 배포 때 provenance manifest를 다시 만든다(관제판 `p-deploy`와 같은 일, 급하지 않음). 이 저장소 병합만으로는 예약 런타임에 영향이 없다(`s7-builder-report-2026-10-01.md:189`).
- 그림자 검증: `holding_timing_rules`·`holding_risk_rules`·`strategy_version`·권한 필드를 건드리지 않으므로 의미 지문과 integrated shadow 코호트(`628c6081…`)는 그대로다. 코호트 이전은 하지 않는다.
- 수동 CA 영수증: `reviewed_receipt_sha256`가 비어 있어(`alert_policy.json:414`) 정책 해시 변경 영향 없음.

## 7. 범위 밖 · 발견 · 후속

- **F1** `event_risk_policy.json` `approved_existing_rules[0].source_path`가 `timing_policy.watch_only_new_buy_activation.earnings_blackout_single_stocks`인데 실제 키는 `holding_timing_rules.new_buy_activation.earnings_blackout_single_stocks`다(옛 경로로 보임, 이 경로를 읽는 코드는 확인 안 함). 승인 정책 수정이라 별도 K3. 기록만.
- **F2** 2027년 달력: 공지 날짜가 승인 달력(2026년) 밖이면 `EARNINGS_WINDOW_NOT_CHECKABLE`로 막힌다. 2027년 1~2월 발표 날짜가 공지되기 전(시점 확인 필요)에 2027 달력 연결이 필요하다. 별도 작업.
- **F3** `--earnings` 파일은 Cowork가 공식 출처를 보고 만든다. 자동 생성기는 만들지 않는다(필요하면 별도 K2).
- **F4** VERIFIED 기록에는 출처·확인 시각 요구가 없다(현행 유지). 일정 변경 위험이 있어 후속 판단.
- **F5** D2(539줄 영문 문구 명확화)는 S7 2단계(`p-s7-p2`)로 이관. 그 단계가 `holding_timing_rules`·`holding_risk_rules`를 바꾸며 integrated shadow 코호트 이전(`migrate_integrated_shadow_cohort.py`, `workspace/state/integrated_shadow/*`)을 어차피 해야 하므로 그때 함께 한다.
- **F6** 통합 점검 v3.8 ① 칸(64줄)은 확인 시각 조건이 없다. 결정론 결과가 `EARNINGS_CHECK_*`·`EARNINGS_RECORD_CONTRADICTORY`면 "확인 필요"로 맞추는 문구 변경(K1)은 다음 지시문 개정 때.
- **F7** J4 근거 보강: MU·NBIS 공지 리드타임을 공식 출처로 기록(다음 카드 갱신 때).
- **F8** (Judge 2 K3) NOT_ANNOUNCED 기록의 모르는 키(예: 오타 `announcement_date`, `Timing`)는 무시되고 통과할 수 있다. 허용 키 목록(`status`·`source_kind`·`source_url`·`checked_at`) 도입은 r1 2-2 문언 변경(K3)이라 S7 2단계에 묶는다(사용자 결정 10/3). 그때까지 Cowork는 `--earnings` 기록에 이 4개 키만 쓴다.
- **F9** (Judge 2 권고) references 새 절 K0 문구 2곳(`EARNINGS_DATE_STALE` 설명, "실적일 확인 필요" 화면 매핑 없음)과 Builder 보고 머리의 브랜치 표기는 병합 뒤 Cowork가 K0로 고친다. 정기 실행에서 `--now`를 쓰지 않는다.

## 8. Judge 질문과 Judge 1 결과

- 질문: **J1** 결정 1 반영 · **J2** fail-open(`references/development-change-review.md` "Fail-open patterns" 6종, Swallowed errors 포함) · **J3** 구간 동작(r1에서는 539줄 미변경, 새 읽기 규칙 키가 코드와 같은지) · **J4** 16:00 ET 기준 충분성 · **J5** 범위·지문·고정 스크립트 · **J6** 이력 문서 메모 방식.
- **Judge 1(대상 `9f0912e`, 2026-10-03): CONDITIONAL_PASS.** J1 PASS, J2 조건부, J3 PASS, J4 확인 필요, J5 조건부, J6 조건부.
  - 필수 수정 반영(r1): ① D2 제외·S7 2단계 이관(사용자 선택 (a)) → 결론 4, 3절, 6절, F5 ② `policy_version` diff를 `:704`로 한정, `:834` 무변경, 계약 테스트 → 3절, 5절 10번 ③ `generated_at` 명시 인자·없으면 금지·코드 → 2절 2-4, 4절, 5절 4번 ④ `ZoneInfo("America/New_York")`, EST 경계 → 2절 2-6, 5절 2번 ⑤ 모순 기록 금지 → 2절 2-2, 5절 6번 ⑥ S5 메모가 `:34`·`:397`·`:574`·`:579`를 모두 가리킴(`:10` 한 번) → 1절 C6, 4절.
  - 권고 반영: 매수 세션 먼저 확인(2절 2-1, 5절 7번), 형식 결함 사례 추가(5절 5번), VERIFIED timing 사례(5절 9번), 제안 경로 사례(5절 11번), 근거 문서 커밋·해시(기준표), 출력 2개로 정정(1절), F6·F7.

## 9. 진행 기록

- 2026-10-03 Cowork: 영향 범위 확인, 사용자 선택 D1(막기 유지)·D2(문구 명확화 포함), 수정안 r0·Judge 지시문 작성 → 사용자 커밋 `9f0912e`.
- 2026-10-03 Judge 1: CONDITIONAL_PASS(필수 수정 6건).
- 2026-10-03 Cowork: 필수 수정 1에 사용자 선택 (a) — D2 제외, S7 2단계 이관. 필수 수정 6건·권고 반영해 r1 작성.
- 2026-10-03 사용자 승인(Cowork 대화, 원문): "p-earn r1 승인: 확인된 미공지는 금지 구간 아님, 확인 못 함은 금지 유지, D2는 S7 2단계로 이관, J4 남은 위험(표시 전용) 수용". 이 승인은 r1(이 문서) 3·4절 범위의 정책·코드·테스트·문서 변경에만 해당한다. Cowork: Builder 지시문 `p-earn-builder-prompt-2026-10-03.md` 작성.
- 2026-10-03 Builder(worktree `p-earn-impl`, HEAD `906f765`): 커밋 전 변경 7개 + 보고, 새 실패 0. Cowork 읽기 전용 확인 통과.
- 2026-10-03 Judge 2: PASS(필수 수정 없음). K3(모르는 키 무시)는 사용자 결정 "지금 병합, S7 2단계에 묶기"(F8). 커밋·병합 대기.
- 2026-10-03 사용자 커밋 `40949cf`, 병합 `7c68ec9`. Cowork 확인(읽기 전용, VM Python 3.10): 병합된 8개 파일의 LF 정규화 해시가 Judge 2 기준과 같음, CRLF·bare LF 0, 노출 관련 대상 테스트 7개 파일 OK, `test_v2_6_7` 실패 목록이 병합 전과 같음, 의미 지문 `628c6081…` 불변. F9 K0 정정 3곳(references 2곳, Builder 보고 브랜치 표기) 반영 — 커밋 대기.
