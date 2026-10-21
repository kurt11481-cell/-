---
id: close-confirm-e-judge-prompt
title: close-confirm-e 독립 Judge (읽기 전용)
date: 2026-10-21
class: K3 독립 Judge — docs/claude/close-confirm-e-builder-prompt.md의 변경(주문표 priceCalc band·hold, 매수 입력 관문을 판정 유지 구간으로 좁힘, 확인 못 한 매수 HOLD_RANGE_UNVERIFIED)을 판정
model: Opus · xhigh · 새 세션(메인 체크아웃 E:\사업\##금동한\코덱스저장소, worktree 아님) — Builder 세션과 다른 세션
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 키움 주문 도구 금지
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(메인 체크아웃) · 이유: K3 독립 Judge(주문표 의미·매수 입력 관문 + decide 경로의 새 계산)

너는 이 변경을 만들지 않은 독립 검토자다. **파일을 고치지 않는다.** 저장소 안에 쓰는 파일은 맨 끝의 보고서 1개뿐이다(예외: 저장소 밖 임시 폴더의 base 복제·합성 입력·드라이버·출력). Builder 보고서와 아래 Cowork 사전 확인의 숫자·주장은 위치 안내일 뿐이다 — 판정은 네가 연 원문과 네가 다시 계산·실행한 값으로 한다.
- 사전 등록(docs/claude/t2-rc-preregistration-2026-10-14.md 16행)대로 너는 규칙을 더 엄격하게만 바꿀 수 있다. 엄격하게 바꾼 것이 있으면 보고서의 "사전 등록 변경" 절에 적는다(Cowork가 병합 뒤 사전 등록 변경 기록 줄에 옮긴다).
- **끝까지 확인하지 못한 PASS 조건은 PASS로 적지 않는다.** "미확인 + 사유"로 두고 그 항목은 FAIL로 본다. 표 1~13의 PASS 조건은 모두 판정에 필요하다("발견에 적는다" 문장만 예외). Builder·Cowork 숫자로 미확인을 메우지 않는다(예: 전체 스위트를 끝내지 못하면 항목 10은 FAIL).

## 0. 시작 확인 (가장 먼저 — 하나라도 아니면 판정하지 말고 멈춰서 그 사실만 알린다)

- `git rev-parse --show-toplevel` = 메인 체크아웃 `E:/사업/##금동한/코덱스저장소`(Code 탭이 만든 `.claude/worktrees/claude/*`·`e-judge-*` 같은 worktree가 아님).
- `git rev-parse --abbrev-ref HEAD` = `codex/master-recovery-expansion`, `git merge-base --is-ancestor 3e753f3 HEAD` 참. (2026-10-21 첫 시도는 Code 탭이 기본 브랜치 `main` 41f7b3f(2026-08-15) 기준 worktree로 열어 무효였다 — 보고서도 남지 않았다.)
- 보고서는 절대 경로 `E:\사업\##금동한\코덱스저장소\docs\claude\close-confirm-e-judge-report.md`에 쓴다.

## 읽을 것

1. 결정: docs/claude/close-confirm-monday-gap-2026-10-20.md 2절 e(24~29행). 지시문: docs/claude/close-confirm-e-builder-prompt.md — 특히 "판정 유지 정의", "구간 계산", "출력", "동치 명세" E1~E7, "바꿀 것" A~D, "기존 테스트 변경 허용 1~3", "지켜야 할 것".
2. Builder 보고: .claude/worktrees/work-close-confirm-e/docs/claude/close-confirm-e-report.md.
3. 변경: worktree `.claude/worktrees/work-close-confirm-e`(branch worktree-work-close-confirm-e, HEAD 3e753f3, 커밋 없음)의 `git diff`와 `git status --porcelain --untracked-files=all`. base = 3e753f3. 메인 체크아웃 HEAD는 그 뒤 docs/claude 커밋(f2c95e5·8d0115f)만 더한 것이다 — `git diff 3e753f3 HEAD --stat`으로 확인한다.
4. 다른 독자(L3): docs/claude/t2rc-oracle.py(priceCalc를 읽는지 grep, 1596~1618행 누수·판정), manage-us-stock-strategy/scripts/portfolio_review_journal.py 573~605행(일지 payload), score_decision_journal.py(priceCalc·HOLD_RANGE를 읽는지 grep, 1165~1170·1354~1361행 gate 이름), auto_core_compare.py(tickets를 읽는지), docs/claude/scheduled-prompts/auto-core-alert.txt 112·138~139행(orders 복사), docs/claude/scheduled-prompts/monday-pre-open-check.txt(주문표를 읽는 줄), t2-rc 사전 등록 16·22~25·48행, dashboard-order-panel-2026-10-07.md 35·84행, auto_core_decide.py 449~452행(예외 → FAIL 기록), auto_core_decide.py run_s7 258~274행(--cards 없음)·portfolio_exposure.py 1426~1427행(S7 add = 보충 ETF뿐).

## 돌려도 되는 것

- **base 트리**: `git clone -c core.longpaths=true -c core.autocrlf=true --no-hardlinks <메인 체크아웃> <저장소 밖 짧은 임시 경로>` 뒤 `git -C <그 경로> checkout --detach 3e753f3`. 복제본 `git status`가 깨끗하고 `git ls-files --eol`이 w/crlf인지 확인한다(메인은 로컬 설정 core.longpaths=true, 작업 트리 CRLF — 줄 끝이 다르면 바이트 해시 비교가 어긋난다). 원본 .git에 쓰는 `git worktree add`는 쓰지 않는다. `git archive`로 푼 폴더는 git 저장소가 아니라 decide 테스트(provenance)가 모두 오류가 나므로 쓰지 않는다. 메인 체크아웃·worktree·복제본은 git 밖 자료(30분봉 pages 등)가 서로 달라 skip·실패가 달라질 수 있다 — 같은 종류 트리끼리(worktree ↔ 복제본) 비교한다.
- 대상 집합: 각 트리에서 `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"`("auto_core.py"가 든 명령은 거부되니 이 패턴으로만).
- 전체 스위트: `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests`(나눠 돌릴 때도 같은 환경 변수 — 저장소 안에 __pycache__를 쓰지 않는다). Builder는 변경 뒤 전체 스위트를 메모리 부족으로 끝내지 못했고, Builder의 전체 기준선(Ran 3247 · failures 21 · errors 9)은 편집 중에 돈 실행이라 **기준선으로 쓰지 않는다**. 한 번에 안 되면 `-p "test_[a-h]*.py"`, `-p "test_[i-p]*.py"`, `-p "test_[q-z]*.py"`(테스트 파일이 모두 test_[a-z]로 시작해 셋이 전체를 덮는다)로 나눠 복제본·worktree를 같은 방식으로 돌린다. 오래 걸리면 `test-runner` 서브에이전트(Haiku)에 실행만 맡기고 실패·오류 목록을 받아 네가 원문으로 다시 확인한다.
- `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`. 파일을 쓰지 않는 python(`python -B`)으로 재계산·합성 실험. base 함수는 복제본 경로에서, 새 함수는 worktree 경로에서 각각 별도 프로세스로 import한다(모듈 이름 충돌 주의).
- 실데이터: 저장소 밖 드라이버로 auto_core_replay를 `--output-root <저장소 밖 임시>`로만 돌린다. 입력은 메인 체크아웃, 경로 상수를 바꾸는 방법은 Builder 보고 4절 첫 문단(130~131행). 키움 호출 없음.
- 금지: 키움 호출, auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply 실행, 커밋·병합, workspace/outputs·stock-strategy-system·workspace/policies·예약 작업·관제판·대시보드 쓰기.

## 판정 항목

| # | 항목 | PASS 조건 |
|---|---|---|
| 1 | 범위 | 바뀐 파일 = auto_core_tickets.py · auto_core_decide.py · auto-core-ticket.schema.json · references/auto-core-decision.md · 새 tests/test_auto_core_hold_range.py · 허용 변경 1(test_auto_core_risk1r.py GOLDEN decide_compare·decide_apply 두 값 + 주석 1줄) · 허용 변경 2(test_auto_core_enter_window.py import 1줄 + 215행 되돌리기 적용) · 보고서. auto_core_replay.py·rules·bars·compare·inputs·portfolio_exposure·journal·score·t2rc-oracle·정책·예약 지시문 diff 0. 허용 변경 3은 쓰지 않음(보고 3절)이 맞는지. 스키마 diff = priceCalc description 1줄 + band·hold(지시문 C의 키·타입 그대로, priceCalc required 불변 — 키 안의 required(band 2·hold 8)·minimum·minLength 추가는 지시문 "출력" 절과 맞으면 허용). references diff = 161~167행의 D 내용뿐. **지켜야 할 것 3·5**: 메인 체크아웃 `git status`의 추적 파일 변경 0, Builder 실행 시간대(2026-10-20 22:05 KST worktree 생성 ~ 2026-10-21 00:08 KST 보고 저장)에 workspace/outputs·workspace/policies·stock-strategy-system·사전 등록·gate-rule-epochs에 예약 작업 산출물 말고 새로 생기거나 바뀐 파일 0(mtime으로 확인) |
| 2 | 권한·안전 | 권한 표지 줄(order_authority·quantity_authority·execution_quantity·kill_switch·ORDER_TICKET_HUMAN_ENTRY, tickets AUTHORITY 66행) 변경 없음, 주문 경로·네트워크·파일 쓰기 코드 추가 없음, 스크립트 2개 ASCII, 줄 끝 CRLF 그대로(일괄 변환 흔적 없음), 커밋 없음. loc_price(376~392행)·SIZING·CONSTANTS·ALLOWED_NO_TICKET·_limit_daily·plan_premise·_sell_ticket·_buy_ticket diff 0 |
| 3 | E1 hold 끔 동치 | 합성 시나리오 여러 개(최소: risk1r `_scenarios` 6개, 매도·매수 함께, 보충 ETF, TRIM 크기 없음, 회로 닫힘)에서 worktree `evaluate_session`(hold_range 인자 없음) 출력 전체 = base 출력 — JSON 글자까지. plan 루프 본문 → `_plan_sell`·`_plan_buy`·`_circuit_inputs` 이동이 줄 단위로 같은 계산인지 원문으로 대조. evaluate_session 본문의 내부 helper(raw_closes·judge·shock_of·requirement_row·data_reason·known·sigma_of·marks_of)가 base의 같은 줄과 같은 함수·같은 인자·같은 순서인지 대조 |
| 4 | E2 decide 동치 | test_auto_core_decide `Env` 방식 decide(compare·apply, 매수 주문표가 나오는 입력 포함)에서 worktree 결과 = base 결과. 허용 차이는 셋뿐이다: ① 각 주문표·dashboard orders의 priceCalc band·hold 추가와 매수 lo/hi 좁힘 ② decision_sha256을 입력으로 쓰는 키(그 코드 위치를 보고서에 적는다) ③ 같은 입력으로 base를 두 번 돌려도 서로 다른 키 경로. 일지 payload는 decision_sha256 외 같다. 네가 직접 diff를 떠서 키 경로로 분류한다. **E2 예외 갈래**: hold_eval이 틀린 값을 내게 만든 decide를 compare·apply로 1회씩 돌려, 매수가 빠진 뒤 번호·no_action·일지 payload(ticket_ids·blocked_reasons·order_ticket)·alerts·compare·dashboard가 "그 매수가 없는 plan 결과"를 decide 규칙대로 따르는지 확인한다 |
| 5 | 판정 유지 정의 | `_hold_break`·`_hold_ticket`·`hold_range`·`_with_hold_ranges`가 지시문 정의와 같다: 매수 = 주문표 있음 ∧ r_b ≥ r ∧ G4(주문표 qty, ⌊b × priceCalc.mult⌋센트, `floor(cash/(p_b × (1 + CASH_BUFFER))) ≥ qty`) ∧ (pct 키가 있으면) G2b; 매도 = 주문표 있음 ∧ r_b ≥ r. 수량·decision_key 차이는 무시. 스캔 시작 ⌈ref⌉/⌊ref⌋(센트면 ±0.01), 첫 깨짐에서 멈춤, 바로 깨지면 끝 = ref, limit 코드(BAND·NO_TICKET:<첫 사유, CARD_TRIM_SIZE_MISSING 제외>·CIRCUIT_CLOSED·STEP_DOWN·CASH·G2B·DATA), 자기 점검(after_sale·ticket_id·gap.plan_premise 제외 전체), unverified 사유(SELF_CHECK_MISMATCH·DATA·EVAL_ERROR). 매수 row를 b의 ctx에서 다시 꺼내는지. hold가 _limit_daily 뒤·plan_premise·번호 앞인지. **decide 쪽**: `hold_eval`·`_bars_with_close`가 지시문 B-1과 같다(바꾸는 ctx 키 8개 + model_for·hold_eval None, 그 밖 그대로, 호출 시점 얕은 복사, raw ≠ adjusted close → None). **예외**: 지시문 "예외가 decide를 멈추게 하지 않는다"(구간 계산 절) — try 밖 줄(tickets 914행 자기 점검 비교, 931~936행, 939~956행 _with_hold_ranges 전체)에서 예외가 _run 밖으로 나가 decide 449~452행 FAIL 기록(매도 주문표까지 사라짐)이 되는 경로가 없는지 |
| 6 | E4 구간 정확성 | 네가 따로 만든 합성 시나리오 2개 이상(하나는 band 안 경계가 있는 매수 — 예 그 종목 자신의 −2σ60 날 경계나 현금 경계, 하나는 센트 사이 ref)에서 band 안 **모든** 센트 b마다 전체 경로(evaluate_session에 그 종목 평가 세션 봉만 b — raw·adjusted close = b, high·low 확장; s7_runner = ref 검토의 제안 평가를 (symbol, target_weight)로 찾아 주는 가짜, 없으면 통과 아님)의 판정과 hold_eval 판정이 같고, hold가 ref부터 끊기지 않는 최대 구간이다. Builder의 H2와 다른 입력으로 한다 |
| 7 | E5 조이기만 · 매도 비차단 | 매수 band.lo ≤ hold.lo ≤ ref ≤ hold.hi ≤ band.hi, priceCalc.lo/hi = hold; 매도 priceCalc.lo/hi = band(ok·unverified 모두), 매도 주문표가 hold 때문에 빠지는 경로 없음; 구간 계산이 주문표를 새로 만들거나 수량·가격을 바꾸는 경로 없음; HOLD_RANGE_UNVERIFIED는 매수를 빼기만 하고 candidates는 그대로 |
| 8 | E3 결과 분류 | classify_outcome이 band(없으면 lo/hi)를 읽고, 무작위 주문 행(범위 안·밖, 부분 체결, 취소, LOC 아님, 수량 다름) 수백 개에서 새 주문표 결과 = band를 lo/hi로 둔 옛 주문표 결과. 가드 테스트(test_auto_core_tickets.py 203~208행) 통과 |
| 9 | E6·E7 | 같은 입력 두 번 → 같은 hold·같은 decision_identity_hash. 스캔 뒤 bars(raw·adjusted 깊은 비교, raw is adjusted 동일성)·ctx·review 불변. `_bars_with_close`가 원본을 고치지 않음 |
| 10 | 테스트 | 대상 집합과 전체 스위트 모두에서, 네가 같은 방식으로 돌린 복제본 결과와 worktree 결과의 **failures·errors 테스트 ID 집합**이 같다(새 실패·새 오류 0). Ran 수 변화 = 새 파일 28개뿐. Windows에서 돌린다 — test_auto_core_enter_window GoldenCauseTests·test_auto_core_risk1r UnchangedTicketTests는 이번에 바뀐 테스트라 **Windows 통과가 PASS 조건**이다(Linux 실패는 근거가 아님). 새 테스트가 주장대로 단언하는지(특히 H2가 band의 모든 센트를 실제로 도는지, H6 unverified 경로, H11 끔/켬 비교가 _run의 hold_range=True 키워드를 실제로 덮는지) 원문으로 확인. GOLDEN 새 값: 켠 decide 뷰를 되돌리면 옛 값(decide_compare 2e565c3b7f2d…·decide_apply d78459cbeb51…)이 되고 새 값이 6d24251698e8…·e4eecf21ef59…임을 네가 Windows에서 다시 계산. 기존 테스트에서 단언이 지워지거나 약해진 곳 없음. risk1r 55행 decide_apply 위 주석이 아직 "enter-window: …"인 것은 발견에 적는다(허용 1 범위라 FAIL 아님) |
| 11 | 실데이터 | ① E1 실데이터: 복제본(base) 코드 리플레이 replay.json = worktree off 리플레이(run id·시각 외). ② 리플레이 off/on(evaluate_session을 hold_range=True로 감쌈) replay.json이 run id·시각 외 같다(주문표 0건이면 공허하므로 ③을 반드시 한다). ③ 최근 세션(2026-10-19) P-R1 실데이터에서 매수 주문표 1장 이상을 **메모리에서만** 만든다. 10-19는 매수 후보 모두 요건 ⑤ R-REC1이 막혀 있고 일부는 ①도 막혀 있다(2026-10-20 decision.json buy_requirements). 회로와 막는 요건은 ctx를 고쳐 열지 않는다(hold_eval이 judge·requirement_row로 다시 구해 ref 자기 점검이 깨진다). evaluate_session 입력(facts 등)이나 모듈 함수 감싸기(tickets_module.evidence_summary·rules.rrec1·tickets_module.buy_requirements를 그 종목에만 통과로)로 연다 — 그래야 hold_eval도 같은 값을 본다. 먼저 ref 자기 점검이 ok인지 확인하고, hold.status ok·회로가 열린 상태의 센트당 시간을 잰다. 가장 비싼 종목(MU, band 약 1,812센트)에서 주문표 1장 ≤ 30초, 보고 4절 표 방식 최악 합계 ≤ 120초가 네 측정으로도 맞는지 |
| 12 | 다른 독자·사전 등록(L3·L5) | 계산기가 priceCalc를 읽지 않고 sha256_lf가 6a74f813c918…그대로; 후보 집합·주문표 수량·가격이 그대로라 C1·C2 영향 없음; HOLD_RANGE_UNVERIFIED 날은 계산기가 누수(ticket_leaks → MISMATCH)로 보고 사전 등록 24행 CORE_BUG·48행 C3 불산입이 그대로 적용됨(지시문이 이를 느슨하게 하지 않음); 일지·채점기·비교·월요일 점검·알림 작업이 새 키 때문에 깨지거나 뜻이 바뀌지 않음(알림은 orders를 그대로 복사). 대시보드: live 화면 코드는 저장소에 없으므로 판정은 dashboard-order-panel 35행("없으면 price만 표시")·지시문 근거 2(Cowork의 live 확인) 인용으로 한정하고, 화면 경고 문구는 병합 뒤 Cowork 몫(지시문 4-①)임을 확인. Builder 보고 5절 2(SOXX·GRID 보유 시 다른 종목 행 고정)·4(decide가 S7에 cards를 넘기지 않음) 전제를 원문(최신 decision.json symbols, run_s7, portfolio_exposure 1426~1427행)으로 확인 |
| 13 | 병합 뒤 절차 | 지시문 "병합·화면 반영" 절이 승인 범위·변경 경로·사전 등록을 느슨하게 하지 않는다: 병합 = 사용자 승인 1줄 + 병합 스크립트(06:00~09:00·23:20~23:45 KST 밖), 화면 반영은 표시 전용, gate-rule-epochs 이름 `GATE:HOLD_RANGE_UNVERIFIED`가 채점기 gate 이름 규칙과 맞음 |

## 출력

- 한국어 표 `| # | 항목 | PASS/FAIL/미확인 | 근거(파일:행 / 재계산 값 / 실행 결과) |`(위 1~13), 그 아래 "발견"(E1·E2·E4 실험 수와 차이 0 확인, 남은 위험, 의견 — 기본 NO_CHANGE), "사전 등록 변경"(엄격하게 바꾼 것, 없으면 "없음"), 고칠 최소 항목(있으면, Builder가 같은 worktree에서 고칠 수 있게 파일:행으로), 바뀐 파일 sha256(네가 잰 작업 트리 바이트 값), 마지막 줄은 정확히 `VERDICT: PASS` 또는 `VERDICT: FAIL`. 미확인이 하나라도 있으면 FAIL.
- 같은 내용을 **새 파일 하나** `docs/claude/close-confirm-e-judge-report.md`(메인 체크아웃)에 저장한다. 그 밖의 파일은 쓰지 않는다.

## Cowork 사전 확인 (2026-10-21 00:0x~00:1x KST, 장치 VM Linux, 읽기 전용 — 참고용, 판정 근거 아님, 네가 다시 잰다)

- worktree HEAD 3e753f3, `git status`: 수정 6개(위 1의 파일) + 새 파일 2개(보고서·새 테스트). diff hunk(새 파일 기준): tickets 645~648·731~757·778~958, decide 664~665·897~1131. 추적 파일 diff에서 권한 표지·주문·키움 단어가 든 추가/삭제 줄 0(새 테스트 파일은 주석의 'Kiwoom' 2줄, 권한 표지 0). 스크립트 2개와 새 테스트 비 ASCII 0. 7개 파일 모두 CRLF 줄 수 = 전체 줄 수.
- 대상 집합(worktree, Linux): `test_auto_core_hold_range.py` Ran 28 OK(skipped 1 = Windows 전용 H11 해시) · `test_auto_core_[!h]*.py` Ran 371 failures 3 skipped 4 · `test_auto_core.py` Ran 89 OK → 합계 488. 실패 3 = PLTR 등록부 + GoldenCauseTests + UnchangedTicketTests — 뒤의 두 건은 이번에 바뀐 테스트라 Linux 결과는 근거가 아니다(항목 10). skipped 4 = PowerShell 없음 3 + "saved 30-minute pages exist only in the main checkout" 1.
- `validate_schema_contracts.py` PASS. Cowork가 tickets 643~962행·decide 895~1142행을 지시문 정의와 대조했다(결과는 적지 않는다 — 네가 판정한다).
- Builder 보고의 남은 확인: 변경 뒤 전체 스위트 미완료, 최종 28개 판의 Windows 대상 집합(488)도 미실행(보고 107·194행) → 항목 10에서 네가 돌린다.

## 작성 기록 (Cowork, 2026-10-21)

- Builder 결과 확인(장치 VM, 읽기 전용): worktree status·diff·hunk, 권한·주문 단어 grep, ASCII·CRLF, 대상 집합 실행(위 사전 확인), 스키마 감사, tickets 643~962·decide 895~1142행 원문 대조, Builder 보고 1~224행.
- 내장 재검토(Opus) 2회: 1회차 발견 18건 모두 원문으로 확인해 반영(base 복제 방식, failures·errors 집합, 미확인 = FAIL, E2 예외 갈래, 지켜야 할 것 3·5 확인, 실데이터 공허 → 메모리에서 주문표 만들기, try 밖 예외 경로, decide B-1, 사전 등록 변경 기록, 허용 차이 좁힘, 시각·hunk·단어 정정 등). 2회차 발견 6건 반영(③ 실행 방법 — 10-19 매수 후보 모두 R-REC1 막힘을 decision.json에서 확인, 스키마 허용 범위, 복제 설정 longpaths·autocrlf, PYTHONDONTWRITEBYTECODE·-B, run_s7 위치, 미확인 재량 제거). 최대 2회라 3회차는 돌리지 않았다.
