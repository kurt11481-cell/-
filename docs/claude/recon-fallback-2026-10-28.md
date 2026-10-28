---
id: recon-fallback-2026-10-28
type: proposal
status: "착수 승인(10/28 08:23 KST) → dev-run recon-fb NEEDS_APPROVAL(Judge PASS, 새 실패 0) → 병합 승인 카드(10/28 09:22 KST), 병합 = 사장 PowerShell. 권한·한도(K3, 대조 불변 조건 I3 B2-N), 제약 완화(H2)"
date: 2026-10-28
authority: "order_authority=false · quantity_authority=none · execution_quantity=null. 이 문서는 진단·제안·결정 기록이며 병합 전까지 아무것도 적용하지 않았다"
consumers: "사장(승인 카드) · 승인 시 개발 큐 authority Builder 지시문 · Judge(Opus)"
---

# 직전 거래일 달러 예수금 행이 없을 때의 B2-N 대체 (recon-fallback)

부딪히는 결정: recon-cap: REPLACE(active-decisions.md 82행, 2026-10-27 10:16) — 이어서 고치는 같은 조건의 다음 단계다. recon-dt a · cashflow-proof B2-N(같은 파일 해당 행) — "불변 조건 완화 아님"이라고 기록된 조건에서 증거 요건을 한 가지 낮추므로 **제약 완화(H2)**다. t2-gate(80행) — "켜" 관문의 대조 OK 연속 셈을 앞당기는 효과가 있어 사장에게 따로 알린다.

## 1. 문제 (읽은 원문)
- 10/27 06:15와 10/28 06:15 두 번 모두 `UNVERIFIED_OUTFLOW_LEDGER_UNAVAILABLE:<직전 거래일>:USD_ROW`로 보류. 10/28 result.json commit_sha 6840416(recon-cap3 병합 후 판)에서도 같다.
- 키움 읽기 조회(10/28 07:32 KST, 실전계좌, ust21132): 10/26 행 있음(fx_entr 59.32), 10/24 행 있음(150.04), **10/27 행 없음**("내역이 없습니다").
- 코드: auto_core_reconcile.py 780-835행 unverified_outflow는 base_before·base_after 두 날의 USD 행을 모두 요구한다. base_after = 이번 스냅숏 시각에 마감된 직전 거래일(ledger_days 744-757행).
- 06:15 시점에는 직전 거래일(D) 행이 구조적으로 없을 가능성이 있다(2회 중 2회). 행이 몇 시에 생기는지는 확인 필요 — 10/28 12:00·21:00 KST 읽기 조회로 재는 중.
- 이 때문에 recon-cap3이 고친 한도 조건(출금 합계 ≤ 기준 현금 + 순정산)은 도달조차 못 해 시험되지 않았다. 11/03 실행부터 체결 조회 창 14일 초과(FILL_WINDOW_TOO_LONG, recon-hold-2026-10-23.md 49행).

## 2. 제안 (검토 순서)
- NO_CHANGE: 행이 일찍 생기기를 기다린다. 11/03 기한과 매일 HOLD 비용(성과 채점·노출·주문표 차단)을 생각하면 비권장.
- REMOVE/SIMPLIFY: B2-N 폐기 → 확인 코드 경로로 1회 기록. 사람 손 일상화, HWM 오차(cashflow-proof-options 22행). 비권장.
- REUSE: 06:15 실행 시각을 늦춘다. 06:40 통합 점검 → 07:45 판정 → 08:40 계산기 → 08:50 알림 사슬 전체와 겨울 시간 일정이 같이 흔들린다. 행이 생기는 시각을 모르면 시도할 수 없다.
- **REPLACE(권장): base_after 행이 없으면 그 앞 거래일 행(fallback_day)으로 대신 대조한다.** 아래 조건을 모두 만족할 때만:
  1. fallback_day는 base_after 바로 앞 거래일 하나뿐(그보다 더 앞은 안 됨), 그리고 fallback_day > base_before.
  2. 계산 창의 모든 체결 session_date ≤ fallback_day (그 뒤 체결이 있으면 행에 안 들어 있으니 HOLD, 지금처럼).
  3. 나머지 조건은 그대로: 0.05 일치, 출금 한도(recon-cap3), 원화 예수금 증가 금지, HWM 조정 0, 열린 주문 0.
  4. 대체했다는 표시를 unverified_outflow_basis에 한 줄로 남기고 알림에 경고로 보인다. **기존 결과 필드 목록은 늘리지 않는다**(basis 안의 기존 키 값으로 표시하거나 warnings 문자열 사용 — Builder 지시문에서 확정).
- 안전 방향: fallback_day 이후(fallback_day~base_after 사이)에 출금이나 입금이 있었다면 스냅숏 잔차 R에는 들어가고 원장 잔차 L에는 안 들어가 |R−L|이 0.05를 넘어 HOLD가 된다. 즉 놓치는 쪽이 아니라 막히는 쪽으로 틀린다(unverified_outflow 로직 820-826행 읽음).
- 지금 건 사전 확인: 마지막 체결 세션 10/21 ≤ 10/26, 키움 10/26 행 fx_entr 59.32 = 10/28 스냅숏 현금 59.32. 병합 뒤 10/29 06:15 실행에서 이 조건이 맞으면 대조가 풀릴 수 있다(확인 필요 — 그날 새 체결·출금이 없어야 함).

## 3. 바뀔 조건
- 12:00/21:00 KST 조회로 10/27 행이 같은 날 일찍 생기는 것이 확인되면 이 안의 필요성이 줄어든다(그래도 구조적 지연 대비책으로 유효). 행이 이틀 뒤에야 생기면 fallback만으로도 부족할 수 있어 재검토.
- Judge가 "행이 늦게 생기는 날 임의 입금을 가릴 수 있는지"를 반례로 보이면 안을 접는다.

## 4. 다음 단계 (승인 시)
1. 개발 큐 authority로 Builder 지시문 작성(전체 테스트 금지·대상 테스트만, 결과 필드 목록 비교 테스트 유의) → Opus Judge → 병합은 사장 승인 + `-ApproveAuthority`.
2. 목표: 11/03 전, 가능하면 10/29~30 병합.

검토 완결: 원문 확인 5/6 (result.json 10/28·reconcile.json cash_flow_evidence, auto_core_reconcile.py 727-905행, 키움 ust21132 조회 3건, recon-i3-2026-10-27.md, 로드맵 스레드 인계 메모) · 내장 재검토 0회 · 미해결 2 (행 생성 시각, 겨울 시간 영향) · 자료 시점 2026-10-28 08:3x KST · 바뀔 조건: 위 3절

## 결정 기록
- 2026-10-28 08:23 KST 사장 결정 카드 "착수 승인"(사장실 회사PC 스레드 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9Dp5L8zK87C48ngGqFy7yKi, 제안 recon-fallback-2026-10-28, 계정=사장, 바로 앞 제안 1건·같은 날·1회). 근거 규칙 CLAUDE.md 64~70행.
- 2026-10-28 08:58 KST dev-run recon-fb NEEDS_APPROVAL: Judge 1회차 PASS(class_ok=false), 테스트 3406→3416, 새 실패 0, diff_hash 42e388ed7c1c4777c1d59ef1ab22cea67573865d33d1b3246af4beea5170c98e (docs/claude/dev-runs/recon-fb.md).
- 2026-10-28 09:22 KST 사장 결정 카드 "병합 승인"(카드 cmsg_0137MRzn9nuDvvQmVxm6WeX93wcDcZ3tuArBSEh1AXykeR, 계정=사장). 병합은 사장이 자기 PowerShell에서 `.\tools\dev-merge.ps1 recon-fb -ApproveAuthority` + Enter 한 번. 병합 확인과 첫 적용(10/29 06:15) 결과는 병합 뒤 이 문서에 덧붙인다.
