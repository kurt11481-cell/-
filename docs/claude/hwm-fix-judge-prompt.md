---
id: hwm-fix-judge-prompt
title: hwm-fix 독립 Judge (읽기 전용)
date: 2026-10-17
class: K3 독립 Judge — docs/claude/hwm-fix-builder-prompt.md의 변경(①+③)을 판정
model: Opus · xhigh · 새 세션(메인 체크아웃, worktree 아님) — Builder 세션과 다른 세션
authority: order_authority=false · quantity_authority=none · execution_quantity=null · 키움 주문 도구 금지
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(메인 체크아웃) · 이유: K3 독립 Judge

너는 이 변경을 만들지 않은 독립 검토자다. **파일을 고치지 않는다.** 저장소 안에 쓰는 파일은 맨 끝의 보고서 1개뿐이다(예외: 저장소 밖 임시 폴더의 제안 파일 1개와 러너 `--output-root` 출력). Builder 보고서의 숫자·주장은 위치 안내일 뿐이다 — 판정은 네가 연 원문과 네가 다시 계산한 값으로 한다.

## 읽을 것

1. 지시문: docs/claude/hwm-fix-builder-prompt.md (메인 체크아웃). 결정 원문: docs/claude/cpi-shock-review-2026-10-15.md 2절 D6(129행)·4-4(200~215행), docs/claude/pre-on-roadmap-review-2026-10-15.md 3절·재검토 절·결정 기록(rrec-k3-timing d). 정책: docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md 55~57행(R6).
2. Builder 보고: .claude/worktrees/hwm-fix/docs/claude/hwm-fix-report.md
3. 변경: 메인 체크아웃과 worktree의 같은 경로 비교(`git -C .claude/worktrees/hwm-fix diff`, `git -C .claude/worktrees/hwm-fix status --porcelain --untracked-files=all`)
   - manage-us-stock-strategy/scripts/portfolio_exposure.py (`evaluate_review_lines`, `build_exposure_review`)
   - manage-us-stock-strategy/scripts/run_portfolio_exposure_review.py
   - 새 테스트 test_portfolio_exposure_hwm_fix.py · test_run_portfolio_exposure_review_hwm_fix.py
   - (입력만 허용) tests/s5_exposure_fixtures.py · tests/test_portfolio_exposure_fail_closed.py · tests/test_portfolio_exposure_judge_fixes.py
4. 코어·계산기 근거: auto_core_tickets.py 182~200행(`s7_summary`)·240~244행(요건 ②)·911~925행(`_buy_ticket` G2), auto_core_decide.py 747~751행(s7_runner)·1057~1062행(EV4)·217~280행(ev4_backfill), auto_core.py 186~199행(run_exposure 요약), docs/claude/t2rc-oracle.py 1275~1279행(S7 모양 확인)·1468~1484행(ev4_hist)·1699~1701행(`s7_fresh`)·1780~1826행(`buy_requirements`, 요건 ② 1806행)·1828~1857행(`gates_check` G2), portfolio_exposure.py 1064~1075행(늦은 대조 필터)·1144~1175행(트리거·멈춤)·1341~1392행(`_evaluate_proposal`).

## 돌려도 되는 것

- worktree 안에서 대상 테스트: `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_portfolio_exposure*.py"`, `-p "test_run_portfolio_exposure_review*.py"`, `-p "test_auto_core*.py"`("auto_core.py"가 든 명령은 거부되니 이 패턴으로만), score_decision_journal을 쓰는 `-p "test_score_*.py"`·`-p "test_decision_journal_cards.py"`·`-p "test_journal_score_task_static.py"`. base(메인 체크아웃)에서도 같은 명령으로 비교한다.
- 파일을 쓰지 않는 python으로 재계산. 러너 실행은 `--output-root`를 저장소 밖 임시 폴더로 줄 때만:
  - 입력 `--state`·`--ledger`·`--journal`·`--closes-root`(필요하면 `--calendar`) = 메인 체크아웃 경로. worktree 러너에는 새 뿌리 인자 `--evidence-root`(Builder 보고 1절)도 메인 체크아웃으로 준다(대조안·브로커 스냅샷은 git 밖이라 worktree에 없다 — 안 주면 broker_capture가 모두 None이 된다). base 러너에는 그 인자가 없다.
  - `--now 2026-10-16T23:00:00Z` 고정. worktree·base 각각 `--session 2026-10-16`·`--session 2026-10-12`.
  - 제안 1건: 저장소 밖 임시 폴더에 `{"proposals":[{"kind":"new_buy_within_band","symbol":"BE","target_weight":"0.05"}]}` 파일 1개(target_weight는 0.001 단위 — 아니면 PROPOSAL_TARGET_INVALID로 멈춤 사유가 안 보인다)를 만들어 worktree·base 각각 `--session 2026-10-16 --proposals <파일>`.
- 키움 조회는 꼭 필요할 때만 1회(order-fills-daily 10/6~10/9, 읽기 전용, options `"profile": "실전계좌"`, `"mode": "real"`. 8005·인증 오류면 재인증하지 말고 "조회 실패"로 적는다).
- 금지: 키움 주문 도구, auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply 실행, 커밋·병합, workspace/outputs·stock-strategy-system·정책 쓰기.

## 판정 항목

| # | 항목 | PASS 조건 |
|---|---|---|
| 1 | 범위 | 바뀐 파일이 지시문 "지켜야 할 것" 1의 목록 + "추가 범위"의 test_auto_core_risk1r.py뿐. 기존 테스트 변경은 픽스처 입력 추가뿐(단언 변경 0)이고, 예외는 test_auto_core_risk1r.py GOLDEN 5개 값(default·sell·pwr·decide_compare·decide_apply)과 이유 주석뿐 — 새 키 두 개를 뺀 실행이 base GOLDEN과 같고 차이가 티켓 `inputs.s7_review_id`뿐인지 네가 다시 확인(Windows에서 base·worktree 각각). auto_core*.py·t2rc-oracle.py·스키마·정책·cash_flow_evidence.py·portfolio_review_journal.py 불변 |
| 2 | 권한·안전 | 권한 표지 줄(order_authority·quantity_authority·execution_quantity·kill_switch·ORDER_TICKET_HUMAN_ENTRY) 변경 없음, 주문 경로 없음, 스크립트 ASCII, 줄 끝 base 그대로, 커밋 없음, 데이터 파일 쓰기 없음 |
| 3 | ① 규칙 | 평가 세션보다 앞서고 **덮는 창이 모두 끝난** 세션만 재평가하며, 그런 세션은 재평가 또는 실패 — 건너뜀 경로 없음(겹친 창 포함). N = S 마감 뒤 첫 확정 리비전, 다음 개장 전이면 POST_CLOSE, 아니면 P와 보유가 같고 "예수금 + 미정산 매도 − 미정산 매수" 합이 같을 때만 BRACKETED(주문 가능액 비교 안 함). 재평가 세션도 532~534행 조정을 먼저 적용하고, S 다음 세션 ~ N 캡처 사이 분할이 있으면 실패. N 앞(as_of ≥ S)의 연결 안 된 리비전이 있으면 실패. 주문 가능액은 대조안이 가리키는 브로커 스냅샷 값이고 연결은 기존 해시 함수(proposal_content_hash, canonical_hash)로 확인. 세션 시각은 달력 core_open_at·core_close_at |
| 4 | fail-closed 불변 | 안 풀린 창 = 지금과 같다(HELD·트리거). 평가 세션 자신이 창 안이면 HELD 그대로. 재평가 실패는 UNVERIFIED → fail-closed(추가·신규 매수 멈춤). 매도·줄이기 권고·automatic_sell false 그대로 |
| 5 | 미래 정보 금지 | 재평가·해제는 1070~1075행 필터를 지난 스냅샷만 쓴다(그 행 불변). `--session 2026-10-12` 기대: status HELD, revalued_sessions = 10-02(BRACKETED)·10-06(POST_CLOSE)뿐, hwm 31711.76(10-06), events [], fail_closed 켜짐 |
| 6 | 엄격성·R6 1회 | 같은 입력에서 매 세션 새 HWM ≥ 재평가 끈 HWM, 옛 사건의 선은 새 계산에서 같은 날 이전에 걸린다. 재평가 실패로 반복이 중단돼도 출력 hwm_usd ≥ 재평가 끈 HWM(코어가 그 값으로 EV4를 기록 — auto_core_decide.py 1058~1059행). 늦게 신고된 입금·출금이 HWM에 정확히 1번 반영된다(B-6 보정, 정책 56행). 날짜를 가릴 수 없으면 UNVERIFIED. 기존 HWM 기대값(test_portfolio_exposure_fail_closed.py 239행, test_portfolio_exposure_judge_fixes.py 113행 등) 그대로. 이 성질을 깨는 입력을 하나라도 찾으면 FAIL |
| 7 | ③ 규칙 | 옛 사건(재평가 끈 계산)과 (line_id, breach_date, hwm)이 정확히 같은 완료 항목만 superseded. 새 사건을 완료 처리하지 않는다(L2 이상이면 멈춤 유지). 그 밖은 unmatched → fail-closed 그대로. 일지 파일을 쓰지 않는다 |
| 8 | 데이터 공급 | 러너 변경은 데이터 공급만. reconstruct_snapshots의 기존 키·값과 auto_core.py `_ledger_snapshot_after`·compare_streak, score_decision_journal.py, auto_core_replay.py(보류 없는 입력 → review_lines 기준과 같음, 새 키는 빈 목록) 동작 불변. 대조안 위조(proposal_id·snapshot_hash·보유 불일치, cash 미검증, 파일 없음) → broker_capture None → 그 세션 fail-closed |
| 9 | 실데이터 재현 | 네가 원시 파일(장부·대조안·브로커 스냅샷·종가 이력)에서 직접 다시 계산: 재평가 6건(10-02 브래킷 30,456.97 · 10-06 31,711.76 · 10-07 30,972.82 · 10-08 29,037.23 · 10-09 28,867.29 · 10-12 27,695.15), HWM 31,711.76(10-06), L1 10-12(28,540.584)·L2 10-15(25,369.408), L3 없음. worktree 러너 출력이 이와 ±0.01 안에서 같다. base 대비 차이는 지시문 "실데이터 확인"의 허용 키 경로와 추가 범위가 허용한 `review_lines.evaluated_through`(`--session 2026-10-12`에서 10-05 → 10-06), `inputs.non_default_inputs`의 `evidence_root`(worktree 러너만 `--evidence-root`를 받음) 안에만 있다. 관제판 doneWhen의 "EV4 날짜(10/12)"는 결정 d로 범위 밖이다 — 과거 decision.json의 EV4 기록이 그대로인 것이 맞다(auto_core_decide.py 1058행은 병합 뒤 실행부터 새 HWM을 쓴다) |
| 10 | **G2 동등 — L2가 열릴 때** | 아래 "G2 점검" (가)(나)에서 L2 장치가 양쪽에 같은 신호로 막음. (다)를 hwm-fix가 새로 만들지 않음 |
| 11 | **10/6~10/9 외부 현금 흐름** | 아래 "현금 흐름 점검"에서 예수금 연속성의 설명 안 되는 잔차가 $1.00 이하 |
| 12 | 다른 독자(L3) | S7 출력을 읽는 곳이 새 키·바뀐 값으로 깨지지 않는다: t2rc-oracle.py 1275~1279행 모양 확인, auto_core_tickets.py `s7_summary`, auto_core.py 186~199행, `exposure_display_block`(1398행~), 통합점검 지시문 docs/claude/integrated-check-prompt-v3.12.6-2026-10-15.txt 100·102·122행(S7 review_lines·EV4 = S7 hwm × 0.9 — 더 엄격해짐), portfolio_review_journal.py 283~291행(검토 키를 open_events에서 만듦), validate_schema_contracts.py 통과 |
| 13 | 테스트 | 대상·전체 스위트에서 base 대비 새 실패 0, Ran 감소 없음. 지시문 H1~H12(H5b 포함)·R1~R3이 있고 주장대로 단언한다(이름만 있고 단언이 약하면 FAIL) |

### G2 점검 (사용자 지정 항목)

코어는 S7 `pauses`(실패 사유 + 열린 멈춤 선 REVIEW_LINE_OPEN)로 매수를 막는다(portfolio_exposure.py 1167~1175·1371행 → 제안 결과 → auto_core_tickets.py 922~924행 G2, 240~244행 요건 ②). 계산기 G2는 `lines_open = any(L2 이상 triggered_in_current_drawdown)`과 pauses.new_buy로 막는다(t2rc-oracle.py 1850~1855행, 요건 ② 1806행). 둘 다 코어가 쓴 같은 S7 파일을 읽는다. "주문표 0"만으로는 판정하지 않는다 — R-REC1·실적 차단·제안 없음으로도 0이 되기 때문이다.

- (가) 실데이터: `--proposals` 1건을 넣은 worktree 러너의 2026-10-16 출력에서 신호별로 확인한다 — 코어 쪽: `recommendations.proposals[].reasons`에 REVIEW_LINE_OPEN:L2, `pauses.new_buy_recommendations.paused` true(→ s7_summary new_buy_paused → 요건 ② "S7 신규 매수 멈춤", best_target 없음 → G2 사유). 계산기 쪽: 같은 dict로 1851행 식(lines_open)과 1853~1854행 G2 식을 파일을 쓰지 않는 python으로 그 식만 재현 → G2 false. base 출력(L2 10-16)도 같은 신호인지 한 줄.
- (나) 합성: L2가 재평가로 처음 열리는 경우(H11)도 같은 신호.
- (다) 이미 있던 차이 — **L2 검토 완료 뒤**: 코어는 완료된 사건을 멈춤에서 빼지만(open_events만 REVIEW_LINE_OPEN, 1167~1168행) 계산기 lines_open은 같은 하락 구간이면 계속 참이다(1851행) → 다른 관문이 모두 열리면 코어만 매수 주문표를 낼 수 있다(C1 extra_in_core). 10-19 L2 수락 세션(docs/claude/l2-full-review-2026-10-17.md 8·133행)이 이 상태를 만든다. 코드 근거(파일:행)로 성립 여부를 확인하고 영향(R-REC1이 막는 동안은 실효 없음 등)을 "발견"에 적는다. **hwm-fix가 이 상태를 새로 만들 때만 FAIL**이다. 이미 있던 (다)가 실데이터에 보이면 발견에 적고, 그날 t2rc-check 결과(주문표 차이 유무)만 기록한다. 고칠 곳은 ev-rg1-hyper 계산기 묶음 후보로 적는다.
- 참고(확인만): 새 고점 뒤 남은 미검토 사건은 계산기도 pauses.new_buy로 같게 막는다(1806·1854행). ③ superseded는 fail_closed가 아니다 — 새 사건이 L2 이상이면 코어 pauses와 계산기 lines_open·pauses(1851·1854행)가 양쪽에서 막고, L1이면 양쪽 다 안 막는다. `HELD_SESSION_NOT_REVALUABLE`만 fail_closed로 읽혀 코어 G1_S7_FAIL_CLOSED(auto_core_decide.py 1049행 부근), 계산기 s7_fresh false(1699~1701행) — 같은 방향인지 한 줄.

### 현금 흐름 점검 (사용자 지정 항목)

- 장부 신고 블록: rev 18(10-02~10-05)·19(10-06)·20(10-07)·24(10-09~10-10)·26(10-08~10-13)의 기간·declaration_status·new_external_net_usd·hwm_adjustment_usd. 10-02~10-13이 이어서 덮이는지.
- 신고만으로는 부족하다: ust21100은 환전·출금 행을 보여 주지 않는다(docs/claude/redesign-t2-firstrun-report-2026-10-13.md 13-1, 사용자 10-13 12:49). 그래서 장 마감 뒤 확정 스냅샷(rev 18 20261005T235936Z · 20 20261007T043650Z · 21 20261007T232156Z · 23 20261009T070141Z · 24 20261009T235205Z · 25 20261013T035125Z의 kiwoom_broker_snapshot.shadow.json)으로 이어 본다.
- 판정은 **예수금(foreign_currency_deposit) 연속성**으로 한다: rev 18 → 25 변화 = 정산된 매도 대금(MVLL 118주 4,457.19 · MVLL 119주 4,932.10 — 체결 원문은 키움 order-fills-daily, cpi-shock-review 1-1 표 위치) + 10-11 예탁금 이용료 $1.47(firstrun 13절, 10-06~10-09 밖) → 5.92 + 4,457.19 + 4,932.10 + 1.47 = 9,396.68. SOXL 22주 3,072.51은 rev 24(d2)·rev 25(d1)에서 미정산이라 예수금이 아니라 주문 가능액 식으로 확인한다(예수금에는 rev 27에서 들어온다). 같은 스냅샷에서 주문 가능액 = 예수금 + 미정산 매도 정산(±0.02)도 확인한다. 개장 전 조회의 주문 가능액 +$3(예수금 그대로)은 표시만 하고, cash UNVERIFIED 파일(20261007T222718Z·20261009T065931Z)은 뺀다.
- 10-06~10-09 구간 예수금 연속성에서 설명 안 되는 잔차가 $1.00를 넘으면 FAIL(사유: 실데이터 HWM 기대값을 받아들일 수 없음 — 코드 문제가 아니라 자료 문제. 고칠 최소 항목에 "외부 흐름 확인·신고 후 기대값 재산정"을 적는다).

## 출력

- 한국어 표 `| # | 항목 | PASS/FAIL | 근거(파일:행 / 재계산 값) |`(위 1~13), 그 아래 "발견"(G2 (다) 결과, 재평가 실패가 영구 fail-closed로 남는 위험과 git 밖 근거 파일 보존 의존(.gitignore 48·157행) — 실패 사유가 코어 결정·예외 알림에 보이는지(Cowork 확인: 결정에는 `G1_S7_FAIL_CLOSED:<트리거 id>`만 실리고, 예외 푸시 목록 auto_core_decide.py 685~767행에는 S7 fail-closed 줄이 없다 — 이 변경 전부터 있던 상태), 남은 위험, 의견 — 기본 NO_CHANGE), 고칠 최소 항목(있으면), 바뀐 코드·테스트 파일 sha256(네가 잰 값), 마지막 줄은 정확히 `VERDICT: PASS` 또는 `VERDICT: FAIL`.
- 같은 내용을 **새 파일 하나** `docs/claude/hwm-fix-judge-report.md`(메인 체크아웃)에 저장한다. 그 밖의 파일은 쓰지 않는다.
