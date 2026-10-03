# S1b 안 B Builder 보고 — "없음 선언"을 빈 PASS로 인정 (K3)

- 날짜: 2026-10-04
- 등급: K3 구현. 사용자가 2026-10-04에 구현 착수를 승인했다.
- 설계: `docs/claude/s1b-plan-b-design-2026-10-03.md`. 착수 시점 최종본은 418줄이었다.
- 세션: Claude Code, Opus 5.5 / xhigh, worktree `preflight-b`(설계를 쓴 worktree를 그대로 사용)
- 기준 HEAD: `be36308`(안 A `98a660b` 포함)
- 상태:
  - **미커밋.**
  - 구현 Judge PASS_WITH_CONDITIONS(2026-10-04). 사용자가 전달한 후속 작업인 K0 문서 정리 4건을 반영했다. 설계 문서 상태·수치 정정과 이 보고서 작성이다.
- 안전: 키움 도구, `.env`, 라이브 실행은 쓰지 않았다. 고정 파일, rmpa, 하류 게이트, 정책·상태 파일, acceptance manifest가 고정한 스크립트는 수정하지 않았다.

## 1. 변경 파일

| 파일 | diff | 줄바꿈 |
|---|---|---|
| `manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py` | +83 / −4 | CRLF 유지, ASCII만 사용 |
| `manage-us-stock-strategy/tests/test_s1b_plan_b_no_data_pass.py` | 새 파일, 566줄 | LF |
| `manage-us-stock-strategy/tests/test_k2_bridge_evidence_integrity.py` | +15 / −0 (테스트 1건 추가만) | CRLF 유지 |

브리지 변경 내용(설계 §4·§5):

- **상수**
  - 연산별 코드 표 `NO_DATA_PASS_MESSAGE_CODES`와 문구 표 `NO_DATA_PASS_MESSAGES`
  - `NO_DATA_MESSAGE_CODE`(`^\[2000\]\(([0-9]{6}):`), `NO_DATA_BODY_KEYS`, `NO_DATA_TERMINATION`
- **판정 함수:** `_continuation_field`, `_terminal_continuation`(C7), `_no_data_terminal`(C1·C2·C3·C4a·C4b·C6·C7)
  - 표는 `.get`으로 조회한다.
  - 예외는 함수 안에서 잡아 거짓으로 본다.
- **`_fetch_account_page`:** 오류를 던지기 직전에 `error.no_data_terminal`(bool)을 붙인다. 상태, `failure_type`, 안 A 표식, 재시도 동작은 그대로다.
- **`_read_pages`:**
  - 승격 조건: 첫 페이지(C5)이고, 상태가 `KIWOOM_API_RESPONSE_ERROR`이며, `no_data_terminal is True`다.
  - 승격 시점: 행 해석과 연속조회 엄격 검사 **앞**에서 return한다.
  - 승격 결과: pagination에 `pages=1`, `exhausted=True`, `complete=True`를 명시해 새로 만든다(F4).
  - 그 밖에는 인자 없는 `raise`로 원래 예외를 그대로 다시 던진다.
- **`_sanitize`:** 최종 상태가 PASS로 확정된 뒤에만 `terminated_by`를 남긴다.
  - 조건: worker 원본 `data`가 빈 list이고, `type(pages) is int and pages == 1`, `complete`·`exhausted`가 True다.
  - 표시 전용이다.
- **기존 주석 보정:** `NO_DATA_RETURN_CODE` 위의 "observation only; it never changes a status"를 안 B에 맞게 고쳤다. 동작 변경은 없다.

## 2. 새 테스트 (28건 + test_k2 1건)

| 클래스 | 건수 | 내용 |
|---|---|---|
| `PromotionTests` | 4 | 미체결·실현손익 승격(pagination dict 전체 단언), 연속 표시 없음·객체형에서도 승격(code 0 대조는 PARTIAL), 재시도 설정과 무관하게 호출 1회 |
| `NegativeTests` | 10 | C1, C2(재작성), C3(C4a·C4b와 함께 깨짐), C4a 단독(패치), C4b 단독(공백·끝 문자·NFD·닫는 전각 괄호·두 연산 문구 맞바꿈), C4 묶음(코드 변경), C5, C6, C7(필드별, 해시 불가 값 포함), 메시지 없는 20 |
| `JudgementSafetyTests` | 2 | 이상한 입력(해시 불가 메시지·`cont_yn`, dict 코드, 예외를 내는 continuation, 정수 키)에서 예외가 새지 않고 원래 상태·표식이 유지되는지. `_read_pages`가 원래 예외 객체를 그대로 다시 던지는지 |
| `TableTests` | 3 | 연산별 표 결속(패치. 다른 연산 코드를 가진 문구도 막는지), 운영 표 고정(코드·문구), 문구와 코드 정합 |
| `SanitizerTests` | 6 | 근거 유지, 위조·불일치 근거 제거(원본 `[None]`, `pages` 타입 등. 다른 필드는 근거가 없을 때와 같음), child 종료 코드 ≠ 0, 멱등, 표시 전용(rmpa·dashboard·shadow 결과 동일), 문구·코드·marker 미저장 |
| `IntendedEffectTests` | 3 | rmpa `scope_complete=true`, dashboard `VERIFIED_NONE`과 900초 신선도, shadow 스냅샷과 I0 제안의 `open_orders_verified=true` |
| test_k2 추가 | 1 | `test_no_data_declaration_reaches_verified_none_on_both_sell_paths`: 두 매도 경로에서 `VERIFIED_NONE`이고 `OPEN_ORDER_EVIDENCE_NOT_VERIFIED`가 없음 |

## 3. 대상 테스트 결과

| 파일 | 결과 |
|---|---|
| `test_s1b_plan_b_no_data_pass` (새 파일) | 28건 OK |
| `test_k2_bridge_evidence_integrity` | 18건 OK (기존 17 + 추가 1) |
| `test_s1b_provider_marks` (안 A, 수정 없음) | 20건 OK |
| `test_kiwoom_broker_shadow` | 24건 OK |
| `test_reconcile_broker_state` | 56건 OK |
| `test_broker_visibility_audit` | 3건 OK |
| `test_k2_evidence_contract` | 34건 OK |
| `test_k2_continuation_coherence` | 13건 OK |
| `test_language_contract` | 2건 OK (scripts ASCII 검사 포함) |
| `test_cash_flow_evidence_u3` | 18건 OK |

- 잠긴 테스트 `test_return_code_twenty_is_still_error`(test_k2:278)는 수정 없이 통과한다.
- 스키마 감사 `validate_schema_contracts.py`: PASS(errors 없음)

## 4. 전체 스위트 (서브에이전트)

명령: `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_*.py"` (이 worktree)

| | 실행 | failures | errors | skipped |
|---|---|---|---|---|
| 코드 수정 전 기준(같은 worktree, 문서 변경만) | 2309 | 23 | 291 | 1 |
| 코드 수정 후 | 2338 (+29) | 23 | 291 | 1 |

- **실패 ID 차집합은 양방향 모두 비어 있다.** 수정 후에만 있는 실패도 0건, 기준에만 있는 실패도 0건이다. 두 목록(각 314줄)이 같다는 비교는 서브에이전트가 했다. 이 세션은 줄 수와, 알려진 17건이 포함됐는지를 다시 확인했다.
- 알려진 실패 17건(`test-run-latest.md`: acceptance 후보 15건 + v2_6_7 2건)은 모두 목록 안에 있다.
- 나머지 297건은 미추적 런타임 파일이 없는 worktree 환경 때문이며, 기준 때부터 있었다. 대부분은 `IntegratedAuthorityLoadError: INTEGRITY_FAILURE` 268건이다. 그 밖에 acceptance manifest 바인딩 14건, `FileNotFoundError` 약 8건, PowerShell `Join-Path` 3건, `SEC_ACCESS_BLOCKED` 2건, `pypdf` 미설치 1건이다.
- 원본 폴더에서의 전체 실행은 하지 않았다.

## 5. 변형 실험 (저장소 밖 임시 폴더)

HEAD 코드에 새 테스트 파일을 넣거나, 현재 브리지를 한 곳씩 일부러 망가뜨린 사본으로 새 테스트 28건을 돌렸다. worktree는 건드리지 않았다. 건수는 subTest 단위 실패다.

| 대상 | 결과 |
|---|---|
| HEAD 브리지(변경 전) | 실패 19 + 오류 14 → 새 테스트가 구현 없이는 통과하지 않음 |
| 현재 브리지 | OK |
| C4b(문구 완전 일치) 제거 | 실패 20 |
| C4a(코드 표) 제거 | 실패 3 |
| C6(최상위 키 부분집합) 제거 | 실패 11 |
| C7(연속 표시) 제거 | 실패 45 |
| C5(첫 페이지) 제거 | 실패 2 |
| 코드 표를 연산별이 아닌 합집합으로 조회 | 실패 2 (*) |
| 문구 표를 합집합으로 조회 | 실패 2 |
| 지역 변수 `pages` 재사용(F4) | 실패 19 + 오류 1 |
| 정제기가 원본 대신 정제된 data로 판정 | 실패 4 |
| 판정 함수의 예외 가드 제거 | 오류 1 |
| `has_next`를 `is False` 대신 거짓값으로 판정 | 실패 4 |

(*) 처음 실행에서는 이 변형을 잡지 못했다. 문구 완전 일치(C4b)가 같은 공격을 한 번 더 막아서였다. 그래서 `TableTests`의 표 결속 테스트에 케이스를 하나 더했다. "다른 연산의 코드를 가진 문구가 이 연산의 문구 표에 들어 있어도 승격하지 않는다"는 내용이다. 그 뒤 11개 변형을 모두 잡는다.

## 6. 설계와 달라진 점 (6가지)

1. 브리지의 두 한글 문구는 `\u` 이스케이프로 썼다. `test_language_contract.py:20-22`가 `scripts/*.py`에 ASCII만 허용하기 때문이다. 값이 원 문구와 같은지 확인했고, 운영 표 고정 테스트가 값을 잠근다. 설계 §5-1의 "UTF-8로 쓰거나" 표현은 이번 정리에서 고쳤다.
2. `NO_DATA_RETURN_CODE` 위의 기존 주석("observation only; it never changes a status")을 사실에 맞게 고쳤다. 동작 변경은 없다.
3. 설계 §5-7의 선택 K0(`broker_visibility_audit.py:42` 주석 수정)은 하지 않았다. 수정 범위가 브리지 하나로 정해져 있었다.
4. 새 테스트는 설계 추정 약 22건보다 많은 28건이다. 더 잘게 나누었고, 세 가지를 더했다.
   - A-3: 연속 표시 모양 추가
   - `_read_pages`의 원래 예외 객체 재던짐 테스트
   - 표 결속 테스트의 코드 표 단독 케이스(§5의 (*))
5. E-3(I0 제안 확인)은 `test_reconcile_broker_state`의 픽스처(`account_results`, `base_state`, `make_proposal`)를 가져다 쓴다. test_k2가 다른 테스트 모듈을 가져다 쓰는 선례가 있다.
6. 브리지 diff가 설계 추정(약 40줄)보다 많은 +83 / −4다. 상수, 보조 함수 3개, 주석 때문이다.

## 7. 다음

- 커밋·병합은 사용자 지시를 기다린다.
- 병합 뒤 라이브 수동 분석 1회로 GRADE_B와 dashboard 컴파일 차단 해제를 확인한다(설계 §9-8).
- 운영 규칙(설계 §9-4)과 열린 항목(§9-10 예약주문, §9-11 주문 유효 기간)은 그대로 열려 있다.
- 임시 산출물(저장소 밖 세션 임시 폴더)은 아래와 같다.
  - 기준·수정 후 전체 실행 로그와 실패 목록: `baseline/`, `after/`
  - 변형 실험 스크립트: `verify_tests.py`
  - 진단 스크립트 2개
