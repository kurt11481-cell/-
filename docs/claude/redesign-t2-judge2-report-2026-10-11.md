---
id: redesign-t2-judge2-report-2026-10-11
title: 재설계 T2 독립 Judge 2차 판정 — 1차 FAIL(F-1~F-4) 해소·조건 반영·r2~r4 변경분
date: 2026-10-12
judge: Claude Code Opus 5.5(중간 일부 Fable 5.1), 새 세션(메인 체크아웃). 파일 수정 없음 — 이 보고 1개만 씀
judge_prompt: docs/claude/redesign-t2-judge2-prompt-2026-10-11.md (sha256 cad4b85d4c1cd9fd…)
basis: builder-prompt 3e754a271a0d7d76… · judge-report(1차) c3427917a7f93b90… · r2 69b8cf5cf3ea7ffb… · r3 8159d02055fb7ae6… · r4 5806b769a03d37c8… · builder-report(worktree) 686dbf5d44588cc9…
target: .claude/worktrees/t2-core (branch worktree-t2-core, base cd6a56d, 미커밋 — 수정 7 + 새 파일 24)
verdict: PASS-WITH-CONDITIONS (병합 차단 조건 없음 · "켜" 전 조건 9건)
authority: 판정은 권한을 주지 않는다. order_authority=false · execution_quantity=null 그대로
consumers: Cowork(병합 판단·배포·"켜" 전 목록) · 관제판 redesign-t2
---

# 판정: PASS-WITH-CONDITIONS — 1차 FAIL 4건 모두 해소. 병합(비교 모드)은 가능하고, 조건은 "켜"(기록 모드) 전에 처리한다

- 1차 FAIL 네 건은 모두 고쳐졌다. 1차 탐침 P1·P2·P3을 다른 변형으로 다시 돌렸고 모두 통과했다.
  - F-1: 연구 기록이 없거나 틀리면 지수 ETF 매수도 막히고, 매도는 그대로다.
  - F-2: 이른 HOLD/FAIL 날이 이틀 이어져도 원장과 미분류 주문표가 이어진다.
  - F-3: 그 세션의 EV4가 R-REC1에 들어간다.
  - F-4: 훼손 사실을 60세션 창에서 모은다. RG1은 기록이 다 있어야 판정하고, −1σ 날의 기록 공백은 unk로 둔다.
- 1차 조건(“켜” 전 1~5, 비교 모드 1·3)과 r3·r4 항목도 모두 PASS다.
- 회귀는 없다. 주문 경로 0, 체결 추정 0, 기준값 불변, 보안 문제 0, 새 사용자 단계 0. 전체 스위트 실패 28줄은 1차 분포와 같고, T2 코드와 무관하다.
- 남은 것은 모두 기록 모드("켜") 전 항목이다. 비교 모드에서는 주문표가 입력 대상이 아니므로 병합을 막지 않는다.
  - r4 보고 새 사실 E·F
  - 재실행 push 전달 경로
  - 휴장 날 입력 문구의 중복 입력 위험
  - HOLD 날 EV4 유실 등

## 0. 확인 범위와 방법

- **diff**: `git -C .claude/worktrees/t2-core diff cd6a56d`로 수정 7파일을 확인했다(+246/−54, `--ignore-cr-at-eol` stat 같음). 새 24파일 중 바뀐 코드 경로(decide·tickets·rules·inputs·compare·replay, 결정 스키마)는 직접 읽었다.
- **바뀐 파일 집합**: 새 24 + 수정 7 = 31개로, Builder 1차 보고 2절의 목록과 하나하나 같다. 새 경로는 0이다. 1차 문서들이 "새 25"라고 적은 것은 세는 법 차이로 보인다(메모 1).
- **탐침**: 세션 임시 폴더의 `probe_t2_judge2.py`에서 132개 검사를 돌렸고 132개 모두 PASS다.
  - 가짜 자료와 테스트 픽스처(Env·FakeReader·Scenario)만 썼다. 키움 호출은 0이고 저장소에 쓴 것도 0이다.
  - Builder 테스트를 다시 실행한 것이 아니라 변형으로 만들었다: 매수 주문표·미체결·HOLD 이틀, 겨울 토요일 창, 비교 모드 휴장 날, 해시 변이 14종.
- **테스트**: Windows에서 직접 돌렸다. 전체 스위트는 test-runner가 돌렸고, 원본 로그에서 실패 id를 직접 셌다.
- **실자료 리플레이 스모크**: 1차 K8과 같은 인자로 두 번 돌렸다. 출력은 세션 임시 폴더에 두었다.
- **실행하지 않은 것**: 키움 조회, kiwoomcli, auto-core daily/decide 실제 실행, reconcile auto/apply, 작업 등록, 커밋, 병합.
- **확인 한계**: r1 시점의 테스트 파일 사본이 없어(미커밋) 기존 테스트의 바이트 diff는 할 수 없었다. 대신 다음을 확인했다(F절).
  - Builder가 바꿨다고 적은 지점을 직접 읽었다.
  - 테스트 수는 감소 없이 늘기만 했다.
  - 대상 테스트가 모두 통과한다.

## A. 1차 FAIL 해소

| 항목 | 판정 | 근거 (worktree 기준 파일:줄) | 1차 탐침 재현 |
|---|---|---|---|
| F-1 연구 기록 OK 아니면 모든 매수 차단 | **PASS** | 그날 기록 상태 → `research_block`(`auto_core_decide.py:497-500`). 요건 ① 지수 ETF 칸 = no `RESEARCH_RECORD_NOT_OK:<이유>`(`auto_core_tickets.py:217-218`). 열린 매수 후보마다 같은 사유(`:648-651`). 매도 경로(`:615-637`)에는 붙지 않는다 | **P3 재현**: 기록 없음·record_day 불일치·JSON 아님 3가지 모두 SOXL 새 단서 2종으로 매수 회로가 열린다 → SOXL 매수 0·사유 확인·① no. 같은 날 기록이 OK면 SOXL 매수 1건(대조군). 매도는 기록 유무와 무관하게 수량·가격·막힘 사유가 같다 |
| F-2 이른 HOLD/FAIL 날을 건너 원장·미분류 주문표 이어짐 | **PASS** | `ledger_carry`(`auto_core_decide.py:107-128`): f6_ran=true인 최근 기록의 keys·open_tickets·발행 tickets(issued_day)·attributed_orders를 가져온다. F6 전 종료·FAIL 기록은 `_settle`(`:998-1019`)이 출처를 그대로 옮겨 적는다(carried_from, f6_ran false). F6은 출처의 미분류 주문표로 돈다(`:535-565`) | **P1 재현(변형)**: D(10-07) 매수 주문표 + 시장 시험 1회 키 + 닫힌 키 → D+1 kill HOLD(조회 0) → D+2 T1 없음 HOLD → D+3에서 D 창(10-07·10-08)을 읽어 unfilled → 키 UNFILLED_TWICE로 닫힘, 닫힌 키 유지, ticket_outcome 일지 1건, 귀속 행 기록. F6 뒤 S7 예외 FAIL 날도 확정 0(일지 0·키 그대로·DECIDE_FAIL push) → 다음 날 1회만 기록. 중간 HOLD 뒤 조회 실패 → OUTCOME_UNKNOWN·G0 HOLD·주문표 0(빈 목록 통과 없음) |
| F-3 그 세션 EV4가 R-REC1에 | **PASS** | `ev4_open`(`auto_core_rules.py:671-678`: 총자산 ≤ 25,626.55 또는 ≤ S7 hwm×0.9). `evaluate_session`이 R-REC1 전에 그 세션을 ev4 목록에 넣는다(`auto_core_decide.py:864-875`). 리플레이도 같은 함수 경로(`auto_core_replay.py:250-263`) | **P2 재현(decide 경유)**: 직전 기록 없음·총자산 약 $9k → ev4_open, shock open, 오늘 사건 EV4, MU ⑤ ≠ ok, MU 매수 회로는 열렸지만 매수 0. 대조군(현금 3만)은 MU 매수 1건. 경계: 1차 선 같음 = 열림, +1센트 = 닫힘. hwm×0.9 같음 = 열림, +1센트 = 닫힘. 총자산 모름 = EV4 아님(요건 ②가 이미 막음) |
| F-4 훼손 사실 60세션 창·RG1 범위·공백 unk | **PASS** | 창 = 평가 세션까지 60세션(`auto_core_decide.py:493-497`). `load_research`가 창 안 유효 기록 전부에서 훼손 사실과 기록 세션을 모은다. C7은 10기록일 그대로(`auto_core_inputs.py:263-301`). RG1은 이벤트 뒤 모든 세션 기록이 필요하다(`auto_core_rules.py:786-792`, rg1_coverage `:774-777`). 첫 기록 뒤 −1σ60 이하(또는 모름) 날의 기록 누락 → status unk·EV3B_RECORD_GAP(`:722-740`) | 이벤트 18세션 전, 훼손 사실이 3세션 늦은 기록에 실림(10기록일 밖) → RG1 no·이벤트 열림. 이벤트 뒤 하루 기록 누락 → RG1 unk. 알려진 훼손 사실은 공백과 무관하게 no. −1.3σ 날 누락 → unk. 같은 날이 첫 기록 앞이면 영향 없음(EV3ⓐ 몫). 덜 빠진 날 누락 → 영향 없음 |

## B. 1차 조건 반영

| 조건 | 판정 | 근거 |
|---|---|---|
| "켜" 전 1 같은 run_day 재실행 멱등 | PASS | 같은 해시면 아무것도 쓰지 않고 기록된 결정 반환, 다르면 HOLD·`decision.rerun-<시각>.json`만(`auto_core_decide.py:644-657, 708-725`). 고정 테스트 `test_auto_core_decide.py:332-353`은 FAIL 기대에서 "OK·일지 추가 0·decision.json 바이트 그대로·rerun 파일 없음"으로 바뀌었고 단언이 늘었다 → 약화 아님(지시 F8과 같음) |
| "켜" 전 2 매도 주문표 S7 계획 전제 줄 | PASS | `plan_premise`(`auto_core_tickets.py:895-925`)가 gap·after_sale 두 곳에(`:657-662`), 대시보드 줄 끝에(`auto_core_decide.py:989-995`) 붙는다. 수량 불변 |
| "켜" 전 3 불일치 결과는 원장 갱신 안 함 | PASS | update_keys에서 reconcile_mismatch 제외(`auto_core_decide.py:559-562`). 귀속 행도 원장에 안 넣는다(`:197-201`) |
| "켜" 전 4 채점기 반환값 경고 | PASS | 0·None이 아니면 `score_warning "SCORER_EXIT:<값>"`(`auto_core_decide.py:676-681`) |
| "켜" 전 5 등록부 kind·side 묶음 | PASS | `KIND_SIDES`·`kind_side_mismatches`·card_check → REGISTRY_KIND_SIDE_INVALID(그 종목만 자격 없음)(`auto_core_inputs.py:49-54, 107-110, 173-174`). 스키마 검증기에 if/then이 없어 설명문 + 로더 강제(수용) |
| 비교 모드 1 대조 엄격화 | PASS | N: ≤0.01 B1 / ≤0.03 B2 / 그 위 B7(`auto_core_compare.py:207-212`). R5: 선과의 거리 ≤1%p만 B2(`:224-228`). b2_wide = 1% 넘게 여유를 쓴 B2(`:171-173`). 연속 일수: FAIL·F1 전 종료(NOT_COMPARED 기본값, `auto_core_decide.py:400`)·읽을 수 없는 기록 = 0, NO_RECORD·NO_NEW_SESSION만 유지(`auto_core_compare.py:280-304`). 탐침으로 재확인 |
| 비교 모드 3 S7 검토 출력 위치 | PASS | `run_s7`가 `<날짜>/s7/`을 --output-root로 쓴다(`auto_core_decide.py:211-227`). exposure-review 파일 수 불변 테스트 통과 |

## C. r3·r4

| 항목 | 판정 | 근거 · 탐침 |
|---|---|---|
| R3-1 세션이 끝난 주문표만 분류 | PASS | `ticket_session_ended`(`auto_core_tickets.py:436-439`). 세션 전이면 조회 없이 열린 채 `G0_TICKET_SESSION_NOT_YET` → HOLD(`auto_core_decide.py:149-150, 174-177`) |
| R3-2 주문일 창 | PASS | 발행 KST 날짜 ~ 운영 달력 core_close_at의 KST 날짜(`auto_core_tickets.py:442-455`). 창 안 조회 하나라도 실패하면 OUTCOME_UNKNOWN(`auto_core_decide.py:183-186`). 탐침: 평일 2일, 토→월 4일(10/17~10/20), 겨울 토→월 4일·마감 06:00 KST, 조기 폐장 13:00 ET → 다음 날 03:00 KST, 달력에 없는 세션 → None(fail-closed). decide 경유 겨울 토요일 주문표가 화 00:40 KST 행으로 filled |
| R3-3 새 세션 없는 날 | PASS | 출처 평가 세션 = 오늘이고 출처 뒤 읽을 수 없는 기록이 없을 때(`auto_core_decide.py:450-456`). `_no_new_session`(`:728-779`): OK·no_new_session·주문표 0·일지 0·push 0·조회 0·원장·미분류·귀속 목록 이어받기·f6_ran true·대조 NO_NEW_SESSION(연속 일수 유지)·decision.json 기록. 탐침: 비교·기록 두 모드 모두 확인. 비교 모드는 next_action_for_user 없음. 출처 뒤 깨진 기록이 있으면 R3-3을 쓰지 않고 G0_PREVIOUS_DECISION_UNREADABLE |
| R2-5는 같은 run_day만 | PASS | 일지 core_decision 중 payload run_day_kst = 오늘인 것만(`auto_core_decide.py:649-652`). 다른 날인데 여기까지 오면 append가 CORE_DECISION_ALREADY_RECORDED로 거부 → FAIL·push(fail-closed) |
| R4-1 귀속 | PASS | `ticket_rows`·`attribute_orders`(`auto_core_tickets.py:458-509`): 이미 귀속된 (ord_dt, ord_no) 제외. 발행일 행은 ord_time ≥ 발행 시각만(같은 시각 포함, "074500" 형식 포함). ord_no 없음·발행일 시각 모름 → unknown. 30일 정리(실행일 포함)·중복 1회. 오래된 주문표부터 분류. 기록 모드에서만 원장 갱신(`auto_core_decide.py:557-565`). 이어받기·HOLD·R3-3로 전달된다. 탐침 6건 통과 |
| R4-2 입력 창 문구 | PASS | `enter_window`(`auto_core_tickets.py:696-705`): 평일 "~ 정규장 개장 전(22:30)", 토→월 "~ 10/19 22:30 개장 전", 겨울 23:30. fillAt 그대로 |

## D. Builder가 새로 고른 것

| 항목 | 판정 | 이유 |
|---|---|---|
| r2-3 1 f6_ran = "F6가 돌았고 FAIL로 끝나지 않음"(F6 뒤 실패도 확정 없음) | 수용 | 분류 결과가 일지 없이 원장만 바뀌는 길을 막는다. 탐침 P1b: 다음 날 같은 행으로 1회만 기록 |
| r2-3 2 FAIL 기록은 주문표를 내지 않음 | 수용 | 일지에 없는 주문표를 사용자에게 보이지 않는다. 결정 스키마 설명과 같다 |
| r2-3 3 결정 스키마 검사를 일지 쓰기 앞으로 | 수용 | 쓴 뒤 바뀌는 것은 journal 블록뿐이다. 그 블록은 additionalProperties 제한이 없어, 마지막 검사가 새로 실패할 수 없다 |
| r2-3 4 decision_sha256 정의 | 수용 | 탐침: 실행 시각·dirty_paths·발행 시각·대기 시각만 바꾸면 같은 해시다. 다음 14종 판정 변경은 모두 다른 해시다: 수량·가격·status·reasons·keys·귀속·열린 주문표·결과·연구 기록 해시·주문표 입력 해시·commit·요건 칸·shock·대시보드 수량. 다른 판정을 같다고 보는 경우는 찾지 못했다. 코드 버전은 commit_sha로 남는다 |
| r2-3 5 같은 해시 → 기록된 status 반환 | 수용 | |
| r2-3 6 | 해소 | r3 R3-3으로 대체 |
| r2-3 7 rerun 파일 내용·LATEST 불변 | 수용(조건) | push가 rerun 파일에만 있다. 알림 작업이 LATEST만 읽으면 push가 나가지 않는다 → "켜" 전 3 |
| r2-3 8 불일치 결과 주문표는 다시 열지 않음 | 수용 | 다시 열면 매일 같은 불일치로 G0가 무기한 닫힌다. 그 결과는 일지에 없고 Cowork push로 간다 |
| r2-3 9 kind·side는 로더가 강제 | 수용 | 실제 등록부 위반 0(테스트) |
| r2-3 10 R2-4 세부 | 수용 | σ·수익률을 모르는 날의 누락도 공백으로 본다(fail-closed). 공백 검사는 각 후보의 RG2 벤치마크로 한다(전력 업종 = GRID). 이는 코드의 EV3ⓑ 정의와 같다(메모 2) |
| r2-3 11 N·R5 비교의 1e-9 | 수용 | 표현 허용이다 |
| r2-3 12 카드 EXIT/TRIM 줄 | 수용 | |
| r2-3 13 사유 = 기록 검사 첫 줄 | 수용 | |
| r3-2 1 휴장 날 못 읽은 지난 주문표는 다음 새 세션 날로 | 수용 | 일지 없이 분류하지 않는다. 잃는 것은 하루 지연뿐이다 |
| r3-2 2 R3-3 날 키움 조회 0 | 수용 | 새 주문표가 없어 G0가 쓰일 곳이 없다 |
| r3-2 3 R3-3 기록 내용(출처 판정 보기·alert_states 복사) | 수용 | |
| r3-2 4 R3-3 날 세션 전 주문표 행 유지("주문표 0" = "새 발행 0") | 수용(조건) | 해석은 맞다(새 발행·일지·push 0). 다만 기록 모드 next_action이 토요일과 같은 "주문표 N건 — 저녁 키움 입력"이고, 그날은 미체결 조회도 하지 않는다. 이미 입력한 사용자가 다시 넣을 위험이 있다 → "켜" 전 4 |
| r3-2 5 출처 뒤 읽을 수 없는 기록 → R3-3 안 씀 | 수용 | 탐침 확인. 출처가 최신인지 알 수 없을 때 fail-closed다 |
| r3-2 6 R2-5 한정 방법 | 수용 | |
| r3-2 7 G0_TICKET_SESSION_NOT_YET에 push 없음 | 수용(조건) | 정상 운영에서는 생기지 않는 이상 상태다. 기록 모드에서는 예외 알림 원칙상 push 여부를 정한다 → "켜" 전 6 |
| r3-2 8 조기 폐장 | 수용 | 탐침으로 재확인 |
| r3-2 9 픽스처 날짜 다섯 곳(_as_of) | 수용 | 10/01 기록이 10/09를 평가한 값은 현실에 없다. R3-3 아래에서 의미가 바뀌므로 바꾼 이유가 맞다. 단언은 그대로다(`test_auto_core_decide.py:312-320`) |
| r4-2 1~8 | 모두 수용 | 원장 항목에 ticket_id 추적 칸, 30일 = 실행일 포함, 불일치 결과 행 제외, 오래된 주문표 우선, 비교 모드 목록, 읽을 수 없는 칸 = unknown, 발행 시각 = 분 단위, 문구 틀. 판정에는 (ord_dt, ord_no)만 쓴다 |

## E. 회귀 — 1차 PASS 항목

| 항목 | 판정 | 근거 |
|---|---|---|
| J1 범위 | PASS | 31파일 모두 허용 경로다. 보호 경로 변경은 worktree·main 모두 0이다. main의 alert_policy(10-07)·decision_journal(10-09)·portfolio_state(10-10 08:52) 수정 시각은 변화 없음. CRLF 일관(LF 수 = CRLF 수), 줄바꿈만 다른 파일 0 |
| J2 주문 경로 0 | PASS | 주문 API·도구 검색 0건. 조회 operation은 account_open_items·account_daily_fills_read 두 가지뿐(`auto_core_decide.py:152-153`) |
| J3 체결 추정 0 | PASS | 분류는 ust21150 행만 쓴다(`auto_core_tickets.py:512-557`). R4-1도 행 선택만 바꿨고 종가·가격 입력은 없다 |
| J4 비교 모드 무쓰기 | PASS | 비교 모드는 원장·귀속을 갱신하지 않는다(`auto_core_decide.py:559`). 일지 쓰기는 apply만(`:644`). R3-3은 일지 0. S7 출력은 `<날짜>/s7`. 리플레이 뒤 worktree·main auto-core 폴더 불변 |
| J5 기준값 불변 | PASS | SIZING·POLICY_EXPECTED·CONSTANTS는 1차와 같다. 새 값은 0.03·1%p(부록 B 대조 범주, r2 지시), 30일(자료 보관), 1e-9(표현 허용)뿐이다. 매매 문턱은 없다 |
| J7~J9 | PASS | 자격·산식·가격 경로 변경은 LOT_ZERO 표시(R2-12)와 연구 기록 사유 추가뿐이다. 황금 테스트 통과 |
| J11 권한 칸 | PASS | ORDER_TICKET_HUMAN_ENTRY는 주문표·일지 payload에만 있다(결정 스키마는 설명문). decision·replay·registry·research 스키마는 order_authority const false |
| J12~J13 | PASS | 대조 범주는 B 참조. ps1·journal 모듈은 1차 이후 변경 0(diff 수치 같음). 스크립트 비ASCII 0줄 |
| J14 보안 | PASS | 새·바뀐 스크립트에서 계좌 식별자 검색 0. subprocess는 git 두 번뿐 |
| J15 일지 읽는 쪽 | PASS | 일지 대상 테스트 14·30 OK |
| J16 새 사용자 단계 0 | PASS | next_action_for_user는 기록 모드 주문표의 "저녁 키움 입력" 하나뿐이다(R3-3 날 같은 주문표 표시 포함, "켜" 전 4). 재실행·불일치는 Cowork push |
| K2·K8 | PASS | 등록부 미변경(r2~r4 범위 밖). K8은 F절 스모크로 재확인 |

## F. 테스트 (Windows, 직접)

| 대상 | 결과 |
|---|---|
| `-p "test_auto_core*"` | Ran 286, OK (skipped=1: 실자료 스모크, worktree에 30분봉 없음). 1차 223 → +63 |
| `test_portfolio_review_journal*` | 14 OK |
| `test_decision_journal_cards*` | 30 OK |
| `test_run_portfolio_exposure_review*` | 24 OK |
| `test_portfolio_status*` | 15 OK |
| 스키마 감사 | `validate_schema_contracts.py` PASS, errors [] |

**전체 스위트** (test-runner 실행, 원본 로그 `scratchpad/full_suite_t2core.log`에서 직접 셈)
- Ran 2907, FAILED (failures=19, errors=9, skipped=3)이고, FAIL/ERROR 줄은 28개다.
- 모듈 분포가 1차 Judge 기록과 같다: v2_6_7 14 · materialize_kiwoom 2 · nbis_v4 2 · setUpClass 3 · 나머지 7개 모듈 각 1.
- auto_core·journal 관련 실패는 0이다.
- 28줄을 낸 13개 모듈을 하나씩 import해 보니, 바뀐 모듈(auto_core*·portfolio_review_journal)을 직접이든 간접이든 불러오는 것이 하나도 없다. 따라서 T2와 무관하다.
- 새 실패 0, 고쳐진 것 0. Ran +63은 r2 30 + r3 15 + r4 18과 같다.
- (cd6a56d를 git archive로 풀어 같은 13개 모듈을 돌린 대조는 경로·무시 자료 차이로 실패 수가 훨씬 많아 기준선으로 쓰지 않았다.)

**바뀐 기존 테스트**
- `def test_` 수는 2869로 늘기만 했다.
- r2 고정 테스트 1개(위 B-1)는 단언이 늘었다.
- 픽스처 현금 변경은 이유가 맞다. Scenario 20000→30000, Env 5000→30000이며, 그 세션 EV4가 들어가면서 옛 기본값은 1차 선 아래가 된다. `≤ 20000` 단언은 그대로다(`test_auto_core_tickets.py:425`).
- r3 픽스처 날짜 5곳도 이유가 맞다(D 표).
- r4는 기존 테스트 변경 0이다.

**실자료 리플레이 스모크** (1차 K8과 같은 인자: `--start 2026-07-10 --end 2026-10-09`, main closes-root, 실측 파일 sha256 84b542a0…(커밋본과 같음), 출력은 세션 임시 폴더)
- 결과: 종료 0 두 번, schema_errors [], exceptions 0, 두 실행의 replay.json이 바이트 단위로 같다.
- 판정: R-A PASS(앵커 26) · R-B PASS(P-R1·P-R2) · R-C NOT_MET. 1차와 같다.
- worktree 상태와 main `workspace/outputs/auto-core`는 바뀌지 않았다.

## G. 조건 — 언제 처리하나

**병합 전**
1. Cowork는 이 보고를 `_pending`에 등록한다. Judge는 이 파일 하나만 쓰므로 등록하지 않았다.
2. 1차 보고 4절 병합 조건은 그대로다: 병합 때 Q1~Q4 답, P-1(`decision_mode "compare"`) 적용, P-2는 따로 "적용".
3. 병합을 막는 새 조건은 없다.

**비교 모드 중 (Cowork 확인 — 사용자 손 0)**
1. 1차 조건이 이어진다.
   - K6: 실제 무효주문 LOC 행의 cncl_qty를 확인한다.
   - K1 7: C6 방향 해석의 대조 차이를 추적한다.
2. R2 판정 때 b2_wide 목록(여유 1~3% B2)을 직접 본다.
3. **실행 자체가 빠진 날**(decision.json 없음)은 연속 일수 이력에 들어가지 않아 끊기지 않는다(`auto_core_compare.py:290-304`). R2 판정 때 Cowork는 5일이 연속된 실행일인지 알림 11(직전 실행 누락)과 같이 확인한다.
4. r4 새 사실 G(같은 종목·방향 주문표 두 개가 함께 분류되는데 오래된 쪽이 unknown)는 정상 운영에서 생기지 않는다. 생기면 기록만 남긴다.

**"켜"(기록 모드) 전 — 일반 변경 또는 배포 항목**
1. **r4 E — 창 끝 날짜의 마감 뒤 행**: 끝 날짜 행은 ord_time ≤ 세션 마감 KST만 쓴다. 지금은 D+1 05:00~07:45 KST에 따로 넣은 같은 종목·방향 주문이 T의 결과로 분류된다.
2. **r4 F — 같은 날 조회 안의 중복 ord_no**: T1의 FILL_ROW_DUPLICATE_CONFLICT처럼 F6에도 중복·충돌 검사를 둔다(지금은 수량을 두 번 더함). 체결이 있으면 T1 대조가 불일치로 잡지만, 미체결은 changed로 잘못 간다.
3. **재실행 push 전달**(r2-3 7): `CORE_DECISION_ALREADY_RECORDED_DIFFERENT` push는 `decision.rerun-*.json`에만 있다. 배포 때 알림 작업이 그 파일을 읽게 한다. 아니면 이 예외 알림은 나가지 않는다.
4. **휴장 날 입력 문구**(r3-2 4): R3-3 날의 next_action_for_user·주문표 행에 다음을 적는다.
   - 이것이 <발행일>에 나간 같은 주문표라는 것
   - "이미 입력했으면 다시 넣지 않음"

   그날은 미체결 조회를 하지 않으므로 표시로만 중복 입력을 막을 수 있다.
5. **HOLD/FAIL 날의 EV4 유실**: 지난 세션의 EV4는 F1까지 간 기록에서만 모인다(`auto_core_decide.py:572-573`). T1 없음·kill 등으로 F1 전에 끝난 날에 계좌가 1차 선 아래였다가 다음 날 회복하면, 그 EV4 이벤트는 R-REC1에 들어가지 않는다(fail-open 경계 사례, 1차부터 있음). 그날 T1 스냅샷과 종가로 EV4를 다시 구할지, 다른 방식으로 막을지 Cowork가 정한다.
6. **G0_TICKET_SESSION_NOT_YET push**(r3-2 7): 기록 모드에서 이 이상 상태에 예외 push를 붙일지 정한다(지금은 HOLD 사유만).
7. 1차 "켜" 전 6이 그대로 이어진다: R1 리플레이 판정 때 extra_tickets 설명, 가정 24번 두 가지.
8. 1차 "켜" 전 7이 그대로 이어진다: 정책 문턱 변경 절차에 POLICY_EXPECTED 동반 수정을 적는다.
9. 1차 "켜" 전 8이 그대로 이어진다: 지시문 R1·R2·R3.

## 메모

1. **파일 수**: 지금 집합은 새 24 + 수정 7 = 31이다. Builder 1차 보고 2절의 목록과 하나하나 같다. 1차 Judge 보고와 Cowork 사전 확인의 "새 25"는 세는 법 차이로 보인다(새 경로 0).
2. **EV3ⓑ 공백의 기준 지수**: 후보별 R-REC1은 그 후보의 RG2 벤치마크(전력 업종 = GRID)로 공백을 본다. 포트폴리오 R-REC1은 SOXX로 본다. r2 지시문은 "SOXX"라고 적었지만, 코드의 EV3ⓑ 정의(그 벤치마크의 −1σ 날)와 일관된다. 매수는 포트폴리오·종목 둘 다 열려야 하므로 더 엄격한 쪽이다.
3. **탐침 과정 기록**: 첫 실행에서 P1 8건이 실패했다. 원인은 내 가짜 decision_key가 16진수가 아니었던 것("k"×64)이다. 그때 코드는 일지 payload 검사로 쓰기를 거부(FAIL)했고, 주문표를 열린 채 두었다. fail-closed로 옳게 동작한 것이다. 키를 16진수로 고쳐 132/132가 통과했다.
   - 같은 관찰: 일지 payload가 틀린 미분류 주문표가 생기면 매일 FAIL·DECIDE_FAIL이 반복된다. 키는 코드가 만드는 sha256이라 운영에서는 생기지 않는다.
4. **Builder 보고 수치**: r3 보고의 `def test_` 2850은 r4 보고가 2851로 바로잡았다. 지금 2869, 전체 Ran 2907로 맞는다.
5. **사용자 손 비용**: 이 판정이 더하는 일상 사용자 단계는 0이다. "켜" 전 항목은 Builder·Cowork 몫이다.
