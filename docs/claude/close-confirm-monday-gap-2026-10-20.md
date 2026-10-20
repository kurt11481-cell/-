---
id: close-confirm-monday-gap-2026-10-20
type: decision-record
status: current
as_of: 2026-10-20 19:5x KST
summary: 사용자 결정 2건 — close-confirm(a는 다음 규칙 파일 개정에 묶음, e는 T2 "켜" 전) · monday-gap(M1: 월요일 개장 전 점검 v2.2, 2026-10-20 20:18 적용).
consumers: 다음 통합점검 규칙 파일 개정 세션(a 반영), T2 "켜" 전 점검(e), 월요일 개장 전 점검 예약 작업, 관제판 close-confirm·close-confirm-e·monday-gap
---

# 결정 기록 — close-confirm · monday-gap (2026-10-20)

## 1. 사용자 결정 (원문)
- 19:43 KST: "1. 결정 close-confirm: a 묶음, e 켜 전 2. 결정 monday-gap: M1"
- 근거 대화: 같은 날 18:49~19:43 Cowork 대화(종가 조회 시각·확정 반영·주문 입력 시각 검토). 재검토 기록 docs/claude/review-stability-2026-10-13.md 2절 22.

## 2. close-confirm
### a — 다음 통합점검 규칙 파일 개정 때 함께 (따로 승인하지 않음)
- 대상: docs/claude/integrated-check-prompt-v3.12.9-2026-10-20.txt 51행 끝 문장.
- 지금: "다음 실행이 확정된 값으로 다시 판정한다."
- 바꿀 문장: "직전 세션의 확정 값은 다음 실행에서 지난 세션 일봉으로만 들어간다(직전 세션 판정을 다시 하지 않는다. 확정 종가 반영은 저녁 입력 카드의 기준종가 환산이 맡는다 — 2026-10-20 close-confirm)."
- 이유: 그 문장을 실행하는 단계가 규칙 파일·로더 어디에도 없다(재검토 2회 확인). 규칙 파일은 해시로 고정되어 있어 한 줄만 고쳐도 로더 해시 교체 승인이 필요하므로, 다음 개정(v3.12.10 이후)에 묶는다.
- 다음 개정 세션 확인 항목: 이 절의 문장을 넣었는지, 변경 기록에 "close-confirm a"를 적었는지.

### e — T2 "켜" 전에 (권한·한도 변경, K3)
- 내용: 주문표마다 판정이 유지되는 근사 종가 구간을 계산해 대시보드 priceCalc lo~hi를 "근사 종가 ±1%"와 그 구간의 겹침으로 좁힌다. 매수는 범위 밖이면 가격을 보여 주지 않고, 매도는 막지 않고 경고만 띄운다(매수만 막는 원칙).
- 근거: auto_core_tickets.py 369~385행(loc_price·±1%), dashboard-order-panel-2026-10-07.md 35·84행(범위 밖이면 화면이 막음), auto_core_rules.py 9행(P3: 근사 종가로 판정).
- 한계: EMA·σ60 재계산으로 판정이 바뀌는 경우는 잡지 못한다.
- 순서: 권한 변경은 한 번에 하나 — enter-window(경로 때문에 authority) 병합 뒤에 Builder 지시문을 쓴다. 수동 경로(worktree Builder + Opus 독립 Judge).

## 3. monday-gap — M1 (월요일 개장 전 점검 v2.2)
- 바꿀 것:
  - 예약 작업 trig_01M1DYJ28pstoumsEV6ZSWhf의 실행 시각 `CRON_TZ=Asia/Seoul 20 21 * * 1` → `CRON_TZ=America/New_York 25 3 * * 1`. 여름에는 16:25 KST, 겨울에는 17:25 KST다. 프리마켓 시작 35분 전이 된다.
  - 지시문 v2.1 → v2.2. 새 4-1) 토요일 주문표 재확인(기록 모드 주문표만, 종목마다 GO / 재검토(매수 입력 보류) 판정, 매도는 막지 않음)을 넣는다. 기록 절 "## 토요일 주문표 재확인"을 넣는다. 알림 ④(대상이 있으면 GO여도 항상 보냄, 확인 푸시)를 넣는다.
- 지시문 원문: docs/claude/scheduled-prompts/pending-monday-gap/monday-pre-open-check-v2.2.txt (sha256 78926184c1cfb7ad89b8bb714d5c351b44e8b8cd7941aff81c119945510915f5, 8,053자). 바탕은 monday-pre-open-check.txt(d05cbe6e…, v2.1)이고, 바꾼 곳 6군데만 다르다.
- 키움은 쓰지 않는다(금지 줄 그대로). 프리마켓 가격 대조(M1b)는 키움이 프리마켓 현재가를 주는지 확인한 뒤에 따로 한다.
- 상태: **적용됨(2026-10-20 20:16~20:18 KST).** 19:5x 첫 시도는 자동 승인 검사(Cowork Scheduled Task Write)가 거절했다. 사용자 "예약 작업 변경 승인: monday-gap"(20:13) 뒤 다시 시도해 성공했다. 시각 updated_at 11:16:33Z, 지시문 11:18:50Z("prompt re-signed by 금동한"), 다음 실행 2026-10-26 16:25 KST. 저장소 사본 monday-pre-open-check.txt = 78926184…, README 표·변경 기록 갱신.
- 적용 뒤 할 일:
  1. scheduled-prompts/monday-pre-open-check.txt를 v2.2로 교체한다.
  2. README 표의 해시를 바꾸고 변경 기록에 한 줄 적는다.
  3. 통합점검 대시보드 주문 카드의 입력 전 확인 1·2번 문구를 토요일 발행분용으로 바꾼다. 1번은 "월요일 개장 전 점검 푸시에서 GO 확인", 2번에는 "(월요일 GO 푸시는 경보 아님)"을 붙인다. 표시 전용이며, 대시보드 HTML을 바꾸기 전에 디자인 규칙 문서를 읽는다.
- 비슷한 기존 안: order-receipt-process-review-2026-10-09.md 2-4(17:15 입력 직전 점검, K3 후보). M1은 그 안의 월요일 한정판이고 새 예약을 만들지 않는다. 2-4는 그대로 후보로 남긴다.
- 잃는 것: 월요일 16:25~21:20 사이의 SAVE 소식. 화 06:40 통합점검이 다시 읽으므로 영향은 작다.
- 매주 사용자 손: 0. 푸시를 읽기만 하면 된다.

- 2026-10-20 20:2x KST 마무리: 통합점검 대시보드 주문 카드의 입력 전 확인 1·2번에 토요일 발행분 문구를 넣었다(통합점검 버전 22, version id 1792495206-e6f6, 표시 전용). 1번은 "월요일 개장 전 점검 푸시에서 이 종목 GO 확인(토요일 발행분)", 2번 뒤에는 "(월요일 GO 확인 푸시는 경보 아님)"을 붙였다. 관제판 monday-gap은 done. 첫 실행은 10/26 16:25 KST다. 지금은 비교 모드라 알림 ④는 없고 기록 줄만 남는 것이 정상이다.

## 4. 확인 필요
- 키움 겨울 프리마켓 시작이 18:00 KST인지.
- 키움 기준가(base_close_pric)가 갱신되는 시각. 관측은 1건뿐이다.
- 키움이 프리마켓 현재가를 주는지(M1b의 전제).
