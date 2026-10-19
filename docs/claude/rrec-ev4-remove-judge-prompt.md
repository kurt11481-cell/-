---
id: rrec-ev4-remove-judge-prompt
title: rrec-ev4-remove 독립 Judge (읽기 전용)
date: 2026-10-19
class: K3 독립 Judge — docs/claude/rrec-ev4-remove-builder-prompt.md의 변경(R-REC1 EV4 제거 — 코어·리플레이·독립 계산기·실행기 고정값)을 판정
model: Opus · xhigh · 새 세션(메인 체크아웃, worktree 아님) — Builder 세션과 다른 세션
authority: order_authority=false · quantity_authority=none · execution_quantity=null · 키움 주문 도구 금지
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(메인 체크아웃) · 이유: K3 독립 Judge(매수 관문 사건 정의 + 독립 계산기 고정값)

너는 이 변경을 만들지 않은 독립 검토자다. **파일을 고치지 않는다.** 저장소 안에 쓰는 파일은 맨 끝의 보고서 1개뿐이다(예외: 저장소 밖 임시 폴더의 계산기 `--out`·합성 입력). Builder 보고서의 숫자·주장은 위치 안내일 뿐이다 — 판정은 네가 연 원문과 네가 다시 계산한 값으로 한다. 이 판정은 독립 계산기의 새 고정값을 확인하는 "Judge 확인"(t2-rc-preregistration-2026-10-14.md 24행)도 겸한다.

## 읽을 것

1. 결정: docs/claude/rrec-ev4-remove-decision-2026-10-19.md. 지시문: docs/claude/rrec-ev4-remove-builder-prompt.md — 특히 "동치 명세" E1~E5, "기존 테스트 변경 허용 1~4", "지켜야 할 것". 승인 정의: docs/claude/recovery-gate-R-REC1-2026-10-09.md 1~2절. 정책: stock-strategy-system/alert_policy.json 822~836행(S7 점검선).
2. Builder 보고: .claude/worktrees/rrec-ev4-remove/docs/claude/rrec-ev4-remove-report.md
3. 변경: `git -C .claude/worktrees/rrec-ev4-remove diff`, `git -C .claude/worktrees/rrec-ev4-remove status --porcelain --untracked-files=all`.
4. 다른 독자(L3): auto_core_compare.py 262~296행, auto_core_tickets.py 210~291행(요건 ②·⑤), portfolio_exposure.py 1378~1386행(S7 멈춤), score_decision_journal.py(`shock`·`ev4` 읽는 곳 grep), 통합 점검 규칙 파일 docs/claude/scheduled-prompts/pending-ev-rg1/integrated-check-prompt-v3.12.7-2026-10-18.txt 102행.

## 돌려도 되는 것

- worktree와 base(메인 체크아웃) 각각: `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"`("auto_core.py"가 든 명령은 거부되니 이 패턴으로만), `-p "test_score_*.py"`, `-p "test_decision_journal_cards.py"`, `python manage-us-stock-strategy/scripts/validate_schema_contracts.py`, `python docs/claude/t2rc-oracle.py selftest --repo <메인 체크아웃>`. 메인 작업 트리의 커밋 안 된 docs 변경 때문에 생기는 실패(예: PLTR 등록부)는 base와 같으면 새 실패가 아니다.
- 파일을 쓰지 않는 python으로 재계산·합성 실험. base 함수는 메인 체크아웃 경로에서, 새 함수는 worktree 경로에서 각각 별도 프로세스로 import한다(모듈 이름 충돌 주의). 계산기 `check`는 `--repo <메인 체크아웃> --out <저장소 밖 임시 파일> --ignore-input-sha`로만.
- 금지: 키움 호출, auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply 실행, 커밋·병합, workspace/outputs·stock-strategy-system·정책·예약 작업·관제판 쓰기.

## 판정 항목

| # | 항목 | PASS 조건 |
|---|---|---|
| 1 | 범위 | 바뀐 파일이 지시문 "지켜야 할 것" 1의 목록뿐. 스키마 diff = `ev4_backfill` description 1곳. 실행기 diff = 16행뿐. 기존 테스트 변경이 허용 1~4 범주뿐(키워드 삭제 줄은 그 키워드만 빠졌는지 줄 단위로 확인, 삭제 테스트는 지시문에 이름이 있는 것만). auto_core_compare·tickets·inputs·portfolio_exposure·score·예약 지시문·사전 등록·정책 불변 |
| 2 | 권한·안전 | 권한 표지 줄(order_authority·quantity_authority·execution_quantity·kill_switch·ORDER_TICKET_HUMAN_ENTRY) 변경 없음, 주문 경로 없음, 스크립트 ASCII, 줄 끝은 체크아웃된 그대로(일괄 변환 흔적 없음), 커밋 없음, 데이터 파일 쓰기 없음. 계산기가 auto_core*·manage-us-stock-strategy/scripts를 import하지 않음 |
| 3 | E1 코어 동치 | 고정 시드 합성 입력 300개 이상(EV1·EV2·EV3a·EV3b·EV5·DS1·RG2·RG3 조합, 훼손 사실 있음/없음, card_accepted_on 있음/없음, research_sessions None/목록, rg2_series 기본/None)에서 worktree `rrec1(x)` = base `rrec1(x, ev4_sessions=[])` — 결과 dict JSON이 글자까지 같다. 하나라도 다르면 FAIL |
| 4 | E2 decide 동치 | 합성 decide 입력 여러 개(최소: EV4만 켜지는 계좌, EV2와 겹치는 계좌, 선 위 계좌, 이전 기록에 ev4_open 참, 이전 기록 없음)에서 worktree `evaluate_session` 결과 = base 결과(EV4를 끈 상태 — base `rules.ev4_open`을 False로 고정, `ev4_sessions=[]`, backfill 없음)에서 `account.ev4_open`·`ev4_backfill`을 뺀 것. 결정 파일에 `ev4_backfill`·`EV4_UNDETERMINED` 없음 |
| 5 | E3 계산기 동치 | 같은 방식으로 worktree 계산기 `rrec1(...)` = base 계산기 `rrec1(..., equity_today=None, s7_hwm=None, ev4_hist=())`. 계산기 diff가 rrec1 시그니처·EV4 줄·docstring·ev4_hist 적재·호출 인자·66행 상수(안 쓰이면 삭제)·selftest 새 경우·출처 docstring 1줄뿐 |
| 6 | E5 완화 범위 | base(EV4 켜짐)와 새 코드의 결과 차이가 생기는 입력은 모두 base에서 EV4 사건(또는 EV4가 가장 최근 사건이 되어 생긴 재기준)이 있던 입력이다 — 3·4의 입력에서 차이 난 경우를 전부 분류해 표로. EV4가 없던 입력의 차이 0 |
| 7 | S7 의존 확인 | 결정이 기대는 대체 장치가 그대로: S7 L2 열린 사건이면 요건 ②가 막힘(REVIEW_LINE_OPEN), 일지 검토 완료 뒤 풀림, L3에서 다시 멈춤(further_lines_action same_as_L2) — portfolio_exposure·tickets 원문과 합성 S7 dict 1개 이상으로 확인. 이 코드들은 diff 없음 |
| 8 | 테스트 | 대상·전체 스위트에서 base 대비 새 실패 0. Ran 수 변화 = 삭제 테스트 수(−) + 새 테스트 수(+)와 정확히 맞음. 새 테스트 X1~X6이 주장대로 단언(X5 기대값의 생성 방법이 재현 가능). risk1r GOLDEN 변경이 있으면: base 같은 시나리오 결과에서 E4 두 키를 뺀 dict의 해시 = 새 값임을 네가 다시 계산 |
| 9 | 계산기 고정값 | 네가 잰 worktree 계산기 sha256_lf(t2rc-oracle.py 108~111행 방식) = worktree t2rc-check-run.ps1 16행 값. selftest PASS(기존 골든·앵커 불변 + 새 경우) |
| 10 | 실데이터 | 계산기 worktree 판 vs base 판 `check --day 2026-10-15·16·17`: 차이가 `oracle_sha256`·`ev4_history`뿐. 코어 rrec1 재계산(평가 세션 2026-10-16, 메인 체크아웃 봉) vs 10-17 decision.json shock·by_symbol: 사건 날짜 목록 같고 kinds에서 "EV4"만 빠짐, event 2026-10-16 [EV2], RG1 no·RG2 no·RG3 no·RG4 ok, status no |
| 11 | 다른 독자(L3) | 비교(auto_core_compare 270~292): 통합 점검 규칙 파일 102행이 EV4를 계속 세는 동안 EV4만 켜지는 날 RREC:open이 B7이 될 수 있음을 발견에 적음(병합 때 규칙 파일 v3.12.8 교체가 필요한 이유). score_decision_journal이 `ev4_*` 키를 읽지 않음(grep). 옛 결정 파일(ev4_backfill 있음)이 스키마를 계속 통과 |
| 12 | 병합·C1 절차 | 지시문 "병합·고정값 교체·C1 재시작" 절이 사전 등록을 느슨하게 하지 않는다: C1은 병합 뒤 첫 decide부터 0/10, 계산기와 실행기 고정값이 한 병합으로 함께 바뀜(ORACLE_SHA_MISMATCH 창 없음), 규칙 파일 교체가 같은 승인 범위·같은 세션, 병합 시각이 06:15 대조·07:45 decide·08:40 대조·23:30 DocsCommit과 겹치지 않음 |

## 출력

- 한국어 표 `| # | 항목 | PASS/FAIL | 근거(파일:행 / 재계산 값) |`(위 1~12), 그 아래 "발견"(E1~E3 실험 수·차이 0 확인, 6의 분류 표, 남은 EV4 주석 위치, 남은 위험, 의견 — 기본 NO_CHANGE), 고칠 최소 항목(있으면), 바뀐 파일 sha256(네가 잰 작업 트리 바이트 값) + 새 계산기 sha256_lf + 실행기 sha256_lf, 마지막 줄은 정확히 `VERDICT: PASS` 또는 `VERDICT: FAIL`.
- 같은 내용을 **새 파일 하나** `docs/claude/rrec-ev4-remove-judge-report.md`(메인 체크아웃)에 저장한다. 그 밖의 파일은 쓰지 않는다.

## 추가 범위 — Builder 세션의 사용자 승인 3건과 지시문 정정 (2026-10-19 19:3x KST, Cowork)

Builder 보고 7절 1에 따르면 사용자가 Builder 세션에서 **"3건 모두 진행 (권장)"**이라고 답했다. 항목 1(범위)에서는 아래 셋을 허용 범주로 본다. 단, 각각이 **최소 변경**인지는 네가 원문으로 확인한다.
- ① test_auto_core_t1_safety.py `Ev4ResolveTests`(base 238~266행) 삭제. 지운 `ev4_backfill_resolve`·`RREC_EV4_NEIGHBOR_MARGIN`만 시험하던 테스트인지 확인.
- ② test_auto_core_rg1_oracle_parity.py 63행 계산기 호출에서 위치 인자 `None, None, ()`만 삭제. 같은 diff 덩어리의 58행 `ev4_sessions=[]` 삭제는 허용 1에 해당.
- ③ test_auto_core_risk1r.py `GOLDEN["cash5"]` 값 교체 + 근거 주석 2줄. `decide_compare`·`decide_apply`는 바뀌지 않아야 한다. 지시문 허용 4가 "두 값을 바꾼다"고 적은 것은 Cowork의 잘못된 예상이다(해시 대상에 `account`·`ev4_backfill`이 없음). base 사본과 worktree에서 `cash5` 시나리오를 각각 돌려 아래를 확인한다:
  - 해시 대상(tickets·blocked·no_action·candidates)의 차이가 `REQ5_RREC1:no` 사유가 빠진 것뿐이다.
  - 그 시나리오의 base R-REC1 사건이 EV4 하나뿐이다.

Builder가 지시문을 해석해 처리한 3건(보고 7절 2)도 항목 1·5에서 판정한다:
- 계산기 1936행 `s7hwm` 계산 삭제
- 계산기 2261행 selftest 도우미 `_rg1_run`의 호출 인자 삭제
- decide docstring 문구 정리

더 쓰이지 않게 된 테스트 helper·import(보고 5절)는 남아 있어도 FAIL 사유가 아니다. 발견에만 적는다.

Cowork 사전 확인(장치 VM Linux, 읽기 전용, 참고용):
- worktree `test_auto_core*.py` Ran 443, 실패 2(PLTR 등록부, risk1r OS 해시 — base와 같은 2건)
- 계산기 selftest PASS
- worktree 계산기 sha256_lf 6a74f813…9d64 = 실행기 16행 값
- 18개 파일 모두 CRLF 유지
- 권한 표지 줄 diff 0

이 확인은 판정 근거가 아니다. 네가 다시 잰다.
