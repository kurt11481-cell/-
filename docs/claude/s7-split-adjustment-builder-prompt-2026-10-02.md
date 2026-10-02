# S7 분할 보정 Builder 지시문 — 공식 분할 기록으로 V와 고점 점검을 분할 보정 종가로 계산 (2026-10-02, K2)

- 목적: 노출 점검이 `V_UNAVAILABLE:SPLIT_GUARD:MVLL:2026-06-26`으로 멈춘 것을 푼다. 정책에 이미 정해진 `sox_equivalent.return_basis = split_adjusted_regular_session_close`와 `technical_price_basis_required = split_adjusted_ohlc_rescaled_to_latest_raw_close`대로 분할 보정 종가를 쓰게 한다. 지금 코드는 원주가만 받고, 하루 비율이 0.5 이하이거나 2.0 이상이면 계산을 멈춘다(S7 보고 U5).
- 사용자 결정(2026-10-02): A안.
  - Cowork가 공식 근거를 붙인 분할 기록 파일을 만든다. 계산할 때 분할 이전 종가를 보정하고, 원시 이력 파일은 그대로 둔다.
  - V와 −30% 고점 점검에 같은 보정을 쓴다. 보정한 뒤에도 급변이 남으면 SPLIT_GUARD로 멈춘다.
  - 3:2 같은 작은 분할은 수집 루틴에서 Cowork가 키움 수정 표시를 확인한다. 코드가 대조하는 A+안은 고르지 않았다.
- 성격: K2. 이미 승인된 정책 기준을 런타임 입력 계약으로 구현하는 일이다.
  - 정책·상태·원장·journal은 바꾸지 않는다.
  - 별도 Judge는 없다. Cowork가 diff·테스트·실데이터 실행으로 확인한다.
  - `order_authority=false`, `quantity_authority=none`, `execution_quantity=null`을 유지한다.
- 상태: 작성 완료, Builder 미실행.

## 1. 사용자 조작 (Windows 터미널)

**[Claude Code 실행 권장] 모델: Sonnet · 추론 노력: high · 세션: 새 worktree `s7-split` · 이유: 새 모듈과 스키마, 계산 경로 2개(V·고점), 자산 경로 보호를 함께 고치는 K2이고 설계는 확정됨**

1. 새 Windows 터미널에서 입력: `cd "E:\사업\##금동한\코덱스저장소"`
2. 이 지시문과 진행 기록을 커밋한다(worktree는 커밋된 HEAD에서 만들어진다).
   `git add docs/claude/s7-split-adjustment-builder-prompt-2026-10-02.md docs/claude/s7-builder-report-2026-10-01.md docs/claude/s7-cli-page-shape-builder-prompt-2026-10-02.md`
   `git commit -m "docs: S7 split adjustment builder prompt"`
3. `claude --worktree s7-split`
4. 세션 안에서 `/model`로 Sonnet, `/effort`로 high를 고른다.
5. 아래 한 줄을 붙여 넣는다.
   `docs/claude/s7-split-adjustment-builder-prompt-2026-10-02.md 3절 상자 안의 지시를 그대로 따르는 Builder로 일해라. 그 밖의 절은 참고만 한다.`
6. 권한 확인 창이 뜨면 다음 기준으로 고른다.
   - 허용: 파일 읽기, `git status`/`log`/`diff`/`show`, python 테스트·해시 계산, worktree 안 파일 쓰기.
   - 거부: 키움 도구 전부, 네트워크, `.env` 읽기, worktree 밖 파일 쓰기, `reconcile_broker_state.py apply`, `portfolio_review_journal.py apply`, 커밋·push·merge.
7. 끝나면 Cowork에 "Builder 완료, worktree s7-split, 새 실패 수 N"만 보낸다.

## 2. Cowork 사전 확인 (2026-10-02, 읽기 전용)

| # | 사실 | 근거 |
|---|---|---|
| C1 | **분할 사실**: GraniteShares가 2026-06-12에 낸 보도자료 "GraniteShares Announces Forward Splits"에 MVLL **3 for 1**이 있다. 기준일은 6/24 장 마감, 지급은 6/25 장 마감 뒤이고, 6/26 개장 전부터 분할 뒤 가격으로 거래했다. 같은 날짜의 설명서 보충 문서도 내용이 같다 | https://graniteshares.com/press/graniteshares-announces-forward-splits/ , https://graniteshares.com/media/t5cbormv/grsh-etf-trust-20260612-fwd-split-supplement.pdf |
| C2 | **키움 수정주가 일봉**(`usa06012`, adjusted=1, 조회 전용): MVLL 20260626 행은 `upd_stkpc_tp "3231"`, `upd_rt "-66.66700"`이고, 그 이전 행은 1/3로 보정돼 있다. 2025-12-15~2026-10-01 SOXX·SOXL·NBIS·MVLL 각 200행 가운데 표시가 있는 행은 이것 하나다(쪽 끝 `"1f"` 제외). 분기 배당 시기에도 표시가 없었다. 관찰한 결과이고, 공식 의미는 확인 필요 | Cowork 조회 |
| C3 | 30분봉 원시 쪽 파일(`usa06011`)에는 분할일에도 `upd_stkpc_tp`·`upd_rt` 표시가 없다(MVLL 6/25·6/26 행 모두 빈 값). 원시 쪽 파일만으로는 분할을 알 수 없다 | `pages/MVLL/*.json` |
| C4 | 원시 15:30 봉 종가는 6/25 155.9500 → 6/26 46.3300(비율 0.2971)이다. 3으로 보정하면 −10.88%다. 같은 날 MRVL 일봉은 281.26 → 266.77(−5.15%)이고, 2배인 −10.3%와 맞는다 | 이력 파일, 키움 일봉 |
| C5 | 6/5 MVLL −33.3%(비율 0.6668)는 분할이 아니다. MRVL이 316.43 → 263.47(−16.7%)였고, 키움 표시도 없다. 0.5/2.0 감시로는 이런 날과 3:2 분할을 구별할 수 없다. 이 빈틈(U5)은 루틴 확인으로 메운다 | 같음 |
| C6 | `portfolio_exposure.py`에서 종가를 쓰는 곳: `ExposureModel`→`daily_returns`(V, SPLIT_GUARD 214행), `evaluate_peak_reviews`(680·709행), `closing_equity`(345행. review lines 493행, `activation_candidate` 608행, 현재 자산 961행에서 호출), 포지션 표시 close(1154행), 기준 상품 종가 존재 확인(964행). 자산은 그 세션 스냅샷 수량 × 원주가라서 보정하면 틀린다. 그래서 자산은 원주가를 유지한다 | 코드 |
| C7 | 참고 계산(정식 실행 아님. 수량 MVLL 396·SOXL 75·NBIS 13, 10/1 종가): 보정한 V는 약 2.91(수익률 126개)이다. 원주가로는 V가 약 3.10이고 SPLIT_GUARD가 걸린다. 6/26 이후만 쓰면 V는 약 2.93(수익률 67개)이다. N은 약 2.29다 | VM 계산 |
| C8 | 줄바꿈: `portfolio_exposure.py`·`run_portfolio_exposure_review.py`·`tests/test_portfolio_exposure*.py`·`schemas/portfolio-exposure-review.schema.json`·`references/portfolio-exposure-review.md`는 모두 CRLF다. 키움 고정 파일 목록에는 없다 | `file`, pin 진단 문서 |
| C9 | 리뷰 스키마의 `inputs`에는 속성 제한이 없다(properties·additionalProperties 미지정). `validate_schema_contracts.py`는 `schemas/*.schema.json`을 폴더째 검사하므로 따로 등록할 필요가 없다 | 스키마, 스크립트 |

## 3. Builder 지시 (이 상자만 따른다)

```
역할: 투자_V2 Builder (K2). 범위 = 공식 분할 기록 파일을 읽어 V와 −30% 고점 점검을 분할 보정 종가로 계산하기.
주문·수량 권한 없음. 키움 도구 호출 금지. 네트워크 금지. 비밀(.env*, 토큰, 계좌번호) 읽기 금지.

바꿔도 되는 파일(이것만):
- 새 manage-us-stock-strategy/scripts/corporate_actions.py (순수 함수: 검증·보정. 파일·시계·네트워크 접근 없음)
- 새 manage-us-stock-strategy/schemas/corporate-actions.schema.json
- manage-us-stock-strategy/scripts/portfolio_exposure.py (build_exposure_review 입력 추가, V·고점 경로 연결, 자산 경로 보호, 주석)
- manage-us-stock-strategy/scripts/run_portfolio_exposure_review.py (기록 파일 읽기, inputs 기록, 읽기 전용 감시 목록)
- manage-us-stock-strategy/schemas/portfolio-exposure-review.schema.json (필요할 때만)
- 새 manage-us-stock-strategy/tests/test_corporate_actions.py, 기존 tests/test_portfolio_exposure*.py·test_run_portfolio_exposure_review.py
  (새 테스트 추가만, 기존 단언 변경 금지)
- manage-us-stock-strategy/references/portfolio-exposure-review.md ("분할 기록" 절 추가와 Routine 한 단계, K0)
- 새 docs/claude/s7-split-adjustment-builder-report-2026-10-02.md (보고)
그 밖의 파일은 고치지 않는다. 특히 regular_session_close_history.py와 그 스키마, 이력·쪽 파일, alert_policy.json,
workspace/policies/*, 상태·원장·journal, 키움 고정 16개, deployment_gate 고정 6개, 기존 픽스처 파일.
목록 밖을 바꿔야 하면 멈추고 묻는다.
값 고정: SPLIT_GUARD_LOW 0.5·HIGH 2.0, V 창 252·최소 60을 포함한 정책 값과 연산자는 바꾸지 않는다.

기록 파일 계약:
- 위치: <closes_root>/corporate-actions.json (기본 workspace/outputs/regular-session-closes/corporate-actions.json).
  명령줄 옵션은 새로 만들지 않는다(--closes-root를 따른다).
- 형태(키는 정확히 아래와 같고, 추가 키는 거부):
  {"schema_version": "corporate-actions-1.0", "artifact_type": "CORPORATE_ACTIONS",
   "actions": [{"symbol": "MVLL", "action_type": "SPLIT", "effective_session": "2026-06-26",
     "new_shares": 3, "old_shares": 1,
     "official_source": {"issuer": "GraniteShares", "url": "https://...", "published_date": "2026-06-12"},
     "kiwoom_crosscheck": {"api_id": "usa06012", "adjusted": "1", "dt": "20260626",
                           "upd_stkpc_tp": "3231", "upd_rt": "-66.66700"},
     "recorded_by": "cowork", "recorded_at": "2026-10-02"}]}
  effective_session = 분할 뒤 가격으로 거래한 첫 세션.
  new_shares/old_shares = 옛 old_shares주가 새 new_shares주가 된다(정분할 3:1이면 3/1, 병합 1:10이면 1/10).
- 검증(하나라도 틀리면 파일 전체가 INVALID):
  V1 JSON·스키마 통과. actions는 list(빈 list 허용). symbol 형식은 regular_session_close_history.SYMBOL과 같다.
  V2 action_type은 "SPLIT"만 받는다. new_shares·old_shares는 1 이상의 정수이고 서로 다르다.
  V3 (symbol, effective_session) 중복 금지. effective_session은 이번 실행 달력의 세션이어야 한다(달력 밖이면 INVALID).
  V4 kiwoom_crosscheck.dt는 effective_session과 같은 날(YYYYMMDD)이다. upd_stkpc_tp는 비어 있지 않고 "1f"가 아니다
     (값의 의미는 해석하지 않는다). Decimal(upd_rt)와 (old_shares/new_shares − 1)×100의 차이는 0.005 이하다.
  V5 official_source.url은 "https://"로 시작한다. published_date ≤ effective_session.
- 파일이 없으면 MISSING: 보정 없이 지금과 같게 동작한다(SPLIT_GUARD가 잡는다).

요구:
R1 보정 방식(뒤쪽 보정, 최신 원주가 기준): 기록마다 effective_session보다 앞선 세션의 종가에 old_shares/new_shares를 곱한다.
   기록이 여러 개면 곱을 누적한다. Decimal로 계산한다. 원래 closes 딕셔너리는 바꾸지 않고 새 딕셔너리를 만든다.
R2 보정 종가는 두 곳에만 쓴다: (a) ExposureModel의 V 수익률(common_window·daily_returns), (b) evaluate_peak_reviews.
   그 밖에는 모두 원주가를 그대로 쓴다: closing_equity(review lines, activation_candidate, 현재 자산),
   포지션 표시 close, 기준 상품 종가 존재 확인.
R3 SPLIT_GUARD는 보정 종가에 그대로 적용한다(값·연산자 무변경). 날짜나 비율이 틀린 기록이면 보정 뒤에도 급변이 남아 멈춘다.
R4 INVALID일 때: V는 계산 불가(사유 CORPORATE_ACTIONS_INVALID, 기존 V_UNAVAILABLE:<사유> 표기 그대로).
   고점 점검은 각 종목 UNVERIFIED(사유 같음). 자산과 선 계산은 원주가를 쓰므로 영향이 없다.
R5 자산 경로 보호(수량 추정 금지): VALID 기록이 있는 종목을 보유한 스냅샷의 as_of가 effective_session보다 앞서는데,
   그 스냅샷으로 effective_session 이후 세션의 자산을 계산하게 되면 그 세션의 자산을 미확인으로 둔다.
   처리는 기존 종가 누락과 같은 방식으로 하고, 사유는 "SPLIT_RECONCILIATION_REQUIRED:<SYMBOL>:<effective_session>"이다.
   분할 비율로 수량을 고치지 않는다. 실데이터에서 지금 결과가 바뀌는지 보고에 적는다(스냅샷이 9/30 이후라 안 바뀔 것으로 예상).
R6 출력: review["inputs"]["corporate_actions"] =
   {"status": "MISSING"|"OK"|"INVALID", "sha256": 원시 바이트 sha256 또는 null, "errors": [...],
    "applied": [{"symbol", "effective_session", "new_shares", "old_shares", "price_factor"(문자열)}]}.
   리뷰 스키마 검증을 통과해야 한다. 한 줄 표시(render_exposure_line)와 display block은 바꾸지 않는다.
R7 읽기 전용: 기록 파일을 watched 목록에 넣는다(실행 중 바뀌면 READ_ONLY_INPUT_MUTATION_DETECTED).
   기록 파일을 쓰거나 고치는 코드는 만들지 않는다.
R8 문서(K0) references/portfolio-exposure-review.md:
   - "분할 기록" 절: 파일 위치·형태·검증 규칙. 보정은 V와 고점 점검에만 쓰고 자산은 원주가를 쓴다.
     기록 추가는 Cowork 대화에서만 한다. 공식 발행사 자료와 키움 수정 표시, 두 근거가 모두 있어야 한다. 예약 작업은 기록하지 않는다.
   - Routine 한 단계: 30분봉을 받은 뒤, 같은 기간 각 종목의 키움 수정주가 일봉(usa06012, adjusted=1)을 조회한다.
     쪽 끝 "1f"가 아닌 upd_stkpc_tp나 비어 있지 않은 upd_rt가 있으면 공식 공지를 찾아 기록을 추가한다.
     0.5/2.0 감시는 3:2 같은 작은 분할을 잡지 못하므로, 이 확인이 그 일을 맡는다.
R9 줄바꿈: 기존 파일의 CRLF를 유지하고 BOM은 넣지 않는다. 일괄 변환 금지. 새 .py·.json 파일도 CRLF로 만든다.

단계:
0. 기준선: git status와 HEAD를 확인한다(HEAD가 이 지시문 커밋이 아니면 멈춘다). 바꿀 기존 파일의 원시 sha256을 기록한다.
   전체 테스트를 서브에이전트로 1회 돌리고, 실패·오류 ID만 파일로 남긴다:
   python -m unittest discover -s manage-us-stock-strategy/tests
1. 테스트를 먼저 쓴다. 픽스처는 테스트 안에서 만들고 실제 계좌 자료는 쓰지 않는다.
   T1 3:1 정분할 원주가 + VALID 기록 → V 계산됨, SPLIT_GUARD 없음, V 값 = 미리 나눈 종가로 계산한 값
   T2 기록 파일 없음 → SPLIT_GUARD:<SYM>:<date> 그대로(회귀)
   T3 기록 날짜가 한 세션 어긋남 → SPLIT_GUARD 남음, V 불가
   T4 비율과 upd_rt 불일치 / dt≠effective_session / upd_stkpc_tp가 "1f"이거나 빈 값 → INVALID, V_UNAVAILABLE:CORPORATE_ACTIONS_INVALID
   T5 JSON 깨짐·추가 키·중복·달력에 없는 세션·new=old·published_date>effective_session → INVALID
   T6 병합 1:10(upd_rt +900) → 보정 맞음
   T7 같은 종목 기록 2개 → 곱을 누적해 보정
   T8 원주가 유지: 기록이 있어도 closing_equity·review lines·포지션 close가 기록이 없을 때와 같다(분할일이 HWM 구간 밖일 때)
   T9 고점 점검: 기준일 뒤 분할 + VALID 기록 → 가짜 −30% 이벤트 없음. peak·close·threshold는 최신 원주가 기준
   T10 R5: 분할 전 스냅샷 + 분할 뒤 세션 → SPLIT_RECONCILIATION_REQUIRED. 분할 뒤 스냅샷이 있으면 정상
   T11 실행 중 기록 파일 변경 → READ_ONLY_INPUT_MUTATION_DETECTED. inputs.corporate_actions의 상태·sha256·applied가 기록됨
   고치기 전 코드에서의 실패 수를 보고에 적는다.
2. 구현한 뒤 대상 테스트를 파일마다 -p로 돌린다: test_corporate_actions.py, test_portfolio_exposure.py,
   test_portfolio_exposure_fail_closed.py, test_portfolio_exposure_judge_fixes.py, test_portfolio_exposure_display.py,
   test_run_portfolio_exposure_review.py, test_regular_session_close_history.py, test_s7_calendar_binding.py.
   스키마 감사: python manage-us-stock-strategy/scripts/validate_schema_contracts.py
3. 전체 테스트를 서브에이전트로 1회 돌리고, 0단계 목록과 비교해 "새 실패"만 보고한다(목표 0).
4. 보고 파일에 적는다: 바꾼 파일과 diff --stat, 파일별 원시 sha256 전후, 줄바꿈 확인, 테스트 결과,
   R5가 실데이터 경로에 미치는 영향, 남은 문제. 커밋하지 않는다.
```

## 4. 이번 범위 밖 (기록만)

- 키움 수정 표시 파일을 코드가 대조하는 일(A+안)은 고르지 않았다. 작은 분할은 루틴의 Cowork 확인에 맡긴다.
- 기록되지 않은 분할이 보유 중에 생기는 경우: 자산 경로에는 분할 감시가 없다. 다음 브로커 대조 전까지 자산이 틀릴 수 있다. 큰 분할은 V 쪽 SPLIT_GUARD가 같이 걸려 드러난다.
- 배당 보정은 하지 않는다. 정책 기준은 분할 보정만 정한다.
- 정책 문구(`price_history_collection` 등)에 기록 파일을 적을지는 S7 2단계 정책 반영 때 함께 검토한다(K3, 지금은 안 함).

## 5. 병합 뒤 Cowork 할 일

1. 원본 폴더에 `workspace/outputs/regular-session-closes/corporate-actions.json`을 만든다. MVLL 기록 1건이고, 값은 2절 C1·C2다. 내용을 사용자에게 보여 준다.
2. `run_portfolio_exposure_review.py`를 기본값으로 실행하고 다음을 확인한다.
   - SPLIT_GUARD가 사라졌는지, V가 계산되는지, `inputs.corporate_actions`가 OK인지.
   - 남은 `NOT_READY` 사유가 무엇인지(예상: `S5_NOT_ACTIVATED`, `JOURNAL_MISSING`).
   - 상태·정책·통합 권한 해시가 실행 전후로 같은지.
3. S7 보고 U5와 이 문서의 진행 기록을 갱신한다.

## 6. 진행 기록

- 2026-10-02 Cowork: 분할 사실을 확인했다(공식 보도자료·설명서 보충 문서·키움 수정 표시·MRVL 대조, 2절). 사용자가 A안을 골라 이 지시문을 작성했다.
