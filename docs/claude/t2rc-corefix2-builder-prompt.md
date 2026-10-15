---
id: t2rc-corefix2-builder-prompt
title: (재실행 t2rc-corefix -> t2rc-corefix2) 코어 5건 수정 — t2-rc 독립 Judge(2026-10-15) 11절 "코어" 항목 (R-REC1 SOXX 기준·RG3 창·새 근거 unk·재배치 후보·G3 ⅓)
date: 2026-10-15
class: 권한 경로(auto_core*.py, tests/test_auto_core*.py) — dev-run class authority(경로 때문). 의미: 일반 변경(규칙 문구에 코드를 맞춤). 효과 방향(2026-10-15 재검토): 2·3 = 매수를 더 막음, 1 = 섞임(SOXX 충격이면 BE·PWR도 막고, GRID만의 충격이면 더는 막지 않음), 4 = 매도 수량(후보가 줄면 같거나 큼), 5 = 매수에만 적용(사용자 결정 5 = b — 매도 단계는 지금 그대로). 관문 기준값·상수·규칙 파일 불변
decision: 사용자 "결정 t2rc-corefix: 1~4 진행, 5 = b"(2026-10-15 09:31 KST, Cowork 대화) — 근거 docs/claude/t2rc-judge-report-2026-10-15.md 3절 1·9a·9b, 4절 S3·S5, 추가 D, 11절 코어 1~5
authority: order_authority=false · quantity_authority·execution_quantity 불변 · 키움 호출 없음 · 정책·상태 쓰기 없음
weekly_user_touch: 0 (병합 1번: .\tools\dev-merge.ps1 t2rc-corefix2 -ApproveAuthority — 경로 때문에 붙는 플래그)
---

```dev-run
{"task_id": "t2rc-corefix2", "class": "authority", "builder_model": "opus", "builder_effort": "high", "max_turns": 120, "builder_timeout_min": 60, "allowed_paths": ["manage-us-stock-strategy/scripts/auto_core_rules.py", "manage-us-stock-strategy/scripts/auto_core_decide.py", "manage-us-stock-strategy/scripts/auto_core_tickets.py", "manage-us-stock-strategy/tests/test_auto_core_rules.py", "manage-us-stock-strategy/tests/test_auto_core_decide.py", "manage-us-stock-strategy/tests/test_auto_core_tickets.py", "manage-us-stock-strategy/tests/test_auto_core_compare_fix3.py", "manage-us-stock-strategy/tests/test_auto_core_rrec_bootstrap.py", "manage-us-stock-strategy/tests/test_auto_core_t2rc_corefix.py", "docs/claude/t2rc-corefix2-report.md", "manage-us-stock-strategy/tests/test_auto_core_risk1r.py"], "target_tests": ["test_auto_core*.py"], "commit_message": "fix(auto-core): R-REC1 events on SOXX (GRID only RG2), RG3 lows from event, unk previous not new, redeploy filter, buy G3 card hit (t2-rc Judge)"}
```

## 재실행 사유 (Cowork 2026-10-15 11:4x KST)

1회차 t2rc-corefix(workspace/outputs/dev-runs/t2rc-corefix, 보고 .claude/worktrees/t2rc-corefix/docs/claude/t2rc-corefix-report.md)는 BLOCKED다. 다섯 항목 구현과 새 테스트 14개는 통과했다. 막힌 이유는 골든 `test_auto_core_risk1r` GOLDEN["sell"] 해시가 바뀐 것 하나다(`a3a2372037ca…` → `07c781346ca9dfa243a83e826f83759e0e57751b7f1b02eb3fb52b9e716cdfb0`).
- 원인은 항목 4의 "⑤ ok" 거르기다. 고정 자료는 SOXX 470(EV1)이라 R-REC1이 열려 있고, 그래서 MU가 후보에서 빠진다. 그러면 SOXL 매도 후회표에 현금 열만 남는다. 1회차 Builder가 이분으로 확인했다.
- 이것은 사용자 결정(1~4 진행)이 뜻하는 결과다. Cowork가 원인을 확인했다. 그래서 이번 회차에는 다음을 허용한다.
  - **허용(한 곳만):** test_auto_core_risk1r.py의 GOLDEN["sell"] 값을 `07c781346ca9dfa243a83e826f83759e0e57751b7f1b02eb3fb52b9e716cdfb0`로 바꾼다. 단, 다섯 항목을 넣은 뒤 다시 잰 값이 이 값과 **정확히 같을 때만**이다. 다르면 고치지 말고 BLOCKED로 둔다.
  - GOLDEN의 나머지 7개 키(default, g2b, cash5, research_block, pwr, decide_compare, decide_apply)는 바뀌면 안 된다. 바뀌면 BLOCKED다.
  - 보고서에 그 고정 자료의 SOXL 매도 주문표를 변경 전후로 적는다: 수량·r·후회표 열 이름·행별 최대 후회. 수량이 바뀌었으면 그 이유도 한 줄 적는다.
- 1회차에서 배운 것:
  - `auto_core_rules.py` docstring·주석은 ASCII만 쓴다(test_language_contract·test_v2_5_beginner_renderer).
  - worktree에는 workspace 산출물이 없다. 그래서 아래 "실자료 확인"은 하지 않아도 된다. 보고서에 "Cowork가 병합 뒤 확인"이라고만 적는다.
- 1회차 worktree·브랜치(worktree-t2rc-corefix)는 건드리지 않는다. 1회차 코드를 참고로 읽는 것은 된다.

## 배경

T2 "켜" 조건 B+(사전 등록 docs/claude/t2-rc-preregistration-2026-10-14.md)는 독립 계산기 docs/claude/t2rc-oracle.py가 코어와 같은 값을 내야 채워진다. 2026-10-15 독립 Judge(docs/claude/t2rc-judge-report-2026-10-15.md)가 두 구현을 원문과 맞대 보고, 다음 5곳은 **코어가 원문과 다르다**고 판정했다. 계산기 쪽 차이는 Cowork가 따로 고친다(이 작업 범위 밖). D0 전에 고치므로 사전 등록 C1 "코어 결함 → C1 0부터"에는 해당하지 않는다.

## 바꿀 것 (다섯 가지만)

1. **R-REC1 벤치마크**(Judge 3절 9a, auto_core_decide.py 1040행 근처 → auto_core_rules.py rrec1 741~866행 근처)
   - 원문: 규칙 파일 102행 "SOXX 일봉으로 σ60을 쓴다(업종이 A1 전력인 종목의 RG2 기준 ETF는 GRID, 그 밖은 SOXX)", recovery-gate-R-REC1-2026-10-09.md 30행.
   - 바꿀 내용: 모든 후보에서 다음은 **SOXX**로 계산한다.
     - 사건: EV1·EV2·EV3ⓑ, EV3ⓑ 기록 공백 검사 포함
     - C0·L0·RG3·RG4·DS1
   - **GRID는 RG2 벤치마크 다리에만** 쓴다(A1 전력 종목: GRID 종가 ≥ GRID EMA50, 그리고 후보 종가 ≥ 후보 EMA50).
   - EV5(종목 자체)·EV4(계좌)는 그대로다.
   - 2026-10-11 Judge2 메모 2("공백 검사는 각 후보의 RG2 벤치마크")는 이 판정으로 바뀐다. 보고서에 한 줄 적는다.
2. **RG3 신저가 창**(Judge 3절 9b, auto_core_rules.py 856~858행 근처)
   - 원문: 규칙 파일 102행 "이벤트 뒤 일봉 저가 < L0인 세션 없음", r-rec1-gate-preregistration 37행 "t_e 다음 날부터 t까지 모든 저가 ≥ L0".
   - 바꿀 내용: 저가 조건은 **이벤트 다음 세션부터** 판정 세션까지 본다. DS1은 "연속 2세션 종가 > C0" 셈만 처음으로 되돌린다(마지막 DS1 세션 뒤 두 세션이어야 함). 저가 창은 되돌리지 않는다.
   - 저가 보정(v3.12.1 정규장 저가 3% 규칙)은 지금 방식 그대로다.
3. **새 근거와 전 세션 unk**(Judge 3절 1, auto_core_rules.py 693행 근처)
   - 원문: builder D5 "오늘 새로 hit가 된"(redesign-t2-builder-prompt-2026-10-10.md 176행). 전 세션이 unk이면 새로 됐는지 확인할 수 없고, 자료 부족은 fail closed다.
   - 바꿀 내용: 그룹의 전 세션 state가 unk(또는 그룹 없음)이면 그 그룹은 **새 근거가 아니다**. 전 세션 none·pending이고 오늘 hit일 때만 새 근거다.
   - 매수 회로의 "새 근거만으로 충족"에만 영향이 있다. basis_met(카드 표 N + 새 M 전체)과 매도 회로는 그대로다.
4. **재배치 후보 거르기**(Judge 4절 S3·S5, auto_core_decide.py 1075~1080행, auto_core_tickets.py 835행 근처)
   - 후보는 다음을 모두 갖춘 종목이다. 그날 매도하는 종목과, 그날 매도 회로가 열린 종목은 뺀다.
     - 그날 매수 요건 ①·③·④·⑤ 모두 ok
     - 상품 승인: alert_policy portfolio_exposure_policy의 card_stock_core ∪ allowed_index_etfs(그래서 매도 전용 MVLL은 빠진다)
     - 등록부 자격(지금 조건)
     - 스트레스 수익률 있음(지금 조건)
   - 순위는 지금 그대로다(강 근거 수 → 약 근거 종류 수 → 종목 코드).
   - 판 종목이 1위이면 "후보 없음"으로 두지 말고 **다음 순위**를 쓴다(위에서 이미 빼므로 자연히 그렇게 된다).
   - ②(노출·현금)·S7 멈춤·판 뒤 E는 거르지 않는다. D+1 관문이 새 상태로 다시 보고, 현금 열이 늘 같이 있기 때문이다.
   - 후회표 모양(4열 한 표, 매도 대금 전부, 센트 반올림)은 바꾸지 않는다. Judge가 코어 읽기를 제안으로 승인 묶음에 넣었다.
5. **G3 ⅓ 상한의 card_defined — 매수 근거에만**(Judge 추가 D, auto_core_rules.py 601·695행 근처, 우선순위 낮음)
   - 원문: 설계 G3 "카드 정의 트리거·공식 사실 없이 C끼리만"(order-instruction-design-2026-10-06.md 88행), builder F4 189행.
   - 사용자 결정 5 = b(2026-10-15): 위험 감축을 늦추지 않는다(builder G2b "매도 금액에는 상한을 두지 않는다(위험 감축을 늦추지 않게)", 프로젝트 원칙 "매도는 막지 않음").
   - 바꿀 내용:
     - **매수(+ 방향) 근거**: 그룹이 card_defined인 것은 그 그룹의 카드 트리거가 **오늘 hit일 때**다. 정의만 있는 것으로는 안 된다.
     - **매도(− 방향) 근거**: 지금 그대로다. 그 그룹에 카드 트리거 정의가 있으면 card_defined다.
   - 지금 차이가 나는 곳은 V3·S5가 든 trend_break(매도 쪽)뿐이다. 그래서 이 항목은 현재 자료로는 결과를 바꾸지 않는다. 앞으로 + 방향 카드 트리거가 공통 C와 같은 묶음에 들어올 때 효과가 생긴다.

## 테스트

새 파일 `manage-us-stock-strategy/tests/test_auto_core_t2rc_corefix.py`(기존 helpers·series 도우미 방식을 따른다). 항목마다 최소 2개를 쓴다.
- **1:**
  - A1 전력 후보에서 GRID만 −2σ로 빠진 날 → 사건 없음.
  - SOXX −2σ 날 → 사건 있음, C0·L0 = SOXX 값.
  - RG2는 GRID와 후보 EMA50으로 판정.
- **2:**
  - DS1 뒤 다시 회복했지만, DS1 앞(이벤트 뒤)에 저가 < L0 세션이 있으면 → RG3 no.
  - 저가가 모두 L0 이상이고, DS1 뒤 2세션 종가 > C0이면 → RG3 ok.
- **3:**
  - 전 세션 unk → 오늘 hit여도 new_kinds에 없음, 매수 회로 닫힘(그 근거만 있을 때).
  - 전 세션 none → 새 근거.
- **4:**
  - 매도 전용 종목·⑤ no·①(금지 구간) 종목은 후보에서 빠짐.
  - 판 종목이 1위면 2위가 후보.
  - 그날 매도 회로 종목은 빠짐.
- **5:**
  - 매수: 카드 트리거 정의는 있으나 오늘 hit 아님 + 공통 C 2종 → r_max ⅓. 카드 트리거 hit → ½.
  - 매도: 같은 모양(정의 있음·hit 아님 + 공통 C 2종) → r_max ½(지금과 같음).

고칠 수 있는 기존 테스트:
- 위 의미 때문에 고정 자료가 맞지 않게 된 테스트는 **고정 자료 값만** 고친다.
- 검사 문장은 그 뜻이 이 다섯 가지와 정면으로 충돌할 때만 고친다. 고친 곳마다 보고서에 파일:행·전후 값·이유를 적는다.
- 골든·불변 테스트(test_auto_core_risk1r GOLDEN, test_auto_core_compare_fix T5 불변)가 바뀌면 고치지 않는다. 예외는 위 "재실행 사유"의 GOLDEN["sell"] 한 키뿐이다(정해 둔 값과 정확히 같을 때만). 그 밖에 바뀌면 원인을 보고서에 적고 그 회차는 BLOCKED로 둔다.

## 지켜야 할 것

- allowed_paths 밖은 건드리지 않는다. 규칙 파일·카드·등록부·정책·상태·스키마·CONSTANTS·관문 기준값 불변.
- 새로 여는 매수·매도 경로를 만들지 않는다. 효과 방향은 머리말 class 줄과 같다(1은 섞임, 5는 매수만).
- 키움 호출·주문 경로·권한 표지 없음. auto_core.py를 실행하는 명령은 쓰지 않는다(테스트는 `-p "test_auto_core*"`).
- CRLF 파일의 줄 끝을 바꾸지 않는다.

## 보고 `docs/claude/t2rc-corefix2-report.md`

- 바꾼 줄(파일:행)과 항목별 새 규칙 한 문단
- 새 테스트 목록, 고친 기존 테스트(값·이유)
- 대상·전체 테스트 결과(Ran 수, 새 실패 0)
- 실자료 확인: 이 회차에서는 하지 않는다(worktree에 자료 없음). Cowork가 병합 뒤 2026-10-15 입력으로 BE·PWR R-REC1과 ⑤ 칸을 변경 전후로 확인한다.
- 골든 "sell" 재측정값과 SOXL 매도 주문표 전후(위 재실행 사유)
- 남은 위험

## Judge 확인 항목

1. 범위: allowed_paths 안이고, 바뀐 의미는 위 다섯 가지뿐이다.
2. 1: 사건·C0·L0·RG3·RG4·DS1·공백 검사가 SOXX이고, GRID는 RG2에만 쓴다(규칙 파일 102행).
3. 2: 저가 창 = 이벤트 다음 세션부터. DS1은 2세션 셈만 되돌린다.
4. 3: 전 세션 unk → 새 근거 아님. basis_met·매도 회로는 불변이다.
5. 4: 후보 거르기와 다음 순위가 맞고, 후회표 모양은 불변이다.
6. 5: 매수 card_defined = 오늘 hit, 매도는 정의만으로(사용자 결정 5 = b).
7. 골든은 GOLDEN["sell"] 한 키만, 정해 둔 값(07c78134…)으로 바뀌었고 나머지 키·T5 불변 테스트는 불변이다. 권한 표지·주문 경로·정책/상태 쓰기·키움 호출 없음. 대상·전체 테스트 새 실패 0.
