---
id: rrec-rg1-builder-prompt
title: R-REC1 RG1 — 첫 연구 기록 이전 세션은 RG1 기록 요구에서 뺀다 (rrec-rg1-bootstrap B)
date: 2026-10-13
class: 권한·한도 변경(K3 — 매수 관문 R-REC1 RG1의 의미 변경). 수동 경로: 이 Builder(worktree) → 별도 Judge 세션 → 사용자 병합 스크립트
decision: 사용자 "결정 rrec-rg1-bootstrap: B"(2026-10-13 18:43 KST, Cowork)
evidence: docs/claude/buy-unblock-review-2026-10-13.md 3절 · docs/claude/redesign-t2-firstrun-report-2026-10-13.md 17절·17-1
base: main HEAD da5d85e6417dbfc0af630ccf4b51ab9f4a07c4a8 (auto_core_rules.py sha256 8d18c6f3565334597ef1ac0cecbdcf7d67f081153a90198a6d6505451e971a80)
model: Opus · xhigh · 새 worktree (claude --worktree rrec-rg1)
authority: order_authority=false · quantity_authority·execution_quantity 불변 · R-REC1 다른 관문(EV1~EV5·RG2·RG3·RG4·DS1·닫힘 규칙)·기준값(rules.CONSTANTS) 불변 · 주문표·S7·대조 모듈 불변 · 키움 호출 없음
weekly_user_touch: 0 (일회성: Builder 1·Judge 1·병합 1)
deadline: 2026-10-15 07:45 KST decide 전에 병합
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 worktree(claude --worktree rrec-rg1) · 이유: 매수 관문 의미 변경(K3)

# 목표

R-REC1 RG1은 r2 R2-4에 따라 "사건 다음 세션부터 평가 세션까지 모든 세션에 유효 연구 기록"이 있어야 판정된다. 연구 기록은 재설계 T2 배포로 기록일 2026-10-13(세션 2026-10-12)부터만 존재한다. 그래서 2026-10-08 사건(EV3a)의 다음 세션 2026-10-09에는 기록이 생길 수 없었고, 코어 RG1은 이 사건이 끝날 때까지 영구히 unk(매수 막힘)이다. 시장 조건(RG2·RG3)과 무관한 부트스트랩 결함이다.

**바꿀 의미 하나**: RG1의 기록 요구에서 **R-REC1 창 안 첫 연구 기록 세션(이미 계산되는 `ev3b_coverage_start`)보다 앞선 세션은 뺀다.** EV3 (b) 공백 판정이 이미 쓰는 경계와 같다("첫 기록 전에는 EV3 (a) 사용자 지정이 창을 덮는다", auto_core_rules.py 765~766행 주석). 첫 기록 이후 세션은 지금처럼 모두 필요하다.

# 근거 (읽기 전용 확인)

- auto_core_rules.py `rrec1` 735행~: 763~764행 `recorded`/`ev3b_coverage_start`, 812행 `rg1_coverage`, 827행 `recorded = coverage is None or all(s["days"][k] in coverage for k in range(e + 1, i + 1))`.
- 2026-10-13 decide(커밋 73e18b4·da5d85e) 결정 기록 `shock`: event EV3a 2026-10-08(C0 563.185, L0 555.82), rg {RG1 unk, RG2 no, RG3 no, RG4 ok}, ds1 2026-10-12, rg1_coverage {from 2026-10-09, to 2026-10-12, missing_sessions [2026-10-09]}, ev3b_coverage_start 2026-10-12.
- 10/10 통합 점검(세션 10/09)은 RG1 충족(공식 훼손 없음)으로 기록했다(대시보드 runs/2026-10-10, 참고 — 코드 입력 아님).
- Cowork 시뮬레이션(rrec1을 research_sessions=None으로 근사): RG1 ok, RG2 no, RG3 no, RG4 ok, status no — 이 변경만으로 매수가 열리지 않고 시장 조건만 남는다.

# 바꿀 것 (auto_core_rules.py `rrec1`만)

1. 첫 기록 세션 `first = out["ev3b_coverage_start"]`(coverage가 None이면 쓰지 않음).
2. `gates` 안 RG1 기록 조건: coverage가 None이면 지금처럼 True. coverage가 있고 `first`가 None(창 안 기록 0개)이면 지금처럼 기록 없음(RG1 None). 그 밖에는 `range(e + 1, i + 1)` 중 `s["days"][k] >= first`인 세션만 coverage에 있어야 한다.
3. `rg1_coverage`: `missing_sessions`는 위 2와 같은 기준(첫 기록 이후 세션 중 기록 없는 것)만 담는다. 첫 기록 이전이라 뺀 세션이 하나라도 있으면 같은 dict에 키 `before_first_record`(그 세션 목록)를 **그때만** 넣는다(빼는 세션이 없으면 dict는 지금과 글자 하나 다르지 않다 — 기존 테스트 test_auto_core_rules.py 435행의 dict 동등 비교 유지). first가 None이면 지금처럼(missing_sessions = 사건 뒤 모든 세션).
4. docstring의 R2-4 문장을 새 규칙으로 고친다(영문, ASCII).
5. 바꾸지 않는 것: EV3 (b) 공백(`gaps`·`settle`), 사건 목록, C0·L0, DS1, RG2·RG3·RG4, 닫힘 규칙, `thesis_damage` 처리(훼손 사실이 있으면 RG1 no — 그대로), rules.CONSTANTS(새 상수 추가 금지), auto_core_decide·tickets·compare·replay·inputs.

# 테스트 — 새 파일 `manage-us-stock-strategy/tests/test_auto_core_rrec_bootstrap.py`

test_auto_core_rules.py의 `helpers.sessions`·`helpers.bars`·`helpers.zigzag`·`rules.build_series` 사용 방식을 따른다(그 파일의 `RRec1R2Tests`류 `bench`/`run_rrec1`/`crash` 패턴 참고).

- B1 사건 다음 세션 1개만 기록 없음, 그 뒤 모든 세션 기록(첫 기록 = 사건+2) → RG1 ok(2세션 경과), `rg1_coverage.missing_sessions` == [], `before_first_record` == [사건+1].
- B2 B1에 더해 첫 기록 이후 세션 하나가 빠짐 → RG1 unk, missing_sessions == [그 세션], before_first_record == [사건+1]. (그 세션이 −1σ60 하락일이 아니게 고른다 — EV3B 공백과 섞지 않는다.)
- B3 research_sessions = [] → RG1 unk(기록 0개는 빼지 않는다), rg1_coverage 키에 before_first_record 없음.
- B4 B1과 같은 기록에 첫 기록 이후 세션의 훼손 사실 1건 → RG1 no.
- B5 research_sessions=None → 변경 전과 같은 결과(rg1_coverage None, RG1 판정 동일).
- B6 2026-10-12 사례 재현(합성 자료): EV3a 사건일 다음 세션 기록 없음, 그다음 세션부터 기록 있음, 벤치마크 종가가 사건 종가 아래·EMA50 아래 → RG1 ok, RG2 no, RG3 no, 사건 open, status "no"(unk 아님).
- B7 사건 이후 세션이 모두 첫 기록 이후면(일반 운영) 결과가 변경 전과 같다 — 기존 test_auto_core_rules·test_auto_core_tickets·test_auto_core_decide의 R2-4 테스트가 그대로 통과하는 것으로 확인(그 파일들은 고치지 않는다).
- 기존 테스트 파일은 고치지 않는다. 기존 테스트가 이 변경 때문에 깨지면 멈추고 보고서에 이유를 적는다.
- 실행: `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"` (Claude Code 설정상 "auto_core.py"가 들어간 명령은 거부된다). 기준선(변경 전 메인) 대비 새 실패 0, Ran 감소 없음. 전체 스위트는 `test-runner` 서브에이전트로 돌려 실패만 보고.

# 실데이터 확인 (읽기 전용, 보고서에 결과만)

worktree에서 저장소 산출물(메인 체크아웃 workspace/outputs/regular-session-closes, workspace/outputs/research-records)을 읽어 2026-10-12 평가 세션으로 `rrec1`을 다시 계산한다(파일을 쓰지 않는 python 한 번, 키움·auto_core.py 실행 금지). 기대: 포트폴리오 SOXX — event EV3a 2026-10-08, RG1 ok, RG2 no, RG3 no, RG4 ok, ds1 2026-10-12, rg1_coverage {from 2026-10-09, to 2026-10-12, missing_sessions [], before_first_record [2026-10-09]}. GRID 기준 종목(PWR·BE)도 한 줄. 다르면 이유를 적는다.

# 지켜야 할 것 (어기면 Judge FAIL)

1. 바뀐 파일은 manage-us-stock-strategy/scripts/auto_core_rules.py, 새 테스트, 보고서뿐.
2. `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`가 들어간 줄을 만들거나 바꾸거나 지우지 않는다. 주문 경로 문자열 없음. 키움·auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply 실행 금지.
3. 스크립트 ASCII만(한국어는 `\u` 이스케이프). 정책·상태 파일·workspace/policies·stock-strategy-system·docs/claude(보고서 제외) 쓰기 금지.
4. **커밋하지 않는다.** 변경은 worktree에 둔다(병합은 사용자 스크립트가 파일 목록·sha256을 확인하고 커밋한다).

# 보고 `docs/claude/rrec-rg1-report.md` (worktree 안에 새로)

바꾼 줄(diff 요약), 새 규칙 한 문단, 테스트 목록과 결과(Ran 수, 대상·전체 새 실패 0), 실데이터 결과, 바뀐 두 파일(auto_core_rules.py, 새 테스트)의 sha256, 남은 위험(첫 기록 이전 세션의 훼손 사실은 코어가 모른다 — EV3 (a) 사용자 지정과 그날 통합 점검 기록이 덮는다; 연구 기록이 60세션 넘게 끊겼다가 다시 시작되면 재개 이전 세션도 빠진다 — EV3 (b) 공백 판정과 같은 가정).

# Judge 확인 항목 (별도 세션, 읽기만)

1. 바뀐 파일·줄이 위 범위뿐. EV3B 공백·사건 목록·DS1·RG2·RG3·RG4·닫힘 규칙·CONSTANTS·decide/tickets/compare/replay 불변.
2. 새 RG1 규칙: 첫 기록(ev3b_coverage_start) 이전 세션만 빠지고, 이후 세션은 모두 필요. 기록 0개면 여전히 unk. coverage None이면 변경 전과 같다.
3. rg1_coverage: 빼는 세션이 없으면 dict가 변경 전과 같다(before_first_record 키 없음). cmp-fix3 `_rg1_record_gap`(auto_core_compare.py)이 바뀐 missing_sessions로도 맞게 동작한다(이 경우 코어 RG1 ok라 B4 조건 밖).
4. 훼손 사실이 있으면 RG1 no — 그대로.
5. B1~B7과 실데이터 결과(RG1 ok·RG2 no·RG3 no — 이 변경만으로 매수가 열리지 않는다).
6. 권한 표지·주문 경로·정책/상태 쓰기 없음, 키움 호출 없음, 커밋 없음. 대상·전체 테스트 새 실패 0.

# 추가 범위 (2026-10-13 19:2x KST, Cowork — Builder 보고 4절 선택지 (가))

- 이유: 기존 테스트 `manage-us-stock-strategy/tests/test_auto_core_compare_fix3.py` `RgGapHelperTests.test_rrec1_output_carries_the_gap_the_helper_reads`의 첫 절반 입력(`research_sessions=days[-2:]`, EV3a `days[-4]`)이 바로 사용자 결정 B가 빼라고 한 부트스트랩 모양이라, 변경 전 동작(missing [days[-3]])을 고정하고 있다. 결정 B와 정면 충돌이며 코드로 둘 다 만족시킬 수 없다. Cowork도 같은 실패를 재현했다(그 파일 16건 중 1건 FAIL, 새 테스트 8건 OK).
- 허용: 그 테스트 **한 곳만** 고친다 — 72행 근처 `research_sessions=days[-2:]` → `research_sessions=[days[-5]] + days[-2:]`(첫 기록을 사건 앞에 두어 `days[-3]`을 첫 기록 이후의 진짜 공백으로 만든다), 주석에 "the first record is before the event (rrec-rg1 bootstrap B leaves out sessions before the first record)" 추가. 단언(assert)·다른 테스트·다른 파일은 바꾸지 않는다. 테스트 이름·개수 그대로.
- 바뀐 파일은 이제 4개: auto_core_rules.py, 새 테스트, test_auto_core_compare_fix3.py, 보고서.
- 할 일: 그 한 곳을 고친 뒤 대상 스위트(test_auto_core*)·전체 스위트(test-runner)를 다시 돌려 보고서를 갱신한다(3절 결과, 4절 "해소", 6절에 test_auto_core_compare_fix3.py 새 sha256 추가, front matter status). 커밋하지 않는다.
