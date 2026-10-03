# 미체결(ust21050)·실현손익(ust21630) 조회 진단 (S1b)

- 날짜: 2026-09-30
- 등급: K2 읽기 전용 진단. 코드·설정·정책·상태 파일은 수정하지 않았다.
- 지시문: `docs/claude/system-review-p4-roadmap-2026-09-30.md` 부록 A4
- 세션: 원본 폴더, 브랜치 `codex/master-recovery-expansion`, Sonnet 5.5 / high

## 1. 결론

- **원인(확정):** 두 조회 모두 요청 결함이 아니다. 키움이 "내역 없음"을 `return_code=20`으로 돌려주고, 브리지가 0이 아닌 `return_code`를 무조건 `KIWOOM_API_RESPONSE_ERROR`로 분류한다. 오늘 재현한 응답이 그렇다.
- **과거 16회도 같은 원인이라는 것은 추정이다.** 당시 응답 메시지는 저장되지 않았다(§3-3).
- 이 상태에서 `scope_complete`가 항상 false인 것은 코드 설계대로다. 고장이 아니라 "빈 결과를 성공으로 보지 않는" 보수 규칙의 결과다.
- 수정은 두 단계로 나뉜다(§5). **관측 추가는 K2, 빈 결과를 PASS로 인정하는 것은 K3**다. 이 단계에서는 수정하지 않았다.

## 2. 재현 결과 (조회 전용, 총 2회)

| 조회 | API | `return_code` | `return_msg`(6자리 이상 숫자는 마스킹) | 최상위 키 | `result_list` |
|---|---|---|---|---|---|
| 미체결 `account_open_items` | ust21050 | `20` (int) | `[2000](<digits-masked>:해당 계좌의미체결내역이 없습니다.)` | `return_code`, `return_msg` | 없음(None) |
| 당일 실현손익 `account_realized_pnl_read` | ust21630 | `20` (int) | `[2000](<digits-masked>:조회내역이 없습니다.)` | `return_code`, `return_msg` | 없음(None) |

- 요청 본문은 운영 브리지와 같다(§3-1). 결과는 실패가 아니라 서버가 "없음"을 선언한 응답이다.
- 정상 조회(잔고 ust21070, 예수금 ust21110, 체결 ust21510)는 이전 세션에서 `return_code=0`이었다(`i0-builder-report-2026-09-30.md` §5, 이 문서는 `worktree-i0-reconcile` 브랜치에 있다).
- **스펙의 오류 코드 표(37행)에는 `20`과 `2000`이 없다.** 이 "내역 없음" 응답은 스펙에 문서화되지 않은 동작이다. 그러므로 메시지 문구를 계약으로 삼을 수 없다.

## 3. 근거

### 3-1. 요청 구성 — 스펙·공식 예제와 일치

| 항목 | 브리지(`kiwoom_account_readonly_bridge.py`) | 스펙(`kiwoom_api_spec.json`) | 판정 |
|---|---|---|---|
| ust21050 본문 | `ord_dt=""`, `slby_tp="0"`, `stex_tp=""`, `stk_cd=""` (:32) | 모두 선택. `ord_dt` 미입력이면 오늘, `slby_tp` 0=전체 | 일치 |
| ust21630 본문 | `fc_krw_tp="0"`, `stex_tp=""`, `stk_cd=""` (:34) | `fc_krw_tp` 필수(0=외화), 나머지 선택 | 일치 |
| 경로 | `/api/us/acnt` (:21-27) | `/api/us/acnt` | 일치 |
| 연속조회 헤더 | 첫 페이지는 `cont_yn`·`next_key`를 보내지 않음 (:116-117, :93-95) | 둘 다 선택 | 일치 |
| 공식 예제 | 예제 `list_overseas_open_orders.py`와 `get_overseas_today_realized_pnl.py`의 기본 본문이 위와 같다 | | 일치 |

실행 성공 여부는 별개다. 재현에서 두 호출 모두 응답을 받았고 예외는 없었다.

### 3-2. 오류로 분류하는 조건

- `kiwoom_account_readonly_bridge.py:99-100`: `_return_code_ok(payload)`가 false이면 `KIWOOM_API_RESPONSE_ERROR`(`API_RESPONSE_ERROR`)를 낸다.
- `kiwoom_runtime_bridge.py:137-138`: `_return_code_ok`는 `return_code`가 `None`, `0`, `"0"`, `"0000"`일 때만 true다. `20`은 false다.
- 이 함수는 acceptance 고정 파일 16개 중 8번(`kiwoom_runtime_bridge.py`)에 있다. 따라서 이 함수는 고치지 않는다.
- 오류로 분류되면 `_sanitize`가 `data=[]`, `runtime_commit=None`, `retrieved_at=None`으로 비우고 `pagination`을 `complete=False`로 덮어쓴다(:237-241). 그래서 **당시 `return_code`와 `return_msg`는 어디에도 남지 않는다.**

### 3-3. 과거 16회에 대해 확인한 것과 못 한 것

- 확인: `docs/claude/i0-builder-report-2026-09-30.md` §6에 따르면 배치가 성공한 16회 모두 두 조회가 `KIWOOM_API_RESPONSE_ERROR`였다. 이 분류는 `return_code`가 0이 아닐 때만 난다.
- 못 함: 그때의 `return_code` 값과 메시지. 위 3-2 때문에 남아 있지 않다. 그래서 "과거도 20이었다"는 **추정**이다.
- 추정이 맞다는 정황: 두 조회 모두 "오늘의 미체결"과 "당일 실현손익"이다. 계좌에 미체결이 없고 그날 매도가 없으면 매번 비는 것이 정상이다.

### 3-4. 확인하지 못한 것

- 미체결이 **실제로 있을 때**의 실응답. 이 계좌에는 지금 미체결이 없어서 정상 `result_list` 경로를 실데이터로 볼 수 없었다. 이 경로는 합성 테스트(`test_k2_bridge_evidence_integrity.py`)로만 확인된다.
- `return_code=20`이 "내역 없음" 말고 다른 오류에도 쓰이는지. 스펙 표에 없어서 알 수 없다.
- 호출 시각이 미국 장 시간대의 어디였는지에 따라 `ust21630`(당일)이 비는 빈도가 달라질 수 있다.

## 4. 영향 (현재 동작)

| 위치 | 동작 |
|---|---|
| `kiwoom_broker_shadow.py:67-68` | 6개 조회가 모두 `PASS`여야 `scope_complete=true`. 이 둘이 실패라 항상 false |
| `kiwoom_broker_shadow.py:118-119` | `scope_complete=false`이면 제안의 `verified_scope="PARTIAL"`, `unresolved_fields=["INCOMPLETE_ACCOUNT_SCOPE"]` |
| `portfolio_decision_dashboard.py:957-966, 984` | 미체결 증거가 `PASS`, `pagination.complete`, `exhausted`가 아니면 `OPEN_ORDER_EVIDENCE_NOT_VERIFIED`. 그러면 `open_order_conflict_status="NOT_VERIFIED"` |
| 같은 파일 :984 | 미체결이 `PASS`이고 빈 목록이면 `VERIFIED_NONE`. **이 값이 주문 의도 단계의 차단을 푸는 쪽에 있다** |
| 실현손익 | `scope_complete`와 표시에만 쓰인다. 주문 게이트에는 쓰이지 않는다(`grep` 확인: `kiwoom_broker_shadow.py:92`, `broker_visibility_audit.py:49`) |

## 5. 수정안

수정은 이 세션에서 하지 않았다.

### 5-1. 안 A — 관측만 추가 (K2)

- 내용: 오류 결과에 정제된 진단 표식을 붙인다. 예: `provider_return_code`(정수만)와 `no_data_declared`(true/false). `bridge_status`는 계속 `KIWOOM_API_RESPONSE_ERROR`이고 어떤 게이트도 바뀌지 않는다.
- 효과: 다음 실행부터 "서버 오류"와 "서버가 없음을 선언"을 구분해 볼 수 있다. 추정(§3-3)이 확정으로 바뀐다.
- 영향 파일:
  - `manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py` (고정 아님)
  - `manage-us-stock-strategy/scripts/broker_visibility_audit.py` 및 스키마 `kiwoom-broker-visibility-audit.schema.json`(`additionalProperties: false`라 필드를 추가하려면 스키마 수정이 필요) (고정 아님)
  - 테스트: 신규 케이스. 기존 `test_return_code_twenty_is_still_error`는 그대로 통과해야 한다.
- 고정 파일 16개: 해당 없음. `kiwoom_runtime_bridge._return_code_ok`는 건드리지 않는다.
- 주의: 메시지 문구는 스펙에 없으므로 표식은 `return_code == 20` **그리고** 메시지가 `[2000]`으로 시작하는 경우로 좁게 잡고, 원문은 저장하지 않는다(계좌번호가 섞여 있다).

### 5-2. 안 B — "없음 선언"을 빈 PASS로 인정 (K3)

> **개정(2026-10-03):** 이 절은 `s1b-plan-b-design-2026-10-03.md`로 대체됐다(B′: 연산별 메시지 코드 허용 목록 추가). 아래는 당시 기록이다.

- 내용: 안 A의 좁은 조건에 맞는 응답을 `PASS`, `data=[]`, `pagination={api_id, pages:1, complete:true, exhausted:true}`로 낸다.
- 효과: `scope_complete`가 true가 될 수 있고, 미체결이 `VERIFIED_NONE`이 될 수 있다. `OPEN_ORDERS_UNVERIFIED` 경고가 사라진다.
- **K3인 이유:** 미체결 `VERIFIED_NONE`은 주문 의도 단계의 차단 해제 근거로 쓰이고(§4), `scope_complete`는 제안의 `verified_scope=FULL`을 결정한다. 이는 생산 의미론과 권한에 닿는다. 또 근거가 서버의 문서화되지 않은 응답이라 "결정론 규칙이 LLM 출력보다 앞선다"는 원칙 아래에서도 독립 Judge가 봐야 한다.
- 위험: (1) 코드 20이 다른 오류와 겹칠 가능성. (2) 한국어 메시지 일치에 의존. (3) 서버가 "없음"이라 했어도 방금 낸 주문이 반영되기 전일 수 있다(선언의 시각 의미가 약함).
- 영향 파일: 안 A와 같다. `portfolio_decision_dashboard.py`와 `kiwoom_broker_shadow.py`는 고치지 않아도 된다(빈 PASS를 이미 처리한다).
- 기존 테스트: `test_return_code_twenty_is_still_error`는 메시지 없는 20을 오류로 본다. 안 B의 좁은 조건이면 이 테스트를 바꾸지 않고 유지할 수 있다. 기대를 약화하는 변경은 하지 않는다.

### 5-3. 실현손익만 따로 (K2 후보)

- ust21630 빈 PASS는 주문 게이트에 닿지 않고 `scope_complete`에만 영향을 준다. 미체결이 실패인 동안은 `scope_complete`가 그대로 false라 실효 영향이 거의 없다.
- 그래도 같은 규칙을 공유하므로 안 A와 함께 넣고, PASS 승격은 안 B에서 같이 판단하는 편이 일관적이다.

### 5-4. 안 C — 현 상태 유지

- 이미 I0에서 "미체결 확인 불가 → 경고 후 적용 허용"으로 정했다(`i0-builder-report-2026-09-30.md` §7-1). 보유 수량은 `poss_qty`(보유분)라 미체결과 무관하다. 사용자가 키움 화면에서 미체결 0건을 눈으로 확인한다.
- 비용: 경고가 매번 남고, 주문 의도 단계는 계속 차단된다.

### 5-5. 권고

1. 안 A를 먼저 K2로 한다. 게이트를 바꾸지 않으므로 위험이 작고, 추정을 확정으로 바꾼다.
2. 안 B는 안 A로 "없음 선언"의 실제 빈도를 몇 회 모은 뒤, 독립 Judge와 함께 K3로 결정한다. 승인 없이는 진행하지 않는다.
3. 구현은 `worktree-i0-reconcile`(커밋 `dfb7f7b`)이 같은 브리지 파일을 이미 크게 바꿨으므로(+120줄, `_account_return_code_ok`가 int 0 또는 `"0"`만 성공으로 봄) **I0 Judge 뒤에 그 위에서** 만든다. 지금 원본 폴더에서 고치면 충돌한다.

## 6. Judge(S3)에 넘길 사항

- 10번(미체결 확인 없이 적용)의 근거: 오늘 재현에서 미체결은 "확인 불가"가 아니라 "서버가 없음을 선언"이었다. 다만 그 선언을 PASS로 인정하는 규칙은 아직 없다. 현행 "경고 후 적용 허용"은 그대로 안전한 쪽이다.
- 실현손익도 같은 원인이다. 별도 결함이 아니다.
- 과거 16회의 원인은 추정이다. 안 A를 넣기 전에는 확정할 수 없다.

## 7. 실행 기록

- 임시 스크립트: 저장소 밖 세션 임시 폴더의 `diag_open_orders_readonly.py`. 실행 전에 내용을 보여 주고 사용자 승인을 받았다.
- 실행: 운영 런타임 `Kiwoom-REST-API`의 venv 파이썬으로 1회. 호출은 ust21050 1회, ust21630 1회, 합계 2회. 인증 토큰은 브리지와 같은 방식(`_runtime_session`)으로 메모리에서 1회 발급했다.
- 출력 제한: `return_code`, `return_msg`(6자리 이상 숫자 마스킹, 200자 제한), 최상위 키 이름, `result_list` 타입만. 계좌 값·토큰·행 데이터는 출력하지 않았다.
- 주문 API·주문 도구·계좌 변경 호출: 없음. `.env` 내용은 읽거나 출력하지 않았다.
- 저장소 변경: 이 문서 1개뿐. 커밋하지 않았다.
- 중단 조건(원인 확인에 주문 API 필요): 해당 없음.
