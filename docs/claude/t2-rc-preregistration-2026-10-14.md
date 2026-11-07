---
id: t2-rc-preregistration-2026-10-14
title: T2 "켜" 조건 R-C 대체(B+) 사전 등록
date: 2026-10-14
decision: 사용자 "결정 t2-rc: B" (2026-10-14 17:34 KST, Cowork 대화)
class: K3 판정 기준 변경(T2 켜 조건). 지금 코드·정책·상태·예약 작업 변경 없음
status: 사전 등록(커밋으로 고정). 효력 = 독립 Judge PASS + 사용자 적용 승인 뒤. 그 전까지 옛 R-C 유지(비교 모드)
authority: order_authority=false · quantity_authority=none · execution_quantity=null · 예산·노출 상한·관문 문턱 불변
consumers: 관제판 t2-rc·redesign-t2 · T2 "켜" 판정(redesign-t2-builder-prompt-2026-10-10.md 46행 R1) · 독립 Judge · 예약 작업 "T2 독립 대조"(만들 예정)·알림 v2.2(만들 예정)
근거: open-items-review-2026-10-14.md 5절(위원회 Full + 재검토 2회), redesign-t2-replay-2026-10-14.md
---

# T2 "켜" 조건 R-C 대체(B+) 사전 등록

## 0. 고정 규칙
- 이 문서는 첫 실운영 후보(회로가 열린 세션)를 보기 전에 커밋한다(2026-10-14 23:30 DocsCommit). 아래 숫자는 이후 느슨하게 바꾸지 않는다. Judge는 더 엄격하게만 바꿀 수 있고, 바꾼 내용은 이 문서 끝 "변경 기록"에 남긴다.
- 셈 시작(D0) = 아래 3절 M1~M3이 모두 적용된 첫 decide 세션. D0 전 세션은 세지 않는다(통과도 실패도 아님).
- 옛 R-C(P-R2 3개월 매수 주문표 ≥ 1)는 효력 시점에 아래 C1·C2로 대체된다. R-A(실제 주문 앵커)·R2(대조 5거래일)·"켜" 전 회차·사용자 "켜"는 그대로.
- R-B 판정은 "PASS(실질 0건) = 미검증"으로 다시 적는다. 그 몫은 C1이 맡는다.

## 1. 켜 조건(모두 참)
- **C1 누수(거짓 음성 포함):** D0부터 decide가 판정한 모든 비교 세션에서, 독립 계산기(M1)가 계산한 회로 열림 집합(종목 × 방향)이 decision.json candidates 집합과 같다. 최소 10개 세션 확인, 불일치 0.
  - decide 결과가 08:40에 아직 없거나(진행 중·HOLD로 F1 전 종료) 입력 파일 sha가 다르면 그 세션은 NOT_CHECKED: 10개에 세지 않고 실패도 아니다. 단 NOT_CHECKED 세션에 주문표가 있으면 그 주문표는 C2·C3 확인으로 쓰지 않는다.
  - 불일치가 나면 그날 원문으로 원인을 가린다: 코어 결함 → CORE_BUG(수정 뒤 C1을 0부터), 계산기 결함 → 계산기 수정(새 sha, Judge 확인) 뒤 C1을 0부터.
- **C2 매수 정확성:** D0 뒤 비교 모드에서 매수 주문표 1건 이상이 나오고, 그 주문표의 수량(정수 동일), LOC 가격(센트 동일), 매수 요건 ①~⑤ 상태, G0~G3 관문 결과, 주문가능 현금 ≥ 주문 금액이 독립 계산기 결과와 모두 같다.
  - 이번 주 exc-1 예외 주문표는 D0 전이면 C2에 세지 않는다.

## 2. 켠 뒤 조건과 감시
- **C3 방향별 첫 주문표 확인:** T2를 켠 뒤 매수·매도 각각 첫 주문표는 독립 계산기가 C2와 같은 항목으로 일치를 기록해야 알림이 입력 안내를 보낸다. 기록이 없거나 불일치면 알림은 "주문표 확인 대기 — 입력 금지"를 보낸다(M3). 매도는 켜기 전 횟수 요건을 두지 않는다(매도 후보는 노출 E ≥ 1.85 또는 카드 EXIT/TRIM일 때만 생겨 무기한일 수 있음).
- **C4 빈도:** D0부터 6주 동안 회로 열림 수·주문표 수(방향별)·막힌 사유 상위 5를 센다. 6주째 주문표 0이면 회로·관문 검토를 사용자에게 1회 알림(자동 변경 없음).
- **C5 일몰:** D0부터 12주 안에 C2가 채워지지 않으면 회로 열림 수·막힌 사유를 붙여 1회 알림. 답이 없으면 T2 비교 모드 유지·B+ 기준 유지(옛 R-C로 돌아가지 않음).

## 3. 필요한 장치(효력 전 준비, 각 Judge 범위)
- **M1 독립 계산기** docs/claude/t2rc-oracle.py: Cowork가 규칙 파일(통합 점검 규칙 파일 현행판)·재설계 설계 원문(7-1 회로, 7-2 가격식)·정책 파일 값만 보고 작성. manage-us-stock-strategy/scripts의 auto_core* 모듈을 import하지 않는다(순환 판정 금지). 입력: 그날 decision.json과 그 inputs가 가리키는 파일(sha 대조), 정규장 종가 기록. 출력: 회로 열림 집합, 주문표별 수량·LOC 가격·요건·관문. 자기 확인: 리플레이 prereg1009 후보 3개(매수 08-13 NBIS ×2, 08-20 MVLL, 모두 요건으로 막힘)와 실운영 10-13·10-14 기록(후보 0)을 재현.
- **M2 예약 작업 "T2 독립 대조"** (화~토 08:40 KST, 08:30 연구 기록 대기 뒤·08:50 알림 전): 그날 파일을 받아 M1을 돌리고 결과를 workspace/outputs/auto-core/<날짜>/t2rc-check.json에 쓴다. 불일치일 때만 푸시. 주문·정책·상태 변경 없음.
- **M3 알림 v2.2**: auto-core-alert.txt에 규칙 1개. apply 모드에서 그 방향의 첫 주문표에 t2rc-check.json 일치 기록이 없으면 ⑦ TICKET 줄·⑩ 입력 안내·orders 쓰기 대신 "주문표 확인 대기 — 입력 금지". 그 밖은 v2.1 그대로.
- 같은 일정: 통합 점검 규칙 파일 115행 보완(매수 불가 상품 + 쪽도 state는 계산값 그대로, label만 "매수 불가 상품", 알림 없음; K1) — R2 연속 일수 전제.

## 4. 사용자 손(일회성, 일상 0)
- 독립 Judge 1번(M1~M3·115행·이 문서를 한 번에 검토, 별도 Claude Code 세션).
- 적용 승인 1번(예약 작업 생성 M2 + 알림 교체 M3 + 규칙 파일 115행 재서명, 한 세션에서).

## 5. 기본 처분
- Judge FAIL 또는 승인 없음 → 옛 R-C 유지, T2 비교 모드 유지(NO_CHANGE). 노출·예산·권한을 올리는 기본값 없음.

## 변경 기록
- 2026-10-14 17:4x KST 작성(Cowork).
- 2026-10-15 독립 Judge 1차 FAIL → 2차 FAIL → 3차 PASS(docs/claude/t2rc-judge-report·judge2-report·judge3-report-2026-10-15.md). Judge가 더 엄격하게만 바꾼 것: (M2) M2를 Claude 예약 작업 대신 Windows 작업 InvestmentV2-T2rcCheck(화~토 08:40 KST)로 두고, 푸시는 08:50 알림 v2.2 ⑫가 보낸다(불일치에 더해 오류·결과 없음도 알림). (C3) 그 방향에 계산기 누락(leak)이 있는 날은 확인으로 세지 않는다. (C1) 계산기가 평가하지 못한 종목이 있는 날, 일치 판정은 NOT_CHECKED(ORACLE_DATA_GAP)로 두고 불일치는 그대로 센다. 모두 조건을 더하기만 해 더 엄격하다.
- 2026-10-15 13:29 KST 사용자 적용 승인 "결정 t2-rc 적용: 승인": 매도 읽기 S1(4열 한 표: {상승, 하락} × {현금, 최선 후보}) · S3(근거 강도 순 → 약 근거 종류 수 → 코드) · S6(후보 열 투자액 = 매도 대금 전부) · S8(분야 한도로 거르지 않음 — 정책 키가 생기면 K3로 두 쪽에 함께) 승인. S5·S7·S9는 Judge가 원문으로 정함, G3 ⅓ 상한은 사용자 결정 5 = b(10-15 09:31). 고정값: 계산기 5607b09b…f02a26 · 실행기 5d3502b9… · 알림 v2.2 eb2b9710… · 로더 v3.12.6-L+R2 915e1966… · 규칙 파일 v3.12.6 129f78af…. 알림·로더 교체 13:31~13:33. 효력 = M2 Windows 작업 등록까지 끝난 뒤, D0 = 그 뒤 첫 decide 세션.
- 2026-10-18 07:1x KST ev-rg1-hyper(사용자 승인 원문 "결정 ev-rg1-hyper 병합: 승인" 07:11, 독립 Judge 1차 FAIL → 재판정 PASS docs/claude/ev-rg1-hyper-judge2-report.md, 병합 0d55b9a): 49행 고정값 갱신 — 계산기 9f0e2238f2a8238016be5406cd2e195aaf24c232adeda5f1fba3a52cd09b1aae · 실행기 fcd8977bac37034e7805dda7dd31756b8b6a224c6cdec673d45189c0cd1680a7(LF 기준; 실행기 16행 = 계산기 값) · 로더 v3.12.7-L+R2 f948ca6e56b0f29a608eb25fede6a27c8352c0998bf63ad8988ecd874df8bc24 · 규칙 파일 v3.12.7 d2bde3c2066b74506b528d4b9f10d8199bd0a7a34fcfa1294ad0ab5c3e9c4203 · 알림 v2.2 eb2b9710… 그대로. 계산기 RG1을 코어와 같은 정의로 고친 계획 변경(결정 rrec-k3-timing d)이라 C1은 병합 뒤 첫 decide 세션부터 0/10으로 다시 센다. 병합 전 C2 일치는 세지 않는다(관문이 바뀜 — 더 엄격). D0(10-16)와 C4·C5 예약 날짜는 그대로.
- 2026-10-19 20:4x KST rrec-ev4-remove(사용자 결정 "rrec-ev4: REMOVE" 17:45, 승인 원문 "결정 rrec-ev4-remove 병합: 승인" 20:38, 독립 Judge PASS docs/claude/rrec-ev4-remove-judge-report.md, 병합 5d5cf79): 49행 고정값 갱신 — 계산기 6a74f813c918046b6e58b19087e1cee69b5984591a54639f84be0b47d0139d64 · 실행기 593a067a848f5d6b27ff8b8ac2e086fa385efe5c83ec3ed88f00d8f19e9fbaf8(LF 기준; 실행기 16행 = 계산기 값) · 로더 v3.12.8-L+R2 91c1e762bdf2419153fa66d575811641975062164d5fa5c609b116d8c321ff9b · 규칙 파일 v3.12.8 f5e4b9c89fd90ead80f3e2064ab4203948f2e27e43ed18f4874c18bbf9223540 · 알림 v2.3 그대로. 계산기 R-REC1에서 EV4를 코어와 함께 지운 계산기 수정(24행)이라 C1은 병합 뒤 첫 decide 세션(10-20 실행, 세션 10-19)부터 0/10으로 다시 센다. 병합 전 C2 일치는 세지 않는다(요건 ⑤ R-REC1 정의가 바뀜 — Judge 권고, 50행 선례). D0(10-16)와 C4·C5 예약 날짜는 그대로.
- 2026-10-20 09:2x KST r5-align(사용자 결정 "r5-align: 1" 08:04, 승인 원문 "결정 r5-align 적용: 승인" 09:17, 독립 Judge PASS docs/claude/r5-align-judge-report.md): 49행 고정값 갱신 — 로더 v3.12.9-L+R2 6f65c89b8a18283e5ced365cd058ed871440d9f7ecf1c6b27e3a2decbd4cfff9 · 규칙 파일 v3.12.9 75fcd5deff628549f10a61a7a628e6693107db317e071cd9994f654fc8fb7722 · 계산기 6a74f813…·실행기 593a067a…·알림 v2.3 그대로. 통합 점검(LLM) 규칙 파일의 R5 문구만 바뀌었고 코어·계산기는 바뀌지 않아 C1을 다시 셀 사유(1절 C1 — 코어 결함·계산기 수정)가 없다. C1·C2·D0·C4·C5 그대로.
- 2026-10-20 16:2x KST c1-keep2(사용자 결정 "결정 c1-keep2: 10-17" 10-20 15:46, 적용 승인 원문 "결정 c1-keep2 적용: 승인" 16:15, 확인 Judge PASS docs/claude/c1-keep2-judge-report.md): 0절의 일회 예외 — 50행(ev-rg1-hyper, 병합 0d55b9a)·51행(rrec-ev4-remove, 병합 5d5cf79) 초기화로 버린 실운영 비교 세션 2026-10-17(평가 세션 10-16) 한 날만 C1에 다시 센다(현행 계산기 6a74f813…·현행 코어 HEAD 4fe10b3으로 그날 입력 재현 일치, 차이는 EV4 표지뿐) → C1 2/10(10-17·10-20). 2026-10-16(평가 세션 10-15)은 세지 않는다(c1-keep 독립 Judge FAIL — hwm-fix 210e951 S7로 요건 ② 재현 불일치, docs/claude/c1-keep-judge-report.md). 24행 초기화 규칙·앞으로의 초기화·C2(병합 전 일치 불산입)·C3·D0(10-16)·C4·C5는 그대로.
- 2026-10-21 19:2x KST close-confirm-e(사용자 결정 "close-confirm: e 켜 전" 10-20 19:43, 승인 원문 "결정 close-confirm-e 병합: 승인" 10-21 19:13, 독립 Judge PASS docs/claude/close-confirm-e-judge-report.md, 병합 f8d065d): 코어 주문표 priceCalc에 band·hold가 더해지고 매수 lo~hi가 판정 유지 구간으로 좁혀질 뿐, 후보·수량·LOC 가격·요건·관문은 그대로라 C1·C2 셈에 영향이 없다. 계산기 6a74f813…·실행기 593a067a…·로더·규칙 파일 그대로(49행 고정값 변경 없음). 매수가 HOLD_RANGE_UNVERIFIED로 빠진 날은 계산기가 누수(ticket_leaks → MISMATCH)로 보며 24행 CORE_BUG(수정 뒤 C1 0부터)·48행 C3 불산입을 그대로 적용한다 — 그날을 MISMATCH에서 빼는 완화는 사용자 결정이다. Judge의 사전 등록 변경 없음.
- 2026-10-26 16:3x KST t2-gate REMOVE-v2(사장 결정 "결정 t2-gate: REMOVE-v2" 10-26 16:07, 독립 Judge 1차 FAIL 저장소 루트 t2-gate-judge-1.txt → 2차 PASS t2-gate-judge-2.txt, 효력 조건 붙음): 재설계 T2 "켜" 조건 R2에서 "5거래일 연속" 셈만 뺀다. 대신 C1 창(지금은 10-17 실행분부터, C1이 0부터면 창도 다시 시작)의 모든 비교일 차이를 분류하고(compare.json COMPARED 5일 이상, 계산기 diagnostics 전 항목·노출 블록 포함, 오라클 결과 없는 날은 차이 0으로 세지 않음), CORE_BUG 해소 커밋 목록, 대조 OK 연속 5회를 더한다. 자세한 조건은 docs/claude/roadmap-fix-decisions-2026-10-26.md 1-1·1-2절. 이 문서의 C1·C2·C3·C5·24행 초기화 규칙·49행 고정값은 그대로.
- 2026-11-03 20:0x KST t2-c2-sell(사장 결정 카드 2026-11-03 19:42:26 KST "매도 주문표로도 검증 인정" — 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9UF5a9M9JfDKP9jzksjeedx, 카드 질문 "자동 판단 켜기 조건의 '매수 주문표 검증'을 어떻게 할까요?"는 제안 id를 적지 않음 · 적용 승인 원문 "결정 t2-c2-sell 적용: 승인" 2026-11-03 20:06:28 KST 사장실 회사PC 스레드 직접 입력(cmsg_0137MRzn9nuDvvQmVxm6WeX93Mnc94nX6fo9rT8kFjSoST, Judge 보고 뒤 바로 앞 제안 1건) · 독립 Judge PASS-WITH-CONDITIONS docs/claude/t2-c2-sell-judge-report.md · 제안 docs/claude/t2-c2-sell-proposal-2026-11-03.md): **사장 결정 완화(H2) — Judge가 바꾼 것 아님.** 25행 C2를 "C2 주문표 정확성: D0 뒤 비교 모드에서 주문표(매수 또는 매도) 1건 이상이 나오고, 그 주문표가 독립 계산기 ticket_check의 모든 항목에서 같다 — 매수면 25행 원문 그대로, 매도면 수량(정수 동일, 재배치 다리 경로 2·3 포함)·LOC 가격(센트 동일)·매도 근거·단계(G3)와 G0~G2 관문 결과·그 주문표가 있어야 하는지(should_exist)가 같다. NOT_CHECKED 세션의 주문표는 세지 않는다"로 읽는다. C3(29행)의 "C2와 같은 항목"은 매수에서는 이전 C2 매수 항목(25행 원문) 그대로, 매도에서는 새 C2 매도 항목이다. Judge 조건(더 엄격하게만, 보고서 '조건' 절): (1) C2로 세는 세션 = 그 세션 t2rc-check.json verdict MATCH·counts_for_c1 true·decision_mode compare·ticket_leaks 0·reason에 ORACLE_DATA_GAP 없음·세는 주문표 not_recomputed 빈 목록 — c2_item_match 하나로 세지 않는다 (2) 세는 매도 주문표마다 목표 비중 출처(S7 reduce target_weight / 등록부 EXIT·TRIM), S7 밖 원자료(보유 수량·정규장 종가·배수)로 손계산한 목표 비중과 정책 target_exposure 1.55(또는 카드 EXIT·TRIM 목표)의 대조, 재배치 경로와 후보, r_max와 근거 종류를 기록한다 — 못 하거나 안 맞으면 세지 않는다 (3) 켠 뒤 첫 매수 주문표는 계산기 일치 기록에 25행 원문 매수 항목 전부(수량·LOC 센트·요건 ①~⑤ 각각·G0~G3·주문가능 현금 ≥ 금액·W*/첫 진입 목표)가 항목별 match true여야 하고, 그 주문표가 확인되기 전까지 비서실 첫 보고의 주문표 줄에 "매수 첫 주문표 미검증"을 붙인다(문구만) (4) C2를 채운 뒤 계산기 t2rc-oracle.py sha(2026-11-03 현행 LF 기준 41bc56df2981606f12653d10efa0f5f6339b1b19fbde6204b05aaca105370466)가 바뀌고 그 수정이 매도 수량·가격·관문·should_exist 계산을 바꾸면 이전 매도 C2 일치는 세지 않는다(50·51행 선례) (5) C1 공식 셈(10-31 MISMATCH 처리 — t2rc-mismatch-1031-pwr-factid-2026-11-01.md)이 정해지기 전에는 "켜" 충족으로 표시하지 않는다 (6) 대시보드 보류 표시: 2026-11-03 통합점검 대시보드 v30(1793703751-bd5d)에서 비교 모드 core.tickets와 기록 모드 hold 주문표가 "키움 입력 금지"로만 보이고 입력 주문(orders)으로 보이지 않음을 페이지 코드·모의 자료로 확인(제안 9절). 그대로: R1·C1·C3·C5·24행 초기화 규칙·49행 고정값·55행 차이 분류 의무·CORE_BUG 보류·대조 OK 연속 5회·R3 사장 "켜"(직접 입력, 이 승인은 decision_mode를 바꾸지 않음)·Hard safety·노출·예산·권한·decision_mode compare. 지금 C2 = 0(첫 매도 주문표는 G1 S7 겨울 봉 수정 9fad610 뒤 decide에서 확인).
- 2026-11-07 17:26 KST c1-1031(사장 직접 입력 "결정 c1-1031: A", 비서실 — 바로 앞 제안 docs/claude/c1-count-1031-2026-11-07.md): 셈 기록, 규칙 변경 없음. 2026-10-31 실행분 MISMATCH(PWR 매수 회로, 같은 fact_id 두 판 — t2rc-mismatch-1031-pwr-factid-2026-11-01.md, 코어 결함·계산기 결함 아님)를 22행 "불일치 0" 그대로 적용해 C1 창을 끊고 **2026-11-03 실행분부터 다시 센다**(이날부터 통합 점검 v3.12.11의 fact_id -vN 규칙 적용). 2026-11-07 기준 C1 5/10(11-03·04·05·06·07, 모두 verdict MATCH·counts_for_c1 true·계산기 41bc56df…·ticket_leaks 0·decision_mode compare). 창 안 코어 병합 db56303·6aea772·7f4bbad·9fad610은 조건부 매수 막힘·종가 라벨만이라 후보 집합 불변(제안 4절). 10-17·10-20·10-27~30 일치는 세지 않는다. C2·C3·C5·R3·24행 초기화 규칙·55행 차이 분류·56행 t2-c2-sell 조건 그대로 — 56행 Judge 조건 (5)의 "C1 공식 셈"은 이 줄로 정해졌다.
