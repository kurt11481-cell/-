---
id: watch-card-gaps-2026-10-17
type: review (결정 요청 포함)
status: 결정 완료 — 사용자 원문 "결정 wcg-1017: 1 b, 2 a, 3 a"(2026-10-17 14:55 KST), 같은 세션에서 반영(5절)
as_of: 2026-10-17 (가격 기준 2026-10-16 종가, 저장소 10/17 14~15시 조회)
consumers: 관제판 wcg-1017 결정 · 관심 카드 7장 kill 행(1 b) · CLAUDE.md Decision journal 줄(2 a) · 주간 재채점 예약 지시문 v3.3 · watchlist-rotation-design-2026-10-03.md 3-3 ⑦·3-4 4단계·3-7
default: NO_CHANGE (세 건 모두 — 답이 없으면 지금 카드·규칙·지시문·문서 그대로)
order_authority: false
quantity_authority: none
---

# 관심 카드 빈틈 3건 검토 (2026-10-17)

요청: 사용자 2026-10-17 14:21 — ① kill ④ 자동 판정을 만들어야 하나 ② "카드 수락하면 기록" 규칙과 기록 도구 불일치 해결 ③ "카드 재사용 작업 시작".

## 결론

| # | 질문 | 권장 | 바뀌는 것 | 사용자 손길 |
|---|---|---|---|---|
| 1 | kill ④를 자동 판정해야 하나 | **만들지 않는다. 대신 관심 카드 7장의 kill ④를 지운다(1 b).** 적용된 적 없는 문구라 동작은 그대로다 | 카드 7장의 ④ 문구와 '①~④ 확정' 표현(아래 범위) + 등록부 절 해시 7개 + 설계 3-7 1줄 | 이번 결정 답 1회뿐(별도 재수락 없음) |
| 2 | 기록 규칙·도구 불일치 | **규칙 문구를 도구 범위에 맞춘다(2 a)**: 결정 기록부(S7b)는 보유 포지션 카드 결정만. 관심 카드 수락의 기록처와 관심 종목 판단의 채점처를 문구에 적는다 | CLAUDE.md 1줄 | 커밋 1회(일회성, docs/claude 밖) |
| 3 | 카드 재사용 | **주간 재채점 지시문 v3.2 → v3.3(3 a)**: 편입·교체 종목에 수락된 카드가 있고 조건(절 해시 일치·수락 뒤 명단 제외 이력 없음·유효일 안)을 맞추면 새 초안 대신 그 카드를 쓴다 | 예약 지시문 교체 + 설계 문서 2줄 + 명단 파일 낡은 칸 1개 삭제 | 편입 1건마다 재수락 1회 줄어듦 |

## 1. kill ④ 자동 판정

- 지금 상태
  - 관심 카드 7장(통합 카드의 MU·BE·DELL·AMD 절, PWR·LITE·PLTR 카드)의 kill 행에 모두 ④ "종가가 EMA50 아래로 마감하고 2세션 안에 회복 못 함"이 있다.
  - 이것을 읽는 자동 작업은 없다(자동 엔진·통합 점검·주간 지시문 검색 0건). 주간 강제 제외는 kill ①~③만 본다(교체 설계 96행).
  - 수락할 때는 모두 미충족이었다(예: LITE 카드 26행 "EMA50 $902.85(+20.2%)" = 종가가 EMA50 위).
- 이번 하락에서 처음 닿았다(자동 엔진 판정 파일 10/14~10/17의 종가÷EMA50)
  - MU: 10/13(−3.8%)부터 4세션 연속 아래 → 늦어도 10/15에 충족.
  - BE·DELL·LITE: 10/14·15·16 아래 → 10/16에 충족.
  - PWR: 10/14 +0.4%, 10/15·16 아래 → 10/19 종가도 아래면 충족.
  - 그런데 4종목 모두 관심 명단에 그대로 있다. **카드에는 철회 기준인데 실제로는 아무도 적용하지 않는 문구**다. 이 카드를 읽는 사람(Cowork 포함)은 문구대로라면 지금 4종목을 빼야 한다. 사람이 해야 하는 숨은 단계이고, 하지 않으면 카드와 실제가 어긋난다(CLAUDE.md Goal: 사람 단계를 빼는 쪽으로 고친다).
- 검토 순서
  - NO_CHANGE: 모순이 남는다. 문구대로 적용하면 아래 ADD와 같은 결과다.
  - REMOVE(**권장 1 b**): 카드 7장에서 ④를 지운다. 적용된 적이 없으니 동작은 바뀌지 않는다. 형식상으로는 철회 기준 하나를 없애는 완화이지만, 매수를 막아 온 실제 장치는 그대로다.
    - 쇼크가 열려 있으면 자동 엔진의 R-REC1 RG2가 종목 종가 ≥ 자기 EMA50과 기준 ETF ≥ EMA50을 모두 요구한다(auto_core_rules.py:870-881; 10/17 실행(10/16 종가)에서 관심 5종목 모두 RG1·RG2·RG3 미충족으로 막힘 — LATEST_DECISION.json buy_requirements).
    - EMA20 아래 2회(W7류) 약화 트리거는 그대로 남는다.
    - 쇼크 밖에서는 EMA50 아래 매수를 막는 자동 장치가 1 b 전에도 후에도 없다. 사라지는 것은 PLTR 카드 46행의 '카드 갱신 때 사람이 본다' 단계뿐이다.
    - 프로젝트 지침 6 "가격선만으로 장기 thesis를 폐기하지 않는다"와 카드 문구 "관심 철회일 뿐 thesis 폐기가 아님"(PLTR 46행)도 1 b와 같은 쪽이다.
  - 1 b 수정 범위
    - kill 행의 ④: 통합 카드의 MU·BE·DELL·AMD 절, PWR:40, LITE:40, PLTR:46.
    - '①~④ 확정·유지' 표현: PWR:10·15, LITE:15, PLTR:4·20·77.
    - PLTR 4절 ④ 검토 문단(71~75행).
    - ⑤ 번호는 그대로 둔다(PWR·PLTR — 번호만 비고, 뜻은 바뀌지 않음).
    - 모든 수정이 끝난 뒤 등록부 7개 항목의 section_sha256을 다시 계산한다. accepted.date·text는 바꾸지 않는다(바꾸면 3의 '수락 뒤 제외 이력' 조건이 AMD에서 풀린다). 변경 기록은 updated_by와 이 문서에 남긴다.
    - 등록부는 같은 세션에서 _pending 커밋 목록에 넣는다. 커밋되지 않으면 모든 관심 종목 주문표가 나오지 않는다(auto_core_inputs.py:182-184).
  - REUSE: 자동 엔진의 ema_below_unrecovered 종류로 '약화'만 걸면 사실상 효과가 없다. 매수 근거는 "+"만 세고(auto_core_tickets.py:110-115), EMA20 트리거와 같은 묶음이다(auto_core_rules.py:88-92).
  - REPLACE: ④를 "EMA50 아래면 신규 매수 보류"라는 새 관문으로 바꾼다. 새 규칙 후보이고, 쇼크 때는 R-REC1과 겹친다. 사용자 기본 방향 "회복 초기 매수"(buylow: a, 2026-10-17)와도 반대 쪽이다.
  - ADD: 주간 강제 제외에 ④를 넣는다. 지시문은 제외를 편입보다 먼저 처리하고 실행당 1건이라(v3.3 198·201·202행), ④ 충족 종목이 남아 있는 동안은 매주 제외만 한다(10/24 MU → BE → DELL → LITE, PWR은 10/19 종가에 달림). 명단이 1~0칸까지 줄어든 뒤에야 채워지고, 철회로 빠진 종목은 excluded로 가서 후보 자격도 잃는다(260행). 하락 한가운데에서 관심 명단을 비우는 쪽이라 방향과 반대다.
- 같은 날 앞선 판단과의 관계: PLTR 카드 4절(오늘 14시대)은 "④ 철회 유지(NO_CHANGE)"였다. 그때는 ④가 기존 관심 종목에 실제로 적용되는지를 보지 않았다(1차 누락 — 지금 4종목이 충족 상태로 남아 있음). 1 b가 정해지면 PLTR 4절도 같이 고친다. 정정 기록은 review-stability 2절에 남긴다.
- 바뀔 조건
  - 관심 종목이 kill ①~③ 없이 크게 망가진 사례(④만 먼저 알렸을 사례)가 생길 때.
  - R-REC1이 규칙 후보에서 빠지거나 바뀔 때(CLAUDE.md R-REC1 줄: rule candidate).
  - 사용자가 "기술 이탈 때 관심에서 빼라"를 원할 때.

## 2. 기록 규칙과 도구 불일치

- 규칙(CLAUDE.md 92행): "when a card or order decision is accepted in Cowork, record the S7b entry in the same session".
- 도구(portfolio_review_journal.py)
  - propose-card는 보유 카드 형식만 받는다(holding-card.schema.json positions[action ∈ ADD·HOLD·TRIM·EXIT·WITHHELD]).
  - propose-user-decision은 이미 있는 card_decision의 decision_id가 필요하다.
  - 미보유 관심 종목의 WATCH 판단도, 미보유 종목의 새 매수 결정도 넣을 칸이 없다.
- 실제 기록부(decision_journal.json): 6건 = s5_activation 1 + 카드 기록 5(MVLL·NBIS·SOXL). 관심 카드 MU·BE·DELL·AMD(10/2)·PWR·LITE(10/3)·PLTR(10/17) 수락은 기록된 적이 없다.
- 이미 있는 기록·채점
  - 관심 카드 수락: card-evidence-registry.json accepted(날짜·원문)·watchlist-registry.json cardStatus — git 커밋으로 시각이 남는다.
  - 관심 종목 새 매수: 자동 엔진이 기록 모드에서 order_ticket·ticket_outcome으로 기록하고, 실제로 나온 주문표는 score_decision_journal.py가 채점한다(같은 파일 17~20행; 비교 모드 주문표 포함). 막힌 매수·WATCH 판단 자체는 채점하지 않는다.
  - 관심·후보 점수: R2.1 점수 → 이후 수익률 사후 채점(docs/claude/watchlist_forward_score.py — 저장소 docs/claude 목록에서 파일 확인; watchlist-forward-score-preregistration-2026-10-17.md 20~26행: 관심 weeklyRun.memberData와 후보 candidates). 편입·교체 선택 자체는 설계 3-8 몫이다.
- 검토 순서
  - NO_CHANGE: 지킬 수 없는 문구가 남아 매번 이번처럼 해석해야 한다.
  - REMOVE/SIMPLIFY(**권장 2 a**): 문구를 도구 범위에 맞춘다.
  - REUSE: 위 기록·채점 3곳을 문구에 적는다.
  - ADD: 기록 도구에 관심 카드 종류를 넣고 채점기를 넓힌다(코드 변경). 포지션이 없는 판단이라 "현금 대비 점수"의 뜻이 약하고, 점수→수익률 채점과 겹친다.
- 바꿀 문구(CLAUDE.md 92행, 영어 1줄)

  "- Decision journal: when a holding-card position decision (ADD/HOLD/TRIM/EXIT, or the user's own action on it) is accepted in Cowork, record the S7b entry in the same session as described in Hard safety (no separate confirmation code). A watch-card (non-held) acceptance is recorded in docs/claude/card-evidence-registry.json (accepted) and watchlist-registry.json (cardStatus), not in the journal; new buys of non-held symbols are journaled by the auto-core (order_ticket/ticket_outcome, recording mode) and issued tickets are scored by score_decision_journal.py; watchlist R2.1 scores are post-scored against later returns by docs/claude/watchlist_forward_score.py."

- 경로
  - CLAUDE.md는 보호 경로라 수동 경로(작업 트리 Builder + Judge, CLAUDE.md:108)에 들어 있다. 다만 그 수동 경로는 코드 변경용이고, 문서 문구만 바꿀 때는 Judge가 필요 없다(CLAUDE.md:55 "Docs-only changes need no Judge").
  - 선례: fx1009-closing-2026-10-16.md 118행("보호 경로라 이 세션에서 사용자 승인 뒤 처리")·119행(결정 세션에서 CLAUDE.md 1줄 삭제). 해당 커밋은 0c58852(git log 2026-10-17 조회).
  - 사용자 결정 뒤 Cowork가 같은 세션에서 고치고 줄바꿈 CRLF를 유지한다.
  - docs/claude 밖이라 자동 커밋이 되지 않으므로 사용자가 커밋 명령 1회를 실행한다.
- 남는 빈틈(알림만): 관심 종목 WATCH 판단과 막힌 매수는 직접 채점하지 않는다. 바뀔 조건: 이것을 채점하자는 요구가 생기면 ADD 안을 다시 본다.

## 3. 카드 재사용 (주간 재채점 지시문 v3.3)

- 문제
  - 자동 편입·교체 때 지시문이 항상 새 카드 초안 docs/claude/watch-card-<CODE>-<TODAY>.md를 쓰고 cardStatus를 "자동 작성 초안(미수락)"으로 둔다(v3.2 204~206행).
  - 검증 251행은 "수락" 표시를 오히려 위반으로 본다.
  - 그래서 이미 수락된 카드가 있어도 다시 수락해야 한다.
- 언제 생기나: 이번 주 기준선은 6점이다(최약 MU 4점, 10/17 주간 실행). PLTR 9점이 10/24·10/31 두 번 연속 넘으면 10/31 교체 평가 대상이 된다. 실제 교체 여부는 유지 보호·28일 규칙·다음 약한 종목 조건에 달려 있다(시뮬레이션 안 함).
- 바꾸는 것(diff: scheduled-prompts/pending-cardreuse/diff-v3.2-v3.3.txt, 89줄)
  1. 1) 사전 확인(컴퓨터, 읽기만): card-evidence-registry.json에서 다음을 **모두** 맞춘 후보를 REUSE로 출력한다.
     - role watch, 수락 원문 있음
     - 절 해시가 맞음(자동 엔진 auto_core_inputs.section_text와 같은 계산)
     - 수락일 뒤로 명단에서 빠진 이력 없음(history의 out)
     - 카드 valid_until에 날짜가 있고 오늘 이후
     - 묶음 카드면 '#절번호'를 붙인다. 다만 지금 묶음 문서는 valid_until이 "확인 필요"라 이 분기는 쓰이지 않는다.
     - valid_until은 줄 맨 앞 날짜만 읽는다(`valid_until: YYYY-MM-DD`). 날짜가 없거나 읽다가 오류가 나면 재사용하지 않고 v3.2 초안 경로로 간다.
     - 지금 실행 결과: 10/24·10/31 = PLTR(유효 11/02까지), 11/03 = 없음. AMD는 10/2 수락 뒤 10/3 사용자 교체로 빠졌고 유효일이 "확인 필요"라 제외된다.
  2. 3) ctx에 reuse를 넣는다.
  3. 6) 편입·교체 종목이 REUSE에 있으면 다음과 같이 한다.
     - 새 카드 파일을 쓰지 않는다(CP 빈 값).
     - members 칸: card = 수락 카드 경로, triggerSet = 등록부 값, cardStatus = "수락(<수락일>, 수락 카드 재사용 — <TODAY> 자동 편입)".
     - 새 카드용 철회 기준 확인 단계(규칙 ⑥)를 건너뛴다.
     - 검증은 재사용이면 "카드 = REUSE 경로·수락 표시·since = TODAY"를 본다.
  4. 문구: 자동 모드 설명(4행 매수 요건 ③ 문장), 규칙 ⑥, 점검 상태 ㉣, 출력 (a)·(f)에 재사용 경우를 넣는다.
- 권한·한도
  - 바뀌지 않는다. 편입 규칙(점수·2주·28일·보호·분야 한도)도 그대로다.
  - 재사용된 카드가 관심 칸에 들어가면 자동 엔진이 그 카드로 매수 요건 ③을 평가한다(v3.2라면 '미수락'으로 막혀 사용자 수락을 기다렸을 단계). 이것은 사용자가 이미 수락한 카드를 그대로 쓰는 것이고, 수락 뒤 명단 제외·유효일 경과면 쓰지 않는다.
  - PLTR은 상품 승인 관문 두 곳에서 매수가 막힌다: auto_core_tickets.py:61·255 APPROVED_BUY, 920-921 정책 card_stock_core(alert_policy.json:746에 PLTR 없음).
- 검토 순서
  - NO_CHANGE: 편입 때마다 재수락 1회.
  - REMOVE/SIMPLIFY: 해당 없음.
  - REUSE(**권장 3 a**): 등록부의 수락 카드를 조건부로 재사용.
  - ADD: 수락 카드 자동 갱신 — 범위 밖.
- 검증(이번 세션)
  - 바뀐 지시문의 python 3개가 컴파일된다.
  - 1) 블록을 실제로 실행했다(날짜 3개).
  - 6)의 바뀐 줄만 떼어 PLTR(재사용)·ETN(초안) 두 경우를 돌렸다: members 칸이 맞고 검증 V=[]가 나왔다.
  - 독립 재검토에서 6) 전체를 합성 일봉으로 한 번 돌렸다: written true, card [], reuseCard 경로가 나왔다.
  - 실제 첫 실행은 10/24(토) 10:20이다.
- 적용 경로: 사용자 승인 → Cowork가 다음을 한다.
  1. 실행 중인 예약 지시문이 저장소 사본(1894bf62…)과 같은지 확인한다.
  2. 예약 작업 지시문을 교체한다(update_trigger).
  3. scheduled-prompts/watchlist-weekly-rescore.txt를 교체하고 README 해시·변경 기록을 갱신한다.
  4. 설계 문서 3-3 ⑦(102행)·3-4 4단계(116행)에 재사용 예외 1줄씩을 넣는다.
  5. 명단 파일 최상위 weakestMember 칸(MU 8)을 삭제한다. 옛 v1 지시문만 쓰던 칸이라 v3.x는 고치지 못하고(허용 밖 최상위 칸 검증), 오늘처럼 잘못 읽게 만든다. 읽는 곳은 0건이다(저장소 검색).
  6. 문서 커밋 목록에 넣는다.
  - 되돌리기: README의 v3.2 원문(git 이력).
- 바뀔 조건: 재사용된 카드가 실제로는 낡아 문제를 만든 사례가 나오면 조건을 좁힌다(예: 수락 뒤 실적 발표가 있었으면 제외).

## 4. 사용자 결정

- 한 줄 답: `결정 wcg-1017: 1 b, 2 a, 3 a`
  - 1 a = NO_CHANGE(④ 그대로 — 적용 안 되는 문구로 남음) / **1 b = 카드 7장에서 ④ 삭제(권장)**
  - **2 a = CLAUDE.md 1줄 교체(권장, 사용자 커밋 1회)** / 2 b = NO_CHANGE
  - **3 a = 지시문 v3.3 적용 + 설계 2줄 + weakestMember 삭제(권장)** / 3 b = NO_CHANGE
- 기본(무응답): 1·2·3 모두 NO_CHANGE.
- 기한: 10/24(토) 10:20 주간 실행 전. 3이 그 실행부터 적용되려면 그 전에 답이 필요하다.

## 5. 결정 기록과 반영 (2026-10-17)

- 사용자 원문: "결정 wcg-1017: 1 b, 2 a, 3 a" (14:55 KST).
- 1 b 반영
  - 카드 7장의 ④를 삭제 문구로 바꿨다: 통합 카드 MU·BE·DELL·AMD 절, PWR·LITE·PLTR 카드. '①~④ 확정' 표현에는 "(④는 2026-10-17 결정 wcg-1017로 삭제)"를 붙였다. PLTR 4절에는 변경 문단을 넣었다.
  - 등록부 section_sha256 7개를 다시 계산했다. accepted 날짜·원문은 유지했다. 로더 검사: 10종목 모두 hash_ok. AMD·PLTR은 관심 명단 밖이라 CARD_NOT_ACCEPTED_IN_WATCHLIST(정상).
  - 설계 3-7에 1줄을 넣었다.
- 2 a 반영: CLAUDE.md 92행을 교체했다(CRLF 유지, diff 1줄). docs/claude 밖이라 사용자 커밋이 필요하다.
- 3 a 반영
  - 예약 작업 '관심 명단 주간 재채점 (자동 모드)'(trig_01MuMHqXHrRAeNVZt2ZjzRxu)의 지시문을 v3.3으로 교체했다(2026-10-17 06:21:22Z).
  - 교체 결과의 prompt sha256 a809c649…가 저장소 사본과 같다. 컴퓨터 요구·자동 승인·폴더 2개는 유지됐다.
  - scheduled-prompts/watchlist-weekly-rescore.txt를 교체했고, README 해시와 변경 기록을 갱신했다.
  - 설계 3-3 ⑦·3-4 4단계에 1줄씩 넣었다.
  - 명단 파일 최상위 weakestMember를 삭제했다.
  - 1) 블록 실행 결과 REUSE = PLTR(유효 11/02)이다.
- 검증
  - validate_schema_contracts PASS.
  - test_auto_core_decide 69건 OK.
  - 첫 실제 실행은 10/24(토) 10:20이다.

