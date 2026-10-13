---
id: rrec-rg1-judge-report
title: rrec-rg1 독립 Judge 보고 (R-REC1 RG1 첫 연구 기록 이전 세션 제외, 결정 B)
date: 2026-10-13
judge_prompt: docs/claude/rrec-rg1-judge-prompt.md
builder_prompt: docs/claude/rrec-rg1-builder-prompt.md (sha256 fc6ff4b3175211b95eebcd8477275b375f6b926b40a5fe1894788ef7757430c5, Builder 보고 기재값과 같음)
builder_report: .claude/worktrees/rrec-rg1/docs/claude/rrec-rg1-report.md (sha256 0b62acbff5b3f3a465a11b975acaa7094bc1a59970b4bcc89d209090905447de)
base: da5d85e6417dbfc0af630ccf4b51ab9f4a07c4a8 (메인 체크아웃 HEAD·worktree HEAD 같음, worktree 브랜치 커밋 0개)
model: Opus 5.5 · xhigh · 새 세션, Builder와 다른 세션
writes: 이 파일 하나뿐 (코드·테스트·정책·상태·관제판 쓰기 없음, 키움·auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply 실행 없음, 커밋 없음)
---

# 0. 결론

- 변경은 지시문 범위 그대로다. 바뀐 파일은 4개(auto_core_rules.py `rrec1`, 새 테스트, compare_fix3 한 곳, 보고서)이고, sha256이 Builder 보고 6절과 병합 스크립트(docs/claude/rrec-rg1-merge-2026-10-13.ps1 13~19행)의 값과 같다.
- 새 RG1 규칙은 "창 안 첫 유효 기록(`ev3b_coverage_start`) 이전 사건 뒤 세션을 기록 있음으로 본 변경 전 규칙"과 정확히 같다. 무작위 입력 30,000건으로 신·구 코드를 비교했고 동치 실패는 0건이다(7번). RG1 말고 다른 경로로 매수 관문이 넓어지지 않는다.
- 실데이터 2026-10-12: 변경 전 코드는 10/13 decide 결정 기록 `shock`을 모든 키에서 그대로 재현했다. 새 코드 결과는 RG1 ok·RG2 no·RG3 no·RG4 ok, status no, before_first_record [2026-10-09]로 지시문 기대와 같다. **이 변경만으로 매수는 열리지 않는다.**
- 병합을 막는 결함은 없다. 의견 3건(4절)은 병합을 막지 않는 기록이다.

# 1. 판정표

| 항목 | PASS/FAIL | 근거(파일:줄) |
|---|---|---|
| 1. 바뀐 파일·줄이 범위뿐, 다른 부분 불변 | PASS | worktree `git status`: M auto_core_rules.py, M test_auto_core_compare_fix3.py, ?? 새 테스트, ?? 보고서. 이 4개뿐이다. `git diff --numstat`: rules +20 −6, compare_fix3 +2 −1. rules diff는 docstring 743~748, 813~826(`first`·`needs_record`·`rg1_coverage`), 838~841(`recorded`)만 바꾼다. EV3 (b) 공백·`settle` 761~779, 사건 목록 781~807, DS1 832~833, RG2~RG4 844~860, 닫힘 규칙 863~888은 diff 밖이다. CONSTANTS 블록(30~75행)은 메인과 줄 단위로 같다. decide·tickets·compare·replay·inputs와 test_auto_core_rules/tickets/decide는 `git diff --quiet HEAD`로 불변 확인 |
| 2. 새 RG1 규칙(첫 기록 이전만 빠짐, 이후 모두 필요, 기록 0개는 unk, None은 같음) | PASS | auto_core_rules.py:815~818. `first = out["ev3b_coverage_start"]`, `needs_record = first is None or day >= first`. :840~841은 필요한 세션만 coverage에 있는지 본다. `first`는 :765~766에서 창 안 benchmark 세션 중 coverage에 든 첫 날이다(창 밖·평가 세션 뒤·주말 문자열은 들어가지 않는다). coverage None이면 :840 `coverage is None`이 먼저 참이 되고 `rg1_coverage`는 None으로 남는다. 무작위 비교에서 None 3,770건, 창 안 기록 0개 7,489건, 첫 기록 ≤ 사건일 17,842건, 사건 없음 365건이 모두 변경 전과 dict 전체가 같다 |
| 3. rg1_coverage(뺀 세션 없으면 dict 동일)·cmp-fix3 헬퍼 동작 | PASS | auto_core_rules.py:821~826. `before_first_record`는 `before`가 있을 때만 붙는다. test_auto_core_rules.py:435의 3키 dict 동등 비교가 그대로 통과한다. 무작위 비교에서도 첫 기록 ≤ 사건이면 dict가 같다. auto_core_compare.py:135~142 `_rg1_record_gap`은 `missing_sessions`만 읽는다. 실데이터 대조를 메모리에서 계산했다(10/13 결정 기록과 연구 기록의 integrated_check_run, 현재 cmp-fix3 코드). 변경 전 core는 `RREC:RG1` B4 RG1_NEEDS_RESEARCH_RECORD였고, 새 core(RG1 ok vs LLM true)는 B1 SAME이다(:283~284 분기가 먼저). RG2~RG4는 B1 그대로다. `_rg1_gap_only`(:145~157)는 신·구 모두 False(RG2·RG3 no) |
| 4. 훼손 사실 → RG1 no 그대로 | PASS | auto_core_rules.py:836~837·842는 diff 밖이다(`damage_after`가 참이면 False). 새 테스트 B4(test_auto_core_rrec_bootstrap.py:84~91)는 첫 기록 이후 훼손 사실로 RG1 no·status no. 훼손 사실은 event_session 기준으로 세므로(:837) 뺀 세션 날짜의 훼손 사실도 이후 유효 기록에 실리면 RG1 no다(auto_core_inputs.py:249는 event_session ≤ 기록 세션을 허용한다) |
| 5. B1~B7과 실데이터(이 변경만으로 매수가 열리지 않음) | PASS | 새 테스트 8건 OK(test_auto_core_rrec_bootstrap.py:55~136). 변경 전 rules를 메모리에 올려 같은 테스트를 돌리면 B1·B2·B4·B6 4건이 실패하고 fixture·B3·B5·B7은 통과한다. 새 테스트가 바뀐 동작을 실제로 잡는다는 뜻이다. B7(일반 운영)은 기존 R2-4 테스트(test_auto_core_rules.py:435 등, test_auto_core_tickets.py:696, test_auto_core_decide.py:676)가 파일 변경 없이 통과하는 것으로 확인했다. 실데이터는 8번 |
| 6. 권한 표지·주문 경로·정책/상태 쓰기·키움·커밋 없음, 테스트 새 실패 0 | PASS | diff와 새 파일에서 `order_authority`·`quantity_authority`·`execution_quantity`·`kill_switch`·`ORDER_TICKET_HUMAN_ENTRY`·kiwoom·주문 도구 문자열 0건. 바뀐 3개 코드·테스트 파일은 비ASCII 0, 모든 줄 CRLF(LF만 있는 줄 0). 120자 넘는 줄 2개(72·789행)는 원래 있던 줄이다. `git rev-list HEAD..worktree-rrec-rg1` = 0. 대상 스위트는 Judge가 직접 돌렸다: `test_auto_core*.py` Ran 360, OK (skipped=1), 기준선 352 + 새 8. 전체 스위트는 Judge 허용 명령 밖이라 다시 돌리지 않았다. 대신 import 범위를 확인했다: 바뀐 모듈(auto_core_rules)과 그 사용 모듈을 import하는 테스트는 test_auto_core*뿐이다(test_dev_pipeline·test_score_ticket_outcomes는 문자열·저널 함수만 쓴다). 그래서 전체 스위트 영향은 대상 스위트 안에 있다. Builder 전체 실행 결과는 Ran 3003, 새 실패 0(기준선 환경 실패 28건 동일, 보고 3-3) |
| 7. fail-open 점검(RG1 말고 다른 경로로 넓어지나) | PASS (의견 4-1) | 무작위 입력 30,000건(벤치마크·후보 무작위, 불완전 봉, EV3a·훼손 사실·EV4·연구 세션의 None/[]/부트스트랩/구멍/무작위/창 밖·평가 세션 뒤·주말 문자열)으로 신·구 rrec1을 비교했다. ① first None·first ≤ 사건·coverage None이면 결과 dict 전체가 같다. ② first > 사건인 534건은 모두 "새 결과 = 변경 전 코드에 research_sessions ∪ before_first_record를 넣은 결과"였다(ev3b_coverage_start와 before_first_record 키만 다름). 동치 실패는 0건이다. EV3 (b) 공백(reasons)·사건 목록·C0/L0는 한 건도 바뀌지 않았다. 상태 변화 304건은 모두 unk→ok/no 또는 닫힘에서 생겼다. 이 가운데 8건은 no→ok인데, 모두 뺀 세션 덕에 RG1이 일찍 충족되어 기존 닫힘 규칙(RG1~RG4 동시 충족, auto_core_rules.py:872~874, recovery-gate-R-REC1-2026-10-09.md:43)으로 사건이 더 일찍 닫힌 경우다. 이것도 RG1 경로이고 ②의 동치 안에 든다 |
| 8. 실데이터 2026-10-12가 기대와 같은가 | PASS | 읽기 전용 python 한 번(파일 쓰기 없음). Production 달력 ACTIVE(sha256 2421eeb7…, 10/13 결정 기록과 같음, `TRUSTED_ROOT`는 메모리에서만 메인 체크아웃으로 지정). load_research 결과: 오늘 OK, sessions [2026-10-12], window_days [2026-10-13], 훼손 0. EV3 문서 날짜 [2026-10-08], EV4 없음. 변경 전 코드는 결정 기록 `shock` 전 키와 by_symbol 8종목을 그대로 재현했다. 새 코드 SOXX: EV3a 2026-10-08, C0 563.185 / L0 555.82, RG1 ok·RG2 no·RG3 no·RG4 ok, status no, open true, ds1 2026-10-12, ev3b_coverage_start 2026-10-12, rg1_coverage {from 2026-10-09, to 2026-10-12, missing_sessions [], before_first_record [2026-10-09]}, reasons []. GRID 기준 PWR·BE: C0 178.3 / L0 176.98, 같은 RG·status no. DELL·LITE·MU·MVLL·NBIS·SOXL(SOXX)도 같다. 신·구 차이 키는 rg·rg1_coverage·status 셋뿐이다. 지시문 기대와 Builder 보고 5절과 같다 |
| 9. compare_fix3 변경이 입력·주석뿐, 단언 그대로, 진짜 공백 유지 | PASS | diff는 test_auto_core_compare_fix3.py:69 주석 1줄 추가와 :73 `research_sessions=days[-2:]` → `[days[-5]] + days[-2:]` 1줄뿐이다(+2 −1). 단언(:74~82)·테스트 이름·개수(16)는 그대로다. 메모리 계산 결과 고친 입력은 first = days[-5](2026-09-07) < 사건 days[-4](09-08)라 아무것도 빠지지 않는다. days[-3](09-09)은 첫 기록 이후의 진짜 공백이다: missing [09-09], before_first_record 키 없음, RG1 unk, 헬퍼 True. 이 입력에서 신·구 코드 결과가 같고, 고친 파일은 신·구 코드 모두에서 16/16 통과한다. 원래 입력(days[-2:])은 새 코드에서 missing []·RG1 ok로 바뀐다. 그래서 충돌은 실제였고, 이 수정은 결정 B가 바꾸지 않는 동작만 고정한다. 원래 목적(rrec1 출력의 공백을 `_rg1_record_gap`이 읽는다)은 지켜진다 |
| 10. INVALID 기록이 "첫 유효 기록 이전"으로 빠지는 위험 | PASS (의견 4-2, 결정 B 범위 안) | auto_core_inputs.py:289~296은 OK 기록의 evaluation_session만 sessions에 넣는다. 그래서 창 시작부터 이어진 INVALID·누락 기록은 "missing"이 아니라 "before_first_record"로 빠진다. 결정 B는 경계를 "EV3 (b)의 ev3b_coverage_start와 같은 방식"으로 정했다(redesign-t2-firstrun-report-2026-10-13.md:160, buy-unblock-review-2026-10-13.md:26·32). 이 값은 첫 유효 기록이고 EV3 (b) 공백(auto_core_rules.py:765~773)이 이미 같은 경계를 쓴다. 지금 노출은 0이다: 기록 파일이 2026-10-13 하나(OK)뿐이고, 그 앞에 INVALID 기록이 없다 |

# 2. 고칠 최소 항목

- 없음(병합 차단 항목 0).

# 3. 확인 방법 요약 (재현용)

- 테스트: worktree에서 `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"` → Ran 360, OK (skipped=1). 새 테스트 단독 Ran 8 OK, compare_fix3 단독 Ran 16 OK.
- 변경 전 코드 비교: 메인 체크아웃의 auto_core_rules.py(sha256 8d18c6f3…, da5d85e와 같음)를 `importlib`로 메모리에 올려 비교했다. 새 테스트(구 코드에서 4건 실패)·compare_fix3(구 코드에서 16/16)·무작위 30,000건(seed 20261013)·실데이터를 이렇게 확인했다. 모두 stdin python이고 저장소에 파일을 쓰지 않았다(`-B`, `PYTHONDONTWRITEBYTECODE=1`).
- 해시: auto_core_rules.py 8ce52c95…fc10d, test_auto_core_rrec_bootstrap.py 0e52f6f5…c07507, test_auto_core_compare_fix3.py 9eab605d…87452. Builder 보고 6절과 병합 스크립트 17~19행의 값과 같다.

# 4. 의견 (병합 차단 아님, 기본 처리 NO_CHANGE)

1. **닫힘 경로와 기록 이전 세션의 닫힘.** 결정 B는 매일 다시 도는 닫힘 반복(auto_core_rules.py:867~877)의 `gates(i)`에도 적용된다. 그래서 첫 유효 기록이 사건+2보다 늦으면 RG1이 기록 이전 세션에서 충족될 수 있다. 그 세션에 RG2~RG4도 충족되면 사건은 연구 기록이 하나도 없던 세션에서 닫힌다. 닫힌 뒤의 훼손 사실은 −1σ60 하락일(EV3b)이 아니면 사건을 다시 열지 않는다. 무작위 비교의 no→ok 8건이 이 경우다.
   - 이번 사례에는 해당하지 않는다. 첫 기록 세션 10-12가 사건+2이고, 이는 RG1이 충족될 수 있는 가장 이른 세션(RREC_RG1_SESSIONS 2)이다. 따라서 기록 이전 세션(10-09)에서는 닫힐 수 없고, 10-12부터는 모든 세션에 기록이 필요하다.
   - 앞으로 더 조이고 싶다면 "평가하는 세션 i 자체가 `first` 이후일 때만 RG1 True" 조건을 더할 수 있다. 이 조건은 10-12 결과를 바꾸지 않는다. 다만 매수 관문 의미가 다시 바뀌는 일이라 K3이고, 이번 범위 밖이다.
2. **경계가 첫 '유효' 기록이라는 점(10번)과 Builder 남은 위험 2의 정확한 조건.** 기록 세션이 빠지는 조건은 "60세션 넘게 끊김"이 아니다. 정확히는 **창 시작(평가 세션 60세션 전)부터 사건 다음 세션까지 유효 기록이 하나도 없을 때**다. 창 시작과 겹친 짧은 장애에 사건이 창 앞쪽에 있어도 해당될 수 있다. 앞으로 스키마가 바뀌어 가장 오래된 기록들이 INVALID가 되면 경계가 뒤로 밀릴 수도 있다. 다음 장치가 이 위험을 덜어 준다.
   - 매수에는 오늘 기록 OK가 필요하다(auto_core_decide.py:536~537, 기록이 없거나 무효면 모든 매수표가 막힌다).
   - 뺀 세션 날짜의 훼손 사실도 이후 유효 기록에 실리면 RG1 no다(1절 4번).
   - EV3 (a) 사용자 지정이 그 구간을 덮는다.
   - 더 조이려면 경계를 "창 안 첫 기록 파일(유효 여부 무관)"로 잡을 수 있다(load_research가 이미 `window_days`를 돌려준다, auto_core_inputs.py:300). 이 방법은 decide·inputs 변경이 필요해 이번 범위 밖이다.
3. **문서 표류.** manage-us-stock-strategy/references/auto-core-decision.md:88~89에는 아직 "RG1 needs a valid record for every session after the event"라고 적혀 있다. 병합 뒤 문서만 고치는 후속(새 규칙 한 문장 + `before_first_record`)을 권한다. 이 파일은 이번 변경이 허용한 파일 목록 밖이라 FAIL 사유가 아니다.

VERDICT: PASS
