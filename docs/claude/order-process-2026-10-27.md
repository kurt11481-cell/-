---
id: order-process-2026-10-27
type: decision
status: "채택 — ② 재량 주문 전 점검 ③ 체결 당일 기록 ④ BE·LITE 보유 카드 작성 ⑤ r-wd-1022 닫기. ⑥(HOLD 중 매도 주문표)은 K3라 별도"
date: 2026-10-27
authority: "order_authority=false · quantity_authority=none · execution_quantity=null. 정책·상태·예약 작업·코드·관문 변경 없음. 사장 주문을 막지 않음"
consumers: "사장실 코디네이터·회사PC 스레드(재량 주문 전 점검·체결 기록을 받을 때) · Cowork(보유 종목 S7b 일지) · 카드 작성 세션(BE·LITE) · 주간 팀장회의"
source_decision: "사장 결정 카드 선택 '②~⑤ 전부 채택'(사장실 회사PC 스레드 주문 지시까지 운영 과정 점검, 2026-10-27 14:13 KST, 계정=사장, 바로 앞 제안 1건·같은 날·1회). 제안 = order-process-assessment-2026-10-27.md 2절(사장실 Library)"
---

# 주문 과정 운영 절차 (2026-10-27 채택)

부딪히는 결정: 없음(active-decisions.md 검색 — G1·매도·재량 주문 관련 결정 0). 긴장: CLAUDE.md 목표 "일상 손 0" — ②③은 사장이 주문표 밖에서 직접 주문하는 날에만 적용하므로 일상 손은 늘지 않는다.

## 배경 (원문)
- 10/22부터 대조 HOLD로 코어 주문표 0건(workspace/outputs/auto-core/2026-10-22~27 decision.json tickets).
- 실제 체결은 사장 재량 주문(10/21 7건, 2026-10-27 result.json holdings_change). 결정 일지 마지막 기록 seq 14(2026-10-20).
- BE·LITE는 코어 보유 위험 규칙 없음(2026-10-27 result.json warnings). 계좌는 10/22 잠정 종가로 HWM 대비 −32.24%, L3 아래(l3-review-draft-2026-10-23.md 12행).

## ② 재량 주문 전 점검
- 사장이 코어 주문표가 아닌 주문을 키움에 넣기 전, 사장실에 `주문 전 점검: <티커> <매수|매도> <수량> <가격>` 한 줄.
- 받는 스레드는 읽기 전용으로 기존 관문만 본다: 노출 E vs 위험 예산 1.55·하드 상한, 상품 승인, R-REC1 회복 관문, 실적 금지 구간, 보유·관심 카드 유무, 시나리오 SCN-27H1 줄.
- 답은 `통과` 또는 `경고: <걸린 관문> — <이유 1줄>`. 주문을 막지 않는다. 수량·가격을 새로 제안하지 않는다(quantity_authority none). 계산 못 한 항목은 "확인 필요"로 표시.

## ③ 체결 당일 기록
- 넣은 날 사장실에 `체결: <티커> <방향> <수량> @<가격>, 이유: <1줄>` 과 출금·입금이 있으면 `출금 <금액> <날짜>`.
- 받는 스레드는 docs/claude/order-instructions/UD-<YYYYMMDD>-<티커>-<번호>.md(선례 UD-20261007-MVLL-1)에 적고 active-decisions.md J절에 한 줄. 체결 수량·가격의 정본은 다음 날 키움 체결 기록(대조)이며, 이 기록은 이유와 출금 증거용이다.
- 보유 종목 결정(ADD/HOLD/TRIM/EXIT)의 결정 일지 S7b 기록은 지금 규칙대로 Cowork에서 한다(CLAUDE.md Hard safety·Decision journal). 이 기록은 일지가 아니다.

## ④ BE·LITE 보유 카드 작성
- l3-review-draft-2026-10-23.md 결론 ②. 별도 스레드에서 초안 → 사장 수락 → 수락 세션이 card-evidence-registry.json 갱신(CLAUDE.md 43행). 기존 카드 파일은 건드리지 않는다(00-home 고치면 안 되는 파일).

## ⑤ r-wd-1022 닫기
- 출금 설명은 recon-i3-2026-10-27.md 숫자 분해로 끝남. 관제판 작업을 done으로 바꿔 비서 제안에서 빠지게 한다.

## 하지 않음
- 사장 재량 주문을 시스템이 막는 것, 새 화면·새 예약 작업, 주문 2단계 논의(redesign-t5 무응답 = 1단계).
- ⑥ 대조 HOLD 중 매도 주문표 허용은 K3 — 10/28 06:15 대조 결과를 본 뒤 따로 제안.

## 기록
- 2026-10-27 14:13 KST 채택(카드). 같은 날 이 문서와 active-decisions.md C절 한 줄.
