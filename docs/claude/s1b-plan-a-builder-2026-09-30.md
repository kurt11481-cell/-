# S1b 안 A Builder 기록 — 계좌 브리지 오류 관측 표식

- 날짜: 2026-09-30
- 등급: K2 (관측 추가, 게이트 불변)
- 설계: `docs/claude/open-orders-diagnosis-2026-09-30.md` §5-1, 결정 기록 `preflight-fail-fix-design-2026-09-30.md` §7-1(다른 worktree, 미커밋)
- 세션: worktree `s1b-plan-a`, 브랜치 `worktree-s1b-plan-a`, 기준 HEAD `b76d5e7`(I0 병합 `5c02146` 포함, 시작 시 확인)
- 상태: **미커밋.** 사용자 승인 뒤 커밋한다.

## 1. 한 줄 요약

계좌 브리지 오류 결과에 `provider_return_code`(int 또는 None)와 `no_data_declared`(bool)만 추가했다. `bridge_status`, `failure_type`, 모든 게이트, preflight 판정은 그대로다. `return_msg` 원문은 어디에도 저장·출력하지 않는다.

## 2. 표식 규칙

| 필드 | 값 |
|---|---|
| `provider_return_code` | 공급자 `return_code`가 `type is int`(bool 제외)이고 상태가 `KIWOOM_API_RESPONSE_ERROR`일 때만 그 값. 그 밖에는 `None` |
| `no_data_declared` | `return_code == 20`(int) **이고** `return_msg`가 문자열이며 `"[2000]"`로 시작할 때만 `true`. 그 밖에는 `false` |

- 표식은 **실패 결과에만** 붙는다. `PASS`/`PARTIAL` 결과에는 필드가 없다.
- `return_msg`는 `_fetch_account_page` 안에서 두 값을 계산한 뒤 버린다. 예외 객체·worker stdout·결과 어디에도 넣지 않는다.
- 부모 쪽 `_sanitize`는 worker 출력을 신뢰하지 않는다. 코드는 int이고 상태가 `KIWOOM_API_RESPONSE_ERROR`일 때만 유지하고, `no_data_declared`는 코드가 20일 때만 `true`를 인정한다.
- 연산 제한은 두지 않았다(지시문 그대로). 공급자가 다른 연산에서 20 + `[2000]`을 내면 그것도 `true`가 된다. 관측 표식이라 게이트에는 쓰이지 않는다.

## 3. 변경 파일 (고정 파일 없음)

| 파일 | 변경 |
|---|---|
| `manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py` | 상수 2개, `_provider_marks`, `_exception_provider_marks`, `_fetch_account_page`가 `BridgeError` 인스턴스에 두 값만 붙임(`BridgeError`는 고정 파일 8번에 있어 수정하지 않음), worker 실패 dict에 두 필드, `_sanitize`의 실패 분기에서 재검증 |
| `manage-us-stock-strategy/scripts/broker_visibility_audit.py` | `_visibility`의 UNKNOWN 항목에 두 필드 추가. 상태는 계속 `UNKNOWN`, `empty_result_interpreted_as_none=false` |
| `manage-us-stock-strategy/schemas/kiwoom-broker-visibility-audit.schema.json` | 5개 visibility 객체에 `provider_return_code`(integer/null), `no_data_declared`(boolean) 타입 명시. 검증기가 `if/then`을 지원하지 않아 "true이면 코드 20" 규칙은 코드와 테스트로 지킨다 |
| `manage-us-stock-strategy/tests/test_s1b_provider_marks.py` (신규, 20건) | 아래 §5 |

- 줄바꿈: 수정한 3개 파일은 CRLF를 그대로 유지했다(파일별 lone LF 0개 확인, diff가 변경 줄에 한정됨). 신규 파일 2개(테스트, 이 문서)는 LF다.
- 수정하지 않은 것: `run_manual_portfolio_analysis.py`, 고정 파일 16개, `kiwoom_broker_shadow.py`, `portfolio_decision_dashboard.py`, 정책·상태 파일.

## 4. 표식이 흐르는 경로 (확인 결과)

1. `_fetch_account_page`: 0이 아닌 `return_code`에서 `BridgeError`를 던질 때 두 값을 붙인다. 이 상태는 재시도 대상이 아니다(`API_RESPONSE_ERROR`는 retryable 목록에 없다).
2. `external_worker`의 실패 dict에 두 필드가 실린다.
3. `invoke_account_bridge_batch` → `_sanitize`: 허용 목록에 두 필드를 추가하고 재검증한다. 상태가 `PASS`/`PARTIAL`이거나 행 검사로 `KIWOOM_SCHEMA_MISMATCH`로 내려가면 표식은 없거나 `None/false`다.
4. `run_manual_portfolio_analysis._normalize_broker_state`(rmpa:336)가 `_sanitize`를 다시 호출한다. 그래서 `broker_observed_state.open_order_evidence`에 두 필드가 자동으로 나타난다(rmpa 수정 없음). 이 경로에는 **미체결 표식만** 나온다. 실현손익 표식은 수동 분석 보고서에 들어가지 않는다.
5. 수동 분석 스키마: `broker_observed_state`는 `additionalProperties: true`이고 `open_order_evidence`에는 제약이 없다. 스키마 수정이 필요 없다. 대시보드(dashboard:947)는 지정한 키만 읽는다.
6. `kiwoom_broker_shadow.normalize_snapshot`은 고정된 키만 만들고 `operation_statuses`만 옮긴다. 표식은 스냅샷·제안·reconcile 파일에 들어가지 않는다. 테스트로 `scope_complete=false`가 그대로인지 확인했다.
7. `broker_visibility_audit`: 미체결·체결·실현손익 등 5개 visibility의 UNKNOWN 항목에 표식이 나온다(`run_broker_visibility_audit.py`가 만드는 `future_execution_broker_visibility.json`).

## 5. 테스트

새 파일 `test_s1b_provider_marks.py`(20건, 구현 전에 실패하는 것을 먼저 확인했다):

- **양성:** 20 + `[2000]…`로 미체결(`account_open_items`)과 실현손익(`account_realized_pnl_read`) 모두 `provider_return_code=20`, `no_data_declared=true`. 상태는 `KIWOOM_API_RESPONSE_ERROR`, `failure_type=API_RESPONSE_ERROR`, `data=[]`, `retrieved_at=None`.
- **음성(12종 e2e + 18종 단위):** 메시지 없는 20, 메시지 `None`, 다른 접두(`[2001]`), 접두가 앞에 없음, 메시지가 문자열 아님, 문자열 `"20"`, bool `True`/`False`, float `20.0`, 다른 코드(21, -1), 코드 없음. 코드 0(int/`"0"`)은 성공이라 표식 없음.
- **원문 미저장:** 합성 marker와 합성 계좌 숫자(`5012345678`)가 worker 출력·부모 결과 어디에도 없다. `return_msg`, `[2000]` 문자열도 없다.
- **`_sanitize` 불신:** worker가 위조한 표식(코드 없음/0/19/21/문자열/bool/float/dict, 상태가 오류가 아닌 경우, PASS/PARTIAL, 행 오류로 강등된 경우)은 버려지거나 `None/false`가 된다. 추가 필드(`return_msg`, `message`, `account_number`)는 계속 버려진다.
- **게이트 불변:** `_normalize_broker_state` 결과에서 미체결 증거는 `KIWOOM_API_RESPONSE_ERROR`, `scope_complete=false`. 대시보드 `_sell_readiness_evidence`는 `OPEN_ORDER_EVIDENCE_NOT_VERIFIED`, `open_order_conflict_status=NOT_VERIFIED`. shadow 스냅샷은 `scope_complete=false`이고 표식·marker가 없다.
- **audit:** 표식이 보여도 `UNKNOWN`, `NOT_READY` 유지. 위조·잘못된 타입은 `None/false`. 스키마가 잘못된 타입을 거부한다.

기존 테스트는 수정하지 않았고 그대로 통과했다: `test_return_code_twenty_is_still_error`, `test_return_code_twenty_remains_api_response_error_offline`, `test_failure_results_discard_untrusted_metadata_and_account_values`.

## 6. 실행 결과

대상 테스트(이 worktree):

| 파일 | 결과 |
|---|---|
| `test_s1b_provider_marks` (신규) | 20건 OK |
| `test_k2_bridge_evidence_integrity` | 17건 OK |
| `test_kiwoom_broker_shadow` | 24건 OK |
| `test_reconcile_broker_state` | 56건 OK |
| `test_broker_visibility_audit` | 3건 OK |
| `test_k2_evidence_contract` | 34건 OK |
| `test_k2_continuation_coherence` | 13건 OK |
| `test_manual_portfolio_analysis` | 115건 중 error 3 (아래 참고) |
| `test_portfolio_decision_dashboard` | 306건 중 failure 1, error 187 (아래 참고) |

- 스키마 감사 `validate_schema_contracts.py`: PASS (errors 없음).
- **manual/dashboard 실패는 내 변경과 무관하다.** 기준 HEAD 체크아웃(다른 경로)에서 내 변경을 넣기 전과 후의 실패 목록이 완전히 같았다(manual 5건 = 5건, dashboard 211건 = 211건). 이 worktree의 실패는 그 기준 목록의 부분집합이다(새 실패 0건). 실패 원인은 위치에 따라 달라지는 환경 의존 항목으로 보인다(`INTEGRITY_FAILURE`, 외부 `bundle_support.py` 경로, 미추적 fixture). 개별 원인은 이번에 진단하지 않았다.
- 전체 스위트: 아래 §7.

## 7. 전체 스위트 (서브에이전트, 실패만)

명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py"`. 서브에이전트가 이 worktree(A, 변경 적용)와 기준 HEAD `b76d5e7` 체크아웃(B, 변경 없음, 저장소 밖 임시 경로)에서 각각 실행하고 실패 목록을 대조했다. 출력은 서브에이전트 보고를 옮긴 것이고 개별 실패는 내가 다시 확인하지 않았다.

| | 실행 | failures | errors | skip |
|---|---|---|---|---|
| A (변경 적용) | 1944 | 23 | 291 | 1 |
| B (기준 HEAD) | 1854 | 23 | 385 | 1 |

- **A에만 있는 실패(변경이 만든 새 실패): 0건.** 신규 `test_s1b_provider_marks` 20건은 모두 통과했다.
- B에만 있는 실패 94건은 환경 문제다. B는 gitignore·미추적 런타임 파일이 없어서 `stock-strategy-system\…`, `workspace\outputs\…` 경로에서 `FileNotFoundError`가 난다.
- **`docs/claude/test-run-latest.md`의 알려진 23건(failure 8 + error 15)과 총계가 다르다.** 그 실행은 원본 폴더에서 했고, 이번 A는 새 worktree라 untracked·gitignore 파일이 없다. 그래서 error가 291건이다(대부분 `test_portfolio_decision_dashboard` 188, `test_integrated_authority_snapshot` 38, `test_portfolio_decision_order_intent` 32). 기준(B)과의 차집합이 비어 있다는 것이 이번 결론의 근거이고, 원본 폴더에서의 전체 실행은 하지 않았다.
- A와 B 공통이며 알려진 항목과 겹치는 것: acceptance 바인딩 "exactly one manifest" 14건, `implementation hash mismatch`(`test_v2_6_7…`), PowerShell `Join-Path` 3건, `SEC_ACCESS_BLOCKED` 2건, `pypdf` 미설치 1건.
- 원본 폴더에서 같은 결과인지 확인하려면(선택): 병합 뒤 원본 폴더에서 전체 스위트를 한 번 돌려 `test-run-latest.md`의 23건과 비교한다.

## 8. 빈도 확인 (읽기 전용 한 줄)

수동 분석 보고서에서 미체결 `no_data_declared`를 집계한다(상태 필드 3개만 출력하고 보유·현금 값은 읽어도 출력하지 않는다). 저장소 루트에서 실행:

```
python -c "import json,glob,os;R=sorted(glob.glob('workspace/outputs/manual-portfolio-analysis/*/manual-portfolio-analysis.json'));E=[((json.load(open(p,encoding='utf-8')).get('broker_observed_state') or {}).get('open_order_evidence') or {}) for p in R];print(*[(os.path.basename(os.path.dirname(p))[7:15],e.get('bridge_status'),e.get('provider_return_code'),e.get('no_data_declared')) for p,e in zip(R,E)][-5:],sep='\n');print('reports',len(R),'no_data_declared_true',sum(e.get('no_data_declared') is True for e in E))"
```

- 출력: 최근 5개 보고서의 (날짜, 상태, 코드, 표식)과 마지막 줄의 집계. 보고서는 원본 폴더의 `workspace/outputs/`에 있으므로 원본 폴더 루트에서 실행한다.
- 현재 25개 보고서는 이번 변경 전이라 `provider_return_code`와 `no_data_declared`가 모두 `None`이다(확인함). 변경이 반영된 실행부터 값이 나온다.
- 안 B 착수 기준(결정 기록 §1): **2거래일 이상에 걸쳐 `no_data_declared=True`가 3회 이상.**
- 한계: 수동 분석 보고서에는 미체결 표식만 나온다. 실현손익 표식은 `run_broker_visibility_audit.py` 실행 결과에서만 볼 수 있다. 같은 원인이라 빈도 판단에는 미체결로 충분하다고 본다.

## 9. 남는 위험 / 확인 못 한 것

- 이번 변경 **이전에** 저장된 캡처는 `_failure_timing_evidence`의 해시 대조에서 새 결과와 맞지 않는다(결과에 필드가 늘었다). 결과는 지금처럼 fail-closed(FAIL)이고, 저장소 안에 캡처 생성기와 캡처 파일은 없다.
- 실제 운영 런타임에서 표식이 나오는지는 라이브로 확인하지 않았다(주문 API·계좌 조회를 이 세션에서 호출하지 않았다). 다음 수동 분석 실행 뒤 §8 명령으로 확인한다.
- 코드 20의 다른 의미, "없음" 선언의 시각 의미, 미체결이 실제로 있을 때의 실응답은 여전히 미확인이다(S1b §3-4).
- 안 B(빈 PASS 인정, K3)는 이 작업에 포함하지 않았다. 표식이 있어도 어떤 게이트도 열리지 않는다.
