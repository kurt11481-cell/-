---
id: c1-keep2-judge-report
title: c1-keep2 확인 Judge 판정 (10-17 한 날 C1 셈 일회 복원)
date: 2026-10-20
prompt: docs/claude/c1-keep2-judge-prompt.md — Judge가 잰 sha256 a705ca8a6cf30914d11d979216cf56884d6f37649f8b923d4a1bd6b8ef705896 (판정 시작·끝 같음)
proposal: docs/claude/c1-keep-2026-10-20/README.md sha256 1d9ba88c54c5af71167d0592d1fb1b05f8c40a792a5ee5f7576b0321edaa6f20 — "c1-keep2 결정 기록" 절(46~49행), 사용자 "결정 c1-keep2: 10-17"(2026-10-20 15:46 KST 기록)
preregistration: docs/claude/t2-rc-preregistration-2026-10-14.md sha256 670f6df8bbfc87f54683f455f9f8e04d695671dd66a706a95bd20112fd30c5a4 (c1-keep Judge 때와 같음)
target: 메인 체크아웃 HEAD 4fe10b3d23192a99ebcea155ef8ccba0447e1fab (codex/master-recovery-expansion) · 계산기 docs/claude/t2rc-oracle.py sha256_lf 6a74f813c918046b6e58b19087e1cee69b5984591a54639f84be0b47d0139d64 · manage-us-stock-strategy 작업 트리 = HEAD(`git status --porcelain` 빈 결과)
class: K3 확인 Judge(읽기 전용) — 제안을 만들지 않은 새 세션, 메인 체크아웃, Opus 5.5 · xhigh, Windows 11 · Python 3.13.15 · git 2.56.0
authority: order_authority=false · quantity_authority=none · execution_quantity=null · 키움 호출 없음 · 저장소에 쓴 파일은 이 보고서 1개(복원 사본·계산기 --out·코어 재현 출력은 모두 저장소 밖 스크래치)
consumers: 사용자 적용 승인 판단("결정 c1-keep2 적용: 승인" 전) · Cowork(사전 등록 변경 기록 1줄·관제판 redesign-t2·t2-rc next "C1 2/10") · 다음 C1 관련 결정·Judge
order_authority: false
quantity_authority: none
---

# c1-keep2 확인 Judge 판정

**결론: PASS.** 2026-10-17 실행(평가 세션 2026-10-16) 한 날을 그날 판으로 다시 복원해 확인했다.

- 현행 계산기: `--ignore-input-sha` 없이 MATCH·counts_for_c1 true다. 원래 t2rc-check.json과 다른 키는 `oracle_sha256`·`ev4_history` 둘뿐이다.
- 현행 코어(decide 안에서 다시 도는 현행 S7 포함): 70칸이 모두 그날 decision.json과 같다.
- hwm-fix(210e951)는 10-17의 S7 HWM을 바꾸지만 멈춤은 바꾸지 않는다. 10-16 종가 자산이 옛·새 L2 문턱보다 모두 낮아서, 두 판 모두 L2가 열려 있기 때문이다.
- 차단 결함은 없다. 적용되면 C1은 1/10 → 2/10이다(10-17 + 10-20).

판정은 이 세션에서 연 원문과 직접 다시 계산한 값으로 했다. 앞 보고서·README·재검사 json의 숫자는 위치 안내로만 썼다.

## 판정 표

| # | 항목 | 판정 | 요지 |
|---|---|---|---|
| 1 | 계산기 재현(10-17) | **PASS** | MATCH · counts_for_c1 true · input_sha_mismatch [] · input_path_mismatch [] · historical_self_check false. 원래 t2rc-check.json과 차이 = `oracle_sha256`·`ev4_history`뿐(read_files 포함 그 밖 0, 부동소수 차이 0) |
| 2 | 현행 코어 재현(10-17) | **PASS** | 70/70칸 같음. 칸 밖 차이는 EV4 표지, 표시 칸 account.s7_hwm_usd, S7 review_id뿐 |
| 3 | 사이 변경 | **PASS** | 1259f566..HEAD 코어·계산기·실행기·정책 커밋 5개(넓은 경로 +1) 모두 분류, 분류 못 한 커밋 0. 210e951은 10-17 결과를 바꾸지 않음(원문 재계산) |
| 4 | 다른 셈 영향 | **PASS** | C1 누계를 코드로 세는 곳 없음. c3_record·C2·D0·C4·C5 불변 |
| 5 | 사전 등록 정합 | **PASS** | 0절 일회 예외 명시, README c1-keep2 결정 기록 있음, 한 날 한정, 24행 불변. 50·51행을 함께 인용하는 적용 문구 초안 제시 |
| 6 | 범위·안전 | **PASS** | `git status --porcelain` 전후 같음(+ 이 보고서 1줄). 권한 표지 불변, 키움·금지 실행 0 |

## 재현 방법 (모두 저장소 밖)

스크래치 폴더: `C:\Users\금동한\AppData\Local\Temp\claude\E-----------------\fd9e4335-235b-48bc-a01b-9d48e395d3dd\scratchpad`

- 스크립트는 `tools\`에 새로 썼다(build_root.py·guard.py·run_oracle.py·regen_history.py·run_core.py·cells70.py·jdiff.py). 앞 Judge의 복원 사본·결과는 쓰지 않았다.
- 사본(`w\`):
  - `oracle-1017`: 계산기용. 그날 decision.json·compare.json·s7/ 원본 포함, 파일 시각 보존.
  - `core-new-1017`: 현행 코어(작업 트리 = HEAD)의 manage-us-stock-strategy. 그날 폴더에는 T1 파일만 둠.
  - `core-old-1017`: 그날 커밋 1259f566의 manage-us-stock-strategy(`git archive`). 복원 검증용.
  - `core-s7old-1017`: 현행 코어 + 그날 커밋의 S7 두 모듈(portfolio_exposure.py·run_portfolio_exposure_review.py). 원인 분리용.
  - `oracle-1017-newcore`: 참고용. 현행 코어가 낸 decision.json·S7을 계산기 사본에 넣음.
- 복원 원천과 검증(build 검사 10~11개, 실패 0):
  - **그날 작업 트리 = 그날 커밋**: 10-17 decision.json `dirty_paths` 7개(Claude outputs 4·docs/claude/_to_delete 2·visualizations 1)에 판정 입력이 없다. git_provenance가 `--untracked-files=all`로 미추적 파일까지 적으므로(auto_core_reconcile.py:1166), 그 시각에 docs/claude의 다른 미추적 m6 파일도 없었다.
  - **추적 문서**: 1259f566 blob. 줄끝은 그날 inputs의 원시 sha로 골랐다.
    - card-evidence-registry.json = `--filters`(CRLF)판 dcb788c2
    - watchlist-registry.json = 원시 blob 75826e4f
    - recovery-gate-R-REC1 문서 = 원시 blob c056d542
    - m6-relative-comparison-7stock-2026-10-08.md = 원시 blob f3f56d3d(원래 read_files.m6와 같음)
  - 그날 커밋의 m6-7stock 파일은 10-08판 하나다. 2026-10-17판은 10-17 17:29에 생성됐다(실행 뒤).
  - 카드 문서 3개(integrated-stock-cards-v1·watch-card-LITE·watch-card-PWR)와 redesign-t2-compare-explained.json도 그날 커밋판을 썼다.
  - **정책·달력·식별 권한·alert_policy**: 1259f566..HEAD `git diff` 0, `git status --ignored` 빈 결과. 그래서 현재 바이트를 썼다. alert_policy sha 98ef14e0 = 그날 inputs.
  - **portfolio_state.json**: stock-strategy-system/backups/portfolio_state.r28.20261019T211506687301Z.json = ddcb987a = 그날 inputs.state. r28은 10-17 06:15 반영부터 10-20 06:15 백업까지의 상태다.
  - **reconciliation_ledger.jsonl**: 앞 14줄(바이트 그대로).
  - **decision_journal.json**: 앞 6건. 7~12번째 항목은 user_confirmed_at이 2026-10-19T08:23:48Z 이후라 그날 실행 때 없었다.
  - **출력**: auto-core 앞날 폴더 전부, reconciliation, research-records ≤ 10-17, corporate-actions.json. 파일 시각 ≤ 기준(코어 22:45:01Z, 계산기 23:40Z)이고, 늦게 바뀌어 빠진 파일은 0개다.
  - **30분 페이지**: 파일 이름 날짜 ≤ 20261017. 이름 기준과 파일 시각 기준이 어긋난 파일은 0개다.
  - **종가 이력**: 사본의 regular_session_close_history(1259f566..HEAD 변경 없음)로 T1 update_history와 같은 호출(build_history·history_errors, 같은 직렬화)로 다시 만들었다. MVLL cbd462db·NBIS a3bf75f6·SOXL 87ce2957·SOXX 1a603de3 = 그날 S7 inputs.close_histories.history_hash.
- **감사 훅(guard.py)**: 스크래치 밖 쓰기·하위 프로세스·소켓을 거부하고, 사본 밖 읽기(파이썬 설치 폴더 제외)를 기록한다. 계산기 2회·이력 재생성 3회·코어 3회 모두 거부 0건, 사본 밖 읽기 0건이었다(계산기 실행은 계산기 파일 자체만 예외).
- **계산기**: `python -I -B tools\run_oracle.py <사본> <out> 2026-10-17`. 메인 체크아웃의 docs/claude/t2rc-oracle.py를 runpy로 `check --day 2026-10-17 --repo <사본> --out <out>`으로 돌렸다. `--ignore-input-sha`는 쓰지 않았다.
- **코어**: `python -I -B tools\run_core.py <사본> <out>`. 별도 프로세스에서 사본의 `auto_core_decide.decide()`를 호출했다(REPO_ROOT가 사본이므로 기본 경로도 사본).
  - 시각: now = 원본 generated_at 2026-10-16T22:45:01.406215Z, clock = 원본 research wait started_at 22:45:01.909660Z.
  - S7 시각: run_s7이 `--now`를 넘기지 않으므로(auto_core_decide.py:258~274, run_portfolio_exposure_review.py:416~417·490) `current_time`만 원본 S7 파일 이름 시각(22:45:05.563376Z)으로 고정했다. `--now`를 넘기면 non_default_inputs에 "now"가 붙어 리뷰가 달라진다(같은 파일 544~545행).
  - 대역 3가지:
    - F6 키움 리더 = 빈 PASS 응답. 세 사본 모두 호출은 `account_open_items` 1건뿐이었다(원본 reasons []·f6_ran true와 같은 상태).
    - provenance = 원본 commit_sha·dirty_paths.
    - registry_committed_check = (True, None)(원본 inputs.registry.committed true).
  - 결과: 세 사본 모두 status OK·reasons []·tickets []·no_action NO_CIRCUIT_OPEN.
- **복원 검증(바이트 단위)**: 그날 커밋 코어(core-old)가 복원 입력으로 낸 파일이 원본과 바이트까지 같다. 입력 복원이 그날 판과 같다는 뜻이다.

| 파일 | 원본 sha256 앞 16자 | core-old | core-s7old | core-new |
|---|---|---|---|---|
| decision.json | 7884ecceee630d18 | 같음 | 5755304c3af8f64a | 2240b68434ed931e |
| compare.json | d5382de694300a3b | 같음 | 같음 | 같음 |
| s7/s7-earnings.json | 01f0293634ad957f | 같음 | 같음 | 같음 |
| s7/s7-proposals.json | 36f092691f32623f | 같음 | 같음 | 같음 |
| S7 리뷰(…20261016T224505563376Z.json) | e15dc88eb5656739 | 같음 | 같음 | 50a990fef0fd1b05 |

원본 decision.json sha 7884ecce…는 원래 t2rc-check.json의 decision_sha256과 같다.

## 항목 1 — 계산기 재현(10-17): PASS

| verdict | counts_for_c1 | input_sha_mismatch | input_path_mismatch | historical_self_check | 회로(계산기 = 코어) | 요건 diffs | tickets / leaks |
|---|---|---|---|---|---|---|---|
| MATCH | true | [] | [] | false | [] = [] | [] | [] / [] |

원래 t2rc-check.json(계산기 5607b09b)과 이 재현(6a74f813)의 깊은 비교에서 나온 차이 키 전부:

| 키 | 원래 | 재현 | 허용 |
|---|---|---|---|
| oracle_sha256 | 5607b09b…f02a26 | 6a74f813…9d64 | 허용 |
| ev4_history | ["2026-10-14","2026-10-15"] | (키 없음) | 허용 |

- 그 밖의 차이는 0이다. read_files(pages 344개·pages_combined_sha256 bfbed6fd·corporate_actions e9b6effc·s7_review e15dc88e·previous_decision bf4ad055·research_history 5개·m6 1개), decision.result_written_at, c3, exposure 부동소수 모두 같다. 1e-12 안의 부동소수 차이도 0건이다.
- 권한 표지: order_authority false · quantity_authority none · execution_quantity null.

## 항목 2 — 현행 코어 재현(10-17): PASS (70/70)

비교 70칸은 c1-keep Judge 보고서 77~81행 정의와 같다. 칸 목록은 앞 Judge 스크래치의 core_compare.py를 위치 안내로만 보고 맞췄고, 비교 코드는 새로 썼다(cells70.py).
- candidates·tickets·blocked: 3
- buy_requirements: 코드 목록 1 + 8종목 × (s 목록·add) 16
- evidence: 종목 목록 1 + 8종목 × 매수·매도 × basis_met·new_basis_met 32
- shock: status·open·rg·사건 날짜·사건 kinds(원본에서 EV4 뺌)·event 날짜·event kinds(EV4 뺌)·event c0/l0/bench 8 + by_symbol 키 1 + by_symbol 8종목(status·open·rg) 8

| 사본 | 같은 칸 | decision.json의 칸 밖 차이 전부 |
|---|---|---|
| core-new(현행 코어, 현행 S7) | **70/70** | account.ev4_open true → 없음 · ev4_backfill [] → 없음 · shock.events[10~12].kinds·shock.event.kinds ["EV2","EV4"] → ["EV2"](dashboard.runCore.shock 사본 같음) · account.s7_hwm_usd "30255.3600" → "31711.7600" · inputs.s7_review.review_id 7990ea27… → eb51084e… |
| core-s7old(현행 코어, 그날 S7) | 70/70 | EV4 표지만(위 목록에서 s7_hwm_usd·review_id 없음). S7 리뷰는 원본과 바이트까지 같음 |
| core-old(그날 커밋 코어) | 68/70 | decision.json이 원본과 바이트까지 같음. 비교기가 원본에서 EV4를 빼고 비교하므로 EV4 칸 2개가 걸린다(비교기가 EV4 차이를 잡는다는 확인) |

- 10-17의 70칸 값: candidates []·tickets []·blocked []. 요건 ②는 8종목 모두 no다(S7 신규·추가 멈춤). shock은 status no·open true·RG1~RG4 no/no/no/ok·event 10-16·by_symbol 8종목 같은 값이다.
- 현행 S7 리뷰와 원본 S7 리뷰의 차이는 47개 경로다. HWM(30,255.36·10-05 → 31,711.76·10-06), 검토선 문턱·거리, L1·L2 돌파일(10-14 → 10-12, 10-16 → 10-15), 그 알림 2개의 breach_date, revalued_sessions·superseded_journal_reviews(새 키), review_id다.
- 같은 비교에서 pauses·recommendations·exposure·equity·band·peak_reviews·single_stock_cap·fail_closed는 차이가 없다. 그래서 decide가 S7에서 받는 멈춤·권고가 같고, 70칸이 같다.

## 항목 3 — 사이 변경: PASS (분류 못 한 커밋 0)

명령 `git log --format='%h %ci %s' 1259f566c729f9a4197359b4495b60821adef59d..HEAD -- manage-us-stock-strategy/scripts docs/claude/t2rc-oracle.py docs/claude/t2rc-check-run.ps1 workspace/policies/auto_core.json stock-strategy-system/alert_policy.json`의 결과는 5개다. 경로를 manage-us-stock-strategy 전체·workspace/policies 전체·달력·식별 권한·stock-strategy-system·tools로 넓히면 5190fe2 1개가 더 나온다.

| 커밋 | 시각(KST) | 바뀐 파일(넓은 경로 한정) | 분류 | 근거(원문) |
|---|---|---|---|---|
| 210e951 | 10-17 17:17 | portfolio_exposure.py·run_portfolio_exposure_review.py(+테스트) | 항목 2가 덮음 — **10-17 결과 불변** | 아래 "210e951 원문 확인" |
| 55133ae | 10-18 07:12 | t2rc-oracle.py·t2rc-check-run.ps1·auto_core_decide/inputs/rules/tickets.py·auto-core-card-registry.schema.json·references(+테스트) | 항목 1·2가 덮음 — 칸 불변 | RG1 정의 변경. 계산기 차이는 sha·ev4_history뿐(항목 1). 코어는 shock.rg·by_symbol rg 포함 70/70(항목 2). core-s7old에서도 EV4 표지 밖 차이가 없다 |
| 5190fe2 | 10-18 10:16 | stock-strategy-system/backtests/rrec_ev4_anchor_replay_2026-10-18.* | 그날 결과와 무관(넓은 경로에서만 나옴) | 리플레이 기록 파일이다. 복원 사본에 넣지 않았고, 계산기·코어 실행의 사본 밖 읽기는 0건이었다 |
| 67e781d | 10-18 11:58 | host_status.ps1·run_journal_score.ps1(+테스트) | 그날 결과와 무관 | PowerShell 감시·주간 채점 실행기다. decide 안의 채점은 decision_mode apply일 때만 돈다(auto_core_decide.py:709 `if mode == "apply":` 블록 안 742행 `_score`, 파이썬 score_decision_journal). 10-17은 compare였다. 코어 실행 중 하위 프로세스는 0건이다(훅) |
| 6d4d6f3 | 10-19 20:39 | t2rc-oracle.py·t2rc-check-run.ps1·auto_core_decide/replay/rules.py·auto-core-decision.schema.json·references(+테스트) | 항목 1·2가 덮음 — 허용 차이(EV4)만 | ev4_history·shock kinds의 EV4·account.ev4_open·ev4_backfill이 빠진다(항목 1·2 차이 목록과 같음). auto_core_replay.py는 decide가 쓰지 않는다 |
| 4fe10b3 | 10-20 11:39 | host_status.ps1·offsite_backup.ps1·register_offsite_backup_task.ps1(+테스트) | 그날 결과와 무관 | 백업·감시용 PowerShell이다. decide·계산기 경로 밖이고, 하위 프로세스 0건이다 |

- 실행기 docs/claude/t2rc-check-run.ps1의 1259f566..HEAD 차이는 16행 `$ExpectedOracleSha256`(5607b09b… → 6a74f813…) 한 줄뿐이다.
- auto_core.json·alert_policy.json은 범위 안에서 바뀌지 않았다(`git diff` 0). auto_core.json decision_mode는 compare다.
- 병합 커밋의 내용은 위 커밋과 같다: 10c08b2(10-17, 부모 1259f56·210e951), 0d55b9a(10-18, 부모 073582d·55133ae), 5d5cf79(10-19, 부모 80d3a1d·6d4d6f3).

### 210e951 원문 확인 (10-17에서 S7 멈춤이 같은 이유)
1. 정책 stock-strategy-system/alert_policy.json:825~826:
   - L1 = fraction_of_hwm 0.90, 멈춤 없음
   - L2 = 0.80, pause_add_recommendations·pause_new_buy_recommendations true
2. 멈춤 사유 코드는 두 판이 같다: 현행 portfolio_exposure.py:1378~1386 = 그날 판(1259f566) 1167~1175. 열린 사건 중 멈춤 표시가 있는 선 → `REVIEW_LINE_OPEN:<선>`.
3. 재계산:
   - 옛 HWM 30,255.36(10-05): L1 27,229.824 · L2 24,204.288
   - 새 HWM 31,711.76(10-06, POST_CLOSE 재평가, state rev 20): L1 28,540.584 · L2 25,369.408
   - 평가 세션 10-16 종가 자산 23,695.4314는 두 L2보다 모두 낮다(Decimal 비교 True·True).
4. 두 리뷰의 열린 사건(원문):
   - 원본 L1(10-14)·L2(10-16), 현행 L1(10-12)·L2(10-15). 두 쪽 모두 L2가 pause true다.
   - pauses는 두 쪽 모두 add·new_buy paused true, reasons ["REVIEW_LINE_OPEN:L2"]다.
5. 그래서 decide의 요건 ②·blocked가 같다. 바뀌는 것은 표시 칸 account.s7_hwm_usd와 S7 리뷰 안의 HWM·문턱·돌파일뿐이다.
   - 이 HWM·돌파일은 210e951 커밋 메시지의 "Real data: HWM 31711.76 (2026-10-06), L1 2026-10-12, L2 2026-10-15"와 같다.
   - 10-16(c1-keep FAIL B1)과 다른 점: 10-16에는 평가 세션 10-15 종가 25,252.58이 옛 L2(24,204.288)보다 높고 새 L2(25,369.408)보다 낮아서 멈춤이 달라졌다. 10-17에는 그런 사이 구간이 없다.

## 항목 4 — 다른 셈 영향: PASS

- C1 누계를 코드로 세는 곳은 없다(저장소 grep, workspace/outputs 제외). `counts_for_c1`이 나오는 코드는 다음뿐이다.
  - t2rc-oracle.py:1450(초기값 false)·1634(하루 단위 플래그: MATCH/MISMATCH이고 compare 모드).
  - t2rc-check-run.ps1:41: 실행기 오류 때 false를 쓴다.
  - docs/claude/scheduled-prompts/ceo-weekly/ceo.py:158과 pending-ceo-weekly 사본들: 날마다 "(C1 셈)" 표시만 한다.
- 누계는 ceo.py:210~211이 관제판 redesign-t2 next의 "C1 … n/10" 문구를 정규식으로 인용할 뿐이다. 문구가 없으면 "확인 필요"로 둔다.
- auto-core-alert.txt:76~77은 그날 t2rc-check의 c1.match·missing·extra를 표시줄에 쓴다. manage-us-stock-strategy/scripts auto_core*의 "t2rc"는 t2rc-corefix 주석뿐이다. tools/에는 없다(dev-run.ps1:318의 "C1"은 AppId GUID의 일부).
- c3_record(t2rc-oracle.py:1672~1674)는 apply 모드이고 같은 계산기 sha이고 self-check가 아닌 앞날 기록만 센다. 10-17 기록은 compare 모드·옛 sha 5607b09b·주문표 0이다. 제안은 t2rc-check.json을 고치지 않는다(README 48행). → C3는 그대로다.
- C2(사전 등록 25~26행, 50·51행 "병합 전 C2 일치는 세지 않는다"): 10-17 decision.json tickets []이라 영향이 없고, 제안도 그대로 둔다.
- D0(10-16)·C4·C5: 제안 본문(Judge 지시문 "10-16·D0·C2·C3·C4·C5·24행 초기화 규칙은 그대로")과 README 46~48행이 바꾸지 않는다. C4는 D0부터 회로·주문표·막힌 사유를 세는 것이라 C1 셈과 따로다.
- C1 산수:
  - 지금 1/10이다. 10-20 실행(세션 10-19)의 t2rc-check.json = MATCH·counts_for_c1 true·계산기 6a74f813·compare이고, 사전 등록 51행 재시작점이다.
  - 적용하면 2/10이다(10-17 + 10-20).
  - 10-18·10-19 실행일에는 decide 폴더가 없다(auto-core 폴더 목록).

## 항목 5 — 사전 등록 정합: PASS

- **0절(16행)** "아래 숫자는 이후 느슨하게 바꾸지 않는다. Judge는 더 엄격하게만 바꿀 수 있고": 버린 세션을 다시 세는 것은 느슨하게 하는 쪽이다. 제안은 이를 일회 예외로 밝힌다.
  - README 48행 "등급·순서: K3(사전 등록 0절 일회 예외, 범위 축소)"
  - Judge 지시문 class 줄 "1절 C1 초기화(24·50·51행)의 일회 예외"
- **사용자 결정 기록**: README 46행 "2026-10-20 15:46 KST 사용자 원문: "결정 c1-keep2: 10-17" (Cowork 대화)".
  - 대화 원문은 이 세션에서 열 수 없다(확인 필요).
  - PASS 조건은 README c1-keep2 절의 결정 기록이 있는 것이고, 그 조건은 충족한다. 적용 승인은 별도 사용자 원문 "결정 c1-keep2 적용: 승인"이 필요하다(README 48행).
- **한 날 한정**: README 46행 "2026-10-17(평가 세션 10-16) 한 날만 C1에 다시 센다 … 10-16은 계속 세지 않는다".
- **24행 불변**:
  - README 48행 "코드·계산기·실행기·t2rc-check.json·정책·상태 불변"
  - README 33행 "상시 규칙화(b)는 하지 않는다"
  - 지시문 제안 "24행 초기화 규칙은 그대로"
- **50·51행(c1-keep Judge N2) 해소**: README 48행이 "사전 등록 변경 기록 1줄(50·51행 함께 인용, Judge N2)"로 정했다. 10-17은 50행(10-18 ev-rg1-hyper, 병합 0d55b9a) 초기화로 빠졌고, 51행(10-19 rrec-ev4-remove, 병합 5d5cf79) 초기화도 거쳤다.
- **적용 문구 초안**(1줄, 사용자 적용 승인 뒤 Cowork가 사전 등록 변경 기록 끝에 덧붙일 문구):
  `- 2026-10-2x KST c1-keep2(사용자 결정 "결정 c1-keep2: 10-17" 10-20 15:46, 적용 승인 원문 "결정 c1-keep2 적용: 승인" …, 확인 Judge PASS docs/claude/c1-keep2-judge-report.md): 0절의 일회 예외 — 50행(ev-rg1-hyper, 병합 0d55b9a)·51행(rrec-ev4-remove, 병합 5d5cf79) 초기화로 버린 실운영 비교 세션 2026-10-17(평가 세션 10-16) 한 날만 C1에 다시 센다(현행 계산기 6a74f813…·현행 코어 HEAD 4fe10b3으로 그날 입력 재현 일치, 차이는 EV4 표지뿐) → C1 2/10. 2026-10-16(평가 세션 10-15)은 세지 않는다. 24행 초기화 규칙·앞으로의 초기화·C2(병합 전 일치 불산입)·C3·D0(10-16)·C4·C5는 그대로.`

## 항목 6 — 범위·안전: PASS

- `git status --porcelain`: 시작(15:50 KST)과 보고서 쓰기 직전(16:12 KST) 모두 47줄이고 diff가 없다. 보고서를 쓴 뒤 늘어나는 것은 `?? docs/claude/c1-keep2-judge-report.md` 1줄이다. HEAD는 4fe10b3 그대로다.
- 세션 중 저장소 안에서 시작 시각 뒤에 바뀐 파일은 workspace/outputs/dev-runs/_queue/의 heartbeat.txt·last-queue-take.err·last-queue-take.out 3개뿐이다(검사 범위: docs·manage-us-stock-strategy·stock-strategy-system·tools·workspace/policies·calendar-authority·instrument-identity-authority, workspace/outputs의 auto-core·research-records·regular-session-closes·reconciliation·dev-runs). 세 파일은 Windows 작업 InvestmentV2-DevQueue가 16:10:02에 쓴 것이다(heartbeat 2026-10-20T07:10:02Z). 이 세션의 쓰기는 감사 훅 기록상 모두 스크래치 안이고, .pyc는 만들지 않았다(`python -I -B`, 계산기는 runpy).
- 권한 표지:
  - 재현 decision.json 3개 모두 order_authority false·execution_quantity null·decision_mode compare·tickets []다.
  - 계산기 출력 2개도 order_authority false·quantity_authority none·execution_quantity null이다.
- 금지 실행 0:
  - 키움 호출 0(리더 대역, 소켓 거부 훅).
  - auto_core.py·run_auto_core.ps1·t2rc-check-run.ps1·dev-run·dev-merge·reconcile apply는 실행하지 않았다.
  - 커밋·병합·테스트 실행은 없다.
  - workspace/outputs·stock-strategy-system·docs/claude(이 보고서 제외)·정책·예약 작업·관제판에는 쓰지 않았다.

## 차단 결함

- 없음.

## 비차단 관찰

- N1: 현행 S7(210e951 뒤)은 10-17에도 HWM·L1/L2 돌파일을 바꾼다(표시 칸 account.s7_hwm_usd 30,255.36 → 31,711.76, 70칸 밖). 10-17에서 멈춤이 같은 것은 평가 세션 종가가 두 L2 문턱 아래에 있어서다(항목 3 재계산). 규칙이 같아서가 아니다. 다른 날을 같은 방식으로 되살리려면 그날마다 다시 확인해야 한다.
- N2: 현재 일지 7~12번째 항목(line_review_completed·peak_review_card_completed, evaluation_session 2026-10-16, user_confirmed_at 2026-10-19T08:23Z~08:31Z)은 그날 입력이 아니어서 복원에서 뺐다. 지금 저장소의 일지를 그대로 넣고 재현하면 S7 superseded_journal_reviews 등이 달라질 수 있다. 그날 판 재현과는 무관하다.
- N3: 이 Judge가 독립으로 만든 결과 파일이 앞 Judge의 같은 이름 결과와 sha256 앞 8자리가 같다(t2rc-check 5d04c861, 현행 코어 출력의 계산기 결과 d7e47961, c1-keep 보고서 실행 기록 표). 판정 근거가 아니라 참고다.
- N4: 앞 Judge 스크래치 폴더(d952b7dc…)가 아직 남아 있다. 이 Judge는 70칸 묶음을 맞추려고 그 안의 core_compare.py만 위치 안내로 읽었고, 사본·결과는 쓰지 않았다.
- N5: 복원은 이번에도 저장소 안 자료만으로 됐다. state 백업 r28이 있었고(10-20 06:15 생성), 원장·일지는 앞부분 자르기로 됐다. 그날 입력을 그날 보관하는 장치는 아직 없다(c1-keep N3과 같은 취지).

## 의견 (판정과 별개)

- PASS이므로 README 48행 순서대로 진행한다. 사용자 "결정 c1-keep2 적용: 승인" → Cowork가 사전 등록 변경 기록 1줄(위 초안) + 관제판 redesign-t2·t2-rc next "C1 2/10". 승인이 없으면 기본 처분 NO_CHANGE(C1 1/10)다.
- 노출·예산·권한을 올리는 효과는 없다. C1은 비교 모드 판정 증거 셈일 뿐이고, "켜"에는 여전히 C2·R2·R-A·사용자 "켜"가 모두 필요하다(README 35행).
- 이 판정이 바뀔 조건:
  - 적용 전에 코어·S7·계산기·실행기 코드가 바뀌어 "현행"이 4fe10b3·6a74f813과 달라진다(그때는 10-17 재현을 다시 해야 한다).
  - 적용 문구가 10-16을 넣거나 24행·앞으로의 초기화를 바꾼다.
  - 사용자 결정 원문이 README 46행 기록과 다르다.

## 실행 기록 (Judge, 2026-10-20 15:50~16:14 KST)

- 돌린 것(모두 위 스크래치 폴더):
  - 복원 사본 생성·검증 4회(build_root.py: oracle·core-new·core-old·core-s7old)
  - 종가 이력 재생성 3회
  - 계산기 check 2회(원본 decision 1회 + 현행 코어 decision 1회, 참고)
  - 코어 decide 재현 3회(현행 코어·그날 커밋 코어·현행 코어+그날 S7)
  - JSON 비교(cells70.py·jdiff.py)
- 결과 파일 sha256(스크래치 out/):

| 파일 | sha256 앞 8자리 |
|---|---|
| t2rc-check-2026-10-17.json | 5d04c861 |
| t2rc-check-newcore-2026-10-17.json | d7e47961 |
| cells70-core-new.json | 9f73f71c |
| cells70-core-s7old.json | c7eedbc7 |
| cells70-core-old.json | 7eb51cc8 |
| s7diff-core-new.json | 466937f0 |
| run-core-new.json | fbb11be4 |
| run-core-old.json · run-core-s7old.json | 3ae370fa |

  스크래치는 세션 임시 폴더라 남지 않는다. 판정에 쓴 값은 이 보고서에 옮겨 두었다.
- 돌리지 않은 것:
  - 키움, auto_core.py·run_auto_core.ps1·t2rc-check-run.ps1·dev-run·dev-merge·reconcile apply
  - 테스트(판정에 필요 없음), 커밋·병합
  - workspace/outputs·stock-strategy-system·docs/claude(이 보고서 제외)·정책·예약 작업·관제판 쓰기

VERDICT: PASS
