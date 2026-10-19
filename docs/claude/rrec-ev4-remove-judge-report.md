---
id: rrec-ev4-remove-judge-report
title: rrec-ev4-remove 독립 Judge 판정 (R-REC1 EV4 제거 — 코어·리플레이·독립 계산기·실행기 고정값)
date: 2026-10-19
prompt: docs/claude/rrec-ev4-remove-judge-prompt.md ('추가 범위' 절 포함 전체) — Judge가 잰 sha256 08972e63310e47ac0e19528dcc07837cacad15906b90f2aa60ccbb458ca0103b (판정 시작·끝 같음)
builder_prompt: docs/claude/rrec-ev4-remove-builder-prompt.md sha256 e29f0837176dcb588e4714bee8d3483eee66ffc1c0a257740e33a9ca5ac87014 (Builder 보고 머리의 값과 같음)
decision: docs/claude/rrec-ev4-remove-decision-2026-10-19.md sha256 8274facd82288e955a1e111605491ff1c615697274019fcfcc6e7335b2723392 — 사용자 "결정 rrec-ev4: REMOVE"(2026-10-19 17:45 KST)
target: .claude/worktrees/rrec-ev4-remove (브랜치 worktree-rrec-ev4-remove, HEAD 80d3a1da0957a872fc16b97ac204ee4d761198ca = 메인 HEAD = 지시문 base, 커밋 0, 커밋 안 된 변경)
class: K3 독립 Judge(읽기 전용) — Builder와 다른 새 세션, 메인 체크아웃, Opus 5.5 · xhigh, Windows 11 · Python 3.13.15. 계산기 새 고정값의 "Judge 확인"(t2-rc-preregistration-2026-10-14.md 24행) 겸함
authority: order_authority=false · quantity_authority=none · execution_quantity=null · 키움 호출 없음 · 파일 수정 없음(저장소에 쓴 파일은 이 보고서 1개. 합성 입력·실험 스크립트·계산기 --out·전체 스위트 사본은 모두 저장소 밖 스크래치 폴더)
consumers: Cowork 병합 스크립트 docs/claude/rrec-ev4-remove-merge-<날짜>.ps1(마지막 줄 VERDICT 확인) · 관제판 rrec-ev4-remove · t2-rc-preregistration 변경 기록
order_authority: false
quantity_authority: none
---

# rrec-ev4-remove 독립 Judge 판정

판정은 이 세션에서 연 원문과 직접 다시 계산한 값으로 했다. Builder 보고·Cowork 사전 확인의 숫자는 위치 안내로만 썼다. base 코드는 메인 체크아웃(대상 파일이 HEAD와 같음 — `git status`·`git diff HEAD` 빈 결과), 새 코드는 worktree에서 각각 별도 프로세스(`python -B -I`)로 불렀다.

## 판정 표

| # | 항목 | PASS/FAIL | 근거(파일:행 / 재계산 값) |
|---|---|---|---|
| 1 | 범위 | PASS | `git -C .claude/worktrees/rrec-ev4-remove status --porcelain --untracked-files=all` = 수정 18 + 새 파일 2(새 테스트, Builder 보고) = 지시문 103행 목록. 스키마: diff 1줄(150행 `ev4_backfill.description`), description 키를 뺀 스키마 dict가 base와 같음(True). 실행기: diff 16행 1줄. 기존 테스트 31덩어리를 줄 단위로 기계 분류 — 허용 1(`, ev4_sessions=[]`만 빠진 줄 15줄: compare_fix3 73·79, rg1_damage 73·181·444, rg1_oracle_parity 58, rrec_bootstrap 31, rules 400·403·410·415·418·441, t2rc_corefix 45, tickets 398) · 허용 2(t1_safety 57~236 `Ev4BackfillTests`, tickets 668~685 `SessionEv4Tests`·337~339 docstring, rules 445~454 `test_ev4_lines`) · 허용 3(equity_cash 61·75~77·80·128·169·303~304, `"ev4"` 키와 `rules.ev4_open` 단언만) · 허용 4(decide 68~69 docstring) · 승인 ①(t1_safety 238~266 `Ev4ResolveTests` — 4개 테스트 모두 지운 `ev4_backfill_resolve`·`RREC_EV4_NEIGHBOR_MARGIN`만 부름, base 238~265 원문) · 승인 ②(rg1_oracle_parity 63 `, None, None, ()`만) · 승인 ③(risk1r 41 `cash5` 값 + 주석 2줄, `decide_compare`·`decide_apply` 불변) — 미분류 0. 삭제 테스트 ID = base만 있는 16개 = 지시문 이름 3묶음 + 승인 ①. auto_core_compare·auto_core_tickets·auto_core_inputs·portfolio_exposure·score_decision_journal·예약 지시문·사전 등록·정책: worktree diff 없음, 메인의 정책·사전 등록도 수정 목록에 없음. Builder 해석 3건(계산기 base 1936행 `s7hwm` — base에서 1936·1938행 두 곳만, 지운 인자 전용 / base 2261행 `_rg1_run` 인자 — rrec1의 유일한 다른 호출처 / decide docstring)은 지시문 E1·E2·B3·B4 범위 안으로 판정. 범위 밖 1건: decide 638행 `checks ={`(base 751 `checks = {`, 공백 1칸 삭제) — 동작 동일(항목 4에서 결과 동치 확인), 비차단(아래 '고칠 최소 항목') |
| 2 | 권한·안전 | PASS | diff ±줄에 `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY` 0줄, 새 테스트에도 0. 추가 줄의 주문 경로 문자열 0(`order` 일치는 decide docstring "order-available" 1건뿐). 비ASCII 바이트: 스크립트 3개 0(base 0), 스키마 0(`—` 이스케이프), 계산기 476 = base 476, 새 테스트 0, 추가·삭제 줄의 비ASCII 0. 줄 끝: 20개 파일 모두 CRLF만(LF 단독 0, CR 단독 0), base 파일도 CRLF. 커밋: `80d3a1d..HEAD` 0개. 무시 파일은 worktree 생성 때부터 있던 3개(.claude/settings.local.json, portfolio_state.json, alert_runtime_state.json)뿐, pyc 없음. 계산기: 정적 import(t2rc-oracle.py 27~36행)에 auto_core* 없음, 실행 시 계산기가 새로 불러온 모듈 0개 |
| 3 | E1 코어 동치 | PASS | Judge 독립 생성기 400개 입력(시드 0~399, Builder `e1_inputs`와 다름): EV1 급락·EV2 연속 하락·EV3a 날짜·EV3b(사실 + −1.5~−2% 하락일)·EV5 후보 급락·DS1(EMA50 아래 구간)·RG2(후보·GRID)·RG3(L0 아래 신저가)·L0 결측·벤치마크 없음/짧음 · 훼손 사실 None/[]/1~3개(도메인 표지 30%) · card_accepted_on 있음/없음(세션 뒤 날짜 포함) · research_sessions None/전체/1~2일 공백/늦은 시작 · rg2_series 생략/None/GRID · 평가 세션 마지막/이전. 두 프로세스 입력 해시 400/400 같음, worktree `rrec1(x)` = base `rrec1(x, ev4_sessions=[])` 결과 JSON **400/400 글자까지 같음**. 닿은 범위(새 결과): kinds EV1·EV2·EV3a·EV3b·EV5 전부, status ok 39·no 225·unk 136, RG1~RG4 × ok/no/unk 12가지 전부, DS1 155·훼손 184·EV3B 공백 25·닫힘 25·사건 없음 57·벤치마크 없음 25. 추가: Builder X5 320개를 base 코드로 다시 계산 → 시드별 320/320 + 전체 해시 129a009c…abc3 일치. 실데이터(평가 세션 2026-10-16) base(`ev4_sessions=[]`) = new 전체 동일 |
| 4 | E2 decide 동치 | PASS | evaluate_session 10개(risk1r GOLDEN의 default·g2b·cash5·research_block·sell·pwr + 현금 5,000(EV4만 켜지는 계좌)·SOXX 급락+현금 5,000(EV2와 겹침)·SOXX 급락+현금 30,000(선 위)·현금 25,000) + decide 12개(test_auto_core_decide.Env: 기본·좋은 소식·좋은 소식 apply·현금 5,000·좋은 소식+5,000·SOXX 급락+5,000·급락+30,000·이전 기록 `account.ev4_open` 참·같은 경우+5,000·첫 기록 F1 전 FAIL(오늘 총액 있음/없음 — 옛 NEIGHBOR_CLEAR·NONE)·이전 기록 3개 모두 F1 도달(이전 기록 없음은 기본 경우)). base_off = base에서 `rules.ev4_open`을 늘 False, `evaluate_session`에 `ev4_sessions=[]`·`ev4_backfill=None` 강제. **new = base_off − {`account.ev4_open`, `ev4_backfill`}가 22/22에서 키 순서까지 같음.** 원시 차이는 apply 경우의 `journal.decision_sha256` 1개뿐 — base_off 기록에서 두 키를 빼고 `decision_identity_hash`(decide 754행)로 다시 내면 새 값과 같음. 새 결과 22/22에 `ev4_backfill`·`account.ev4_open`·`EV4_UNDETERMINED` 없음, decide 12/12 스키마 오류 0, 디스크의 decision.json = 반환값(12/12) |
| 5 | E3 계산기 동치 | PASS | 같은 400개 입력 중 벤치마크가 있는 391개를 계산기 입력(SOXX·X·GRID 계열, ev3a, records, accepted_on)으로 바꿔 worktree `rrec1(...)` = base `rrec1(..., None, None, ())` **391/391 글자까지 같음**(입력 해시도 같음). 계산기 diff = 출처 docstring 1줄(15행) · 66행 `V6_FIRST, V6_APPROACH` 삭제(worktree에 남은 사용처 0 — grep) · rrec1 시그니처(1041행) · docstring 1문장(1046행) · EV4 판정 3줄(base 1109~1111) · `ev4_hist` 적재와 `res["ev4_history"]`(base 1587~1601) · 호출 인자(1915~1916행) + `s7hwm` 1줄 · `_rg1_run` 인자(2236행) · selftest 새 경우(2436~2441행). 그 밖의 diff 없음. `s7`·`exp`는 1896~1906행에서 계속 쓰임 |
| 6 | E5 완화 범위 | PASS | 아래 '발견 2' 표. EV4가 없던 입력의 차이 0: 코어 창 밖 EV4 400/400 같음·사건 판정 전 반환 25 같음, 계산기 선 위·창 밖 391/391 같음·사건 판정 전 반환 49 같음, decide 수준 EV4 없는 11개 차이 0. 차이 난 입력은 전부 base에 EV4 사건(또는 EV4 재기준) 또는 `EV4_UNDETERMINED`(E4)가 있던 입력. 단, 완화만 있는 것은 아님(코어 2건·계산기 11건 엄격화 — 발견 2) |
| 7 | S7 의존 확인 | PASS | 원문: portfolio_exposure.py 142~157(L3 이하는 마지막 설정 선의 멈춤을 복사), 719·721(새 HWM에서 재무장, 선당 1회), 744~767(일지 `line_review_completed`가 line_id·breach_date·hwm 모두 맞아야 completed), 1378~1386(열린 선 → `REVIEW_LINE_OPEN:<선>` 멈춤); auto_core_tickets.py 183~201(`s7_summary.new_buy_paused`)·240~241(요건② "S7 신규 매수 멈춤"); 정책 alert_policy.json 824~835(L1 0.90 멈춤 없음 · L2 0.80 멈춤 · further 0.10 same_as_L2 · 선당 1회 · 재무장 · 해제 = 일지 검토 + 사용자 확인). 합성 S7(실제 `build_exposure_review`, MU 100주 + 현금 30,000, HWM 50,050): A L2 열림 → `REVIEW_LINE_OPEN:L2`, 요건② "막힘 S7 신규 매수 멈춤" / B 같은 날 L1·L2 검토 완료 일지 → 멈춤 없음, 요건② "통과 (E 0.8189 · 현금 $20000)" / C 더 내려 L3(0.7) → `REVIEW_LINE_OPEN:L3`, 요건② 다시 막힘. 세 파일 diff 없음 |
| 8 | 테스트 | PASS | 대상 `test_auto_core*.py`: worktree Ran 443(실패 1 = RegistryTests PLTR, 건너뜀 1) / base(메인) Ran 453(실패 1 = 같은 PLTR). 테스트 ID 비교: base에만 16 = 삭제 16, worktree에만 6 = X1~X6 → 453 − 16 + 6 = 443 정확히 일치. 건너뜀 1 = test_auto_core_replay RealDataSmokeTests(봉이 메인에만) → 대신 새 replay를 메인 봉으로 2026-09-01~10-09 실행: base 결과와 차이 `registry_sha256` 1개(메인 작업 트리 등록부 vs worktree HEAD 등록부 — 입력 차이)뿐, 예외 0·스키마 오류 0, base 출력에 EV4 0건. `test_score_*` 66/66 OK·`test_decision_journal_cards` 36/36 OK(양쪽). 전체 `test_*.py`(test-runner로 실행, 로그는 Judge가 다시 읽음): 저장소 밖 같은 자료 사본 두 개(.git 없음) — 새판 Ran 3213 / base판 Ran 3223(−10), 둘 다 failures 29·errors 11·skipped 5, 실패·오류 ID 40개 집합 동일 → 새 실패 0(40개는 .git 없음·자료 없음 등 환경 원인, auto_core 관련은 PLTR 1개). `validate_schema_contracts.py` PASS(양쪽). X1~X6 단언은 보고 3절 주장과 같음(파일 64~173행), X5 기대값 base 재현(항목 3). GOLDEN: base·worktree에서 각자 measured = 각자 파일 GOLDEN. `decide_compare` 612f246d…·`decide_apply` 91c252b8…는 base = new(해시 대상에 `account`·`ev4_backfill`이 없어 'base에서 E4 두 키를 뺀 해시' = base 해시 = 새 값). `cash5`만 c3ad82a2… → c6f61589…: 해시 대상 차이 = `blocked[0].reasons`·`no_action.reasons`에서 "REQ5_RREC1:no"만 빠짐(base에서 그 문자열을 빼면 새 view와 같음 True), base cash5 사건 = 포트폴리오·MU·SOXL 모두 [2026-10-09 EV4] 하나뿐 |
| 9 | 계산기 고정값 | PASS | worktree t2rc-oracle.py sha256_lf(110~113행 방식) = **6a74f813c918046b6e58b19087e1cee69b5984591a54639f84be0b47d0139d64** — 계산기 자체 `sha256_lf()`, 실행기 55~70행과 같은 PowerShell 계산(UTF-8 읽기 → CRLF→LF → SHA256), worktree t2rc-check-run.ps1 16행이 모두 같음. base 계산기 sha256_lf = 9f0e2238…1aae(= base 실행기 16행). selftest worktree·base 모두 PASS, 출력 바이트 동일(앵커 5개 true, 기존 골든 불변), 새 경우 `_rg1_run(_rg1_world())` = ok·False·[] (같은 세계에 10-16 총액 23,695.43·hwm 31,711.76을 준 base는 no·열림·EV4) |
| 10 | 실데이터 | PASS | 계산기 `check --day 2026-10-15·16·17 --repo <메인> --out <저장소 밖> --ignore-input-sha`: 세 날 모두 차이 = `oracle_sha256` + `ev4_history`(base 10-15 [] · 10-16 ['2026-10-14'] · 10-17 ['2026-10-14','2026-10-15'])뿐, 판정 INFO_MATCH 양쪽, 종료 0. 코어: 메인 체크아웃의 바뀌지 않은 로더로 입력을 한 번 읽음(달력·봉 10종 OK·연구 기록 5세션·훼손 0·EV3a 10-08·보유 MVLL·NBIS·SOXL, auto_core 모듈 import 없음). base + `ev4_sessions` [10-14,10-15,10-16] = 10-17 decision.json `shock` 전체 동일(재현 확인). new vs 기록: 사건 날짜 13개 같음, 차이는 events[10~12]·event의 kinds에서 "EV4"만 빠짐, event 2026-10-16 [EV2](c0 493.14, l0 492.88), RG1 no·RG2 no·RG3 no·RG4 ok, status no, open True, by_symbol 8종 동일 |
| 11 | 다른 독자(L3) | PASS | auto_core_compare.py 271~292: 통합 점검 shock.open ≠ 코어면 `RREC:open` B7(274행, timing이면 B6). 규칙 파일 v3.12.7 102행이 "EV4 계좌 1차 선 도달"을 계속 세므로 병합 뒤 규칙 파일 교체 전까지 EV4만 켜지는 날 B7이 난다 — 병합 때 v3.12.8 교체가 같은 세션이어야 하는 이유(발견 4). score_decision_journal.py의 `ev4` 0건(grep -c), `shock.open`·`event`·`by_symbol`만 읽음(1328~1415행). 옛 결정 파일 5개(10-13~10-17, 그중 4개 `ev4_backfill`=[], 5개 모두 `account.ev4_open`)가 새 스키마로 오류 0 |
| 12 | 병합·C1 절차 | PASS | 지시문 113~118행: (C1) 115행 "C1 0부터" + 118행 병합 뒤 첫 08:40 확인 + 사전 등록 24행 규칙·50행 선례(병합 뒤 첫 decide부터 0/10) — 느슨하게 하지 않음. (한 병합) 115행 "계산기·실행기 한 병합"; 계산기 고정값을 실제로 대조하는 곳은 실행기 16행뿐(`git grep --untracked 9f0e2238`: 나머지는 기록 문서·옛 병합 스크립트), 실행기는 실행 때 계산기 파일을 읽어 16행과 비교(55~70행) → 같은 커밋이면 ORACLE_SHA_MISMATCH 창 없음. 실행기 sha(fcd8977b…)를 대조하는 코드 없음(기록뿐). (규칙 파일) 115행 ①이 같은 승인 1줄의 초안, 117행 "같은 세션" 교체, 결정 문서 39행. (시각) 116행 "화~토 06:00~09:00 KST·23:20~23:45 KST 밖" + 선례 스크립트 ev-rg1-hyper-merge-2026-10-18.ps1 36~45행(시각·실행 중 작업 멈춤). Windows 작업 트리거(2026-10-19 읽기): AutoCore 06:15·AutoCoreDecide 07:45·T2rcCheck 08:40 = DaysOfWeek 124(화~토), DocsCommit 매일 23:30, DevQueue 5분마다(실행 중·잠금 확인 대상), JournalScore 일 09:20(score_decision_journal은 바뀐 모듈을 import하지 않음 — 충돌 없음). 더 엄격하게 넣을 것 1건(아래) |

## 발견

### 1. E1~E3 실험 수와 차이 0
- E1 코어: Judge 생성기 400개 400/400 글자까지 같음 + Builder X5 320개 base 재현 320/320 + 실데이터 1건 같음.
- E2 decide: evaluate_session 10개 + decide 12개 = 22/22 같음(두 키를 뺀 뒤, apply의 decision_sha256은 같은 함수로 다시 내면 같음).
- E3 계산기: 391/391 글자까지 같음 + 실데이터 3일 출력 차이 `oracle_sha256`·`ev4_history`뿐.

### 2. E5 분류 표 (base = EV4 켜짐, new = worktree)

| 수준 | EV4 없던 입력(차이 0) | EV4 있던 입력(차이) |
|---|---|---|
| 코어 rrec1 400개 | EV4 날을 창 밖(창 앞·평가 세션 뒤)에만 줌: 400/400 같음. EV4를 창 안에 줬어도 사건 판정 전 반환(벤치마크 없음·짧음) 25개: 같음 | EV4 1~3일을 창 안에: 375개 다름, 모두 base에 EV4 사건. 사건 목록 = base 목록에서 EV4를 뺀 것(375/375). 기준 사건 이동(EV4가 가장 최근 사건) 141 · 기준 같고 kinds만 234. status no→no 222 · unk→unk 109 · no→ok 15 · ok→ok 15 · unk→ok 9 · unk→no 3 · **ok→unk 1 · no→unk 1**, 열림→닫힘 33 |
| 계산기 rrec1 391개 | 총액 30,000(두 선 위)·hwm 30,000·`ev4_hist` 창 밖: 391/391 같음. 총액 20,000이어도 사건 판정 전 반환(EV3B 기록 공백 33·SOXX 없음 16) 49개: 같음 | 총액 20,000(두 선 아래) + `ev4_hist` 창 안: 342개 다름, 모두 base 마지막 사건 kinds에 EV4. status no→no 282 · no→ok 49 · **no→unk 11** |
| evaluate_session 10개 | default·g2b·research_block·pwr·crash_high·cash25000: 차이 0 | cash5: 사건 [10-09 EV4] → 없음, MU·SOXL 열림 → 닫힘, MU 막힘 사유에서 `REQ5_RREC1:no`만 빠짐(G2 하드 상한은 그대로 막음) · cash5000: [EV4] → 없음, MU 요건⑤ no→ok, **MU 비교용 매수 주문표 0→1** · sell·crash_low: 10-09 kinds [EV1,EV2,EV4] → [EV1,EV2](6개 경로, 그 밖 같음) |
| decide 12개 | d_default·d_good·d_good_apply·d_crash_high·d_all_prev_records: 차이 0 | d_cash5000: [EV4] → 없음, 알림 상태 2:RREC open→closed · d_good_cash5000: 같은 변화 + **MU 비교용 주문표 0→1** · d_crash_low: kinds에서 EV4만(4개 경로) · d_prev_ev4_true: 10-07·10-08 [EV4] → 없음, 알림 `2:RREC`·`EV4_UNDETERMINED` 빠짐 · d_prev_ev4_true_low: 10-07~10-09 [EV4] → 없음 · d_first_fail_total: EV4 사건 없이 `EV4_UNDETERMINED` 알림 1개만 빠짐(E4) · d_first_fail_no_total: NEIGHBOR_NONE 10-06~10-08 [EV4] → 없음, 알림 `2:RREC`·`EV4_UNDETERMINED` 빠짐 |

- 엄격해지는 경우(코어 2건: 시드 55 ok→unk, 시드 110 no→unk / 계산기 11건 no→unk): EV4가 가장 최근 사건으로 기준을 다시 잡아, 그 이전 사건 뒤의 연구 기록 공백(RG1 unk)을 가리던 입력이다. EV4를 빼면 이전 사건이 기준이 되어 RG1 unk가 드러난다(시드 55: base 기준 08-17 [EV4] 닫힘 → new 기준 08-06 [EV1,EV2], 08-07 기록 없음). 매수 쪽으로 더 막는 방향(fail-closed)이고 EV4 입력에서만 생기므로 E5 위반이 아니다. Builder 보고 2절 표의 "base보다 엄격해진 경우 0"은 Builder 입력에서만 맞다. 결정 문서 17행의 "완화"는 대부분 입력에서 맞지만 단조 완화는 아니다(기록용).
- 가정 실험(참고): 10-16 SOXX 창을 사건 없는 상승 사본으로 바꾸고 문서의 EV3a 10-08은 남김 → base는 10-16 EV4로 재기준(RG1 no), new는 EV3a 사건 그대로(RG1 ok, RG3 no). 재기준이 RG1을 늘 no로 만들던 결정 문서 23행의 구조를 재현.

### 3. 남은 EV4 주석·코드 위치 (worktree, 고치지 않음 — 지시문 범위 밖 또는 의도)
- manage-us-stock-strategy/scripts/auto_core_tickets.py:157 "The total also feeds V6 and EV4."
- manage-us-stock-strategy/scripts/portfolio_exposure.py:741 "the core records the day's EV4 from this value." — 병합 뒤에는 사실과 다른 주석.
- docs/claude/t2rc-oracle.py:1739, 1773 "V6 / EV4" (값은 `total_assets_v6` 표시용으로 계속 쓰임).
- manage-us-stock-strategy/schemas/auto-core-decision.schema.json:149~162 `ev4_backfill` 구조(옛 파일 통과용, description만 legacy — 의도).
- 테스트: test_auto_core_equity_cash.py 2·55·76·184(`ACCOUNT_TOTAL_FIELDS`의 `"ev4_open"`, pop이라 무해)·278, test_auto_core_rules.py 433, test_auto_core_t1_safety.py 3~5(모듈 docstring Fix 1)·47·53과 더 안 쓰이는 helper·상수·import(`run_day_of`·`without_backfill`·`comparable`·`S1~S3`·`Decimal`·`mock`·`rules`·`copy`·`validate_instance`) — 지시문대로 FAIL 사유 아님.
- manage-us-stock-strategy/scripts/auto_core_decide.py:575 `multipliers` — 소급 절 삭제 뒤 `_run`에서 안 쓰임(정책 키가 없을 때 같은 자리에서 멈추는 동작 유지, Builder 보고 5절과 같음).
- 범위 밖 문서(병합 때 Cowork): 통합 점검 규칙 파일 v3.12.7 102행, recovery-gate-R-REC1-2026-10-09.md 26행(EV4 행), CLAUDE.md R-REC1 줄 "account line L1,", gate-rule-epochs.json, t2-rc 사전 등록 변경 기록.

### 4. 남은 위험
- 병합 ~ 규칙 파일 v3.12.8 교체 사이: 통합 점검이 EV4를 세는 동안 EV4만 켜지는 날 `RREC:open` B7(compare 274행). EV4 재기준 때문에 통합 점검과 코어의 RG가 다르면 RG3 차이는 B2 "L0_REGULAR_LOW_DEFINITION"(290행)으로 '설명된 것처럼' 분류되고, 요건 ⑤ 칸 차이는 B7(241~243행)이 된다. 같은 세션 교체로 막는다(결정 문서 39행, 지시문 117행).
- 반도체 지수 밖 손실(MVLL·NBIS)로 계좌가 빠져도 L2 전까지는 R-REC1이 매수를 막지 않는다. L2·L3 멈춤과 일지 해제는 항목 7에서 확인(결정 문서 36행 대응 그대로).
- 3배 SOXL 기준 검증 없음(결정 문서 37행 "확인 필요") — 비교 모드("켜" 전 주문 입력 없음)가 대응.
- 합성 계좌(현금 5,000)에서 MU 비교용 매수 주문표가 0→1장 생긴다(발견 2). 비교 모드라 입력되지 않는다.
- 실데이터(평가 세션 10-16) 기준으로는 열림·RG·status가 그대로고 kinds에서 EV4만 빠진다(항목 10). 10-14~10-16은 같은 날 EV2가 있었다.
- Cowork 사전 확인과 다른 점: Windows에서 대상 스위트 실패는 1건(PLTR)이다. risk1r 해시 테스트는 Windows에서 통과(지시문 근거 8의 예상과 같음).

### 5. 의견
- 차단 결함 없음 → PASS. E1~E3 동치는 Judge 독립 입력·Builder 입력·실데이터 모두에서 차이 0, E5 차이는 EV4 입력에만 있고, S7 대체 장치는 원문과 합성 실행으로 그대로임을 확인했다.
- 기본 처분: 병합 승인이 없으면 NO_CHANGE(EV4 유지, 결정 문서 41~44행). 이 판정은 노출·예산·권한을 올리지 않으며 매도를 막지 않는다.
- 이 판정이 바뀔 조건: 병합 전 worktree 대상 파일의 sha가 아래 표와 달라짐, 병합 스크립트가 계산기와 실행기를 다른 커밋으로 옮김, 또는 규칙 파일 교체가 병합과 다른 세션으로 미뤄짐.

## 고칠 최소 항목
- 차단 항목: 없음.
- 비차단 N1: manage-us-stock-strategy/scripts/auto_core_decide.py:638 `checks ={symbol: …` → `checks = {symbol: …`(base 751행). 지시 범위(B2 "746~749행 삭제") 밖의 공백 1칸 삭제이며 토큰·동작은 같다. 이번 병합에서는 그대로 두기를 권장한다(아래 sha와 병합 스크립트 대조값 유지). 고친다면 그 1줄 diff만 확인하고 decide sha를 다시 잰다. 그러지 않으면 다음에 auto_core_decide.py를 고치는 K3 변경 때 함께 되돌린다.
- 병합 기록에 넣을 것(사전 등록 0절: Judge는 더 엄격하게만 바꿀 수 있음): t2-rc-preregistration 변경 기록 줄에 "병합 전 C2 일치는 세지 않는다(요건 ⑤ R-REC1 정의가 바뀜)"를 C1 0/10과 함께 적는다. ev-rg1-hyper 선례(사전 등록 50행)와 같다. 지시문 115행은 C1만 적고 있다.
- 비차단 N2: portfolio_exposure.py:741·auto_core_tickets.py:157 주석은 그 파일을 다음에 고칠 때 정리한다(이번 범위 밖).

## 바뀐 파일 sha256 (Judge가 잰 작업 트리 바이트 값, 모두 CRLF)

| 파일 | sha256 (작업 트리 바이트) | LF 정규화 sha256 |
|---|---|---|
| docs/claude/t2rc-check-run.ps1 | beaf8446802621e1a9cd29c2a6c025eef62a5c9bc6c8ceb3c247e8d2906a15a7 | 593a067a848f5d6b27ff8b8ac2e086fa385efe5c83ec3ed88f00d8f19e9fbaf8 |
| docs/claude/t2rc-oracle.py | d79b12212ee2c043e8c1ad8be739e84498506126b8ed42c60cc23f2a5ff42631 | 6a74f813c918046b6e58b19087e1cee69b5984591a54639f84be0b47d0139d64 |
| manage-us-stock-strategy/references/auto-core-decision.md | 61b0af682c1c43e6b750cf6312d8e6ff6a6a1d3f436dbf3d9afa53834c5c6010 | f656b63c3d4463177dde52d3a24f0c6caaee233f80c7989c72b3317c9c36f377 |
| manage-us-stock-strategy/schemas/auto-core-decision.schema.json | 3b540d749011d8ff953d8a81f621ecbbbedc66935252755da960c3782ee94514 | 9c594f3b55e7bd6043ec0a4d815efb407dd677cdc7d34d28227eaca666026e17 |
| manage-us-stock-strategy/scripts/auto_core_decide.py | 97b78ac5edfc1850267a8b1c70a3919c9dc2a0f93d8ed8534c54bd935e0d57ec | 39eb1cb686b91cde5a6326f91863edeb069b5a7f79de25d7bb2f3f894d48db0d |
| manage-us-stock-strategy/scripts/auto_core_replay.py | d346ba92f7839860b63295ff1e12ae26d7fefeb8e431a03959e4482d5b06dbd0 | 088a0f30ba206007f40730202ac96139937776f2bba96b979c818db3607836b6 |
| manage-us-stock-strategy/scripts/auto_core_rules.py | 187a46f628c621da908fe696eeb1c8a130ae01946b9533add393a9283d90ab56 | 9ba4b9ae4480ce456a636d36bda301e179a8e1d0001bf46d5b05a14edc090c32 |
| manage-us-stock-strategy/tests/test_auto_core_compare_fix3.py | e42fff9044295aca7e4c2d1b8518f99e2859d1c0ea10f351adfea9eb244faae9 | a54becf51183fb1e70b0b25201c1bc5fc85e8b51887e02c4d67c7852ab790c4d |
| manage-us-stock-strategy/tests/test_auto_core_decide.py | 6c6e8611f07a2e583f9da652d98c8b7e452d8c4bab5af05a297f6f21778fb644 | 30063967af89c286f847ea032c58d4972dca2eea452f4e121df005a8e6fd264c |
| manage-us-stock-strategy/tests/test_auto_core_equity_cash.py | 526d927485e8f02dc0040c2663f0915b8752845814695bee278369a8fc3b02b4 | 64a4e5864cca5ea0db422b95dcec867c6cf31d7cddb21da6906fb47703502282 |
| manage-us-stock-strategy/tests/test_auto_core_rg1_damage.py | a1b5ad03926894ae94e3be0a839b928379ada3c1b6135dfb004e334b17cf082e | db247f6ff4bc80552d3b02783c342fe3dc0bb7e5bdb3e6a54356c103a5ee3fb9 |
| manage-us-stock-strategy/tests/test_auto_core_rg1_oracle_parity.py | f0e93633139176dfc71ff4ea06178d64ab12f7849135835ed6523169ef1e6be0 | 7c129478d4c5c83973df14c2186864806aac51b7cc7b04eed8d42cce43c94c5b |
| manage-us-stock-strategy/tests/test_auto_core_risk1r.py | 2a95458c3563af25c077baa966f9ee8be918f78a9f18bfde407d6221672831f6 | 4d07b6b2f65d484453a11d1bd286de136b0998764b7ecf86e4c09e661ccce520 |
| manage-us-stock-strategy/tests/test_auto_core_rrec_bootstrap.py | 7a1832d2ca1a40de851071aa897dbbcbff391f26f3552338aaa84aa8d0cdcd9e | 56d2a61ef0056e201a4490ae51f3ef4db06ae8394fd85447f768d84de6e34d93 |
| manage-us-stock-strategy/tests/test_auto_core_rrec_ev4_remove.py (새) | 6c8db4bc21fbaa51127d992ae82391773c5fba43fd955b6ff0f6775b06003f74 | 631b284d7d2f936ad17e1a4f529db6a0294b8bb86f9ee2ad7e06139056a44d12 |
| manage-us-stock-strategy/tests/test_auto_core_rules.py | 0b457f6c5b7864c7aaa9605713f7b985785dff0d2f9523aed104ef9de266f0b8 | 10753a057905f562428c7bbaae072366572ead15ec9dd06c80eb5778ecf297d2 |
| manage-us-stock-strategy/tests/test_auto_core_t1_safety.py | b6d00d34907df4237bab30935d074b43bd695d352e05b7a4428838e6a80f4a3d | e242ea79c075d83fff703c68afa390deb7f9c807741dfb690ab8d58990b86837 |
| manage-us-stock-strategy/tests/test_auto_core_t2rc_corefix.py | a6402a15148f4f4facd9746445d4bfcd91c651fb588ab880633c1e2a800dd613 | a83b7001281319b5d87de6488900c5f5996d36e791fa96aa22376e154c12bcbc |
| manage-us-stock-strategy/tests/test_auto_core_tickets.py | b687a826c725c28c78c2fb967d31fe82e885601e5a3c963664cab838d69eac42 | 5e100d8656205cbd81ad052bdafc9222ffbdb4ffada5eca4d5105d7e9ab53b7f |
| docs/claude/rrec-ev4-remove-report.md (Builder 보고, 새) | 93bdd50b0edcc39eff2e1949a8d93ad3fc1cc0fc67cb7215a38d33243bf9de3c | d5a4c578e5cc81c4d6a3465a2b2afdd539db77e0e35d29d04e74698de87448da |

- 위 19개 코드·테스트·문서 파일의 작업 트리 sha256은 Builder 보고 6절 표의 값과 모두 같다.
- 새 계산기 sha256_lf = **6a74f813c918046b6e58b19087e1cee69b5984591a54639f84be0b47d0139d64** (= worktree 실행기 16행 `$ExpectedOracleSha256`).
- 새 실행기 sha256_lf = **593a067a848f5d6b27ff8b8ac2e086fa385efe5c83ec3ed88f00d8f19e9fbaf8** (base 실행기 sha256_lf fcd8977bac37034e7805dda7dd31756b8b6a224c6cdec673d45189c0cd1680a7, base 계산기 9f0e2238f2a8238016be5406cd2e195aaf24c232adeda5f1fba3a52cd09b1aae).

## 실행 기록 (Judge, 2026-10-19 19:4x~20:2x KST)
- 돌린 것: worktree·메인 각각 `test_auto_core*.py`(-v 포함)·`test_score_*.py`·`test_decision_journal_cards.py`·`validate_schema_contracts.py`·계산기 `selftest --repo <메인>`; 계산기 `check --day 2026-10-15·16·17 --repo <메인> --out <저장소 밖> --ignore-input-sha`(base판·worktree판); 저장소 밖 사본 두 개의 전체 스위트(test-runner 서브에이전트 실행, 로그는 Judge가 다시 읽음); 합성·재계산 스크립트(파일은 저장소 밖에만 씀).
- 돌리지 않은 것: 키움, auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply, 커밋·병합. workspace/outputs·stock-strategy-system·정책·예약 작업·관제판 쓰기 없음. 이 세션 동안 메인 체크아웃에서 바뀐 파일은 DevQueue 하트비트(예약 작업)뿐이고, 이 세션이 쓴 파일은 이 보고서 하나다.

VERDICT: PASS
