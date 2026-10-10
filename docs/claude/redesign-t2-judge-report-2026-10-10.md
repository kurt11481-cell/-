---
id: redesign-t2-judge-report-2026-10-10
title: 재설계 T2 독립 Judge 판정 — 판정 규칙 코드화 · 주문표(주문 1단계) · 일지 자동
date: 2026-10-10
judge: Claude Code Opus 5.5, 새 세션(메인 체크아웃). 파일 수정 없음 — 이 보고 1개만 씀
judge_prompt: docs/claude/redesign-t2-judge-prompt-2026-10-10.md (sha256 5867bade…)
builder_prompt: docs/claude/redesign-t2-builder-prompt-2026-10-10.md (sha256 3e754a271a0d7d76… 확인 — Judge 지시문과 같은 최종본)
target: .claude/worktrees/t2-core (branch worktree-t2-core, base cd6a56d, 미커밋 — 수정 7 + 새 파일 25)
verdict: FAIL (최소 수정 4건 → 변경분 Judge)
authority: 판정은 권한을 주지 않는다. order_authority=false · execution_quantity=null 그대로
consumers: Cowork(병합 판단·Builder 수정 지시) · 관제판 redesign-t2
---

# 판정: FAIL — 매수 관문·재발행 원장에서 새는 곳 4건(최소 수정 F-1~F-4) 뒤 변경분 Judge

- 주문 경로 0, 체결 추정 0, 비교 모드 무쓰기, 기준값 불변, 등록부 충실도, 황금 테스트, 실자료 손계산은 모두 통과했다.
- 실패한 J 항목은 두 개다.
  - **J6**: 연구 기록이 없으면 매수가 막혀야 하는데, 지수 ETF(SOXL·TQQQ) 매수 주문표는 나온다.
  - **J10**: 이른 HOLD/FAIL 날에 재발행 원장과 미분류 주문표가 끊긴다.
- 그 밖에 R-REC1(G5) 결함이 두 건 있다.
  - 그 세션의 EV4가 반영되지 않는다.
  - 테제 훼손 사실을 10일 창으로만 본다.
- 네 결함 모두 실제 영향은 기록 모드('켜' 뒤) 주문표에서 생긴다. 비교 모드에서는 입력 대상이 아니다. 다만 J 문장 기준으로 실패이고, 고치는 양이 작아서 병합 전 수정을 요구한다.
- 수정 뒤 Judge는 변경분(F-1~F-4 diff와 새 테스트)만 보면 된다.

## 0. 확인 범위와 방법

- **지시문 해시**: 기준 지시문 sha256 = 3e754a271a0d7d761f7b828fff221bd5afeb3e31b817689c081e61c884e06c4a ✓. 실측 파일 sha256 = 84b542a0…(main 미커밋, `_pending/redesign-t2-builder.txt`에 등록돼 23:30 커밋 대기).
- **diff**: `git diff cd6a56d`로 수정 7파일을 보고, 새 25파일은 직접 읽었다. 읽은 파일은 decide·tickets·rules·inputs·bars·compare·replay, journal diff, ps1 2개, 스키마, 정책 제안이다.
- **Windows 테스트**: 직접 돌렸다. 전체 스위트는 test-runner가 돌렸고, 원본 로그에서 실패 id를 직접 셌다.
- **탐침 3개**: 세션 임시 폴더에서 돌렸다. 가짜 자료와 테스트 픽스처만 썼고 저장소에는 쓰지 않았다.
  - P1: 이른 HOLD 뒤 원장
  - P2: 그 세션의 EV4
  - P3: 연구 기록 없음 + SOXL 매수
- **포크 2개(Opus)**: K2 등록부, K8 리플레이와 손계산을 맡겼다. 결과는 직접 재확인했다(등록부 해시 9개 재계산, MU 표 강도 칸 대조).
- **실행하지 않은 것**: 키움 조회, kiwoomcli, `auto_core.py daily/decide`, reconcile auto/apply, 작업 등록, 커밋, 병합.

## 1. 판정표 — 지시문 6절 J1~J16

| 항목 | 판정 | 근거 (worktree 경로 기준 파일:줄) |
|---|---|---|
| J1 범위 | PASS | 바뀐 파일 32개 모두 4절 허용 경로 안. 보호 경로(stock-strategy-system·workspace/policies·.claude·CLAUDE.md·AGENTS.md·tools·.gitignore) 변경 0 — worktree·main 모두 `git status` 빈 결과. main의 alert_policy(10-07 00:04)·decision_journal(10-09 16:04)·portfolio_state(10-10 08:52)·auto_core.json(10-10 14:23) 수정 시각은 Builder보다 앞섬. 줄바꿈만 다른 파일 0: `--ignore-cr-at-eol` stat이 일반 stat과 같음(7파일 +246/−54). 작업 트리는 CRLF로 일관. 기존 테스트 파일 수정 0 → 약화 assert 0. `def test_` 2671→2805, Ran 2710→2844 |
| J2 주문 경로 없음 | PASS | 새·바뀐 scripts·schemas·tests·fixtures·ps1에서 `/api/us/ordr`·`ust2000`·`overseas orders`·`kiwoom_order`·`order_submit` 검색 0건. 키움 호출은 `auto_core_decide.py:104-106`의 account_open_items(ust21050)·account_daily_fills_read(ust21150) 두 가지뿐. 기존 브리지(`:463`)를 T1과 같은 방식(`auto_core_reconcile.py:960-962`)으로 부르고, 프로필 별칭은 조회 전에 검사(`:293-297`). subprocess는 git 두 번뿐(`auto_core_inputs.py:85-88`) |
| J3 체결 추정 없음 | PASS | `classify_outcome`(`auto_core_tickets.py:427-472`)는 ust21150 행의 ord_qty·cntr_qty·cncl_qty·ord_uv·cntr_uv·frgn_trde_tp와 식별 칸(stk_cd·slby_tp_nm)만 씀. 평균가는 cntr_uv 가중. 종가·가격 입력 없음. 종목·방향 표기는 T1 `parse_fills`(`auto_core_reconcile.py:265-266`, FILL_SIDES)와 같음 |
| J4 비교 모드 무쓰기 | PASS | compare는 would_append만 남김(`auto_core_decide.py:557-558`). decide가 쓰는 파일은 decision.json·LATEST_DECISION.json·compare.json·S7 입력 2개·S7 검토 새 파일뿐 — 상태·원장·정책 쓰기 경로 없음. apply 쓰기 순서: 재확인(설정 decision_mode·kill·provenance guard, `:560-571`) → head → 멱등 → 스키마·사슬 검증 → 직전 head 재확인 → 원자 교체 → 재검증(`portfolio_review_journal.py:597-645`). 무쓰기·사슬·멱등·S7 불변 테스트 통과 |
| J5 기준값 불변 | PASS | 상수표(`auto_core_rules.py:26-67`, `auto_core_tickets.py:34-56`) = 규칙 파일(V6 4값 문자열 일치, R5 0.70/0.75, C 문턱), R-REC1 문서(2σ·3σ·1σ·2σ·1.5배·20세션), 설계(3%·2%·½·0.25%·0.5σ·1σ). 새 문턱 없음: 1e-9는 표현 허용, 0.45·3%는 분할 자료 검사, B2 여유값은 부록 B 사전 등록 값. 단 자료 범위 `RESEARCH_LOOKBACK_DAYS=10`(`auto_core_inputs.py:45`)이 R-REC1 창보다 짧음 → F-4 |
| **J6 fail-closed** | **FAIL** | **연구 기록이 없거나 틀려도 지수 ETF 매수 주문표가 나온다.** 매수 요건 ①은 INDEX_ETFS면 연구 기록과 무관하게 ok(`auto_core_tickets.py:210-211`). S7 제안 평가도 SOXL에는 실적 검사가 없음(`portfolio_exposure.py:958-967`). RG1 unk는 R-REC1 이벤트가 열린 날만 막음(`auto_core_tickets.py:256-263`). **탐침 P3**: facts=None·earnings=None(decide가 연구 기록 없을 때 넘기는 값) + SOXL에 새 + 가격 단서 2종류가 나온 날 → 요건 칸 [ok, ok, ok, ok, ok, wait], SOXL 매수 47주 LOC $104.70 발행. 지시문 D4·F3("없거나 틀리면 매수는 막히고")·J6 문장과 다름. 나머지 fail-closed는 통과: 등록부(card_check `auto_core_inputs.py:137-167`), 종가·σ(`auto_core_decide.py:697-699`), S7 최신·fail_closed(`:662-665`), T1 결과(`:299-305`). R-REC1은 매도 경로에 없음(`_sell_ticket` `auto_core_tickets.py:630-679`) ✓ |
| J7 카드 근거 | PASS | 자격 4가지(항목·수락·절 해시·커밋, `auto_core_inputs.py:137-167`) 중 하나라도 아니면 사유가 붙어 매수·매도 모두 차단(`auto_core_tickets.py:549, 563-564`), r_max도 0(`:126-127`). 등록부 9종목 원문 대조에서 다른 칸 0(K2). 기술 신호가 정적 근거에 없음 |
| J8 산식 | PASS | GoldenTests 3개를 직접 다시 돌려 OK. G-1: 후회표 4행이 설계 5절 표와 $1 안, 118주, 꼬리 $1,848. G-2: 하한 $130.56(mult 0.9165 올림), 매수 상한 $148.39. G-3: S7 계획 목표 0.271 → 20주(E 1.5495). SOXL만 팔면 22주→1.552, 23주→1.538. 매수 목표 = S7 `_evaluate_proposal`이 DISPLAY로 통과시킨 가장 큰 격자(`best_target :503-513`), 첫 진입은 ½(`:704`). r을 올리는 경로 0: `choose_step :341-350`, C 단독·연구 기록 상한·자격 검사는 모두 min만 |
| J9 가격 | PASS | type은 'LOC' 고정(`_common_ticket :619`). `loc_price :353-369`: 매수는 배수·가격 모두 ROUND_FLOOR, 매도는 ROUND_CEILING. lo/hi = 기준가 ±1%. 긴급·MOC·강세 지정가 주문표 경로 없음 |
| **J10 유효·재발행·R-NE1** | **FAIL** | 규칙 자체는 맞다: `update_keys :381-404`, `reissue_block :588-600`, 첫 상한 `:729-732`, Q2 연결. 사용자 단계도 없다. **그러나 "닫힘"이 이른 HOLD/FAIL 날을 넘지 못한다.** `_empty_decision`은 keys {}·open_tickets []로 시작한다(`auto_core_decide.py:326-337`). kill_switch, T1 없음/FAIL, 설정·프로필·달력 실패는 F6 전에 그대로 기록된다(`:287-305, 315-323`). 다음 실행은 읽을 수 있는 마지막 기록 하나에서만 원장과 미분류 주문표를 가져온다(`:277, 456-459, 479`). **탐침 P1**: 전날 기록에 닫힌 키(UNFILLED_TWICE)와 발행 주문표 1건 → 오늘 T1 없음 HOLD → keys {}, open_tickets []. 그다음 날 그 결정은 다시 열리고, 그 주문표 결과는 분류·일지 기록되지 않는다. G0의 "직전 주문표 모두 분류"는 빈 목록이라 통과한다 |
| J11 권한 칸 | PASS | ORDER_TICKET_HUMAN_ENTRY는 주문표(`auto_core_tickets.py:63`), order_ticket payload(`portfolio_review_journal.py:74`), ticket·payload 스키마에만 있다. 일지 항목 자체의 quantity_authority는 "none". decision·replay·registry·research 스키마는 order_authority const false, execution_quantity null |
| J12 대조·리플레이 | PASS | 부록 B 범주·여유값은 `auto_core_compare.py:35-50`, 부록 C 기간·포트폴리오·E-R1 상수는 `auto_core_replay.py:54-64`에 상수로 있다. 오라클(`auto_core_replay.py:117-165`)은 plan·buy_requirements를 거치지 않는다(F1 그룹·S7·earnings_blackout·R-REC1을 직접 씀). 실자료 SOXL·NBIS 3세션 손계산 일치(K8). B2 자동 분류가 관대한 점은 비교 모드 조건 1 |
| J13 Windows | PASS | ps1 비ASCII 0줄. `run_auto_core.ps1:17-18`: daily/decide 외에는 exit 3, 로그 이름에 명령 포함. register: 두 이름만(`:25-28`), 60분·IgnoreNew·Interactive·Limited, KST 아니면 exit 2, -PlanOnly 유지, Register-ScheduledTask만 있고 실행은 없음. 이번 세션에서 실행하지 않았다 |
| J14 보안 | PASS | outcome에는 행 수만(`auto_core_tickets.py:438`), 미체결은 개수만(`auto_core_decide.py:113`) 남는다. 새 파일에서 acnt 계열 검색 0건(테스트 마커 줄 제외). test_no_account_identifier_in_outputs 통과 |
| J15 일지 읽는 쪽 | PASS | load_journal OK. 사람 항목에 null이 있으면 예외가 아니라 CORRUPT(`portfolio_review_journal.py:164-168`). journal_view 불변, 채점기 head 일치, journal_pending OK. JournalReaderTests 5개 + 기존 일지 테스트 Windows 통과 |
| J16 새 사용자 단계 0 | PASS | next_action_for_user는 apply 모드에 주문표가 있을 때 "저녁 키움 입력" 하나뿐(`auto_core_decide.py:551-552`). 비교 모드 푸시는 예외만(`:241-243`). 카드 바뀜·대조 차이·결과 불일치는 Cowork 몫 문구. "다시/종료" 질문 없음 |

## 2. 추가 확인 K1~K8

| 항목 | 판정 | 요약 |
|---|---|---|
| K1 Builder 판단 1~27 | 25 수용 · 2 일부 거절(8·10) · 조건부(7·16·23b) | 아래 표 |
| K2 등록부 충실도 | PASS | 9종목 강도·방향·인용·트리거 params·절 해시·수락·kill·일정 모두 원문과 같음. 다른 칸 0 |
| K3 회로·관문 순서 | 물은 항목 PASS · G5 결함 2건(F-3·F-4) | 아래 |
| K4 decide 실패 경로 | FAIL | F-2(실패 경로 원장 끊김). 같은 날 두 번이 apply에서 FAIL(조건) |
| K5 일지 | PASS(메모 1) | 채점기 반환값 무시 |
| K6 결과 분류 | PASS(확인 1) | 무효주문 행의 cncl_qty |
| K7 테스트 | PASS | 대상 5묶음 OK, 전체 새 실패 0 |
| K8 실자료 스모크 | PASS | 예외 0, 손계산 불일치 0 |

### K1 — Builder 판단 1~27

| # | 판정 | 이유 |
|---|---|---|
| 1 시나리오 창(5세션 수익률 60개, 종가 65개) | 수용 | 설계 예시의 하락 분위·최악 1일은 재현된다. 상승 분위 차이는 종가 출처 차이(설계 = 키움 종가, 코어 = 30분봉 정규장 종가 D2) |
| 2 배수 4자리, 같은 방향 반올림 | 수용 | 설계 9-1과 같은 방식이고 영향은 센트 단위 |
| 3 미완성 세션 뒤 ATR unk | 수용 | 값을 만들지 않는다. 비교에서는 B2 CORE_INCOMPLETE_BARS로 보인다 |
| 4 부동소수 허용 1e-9 | 수용 | 표현 허용이지 문턱이 아니다 |
| 5 C3 상태형, 카드 별칭은 앞 조건 없음 | 수용 | 규칙 파일 113·114·128줄 |
| 6 S5 = 아래 3회 이상 | 수용 | R-REC1 DS2 "EMA50 아래 마감 뒤 2세션 안 미회복" |
| 7 C6 | 조건부 수용 | 규칙 110줄의 "반등한/눌린 세션"에 직전 세션 대비 방향 조건을 넣지 않아 더 자주 충족된다. 문장 해석 범위로는 보지만, 비교 모드에서 C6 차이가 B7로 나오면 Cowork가 정의를 결정한다 |
| 8 C7 기준가·최근 10개 기록일 | 일부 거절 | C7(2세션 반응)에는 충분하다. 같은 10일 창이 RG1·EV3ⓑ 훼손 사실에도 쓰이는 것은 R-REC1 60세션 창보다 짧다 → F-4 |
| 9 C8+ 대칭 | 수용 | 경보만 |
| 10 R-REC1 | 일부 거절 | σ에 그 세션 수익률을 넣는 것은 수용(F1 "평가 세션 t까지"). EV5의 C0·L0 = 벤치마크도 수용(부록 A-4). EV4를 지난 기록에서만 받는 것은 거절: 그 세션의 EV4가 빠진다 → F-3 |
| 11 매도 간격 출처가 둘이면 목표 비중이 낮은 쪽 | 수용 | 두 출처를 모두 만족하는 목표다. 이후 후회표는 줄이기만 하고, 출처는 gap.source에 남는다 |
| 12 매도 후회 = 현금·후보 경로 중 큰 최대 후회 | 수용 | 보수 쪽이고 r_max 위로는 못 간다(`:341-350`) |
| 13 W* 격자 범위 | 수용 | 결과는 같고 제안 수만 준다 |
| 14 공식 사실은 새것만 | 수용 | 지시 F3 |
| 15 Q2 = 키 존재로 연결 | 수용 | 7절 "답이 없으면 그 부분 주문표를 만들지 않는 쪽"과 같다. P-1 note에도 적혀 있다 |
| 16 결과가 T1 I2와 다르면 | 수용(조건 1) | G0 실패(`auto_core_decide.py:468-474`), 일지 제외(`portfolio_review_journal.py:585-587`), 푸시 모두 확인. 단 불일치 결과도 원장(keys)을 갱신한다(`auto_core_decide.py:480-481`) → '켜' 전 조건 3 |
| 17 비교 모드 주문표 분류 | 수용 | update_keys가 mode≠apply를 건너뛰고(`:386`), compare에서는 원장 갱신 자체를 안 한다 |
| 18 정책 값 교차 검사 | 수용 | fail-closed 결합. 정책 문턱을 바꾸는 절차에 코드 상수를 함께 바꿔야 한다('켜' 전 조건 7) |
| 19 URL 검사는 항목 단위 | 수용 | |
| 20 official_domains는 발행사만 | 수용 | BE의 BusinessWire 공지는 버려진다(fail-closed). 필요하면 Cowork가 추가 |
| 21 화면용 거리 | 수용 | |
| 22 설정 없음/틀림 = FAIL | 수용 | `auto_core_decide.py:280-282` |
| 23 G-3 | (a) 수용 · (b) 조건 | (a) 설계 7-1("S7 줄이기 순서 ①②③, 주수 = 보유 − ⌊목표 비중 × 자산 ÷ 기준가⌋")과 같고, 설계 예시(SOXL 0.27 → 26주)도 계획 기준이다. (b) 덜 파는 쪽으로만 틀린다: 계획상 SOXL 목표 ≥ SOXL 단독 목표라 매도 수량 ≤ 22. 그러나 앞 순서(MVLL) 미발행 사실은 주문표·매도 뒤 경로에 명시되지 않고, after_sale.e가 1.55 위로 보일 뿐이다(`auto_core_tickets.py:677-678, 785-824`) → '켜' 전 조건 2 |
| 24 리플레이 가정 | 수용(리플레이 전용) | HWM = 첫 세션 가정 때문에 P-R1 EV4가 07-16부터 열려 매수 차단이 생긴다. P-R1 E는 부록 C 전제 1.73이 아니라 1.11~1.47이다(고정 수량 × 그날 가격) → Cowork의 R-C 판정 때 명시 |
| 25 페이지 충돌 | 수용 | |
| 26 등록부 12건 | 수용 | K2 |
| 27 ASCII만 | 수용 | 스크립트 9개 비ASCII 0줄 |

### K3 — 회로·관문
- **물은 항목은 통과.**
  - 매수 열림은 `new_basis_met`(새 M만으로 기준 충족) 또는 `S7 add ∧ ③`뿐이다(`auto_core_tickets.py:558`). S7 add 후보는 보충 ETF SOXL뿐이다(카드 ADD를 넘기지 않음, `portfolio_exposure.py:1215-1216`).
  - 등록부 자격이 없으면 매수·매도 모두 r_max 0이고 차단 사유가 붙는다.
  - G0는 전체 단위다: global_reasons(`:526`)가 모든 후보에 붙는다.
  - G2b·research_only_strong_r_cap은 키가 있을 때만 쓰이고 min만 한다(`:122-125, 735-743, 768-778`).
- **G5 결함 1 (F-3)**: 그 세션의 EV4가 R-REC1에 들어가지 않는다. 종목별 충격은 지난 decide 기록의 ev4_sessions로만 계산되고(`auto_core_decide.py:489-490, 637-640`), 그 세션의 ev4_open은 그 뒤에 계산된다(`:673-676`). 리플레이도 같다(`auto_core_replay.py:260-261`).
  - **탐침 P2**: 직전 기록 없음, 총자산 $6,027(V6 1차 선 아래) → ev4_open true, shock open false, MU 매수 5주 발행, ⑤ ok.
  - 실제 운영에서는 계좌가 1차 선을 처음 깬 다음 날 아침 decide 한 번이 R-REC1 없이 매수 주문표를 낼 수 있다.
- **G5 결함 2 (F-4)**: RG1·EV3ⓑ의 훼손 사실은 최근 10개 연구 기록일에서만 모은다(`auto_core_inputs.py:45, 249-250` → `auto_core_rules.py:708, 749-751`). 이벤트 창은 60세션이다. 그래서 10기록일보다 오래된 훼손 사실이 잊히고, RG1이 ok가 되거나 EV3ⓑ 이벤트가 사라질 수 있다(코드 판독, fail-open).

### K4 — decide 실패 경로
- **통과한 것**
  - 연구 기록 대기는 08:30에 끝난다(`auto_core_decide.py:340-351`). 가짜 시계 테스트에서 45분이다.
  - T1 없음·FAIL = HOLD.
  - kill = HOLD이고 조회 요청은 0건이다.
  - 프로필 별칭이 없으면 조회 전 FAIL.
  - 결과 스키마 오류 = FAIL(`_finish :798-806`).
  - 같은 날 두 번은 compare 모드에서 같은 결과다.
- **FAIL**: 실패·HOLD 기록이 원장과 미분류 주문표를 넘기지 않는다(F-2, J10).
- **조건**: apply 모드에서 같은 날 두 번째 실행은 FAIL(CORE_DECISION_ALREADY_RECORDED)이 되고, DECIDE_FAIL 푸시가 나가며, 그날 decision.json을 FAIL 기록으로 덮는다. 테스트 `test_auto_core_decide.py:332-334`가 이 동작을 고정하고 있다. 지시 F8 "같은 날 두 번 = 같은 결과"와 다르다. 쓰기는 막혀 있어 fail-closed이므로 '켜' 전 조건 1로 둔다.

### K5 — 일지
- 일지는 apply에서만 쓴다(`auto_core_decide.py:557-584`).
- 쓰기 직전 재확인을 한다: 설정 다시 읽기·kill·provenance → head → 멱등 → 직전 head 재확인.
- 사람 apply는 AUTO_CORE를 거부한다: CONFIRMATION_METHODS 불변(`portfolio_review_journal.py:67`), argparse·apply_proposal_entries 테스트.
- `_auto_core_inconsistency`는 코드 검사 전에 돈다(`:164-165`). 사람 항목에 null이 있으면 CONFIRMATION_FIELDS_INVALID다.
- `_atomic_write`의 기본 newline "\n"은 그대로다(`:444`).
- 채점기 예외는 경고로만 남는다(`auto_core_decide.py:577-580`).
- **메모**: `_score`가 `score_decision_journal.main`의 반환값 2를 무시한다(`:738-741`). 그래서 이 실패는 경고로도 남지 않는다('켜' 전 조건 4).

### K6 — 결과 분류
- 다섯 상태 판정(`auto_core_tickets.py:439-472`)은 ust21150 행만 쓴다.
- "Limit On Close" 외 표기 = changed(`:457-458`).
- 비교 모드 결과는 원장을 바꾸지 않는다.
- **확인 필요**: 실제 미체결 LOC('무효주문') 행의 cncl_qty가 0이 아니면 unfilled가 아니라 changed로 분류된다. 원장 효과는 같다(시장 시험 +1). 비교 모드에서 첫 실제 행으로 확인한다.

### K7 — 테스트 (Windows, 직접)

**대상 테스트**

| 패턴 | 결과 |
|---|---|
| `test_auto_core*` | Ran 223 OK (skip 1 = 실자료 스모크, worktree에 30분봉 없음) |
| `test_portfolio_review_journal*` | 14 OK |
| `test_decision_journal_cards*` | 30 OK — VM에서 실패하던 2건은 Windows에서 통과 |
| `test_run_portfolio_exposure_review*` | 24 OK |
| `test_portfolio_status*` | 15 OK |

**전체 스위트** (test-runner, 원본 로그에서 직접 셈)
- Ran 2844, failures 19, errors 9, skipped 3. FAIL/ERROR 줄은 28개다.
- 모듈별 분포가 보고 1절 기준선과 같다: v2_6_7 14 · materialize_kiwoom 2 · nbis_v4 2 · setUpClass 3 · 나머지 7개 모듈 각 1.
- 새 실패 0, 고쳐진 것 0.
- 28개를 낸 13개 모듈은 바뀐 파일을 참조하지 않는다.
- 같은 13개 모듈을 main 체크아웃(코드 = cd6a56d)에서 돌리면 3개만 실패한다. 25개는 main에만 있는 무시 자료로 통과하므로, 이 실패들은 환경 의존이고 T2와 무관하다.

**그 밖**
- 기존 테스트 파일 수정 0.
- 황금 G-1·G-2·G-3 값은 `test_auto_core_tickets.py:43-101`에서 확인했다.
- G-3 테스트는 `_sell_ticket`을 거치지 않고 같은 식을 테스트 안에서 계산한다(메모).

### K8 — 실자료 스모크 (포크 실행, 결과 재확인)

**실행**
- `auto_core_replay.py --start 2026-07-10 --end 2026-10-09`를 main의 closes-root와 실측 파일로, 출력은 세션 임시 폴더로 돌렸다.
- 종료 0, 약 3초, 예외 0, 스키마 오류 0. 다시 돌린 결과가 바이트 단위로 같다.
- worktree 상태와 main `workspace/outputs/auto-core`는 바뀌지 않았다.

**판정**
- R-A PASS: 앵커 26개.
- R-B PASS: 오라클 열림 0.
- R-C NOT_MET: 관심 종목·GRID 자료가 없어 예상된 결과다.

**손계산** — 저장소 모듈을 import하지 않은 독립 스크립트로 원본 30분봉 페이지에서 일봉과 지표를 만들었다.
- SOXL·NBIS 각 65세션 × 지표 15종의 불일치 0(최대 상대 오차 2e-16).
- 트리거 상태 불일치 0.

| 세션·종목 | 회로 | 주요 값(손 = 코어) | 첫 차단 |
|---|---|---|---|
| 08-13 NBIS | 매수 열림(NEW_EVIDENCE: C3+·C5+ 새로, "C 단독" → r_max ≤ ⅓) | 종가 255.025 · EMA20 209.3223 · RSI 60.8417 · ATR 26.6170 · σ60 0.092640 · C2− 선 270.68 ≤ 고가 275.96 | REQ1_EARNINGS:no (NBIS 실적 기록 없음 = 금지 구간) |
| 07-29 SOXL | 닫힘 | 종가 91.92(−16.06%) · RSI 33.5148 · C1+·C5−·S4·S5 hit · S6·S8 review | NO_CIRCUIT_OPEN (S7 줄이기 항목 없음, E 1.108) |
| 08-11 NBIS | 닫힘 | 종가 192.81 · N9 review(193.50까지 여유 0.36%) · C4−·N6 hit | SELL_CIRCUIT_CLOSED / BUY_CIRCUIT_CLOSED |

## 3. 최소 수정 목록 (FAIL 해소 — Builder, 같은 worktree)

| # | 결함 | 최소 수정 | 고정할 테스트 |
|---|---|---|---|
| F-1 | J6: 연구 기록 없음/틀림에서 지수 ETF 매수 주문표가 나옴 | 그날 연구 기록 상태가 OK가 아니면 모든 매수 후보에 차단 사유(예: `RESEARCH_RECORD_NOT_OK`)를 붙인다. 매도에는 붙이지 않는다 | research 없음 + SOXL에 새 + 가격 단서 2종류 → SOXL 매수 0, 사유 확인 / 같은 조건의 매도는 그대로 |
| F-2 | J10·K4: 이른 HOLD/FAIL 기록에서 재발행 원장과 미분류 주문표가 끊김 | F6 전에 끝나는 모든 기록(kill, T1 없음·FAIL, DecideFailure·예외)에 직전 기록의 keys와 미분류 주문표(open_tickets + 아직 분류 안 된 tickets, issued_day 포함)를 그대로 넘긴다. 또는 다음 실행이 "F6를 실제로 돈 마지막 기록"에서 가져온다 | D apply 주문표·닫힌 키 → D+1 T1 없음 HOLD → D+2에서 D 주문표 분류·일지 기록, 닫힌 키 유지 |
| F-3 | G5: 그 세션의 EV4 누락 | 계좌 EV4(V6 1차 선 또는 S7 hwm × 0.9)를 R-REC1 계산 전에 구해, 열렸으면 그 세션을 ev4_sessions에 넣고 종목별·포트폴리오 충격을 계산한다. 리플레이도 같은 함수를 쓴다 | 직전 기록 없음 + 총자산 ≤ 1차 선 → shock open, ⑤ ≠ ok, 매수 0 |
| F-4 | G5: 훼손 사실 10기록일 창 | root_thesis_damage 사실(RG1·EV3ⓑ용)은 R-REC1 창(60세션)을 덮는 기간의 연구 기록에서 모은다. 기록이 그 기간보다 짧게 남아 있으면 RG1은 unk로 둔다 | 이벤트 뒤 15기록일 전 훼손 사실 → RG1 no/unk, 매수 0 |

## 4. 조건

**병합 전**
1. F-1~F-4를 수정하고 테스트로 고정한다. 기존 테스트 약화 0, 대상 테스트 OK, 전체 스위트 실패 28줄 유지(새 실패 0).
2. 변경분 Judge(새 세션, Opus): F-1~F-4 diff, 새 테스트, 대상 테스트를 Windows에서 다시 실행한다. 이 보고의 나머지 PASS 판정은 수정이 그 범위를 건드리지 않는 한 유지한다.
3. Builder 보고를 5절 "다른 사실" 1~6대로 고친다.
4. Cowork: 이 보고를 `_pending`에 등록한다. Judge는 이 파일 하나만 쓰므로 등록하지 않았다. 병합 때 7절 Q1~Q4 답을 받고, P-1(decision_mode "compare")을 적용한다. P-2는 따로 "적용"을 받는다.

**비교 모드 중 (Cowork 확인 — 사용자 손 0)**
1. **F9 대조가 관대하다.**
   - N_DIFFERENCE·R5_DIFFERENCE는 차이 크기와 무관하게 B2로 자동 분류된다(`auto_core_compare.py:183-188, 194-201`).
   - EMA 기반 거의 모든 그룹이 3% 여유를 받는다(`:93-94`, 알려진 차이 ② 확대 적용).
   - decide FAIL·이른 HOLD 날은 대조 기록이 없어 "건너뜀(유지)"로 처리된다(`:255-257`).
   - 그래서 R2 판정 때 Cowork가 직접 본다: |ΔN| > 0.01 항목, 여유 1~3%인 B2 항목, 5일 창 안의 FAIL·이른 HOLD 날(유지가 아니라 0으로 본다). 또는 일반 변경으로 상한을 둔다.
2. **실제 ust21150 행**으로 무효주문 LOC의 cncl_qty를 확인한다(K6). 비교 주문표와 같은 종목·방향에 사용자 주문이 섞이면 changed로 분류된다.
3. **S7 검토 최신 파일**: decide가 같은 세션 폴더에 격자 제안 수백 개가 든 S7 검토 파일을 07:45 이후 새로 쓴다(덮어쓰지는 않음). '최신 파일'을 읽는 소비자(카드·M6·상태 화면)에 영향이 없는지 확인한다.
4. C6 방향 해석(K1 7)의 대조 차이를 추적한다.

**"켜" 전 (기록 모드 전 필수)**
1. apply 같은 날 재실행 멱등: 같은 평가 세션의 core_decision이 같은 decision_sha256으로 이미 있으면 쓰지 않고 OK로 끝낸다. 그날 decision.json을 FAIL로 덮지 않고, 테스트 `:332-334`를 바꾼다.
2. 앞 순서 미발행 표시(K1 23b): 매도 주문표 gap·after_sale에 "S7 계획 전제(앞 순서 종목과 오늘 그 주문표 유무)"와 "이 주문표만 체결될 때 예상 E"를 한 줄로 적는다.
3. OUTCOME_MISMATCH_WITH_RECONCILE 결과는 원장을 다시 열지 않는다. 닫거나 갱신에서 제외한다.
4. 채점기 반환값이 0이 아니면 score_warning으로 남긴다.
5. 등록부의 kind와 side를 묶는다: drop_alert·close_at_or_below는 side alert만. 코드나 스키마로 한다. 경보가 매도 근거로 바뀌는 등록부 실수를 막기 위해서다.
6. R1 리플레이(부록 C, 외부 오라클 먼저 커밋) 판정 때 extra_tickets(오라클이 열지 않았는데 나온 주문표)도 하나씩 설명한다. 가정 24번 두 가지(HWM = 첫 세션 → EV4, P-R1 E 전제)를 명시한다.
7. 정책 문턱(1.55·1.85·1.9·0.4)을 바꾸는 절차에 `POLICY_EXPECTED`(`auto_core_tickets.py:55-56`) 동반 수정을 적는다. 빠지면 G1 POLICY_THRESHOLD_CHANGED로 주문표가 0이 된다.
8. 지시문 R1·R2·R3 그대로.

## 5. Builder 보고와 다른 사실

1. **6절**: "연구 기록 없이 돌아 매수 막힘"은 개별 주식만 맞다. 지수 ETF(SOXL·TQQQ) 매수는 막히지 않는다(J6, 탐침 P3).
2. **5절 10번**: EV4를 지난 decide 기록에서 이어받는다고만 적었다. 그 세션 자신의 EV4가 R-REC1에 들어가지 않는다는 사실은 없다(탐침 P2).
3. **5절 8번**: "최근 10개 기록일"은 C7만이 아니라 RG1·EV3ⓑ 훼손 사실에도 적용된다(F-4).
4. **apply 모드 같은 날 재실행 = FAIL**: 테스트로 고정돼 있는데 5절 판단 목록에 없다. 지시 F8 "같은 결과"와 다르다.
5. **3절 리플레이 스모크**의 "매수 회로가 열리지 않음"은 틀렸다.
   - 코어 경로에서는 NBIS 08-13(두 포트폴리오)과 MVLL 08-20(P-R1)에서 매수 회로가 열렸다.
   - 둘 다 관문(REQ1·REQ2·POLICY_UNREGISTERED)에서 막혔다.
   - 오라클 열림 0은 "열림 + 관문 통과"만 세기 때문이라 모순은 아니다.
6. **이른 HOLD/FAIL 날 원장·미분류 주문표 끊김**(J10, 탐침 P1)은 보고에 없다.

## 6. 메모

- **부록 C 전제 차이**: 지시문 부록 C는 P-R1 E를 1.73으로 전제했지만, 실제 리플레이 E는 1.11~1.47이다. 지시문 쪽 사실이며 R-C 해석 때 같이 본다.
- **실측 파일 대조**: Builder가 읽은 main 사본의 해시 기록이 없다. 커밋본(84b542a0…)을 기준으로 삼는다.
- **사소한 것(주문표 영향 0 또는 줄이는 쪽)**
  - 매수에서 단계를 적용한 뒤 0주가 되면 LOT_ZERO 대신 CASH_ZERO/G2B_CAP로 표시된다(`auto_core_tickets.py:720-754`).
  - C7+ 종류에 customer_change가 더해져 있다. 규칙 문장은 가이던스 하향·희석·주요 계약 축소다.
  - LITE 밸류에이션 neutral 행의 방향이 "+"다.
  - MVLL 일정 라벨의 "Q3"는 카드에 없는 말이다.
  - MVLL(매수 불가 상품)의 매수 후보가 생성된 뒤 관문에서 막힌다(표시 정확도).
  - U6·BE6·AM6의 band 값은 코드가 읽지 않는다(공통 C6+를 씀).
- **사용자 손 비용**: 이 판정이 더하는 일상 사용자 단계는 0이다. 수정과 변경분 Judge는 Builder·Judge 세션 몫이다.
