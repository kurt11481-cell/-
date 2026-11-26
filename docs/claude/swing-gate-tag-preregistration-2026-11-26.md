---
id: swing-gate-tag-preregistration-2026-11-26
type: preregistration (고정)
status: 고정 — 2026-11-26 21:06:46 KST 사장 고정 카드 '제안값 그대로 고정'(cmsg_0137MRzn9nuDvvQmVxm6WeX9GmFZrnd7QXWeFZTxhgZ54N, 질문 '더 이른 매수 시험 3건을 어떤 숫자로 고정할까요?', 누른 계정 = 사장). 독립 점검 통과판(e1-prereg-independent-review-2026-11-26.md). 이 파일의 sha256은 swing-gate-tag-preregistration-2026-11-26.sha256에 있다. 고친 뒤의 결과는 이 사전 등록의 결과가 아니다
as_of: 2026-11-26 KST
decision: recovery-gate-1126 — 2026-11-26 19:54:16 KST 사장 카드 '과거 자료 시험도 함께'(cmsg_0137MRzn9nuDvvQmVxm6WeX9TMTwqXjdpKr7mxJRG6uHwp). D3 동결 예외 1건(이 문서·사이드카·꼬리표 계산 파일·꼬리표 장부)
default: 보고만. 스윙 재량 주문의 R-REC1 예외는 두지 않는다(결정 색인 recovery-gate-1126 행). 고정된 스윙 사전 등록(swing-prereg-draft-2026-11-19.md)·swing_shadow_ledger.py·recovery-gate-R-REC1-2026-10-09.md는 고치지 않는다
consumers: 스윙 판정 보고(swing-prereg-draft-2026-11-19.md 3절 9번 판정 지점) · 관제판 swing-gate-tag-1126 · swing-1119
authority: order_authority=false · quantity_authority=none · execution_quantity=null
---

# 스윙 그림자 신호의 관문 상태 꼬리표 — 사전 등록

## 1. 질문
회복 관문이 닫힌 동안 난 스윙 신호의 성적이 열린 동안 난 신호와 다른가.

## 2. 꼬리표 (신호가 장부에 붙을 때 함께 고정)
- 신호마다 swing-signal-ledger.jsonl 줄의 evaluation_session과 **같은 evaluation_session을 가진** 코어 기록 workspace/outputs/auto-core/<폴더>/decision.json을 찾는다(폴더 이름은 KST 실행일이라 쓰지 않고 파일 안 evaluation_session으로 맞춘다).
- 그 기록의 shock.by_symbol.<종목>.status: 'no' = 닫힘 중, 'ok' = 열림 중, 'unk' = 미상. 매수 요건 ⑤와 같은 판정이다(auto_core_tickets.py 278~288행 · auto_core_rules.py 860~873·981~989행). open 칸은 쓰지 않는다(open은 '사건 열림'이라 말이 거꾸로이고, 공식 악재로 막힌 종목은 open 거짓인 채 status만 'no').
- 미상으로 따로 셈: 맞는 코어 기록이 없을 때(예: 2026-11-09·11-10 평가분 없음) · 그 종목 칸이 없을 때(2026-11-20에 넓힌 AMAT·LRCX·KLAC·NOW·SNOW·DDOG는 코어 종목이 아님) · status 'unk'. 미상은 두 무리에 넣지 않는다.
- 계산 파일: docs/claude/swing_gate_tag.py(sha256 c8e4657c4feebfb7ce26cce219344ec8785202bb0079fa0cb7f1fea7c235854d, 사이드카 runner 줄, --self-test 통과 — 합성 기록만). 참고: 고정일에 이미 있는 2줄은 기록일이 스윙 고정일(2026-11-19) 앞이라 스윙 판정 표본 밖이다(swing_shadow_ledger.py run()의 FIX_DATE 자르기). 꼬리표는 붙이되 무리 통계에는 들어가지 않는다.
- **고정 방법**: 코어 기록은 git 추적 밖이라 뒤에 바뀔 수 있다. 그래서 꼬리표 계산 파일(docs/claude/swing_gate_tag.py, 새 파일)이 `--tag-lines`로 낸 줄(signal_id · evaluation_session · 찾은 decision.json 경로·sha256·generated_at · status · 꼬리표 · tagged_at · late)을 그대로 docs/claude/swing-gate-tag.jsonl(추가 전용, git)에 붙여 _pending 커밋한다. 스윙 장부 줄을 붙이는 같은 손 실행에서 함께 한다. 이미 적힌 줄은 고치지 않는다.
- 고정일에 이미 장부에 있는 2줄(PWR-2026-10-29 · LITE-2026-11-02)도 고정 직후 같은 방법으로 꼬리표를 붙인다(코어 기록 2026-10-31·2026-11-03 폴더가 남아 있음을 2026-11-26 확인, sha256은 그때 적는다).

## 3. 보고 때와 방법
- 고정된 스윙 눈가림을 지킨다: 스윙 판정이 '계속'인 지점에서는 평균·t가 기록에 남지 않는다(swing-prereg-draft-2026-11-19.md 72행 ⓑ, swing_shadow_ledger.py 357행). 그래서 **무리별 평균·t와 4절 판정은 스윙 판정이 통과·닫힘(기한·마지막 지점 닫힘 포함)으로 끝난 지점에서 한 번만** 낸다. '계속' 지점과 주간 표시에서는 무리별 **건수만** 낸다.
- 거래 목록: swing_shadow_ledger.py `--json`은 건수·상태·판정만 내고 거래별 excess를 내지 않는다(393~394행). 그래서 꼬리표 계산 파일이 그 파일의 함수(ledger_signals · in_scope · trade · clusters 등)를 가져와 run()과 같은 순서·같은 자르기로 거래를 다시 만든다(그 파일은 바꾸지 않음). 자체 시험으로 묶음 수·trade_status가 run() 출력과 같은지 대조한다.
- 자르기와 한 번만: 무리 통계는 스윙이 통과·닫힘으로 끝난 판정 지점의 cut_day(그 지점 k번째 묶음의 청산일)까지 청산한 거래만 쓴다(기한·마지막 지점 닫힘은 그날까지). 처음 낸 결과를 docs/claude/swing-gate-tag-report.jsonl(추가 전용, git)에 붙이고, 뒤 실행은 그 줄을 따르고 다시 계산하지 않는다.
- 무리 안 묶음 규칙은 스윙 사전 등록과 같다(overlap · ROOT_OF). 보고 칸: 무리별 묶음 수 · 평균 excess(스윙 − β×QQQ, 비용 뒤) · t(스윙 사전 등록과 같은 식 — 보통 표준오차와 분기 묶음 표준오차 중 큰 쪽) · 미상 수.

## 4. 예외 안건을 올릴 조건 (고정값, 2026-11-26 21:06 KST 카드)
- '닫힘 중' 무리가 10묶음 이상이고, 평균 excess > 0이며 t ≥ 2.3이면 '스윙 재량 주문의 R-REC1 예외' 권한·한도 안건을 올린다(선례 rrec-ev4·ev-rg1-hyper와 같은 급). 그 밖은 NO_CHANGE.
- 조건을 넘어도 이것은 안건을 올리는 조건일 뿐이다. 스윙 몫 키우기 판정(스윙 사전 등록 3절 10·11번)과는 따로다.
- 결과를 본 뒤 기준·무리 나누기를 바꾸지 않는다.

## 5. 자체 시험 (꼬리표 계산 파일)
1. 합성 기록 3건: status 'no'·open 참 → 닫힘 중 · status 'no'·open 거짓(공식 악재) → 닫힘 중 · 종목 칸 없음 → 미상.
2. 같은 evaluation_session의 기록이 둘 이상이면(재실행) generated_at이 가장 늦은 파일을 쓰고 둘 다 sha256을 적는다(코어 기록에는 written 칸이 없고 generated_at만 있다). 하나도 없으면 미상. 꼬리표 줄의 tagged_at이 신호 written_at보다 7일 넘게 늦으면 late = 참.
3. `--tag-lines`는 꼬리표 장부에 이미 있는 signal_id를 다시 내지 않는다.
4. 스윙 판정이 '계속'이거나 판정 지점 전인 실행에서는 평균·t 칸이 출력에 없다.
5. 다시 만든 거래의 묶음 수·trade_status가 같은 as_of의 swing_shadow_ledger.run() 출력과 같다(다르면 멈춤).

## 6. 하지 않음
- 고정된 스윙 사전 등록·swing_shadow_ledger.py·스윙 장부 줄·판정 기록·R-REC1 문서 고치기. 코어·정책·예약 변경. 주문·수량 제안. 스윙 재량 주문에서 관문 무시.

## 7. 연결표
| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| swing-gate-tag.jsonl 줄 | 사장실 회사PC 스레드, 스윙 장부 줄을 붙이는 같은 손 실행(swing-prereg-draft-2026-11-19.md 7절 ②) | 스윙 판정 보고(같은 문서 3절 9번) | 4절 조건 충족 시 예외 안건 | 스윙 장부 줄 수 ≠ 꼬리표 줄 수면 꼬리표 계산 파일이 경고. 이 점검을 읽는 곳은 아직 없음 | **끊김** — 메우는 길: 고정 카드 뒤 스윙 판정 절차 문서(관제판 swing-1119 메모)에 '장부 줄 붙일 때 `swing_gate_tag.py --tag-lines`도 함께' 한 줄(문서만, 고정본 안 고침, 승인 불필요) |

## 검토 기록
- 조언(Fable) 1회 — 세 초안 합쳐 결론 바뀜 3 · 정정 5 · 미반영 0. 이 문서 반영: 평균·t·4절 판정은 스윙 판정이 통과·닫힘으로 끝난 지점에서만, 거래는 함수로 다시 만들고 run()과 대조(결론 바뀜) · generated_at·tagged_at·late(정정). (작업자 약 19만 토큰 · 8분 28초)
- 독립 점검(2026-11-26 20:28 KST, e1-prereg-independent-review-2026-11-26.md): 권장 반영 — cut_day 자르기·한 번만 기록, 자체 시험 3·4 추가, 꼬리표 file 칸 저장소 기준 경로.
