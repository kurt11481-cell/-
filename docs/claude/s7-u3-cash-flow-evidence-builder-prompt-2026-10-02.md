# S7 U3 거래내역 증거 보정 Builder 지시문 — 빈 기간과 분할·병합 행 처리 (2026-10-02, K2)

- 목적: U3 실측(`s7-u3-transaction-history-measurement-2026-10-02.md`)에서 나온 막힘 3건을 고친다.
  - B1: 거래가 없는 기간의 키움 응답(501724)이 `CASH_FLOW_EVIDENCE_RAW_SHAPE_INVALID`로 실패한다. 이 계좌는 거래가 드물어 대조 간격 대부분이 빈 기간이다.
  - B2: `병합단주대금입금(외화)`가 외부 입금(DEPOSIT)으로 분류된다.
  - B3: `액면병합출고`·`액면분할병합입고/출고`(입출고)가 UNCLASSIFIED로 멈춘다.
- 사용자 결정(2026-10-02): 실측 문서 6절 권장안 승인.
  - 501724 빈 응답만 "행 0개"로 받고, 다른 오류는 지금처럼 실패한다.
  - 외부 흐름이 아닌 분류 `CORPORATE_ACTION`(낱말 `액면`, `단주대금`)을 더한다. `타사대체입고` 같은 다른 입출고는 그대로 멈춘다.
- 성격: K2. 이미 승인된 R6 규칙(배당·수수료·세금·이자는 외부 흐름 아님, 모르는 줄은 멈춤)을 실측 문자열에 맞추는 일이다.
  - 정책·상태·원장·journal은 바꾸지 않는다. 외부 흐름 판정(DEPOSIT·WITHDRAWAL·FX만 외부)은 바꾸지 않는다.
  - 별도 Judge는 없다. Cowork가 diff·테스트·실측 문자열 재현으로 확인한다.
  - `order_authority=false`, `quantity_authority=none`, `execution_quantity=null`을 유지한다.
- 상태: 작성 완료, Builder 미실행.

## 1. 사용자 조작 (Windows 터미널)

**[Claude Code 실행 권장] 모델: Sonnet · 추론 노력: high · 세션: 새 worktree `s7-cashflow` · 이유: 증거 정규화 코드·스키마·낱말표를 함께 고치는 작은 K2이고 설계는 확정됨**

1. 새 Windows 터미널에서 입력: `cd "E:\사업\##금동한\코덱스저장소"`
2. 이 지시문과 실측 기록을 커밋한다(worktree는 커밋된 HEAD에서 만들어진다).
   `git add docs/claude/s7-u3-cash-flow-evidence-builder-prompt-2026-10-02.md docs/claude/s7-u3-transaction-history-measurement-2026-10-02.md docs/claude/s7-builder-report-2026-10-01.md`
   `git commit -m "docs: S7 U3 measurement and cash-flow evidence builder prompt"`
3. `claude --worktree s7-cashflow`
4. 세션 안에서 `/model`로 Sonnet, `/effort`로 high를 고른다.
5. 아래 한 줄을 붙여 넣는다.
   `docs/claude/s7-u3-cash-flow-evidence-builder-prompt-2026-10-02.md 3절 상자 안의 지시를 그대로 따르는 Builder로 일해라. 그 밖의 절은 참고만 한다.`
6. 권한 확인 창이 뜨면 다음 기준으로 고른다.
   - 허용: 파일 읽기, `git status`/`log`/`diff`/`show`, python 테스트·해시 계산, worktree 안 파일 쓰기.
   - 거부: 키움 도구 전부, 네트워크, `.env` 읽기, worktree 밖 파일 쓰기, `reconcile_broker_state.py apply`, `portfolio_review_journal.py apply`, 커밋·push·merge.
7. 끝나면 Cowork에 "Builder 완료, worktree s7-cashflow, 새 실패 수 N"만 보낸다.

## 2. Cowork 사전 확인 (2026-10-02, 읽기 전용)

| # | 사실 | 근거 |
|---|---|---|
| C1 | **빈 기간 응답**: `{"return_msg": "[2000](501724:관련자료가 없습니다)", "return_code": 20}`. `result_list`·`acnt_print`가 없다. MCP로 받으면 `{"result": {...}}`로 한 번 감싸진다 | 2026-09-25~09-29 `all` 실측 |
| C2 | **1년 초과 기간**: `{"return_msg": "[2000](501058:조회기간은 1년 이내로만 가능합니다.)", "return_code": 20}` | 실측 |
| C3 | 지금 코드는 `result_list` 검사(123행)가 `return_code` 검사(125행)보다 먼저라 C1이 `RAW_SHAPE_INVALID`가 된다. 기존 테스트 `test_malformed_raw_files_are_rejected`는 "행 있음 + return_code 20(메시지 없음) → `RETURN_CODE_NOT_ZERO`"와 "`{"result": {}}` → `RAW_SHAPE_INVALID`"를 단언한다. 둘 다 유지해야 한다 | `scripts/cash_flow_evidence.py`, `tests/test_cash_flow_evidence.py` |
| C4 | 실측 문자열과 지금 분류: `입출금`/`배당금(외화)입금` → DIVIDEND, `입출금`/`병합단주대금입금(외화)` → **DEPOSIT(+)**, `입출고`/`액면병합출고`·`액면분할병합입고`·`액면분할병합출고` → **UNCLASSIFIED**, `매매`/`매수`·`매도` → TRADE. 관측 행의 `crnc_code`는 전부 USD | 실측 문서 3절, `classify_row` 직접 호출 |
| C5 | 2026-08-25~09-29에 매매·입출금·입출고·환전 행이 하나도 없었다. 빈 응답이 예외가 아니라 평소 모습이다 | 실측 |
| C6 | 고칠 곳: `NON_EXTERNAL_CLASSES`(38행), `normalize_transaction_history`의 응답 검사(121~126행), 증거 스키마 `classification` enum(47행), 낱말표 규칙 목록. 신고 블록 스키마의 외부 행 enum은 DEPOSIT·WITHDRAWAL·FX뿐이라 바꿀 필요가 없다 | 코드·스키마 |
| C7 | `tests/test_portfolio_exposure_judge_fixes.py`의 `FixFClassificationTests`가 `이체입금` → DEPOSIT, `이체출금` → WITHDRAWAL, `타사대체입고`(입출고) → UNCLASSIFIED, 수수료·이용료 줄 → FEE_TAX_INTEREST를 고정한다. 새 규칙이 이것을 바꾸면 안 된다 | 테스트 |
| C8 | 줄바꿈: `cash_flow_evidence.py`, `tests/test_cash_flow_evidence.py`, `schemas/kiwoom-cash-flow-evidence.schema.json`, `assets/kiwoom-transaction-history-classification.json`, `references/portfolio-exposure-review.md`는 모두 CRLF, bare LF 0, BOM 없음 | `file`, 바이트 검사 |

## 3. Builder 지시 (이 상자만 따른다)

```
역할: 투자_V2 Builder (K2). 범위 = 거래내역 증거 정규화가 빈 기간(키움 501724)과 분할·병합 행을 처리하게 하기.
주문·수량 권한 없음. 키움 도구 호출 금지. 네트워크 금지. 비밀(.env*, 토큰, 계좌번호) 읽기 금지.

바꿔도 되는 파일(이것만, 모두 manage-us-stock-strategy/ 아래):
- scripts/cash_flow_evidence.py (응답 검사 분기, NON_EXTERNAL_CLASSES, 주석)
- schemas/kiwoom-cash-flow-evidence.schema.json (classification enum에 "CORPORATE_ACTION" 추가만)
- assets/kiwoom-transaction-history-classification.json (규칙 1개 추가, purpose·status 문구)
- 새 tests/test_cash_flow_evidence_u3.py
- references/portfolio-exposure-review.md ("Cash-flow declaration (R6)" 절에 두 줄, K0)
- 새 docs/claude/s7-u3-cash-flow-evidence-builder-report-2026-10-02.md (보고, 저장소 루트 기준 경로)
그 밖의 파일은 고치지 않는다. 특히 기존 테스트 파일 전부, schemas/cash-flow-declaration.schema.json,
reconcile_broker_state.py, kiwoom_broker_shadow.py, apply_user_confirmed_broker_snapshot.py, portfolio_exposure.py,
alert_policy.json, workspace/policies/*, 상태·원장·journal, 키움 고정 16개, deployment_gate 고정 6개.
목록 밖을 바꿔야 하면 멈추고 묻는다.

요구:
R1 빈 응답: 응답 본문(감싼 경우 "result" 안)이 dict이고, return_code가 정수 20이며, return_msg 문자열에
   "501724:"가 들어 있을 때만 "행 0개" 증거로 정규화한다.
   - 이때 result_list는 없거나 빈 list여야 한다. 행이 있으면 CASH_FLOW_EVIDENCE_EMPTY_RESPONSE_HAS_ROWS로 실패한다.
   - 결과는 기존 스키마 그대로다: row_count 0, rows [], unresolved [], totals 전부 "0.00",
     account_identifier_stored false. schema_version·source 필드는 바꾸지 않는다.
   - 기간 검사(PERIOD_INVALID)는 빈 응답에도 똑같이 한다.
   - 이 분기는 기존 검사 앞에 둔다. 그 밖의 검사 순서와 오류 코드는 바꾸지 않는다.
     그래서 501058, 메시지 없는 20, 다른 0 아닌 코드는 지금처럼 RETURN_CODE_NOT_ZERO 또는 RAW_SHAPE_INVALID로 실패한다.
R2 낱말표: 아래 규칙 하나를 FEE_TAX_INTEREST 바로 다음, FX 앞에 넣는다.
   {"classification": "CORPORATE_ACTION", "fields": ["deal_kind_nm", "rmrk_nm"], "match_any": ["액면", "단주대금"]}
   다른 규칙의 낱말·순서·필드는 바꾸지 않는다. rule_order(first_match_wins)도 그대로다.
   purpose 문장에 "corporate-action rows (par-value split/merge transfers and fractional-share cash) are not external
   cash flows"를 더한다. status는 "dividend_trade_split_and_fractional_cash_strings_verified_2026_10_02_transfer_and_fx_strings_unobserved"로 바꾼다.
R3 코드: NON_EXTERNAL_CLASSES에 "CORPORATE_ACTION"을 더한다. classify_row의 흐름은 바꾸지 않는다(비외부 분류는 (분류, None)).
   CORPORATE_ACTION 행의 금액은 어떤 합계(external_net, dividend_settlement, fees, taxes)에도 새로 넣지 않는다.
   단, fees_usd·taxes_usd는 지금처럼 USD 행 전체의 수수료·세금 필드 합이다(무변경).
R4 외부 흐름 판정 무변경: DEPOSIT·WITHDRAWAL·FX만 외부다. 타사대체입고·타사대체출고 같은 다른 입출고는 UNCLASSIFIED로 남는다.
R5 문서(K0) references/portfolio-exposure-review.md의 "Cash-flow declaration (R6)" 2번 항목 뒤에 두 줄:
   - A Kiwoom "no data" response (message code 501724) is normalized as evidence with zero rows; any other non-zero
     return code still fails.
   - Par-value split/merge transfer rows and fractional-share cash rows (CORPORATE_ACTION) are not external flows.
     Quantity changes from splits are handled by the split record (corporate-actions.json) and the broker reconciliation.
R6 줄바꿈: 기존 파일의 CRLF를 유지하고 BOM은 넣지 않는다. 일괄 변환 금지. 새 .py 파일도 CRLF로 만든다.

단계:
0. 기준선: git status와 HEAD를 확인한다(HEAD가 이 지시문 커밋이 아니면 멈춘다). 바꿀 기존 파일의 원시 sha256을 기록한다.
   전체 테스트를 서브에이전트로 1회 돌리고, 실패·오류 ID만 파일로 남긴다:
   python -m unittest discover -s manage-us-stock-strategy/tests
1. 테스트를 먼저 쓴다(새 파일 test_cash_flow_evidence_u3.py). 문자열은 실측 값을 쓰고, 금액·계좌는 가짜(TEST_ONLY)만 쓴다.
   T1 실측 문자열 분류(load_classification 실제 표):
      입출금/배당금(외화)입금 → DIVIDEND, 입출금/병합단주대금입금(외화) → CORPORATE_ACTION,
      입출고/액면병합출고·액면분할병합입고·액면분할병합출고 → CORPORATE_ACTION, 매매/매수·매도 → TRADE
   T2 위 7행(같은 날 deal_no 1~7, crnc_code USD)으로 만든 증거: unresolved [], external_net_usd "0.00",
      evidence_errors [], build_declaration(declared_usd=None) → NO_EXTERNAL_FLOW
   T3 빈 응답 두 형태(감싼 것 {"result": {...}}와 안 감싼 것): row_count 0, rows [], 스키마 통과,
      build_declaration → NO_EXTERNAL_FLOW, 결과 JSON에 "acnt_print" 없음
   T4 실패 유지: 501058 메시지 → RETURN_CODE_NOT_ZERO 또는 RAW_SHAPE_INVALID(지금 규칙대로, 코드 이름을 단언),
      return_code 20 + 501724가 없는 메시지 → 실패, 501724인데 result_list에 행 1개 → EMPTY_RESPONSE_HAS_ROWS,
      return_code 0인데 result_list 없음 → RAW_SHAPE_INVALID, 빈 응답 + from>to → PERIOD_INVALID
   T5 회귀: 입출고/타사대체입고·타사대체출고 → UNCLASSIFIED, 입출금/이체입금 → DEPOSIT(+1),
      환전/환전매수 → FX(+1), 입출금/수수료출금 → FEE_TAX_INTEREST
   T6 빈 증거의 신고 블록으로 cash_flow_chain: 적용 시작 뒤 대조 1건, 기간이 연속이고 as_of까지 닿으면 CLEAR,
      adjustments 없음, covered_through = period_to
   T7 normalize CLI: 빈 응답 원문 파일 → 종료 코드 0, 출력 row_count 0, 결과 파일 스키마 통과
   고치기 전 코드에서의 실패 수를 보고에 적는다.
2. 구현한 뒤 대상 테스트를 파일마다 -p로 돌린다: test_cash_flow_evidence_u3.py, test_cash_flow_evidence.py,
   test_portfolio_exposure_judge_fixes.py, test_portfolio_exposure_fail_closed.py, test_reconcile_broker_state.py,
   test_run_portfolio_exposure_review.py.
   스키마 감사: python manage-us-stock-strategy/scripts/validate_schema_contracts.py
3. 전체 테스트를 서브에이전트로 1회 돌리고, 0단계 목록과 비교해 "새 실패"만 보고한다(목표 0).
4. 보고 파일에 적는다: 바꾼 파일과 diff --stat, 파일별 원시 sha256 전후, 줄바꿈 확인, 테스트 결과,
   낱말표 canonical hash 전후(증거의 classification_table_sha256이 바뀐다는 사실), 남은 문제. 커밋하지 않는다.
```

## 4. 이번 범위 밖 (기록만)

- 실제 입금·출금·환전 문자열: 21개월 동안 실제 행이 없어 잴 수 없었다. 처음 생기면 U3를 다시 잰다. 그때까지 FX·TRANSFER 규칙은 추정이고, 맞지 않으면 fail-closed로 멈춘다.
- 원문 저장 방법: 증거 절차는 Windows에서 `kiwoomcli ... --format json > 파일`로 원문을 저장하는 쪽이 될 것이다. 빈 기간일 때 CLI 종료 코드와 stdout 형태는 **확인 필요**다. 병합 뒤 Cowork가 사용자와 한 번 시험한다.
- 연속조회 완전성(U4), 9/30에 빠진 `deal_no` 1번의 정체.
- `deal_dt`가 결제 반영일 성격이라는 점: 매매 행은 외부 흐름이 아니라서 이번 범위에는 영향이 없다.

## 5. 병합 뒤 Cowork 할 일

1. 원본 폴더 코드로 실측 문자열 7종과 빈 응답(감싼 것·안 감싼 것)을 다시 돌려 본다(결과는 VM 임시 폴더, 금액 없음).
2. 사용자와 빈 기간 1회로 원문 저장 절차를 시험한다(Windows 터미널, 읽기 전용 명령). 원문은 정규화 뒤 지운다.
3. S7 보고 U3·5.4-4, 실측 문서와 이 문서의 진행 기록을 갱신한다. 다음은 5.4-5 브로커 대조다.

## 6. 진행 기록

- 2026-10-02 Cowork: U3 실측(막힘 3건). 사용자가 권장안을 승인해 이 지시문을 작성했다.
- 2026-10-02 Builder 완료(worktree `s7-cashflow`, 기준 `dcc17e9`, 새 실패 0, 보고 `s7-u3-cash-flow-evidence-builder-report-2026-10-02.md`). Cowork 확인: 바꾼 파일은 허용 목록 안 6개(기존 4·새 2), 금지 파일 무변경, 6개 모두 CRLF·bare LF 0·BOM 없음. diff 검토: 501724 분기는 정수 20 + 문자열 `501724:`일 때만, 그 밖의 검사 순서·오류 코드 그대로, 규칙은 FEE_TAX_INTEREST 다음·FX 앞. VM 대상 테스트: u3 18·cash_flow 19·judge_fixes 29·fail_closed 32·run_review 22 OK, reconcile 56 중 1건 실패는 VM에서 worktree git을 못 쓰는 환경 문제(`git check-ignore` 테스트, 원본 폴더에서는 56 OK, Builder 보고도 OK). 스키마 감사 PASS. 실측 문자열 재현: 단주대금·액면 3종 → CORPORATE_ACTION, 배당·매매 그대로, 타사대체입고 UNCLASSIFIED, 이체입금 DEPOSIT. 실측 빈 응답(감싼 것·안 감싼 것) → 0행·NO_EXTERNAL_FLOW, 501058 → RAW_SHAPE_INVALID(실패 유지). 낱말표 해시 `c176f347…` → `ea2c156b…`. 다음: 사용자 커밋·병합.
- 2026-10-02 사용자 커밋 `6ca8731`, 병합 `23823f4`. Cowork 원본 폴더 확인: 파일 해시가 Builder 보고 '후' 값과 같음, 대상 테스트 u3 18·cash_flow 19·judge_fixes 29·reconcile 56 OK, 실측 문자열 7종·빈 응답 재현 OK(낱말표 해시 `ea2c156b…`). 다음: 빈 기간·행 있는 기간 각 1회로 Windows 원문 저장 절차 시험(5절 2번).
- 2026-10-02 Windows 원문 저장 시험(사용자 실행, 조회 전용): 빈 기간 9/25~9/29와 9/30~10/2 각 1회, 둘 다 종료 코드 0. CLI 원문은 감싸지 않은 JSON 한 줄(UTF-8, BOM 없음, 끝 CRLF)이다. 빈 기간은 `{"return_msg": "[2000](501724:관련자료가 없습니다)", "return_code": 20}`. Cowork가 원본 폴더 코드로 normalize(결과는 VM 임시 폴더, 확인 뒤 삭제): 빈 기간 0행·OK, 9/30 배당 1행 DIVIDEND, 둘 다 스키마 통과·NO_EXTERNAL_FLOW, 결과에 계좌 표시·이름 없음. 확정 절차: PowerShell에서 `$env:PYTHONIOENCODING = 'utf-8'` 뒤 `cmd /c "kiwoomcli overseas accounts transaction-history --from YYYYMMDD --to YYYYMMDD --kind all --pages 0 --format json > workspace\private_inputs\cash_flow_evidence\raw_<기간>.json"`(PowerShell의 `>`는 UTF-16으로 저장하므로 쓰지 않는다). 폴더는 git 제외. 기간은 1년 이내. 원문은 정규화 뒤 지운다. U3 남은 일: 첫 실제 입출금·환전 행이 생기면 다시 잰다.
