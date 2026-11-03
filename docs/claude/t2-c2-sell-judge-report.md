VERDICT: PASS-WITH-CONDITIONS

# 독립 Judge 판정: t2-c2-sell (T2 "켜" 조건 C2를 매도 주문표로도 인정, K3 · H2)

- 판정 시각: 2026-11-03 KST(약 20시대). 판정 대상: docs/claude/t2-c2-sell-proposal-2026-11-03.md(미커밋 새 파일, 저장소 E:\사업\##금동한\코덱스저장소, 브랜치 codex/master-recovery-expansion HEAD 8f2fdd5).
- 결론: 제안의 핵심 주장(코드 변경 0, 계산기 ticket_check·c2_item_match가 방향과 무관, C3·M3가 켠 뒤 첫 매수 주문표를 입력 전에 막음)은 원문 코드로 맞다. 다만 ① 매도 주문표 일치는 매수 쪽 계산 경로 4곳을 시험하지 못하고, ② 매도 수량의 목표 비중이 코어와 같이 쓰는 S7 값이라 독립성이 매수보다 얕고, ③ c2_item_match가 누락(leak)·C1을 보지 않으며, ④ 승인 기록이 btn-approval 4요건 중 "카드가 가리키는 제안 id"를 채우지 못하고 제약 완화(H2)는 sc-1022 S4상 직접 입력 대상일 수 있다. 아래 조건 1~8(모두 더 엄격하게만)을 붙여 PASS.
- 결론을 바꿀 조건: 사장이 조건 7의 직접 입력을 주지 않거나, 대시보드가 확인 대기 주문표를 입력 가능한 주문으로 보여 주는 것이 확인되면(조건 6) FAIL로 본다.
- 파일 위치 참고: 이 세션의 쓰기 보호(hook)가 본 저장소 쓰기를 막아, 같은 상대 경로를 이 세션 worktree(.claude\worktrees\nice-maxwell-d462cc\docs\claude\)에 썼다. 커밋하지 않았다.
- 보관 메모(회사PC 스레드, 2026-11-03 KST): Judge가 worktree에 쓴 원본을 docs/claude로 옮기며 계좌 금액 2곳(현금 달러 값·10-21 주문표 수량)만 지웠다(docs/claude 금액 금지). 판정 내용은 그대로.

## 항목 판정

### 1. 바뀌는 것이 C2 한 줄뿐인가 — PASS(조건 8)
- 제안 1절은 사전 등록 25행(C2) 한 줄만 바꾸고, 기록은 0절(16행) 방식대로 끝 "변경 기록"에 덧붙인다(제안 18행). 제안 4절(30행)이 R1·C1·C3·C5·차이 분류 의무·CORE_BUG 보류·대조 OK 5회·R3를 그대로 둔다고 적었고, 이는 roadmap-fix-decisions-2026-10-26.md 1-2절 조건 1("R1·C1·C2·C3·C5·R3 … 그대로")·active-decisions.md 105행(t2-gate)과 맞는다.
- 0절(16행)은 "숫자를 느슨하게 바꾸지 않는다, Judge는 더 엄격하게만"이다. 이번 완화는 Judge가 아니라 사장 결정이고, 사장 결정 완화의 선례가 있다(사전 등록 54행 "완화는 사용자 결정이다", 55행 t2-gate REMOVE-v2). 따라서 허용되나, 변경 기록에는 "사장 결정 완화(H2), Judge가 바꾼 것 아님"으로 적어야 한다.
- 주의: C3(29행)는 "C2와 같은 항목으로 일치"를 기준으로 삼는다. C2 문구가 바뀌면 C3의 매수 기준도 따라 흐려질 수 있다 → 조건 8.

### 2. ticket_check가 매도를 매수와 같은 깊이로 다시 계산하는가 — PASS(빠지는 항목 있음, 조건 2·3)
원문 docs/claude/t2rc-oracle.py:
- 방향 공통: LOC 가격 센트 재계산(2022-2024행, loc_mult 1181-1187·loc_price 1190-1194 — 매도는 1−σ, 올림), 수량 정수 비교(2086행), G0·G1 재계산(1938-1949행), G3 = r_max 문자열(1958·2104행), should_exist(2109-2110행), not_recomputed가 있으면 불일치(2115행). 매도 수량은 재배치 다리 경로 2·3(2068-2077행, regret_choice 1204-1235행, redeploy_candidates 1848-1874행)이 맞다.
- c2_item_match(1605행) = `bool(tickets) and all(match)` — 방향과 무관. PASS.
- **매도에서 빠지거나 얕은 항목**:
  a. G2: 매도는 계산 없이 True(1956-1957행, 2103행). 코어도 True를 적으므로 비교는 형식 확인뿐.
  b. 현금: 매도는 무조건 일치(2089행).
  c. 매수 요건 ①~⑤: 매도는 비교하지 않음(2096-2097행, reqs=["ok"]*5).
  d. **목표 비중이 공유값**: 매도 목표 비중은 S7 reduce 권고의 target_weight(2046-2048행) 또는 등록부 EXIT/TRIM(2049-2053행)이다. S7은 코어와 계산기가 같이 쓰는 파생값이고(roadmap-fix-decisions 1-1절 "S7 파생값(코어와 계산기가 같이 씀)은 보지 않는다"), 총자산도 S7 closing_equity_usd다(1728행). 매수는 W*를 정책값으로 다시 계산한다(w_star 1816-1836행). 즉 매도 수량 일치는 "S7 목표 비중이 맞다는 전제 위의 일치"다.
  e. **매도 일치로 시험되지 않는 매수 경로**: W*·첫 진입 절반(2037-2043행), 매수 요건 ①~⑤ 재계산(1876-1920·2091-2095행), G2 매수(g2_buy 1923-1930행), 주문가능 현금 G4 깎기·수수료 여유(2081-2083행). 이 네 곳은 켠 뒤 첫 매수 주문표(C3)에서 처음 시험된다.
- 그 밖: c2_item_match는 ticket_leaks와 C1 일치를 보지 않는다(1605행; verdict는 1617행에서 둘 다 봄) → 조건 1.

### 3. C3·M3가 실제로 동작하는가 — PASS(조건 6)
- 계산기 c3_record(1656-1687행): 방향별로 `entry_allowed = 오늘 그 방향 주문표 없음 or confirmed_before or 오늘 전부 일치`. confirmed_before는 **apply 모드**·같은 날짜·MATCH/MISMATCH·자기 확인 아님·**같은 계산기 sha**인 이전 기록만 센다(1672-1674행). 그래서 비교 모드의 매도 C2 일치는 켠 뒤 매도·매수 어느 쪽 C3도 미리 채우지 못한다(엄격, 맞음). 대조를 못 한 날은 finish()가 오늘 주문표를 불일치로 두고 c3를 만든다(2120-2126행).
- 알림 스크립트(sha 고정: auto-core-alert.txt 17-19행, 실제 core.py sha256 c033e4a8… · read.py a1eb9a75… 일치 확인): read.py(31-33·39-51행)와 core.py(5-8·13-20·23-25행)는 apply 모드에서 allow()가 거짓인 주문표를 "D HOLD"로 빼고, PUSH 줄·NEXT_USER 입력 안내에서 그 종목을 지우고, 대시보드 core에 `ticketHold`·`hold='주문표 확인 대기 — 입력 금지'`를 붙이고, orders 쓰기에서 뺀다. 지시문 ⑬(48행)이 "주문표 확인 대기(<방향>: <종목>) — 입력 금지"를 보낸다. 대조 결과가 없거나 다른 decision(generated_at)을 봤으면 c3=None → 전부 보류(fail closed).
- 매수 첫 주문표가 빠져나갈 길: 코드에서 찾지 못함. 남는 틈 두 가지:
  a. allow()는 주문표별 matched만 보고(core.py 8행, read.py 33행) 같은 방향 누락(leak)은 보지 않는다. 그날 일치한 매수 주문표는 입력 안내가 나가지만, 그날은 today_all_match=false라 다음 날 confirmed_before로 세지 않는다(1681행). 주문표 자체는 검증됐으므로 허용 가능하나 기록해 둔다.
  b. 대시보드 runs 문서의 core.tickets에는 보류 주문표가 `hold` 표시만 붙은 채 남는다(core.py 19-20행). 사장이 "대시보드 주문 지시만 보고" 운영하려는 상황(제안 12행)에서, 대시보드 화면이 hold 표시를 실제로 보여 주는지는 이번 판정에서 **확인 필요**(대시보드 페이지 코드를 읽지 않음) → 조건 6.

### 4. 제안서 2절 사실 — PASS(문구 정정 1건)
- 매수 요건 ②·⑤: decide가 돈 2026-10-27·28·29·30·31·11-03 여섯 날 모두, buy_requirements의 6개 종목(BE·DELL·LITE·MU·PWR·SOXL) 전부 ② no·⑤ no(각 날짜 decision.json buy_requirements c[1]·c[4]). 11-01·11-02는 decide 결과 폴더 없음(화~토 일정).
  - 정정: ②의 막힘 사유는 10-27~10-29에는 "E ≥ 1.85"가 아니라 E 없음(S7 fail closed: exposure_or_equity_or_v_unavailable, 그날 reasons)이었다. 10-30(E 2.0534)·10-31(1.9861)·11-03(2.0047)은 E ≥ 1.85·현금 1주 미만이 맞다.
- 11-03: candidates에 SOXL sell·LITE buy, blocked SOXL sell = G1_S7_FAIL_CLOSED:required_price_missing(2026-11-03 decision.json). 9fad610 "fix(closes): accept -05:00 bar labels …"(2026-11-03 15:21:22 +0900)이 HEAD에 들어 있음 확인.
- target_exposure 1.55·reduce ≥ 1.85: auto_core_tickets.py 58-59행 POLICY_EXPECTED, stock-strategy-system/alert_policy.json 684·687행.
- 제안서에 없던 사실: 2026-10-21 비교 모드에서 매도 주문표 AT-20261021-SOXL-1(수량·가격은 원문 decision.json)이 있었으나 t2rc-check는 NOT_CHECKED(DECIDE_AFTER_0840)라 C2에 세지 않는다(사전 등록 23행). 비교 모드 매도 주문표가 실제로 나온다는 근거이며, 08:40 전 decide 완료가 C2 셈의 실제 병목일 수 있다.

### 5. 승인 기록이 btn-approval 조건을 채우는가 — 부분 PASS(조건 7)
- 채운 것(제안 11행): 카드 message id cmsg_0137MRzn9nuDvvQmVxm6WeX9UF5a9M9JfDKP9jzksjeedx, 선택지 "매도 주문표로도 검증 인정", 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH(다른 결정 문서에서 프로젝트 소유자=사장으로 쓰인 id와 같음, 예 basefail-cleanup-proposal-2026-11-02.md 63행), KST 19:42:26.
- 못 채운 것: CLAUDE.md 75행은 "카드 message id **와 그 카드가 가리키는 제안 id**"를 요구한다. 기록에는 카드가 t2-c2-sell-proposal-2026-11-03을 가리켰다는 내용이 없고, 카드 질문 문구만 있다. 또 기록이 하네스 알림 원문에서 옮긴 것인지(요약이 아닌지) 이 판정에서 검증할 수 없다.
- 승인 장소 범위: btn-approval(active-decisions.md 76행, CLAUDE.md 64-78행)은 권한·한도 Change class 승인에 한한다. sc-1022 S4(active-decisions.md 31행)는 "제약 완화"를 카드로 받지 않는 항목에 따로 적었고 btn-approval이 대체한 범위는 "권한·한도 작업 착수"다. 이번 변경은 제안 스스로 H2(제약 완화)로 표시했고, 같은 종류의 선례 t2-gate REMOVE-v2는 직접 입력으로 승인됐다(roadmap-fix-decisions 34행). 카드만으로 효력 기록까지 가는 것은 해석이 갈린다 → 엄격한 쪽(조건 7).
- decision_mode '켜': 제안 13행이 "이 카드로 승인되지 않는다(R3 그대로)"라고 명시하고, 선택지 문구에도 켜기를 승인하는 말이 없다. PASS.

### 6. 새로 생기는 위험과 조건 — 조건 1~8
- 켠 뒤 첫 매수 결함: 매수 고유 경로(항목 2-e)가 켜기 전에는 한 번도 실운영 대조를 받지 않는다. C3·M3가 입력 전에 막지만, 그 하루 일치 한 번으로 이후 매수는 계속 허용된다(confirmed_before, 1678-1685행). → 조건 3·8.
- 매도만 검증된 상태의 G3 결함: 매도 r_max는 카드에 정의된 종류만 있어도 1/3 상한을 넘는다(1990행, 사용자 결정 t2rc-corefix 5=b). 코어와 계산기가 같은 해석이라 일치가 "규칙이 맞다"를 뜻하지 않는다. 기존 결정이라 바꾸지 않되 조건 2의 기록에 r_max 근거 종류를 남긴다.
- 매도 목표 비중이 S7 공유값(항목 2-d). → 조건 2.

## 조건 (모두 더 엄격하게만)
1. **C2로 세는 세션**: 그 세션 t2rc-check.json이 verdict "MATCH"(INFO_·NOT_CHECKED·MISMATCH 아님), counts_for_c1 true, decision.decision_mode "compare", ticket_leaks 0, reason에 ORACLE_DATA_GAP 없음, 세는 주문표의 not_recomputed 빈 목록일 때만 센다. c2_item_match(1605행) 하나만으로 세지 않는다.
2. **매도 수량 독립 확인**: C2로 세는 매도 주문표마다 기록에 ① 목표 비중 출처(S7 reduce target_weight / 등록부 EXIT·TRIM), ② 그 목표 비중이 정책 target_exposure 1.55(또는 카드 EXIT=0·TRIM 목표)에서 나온 값임을 S7 밖 원자료(보유 수량·정규장 종가·배수)로 손계산한 결과, ③ 재배치 경로(SELL_TO_CASH / SELL_CASH_AND_CANDIDATE)와 후보, ④ r_max와 근거 종류를 남긴다. ②가 맞지 않거나 못 하면 그 주문표는 C2로 세지 않는다.
3. **켠 뒤 첫 매수 주문표**: C3 그대로에 더해, 켠 뒤 첫 매수 주문표의 계산기 일치 기록에는 이전 C2 매수 항목 전부(수량 정수·LOC 센트·요건 ①~⑤ 각각·G0~G3·주문가능 현금 ≥ 금액·W*/첫 진입 목표)가 항목별 match true로 있어야 한다. 그 주문표가 확인되기 전까지 비서실 첫 보고의 주문표 한 줄에 "매수 첫 주문표 미검증"을 붙인다(문구만, 판정 변경 없음).
4. **계산기 sha 변경**: C2를 채운 뒤 계산기(t2rc-oracle.py) sha가 바뀌면, 그 수정이 매도 수량·가격·관문·should_exist 계산을 바꾸는 경우 이전 매도 C2 일치는 세지 않는다(사전 등록 50·51행 "병합 전 C2 일치는 세지 않는다" 선례를 매도에도 적용).
5. **C1·차이 분류 선행**: 매도 C2 일치가 있어도 C1 공식 셈(10-31 MISMATCH 처리 포함, 제안 39행 "확인 필요")이 정해지기 전에는 "켜" 판정 조건 충족으로 표시하지 않는다.
6. **대시보드 보류 표시 확인**: "켜" 판정 전에, 통합점검 대시보드가 core.tickets의 `hold`/meta.ticketHold를 "주문표 확인 대기 — 입력 금지"로 보여 주고 그 주문표를 입력 가능한 주문으로 보이지 않는지 페이지 코드로 확인해 기록한다. 확인 못 하면 "켜" 판정하지 않는다.
7. **승인**: 효력 기록(사전 등록 변경 기록 한 줄·active-decisions.md 행) 전에 ① 카드 하네스 알림 원문에서 카드가 가리킨 제안 id를 기록하고, ② H2 제약 완화이므로 사장 직접 입력 한 줄(예: `결정 t2-c2-sell 적용: 승인`, 이 Judge 보고 뒤 바로 앞 제안 1건·같은 날·1회)을 받는다. 없으면 이전 C2 유지(제안 43행 기본 처분).
8. **C3 문구 고정**: 변경 기록에 "C3의 'C2와 같은 항목'은 매수에서는 이전 C2 매수 항목(25행 원문) 그대로, 매도에서는 새 C2 매도 항목"이라고 함께 적는다. 변경 기록에는 "사장 결정 완화(H2) — Judge가 바꾼 것 아님"도 적는다.

## 읽은 파일
- docs/claude/t2-c2-sell-judge-prompt.md, docs/claude/t2-c2-sell-proposal-2026-11-03.md
- docs/claude/t2-rc-preregistration-2026-10-14.md(전체)
- docs/claude/t2rc-oracle.py 1181-1240, 1560-1736, 1740-2138, 2334-2420행
- docs/claude/scheduled-prompts/auto-core-alert.txt(전체), auto-core-alert/core.py(전체), auto-core-alert/read.py 20-60행 (core.py·read.py sha256 확인)
- docs/claude/roadmap-fix-decisions-2026-10-26.md 15-85행, docs/claude/active-decisions.md 31·75·76·105·117행
- CLAUDE.md 55-85행
- manage-us-stock-strategy/scripts/auto_core_tickets.py 50-66행, stock-strategy-system/alert_policy.json 684·687행(grep)
- workspace/outputs/auto-core/2026-10-27·28·29·30·31, 2026-11-03 decision.json(buy_requirements·candidates·tickets·blocked·reasons)·t2rc-check.json(verdict·c2_item_match·exposure), 2026-10-21 decision.json(tickets)·t2rc-check.json, 그 밖 날짜 decision.json의 tickets 유무
- docs/claude/basefail-cleanup-proposal-2026-11-02.md 63행(계정 id 대조), git log 9fad610
