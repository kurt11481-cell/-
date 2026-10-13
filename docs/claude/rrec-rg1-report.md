---
id: rrec-rg1-report
title: R-REC1 RG1 첫 연구 기록 이전 세션 제외 (rrec-rg1-bootstrap B) — Builder 보고
date: 2026-10-13
prompt: docs/claude/rrec-rg1-builder-prompt.md (추가 범위 절 포함, 프롬프트 sha256 fc6ff4b3175211b95eebcd8477275b375f6b926b40a5fe1894788ef7757430c5)
base: da5d85e6417dbfc0af630ccf4b51ab9f4a07c4a8 (auto_core_rules.py sha256 8d18c6f3565334597ef1ac0cecbdcf7d67f081153a90198a6d6505451e971a80 확인)
worktree: .claude/worktrees/rrec-rg1 (branch worktree-rrec-rg1), 커밋 없음
model: Opus 5.5 · xhigh
status: READY_FOR_JUDGE — 추가 범위(4절 선택지 (가), Cowork 2026-10-13 19:2x KST)로 기존 테스트 충돌 해소. 대상·전체 테스트 새 실패 0. 커밋 없음.
history: 1차 STOP(기존 테스트 1건 실패) → 추가 범위로 test_auto_core_compare_fix3.py 한 곳 수정 → 재실행
---

# 0. 결론 (먼저 읽을 것)

- 코드 변경·새 테스트 B1~B7·실데이터 확인은 프롬프트대로 끝났고 기대값과 모두 일치한다(실데이터: SOXX·PWR·BE 모두 RG1 ok, RG2 no, RG3 no, RG4 ok, status no — 이 변경만으로 매수는 열리지 않는다).
- 1차 실행에서 기존 테스트 1건(`test_auto_core_compare_fix3.RgGapHelperTests.test_rrec1_output_carries_the_gap_the_helper_reads`)이 결정 B와 정면 충돌해 멈췄다(4절). Cowork가 프롬프트 "추가 범위" 절로 선택지 (가)를 허용했고, 그 테스트의 입력 한 줄과 주석 한 줄만 고쳤다(단언·테스트 이름·개수 불변).
- 재실행: 대상 스위트 Ran 360 OK(skipped 1), 전체 스위트 새 실패 0(3-3). Judge로 넘길 수 있다.
- 바뀐 파일 4개: auto_core_rules.py, 새 테스트, test_auto_core_compare_fix3.py, 이 보고서(6절 sha256).

# 1. 바꾼 줄 (diff 요약)

`manage-us-stock-strategy/scripts/auto_core_rules.py` `rrec1`만, +20 −6 (CRLF 유지, ASCII만, 새 상수 없음):

1. docstring R2-4 문장(743~748행): "RG1은 창 안 첫 기록 세션(ev3b_coverage_start)부터 사건 뒤 모든 세션의 기록이 필요하다; 그 이전 세션은 기록이 있을 수 없고 EV3 (a)가 덮는다(rrec-rg1 bootstrap B: 빼고 rg1_coverage.before_first_record에 적는다); 창 안 기록이 0개면 RG1은 계속 unknown" 으로 고침.
2. 사건 결정 직후(813~819행): `first = out["ev3b_coverage_start"]`, 내부 함수 `needs_record(day)` = `first is None or day >= first`.
3. `rg1_coverage`(821~826행): `missing_sessions`는 `needs_record`인 세션 중 기록 없는 것만. 뺀 세션이 있을 때만 키 `before_first_record`(그 목록)를 넣는다. 뺀 세션이 없으면 dict는 변경 전과 같다(키 3개).
4. `gates` 안 RG1 기록 조건(838~841행): `all(s["days"][k] in coverage for k in range(e + 1, i + 1) if needs_record(s["days"][k]))`. 주석 갱신.

바꾸지 않은 것: EV3 (b) 공백(`gaps`·`settle`), 사건 목록, C0·L0, DS1, RG2·RG3·RG4, 닫힘 규칙, `thesis_damage`(훼손 사실 → RG1 no), rules.CONSTANTS, decide·tickets·compare·replay·inputs.

# 2. 새 규칙 (한 문단)

R-REC1 RG1의 연구 기록 요구(r2 R2-4)는 이제 R-REC1 창 안 **첫 유효 연구 기록 세션(`ev3b_coverage_start`)부터** 평가 세션까지의 사건 뒤 세션에만 적용된다. 첫 기록보다 앞선 사건 뒤 세션은 기록이 생길 수 없었던 세션이므로 요구에서 빼고 `rg1_coverage.before_first_record`에 남긴다(EV3 (b) 공백 판정이 이미 쓰는 경계와 같다). 첫 기록 이후 세션은 지금처럼 하나라도 빠지면 RG1 unknown이다. 창 안 기록이 하나도 없으면(`first` None) 아무것도 빼지 않아 RG1은 그대로 unknown이고, `research_sessions=None`(추적 안 함)이면 변경 전과 같다. 2세션 경과 조건과 훼손 사실(RG1 no)은 그대로다.

# 3. 테스트

## 3-1. 새 파일 `manage-us-stock-strategy/tests/test_auto_core_rrec_bootstrap.py` (8건)

합성 벤치마크: zigzag 494/506(EMA50 약 500, sigma60 약 2.4%), EV3a 사용자 지정 사건.

| 테스트 | 내용 | 결과 |
|---|---|---|
| test_fixture | 사건은 EV3a 1개, RG3 no, 사건 open (고정 자료 확인) | ok |
| B1 test_b1_session_before_the_first_record_is_left_out | 사건+1 기록 없음, 사건+2부터 모두 기록 → RG1 ok, missing [], before_first_record [사건+1], 이유 없음 | ok |
| B2 test_b2_a_session_after_the_first_record_is_still_needed | B1 + 첫 기록 이후 상승일 1개 빠짐 → RG1 unk, status unk, missing [그 세션], before_first_record [사건+1], EV3B 공백 아님 | ok |
| B3 test_b3_no_record_in_the_window_is_not_left_out | research_sessions [] → RG1 unk, missing = 사건 뒤 모든 세션, before_first_record 키 없음 | ok |
| B4 test_b4_damage_fact_after_the_first_record_is_no | B1 기록 + 첫 기록 이후(상승일) 훼손 사실 → RG1 no, status no, 사건은 EV3a 그대로 | ok |
| B5 test_b5_untracked_records_are_unchanged | research_sessions None → rg1_coverage None, RG1 ok, 전부 기록된 경우와 status·open·rg 같음; thesis_damage None이면 RG1 unk | ok |
| B6 test_b6_rg1_ok_and_the_market_gates_decide | 2026-10-12 재현(합성): 사건 EV3a(t−2), 사건+1 기록 없음, t만 기록, t 종가 < C0·< EMA50 → RG1 ok, RG2 no, RG3 no, RG4 unk 아님, open, status "no", ds1 = t | ok |
| B7 test_b7_records_from_before_the_event_are_unchanged | 첫 기록이 사건 앞(일반 운영) → dict 키 3개 그대로, 빠진 세션 있으면 RG1 unk (변경 전 동작) | ok |

변경 전 코드로 돌린 결과: B1·B2·B4·B6 실패(새 동작 검증), fixture·B3·B5·B7 통과 — 새 테스트가 바뀐 동작을 실제로 잡는다.

## 3-2. 대상 스위트 `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"`

| | Ran | 결과 |
|---|---|---|
| 기준선(변경 전, 새 파일 없음) | 352 | OK (skipped=1) |
| 1차 변경 후(rules·새 테스트) | 360 | FAILED (failures=1, skipped=1) — 4절 |
| **추가 범위 후(+ compare_fix3 한 곳)** | **360** | **OK (skipped=1)** |

1차 새 실패 1건(`test_auto_core_compare_fix3.RgGapHelperTests.test_rrec1_output_carries_the_gap_the_helper_reads`)은 추가 범위 수정으로 해소(4절). 최종: 기준선 대비 새 실패 0, Ran 352 → 360(새 테스트 8건, 감소 없음). `test_auto_core_compare_fix3.py` 단독: Ran 16, OK.
B7 확인: test_auto_core_rules(R2-4 `RecoveryCoverageTests` 435행 dict 동등 비교 포함)·test_auto_core_tickets(`ResearchCoverageTests`)·test_auto_core_decide(`test_old_damage_fact_keeps_rg1_no`)는 모두 그대로 통과.

## 3-3. 전체 스위트 (`test-runner` 서브에이전트, `-p "test_*.py"`)

| | Ran | 결과 |
|---|---|---|
| 기준선(변경 전 코드) | 3003 | FAILED (failures=23, errors=9, skipped=3) |
| 1차 변경 후(rules·새 테스트) | 3003 | FAILED (failures=20, errors=9, skipped=3) |
| **추가 범위 후(+ compare_fix3 한 곳)** | **3003** | **FAILED (failures=19, errors=9, skipped=3)** |

기준선 실행에는 새 테스트 파일이 이미 들어가 있었다(변경 전 코드에서 B1·B2·B4·B6 실패 4건 포함). 그 4건을 빼면 기준선 고유 실패·오류는 28건(failures 19, errors 9)이고, 모두 이 worktree에 없는 workspace/outputs·stock-strategy-system 자료(FileNotFoundError, acceptance binding 0건 등) 때문으로 이 변경과 무관하다. FAIL/ERROR 목록 diff(정렬, 직접 확인):
- 1차 변경 후: B1·B2·B4·B6 4건 없어짐, 새로 생긴 것 1건(`test_auto_core_compare_fix3...test_rrec1_output_carries_the_gap_the_helper_reads`).
- **추가 범위 후(최종)**: 기준선 대비 없어진 것 4건(B1·B2·B4·B6), **새로 생긴 것 0건**. 남은 28건은 기준선 고유 실패·오류와 같다. Ran 감소 없음(3003).

# 4. 깨진 기존 테스트 — 이유, 선택지, 해소

**해소 (추가 범위, Cowork 2026-10-13 19:2x KST, 선택지 (가))**: 허용된 한 곳만 고쳤다 — `test_rrec1_output_carries_the_gap_the_helper_reads`의 `research_sessions=days[-2:]` → `research_sessions=[days[-5]] + days[-2:]`(73행), 주석 한 줄 추가(69행: "The first record is before the event (rrec-rg1 bootstrap B leaves out sessions before the first record)."). 단언·다른 테스트·테스트 이름·개수 불변(+2 −1줄, CRLF·ASCII 유지, 120자 넘는 줄은 원래 있던 3줄뿐). 재실행: 이 파일 Ran 16 OK, 대상 스위트 Ran 360 OK. 아래는 1차 실행 때의 기록이다.

**테스트**: `manage-us-stock-strategy/tests/test_auto_core_compare_fix3.py` 67~81행 `test_rrec1_output_carries_the_gap_the_helper_reads` (cmp-fix3, da5d85e에서 추가).

**이유**: 이 테스트의 첫 절반은 `research_sessions=days[-2:]`, EV3a `days[-4]`로 `rrec1`을 부른다. 창 안 첫 기록은 `days[-2]`이고 사건 다음 세션 `days[-3]`은 첫 기록보다 앞선다 — 2026-10-12 사례와 같은 부트스트랩 모양이다. 테스트는 여기서 `missing_sessions == [days[-3]]`, RG1 `unk`, `_rg1_record_gap` True를 고정한다. 사용자 결정 B는 바로 이 세션을 요구에서 빼라는 것이므로 새 코드는 `missing_sessions []`, `before_first_record [days[-3]]`, RG1 ok를 낸다. 즉 이 테스트는 결정 B와 정면으로 충돌하며, 코드 쪽에서 둘 다 만족시킬 방법은 없다. (프롬프트 B7은 rules·tickets·decide의 R2-4 테스트만 확인 대상으로 적었고 이 cmp-fix3 테스트는 빠져 있었다.)

**compare 동작 자체는 맞다**(Judge 3번 항목): `_rg1_record_gap`은 `missing_sessions`만 읽으므로 새 키 `before_first_record`의 영향이 없다. 실데이터에서는 코어 RG1이 ok가 되어 B4 조건 밖이고(RG1 ok vs 통합 점검 rg1 true → B1 SAME, `test_core_ok_is_unchanged`가 이미 다룸), 첫 기록 이후 공백이 생기면 지금처럼 `missing_sessions`에 남아 B4로 분류된다.

**수정 후보 (스크래치에서만 확인, 파일은 고치지 않음)**: 72행 `research_sessions=days[-2:]` → `research_sessions=[days[-5]] + days[-2:]`, 68행 주석에 "the first record is before the event" 추가. 첫 기록을 사건 앞에 두면 `days[-3]`은 첫 기록 이후의 진짜 공백이 되어 테스트의 원래 목적(rrec1 출력의 공백을 헬퍼가 읽는다)이 새 규칙에서도 그대로 성립한다. 스크래치 실행 결과(새 코드):
- 지금 입력 `days[-2:]`: rg1_coverage {from 2026-09-09, to 2026-09-11, missing [], before_first_record [2026-09-09]}, RG1 ok, 헬퍼 False → 테스트 실패.
- 후보 `[days[-5]] + days[-2:]`: missing [2026-09-09](before_first_record 키 없음), RG1 unk, 헬퍼 True, 이유 없음 → 첫 절반 통과.
- 뒤 절반 `days[-3:]`: missing [], RG1 ok, 헬퍼 False → 그대로 통과(바꿀 필요 없음).

**선택지 (1차 보고 당시 — Cowork가 (가)로 결정)**:
- (가) 범위 보정(권장): 프롬프트·Judge 프롬프트·병합 스크립트의 파일 목록에 `test_auto_core_compare_fix3.py`(위 한 줄 입력 변경 + 주석)를 넣고, 이 worktree에서 Builder가 그 한 곳만 고친 뒤 대상·전체 테스트를 다시 돌려 이 보고서를 갱신한다. 그다음 Judge.
- (나) 이 변경을 보류하고 다른 방법을 다시 설계한다.

# 5. 실데이터 확인 (읽기 전용)

방법: worktree 코드로 메인 체크아웃의 산출물을 읽어 2026-10-12 평가 세션으로 `rrec1`을 다시 계산하는 python 한 번(스크래치 `rrec_realdata.py`). 입력은 decide `_run`과 같게 맞췄다 — Production 달력(메인 체크아웃 권한, 메모리 안에서만 `TRUSTED_ROOT` 지정), `load_research`(창 60세션, 연구 기록 2026-10-13 하나 → 유효 세션 [2026-10-12], 훼손 사실 0), `load_symbol`(regular-session-closes/pages, corporate-actions, history의 exchange), EV3 문서 날짜 [2026-10-08], EV4 없음(2026-10-13이 첫 decide 기록, ev4_open False). 파일 쓰기 없음, 키움·auto_core.py 실행 없음.

변경 전 코드로 같은 계산을 먼저 돌려 2026-10-13 decide 결정 기록(`shock`)을 그대로 재현했다(RG1 unk, missing_sessions [2026-10-09], by_symbol 전부 RG1 unk).

| 대상 (벤치마크) | 사건 | C0 / L0 | RG1 | RG2 | RG3 | RG4 | status | ds1 | rg1_coverage |
|---|---|---|---|---|---|---|---|---|---|
| 포트폴리오 (SOXX) | EV3a 2026-10-08 | 563.185 / 555.82 | ok (전: unk) | no | no | ok | no (전: unk) | 2026-10-12 | from 10-09, to 10-12, missing [], before_first_record [10-09] |
| PWR (GRID) | EV3a 2026-10-08 | 178.3 / 176.98 | ok (전: unk) | no | no | ok | no | 2026-10-12 | 같음 |
| BE (GRID) | EV3a 2026-10-08 | 178.3 / 176.98 | ok (전: unk) | no | no | ok | no | 2026-10-12 | 같음 |
| DELL·LITE·MU·MVLL·NBIS·SOXL (SOXX) | EV3a 2026-10-08 | 563.185 / 555.82 | ok | no | no | ok | no | 2026-10-12 | 같음 |

프롬프트 기대값(SOXX: EV3a 2026-10-08, RG1 ok, RG2 no, RG3 no, RG4 ok, ds1 2026-10-12, rg1_coverage {from 2026-10-09, to 2026-10-12, missing_sessions [], before_first_record [2026-10-09]})과 **일치**. ev3b_coverage_start 2026-10-12, reasons [] (EV3B 공백 없음). 매수 요건 (5)는 unk에서 no로 바뀔 뿐 열리지 않는다 — 남은 막힘은 시장 조건(RG2·RG3)이다.

# 6. 바뀐 파일과 sha256

| 파일 | sha256 |
|---|---|
| manage-us-stock-strategy/scripts/auto_core_rules.py (수정, CRLF) | 8ce52c9566cd775e8a3bd039d3b125abcb79aaedec9411c7cf51513b177fc10d |
| manage-us-stock-strategy/tests/test_auto_core_rrec_bootstrap.py (새 파일, CRLF, ASCII) | 0e52f6f5016de7987e6ba9d480f6cd21ee5d23ce183134e5b400f4bb08c07507 |
| manage-us-stock-strategy/tests/test_auto_core_compare_fix3.py (추가 범위 수정, CRLF) | 9eab605dea99a2f30b6a437c114fc75d4bf32e50d2d6c02b0c3084a2a4387452 |
| docs/claude/rrec-rg1-report.md (이 보고서) | — |

test_auto_core_compare_fix3.py 수정 전(HEAD) sha256: 9e153542dc3e69f9fcbcafaa0a2ef7cc0f5d609f1f98f7f647ce7b2fef817155. auto_core_rules.py·새 테스트 sha256은 1차 보고 이후 바뀌지 않았다.

# 7. 지켜야 할 것 확인

- 바뀐 파일: 위 4개뿐 (`git status`: M auto_core_rules.py, M test_auto_core_compare_fix3.py, ?? 새 테스트, ?? 이 보고서).
- `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY` 줄 생성·변경·삭제 없음(diff·새 파일 grep 0건). 주문 경로 문자열 없음.
- 키움·auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply 실행 없음. 정책·상태·workspace/policies·stock-strategy-system 쓰기 없음. docs/claude 쓰기는 이 보고서뿐.
- 커밋 없음.

# 8. 남은 위험

1. 첫 기록 이전 세션의 훼손 사실은 코어가 모른다. 그 구간은 EV3 (a) 사용자 지정과 그날의 통합 점검 기록(예: 10/10 통합 점검이 세션 10/09를 RG1 충족으로 기록)이 덮는다는 가정에 기댄다.
2. 연구 기록이 60세션 넘게 끊겼다가 다시 시작되면 창 안 첫 기록이 재개 시점이 되어, 재개 이전의 사건 뒤 세션도 빠진다 — EV3 (b) 공백 판정과 같은 가정이다.
3. (해소됨) 4절의 기존 테스트 충돌은 추가 범위 수정으로 풀렸다. 병합 스크립트의 파일 목록·sha256에 test_auto_core_compare_fix3.py가 들어가 있어야 한다(6절 값).
