---
id: c6-fix-review-2026-10-14
title: c6-fix 검토 — 코어 C6± 반등·눌림(전일 대비 방향) 조건 추가
date: 2026-10-14
class: 검토 (코드 변경 없음). 수정 자체는 권한 경로 dev-run(authority-paths.txt) → 사용자 결정 뒤 큐
source: docs/claude/redesign-t2-day2-check-2026-10-14.md 18·25행
consumers: c6-fix builder prompt(결정 뒤 작성), 개발 관제판 tasks/c6-fix, redesign-t2-compare-explained.json(MU CORE_BUG 근거)
authority: order_authority=false · 규칙 파일·정책·상태 변경 없음
---

## 결론
- **CORE_BUG 확인.** auto_core_rules.py 330~337행 C6±에 "반등한/눌린 세션"의 전일 대비 방향 조건(c_{t-1} > c_{t-2} / c_{t-1} < c_{t-2})이 없다. 규칙 문구, 사전 등록, 리플레이 스크립트, 카드 DL6에는 모두 이 조건이 있다.
- **권장 A: C6- · C6+ 양쪽에 조건 추가**(엄격 부등호, 사전 등록과 같음). 상수·문턱·규칙 파일은 바뀌지 않는다.
- 분류: 내용은 일반 변경(규칙 문구에 코드를 맞춤, D16 값 불변). 다만 경로가 권한 경로(auto_core*.py, tests/test_auto_core*.py)라서 파이프라인이 NEEDS_APPROVAL로 끝난다. 큐에 넣으려면 사용자 결정 기록이 필요하다(dev_pipeline README 44행). builder_model은 opus.
- 기본 처분: 답이 없으면 NO_CHANGE(현행 코드 유지). 그 경우 MU 대조 B7(CORE_BUG)이 10-12 C6- 창(~10-16)까지 이어지고, 같은 모양이 나올 때마다 다시 생긴다.

## 근거 (이번 세션에서 연 원문)
| 항목 | 위치 | 내용 |
|---|---|---|
| 코어 | manage-us-stock-strategy/scripts/auto_core_rules.py:330-337 | C6-: c_{t-2}<E_{t-2}, c_{t-1}<E_{t-1}, c_{t-1}≥E_{t-1}×0.985, c_t<c_{t-1}, c_t<E_t. 방향 항 없음(C6+ 대칭) |
| 규칙 | integrated-check-prompt-v3.12.2-2026-10-09.txt:110 (v3.12.4-2026-10-14:110 같은 문장), :104 "각 쌍은 같은 숫자를 위아래로 뒤집은 것" | "1.5% 이내까지 **반등한** 세션", "**눌린** 세션" |
| 사전 등록 | c-rule-replay-preregistration-2026-10-09.md:75-76, :79 (ii) | c_s > c_{s-1} / c_s < c_{s-1} |
| 리플레이 | stock-strategy-system/backtests/c_rule_replay_2026-10-09.py:162-167, 자체 시험 :682-696 (sha256 5e618b53…, 결과 문서 15행과 같음) | 방향 조건 포함, "반등 아님"이면 False |
| 카드 | integrated-stock-cards-v1-2026-10-02.md:274 (DL6 "눌린 뒤 반등 마감"), :448 ("내려왔다가 반등") | 같은 뜻 |
| 경위 | redesign-t2-builder-report-2026-10-10.md:273 (Builder가 방향 조건을 넣지 않음), redesign-t2-judge-report-2026-10-10.md:82 (조건부 수용, 대조에서 B7이 나오면 Cowork가 정의를 정함) | 지금 그 조건이 충족됨 |
| 카드 별칭 | auto_core_rules.py:499-500 | pullback_rebound = 공통 C6+ 배열 → U6·BE6·DL6 등은 따라서 고쳐진다. C6-의 카드 별칭은 없다 |

## MU 재계산 (코어 함수로 계산, 평가 세션 2026-10-13, 자료 regular-session-closes 정규장 일봉)
| 세션 | 종가 | EMA20 | 전일 대비 | 현행 | 수정 뒤 |
|---|---|---|---|---|---|
| 10-06 | 1045.44 | 1036.24 (+0.89%) | -1.72% (눌림) | | |
| 10-07 | 1087.84 | 1041.15 | +4.06% | C6+ 충족 | C6+ 충족 |
| 10-08 | 1035.47 | 1040.61 (-0.49%) | -4.81% | | |
| 10-09 | 1028.00 | 1039.41 (-1.10%) | **-0.72% (반등 아님)** | | |
| 10-12 | 988.96 | 1034.60 | -3.80% | **C6- 충족** | 미충족 |
| 10-13 | 953.19 | 1026.85 | -3.62% | C6+ 10-12에 해소 | C6+(U6) 충족 유지(창 10-07~10-13) |

- 수정 뒤 MU 매도 근거는 [rebound_fail, trend_break] → [trend_break]가 되어 basis_met true → false(auto_core_tickets.py:140 "강 1 또는 약 종류 2"). 매수 쪽에는 pullback_rebound 그룹이 생긴다(새 근거 아님: 10-07부터).
- 10-14 주문표 영향 없음: MU는 관심 종목(member)이라 매도 근거는 표시만이고(보유 알림은 auto_core_decide.py:404 held만), 매수는 충격 RG2·RG3 "no"로 막힘(decision.json 2026-10-14). → 아래 "미해결 2건 처리" 1에서 리플레이로 확인.

## 영향 범위 (2026-04-01~10-13, 135세션 × 8종목)
- 원시 충족: C6- 8→7, C6+ 24→20. 보유 MVLL·NBIS·SOXL은 수정 전후가 같다(0·1·0).
- 안전 방향: 조건을 하나 더할 뿐이라 충족을 새로 만들지 않는다. 매수 쪽은 엄격해진다. **매도 쪽은 좁아진다**: 매도 주문표는 간격 출처 + basis_met를 함께 요구하므로(auto_core_tickets.py:709) 잘못된 C6-가 보유 종목의 둘째 약 근거였다면 그 매도 주문표·알림이 사라질 수 있다. 다만 그 C6-는 규칙이 정의하지 않은 근거다. 위 기간 보유 종목에서 실제로 그런 날은 없었다.
- 대안 검토: NO_CHANGE(차이가 매번 B7로 남음) / REMOVE·SIMPLIFY 해당 없음 / REUSE: 같은 `_cmp` 한 항씩 추가 / B안: C6+만 고침(매도 손대지 않음) → 규칙 104행 대칭과 110행 문구를 일부러 어기는 것이고, CLAUDE.md의 "매수 막고 매도 안 막음"은 자료 누락·관문 규칙이지 정의 수정에는 해당하지 않아 기각 / 규칙 문구를 코드에 맞춤 → 카드·사전 등록·리플레이와 어긋나 기각.

## 테스트 영향 (임시 사본에 수정만 넣어 실행, 이 PC의 Linux VM python)
- 현행 그대로인 테스트: test_auto_core_rules C6 테스트(기존 예시는 방향이 맞음).
- 새로 실패하는 3개(고정 자료의 "눌림" 세션이 실제로는 올랐다): test_auto_core_compare_fix `EventDayMarginTests.test_card_alias_of_an_event_rule_uses_its_firing_session`, test_auto_core_decide `ResearchRecordBuyGateTests.test_record_not_ok_blocks_the_index_etf_buy`(하위 3개), test_auto_core_tickets `ResearchRecordGateTests.test_no_research_record_blocks_the_index_etf_buy`. 앞 2개 파일의 `soxl_two_new_cues`는 끝 3종가 100.05·100.3·100.5라 눌림이 아니다 → 고정 자료를 눌림 모양으로 바꾸고 테스트 뜻(C5+·C6+ 두 종류 새 충족)은 그대로 둔다.
- 별건(c6와 무관, 기존 실패): test_auto_core_risk1r `UnchangedTicketTests.test_tickets_without_risk_1r_hash_as_before`가 실제 저장소에서 지금 실패한다(이 VM 기준, Windows는 확인 필요). 파이프라인 기준선에 들어가므로 c6-fix를 막지는 않는다.
- 소비자: auto_core_replay.py·auto_core_compare.py·decide·tickets가 같은 함수를 쓴다. test_auto_core*.py 전체를 대상 테스트로 둔다. 다시 돌린 리플레이·대조 결과는 이전 기록(redesign-t2-compare-explained.json 등)과 달라진다(의도된 차이).

## Builder 지시 요점 (결정 뒤 c6-fix-builder-prompt.md로)
- class authority, builder_model opus/high. allowed_paths: auto_core_rules.py, test_auto_core_rules.py, test_auto_core_compare_fix.py, test_auto_core_decide.py, test_auto_core_tickets.py, docs/claude/c6-fix-report.md. target_tests: test_auto_core*.py.
- raw_common C6-에 `_cmp(p_close, "gt", pp_close)`, C6+에 `_cmp(p_close, "lt", pp_close)`. 상수·다른 규칙은 한 글자도 바꾸지 않는다.
- 새 테스트: 반등 아님(c_{t-1} ≤ c_{t-2})·눌림 아님 → none, 같은 종가(평평) → none, 자료 None → unk. MU 10-06~10-13 모양 재현(10-12 C6- none, 10-13 C6+ hit).
- 위 3개 테스트는 고정 자료만 고친다(검사 문장 그대로).

## 사용자 손 비용
- 지금 1번(결정 문장) + 병합 때 `-ApproveAuthority` 1번(평소 병합 1번을 대신함). 매주 일상 손 추가 0.
- 진행 중 권한 작업 0(t1-safety·rrec-rg1·cmp-fix3 병합됨, git log). 개발 작업: event-ctx3(일반, READY_TO_MERGE) + c6-fix = 2 ≤ 3.

## 바뀔 조건
- 규칙 파일 110행 문구가 바뀌거나 사용자가 "방향 조건 없음"으로 정의를 정하면 → 결론 철회.
- 보유 종목에서 수정으로 사라지는 C6-가 실제 매도 주문표를 없애는 사례가 나오면 → B안 재검토(사용자 결정).

## 결정 기록
- 2026-10-14 13:31 KST 사용자: "결정 c6-fix: 진행" → 권장 A(C6−·C6+ 양쪽 방향 조건). 지시문 docs/claude/c6-fix-builder-prompt.md, 큐 docs/claude/_dev-queue/c6-fix.txt. 병합: `.\tools\dev-merge.ps1 c6-fix -ApproveAuthority`(경로 때문).

- 2026-10-14 13:48 KST c6-fix 1회차 BLOCKED(지시문 결함): 수정 뒤에는 C5+·C6+ 같은 날 새 충족이 불가능한데 지시문이 그 짝을 유지하라고 했다(Builder 판단 맞음, 수학적 모순 확인). 규칙 수정·새 테스트·compare_fix 자료는 통과. → c6-fix2로 재큐(tickets 634행 기대 짝 pullback_rebound → trend_recover, SOXL 고정 자료 t−2 = 99.85). Cowork 사본에서 test_auto_core*.py 새 실패 0 확인.

- 2026-10-14 14:37 KST c6-fix2 병합(1a2b7d6, ff, Judge PASS 12/12, 새 실패 0, 3022→3026). 첫 적용은 10-15 06:15·07:45 자동 실행. 확인 항목: 10-15 대조에서 MU rebound_fail/pullback_rebound CORE_BUG 0.

## 미해결 2건 처리 (2026-10-14 13:3x KST)
1. **고친 decide 경로 실행 → 해소.** auto_core_replay(decide와 같은 evaluate_session, 읽기 전용, 출력은 저장소 밖)를 2026-07-10~10-13 고정 포트폴리오 P-R1(MVLL·SOXL·NBIS 보유)·P-R2로 수정 전후 각각 실행(각 67세션, 예외 0, R_A·R_B PASS, R_C NOT_MET 동일).
   - 주문표·막힘·후보·no_action: 134개 세션 결과 모두 같다.
   - 근거만 다름(10건, 두 포트폴리오 같은 5건): DELL 10-08 매수 DL6 빠짐(basis 충족 유지), MU 10-12·10-13 매도 C6− 빠짐(basis true→false), MU 10-12·10-13 매수 U6 생김. 보유 종목 근거 차이 0.
   - 한계: 리플레이 가정(고정 포트폴리오, 카드 역적용, 공식 사실 없음)이라 등급 D. 리플레이 기간 주문표가 0건이라 주문표 차이를 볼 검정력은 낮다.
2. **risk1r 실패의 Windows 확인 → 해소(이 VM 환경 문제).** Windows 파이프라인 기준선(event-ctx3, base 1d98bd0 = t1-safety 병합 뒤, Python 3.13.15, 3022개 실행)의 실패 목록 28건에 test_auto_core_risk1r가 없다 → Windows에서는 통과. 이 VM(Python 3.10.12)에서는 GOLDEN 8개 중 decide_compare·decide_apply 2개 해시만 다르다. c6 수정 전후 해시는 VM에서 8개 모두 같다 → c6-fix가 골든을 바꾸지 않는다.

검토 완결: 원문 확인 19/19 · 내장 재검토 2회(반영 4건) · 미해결 0 · 자료 시점 decide 2026-10-14 08:37 KST(세션 10-13), 일봉 regular-session-closes 2026-10-13, Windows 기준선 2026-10-14T00:23Z · 바뀔 조건 위 2개
