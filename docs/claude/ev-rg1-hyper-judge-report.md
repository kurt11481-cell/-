---
id: ev-rg1-hyper-judge-report
title: ev-rg1-hyper 독립 Judge 판정 — R-REC1 RG1 공식 테제 훼손 + 빅테크 훼손 출처 + 계산기 RG1 동반 수정
date: 2026-10-18
prompt: docs/claude/ev-rg1-hyper-judge-prompt.md
target: .claude/worktrees/ev-rg1-hyper (브랜치 worktree-ev-rg1-hyper, HEAD 073582db663633c6c5b860ad5ddcec18b2990f40 = 메인 HEAD, 커밋 안 된 변경)
class: K3 독립 Judge(읽기 전용) — Builder 세션과 다른 세션, 메인 체크아웃, Opus
authority: order_authority=false · quantity_authority=none · execution_quantity=null · 키움 호출 없음 · 파일 수정 없음(이 보고서 1개만 씀; 합성 입력·계산기 --out은 저장소 밖 스크래치 폴더)
---

# 판정 표

| # | 항목 | PASS/FAIL | 근거(파일:행 / 재계산 값) |
|---|---|---|---|
| 1 | 범위 | PASS | `git status --porcelain --untracked-files=all`: M 10개(rules·inputs·decide·tickets·등록부 스키마·references/auto-core-decision.md·card-evidence-registry.json·t2rc-oracle.py·t2rc-check-run.ps1·test_auto_core_decide.py) + 새 파일 3개(보고서·test_auto_core_rg1_damage.py·test_auto_core_rg1_oracle_parity.py) = 지시문 "지켜야 할 것" 1 목록. 등록부 diff = 9행 `"thesis_damage_domains": [...]` 1줄(2칸 들여쓰기, CRLF, 앞뒤 줄과 같음). 실행기 diff = 16행 1줄. test_auto_core_decide.py +5/−0(666~670행: 영문 주석 1 + 임시 등록부 accepted.date 입력 4줄, 단언 변경 0 — diff 안 `assert` 0건). auto_core_compare·auto_core_replay·score_decision_journal·portfolio_exposure·docs/claude/scheduled-prompts·t2-rc-preregistration·stock-strategy-system·workspace/policies diff 없음. 메인 체크아웃 추적 파일 변경 0. 메모: 계산기 G2 식을 `g2_buy()`(t2rc-oracle.py:1942)로 옮김 — 남은 항 글자·의미 같음(base 1851~1855 대조), S16에서 부르기 위한 것(Builder 보고 4-2) |
| 2 | 권한·안전 | PASS | diff 추가·삭제 줄에 order_authority·quantity_authority·execution_quantity·kill_switch·ORDER_TICKET_HUMAN_ENTRY 0건, kiwoom·주문 경로 문자열 0건. 추가 줄 비ASCII 0바이트(계산기 비ASCII 476바이트는 base와 같은 기존 값). 줄 끝: 바뀐 파일 모두 CRLF 줄 수 = 전체 줄 수(rules 1009/1009·oracle 2501/2501·ps1 117/117·등록부 1282/1282 …), 인덱스(HEAD)는 LF — 일괄 변환 흔적 없음(diff --stat 454+/43−). 커밋 없음(worktree HEAD = 메인 HEAD 073582d). 계산기 import = 표준 라이브러리뿐(t2rc-oracle.py:26~35), auto_core*·manage-us-stock-strategy/scripts import 0건 |
| 3 | R0·R1 RG1 | PASS | 코어 auto_core_rules.py:753~797(`KST_FIXED`·`iso_day`·`damage_release_day`·`uncleared_damage`) ↔ 계산기 t2rc-oracle.py:990~1037(`strict_day`·`offset_moment`·`rg1_release_day`·`rg1_uncleared`): 창 W[0]·rel = max(event_session, KST 날짜)·rel ≤ a ≤ d·"Z"→+00:00·오프셋 필수·YYYY-MM-DD 엄격이 같은 식. RG1(i) = U(day_i) 비면 기존 식, 아니면 no(rules:938~942, oracle:1130~1133) — 사건 날과 비교 없음. 포트폴리오 = auto_core_decide.py:990~995(보유 종목 최소 수락일, 하나라도 없음·보유 0 → None). 재계산: 이름 붙은 28경우(S1~S9·S6b + Judge 경우 J1~J7) 코어·계산기 status·RG1·요건 ⑤ 칸 불일치 0. ⓐ 사건 날 훼손(S1·J1)·ⓑ 재기준 전 훼손(S2·J2 EV4 재기준) 모두 RG1 no. announced_at 없음·오프셋 없음 → 해제 불가(S6). 카드 항목 없음 → `card_accepted_on` None(decide:985~988) |
| 4 | R2 시간 소멸 | PASS | 코어 rules:980~983 `current["RG1"] is not False`, 계산기 oracle:1171~1172 `rg["RG1"] != "no"`. S3(사건 → 훼손 → DS1 없이 20세션·RG2 ok): 양쪽 open·no·RG1 no(base 80에서 닫힘). RG1 unk는 막지 않음(조건이 False/"no"만 봄). 모두 충족 닫힘 식 불변 |
| 5 | R3·D2 | PASS | 코어 `damage_block`(rules:871~877, 사건 없음 906·닫힘 990에서 호출) / 계산기 `damage_block`(oracle:1077~1081, 1119·1176): status "no"·open False·rg RG1 "no"(사건 없음 → {"RG1": "no"})·reason `RG1_THESIS_DAMAGE:<정렬 id>`·`rg1_damage`(settle 867~868, 미해제 있을 때만). D2(사건 없음도 막음) 지시문대로. 요건 ⑤: auto_core_tickets.py:271~273 새 가지(unk 다음, open 앞), 기존 세 가지 줄은 diff에서 바뀌지 않음(삽입 3줄뿐). S4·S5·J3·J4 재계산 양쪽 같음 |
| 6 | R4 우선순위·대등 | **FAIL** | rrec1 단계는 같다: 자료 없음 → EV3B 공백(J7: 양쪽 unk) → R3 → 기존 식, 합성 대등 이름 붙은 28경우 + 고정 시드 무작위 300입력×(재수락 없음/있음) = 600실행 불일치 0(Judge가 만든 경우: 같은 날 훼손+EV1·훼손 뒤 EV4 재기준·DS1 반복 중 훼손·창 경계 W[0]·재수락 경계 a = rel−1/rel/t/t+1·두 사실 중 하나만 해제·EV3B 공백+훼손). G-1-1 ①~③(오프셋 없는 기록 전체 제외·결정 시각·event_session ≤ 기록 세션·summary 200자·fact_id 첫 판)도 재현 같음. **그러나 rrec1에 들어가는 ③ 사실이 코어와 다르다**: 계산기 `validate_facts`(t2rc-oracle.py:829~843)는 표지(③) 사실이 if/elif 사슬의 DOMAIN 가지(831~835)로 들어가 그 뒤 검사 — `source_kind`(836)·작성 시각(838~841)·**event_session 거래일 여부(842)** — 를 건너뛴다. 코어 check_record(auto_core_inputs.py:261~270)는 ③ 사실도 남은 검사를 모두 한다(지시문 B-2 "남은 검사를 계속", G-2 "B-2와 같은 규칙"). 재계산(스크래치, 같은 기록 파일을 양쪽 적재기에): event_session = 토요일 2026-09-12인 microsoft.com 훼손 사실 → 코어 damage [] / 계산기 ['DMG-SAT']. 표지 없는 sec.gov 사실은 양쪽 모두 버림(계산기 base도 EVENT_SESSION) → **이번 변경에서 새로 생긴 차이**. 요건 ⑤ 끝까지: 사건 없음·닫힌 사건 두 경우 모두 코어 status ok·칸 ok / 계산기 reqs[4] no(RG1_THESIS_DAMAGE:MSFT-SAT) → MISMATCH가 창 60세션 동안 매일 날 수 있다. 통합 점검 로더는 event_session을 날짜 형식·≤ 평가 세션으로만 거른다(integrated-check-daily.txt:72, 거래일 검사 없음)라 실제로 닿을 수 있는 경로다 |
| 7 | R5 ③ 출처 | PASS | 코어: `damage_domains`(inputs:145, OK 아닐 때 [] 125), `damage_domain` = 공식 아님 ∧ root_thesis_damage is True ∧ `_host_allowed`(258~260) → `damage_only`(274·278~279) → load_research `damage`에만(316~318, 표지 `damage_source`). 소비처 전수(grep): `research["damage"]` → decide:774·1032 → rrec1 두 호출(1099·1104)뿐, EV3b는 표지 제외(rules:880), `facts`·근거·C7·facts_seen은 `research["facts"]`(decide:668·1054)라 ③ 없음, 리플레이 damage [](auto_core_replay.py:256). 계산기: `validate_facts` 호출 3곳 — 1406(history·C7)·1555(오늘 사실·근거·new·r_max)는 인자 없음 → DOMAIN 버림(base와 같음), 1434(load_rrec1_records)만 표지 받음 → `env["rrec_records"]`(1583) → `buy_requirements`의 rrec1(1936)뿐, EV3b 표지 제외(1106). root false → 버림(S9·Judge 실험 'root_thesis_damage false' 양쪽 []), 키 없는 등록부 → base와 같은 버림(S9). 스키마: 선택 키·uniqueItems·소문자 호스트 pattern, required 불변(schema diff +6). 항목 6의 검사 누락은 6에서 판정 |
| 8 | R7 엄격성 | PASS | base 코어(메인 체크아웃 auto_core_rules.py, `card_accepted_on` 없음) vs worktree 코어, 고정 시드 7 무작위 400입력(충돌·−1σ 하락·반등·DS1·EV4·사실 0~3개·표지 30%·announced 6종·기록 all/none/gap): base 막힘(no·unk) → 새 ok **0건**, 사건 목록·사건·C0·L0 변화 **0건**(③ 사실 포함), 사실 없음 입력 결과 dict 차이 0, 창 밖 사실만 있는 입력 dict 차이 0. 재수락 있는 입력 150개(시드 11), 재수락 날 전 평가 세션 2,365개를 잘라 계산: 재수락 있음 결과 dict = 재수락 없음 결과 dict **불일치 0**, 재수락 날 전 느슨해짐 0, 느슨해짐 14건은 모두 평가 세션 ≥ 재수락 날(허용된 해제). S6b(사건 → 훼손 → 충족 며칠 → DS1 → 재수락) 열림·no 확인 |
| 9 | ④ 골든 불변 | PASS | test_auto_core_risk1r.py 미수정(status 목록에 없음)·Windows worktree에서 통과. `-p "test_auto_core*.py"`: base Ran 423·실패 1 / worktree Ran 450·실패 1(같은 PLTR 등록부 실패), 기존 decide·tickets·rules·compare·replay 테스트 수정 없이 통과(허용 입력 1건 제외). `2:RG1DMG`·`rg1_damage`는 미해제가 있을 때만(decide:448~449·475, rules:867~868, by_symbol 1115~1116 조건부). 예외 줄: push True·모드 무관·기존 예외 뒤(decide:471~479), 줄 글자 "R-REC1 RG1 공식 테제 훼손 N건 — 카드 재수락 전 매수 막힘 M종목(대시보드 매수 요건 ⑤)" — 종목 코드·fact_id 없음, 알림 지시문 필터(auto-core-alert.txt:60 `any(c in str(l) for c in B)`)에 걸릴 등록부 종목 코드 부분 문자열 없음. auto-core-alert.txt diff 없음. 실데이터(훼손 0): 10-17 decision shock 재계산이 글자까지 같음(항목 12) |
| 10 | 계산기 고정값 | PASS(현재 diff 기준 — 항목 6 수정 뒤 다시 잼) | Judge가 잰 worktree t2rc-oracle.py sha256_lf(108~111행 방식) = 88c3365bf636386c6f366983ba2658c5c00de796213255e03d24091bd5d1485c = 실행기 16행 값. 원시 c923d43c…(CRLF). diff 범위: 출처 docstring·validate_facts·R0 함수·rrec1·load_rrec1_records·cmd_check env·buy_requirements 호출 인자(accepted_on 1937)·D1(lines_open 정의·항 삭제, g2_buy 이동)·selftest(S1~S9·S16) — 범위 안. selftest PASS(기존 앵커 5 참, fails []) worktree·base 모두. 실데이터 check(--repo 메인, --out 스크래치): 10-16·10-17 모두 기본 NOT_CHECKED(입력 sha) 양쪽 같음 → `--ignore-input-sha` 양쪽 INFO_MATCH·requirements diffs [], 출력 JSON이 oracle_sha256 말고 완전히 같음(88c3365b… vs 5607b09b…) |
| 11 | D1 lines_open (c) | PASS | worktree에 `lines_open` 0건(grep). base t2rc-oracle.py:1851(정의)·1853(`and not lines_open`)만 사라지고 다른 항(E < 1.85·approved·reqs[0]·delta_positive·pauses.new_buy·보유 종목 add 멈춤·peaks)은 g2_buy(1942~1949)에 글자 그대로. 코어: 열린 멈춤 선 → `REVIEW_LINE_OPEN`(portfolio_exposure.py:1378~1386) → new_buy_paused → 요건 ① 막힘(auto_core_tickets.py:240~241). 승인 정의 portfolio-exposure-review.md:27(R4 "until a journal review")·321(`line_review_completed` releases the pause). selftest S16(selftest_g2_lines 2333): 검토 끝난 L2 → G2 True, 열린 L2 → False, PASS |
| 12 | 실데이터 | PASS | 연구 기록 2026-10-13~10-17(최신 10-17) 사실 0건 · root_thesis_damage 0건 · ③ 호스트 0건(Judge 직접 셈). worktree 코어 rrec1 재계산(평가 세션 2026-10-16, 메인 pages+기업 행동, Production 달력, 메인 연구 기록, ev4 = 그 decision 사건 기록 [10-14, 10-15, 10-16], 포트폴리오 카드 날 2026-10-04): 포트폴리오 결과 = 10-17 decision.json shock(by_symbol 제외) **완전히 같음**(event 10-16 [EV2, EV4], RG1 no·RG2 no·RG3 no·RG4 ok, status no), 8종목 by_symbol 완전히 같음, `rg1_damage` 없음. 가정 실험(MSFT microsoft.com 표지 사실, event_session 10-14, 16:05 −04:00, SOXL 실제 봉): 카드 10-04 → `rg1_damage` ['TEST-MSFT-CAPEX'], 수락일 10-15 → 키 없음, 두 경우 그 밖 키 = 사실 없는 결과(EV3b 없음). U(t): 코어 ['TEST-MSFT-CAPEX'] / [] = 계산기 같은 값(W[0] 2026-07-24) |
| 13 | 다른 독자(L3) | PASS(발견에 적음) | 비교 auto_core_compare.py:270~292: open은 R3에서도 False라 RREC:open 불변, 훼손 없으면 rg 불변 → B 분류 불변. 훼손 있으면 코어 RG1 no vs 통합 점검 ok → 292행 B7 UNEXPLAINED "RREC:RG1" 가능(규칙 파일 102행 교체 전). 알림 2:RREC(decide:438~441)은 open만 읽어 불변. 채점 `_shock_periods`(score_decision_journal.py:1328~1347) open 기준 불변, R3 막힘은 rrec1_key NONE(1413~1415) → RREC1_DISPLAY_KEYS(873) → DISPLAY_ONLY(1709~1710). 대시보드 runCore.shock은 open·events·event·rg·ds1만(메인 decide:1206, worktree 1239) → status 없어 '닫힘'으로 보임(rg RG1 no는 보임). 문구 목록은 "발견" |
| 14 | 테스트 | PASS | 대상: worktree `test_auto_core*` 450(base 423 + 27)·실패 1 동일, `test_score_*` 66 OK(base 66 OK), `test_decision_journal_cards` 36 OK(base 36 OK), 스키마 검사 PASS(양쪽). 전체 스위트(test-runner, 로그는 Judge가 grep 재확인): base(메인) Ran 3212·실패 5 / worktree Ran 3210·실패 21·오류 9·건너뜀 3. 수집 ID base 3212 → worktree 3239(+27 = 새 두 파일, base에만 있는 ID 0). Ran 차이 29 = setUpClass 오류 3클래스의 테스트 수 29(ID 목록에서 셈). base 실패 5건은 모두 worktree에도 있음, worktree에만 있는 25건은 모두 바뀐 모듈·등록부·계산기·연구 기록을 참조하지 않는 모듈(테스트 파일과 그 import 스크립트 grep 0)이고 오류 8건은 worktree에 없는 무시 대상 workspace/outputs 산출물 FileNotFoundError → 변경 기인 새 실패 0. S1~S14는 test_auto_core_rg1_damage.py에 있고 단언이 주장대로(값·키·순서·줄 위치·push까지), S15는 parity 파일 LoaderParityTests. 빠진 것: ③ 사실의 source_kind·event_session 검사 경우(항목 6) |
| 15 | 병합·C1 절차 | PASS | 지시문 175~184행: C1 = 병합 뒤 첫 decide부터 0/10(183), 병합 전 C2 일치 불산입(181·183 — 사전 등록보다 엄격), 변경 기록에 계산기·실행기·로더·규칙 파일 v3.12.7 새 sha(49행 고정값, 알림 v2.2는 바뀌지 않음 — 알림 지시문 diff 없음)(183), 실행기 16행과 계산기가 한 병합(H, 병합 뒤 "실행기 16행 = 계산기 sha256_lf" 확인 178) → 중간 ORACLE_SHA_MISMATCH 창 없음, 시각 "화~토 06:00~09:00·23:20~23:45 밖"(182)이 06:15·07:45·08:40·23:30과 안 겹치고 병합 스크립트가 실행 중 작업이면 멈춤(178). 사전 등록 C1 "계산기 결함 → 새 sha·Judge 확인 뒤 0부터"(t2-rc-preregistration :24)보다 느슨해지는 곳 없음 |

# 발견

## 1. FAIL 사유 (항목 6) — 계산기 `validate_facts`의 ③ 사실이 남은 검사를 건너뜀
- 위치: docs/claude/t2rc-oracle.py(worktree) 829~843행. `elif not any(... doms)` 가지 안에서 `marked`가 참이면 `why`가 None으로 남지만, if/elif 사슬이라 그 아래 `source_kind`(836)·`WRITTEN_BEFORE_CLOSE`(838)·`WRITTEN_AFTER_DECIDE`(840)·`EVENT_SESSION`(842) 검사가 실행되지 않는다.
- 코어 대응: auto_core_inputs.py 258~270 — `official`/`damage_domain`을 먼저 구하고 SOURCE_KIND → HOST → EVENT_SESSION(달력·≤ 기록 세션) → ANNOUNCED_AT → SUMMARY를 모두 거친다.
- 영향 재계산: 작성 시각 두 검사는 기록 단위 `research_record_ok`(779~804)가 이미 하므로 차이 없음. load_rrec1_records(1435~1437)가 결정 시각·event_session ≤ 기록 세션·summary를 다시 거른다. 남는 차이 둘:
  - event_session이 거래일이 아닌 ③ 사실(예 토요일·미국 휴장일): 코어 버림, 계산기 받음 → 계산기만 RG1 no·요건 ⑤ no → MISMATCH(계산기가 더 엄격 — 입력 금지 쪽이지만 C1이 그 60세션 동안 쌓이지 않고, 그 방향 첫 주문표는 C3 "확인 대기 — 입력 금지"). 통합 점검 로더는 거래일 검사를 하지 않는다(integrated-check-daily.txt:72; 지시 문구 :37은 "거래일이면 그날, 아니면 직전 거래일"이지만 LLM 계산).
  - source_kind가 열거값 밖인 ③ 사실: 코어는 스키마로 기록 전체 무효(기록 범위에서도 빠짐), 계산기는 기록·사실 모두 받음. 기록 단위 차이는 표지 없는 사실에도 이미 있던 것(범위 밖)이지만 ③ 사실을 받는 것은 새 차이. 로더가 source_kind를 거르므로(:72 `f['source_kind'] in SK`) 지금 경로로는 닿기 어렵다.
- 테스트 공백: selftest·parity 테스트에 ③ 사실의 source_kind·event_session 불량 경우가 없다.

## 2. R7 실험 결과 요약
- 대등(코어 ↔ 계산기 rrec1): 이름 붙은 28경우 + 무작위 600실행, status·RG1·요건 ⑤ 칸 불일치 0. (사건이 index 50 전이면 계산기의 기존 EMA50 자료 공백 규칙(1153~1155)이 달라 비교에서 뺐다 — 이번 변경 전부터 있던 차이, Builder 보고 4-4.)
- 엄격성(base ↔ worktree 코어): 400입력 느슨해짐 0·사건/C0/L0 변화 0·사실 없음 dict 차이 0. 재수락 150입력·재수락 전 2,365세션 결과 = 재수락 없음 결과(소급 해제 0), 느슨해짐 14건은 모두 재수락 날 이후.
- 스크립트: 스크래치 judge_exp_rules.py·judge_exp_loader.py·judge_exp_real.py(저장소 밖, 파일 쓰기 없음 — 로더 실험만 임시 폴더).

## 3. ③ 사실 소비처 전수 표 (Judge grep)
| 쪽 | 위치 | 소비 | ③ 사실 |
|---|---|---|---|
| 코어 | inputs:316~318 → `research["damage"]` | decide:774 → 1032 → rrec1(1099 종목·1104 포트폴리오) | RG1만(EV3b는 rules:880에서 표지 제외) |
| 코어 | inputs:310~312 `research["facts"]` | decide:668(근거·C7)·1054(facts_seen) | 없음(damage_only는 facts에 안 들어감) |
| 코어 | decide:672~674 결정 파일 research_record | status·reasons·dropped만(`damage_only` 키 안 씀) | 없음(③ 사실은 dropped에서 빠짐 — 사실이 있을 때만 달라짐) |
| 코어 | auto_core_replay.py:256 | damage [] | 없음 |
| 계산기 | 1406 load_research_history | history → C7(1567~1568)·research_history | 없음(인자 없음 → DOMAIN 버림, base와 같음) |
| 계산기 | 1555 cmd_check 오늘 사실 | res["facts"]·근거·new·r_max·c7 | 없음(DOMAIN 버림 — 표시 `res.facts.dropped`에는 DOMAIN으로 보임, 코어는 RG1에 씀: 표시만 다름) |
| 계산기 | 1434 load_rrec1_records → env["rrec_records"](1583) | buy_requirements rrec1(1936) → 요건 ⑤·detail rrec1 | RG1만(EV3b 1106 표지 제외) |

## 4. 비교 B7·통합 점검 문구 차이 (병합 뒤 사실과 달라지는 문구 — Cowork 교체 대상)
- 규칙 파일 integrated-check-prompt-v3.12.6-2026-10-15.txt:102 — "이벤트 뒤 RG1(2세션 경과 + … 공식 확인 없음)"(사건 뒤 훼손만 셈 → 창 안 미해제 훼손이면 카드 재수락 전 no), "이벤트 닫힘 = … 또는 … 20세션 경과 + RG2 충족"(RG1 no면 시간 소멸 안 닫힘), "열린 이벤트가 있으면 … ⑤는 RG1~RG4 모두 충족일 때만 통과"(닫힘·사건 없음에서도 미해제 훼손이면 ⑤ 막힘), EV3 ⓑ(③ 도메인 사실은 EV3ⓑ 아님) — 교체 전에는 훼손 사실이 있을 때 비교 292행 B7 "RREC:RG1"이 날 수 있다.
- 통합 점검 로더 integrated-check-daily.txt:37 ㉰ "회사 공식 출처(sec.gov 또는 그 회사 도메인)" — 하이퍼스케일러 IR(symbol = 그 회사 코드, root_thesis_damage 참)도 받는다는 줄. 로더 검사 :72에는 event_session 거래일 검사가 없다(발견 1과 연결).
- 개장 전 점검 event-pre-open-calendar.txt:15 "(회복 관문 R-REC1 RG1은 이 회사 출처를 받지 않는다 — 관제판 ev-rg1-hyper)" — 병합 뒤 거짓.
- 같은 정의 문서: recovery-gate-R-REC1-2026-10-09.md 37·43행 메모, CLAUDE.md R-REC1 요약 "RG1 thesis (no official damage within 2 sessions)"(지시문 병합 절 ④~⑥).

## 5. 남은 위험
- (a) Builder 보고 8(a)~(i) 확인: KST 날짜 단위 재수락, 잘못된 훼손도 재수락 전까지 막힘(매도 불변), B7 RREC:RG1, 관심 cardStatus ↔ accepted.date 어긋남, 도메인 목록 변경 K3, D1, 채점 DISPLAY_ONLY·대시보드 '닫힘' 표시, KST 아침 재수락 한 세션 늦음, 경계 기록의 fact_id 첫 판.
- (b) 호스트 추출 차이(이미 있던 것): 계산기는 정규식 `^https://([^/]+)`(824)라 포트(`:443`)·경로 없는 쿼리(`?a=b`)가 든 URL의 호스트가 코어 `urlsplit().hostname`과 달라진다. Judge 재현: 그런 ③ 사실을 코어는 받고 계산기는 DOMAIN으로 버림(계산기가 덜 엄격 → 코어는 막고 계산기는 주문표 기대 → MISMATCH). 표지 없는 공식 사실에도 base부터 있던 차이라 이번 판정의 FAIL 사유로 세지 않는다. 새 규칙이 훼손을 60세션 붙잡아 영향이 커진다.
- (c) 알림 ⑦은 push 줄 최대 3개(auto-core-alert.txt:61~62)라 기록 모드에서 앞선 상태 줄이 3개 이상인 날 RG1DMG 줄은 "외 N건"으로 접히고, 상태는 저장되어 다음 날 다시 울리지 않는다. 막힘 자체는 요건 ⑤로 유지(표시 위험).
- (d) 등록부 base 판은 지시문 8행 설명과 달리 PLTR이 이미 커밋돼 있다(698baf2). 결과는 기존 실패 1건뿐(Builder 보고 0절과 같음).
- 의견: 결정 a 수정판 ①~④·D1 c·D2 처리는 코어와 계산기 rrec1 수준에서 정확히 구현됐고(대등·엄격성·골든·실데이터 모두 확인), 남은 결함은 계산기 적재기의 ③ 사실 검사 1곳이다. 기본 처분은 NO_CHANGE(병합하지 않음, 현행 관문·계산기 고정값 5607b09b… 유지) — 아래 최소 수정 뒤 재판정.

# 고칠 최소 항목
1. docs/claude/t2rc-oracle.py `validate_facts`(829~843): 공식 여부와 `marked`를 사슬 전에 구하고, 가지를 `if host is None: URL` → `elif not official and not marked: DOMAIN` → (기존 `source_kind`·작성 시각·`event_session` 가지 그대로)로 바꿔 ③ 사실도 남은 검사를 모두 거치게 한다(지시문 B-2·G-2). `damage_domains` 기본값 호출(1406·1555)은 marked가 늘 거짓이라 출력이 base와 글자까지 같아야 한다.
2. 테스트: selftest(또는 test_auto_core_rg1_oracle_parity.py LoaderParityTests)에 ③ 사실 경우 2개 — event_session이 거래일 아님 → 코어·계산기 모두 버림, source_kind 열거값 밖 → 계산기 버림(코어는 기록 전체 무효 — 기록 단위 차이는 기존 범위 밖으로 주석).
3. 새 계산기 sha256_lf로 t2rc-check-run.ps1 16행만 다시 바꾸고 Builder 보고 7절 sha 표 갱신.
4. 재판정 범위(제안): 계산기 diff·실행기 16행·바뀐 테스트 → 항목 6·10·14 재확인과 selftest·실데이터 check 10-16/10-17 재실행. 다른 파일 바이트가 아래 sha와 같으면 나머지 항목 판정은 유지.
- (선택, 권장) 발견 5(b) 호스트 추출을 코어와 같게(`urllib.parse.urlsplit(url).hostname`) — 오늘 사실·C7에도 영향이 있어 범위·분류는 Cowork가 정한다.

# sha256 (Judge가 잰 Windows worktree 작업 트리 바이트, 2026-10-18 05시 KST)

| 파일 | sha256 |
|---|---|
| manage-us-stock-strategy/scripts/auto_core_rules.py | 48433ab8d4c5eae45f9c6e54740e282cf5004807f5ce75842f64ea8cc4fbab4e |
| manage-us-stock-strategy/scripts/auto_core_inputs.py | 6e0f2cf1d6302c87612a41fb06b0ddd347eb279aef0f45d5bccd26b013b49201 |
| manage-us-stock-strategy/scripts/auto_core_decide.py | 1013da08704fb74d7afb30455403d6d3e31f67d75392e93d1242f3c5cb7448f1 |
| manage-us-stock-strategy/scripts/auto_core_tickets.py | 2393fa7b19352fd435846aa67d68604b74ca1d73fb9a0e51b845931433afb8c1 |
| manage-us-stock-strategy/schemas/auto-core-card-registry.schema.json | 5b69e590f16542306ba2af88e72d9e3db434e29e50b3b7cfc3834def713c791e |
| docs/claude/card-evidence-registry.json | 1654aa0d7a525e167452d62800cb9f80237d29649b95e52f0343498cc83abdb8 |
| docs/claude/t2rc-oracle.py | c923d43c749da85581d390eb9e52fd3c730b63874816d1d10116d2aca8fd9501 (원시, CRLF) |
| docs/claude/t2rc-check-run.ps1 | 8a786cbcdfdb6a8e4443a1e8f9e00ae3744ed2ebcd74d7bd4ba605aa936d4209 (원시, CRLF) |
| manage-us-stock-strategy/references/auto-core-decision.md | c47bbc876a12a9263b1d24f6d058131c01ba019a6a0aad7d6ba4c50ad09886a8 |
| manage-us-stock-strategy/tests/test_auto_core_rg1_damage.py | d4c8e9a202f145130b404b490caec9d3f41ce4e38285f400eaef32a05a0b4464 |
| manage-us-stock-strategy/tests/test_auto_core_rg1_oracle_parity.py | ddbc98988e1ddbb31039fba715c28ef34881d60f4fa314759840fbd7b4f258c2 |
| manage-us-stock-strategy/tests/test_auto_core_decide.py | 0b6866a2f564b5faa342d662df478644dc72ffb85b77f2b8c36412533c98519c |
| docs/claude/ev-rg1-hyper-report.md | bcd0c649556aae3d6f9745fb0ef2d198bc0551f26db1d7d1d7198b2c6aa04d85 |

- 새 계산기 sha256_lf: 88c3365bf636386c6f366983ba2658c5c00de796213255e03d24091bd5d1485c (= 실행기 16행 `$ExpectedOracleSha256`, 일치). 메인 계산기(base) sha256 = sha256_lf = 5607b09b47585a8b0799ae84b93cff434ebecdfc2b30f305607c8641b8f02a26.
- 실행기 sha256_lf: 8262212d0c05c24e7fc829aae48fa20c5aa6d8969ca2cd78ac963200b234c595 (원시 8a786cbc…; 메인 base 실행기 5d3502b90b3901823e0eded7d196d7c6710b63765bc7d003dc3e1ef313d2df7b).
- Builder 보고 7절 표의 값과 모두 같다. 항목 6 수정 뒤에는 t2rc-oracle.py·t2rc-check-run.ps1(과 바뀐 테스트) 값이 바뀐다.

# 원문 확인 기록
지시문(빌더·Judge) 전문 · Builder 보고 전문 · worktree diff 전부(rules·inputs·decide·tickets·스키마·등록부·실행기·references·test_auto_core_decide) · t2rc-oracle.py diff 전부와 760~860·1040~1183·1380~1440·1894~1975행 · 새 테스트 2개 전문 · event-strategy-2026-10-13.md 238~258 · pre-on-roadmap-review-2026-10-15.md 50~68·103~126 · recovery-gate-R-REC1-2026-10-09.md 35~43 · t2-rc-preregistration-2026-10-14.md 전문 · auto_core_compare.py 130~160·265~292 · auto_core_decide.py 398~490·593~700·738~750·1084~1116·1200~1210(메인) · score_decision_journal.py 868~876·1325~1347·1392~1420·1704~1714 · auto_core_tickets.py 232~250·262~278 · portfolio_exposure.py 1376~1390 · portfolio-exposure-review.md 27·321 · 연구 기록 스키마 · validation_common.py parse_datetime · integrated-check-prompt-v3.12.6 102 · integrated-check-daily.txt 35~37·52~77 · event-pre-open-calendar.txt 15 · auto-core-alert.txt 44~62·118~124 · 10-17 decision.json shock.

VERDICT: FAIL
