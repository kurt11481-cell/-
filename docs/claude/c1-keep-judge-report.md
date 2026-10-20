---
id: c1-keep-judge-report
title: c1-keep 독립 Judge 판정 (10-16·10-17 C1 셈 일회 복원)
date: 2026-10-20
prompt: docs/claude/c1-keep-judge-prompt.md — Judge가 잰 sha256 4ec8421f8275476861b060b8a8b01f041d53e6faf84a18078624054e2aa11940 (판정 중·끝 같음)
proposal: docs/claude/c1-keep-2026-10-20/README.md sha256 3f4bb0d6a1fec1847f9b715a5c85d946288539ba0ce40064b976c744a6966f93 — 사용자 "결정 c1-keep: a"(README 33행 기록, 2026-10-20 14:51 KST)
preregistration: docs/claude/t2-rc-preregistration-2026-10-14.md sha256 670f6df8bbfc87f54683f455f9f8e04d695671dd66a706a95bd20112fd30c5a4
target: 메인 체크아웃 HEAD 4fe10b3d23192a99ebcea155ef8ccba0447e1fab (codex/master-recovery-expansion) · 계산기 docs/claude/t2rc-oracle.py sha256_lf 6a74f813c918046b6e58b19087e1cee69b5984591a54639f84be0b47d0139d64 · manage-us-stock-strategy 작업 트리 = HEAD(`git status` 빈 결과)
class: K3 독립 Judge(읽기 전용) — 제안을 만들지 않은 새 세션, 메인 체크아웃, Opus 5.5 · xhigh, Windows 11 · Python 3.13.15 · git 2.56.0
authority: order_authority=false · quantity_authority=none · execution_quantity=null · 키움 호출 없음 · 저장소에 쓴 파일은 이 보고서 1개(복원 사본·계산기 --out·코어 재현 출력은 모두 저장소 밖 스크래치)
consumers: 사용자 적용 승인 판단("결정 c1-keep 적용: 승인" 전) · Cowork(사전 등록 변경 기록·관제판 redesign-t2·t2-rc next) · 다음 C1 관련 결정·Judge
order_authority: false
quantity_authority: none
---

# c1-keep 독립 Judge 판정

**결론: FAIL.** 계산기 재현(항목 1)은 두 날 모두 통과했다. 그러나 현행 코어 재현(항목 2)에서 10-16이 그날 결과와 다르다. hwm-fix(210e951, 10-17 병합)로 바뀐 S7이 10-15 종가에서 L2 선을 열어, 매수 요건 ②가 6종목에서 ok → no로 바뀌고 DELL·MU의 막힘 사유가 늘어난다. 이 차이는 허용 차이(EV4) 밖이다. C1이 비교하는 회로 집합(DELL·MU 매수)은 그대로다. 기본 처분은 NO_CHANGE(C1은 10-20부터 센 1/10 유지)다.

판정은 이 세션에서 연 원문과 직접 다시 계산한 값으로 했다. README·재검사 json·앞선 Judge 보고서의 숫자는 위치 안내로만 썼다.

## 판정 표

| # | 항목 | 판정 | 요지 |
|---|---|---|---|
| 1 | 계산기 재현 | **PASS** | 두 날 MATCH · counts_for_c1 true · input_sha_mismatch [] · input_path_mismatch [] · historical_self_check false. 원래 t2rc-check.json과 차이 = `oracle_sha256`·`ev4_history`뿐 |
| 2 | 새 코어 재현 | **FAIL** | 10-17은 70/70칸 같음(차이는 EV4 표지뿐). 10-16은 63/70칸: 요건 ② 6종목 ok → no, blocked 사유 2개 추가. 원인 210e951(S7 HWM D6) |
| 3 | 사이 변경 전수 | **PASS** | 범위 안 7개 커밋 모두 분류(분류 못 한 커밋 0). 210e951은 "항목 2가 덮음 — 10-16 결과를 바꿈" |
| 4 | 다른 셈 영향 | **PASS** | C1 누계를 코드로 세는 곳 없음. c3_record·C2·D0·C4·C5 불변 |
| 5 | 사전 등록 정합 | **PASS** | 0절 예외임을 밝힘, README 결정 기록 있음, 두 날 한정, 24행 불변. 비차단: 50·51행을 함께 적어야 함 |
| 6 | 범위·안전 | **PASS** | `git status --porcelain` 전후 같음(+ 이 보고서 1줄). 권한 표지 불변, 키움·금지 실행 0 |

## 재현 방법 (모두 저장소 밖)

스크래치 폴더: `C:\Users\금동한\AppData\Local\Temp\claude\E-----------------\d952b7dc-41d6-4074-ab0d-0c2dffa26113\scratchpad`

- 날마다 사본을 따로 만들었다: `oracle-<날>`(계산기용, 그날 decision.json 원본 포함, 파일 시각 보존)과 `core-<날>`(코어용, 그날 폴더에는 T1 파일만 둠). 분리 실험용으로 `s7old-<날>`·`corexs7old-<날>`도 만들었다(S7 두 모듈만 그날 커밋 판으로 바꿈).
- 복원 원천과 검증(사본마다 34~40개 검사, 모두 일치):
  - **추적 문서**: 그날 decision.json `commit_sha`(10-16 ad127596…, 10-17 1259f566…)의 blob. 그날 작업 트리 기준으로 watchlist-registry.json·recovery-gate-R-REC1 문서·m6 10-08 문서는 LF였다. blob 원본 = 75826e4f·332a416e(10-16)/c056d542(10-17)·f3f56d3d였고, `git cat-file --filters`의 CRLF판은 eaff1078 등으로 달랐다. card-evidence-registry.json은 CRLF판(--filters)이 dcb788c2로 일치했다. 카드 문서 3개(integrated-stock-cards-v1·watch-card-LITE·watch-card-PWR)는 그날 커밋 판을 썼다. 코어(auto_core_inputs.py:64~66)와 계산기(t2rc-oracle.py:726)가 모두 CRLF를 정규화하므로 줄끝은 결과와 무관하다.
  - **m6**: 그날 커밋에 있는 것은 m6-relative-comparison-7stock-2026-10-08.md 하나다. 2026-10-17 판은 10-17 17:29에 생성됐고 커밋 88a207a는 10-17 23:30이다(두 실행 뒤).
  - **portfolio_state.json**: stock-strategy-system/backups/portfolio_state.r27.20261016T211506926147Z.json = bdc2720a(10-16), r28.20261019T211506687301Z.json = ddcb987a(10-17).
  - **reconciliation_ledger.jsonl**: 앞 13줄(10-16)·14줄(10-17). 그날 S7 기록의 ledger_entries·ledger_last_entry_sha256(9eac42bf…·a082babb…)와 일치한다.
  - **decision_journal.json**: 앞 6건. load_journal head 54d5aecc…가 두 날 S7 기록의 journal_head_sha256과 같다.
  - **30분 페이지**: 파일 이름 날짜 ≤ 실행일(10-16: 334개, 10-17: 344개). pages_count·pages_combined_sha256이 원래 t2rc-check.json read_files(a28767f4…·bfbed6fd…)와 같다. 종가 이력은 그 페이지로 T1 update_history와 같은 함수(build_history·history_errors·_write)로 다시 만들었고, S7 기록의 history_hash 6개(10-16)·4개(10-17)가 일치한다.
  - 그 밖: corporate-actions.json e9b6effc, research-records ≤ 실행일(sha 4개·5개 일치), 앞날 decision.json(read_files.previous_decision 일치), S7 리뷰 원본(c9bde7ea…·e15dc88e…), 정책·달력·식별 권한 트리(그날 커밋 이후 diff 없음, 작업 트리 깨끗), decision.json 파일 시각 원본과 같음. 그날 decision.json inputs의 sha 9개와 calendar(2421eeb7…)도 모두 일치한다.
- **계산기**: `python docs/claude/t2rc-oracle.py check --day <날> --repo <scratch>/oracle-<날> --out <scratch>/out/t2rc-check-<날>.json`. `--ignore-input-sha`는 쓰지 않았다.
- **코어**: 메인 체크아웃 manage-us-stock-strategy를 바이트 그대로 복사한 사본에서 별도 python 프로세스로 `auto_core_decide.decide()`를 호출했다. REPO_ROOT가 사본이므로 기본 경로도 모두 사본을 가리킨다.
  - 시각: now = 원본 generated_at, clock = 원본 research wait started_at.
  - S7 시각: run_s7이 `--now`를 넘기지 않으므로(auto_core_decide.py:258~274, run_portfolio_exposure_review.py:416~417) `current_time`만 원본 S7 파일 이름의 시각으로 고정했다. 그래서 같은 파일 이름·같은 평가 세션으로 돈다.
  - 대역 3가지:
    - F6 키움 리더 = 빈 PASS 응답. 호출 기록은 두 날 모두 `account_open_items` 1건뿐이었다(대기 주문표 0, 원본 reasons []와 같은 상태).
    - provenance = 원본 commit_sha·dirty_paths.
    - registry_committed_check = (True, None)(원본 inputs.registry.committed true).
  - 감사 훅으로 스크래치 밖 쓰기·하위 프로세스·소켓을 막았다. 거부 0건, 사본 밖 읽기 0건(파이썬 설치 폴더 제외), 결과 status OK·reasons [].

## 항목 1 — 계산기 재현: PASS

| 날 | verdict | counts_for_c1 | input_sha_mismatch | input_path_mismatch | historical_self_check | 회로(계산기 = 코어) | 요건 diffs | tickets / leaks |
|---|---|---|---|---|---|---|---|---|
| 10-16 | MATCH | true | [] | [] | false | DELL 매수·MU 매수 = 같음 | [] | [] / [] |
| 10-17 | MATCH | true | [] | [] | false | 없음 = 없음 | [] | [] / [] |

원래 t2rc-check.json(계산기 5607b09b)과 이 Judge 재현(6a74f813)의 차이 키 전부:

| 날 | 키 | 원래 | 재현 | 허용 |
|---|---|---|---|---|
| 10-16 | oracle_sha256 | 5607b09b…f02a26 | 6a74f813…9d64 | 허용 |
| 10-16 | ev4_history | ["2026-10-14"] | (키 없음) | 허용 |
| 10-17 | oracle_sha256 | 5607b09b…f02a26 | 6a74f813…9d64 | 허용 |
| 10-17 | ev4_history | ["2026-10-14","2026-10-15"] | (키 없음) | 허용 |

- 그 밖(read_files·decision.result_written_at·c3·exposure 부동소수 포함)은 차이 0이다. 복원이 그날 판과 같아서 read_files까지 원래와 같다.
- README 재검사 json과 비교하면 read_files만 다르다. README 쪽은 pages 354개와 m6 2개를 읽었고(현재 저장소의 전체 페이지와 10-17 m6 판), 경로 구분자도 / vs \로 다르다. 이 밖에는 10-16 exposure.E_oracle·V_oracle의 차 5.6e-16(≤ 1e-12)뿐이다. c1·requirements·tickets·ticket_leaks·c3·verdict는 같다.

## 항목 2 — 새 코어 재현: FAIL (10-16) · 10-17은 통과

비교 70칸:
- candidates·tickets·blocked
- buy_requirements: 코드 목록, 8종목 × (6칸 s 목록 + add)
- evidence: 8종목 × 매수·매도 × basis_met·new_basis_met
- shock: status·open·rg·사건 날짜·사건 kinds(EV4 제외)·event·by_symbol 8종목

| 날 | 현행 코어(decide 안의 현행 S7 포함) | 다른 칸 |
|---|---|---|
| 10-17 | 70/70 같음 | 허용 차이만: shock events 10-14·10-15·10-16과 event의 kinds에서 EV4가 빠짐, account.ev4_open·ev4_backfill 없음. 항목 밖 표시 칸 account.s7_hwm_usd는 30255.36 → 31711.76 |
| 10-16 | **63/70** | buy_requirements ②(c[1].s) BE·DELL·LITE·MU·NBIS·PWR: ok → **no**. blocked DELL·MU: ["REQ5_RREC1:no"] → ["REQ2_EXPOSURE_CASH_PRODUCT:no","REQ5_RREC1:no","G2:REVIEW_LINE_OPEN:L2"] |

10-16에서 같은 칸:
- candidates [DELL buy NEW_EVIDENCE, MU buy NEW_EVIDENCE], tickets []
- evidence 32칸
- shock: status no·open true·RG1~RG4 no/no/no/ok·사건 10-15·by_symbol 8종목. EV4 표지만 다르다.
- MVLL·SOXL의 ②는 원래도 no였다(문구만 바뀜).

### 원인 분리 (원문 재계산)
1. 그날 커밋의 S7 두 모듈(portfolio_exposure.py·run_portfolio_exposure_review.py, ad127596/1259f566 판)을 같은 복원 입력, 같은 시각, 원본 s7-earnings·s7-proposals로 돌리면 원래 S7 리뷰와 **차이가 0**이다(review_id 43dfbf22…·7990ea27… 그대로). → 입력 복원은 정확하다.
2. 현행 S7(210e951 뒤)을 같은 입력으로 돌린 결과:
   - HWM이 30,255.36(10-05)에서 31,711.76(10-06, POST_CLOSE 재평가, state rev 20)으로 바뀐다.
   - L2 문턱 0.8 × 31,711.76 = 25,369.408이 10-15 종가 자산 25,252.58보다 높다 → 10-15에 L2가 열린다.
   - 그래서 pauses.new_buy_recommendations·add_recommendations = true(REVIEW_LINE_OPEN:L2)가 된다.
   - 원래 S7에서는 L2 문턱이 0.8 × 30,255.36 = 24,204.288로 25,252.58보다 낮아 열리지 않았고 멈춤도 false였다.
   - 이 값은 210e951 커밋 메시지의 "Real data: HWM 31711.76 (2026-10-06), L1 2026-10-12, L2 2026-10-15"와 같다.
3. 현행 코어 + 그날 S7 모듈로 돌리면 두 날 모두 70/70칸이 같다(차이는 EV4 표지·account.ev4_open·ev4_backfill뿐, S7 리뷰 차이 0, s7-proposals 같음). → auto_core_* 변경(04f9a85·55133ae·6d4d6f3)은 두 날 결과를 바꾸지 않는다. 10-16 차이는 전부 210e951에서 온다.
4. 10-17은 원래 S7에서도 L2가 이미 열려 있었다(10-16 종가 23,695.43 < 24,204.288). 멈춤이 같으므로 칸도 같다.

### C1 영향 (참고, 판정 기준 아님)
- 현행 코어가 쓴 10-16·10-17 decision.json과 S7 리뷰를 계산기 사본에 넣고(파일 시각은 원본과 같게) 같은 계산기를 돌렸다. 두 날 모두 MATCH·counts_for_c1 true이고, 회로 집합이 같고, 요건 차이는 []다. 계산기도 새 S7 리뷰를 읽어 ② = no로 계산하기 때문이다.
- S7이 회로에 들어가는 길(t2rc-oracle.py:1293 s7_add, 1301 s7_reduce)은 닫혀 있다. 옛·새 S7 모두 add·reduce 권고가 []이기 때문이다.
- 즉 C1이 세는 칸은 그대로다. 그러나 사전에 정한 항목 2 기준(요건 칸·blocked 동일, 허용 차이는 EV4만)은 10-16에서 어긋난다. Judge는 기준을 느슨하게 바꿀 수 없다(사전 등록 16행) → FAIL.
- 해석을 바꿔도 결론은 같다.
  - S7을 코어의 일부로 보면 항목 2가 FAIL이다.
  - S7 리뷰를 "그날 입력"으로 보더라도, 항목 3에서 210e951을 "그날 결과와 무관"으로 분류할 수 없다(위 2). 같은 결함이 항목 3으로 옮겨갈 뿐이다.

## 항목 3 — 사이 변경 전수: PASS (분류 못 한 커밋 0)

명령 `git log --format='%h %ci %s' ad127596badd3bfab74e9de835d09d62e0a4e043..HEAD -- manage-us-stock-strategy/scripts docs/claude/t2rc-oracle.py docs/claude/t2rc-check-run.ps1 workspace/policies/auto_core.json stock-strategy-system/alert_policy.json`의 결과는 7개다.

| 커밋 | 시각(KST) | 바뀐 파일(경로 한정) | 분류 | 근거(원문) |
|---|---|---|---|---|
| 04f9a85 | 10-16 09:50 | auto_core_decide.py·auto_core_tickets.py | 항목 2가 덮음 — 두 날 칸 불변 | 바뀐 것은 F6 대기 주문표 분류(종가 뒤 주문 제외)·no-new-session 문구·G0 예외 알림이다. 두 날 모두 대기 주문표 0(리더 호출 = account_open_items 1건)이고 새 세션이 있는 날이라 이 길을 타지 않는다. 항목 2 실행에 포함됐고 칸이 같다 |
| c3bd452 | 10-16 18:23 | score_decision_journal.py·run_journal_score.ps1·register_journal_score_task.ps1 | 그날 결과와 무관 | 채점은 decision_mode apply일 때만 돈다(auto_core_decide.py:709 `if mode == "apply":` 블록 안 742행 `_score`). 두 날은 compare였다. ps1은 Windows 작업 스크립트다 |
| 210e951 | 10-17 17:17 | portfolio_exposure.py·run_portfolio_exposure_review.py | 항목 2가 덮음 — **10-16 결과를 바꿈**(요건 ②·blocked), 10-17 칸 불변 | 항목 2 원인 분리 1~4 |
| 55133ae | 10-18 07:12 | t2rc-oracle.py·t2rc-check-run.ps1·auto_core_decide/inputs/rules/tickets.py | 항목 1·2가 덮음 — 두 날 칸 불변 | RG1 정의 변경이다. 계산기(항목 1)와 원래 결과의 차이는 sha·ev4_history뿐이고, 코어(항목 2, 그날 S7)는 70/70이다. 실행기 diff는 16행 고정값뿐이다 |
| 67e781d | 10-18 11:58 | host_status.ps1·run_journal_score.ps1 | 그날 결과와 무관 | PowerShell 감시·주간 채점 실행기다. decide·계산기 경로에서 import하거나 호출하지 않는다 |
| 6d4d6f3 | 10-19 20:39 | t2rc-oracle.py·t2rc-check-run.ps1·auto_core_decide/replay/rules.py | 항목 1·2가 덮음 — 허용 차이(EV4)만 | ev4_history·shock kinds의 EV4·account.ev4_open·ev4_backfill이 빠진다. auto_core_replay.py는 리플레이 전용이다(decide 미사용). 실행기 diff는 16행뿐이다 |
| 4fe10b3 | 10-20 11:39 | host_status.ps1·offsite_backup.ps1·register_offsite_backup_task.ps1 | 그날 결과와 무관 | 백업·감시용 PowerShell로, decide·계산기 경로 밖이다 |

- auto_core.json·alert_policy.json을 건드린 커밋은 범위 안에 없다. 그날 커밋과 작업 트리 사이 diff도 없다(alert_policy sha 98ef14e0 = 두 날 inputs).
- 병합 커밋 0d55b9a(10-18, 부모 073582d·55133ae)와 5d5cf79(10-19, 부모 80d3a1d·6d4d6f3)의 내용은 위의 55133ae·6d4d6f3이다.

## 항목 4 — 다른 셈 영향: PASS

- C1 누계를 코드로 세는 곳은 없다. `counts_for_c1`이 나오는 코드는 다음과 같다.
  - t2rc-oracle.py:1450·1634: 하루 단위 플래그.
  - t2rc-check-run.ps1:41: 실행기 오류 때 false로 씀.
  - docs/claude/scheduled-prompts/ceo-weekly/ceo.py:158: 날마다 "(C1 셈)"을 표시한다. 그날 t2rc-check.json의 플래그일 뿐 누계가 아니다(pending-ceo-weekly 사본들도 같은 줄).
- 누계는 ceo.py:210~211이 관제판 redesign-t2 next의 "C1 … n/10" 문구를 인용할 뿐이다. auto-core-alert.txt는 그날 c1.match를 불일치·오류 푸시 문구에만 쓴다. manage-us-stock-strategy/scripts(auto_core*)와 tools에는 해당 코드가 없다(auto_core_*의 "t2rc"는 t2rc-corefix 주석뿐).
- c3_record(t2rc-oracle.py:1672~1674)는 apply 모드이면서 같은 계산기 sha인 앞날 기록만 센다. 10-16·10-17 기록은 compare 모드이고 옛 sha(5607b09b)이며, 제안은 t2rc-check.json을 고치지 않는다(README 34행). → C3는 그대로다(두 날 주문표가 0이기도 하다).
- C2(병합 전 일치 불산입, 사전 등록 50·51행): 두 날 주문표가 0이라 영향이 없고, 제안도 그대로 둔다. D0(10-16)·C4·C5 날짜도 제안 본문과 README 34행에서 그대로다.
- C1 산수: 10-20 실행(세션 10-19)의 t2rc-check.json = MATCH·counts_for_c1 true·계산기 6a74f813이므로 현재 1/10이다. 제안이 통과했다면 3/10이 됐을 것이다.

## 항목 5 — 사전 등록 정합: PASS (비차단 1건)

- **0절(16행)** "숫자는 이후 느슨하게 바꾸지 않는다 · Judge는 더 엄격하게만": 버린 세션을 다시 세는 것은 느슨하게 하는 쪽이다. README 34행이 "사전 등록 0절은 느슨하게 바꾸지 못함 … 초기화의 일회 예외"라고 예외임을 밝히고 K3로 분류했다.
- **사용자 K3 결정**: README 33행에 "2026-10-20 14:51 KST 사용자 원문: "결정 c1-keep: a" (Cowork 대화)"가 있다. 대화 원문은 이 세션에서 열 수 없다(확인 필요). 다만 PASS 조건은 README 결정 기록이 있는 것이고, 그 조건은 충족한다.
- **두 날 한정·24행 불변**: README 33행 "상시 규칙화(b)는 하지 않는다", 34행 "코드·계산기·실행기·결과 파일(t2rc-check.json)·정책·상태·예약 작업은 바꾸지 않는다".
- 비차단 N2: README 34행은 "24·50행 초기화의 일회 예외"라고만 쓴다. 그러나 10-16·10-17은 50행(10-18 ev-rg1-hyper) 초기화로 빠진 뒤 51행(10-19 rrec-ev4-remove) 초기화도 거쳤다. 적용 문구에는 50·51행을 함께 적어야 한다.
- **적용 문구 초안**(1줄. PASS였을 때 쓸 문구이며, 이번 FAIL로 쓰지 않는다):
  `- 2026-10-2x KST c1-keep(사용자 결정 "결정 c1-keep: a" 10-20 14:51, 적용 승인 원문 …, 독립 Judge PASS docs/claude/c1-keep-judge-report.md): 0절의 일회 예외 — 50·51행 초기화로 버린 실운영 비교 세션 2026-10-16·2026-10-17(평가 세션 10-15·10-16) 두 날만 C1에 다시 센다(현행 계산기 6a74f813…·현행 코어로 그날 입력 재현 일치). 24행 초기화 규칙·앞으로의 초기화·C2(병합 전 일치 불산입)·C3·D0(10-16)·C4·C5는 그대로.`

## 항목 6 — 범위·안전: PASS

- `git status --porcelain`: 시작(15:14 KST)과 보고서 쓰기 직전(15:40 KST) 모두 44줄이고 diff가 없다. 보고서를 쓴 뒤 늘어나는 것은 `?? docs/claude/c1-keep-judge-report.md` 1줄이다.
- 세션 중 저장소 안에서 새로 바뀐 파일은 0개다(docs·manage-us-stock-strategy·stock-strategy-system·tools·workspace/policies·calendar-authority·instrument-identity-authority, .pyc 0개). workspace/outputs/dev-runs/_queue/heartbeat.txt 등 3개는 Windows 작업 InvestmentV2-DevQueue가 15:35에 쓴 heartbeat다. 이 세션이 쓴 것이 아니며 감사 훅 기록에도 없다.
- 권한 표지: 두 재현 decision.json 모두 order_authority false·execution_quantity null이다. 계산기 출력도 order_authority false·quantity_authority none·execution_quantity null이다.
- 금지 실행: 키움 호출 0(리더 대역, 소켓 거부 훅). auto_core.py·run_auto_core.ps1·t2rc-check-run.ps1·dev-run·dev-merge·reconcile apply는 실행하지 않았고, 커밋·병합도 없다.

## 차단 결함

- **B1 (항목 2, 10-16)**: 현행 메인 체크아웃 코어(decide 안에서 다시 도는 S7 포함)가 10-16 입력으로 그날 결과를 재현하지 못한다.
  - buy_requirements ②: BE·DELL·LITE·MU·NBIS·PWR이 ok → no.
  - blocked DELL·MU에 REQ2_EXPOSURE_CASH_PRODUCT:no·G2:REVIEW_LINE_OPEN:L2가 추가됨.
  - 원인: hwm-fix 210e951(K3, Judge PASS, 10-17 17:17 병합)의 HWM D6 재평가로 10-15에 L2가 열림.
  - 허용 차이(EV4 표지) 밖이다. 제안의 조건("현행 계산기와 현행 코어가 그날 입력으로 그날 결과를 그대로 재현한다")을 10-16에서 충족하지 못한다.

## 비차단 관찰

- N1: README 재검사는 현재 저장소의 페이지 전체(354개, 그날 뒤 20개·10개 포함)와 10-17 m6 문서(10-17 17:29 생성, 두 실행 뒤)를 읽었다. 이 Judge의 그날 판 복원은 원래 read_files와 똑같이 맞았고, 판정 칸 결과는 README와 같다. → README의 계산기 재현 결론은 맞지만, 방법은 그날 판이 아니었다.
- N2: 항목 5(50·51행).
- N3: 이번에는 저장소 안 자료만으로 그날 판을 정확히 복원할 수 있었다.
  - state = stock-strategy-system/backups r27·r28
  - 원장 앞 13·14줄, 일지 앞 6건, 페이지 이름 날짜 ≤ 실행일
  - 추적 문서 = 그날 commit_sha blob(관심 명단·R-REC1 문서·m6는 LF 원본, 등록부는 CRLF판)
  - 다만 state 백업은 다음 리비전이 생길 때 만들어지므로, 그 전에는 worktree 사본에 기대야 한다. 그날 입력을 그날 보관하는 장치가 있으면 이런 재현의 수작업 위험이 준다(README 30행 한계와 같은 취지).

## 의견 (판정과 별개)

- 기본 처분은 NO_CHANGE다. C1은 10-20부터 센 1/10을 유지하고, 사전 등록·관제판은 바꾸지 않는다. 노출·예산·권한을 올리는 효과는 없다.
- 두 날을 살리려면 새 사용자 결정과 새 Judge가 필요하다(이 Judge는 기준을 넓힐 수 없다).
  - **(a) 10-17만 복원(1/10 → 2/10)** — 권고. 이 판정에서 10-17은 항목 1~4를 모두 통과했다(현행 코어 70/70, 계산기 차이는 sha·ev4_history뿐). 기준을 넓히지 않고 범위만 줄이는 안이다.
  - (b) 두 날을 유지하고, 항목 2 비교를 C1 칸(candidates·evidence·shock)으로 좁히거나 hwm-fix의 S7 멈춤 차이를 허용 목록에 넣는 안. 근거는 있다(10-16 현행 코어 출력에도 계산기 MATCH, 회로 집합 불변). 그러나 "그날 결과를 그대로 재현" 조건을 느슨하게 바꾸는 것이라 K3 사용자 결정이 먼저다.
- 이 판정이 바뀔 조건:
  - 10-16 재현에서 S7을 그날 코드로 고정하는 것을 사용자가 허용 기준으로 정한다(→ 항목 2는 70/70).
  - hwm-fix(210e951)가 되돌려진다.
  - 제안 범위가 10-17만으로 바뀐다.

## 실행 기록 (Judge, 2026-10-20 15:14~15:45 KST)

- 돌린 것(모두 위 스크래치 폴더):
  - 복원 사본 생성·검증 스크립트
  - 계산기 check 4회(원본 decision 2회 + 현행 코어 decision 2회)
  - 코어 decide 재현 4회(현행 S7 2회 + 그날 S7 2회)
  - S7 단독 실행 4회(그날 코드 2회 + 현행 코드 2회)
  - JSON 비교
- 결과 파일 sha256(스크래치 out/):

| 파일 | sha256 앞 8자리 |
|---|---|
| t2rc-check-2026-10-16.json | 25677f9b |
| t2rc-check-2026-10-17.json | 5d04c861 |
| t2rc-check-currentcore-2026-10-16.json | b61f7d41 |
| t2rc-check-currentcore-2026-10-17.json | d7e47961 |
| core-compare-2026-10-16.json | 04e8c9df |
| core-compare-2026-10-17.json | 50ed6cdd |
| core-compare-xs7old-2026-10-16.json | 28abfde1 |
| core-compare-xs7old-2026-10-17.json | c9551c19 |

  스크래치는 세션 임시 폴더라 남지 않는다. 판정에 쓴 값은 이 보고서에 옮겨 두었다.
- 돌리지 않은 것:
  - 키움, auto_core.py·run_auto_core.ps1·t2rc-check-run.ps1·dev-run·dev-merge·reconcile apply
  - 테스트(판정에 필요 없음), 커밋·병합
  - workspace/outputs·stock-strategy-system·docs/claude(이 보고서 제외)·정책·예약 작업·관제판 쓰기

VERDICT: FAIL
