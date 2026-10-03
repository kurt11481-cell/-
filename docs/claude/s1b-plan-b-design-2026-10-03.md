# S1b 안 B 설계 개정안 — "없음 선언"을 빈 PASS로 인정 (K3)

- 날짜: 2026-10-03.
- 개정(모두 2026-10-04):
  - Judge 조건 1~8 반영(§14)
  - 운영 규칙 시간대를 확정하고 열린 항목 2개를 추가(§9-4, §9-10·9-11)
  - Judge 재확인 조건 A~C와 F4 반영(§14-2)
- 등급: K3 설계. 설계 단계에서는 코드·테스트·정책·상태 파일을 수정하지 않았다. 구현은 §10과 `s1b-plan-b-builder-report-2026-10-04.md`를 본다.
- 상태:
  - 사용자 설계 승인(2026-10-03, §10), C4 확정(§12)
  - **독립 Judge 1차 판정 PASS_WITH_CONDITIONS, 조건 1~8 반영(2026-10-04, §14)**
  - **Judge 재확인 PASS_WITH_CONDITIONS, 조건 A~C와 F4 반영(2026-10-04, §14-2)**
  - **구현 완료(2026-10-04, `s1b-plan-b-builder-report-2026-10-04.md`). 구현 Judge PASS_WITH_CONDITIONS. 커밋·병합 대기.**
- 개정 대상: `open-orders-diagnosis-2026-09-30.md` §5-2. 이 문서가 그 절을 대체한다.
- 입력:
  - `preflight-fail-fix-design-2026-09-30.md` §1-4·§4·§7-3
  - `s1b-plan-a-builder-2026-09-30.md`
  - `s7-u3-transaction-history-measurement-2026-10-02.md`
  - Judge 판정. 판정 원문은 저장소에 없고, 조건 요약은 사용자가 전달했다.
- 기준 코드: `be36308` (안 A `98a660b` 포함). 줄 번호는 이 커밋 기준이다. 지시문의 bridge:145-167은 안 A 이전 번호이며 지금은 **164-186**이다.
- 세션: Claude Code, Opus 5.5 / xhigh, worktree `preflight-b`
- 표기: **확인**은 코드·문서·보고서로 직접 본 것, **추론**은 확인하지 못한 것이다.

## 1. 결론

1. 지시 요건 4개를 모두 반영했다(§4 C1·C2·C3, §5-3, §7-F).
2. **새 쟁점(결정됨: B′, 2026-10-03): `[2000]` 접두는 "없음" 전용이 아니다(§3).** 같은 `return_code=20` + `[2000](…)` 봉투가 다른 API에서 "조회기간 1년 초과" 거부에도 쓰였다. 요건 ③만으로 승격하면 다른 거부가 미체결 `VERIFIED_NONE`으로 바뀔 수 있다(fail-open).
   - **B′:** ③에 C4를 더한다. C4는 연산별 메시지 코드(C4a)와 연산별 메시지 전체 완전 일치(C4b)다. ③보다 좁히는 방향이라 ③과 충돌하지 않는다.
   - U3도 메시지 코드로 판정하지만 부분문자열 검사여서 C4보다 넓다(§3).
   - 선행 조건 충족: 두 연산의 코드는 모두 `571758`이다(§11·§12). 같은 코드가 서로 다른 두 문구에 쓰이므로 문구 완전 일치를 AND로 더했다(Judge 조건 1, §14).
3. 추가 조건:
   - C5: 첫 페이지일 때만
   - C6: 최상위 키 ⊆ {`return_code`, `return_msg`} (Judge 비차단 권고 채택)
   - C7: 연속 표시의 정확한 허용값 (Judge 조건 2)
   - PASS 근거 표식 `pagination.terminated_by`. 표시 전용이다.
4. 수정 파일은 `kiwoom_account_readonly_bridge.py` 하나(+ 선택 K0 주석 1줄)다. 고정 파일·rmpa·하류 게이트는 바꾸지 않는다. 하류는 이미 빈 PASS를 처리한다(§6).

## 2. 착수 근거 재확인

원본 폴더 `workspace/outputs/manual-portfolio-analysis/` 보고서 32개에서 상태 필드만 읽었다(보유·현금 값은 출력하지 않음).

| 실행(UTC) | 미체결 상태 | 코드 | `no_data_declared` | 실현손익 상태 | preflight |
|---|---|---|---|---|---|
| 09-30 06:39, 11:21, 13:44 | `KIWOOM_API_RESPONSE_ERROR` | 20 | true | `KIWOOM_API_RESPONSE_ERROR` | FAIL |
| 10-02 04:07, 04:24, 08:17 | `KIWOOM_API_RESPONSE_ERROR` | 20 | true | `KIWOOM_API_RESPONSE_ERROR` | FAIL |
| 10-02 08:16 | `RUNTIME_PYTHON_UNAVAILABLE` | None | false | 같음 | FAIL |

- **확인:** `no_data_declared=true` 6건, ET 기준으로도 9/30·10/2 2거래일. 착수 기준(2거래일 이상, 3회 이상)을 충족한다.
- **한계:** 6건은 모두 **미체결** 표식이다. 실현손익 표식은 수동 분석 보고서에 저장되지 않는다(rmpa는 `open_order_evidence`만 남긴다). 안 A 이후 visibility audit 산출물도 없다(확인). 실현손익의 20 + `[2000]` 직접 관측은 진단(9/30, 10/3)뿐이다. 실현손익은 주문 게이트에 쓰이지 않는다(§6).

## 3. 새 쟁점: `[2000]`은 공통 메시지 봉투다

- **확인:** U3 실측(`s7-u3-transaction-history-measurement-2026-10-02.md` 18-24행, 59-60행)에서 ust21100은 아래를 돌려줬다. 테스트 픽스처(`test_cash_flow_evidence_u3.py:27-28`)에서 둘 다 `[2000](NNNNNN:…)` 형식이다.
  - 행이 없을 때: `return_code 20` + `501724:관련자료가 없습니다`, `result_list` 없음
  - 기간이 1년을 넘을 때(거부): `return_code 20` + `501058:조회기간은 1년 이내로만 가능합니다`
- **U3 판정 방식 (정정, Judge 조건 6):** U3는 메시지 안에 `501724:`가 **들어 있는지**(부분문자열)로 판정한다(`cash_flow_evidence.py:42, 119-125`). 위치나 `[2000](` 접두는 보지 않는다. 안 B의 C4는 이보다 좁다. 시작 위치를 고정한 코드(C4a)에 더해 메시지 전체가 완전히 일치해야 한다(C4b).
- S1b 진단(9/30)은 괄호 안 숫자를 계좌번호일 수 있다고 보고 마스킹했다(`<digits-masked>`). 10/3 진단으로 값을 얻었고, 사용자가 계좌 식별자의 일부가 아님을 확인했다(§12).
- **영향(추론):** ③만으로 승격하면 같은 봉투를 쓰는 다른 거부도 빈 PASS가 된다(예: 조회 가능 시간 아님, 파라미터 오류. 실관측은 없음). 미체결에서 이는 `VERIFIED_NONE`이고 주문 의도 차단 해제 쪽이다.
- **10/3 진단(§11·§12):** ust21050과 ust21630이 서로 다른 문구로 같은 코드 `571758`을 돌려줬다. 그래서 이 코드는 문구별 고유 코드가 아니라 "조회 결과 없음" 계열의 묶음 코드로 보인다(추론). U3 ust21100의 "없음" 코드(501724)와도 다르다. 이것이 C4b(문구 완전 일치)를 더한 이유다.
- 안 A의 합성 메시지는 괄호 안이 10자리 계좌형 숫자(`5012345678`)이고 문구도 합성이다. C4a와 C4b를 모두 만족하지 않아 승격되지 않는다. 그래서 안 A 테스트 20건은 수정 없이 계속 유효하다. 그 뜻은 "허용 목록 밖 선언은 오류와 게이트 차단을 유지한다"이다(§7-F).

## 4. 승격 조건

아래를 **모두** 만족할 때만 승격한다. 하나라도 어긋나면 지금처럼 `KIWOOM_API_RESPONSE_ERROR`이고 안 A 표식도 지금과 같다.

| # | 조건 | 출처 |
|---|---|---|
| C1 | 연산이 표의 키(`account_open_items`, `account_realized_pnl_read`)에 있음. 표 조회는 `.get(operation, frozenset())` | 요건 ②, Judge 조건 3 |
| C2 | `type(return_code) is int and return_code == 20`. bool, `"20"`, `20.0`은 제외한다(안 A `_provider_marks`와 같은 타입 규칙) | 요건 ③ |
| C3 | `return_msg`가 문자열이고 `[2000]`으로 시작 | 요건 ③ |
| C4a | `return_msg`가 정규식 `^\[2000\]\(([0-9]{6}):`에 맞고, 잡힌 코드가 `NO_DATA_PASS_MESSAGE_CODES.get(operation, frozenset())`에 있음. **값: 두 연산 모두 `{"571758"}`.** `\d` 대신 `[0-9]`를 써서 비ASCII 숫자를 배제한다 | §3, §12 |
| C4b | `return_msg`가 `NO_DATA_PASS_MESSAGES.get(operation, frozenset())`의 원소와 **완전히 같음**. strip, 대소문자 변환, 유니코드 정규화를 하지 않는다. 값은 아래와 같다 | Judge 조건 1, 사용자 결정(2026-10-04) |
|  | 미체결: `[2000](571758:해당 계좌의미체결내역이 없습니다.)` |  |
|  | 실현손익: `[2000](571758:조회내역이 없습니다.)` |  |
| C5 | 첫 페이지(`page_index == 1`) | 연속 페이지 뒤의 "없음"은 앞 페이지의 "더 있음"과 모순이고, 앞 페이지 행만 남는 경로를 막는다 |
| C6 | 응답 본문의 최상위 키 집합 ⊆ {`return_code`, `return_msg`}. `result_list`를 포함해 다른 키가 하나라도 있으면 승격하지 않는다. C2·C4가 두 키를 요구하므로 실제로는 정확히 이 두 키다 | Judge 비차단 권고 채택. 9/30·10/3 관측 모양 |
| C7 | 연속 표시의 각 필드가 아래 허용값 중 하나다. 그 밖의 값은 모두 승격하지 않는다 | Judge 조건 2. 10/3 실응답은 `cont_yn="N"`, `next_key=None`, `has_next=False` |
|  | `cont_yn`: 없음, `None`, `""`, `"N"` (예: 소문자 `"n"`, `"Y"`, `" "`, `0`은 승격 안 함) |  |
|  | `next_key`: 없음, `None`, `""` |  |
|  | `has_next`: 없음, 또는 정확히 `False`(bool). 키가 있는데 `None`, `0`, `"false"`이면 승격 안 함 |  |

C7을 읽는 방법:

- continuation이 `None`이면 세 필드 모두 "없음"이다.
- dict이면 키로, 그 밖의 객체면 속성으로 읽는다. `_read_pages` 165-179와 같은 방식이다.
- 엄격 검사(164-186)처럼 표시의 존재를 요구하지 않는다(요건 ①과 양립).

C3·C4a는 C4b에 포함되지만 독립 검사로 남긴다. 문구 표가 잘못 바뀌어도 코드 표가 한 번 더 막게 하려는 것이다.

**판정 계산의 안전 (Judge 조건 3)**

- 승격 판정은 어떤 입력에서도 예외를 내지 않는다.
- 타입을 먼저 확인한다. 예를 들어 `return_msg`가 문자열이 아니면 표 조회 전에 거짓이다. 그래서 해시가 안 되는 값으로 집합을 조회하는 일이 없다.
- 표는 `.get`으로 찾는다.
- 예상하지 못한 예외(예: 속성 접근이 예외를 내는 continuation 객체)는 판정 함수 안에서 잡아 거짓으로 본다.
- 그래서 승격되지 않은 응답은 지금과 같은 `BridgeError` 인스턴스로, 같은 상태(`KIWOOM_API_RESPONSE_ERROR`)·`failure_type`·안 A 표식을 달고 그대로 던져진다.

**승격 결과**

- `bridge_status="PASS"`, `data=[]`
- `pagination={api_id, pages: 1, exhausted: true, complete: true, secret_fields_retained: false, terminated_by: "PROVIDER_NO_DATA_DECLARATION"}`
- `runtime_commit`은 세션 커밋, `retrieved_at`은 worker의 `utc_now()`다. 다른 PASS와 같다.
- 안 A 오류 표식(`provider_return_code`, `no_data_declared`)은 붙지 않는다. 안 A의 "표식은 오류 결과에만" 불변식이 그대로다.
- `terminated_by`는 **표시 전용**이다(§5-5).

## 5. 구현 위치와 동작

파일: `manage-us-stock-strategy/scripts/kiwoom_account_readonly_bridge.py` (고정 아님, 실제 diff +83 / −4)

1. **상수**
   - 코드 표 `NO_DATA_PASS_MESSAGE_CODES`:

     ```python
     {"account_open_items": frozenset({"571758"}),
      "account_realized_pnl_read": frozenset({"571758"})}
     ```

   - 문구 표 `NO_DATA_PASS_MESSAGES`:

     ```python
     {"account_open_items": frozenset({"[2000](571758:해당 계좌의미체결내역이 없습니다.)"}),
      "account_realized_pnl_read": frozenset({"[2000](571758:조회내역이 없습니다.)"})}
     ```

   - `NO_DATA_TERMINATION = "PROVIDER_NO_DATA_DECLARATION"`
   - 두 표의 키 집합은 같아야 하고, C1은 그 키로 정한다. 연산별 표로 두는 이유는 한쪽 값이 바뀌어도 다른 연산에 번지지 않게 하려는 것이다.
   - 문구는 소스 리터럴이다. `scripts/*.py`는 ASCII만 허용되므로(`test_language_contract.py:20-22`) `\u` 이스케이프로만 쓸 수 있다. 운영 표 고정 테스트가 값으로 잡는다(§7 C-2).
2. **`_fetch_account_page` (125-129)**
   - 오류를 던지기 직전에 판정 함수(예: `_no_data_terminal(operation, payload, response)`)로 C1·C2·C3·C4a·C4b·C6·C7을 계산한다. 결과는 **bool 하나**(`error.no_data_terminal`)로 예외에 붙인다.
   - 판정 함수는 예외를 내지 않는다(§4).
   - 메시지·코드 문자열은 예외에 붙이지 않는다(안 A 원칙).
   - 상태, `failure_type`, 안 A 표식, 재시도 동작은 그대로다. `API_RESPONSE_ERROR`는 재시도 대상이 아니어서 첫 시도에서 던진다.
3. **`_read_pages` (150-152)**
   - `_fetch_account_page` 호출을 감싼다. 아래를 모두 만족하면 §4의 승격 결과로 return한다.
     - 예외가 `BridgeError`다
     - `status == "KIWOOM_API_RESPONSE_ERROR"`다
     - `page_index == 1`이다(C5)
     - `getattr(exc, "no_data_terminal", None) is True`다
   - 그 밖에는 인자 없는 `raise`로 같은 예외를 다시 던진다.
   - **구현 주의 (F4):** 조기 return 시점의 지역 변수 상태는 `pages = 0`(148행, 162행 대입 전), `exhausted = False`(147행)다. 그래서 승격 결과의 pagination은 `pages: 1`, `exhausted: True`, `complete: True`를 **명시해서** 새로 만든다. 지역 변수나 기존 return문(193-194)을 재사용하지 않는다.
   - 이 return은 `result_list` 해석(153-161)과 미체결 연속조회 엄격 검사(164-186) **앞**이다(요건 ①). 이유는 두 가지다.
     - 오류 응답은 `_fetch_account_page`에서 이미 예외가 된다.
     - 설령 넘어가도 `result_list`가 없으면 156행에서 `KIWOOM_SCHEMA_MISMATCH`가 된다.
   - 10/3 실응답의 연속 표시는 엄격 검사를 통과하는 모양이었다(§11). fix-design §7-3의 "break → PARTIAL" 추정을 정정한다.
4. **`external_worker`**: 변경 없음. PASS 판정은 기존대로 `pagination["complete"]`다.
5. **`_sanitize`의 `terminated_by` (Judge 조건 4)**
   - **판정 시점:** 최종 상태가 확정된 뒤에 판정한다. 즉 미체결 행 강등(264-268)과 오류 분기(269-278) 다음이고, 최종 상태가 PASS일 때만이다.
   - **조건(모두 만족):**
     - 값이 `NO_DATA_TERMINATION`과 같다.
     - 연산이 표의 키에 있다.
     - **worker 원본** `data`가 list이고 비어 있다. 정제된 `data`로 보면 안 된다. 실현손익의 `[None]`은 정제하면 `[]`가 되기 때문이다.
     - 원본 pagination이 dict이고 `type(pages) is int and pages == 1`이다(`True`, `1.0`, `"1"` 제외). `complete is True`, `exhausted is True`이다.
   - 하나라도 어긋나면 키를 만들지 않는다. 상태는 바꾸지 않는다.
   - child 종료 코드가 0이 아니어서 실패로 다시 정제되는 결과(322-323)에는 붙지 않는다.
   - **표시 전용:** 어떤 게이트도 이 키를 읽지 않는다. 게이트 판정은 `bridge_status`, `data`, pagination의 기존 키로만 한다. 이 키가 있든 없든 하류 결과가 같아야 한다(§7 D-4).
   - rmpa:336이 `_sanitize`를 한 번 더 부르므로 같은 입력에 같은 출력(멱등)이어야 한다.
6. **성공 판정 함수는 바꾸지 않는다.** `_account_return_code_ok`는 여전히 0만 성공으로 본다. 승격은 성공 판정을 넓히는 것이 아니라 열거된 한 가지 예외 경로다.
7. **(선택 K0)** `broker_visibility_audit.py:42` 주석 "a provider 'no records' declaration never turns UNKNOWN into AVAILABLE"은 안 B 뒤 전체 경로 기준으로 틀린 말이 된다. "오류 결과의 표식은 UNKNOWN을 AVAILABLE로 바꾸지 않는다(승격은 브리지에서만)"로 고친다. 동작 변경은 없다.

## 6. 하류 영향 (승격 시, 코드는 그대로)

| 위치 | 지금 | 안 B 뒤 |
|---|---|---|
| rmpa:1763-1765 | `ACCOUNT_EVIDENCE_NOT_VERIFIED:` 두 연산 | 사라짐 → preflight PASS, GRADE_B, `decision_quality_eligible=true` 가능(추론: cutoff·권한 재검증·일봉 검증 통과 필요) |
| rmpa:342-344 브로커 `as_of` | 두 연산 제외 | 두 연산의 `retrieved_at` 포함 |
| **dashboard:1297-1314 → 1527-1536 (Judge 조건 6)** | `_canonical_evidence_gate`의 필수 조건이 걸린다. `PREFLIGHT_NOT_PASS`, `EVIDENCE_GRADE_NOT_GRADE_B`, `FINALIZED_BAR_PREFLIGHT_NOT_PASS`, `DECISION_QUALITY_NOT_ELIGIBLE` 등이 `evidence_gate_blockers`가 되어 `core_status=BLOCKED` | rmpa가 PASS·GRADE_B·적격에 닿고 일봉 검증이 PASS면 이 차단이 풀려 `core_status`가 VERIFIED가 될 수 있다(추론). **컴파일 차단 해제 경로다.** 아래 `VERIFIED_NONE`과 합쳐져 `ORDER_INSTRUCTION_READY`에 이른다 |
| dashboard:947-984 | `NOT_VERIFIED` | **`VERIFIED_NONE`**. 900초 신선도와 `FROM_FUTURE` 검사는 그대로 적용된다 |
| order intent:738-748 | `ORDER_BLOCKED`(`OPEN_ORDER_EVIDENCE_NOT_VERIFIED`) | **다른 차단이 없으면 `ORDER_INSTRUCTION_READY`.** `order_authority=false`, `broker_submission=DISABLED`는 그대로다. **K3의 핵심** |
| dashboard:1490-1495 | `OPEN_ITEMS_VISIBILITY_UNAVAILABLE`, `AUXILIARY_SCOPE_INCOMPLETE…` 경고 | 사라짐 |
| render_beginner:370 | `BROKER_SCOPE_INCOMPLETE` | 사라짐 |
| shadow:85-90, 101 | `scope_complete=false` | true. `broker_snapshot_as_of`가 두 연산 시각까지 포함 |
| shadow:320-351 (I0 제안) | `open_orders_verified=false`, `OPEN_ORDERS_UNVERIFIED` 경고 | true, 경고 없음. 사용자 확인 apply 때 `portfolio_state.last_confirmed_broker_snapshot.open_orders_verified=true`로 기록된다(apply:132). 이 필드를 게이트로 읽는 코드는 없다(grep) |
| audit:30-46, 84-86 (Judge 조건 6) | 두 visibility UNKNOWN, `NOT_READY` | 두 visibility AVAILABLE(0건). `broker_visibility_for_live_execution="READY"`가 되려면 신선함, 미체결 AVAILABLE, **체결(fills) AVAILABLE**이 모두 필요하다. 체결은 지금도 PASS다(최근 보고서 9건 중 8건 PASS, 1건은 런타임 오류. 확인). 그래서 미체결이 AVAILABLE이 되면 신선할 때 사실상 READY다. 이 값을 읽는 코드는 없다(grep: 산출 파일과 콘솔 출력뿐) |

## 7. 테스트 계획

새 파일 `test_s1b_plan_b_no_data_pass.py` 28건(실제)과, `test_k2_bridge_evidence_integrity.py`에 **추가만** 1건이다. 기존 테스트는 고치지 않는다.

- **양성 픽스처:** 10/3 실응답 모양.
  - 본문: `{"return_code": 20, "return_msg": <그 연산의 C4b 문구>}` (키 두 개)
  - continuation: `{"cont_yn": "N", "next_key": None, "has_next": False}`
  - 1쪽
- **원칙 (Judge 조건 5):** 음성 테스트는 모두 양성 픽스처에서 **조건 하나만** 바꾼다. subTest 이름에 바꾼 조건(C1~C7)을 적는다. 다른 조건까지 함께 깨지는 입력은 쓰지 않는다. 예: 안 A의 음성 12종은 모두 `result_list=[]`를 함께 넣어 C6도 깨지므로, 그대로 재사용하지 않는다.

- **A. 승격(4)**
  1. 미체결: worker와 부모 모두 PASS, `data=[]`, `retrieved_at=NOW`, `runtime_commit` 있음, 호출 1회. pagination은 dict **전체**가 아래 값과 같은지 단언한다(키 일부만 보지 않는다). `pages=0` 재사용(F4)도 이 단언이 잡는다.
     `{"api_id": "ust21050", "pages": 1, "exhausted": True, "complete": True, "secret_fields_retained": False, "terminated_by": "PROVIDER_NO_DATA_DECLARATION"}`
  2. 실현손익: 같은 결과. pagination 전체 단언에서 `api_id`만 `"ust21630"`이다
  3. continuation이 `None`(세 필드 없음)이어도 PASS. 대조: 같은 헤더에 code 0 + `result_list=[]`이면 PARTIAL이다(엄격 검사 앞 종결 증명)
  4. `maximum_attempts=2`여도 호출 1회로 승격한다(`API_RESPONSE_ERROR`는 재시도 안 함)
- **B. 음성: 오류 유지, 안 A 표식은 안 A 규칙대로(8, subTest)**
  1. **C1만:** 다른 4개 연산에 미체결 문구와 실현손익 문구를 각각 그대로 준다.
  2. **C2만 (재작성):** `return_code`를 `"20"`, `20.0`, `True`, `False`, `19`, `21`, `-1`, 키 없음으로 바꾼다. 키를 빼도 C6(부분집합)은 그대로 만족하므로 C2만 깨진다. 기대 표식은 안 A 규칙대로다: 정수면 그 값과 false, 나머지는 None과 false.
     - **C3 (C4a·C4b와 함께 깨짐):** `return_msg`를 `None`, `2000`(int), `[…]`(list), `[2001](571758:…)`로 바꾼다. 메시지를 바꾸면 C4a·C4b도 함께 깨지므로 단일 조건 원칙의 예외로 표시한다.
  3. **C4a만:** 패치로 문구 표에 허용 목록 밖 코드의 문구(예: `[2000](571757:해당 계좌의미체결내역이 없습니다.)`)를 넣는다. 그 응답은 C4b를 통과해도 C4a에서 막혀 승격되지 않는다(코드 표의 독립 방어 확인).
     - **C4b만 (코드는 `571758` 그대로, 문구만 바꿈):**
       - 공백과 끝 문자: 끝 공백, 끝 줄바꿈, 마침표 없음, 닫는 괄호 없음, 코드 뒤 공백(`571758: 해당…`), 띄어쓰기 다름(`계좌의 미체결`), 뒤에 덧붙은 글자
       - 문자 형태: 유니코드 분해형(NFD), 닫는 전각 괄호(`…없습니다.）`). 여는 괄호를 전각으로 바꾸면 C3·C4a도 깨지므로 여기에 넣지 않는다.
       - **두 연산 문구 맞바꿈:** 미체결 연산에 실현손익 문구, 그 반대. 문구가 다르므로 이제 의미가 있다.
     - **C4a·C4b 함께(코드만 바꿈):** `571757`, `571759`, `501724`, `501058`, 5자리, 7자리, 전각 숫자, 콜론 없음, `(` 뒤 공백. 이 경우는 문구 일치도 함께 깨지므로, C4 묶음 하나를 깨는 것으로 표시한다.
  4. **C5만:** 1쪽은 code 0 + `cont_yn=Y` + 커서 + 행 1개, 2쪽은 양성 응답이다. 결과는 오류이고 1쪽 행은 남지 않는다.
  5. **C6만:** 키 하나를 더한다. `result_list`가 `[]`, `None`, 행 있음인 경우와, 다른 키(`output: []`, 임의 문자열 키)인 경우다.
  6. **C7만 (필드별):**
     - `cont_yn`: `"Y"`, `"2"`, `"MORE"`, `"TRUE"`, `"n"`, `"N "`, `" "`, `"X"`, `0`, `False`, `["N"]`(list), `{"N": 1}`(dict)
     - `next_key`: `"k"`, `" "`, `0`, `False`
     - `has_next`: `True`, `None`(키 있음), `0`, `"false"`
  7. **판정 계산 안전 (Judge 조건 3):** 아래 입력에서 예외가 새지 않고 결과는 오류이며, 상태·`failure_type`·안 A 표식이 지금 규칙과 같다.
     - `return_msg`가 list나 dict(해시 불가)
     - `return_code`가 dict
     - `cont_yn`이 list나 dict(해시 불가). 허용값을 집합으로 조회하는 구현이면 타입 확인 없이 `TypeError`가 날 수 있다
     - 속성 접근이 예외를 내는 continuation 객체
     - 정수 키가 섞인 본문
  8. 메시지 없는 20(잠긴 테스트와 같은 입력)도 여기서 오류임을 한 번 더 본다.
- **C. 표(3)**: "두 연산 코드 맞바꿈"을 대체한다.
  1. **표 결속(동작 검증):** `patch.dict`로 두 표를 연산별로 다른 합성 코드·문구로 바꾼다. 각 연산이 자기 항목으로만 승격되고 상대 항목으로는 오류인지 확인한다. 구현이 연산별 조회 대신 합집합을 쓰는 실수를 잡는다.
  2. **운영 표 고정(데이터 잠금):** 두 표가 정확히 §5-1 값인지 확인한다(키 집합, 코드, 문구 포함). 코드·문구·연산을 하나라도 늘리거나 바꾸면 이 테스트가 깨진다. 그래서 허용 목록 변경은 반드시 테스트 변경과 K3 검토로 드러난다.
  3. **표 정합:** 문구 표의 각 문구가 `[2000](` + 같은 연산의 코드 + `:`로 시작한다.
- **D. 정제기 (Judge 조건 4, 5)**
  1. 위조·불일치 `terminated_by`는 키 없음, 상태 불변이다.
     - `data` 쪽: 원본 `data=[None]`인 실현손익 PASS(정제하면 `[]`), 행 있음, `data` 없음·`None`·문자열
     - `pages` 쪽: `True`, `1.0`, `"1"`, `2`
     - `complete`·`exhausted`가 false이거나 없음
     - 값이 다름, PARTIAL·오류 상태, 다른 연산, 미체결 행 강등(`KIWOOM_SCHEMA_MISMATCH`)
  2. child 종료 코드가 0이 아니면 실패가 되고, 키는 없다.
  3. 멱등: `_sanitize` 두 번 = 한 번. `_normalize_broker_state` 뒤에도 유지된다.
  4. **표시 전용:** 승격 결과에서 `terminated_by`를 지워도 rmpa `_normalize_broker_state`, dashboard `_sell_readiness_evidence`, shadow 스냅샷 결과가 같다.
  5. **원문 미저장:** 아래가 worker와 부모 출력 어디에도 없다. 두 문구, `571758`, `[2000]`, `return_msg`, 합성 marker, 계좌형 숫자.
- **E. 의도한 K3 변화를 고정(3 + test_k2 추가 1)**
  1. rmpa `_normalize_broker_state`: 미체결 PASS, `scope_complete=true`, 두 연산 PASS
  2. dashboard `_sell_readiness_evidence`: `VERIFIED_NONE`. 같은 결과의 시각이 900초를 넘으면 `OPEN_ORDER_EVIDENCE_STALE`(기존 검사가 적용되는지 확인)
  3. shadow 스냅샷과 I0 제안: `scope_complete=true`, `open_orders_verified=true`, 경고 없음, 스냅샷에 `terminated_by`·표식 없음
  4. (test_k2 추가) 두 매도 경로에서 `VERIFIED_NONE`, `OPEN_ORDER_EVIDENCE_NOT_VERIFIED` 없음, `order_authority=false`, `broker_submission=DISABLED`
  - dashboard 컴파일 차단 해제(§6 1297-1314)는 rmpa 전체 실행이 필요해 단위 테스트로 고정하지 않는다. 병합 뒤 라이브 1회로 확인한다(§9-8).
- **F. 그대로 통과**
  - `test_return_code_twenty_is_still_error`(test_k2:278). 메시지 없는 20이라 C3에서 걸린다(요건 ④)
  - `test_s1b_provider_marks` 20건. 수정 없음(§3 끝). 기록용: B였다면 3건이 뒤집혀 수정해야 했다
  - test_k2_evidence_contract:354, test_reconcile_broker_state:162, test_broker_visibility_audit, test_kiwoom_broker_shadow
  - test_manual_portfolio_analysis(고정, 수정 금지): 기준 대비 새 실패 0
- 대상 테스트를 먼저 돌린다. 전체 스위트는 서브에이전트로 돌려 기준 HEAD와 실패 목록을 대조한다. 스키마 감사도 돌린다.

## 8. 바꾸지 않는 것

- `run_manual_portfolio_analysis.py`, 고정 파일 16개(`kiwoom_runtime_bridge.py`의 `_return_code_ok`, `BridgeError`, `_continuation` 포함). acceptance manifest가 고정하는 브리지는 `kiwoom_runtime_bridge.py`뿐이다(확인).
- dashboard, order intent, shadow, reconcile, apply, audit 동작.
- 스키마: 수동 분석 `open_order_evidence`는 제약이 없다(안 A 확인). audit은 `terminated_by`를 옮기지 않는다.
- 정책 파일, `portfolio_state.json`
- 줄바꿈: 기존 파일을 수정할 때는 CRLF 유지(일괄 변환 금지). 새 파일은 LF로 둔다(안 A 선례). 커밋하면 autocrlf로 저장소에는 LF로 들어간다.

## 9. 남는 위험 / 확인 못 한 것

1. (기록용, B는 선택되지 않음) ③만으로 승격하면 다른 `[2000]` 거부가 승격되는 fail-open(§3).
2. **허용 코드 `571758`과 두 문구는 하루(2026-10-03 토요일·개천절)만 관측했다.**
   - 평일 값이 다르면 승격되지 않아 지금처럼 FAIL이고, 안 A 표식으로 보인다(fail-closed).
   - 반대로 같은 코드·문구가 "없음" 외 조건에 쓰이면 fail-open이 남는다. 문구 완전 일치(C4b)로 그 범위를 좁혔다(§13 ①②, §14 조건 1).
3. **문구 완전 일치의 출처 (Judge 조건 1)**
   - C4b 문구는 2차 진단의 120자 마스킹 출력(`message_text_masked`)에서 읽은 값을 사용자가 전달한 것이다. 이 세션은 원 출력을 보지 못했다.
   - 공백이나 끝 문자(마침표, 닫는 괄호, 줄바꿈, 전각 문자 등)가 원문과 다를 수 있다. 다르면 승격되지 않아 지금처럼 FAIL이다(fail-closed). 이 차이는 병합 뒤 라이브 수동 분석에서 드러난다.
   - 보고서에는 어느 조건이 어긋났는지 남지 않는다(안 A 표식은 그대로 `20`, true). 그때는 §12의 진단 스크립트를 다시 돌려 문구를 대조한다.
4. **열린 K3 항목: `ord_dt=""`("오늘")의 기준일 (Judge 조건 7)**
   - **위험: "오늘"을 어떤 날짜로 해석하는지 모른다 (Judge 재확인 조건 C).** 날짜가 바뀌는 시각에 따라, 그 전에 낸 주문을 그 뒤 조회에서 놓칠 수 있다. 세 가설은 아래와 같다(모두 추론).
     - **가설 1. KST 날짜:** KST 00:00에 바뀐다. 이때는 정규장 도중이다. KST 전날 낸 주문이 살아 있으면 00:00 뒤 조회에서 놓칠 수 있다.
     - **가설 2. 미국 동부 달력 날짜:** ET 00:00에 바뀐다. 이는 KST 13:00(서머타임) 또는 14:00(미적용)으로, 주간거래 도중이다. 주간거래 앞부분에 낸 주문을 그 뒤 조회에서 놓칠 수 있다. 이 경계는 KST 00:00~08:00 밖이다.
     - **가설 3. 미국 거래 세션 날짜:** 한 거래일의 세션(주간·Pre·정규·애프터)을 한 날짜로 묶는다. 날짜는 세션 사이(애프터마켓 종료 08:00과 다음 주간거래 시작 사이)에 바뀐다. 같은 세션 묶음 안에서는 놓치지 않는다. 다만 주문이 세션 묶음을 넘어 살아 있으면(§9-11) 놓칠 수 있다.
     - KST 환산은 UTC 오프셋(EDT −4, EST −5, KST +9)과 아래 MTS 시각표로 계산했다.
     - code 0 빈 결과에도 같은 문제가 있지만, 운영에서 `VERIFIED_NONE`이 실제로 나오게 되는 것은 안 B가 처음이다. 900초 신선도 창은 이 문제를 막지 못한다.
   - **사용자 수용 (2026-10-04):** 이 위험을 수용하고 안 B를 진행한다.
   - **운영 규칙 (사용자 결정 2026-10-04, Judge 재확인 조건 A, 코드로 강제하지 않음):** 세 항목이 해소될 때까지, 시간대와 관계없이 SELL READY(`ORDER_INSTRUCTION_READY`인 매도 지시)를 쓰기 전에 키움 미체결·예약주문 내역 화면을 확인한다. 세 항목이 해소되면 규칙을 좁힌다.
     - 세 항목: 후속 관측 (a) `ord_dt` 기준일, §9-10 예약주문, §9-11 주문 유효 기간
   - **변경 이력:**
     - 2026-10-04 처음 정한 규칙: "KST 00:00부터 08:00(애프터마켓 종료)까지 실행에서 나온 SELL READY는 키움 미체결 화면을 확인하기 전에는 쓰지 않는다."
     - 같은 날 Judge 재확인에서 위 규칙으로 바꿨다. 이유: 세 항목이 해소되기 전에는 시간대 한정 규칙이 위험을 다 덮지 못한다(F6). 예를 들어 가설 2의 날짜 경계, 예약주문 누락(§9-10), 세션을 넘는 주문(§9-11)은 KST 00:00~08:00 밖에서도 생긴다.
   - 근거: 사용자가 제공한 키움 MTS 안내 화면의 세션 시각(KST)

     | 세션 | 서머타임 적용 | 서머타임 미적용 |
     |---|---|---|
     | 주간거래 | 09:00~16:45 | 10:00~17:45 |
     | Pre | 17:00~22:30 | 18:00~23:30 |
     | 정규장 | 22:30~05:00 | 23:30~06:00 |
     | 애프터마켓 | 05:00~08:00 | 06:00~08:00 |

     - 애프터마켓은 두 경우 모두 08:00 KST에 끝난다. 이전 규칙의 끝(08:00)은 이 표에서 정했다.
     - 지금 규칙은 시간대를 쓰지 않는다. 이 표는 위 세 가설의 KST 환산 근거이고, 세 항목이 해소된 뒤 규칙을 좁힐 때도 근거로 쓴다.
     - **이 시각들은 MTS 화면에서 읽은 값이다. 키움 공식 공지로 교차 확인하지 못했다.**
   - **후속 관측 항목:**
     - (a) `ord_dt=""`의 "오늘"이 어느 가설인지 확인한다: 가설 1 KST 날짜, 가설 2 미국 동부 달력 날짜, 가설 3 미국 거래 세션 날짜
     - (b) `sell_alowq`(매도가능수량)가 미체결 매도 수량을 빼는지. 뺀다면 이중 매도 위험의 일부를 `AVAILABLE_SHARES_INSUFFICIENT`가 막는 보조 장치가 된다(추론).
5. 실현손익은 표식 기준 운영 관측이 0회다(§2). 주문 게이트에는 닿지 않는다.
6. 시각 의미: `retrieved_at`은 응답 직후 worker 시계로, code 0 빈 결과와 같은 수준이다. "방금 낸 주문 미반영" 위험은 빈 PASS 일반의 위험이며 안 B가 새로 만들지 않는다.
7. audit `READY` 라벨이 바뀐다(체결 AVAILABLE도 필요, §6). 소비자는 없고 주문 권한도 없다.
8. GRADE_B와 dashboard 컴파일 차단 해제(§6)는 여전히 추론이다. 병합 뒤 라이브 1회로 확정한다(fix-design §8).
9. 미체결이 실제로 있을 때의 실응답은 여전히 미확인이다(S1b §3-4).
10. **열린 항목: 접수 전 예약주문이 미체결 조회(ust21050)에 잡히는지 확인이 필요하다.**
    - MTS 안내에 따르면 예약주문은 계좌 상태를 확인하지 않고 임의로 취소될 수 있다.
    - 미체결 조회에 잡히지 않는다면, "미체결 없음 확인"(`VERIFIED_NONE`)이 나와도 예약 매도가 남아 있을 수 있다.
    - 이 누락은 시간대와 관계없다. 언제 실행해도 놓칠 수 있다.
    - 예약주문이 `sell_alowq`(매도가능수량)에서 빠지지 않을 가능성이 있다(추론). 접수 전이라 거래소에 나가지 않은 주문이기 때문이다. 그렇다면 §9-4 (b)의 `AVAILABLE_SHARES_INSUFFICIENT` 보조 장치도 예약 매도의 이중 매도를 막지 못한다.
11. **열린 항목: 키움 주문의 유효 기간(세션이 끝나면 만료되는지)을 확인해야 한다.** 주문이 다음 세션까지 살아 있다면, `ord_dt=""`(오늘) 조회가 전날 낸 미체결을 놓치는 위험(§9-4)이 KST 00:00~08:00 밖에서도 생길 수 있다(추론).

## 10. 사용자 결정과 진행

- **결정 1:** B′(권장, C4 추가) 또는 B(지시 그대로 ③만)
- **결정 2:** C5·C6·C7 추가 조건 채택(권장: 채택)
- **결정 3:** PASS 근거 표식 `pagination.terminated_by` 채택(권장: 채택. 승격 근거가 보고서에 남는다)

**사용자 결정 (2026-10-03):** 결정 1 **B′**, 결정 2 **채택**, 결정 3 **채택**.

순서:

1. 읽기 전용 진단. S1b §7과 같은 방식으로, 스크립트를 먼저 보여 드리고 승인 뒤 실행한다.
   - 호출: ust21050, ust21630 각 1회
   - 출력: `return_code`, 괄호 안 코드의 자릿수와 값(6자리일 때만 값), 최상위 키 이름, continuation의 `cont_yn`·`next_key` 존재 여부와 "더 있음" 여부
   - 메시지 원문, 계좌 값, 토큰은 출력하지 않는다
   - 이 결과로 C4 값을 채우고 C6·C7을 실응답 모양에 대조한다
2. 이 문서에 값을 반영한다.
3. 독립 Judge(별도 세션, 읽기 전용)
4. Builder(새 worktree)
5. 병합 뒤 라이브 수동 분석 1회로 GRADE_B 여부를 확인한다

진행:

- 1단계 완료(2026-10-03): 1차는 이 세션이 실행했다(§11). 2차는 사용자가 실행했다(§12).
- 2단계 완료(2026-10-03): C4 코드는 두 연산 모두 `{"571758"}`(사용자 결정).
- 3단계 완료(2026-10-04): Judge PASS_WITH_CONDITIONS. 조건 1~8과 비차단 권고를 이 개정에 반영했다(§14).
- 3단계 재확인(2026-10-04): Judge 재확인 PASS_WITH_CONDITIONS. 조건 A~C와 F4를 반영했다(§14-2).
- 4단계 완료(2026-10-04): 사용자 승인 뒤 Builder가 구현했다. worktree는 새로 만들지 않고 이 설계를 쓴 `preflight-b`를 그대로 썼다. 아직 커밋하지 않았다. 보고서는 `s1b-plan-b-builder-report-2026-10-04.md`다.
- 구현 Judge(2026-10-04): PASS_WITH_CONDITIONS.
- **다음: 커밋·병합(사용자 지시 대기), 그 뒤 5단계 라이브 수동 분석 1회.**

`open-orders-diagnosis-2026-09-30.md` §5-2에는 이 문서를 가리키는 한 줄을 추가했다(2026-10-03).

## 11. 진단 1차 결과 (2026-10-03, 토요일·개천절)

- 실행: 이 세션이 사용자가 준 해시 확인 명령(`sha256 37fea23b…53b6cc`)으로 운영 런타임 venv에서 1회 실행했다.
  - 런타임 커밋 `69642586f7d8`, 토큰은 메모리에서 발급 성공
  - 호출 2회, 주문 API 없음, 파일 쓰기 없음

| 항목 | ust21050 미체결 | ust21630 실현손익 |
|---|---|---|
| `return_code` | 20 (int) | 20 (int) |
| `[2000]` 시작 | true | true |
| 괄호 안 코드 | 6자리 `571758` | 6자리 `571758` |
| 최상위 키 | `return_code`, `return_msg` | 같음 |
| `result_list` | 키 없음 | 키 없음 |
| continuation | `cont_yn="N"`(있음), `next_key=None`(있음), `has_next=false`(있음) | 같음 |

- **C6·C7은 실응답 모양과 맞는다.** `result_list` 키가 없고 연속 표시는 "끝"이다.
- **fix-design §7-3의 추정 정정:** 실응답은 연속 표시가 모두 있고 서로 일치해서, 미체결 엄격 검사(164-186)를 그대로 통과한다. 그래도 "없음 선언"을 그 앞에서 끝내야 한다는 결론은 같다. 오류 결과는 `_fetch_account_page`에서 이미 예외가 되고, 설령 넘어가도 `result_list`가 None이면 156행에서 `KIWOOM_SCHEMA_MISMATCH`가 되기 때문이다.
- **1차 시점에는 C4 값을 정하지 않았다.** 두 연산의 코드가 같았기 때문이다(`571758`). 9/30 진단에서는 두 메시지 문구가 달랐고, U3에서는 문구가 다르면 코드도 달랐다(501724 / 501058). 그래서 해석이 두 가지로 갈렸다(추론).
  1. 오늘(휴일) 두 조회가 "없음"이 아닌 같은 안내(예: 휴장·조회 불가)를 돌려줬다.
  2. 이 숫자가 문구별 메시지 코드가 아니다.
- → **2차 결과로 해석 1은 기각됐고, 해석 2는 부분 확인됐다(§12).**

## 12. 진단 2차 결과와 C4 확정 (2026-10-03)

- 실행: 2차 스크립트 `diag_s1b_plan_b_message_text.py`(sha256 `d3ced130…ee62d9`). 1차 출력에 코드 뒤 문구를 더한 것이다. 6자리 이상 숫자는 가리고 120자에서 자른다.
- **출처:** 사용자가 실행하고 결과를 이 세션에 전달했다. **이 세션은 원 출력을 직접 보지 못했다.** 아래 표는 사용자 보고를 옮긴 것이다.

| 항목 | ust21050 미체결 | ust21630 실현손익 |
|---|---|---|
| `return_code` | 20 | 20 |
| 메시지 | `[2000](571758:…)` | `[2000](571758:…)` |
| `message_text_masked` (코드 뒤 부분 + 닫는 괄호) | `해당 계좌의미체결내역이 없습니다.)` | `조회내역이 없습니다.)` |
| `result_list` | 키 없음 | 키 없음 |
| continuation | `cont_yn=N`, `next_key` 없음, `has_next=false` | 같음 |

- **해석 1 기각:** 휴일 안내가 아니라 실제 "없음" 응답이다. 문구가 9/30 진단의 문구와 같다.
- **해석 2 부분 확인:** 같은 코드 `571758`이 서로 다른 두 문구에 쓰였다. 그래서 문구별 고유 코드가 아니다. 이 코드가 "없음" 외의 응답에도 쓰이는지는 모른다(§13 ②).
- 두 문구에는 6자리 이상 숫자가 없고 120자보다 짧다. 그래서 마스킹과 자르기가 문구를 바꾸지 않았다. 다만 공백·끝 문자는 사람이 읽어 옮긴 값이다(§9-3).
- **사용자 결정 (2026-10-03):** C4 허용 코드는 두 연산 모두 `{"571758"}`.
- **사용자 결정 (2026-10-04, Judge 조건 1):** C4에 연산별 문구 완전 일치를 AND로 추가한다(C4b). 문구는 위 `message_text_masked`를 그대로 쓴다.
- **사용자 확인 (2026-10-04): 계좌 식별자 일부 아님** (Judge 조건 8).

## 13. 1차 Judge 전달 사항 (기록)

1. **C4 근거 관측은 하루뿐이다.** 2026-10-03(토요일·개천절)에 1차와 2차를 실행했다. 평일과 미국 장중 값은 관측하지 않았다. 9/30 진단의 코드는 마스킹돼 비교할 수 없다. 운영 수동 분석 6건의 코드도 저장되지 않았다(안 A 표식은 `return_code`만 남긴다).
2. **`571758`이 "없음" 외의 다른 조건에도 쓰이는지 미확인이다.** 같은 코드가 서로 다른 두 문구에 쓰였으므로 묶음 코드일 수 있다. 그 묶음에 "없음"이 아닌 응답(예: 조회 불가 시간, 파라미터 오류)이 들어 있으면 fail-open이 남는다.
   - Judge가 이 위험을 중대하다고 보면 고를 수 있는 추가 축소로 연산별 문구 일치를 제시했다. → 조건 1로 채택(§14).
3. 2차 진단의 원 출력은 이 세션이 직접 보지 못했다(사용자 보고, §12).
4. `ord_dt=""`의 기준일(KST인지 미국 거래일인지)을 모른다. 미국 장중 실행 시 미체결을 놓칠 가능성이 있다. → 조건 7로 사용자 수용(§9-4).
5. K3 핵심 효과: 미체결 `VERIFIED_NONE`이 되면 주문 지시가 `ORDER_INSTRUCTION_READY`로 풀릴 수 있다. I0 제안에는 `open_orders_verified=true`가 기록되고, audit에는 `READY`가 나온다(§6). 주문 권한은 계속 없다.
6. 실현손익은 운영 관측(표식 기준)이 0회다. 진단에서만 관측했다(§2, §9-5).
7. 안 A 테스트 20건을 고치지 않는 근거(§3 끝, §7-F)와, 맞바꿈 테스트의 대체안(§7-C)

## 14. Judge 판정과 반영 (2026-10-04)

### 14-1. 1차 판정

- 판정: **PASS_WITH_CONDITIONS** (독립 Judge, 별도 세션).
- 판정 원문은 저장소에 없다. 아래 조건은 사용자가 전달한 요약이다.

| 조건 | 내용 | 결정 | 반영 위치 |
|---|---|---|---|
| 1 | C4에 연산별 문구 완전 일치 추가 | 사용자 결정: AND로 추가. 문구는 `message_text_masked` 그대로. 연산별 표로 두고, 운영 표 고정 테스트에 문구 포함 | §4 C4b, §5-1, §7 B-3·C-2·C-3, §9-3, §12 |
| 2 | C7 정확 정의 (`cont_yn` 없음/None/""/"N", `next_key` 없음/None/"", `has_next` 없음/정확히 False, 그 밖은 승격 안 함) | 반영 | §4 C7, §7 B-6 |
| 3 | 승격 판정 계산은 예외 없음. 표 조회는 `.get`. 어떤 입력에서도 원래 `BridgeError`·상태·안 A 표식 유지 | 반영 | §4 "판정 계산의 안전", §5-2·5-3, §7 B-7 |
| 4 | 정제기 `terminated_by`: 원본 `data`가 빈 list, `type(pages) is int and pages == 1`, 최종 상태 확정 뒤 판정, 표시 전용 명시 | 반영 | §4 승격 결과, §5-5, §7 D-1~4 |
| 5 | 음성 테스트는 양성 픽스처에서 조건 하나만 바꿈, B2 재작성, 빠진 케이스 추가 | 반영 | §7 원칙, A-4, B-2(재작성)·B-3·B-6·B-7, D-1·D-2 |
| 6 | §6에 dashboard:1297-1314 컴파일 차단 해제 경로. audit READY는 fills AVAILABLE도 필요. §3 U3 설명을 부분문자열 판정으로 정정 | 반영 | §6, §3, §9-7·9-8 |
| 7 | `ord_dt` 기준일 위험 | 사용자 수용(2026-10-04). 운영 규칙(재확인 조건 A로 갱신): 세 항목(`ord_dt` 기준일, 예약주문, 주문 유효 기간)이 해소될 때까지 시간대와 관계없이 SELL READY를 쓰기 전에 키움 미체결·예약주문 내역 화면을 확인하고, 해소되면 좁힌다. 처음 정한 KST 00:00~08:00 규칙은 변경 이력으로 남겼다(F6). 열린 항목 2개 추가 | §9-4, §9-10·9-11 |
| 8 | `571758`이 계좌번호 일부인지 | 사용자 확인(2026-10-04): 계좌 식별자 일부 아님 | §12 |
| 권고 | C6를 최상위 키 부분집합으로 좁히기(비차단) | **채택** | §4 C6, §7 B-5 |

권고를 채택한 이유:

- 두 차례 진단의 실응답 모양(키 두 개)과 정확히 맞는다.
- 행이나 다른 데이터를 실을 수 있는 미지의 키가 있는 응답을 승격하지 않는다.
- 같은 쪽(fail-closed)으로 좁히는 변경이라, 키가 늘어나도 결과는 지금처럼 FAIL이다.
- "같음"이 아니라 "부분집합"으로 적었기 때문에, `return_code` 키를 빼는 음성 테스트를 C2 하나만 깨는 입력으로 만들 수 있다. `return_msg`를 빼면 C3·C4a·C4b가 함께 깨진다(§7 B-2).

### 14-2. 재확인 판정

- 판정: **PASS_WITH_CONDITIONS** (Judge 재확인, 별도 세션).
- 판정 원문은 저장소에 없다. 아래 조건은 사용자가 전달한 요약이다.

| 조건 | 내용 | 결정 | 반영 위치 |
|---|---|---|---|
| A | 운영 규칙을 시간대 한정에서 "세 항목 해소 전까지 시간대와 관계없이 확인"으로 넓히기 | 사용자 결정: 권장안 채택 | §9-4 운영 규칙·변경 이력(F6)·MTS 시각표 유지, §9-10 추가 두 줄, §9-11 문구, §14-1 조건 7 행 |
| B | 테스트 계획 보정 | 반영 | §7 B-2(C3는 C4a·C4b와 함께 깨짐), B-3(닫는 전각 괄호로 한정), B-6·B-7(해시 불가 `cont_yn`: list, dict), A-1·A-2(pagination dict 전체를 정확한 값으로 단언) |
| C | "오늘" 해석을 세 가설로 나누기 | 반영 | §9-4 위험(가설 1~3), 후속 관측 (a) |
| F4 | 조기 return 시점의 `pages=0` 주의 | 반영 | §5-3 구현 주의 |
