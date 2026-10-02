# S7 U3 거래내역 증거 보정 Builder 보고 (2026-10-02, K2)

- 지시문: `docs/claude/s7-u3-cash-flow-evidence-builder-prompt-2026-10-02.md` 3절.
- worktree `s7-cashflow`, 기준 HEAD `dcc17e9`(지시문 커밋). 커밋하지 않았다.
- 키움 도구·네트워크·비밀 파일은 쓰지 않았다. 정책·상태·원장·journal은 건드리지 않았다.

## 1. 바꾼 파일

| 파일 | 변경 |
|---|---|
| `scripts/cash_flow_evidence.py` | 빈 응답 분기 `_is_no_data_response`(R1), `NON_EXTERNAL_CLASSES`에 `CORPORATE_ACTION`(R3), 상수 2개, 머리 설명 3줄 |
| `schemas/kiwoom-cash-flow-evidence.schema.json` | `classification` enum에 `CORPORATE_ACTION`만 추가 |
| `assets/kiwoom-transaction-history-classification.json` | 규칙 1개(FEE_TAX_INTEREST 다음, FX 앞), purpose·status 문구 |
| `references/portfolio-exposure-review.md` | R6 절 2번 항목 뒤 두 줄(K0) |
| `tests/test_cash_flow_evidence_u3.py` (새 파일) | 18개 테스트 |
| `docs/claude/s7-u3-cash-flow-evidence-builder-report-2026-10-02.md` (새 파일) | 이 보고 |

`git diff --stat`(추적 파일 4개): 40 insertions, 10 deletions.
`cash_flow_evidence.py` 35줄, 낱말표 9줄, 참고 문서 4줄, 스키마 1줄. 새 테스트 파일은 추적 전이라 stat에 안 나온다(272줄).

### 구현 요약
- 응답 본문(감싼 경우 `result` 안)이 dict이고 `return_code`가 정수 20(bool·float·문자열 제외)이며 `return_msg`가 문자열로 `"501724:"`를 포함할 때만 "행 0개"로 받는다.
  - `result_list`가 없거나 빈 list여야 한다. 행이 있으면 `CASH_FLOW_EVIDENCE_EMPTY_RESPONSE_HAS_ROWS`, list가 아니면 `RAW_SHAPE_INVALID`.
  - 기간 검사는 이 분기보다 앞에 있어 빈 응답에도 똑같이 적용된다.
  - 그 밖의 응답은 기존 검사(`result_list` 형태 → `return_code != 0`)를 순서·오류 코드 그대로 지난다.
- 낱말표 규칙: `{"classification": "CORPORATE_ACTION", "fields": ["deal_kind_nm", "rmrk_nm"], "match_any": ["액면", "단주대금"]}`. 다른 규칙·`rule_order`는 그대로다.
- `classify_row` 흐름과 합계 계산은 바꾸지 않았다. `CORPORATE_ACTION` 행은 `signed_amount_usd`가 None이고 어떤 합계에도 새로 들어가지 않는다.
- 외부 흐름 판정(DEPOSIT·WITHDRAWAL·FX만 외부)과 `cash-flow-declaration.schema.json`은 그대로다.

## 2. 원시 sha256 전후

| 파일(manage-us-stock-strategy/ 기준) | 전 | 후 |
|---|---|---|
| scripts/cash_flow_evidence.py | `eb0e1db283264c2c4a1f482268255ed4d2fccd9fb6ef4b89896d807046571e4d` | `9765a75df33ad19ce86ef16538cf4e201b517741cf8e237c611221f1f18c2bd9` |
| schemas/kiwoom-cash-flow-evidence.schema.json | `6f37ac88c5501aa66ccca62689b35d0fa42a0f0ef0f19cf4d3fdf001129b188a` | `9772c90c077a5520ee1efc364016580ce2f8d5843354450e4558e139521a8d3e` |
| assets/kiwoom-transaction-history-classification.json | `db2d63559ce0381a49e60861a634c04c5820c3a5829ac726aa697929d73cac03` | `d6ef55bee9379bafe08291213bfb1b4f866865a2b3018ffee876a062220d03dc` |
| references/portfolio-exposure-review.md | `f36c2390d93989f48dd952f75eb3da46d458bc5c7f9978057925daf2f4a2b2ba` | `141e612405aca0716fe548ab5cc1b09d202390347b253bfa3ba11d1b0ed4e87d` |
| tests/test_cash_flow_evidence_u3.py (새) | — | `64767e2a995f8f2208bf1e980224bdf20249b67e2173d35a893a664496174295` |

## 3. 줄바꿈

바이트 검사 결과 다섯 파일 모두 전체 CRLF, bare LF 0, BOM 없음이다(`cash_flow_evidence.py` 460/460, 스키마 78/78, 낱말표 49/49, 참고 문서 284/284, 새 테스트 272/272). 일괄 변환은 하지 않았다. 편집은 바이트 단위 치환으로 했고, 새 테스트 파일만 LF 원본을 CRLF로 만들었다.

## 4. 낱말표 canonical hash 전후

| | `canonical_hash(table)` |
|---|---|
| 전 | `c176f347ab69b12bf6e03e9ecbfbf26ca71a10e3d16ff6dc37aefee395193b89` |
| 후 | `ea2c156bc054e6b005dc3f2a12d6044ba72025ad32b54769f7b2c3b3ab9ee95d` |

증거의 `classification_table_sha256`이 이 값으로 바뀐다. 이미 만들어 둔 증거 파일이 있다면 그 해시는 옛 낱말표를 가리키므로 새 표로 다시 정규화해야 같은 해시가 된다.

## 5. 테스트 결과

- **수정 전**: 새 테스트 파일 18개 중 실패 18건 세부(실패 9 + 오류 9, subTest 포함)가 나왔다. 회귀 단언(T5 일부, 환전·이체·타사대체)은 수정 전에도 통과했고, 새 동작을 요구하는 단언이 실패했다.
- **수정 후 대상 테스트**(파일별 `-p`):

| 파일 | 결과 |
|---|---|
| test_cash_flow_evidence_u3.py | 18 OK |
| test_cash_flow_evidence.py | 19 OK |
| test_portfolio_exposure_judge_fixes.py | 29 OK |
| test_portfolio_exposure_fail_closed.py | 32 OK |
| test_reconcile_broker_state.py | 56 OK |
| test_run_portfolio_exposure_review.py | 22 OK |

- **스키마 감사** `validate_schema_contracts.py`: PASS, errors [].
- **전체 테스트**(서브에이전트, 전 후 각 1회):
  - 기준선 2275건: 실패 23, 오류 291, 건너뜀 1 (314 ID).
  - 수정 후 2293건(새 테스트 18 증가): 실패 23, 오류 291, 건너뜀 1 (314 ID).
  - 두 ID 목록은 정렬 후 `diff`로 동일. **새 실패 0**, 해결된 ID도 0.
  - 신규·변경 모듈(`cash_flow_evidence`)은 실패 목록에 없다.

### 새 테스트 내용(T1~T7)
- T1: 실측 문자열 7종 분류 및 낱말표 순서·문구·status.
- T2: 7행 증거는 unresolved [], external_net "0.00", 신고 `NO_EXTERNAL_FLOW`. `CORPORATE_ACTION` 금액은 어떤 합계에도 안 들어감.
- T3: 빈 응답 4가지 모양(감싼/안 감싼, `result_list` 없음/빈 list). 결과가 스키마를 통과하고 감싼 것과 안 감싼 것의 증거가 동일하며 `acnt_print` 없음.
- T4: 실패 유지 18가지(501058, 메시지 없는 20, 다른 메시지, 콜론 없는 501724, 문자열·float·bool 코드, 0인데 목록 없음, 행이 있는 501724, 기간 오류 등).
- T5: 타사대체입고·출고 UNCLASSIFIED, 이체입금 DEPOSIT, 환전매수 FX, 수수료출금 FEE_TAX_INTEREST 유지.
- T6: 빈 증거 신고 블록으로 `cash_flow_chain` CLEAR, adjustments 없음, covered_through = period_to. 연속 두 기간 CLEAR, 사이에 틈이 있으면 `CASH_FLOW_COVERAGE_GAP` HOLD.
- T7: normalize CLI는 빈 원문에서 종료 코드 0, `row_count` 0, 결과 파일이 스키마를 통과한다. 501058 원문은 종료 코드 2.

## 6. 남은 문제·메모

- 501058(1년 초과)처럼 `result_list`가 없는 오류는 지금처럼 `RAW_SHAPE_INVALID`로 멈춘다(`result_list` 검사가 `return_code` 검사보다 앞이라서). 지시문이 이 순서를 바꾸지 말라고 했으므로 그대로 두었고, 테스트가 이 코드 이름을 못 박는다.
- 기준선의 314개 실패는 이 worktree 환경 문제다. 서브에이전트 보고로는 `IntegratedAuthorityLoadError: INTEGRITY_FAILURE`와, worktree에 없는 `workspace/outputs/activation/nbis-v2-shadow/20260814-v4/activation-receipt.json`의 `FileNotFoundError`가 대부분이다. 23개 FAIL 항목은 개별로 보지 않았고 이번 변경과 무관하다는 것은 ID 목록 동일성으로만 확인했다. 원본 폴더에서 같은 전체 테스트를 돌려 보는 것이 좋다.
- 다시 확인할 것(범위 밖): 실제 입금·출금·환전 문자열, 빈 기간일 때 키움 CLI의 종료 코드와 stdout 형태, 연속조회 완전성(U4).
- 커밋하지 않았다.
