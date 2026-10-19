---
id: rrec-ev4-remove-decision-2026-10-19
type: decision
status: 결정 완료 — 사용자 원문 "결정 rrec-ev4: REMOVE"(2026-10-19 17:45 KST, Cowork 대화). 구현 전 — 권한·한도(K3) 수동 경로(Builder worktree → 독립 Judge → 사용자 승인 1줄 + 병합 스크립트 1번). 병합 전까지 운영 코어·독립 계산기·통합 점검은 EV4를 그대로 쓴다
as_of: 2026-10-19
consumers: docs/claude/rrec-ev4-remove-builder-prompt.md · docs/claude/rrec-ev4-remove-judge-prompt.md · 관제판 rrec-ev4-remove · (병합 뒤 Cowork) recovery-gate-R-REC1-2026-10-09.md 1절 · 통합 점검 규칙 파일 102행(v3.12.8) · CLAUDE.md R-REC1 줄 · gate-rule-epochs.json · t2-rc-preregistration-2026-10-14.md 변경 기록
order_authority: false
quantity_authority: none
---

# R-REC1 EV4(계좌 총액 조건) 제거 — 결정 기록 (2026-10-19)

## 결정

- R-REC1 사건 목록에서 **EV4(계좌 총액 ≤ V6 1차 선 $25,626.55 또는 ≤ S7 HWM × 0.9)를 뺀다.** 남는 사건: EV1·EV2·EV3(ⓐ·ⓑ)·EV5. RG1~RG4·DS1·C0·L0·닫힘·RG1 훼손 규칙은 그대로.
- 계좌 하락 위험은 S7 점검선이 맡는다(`stock-strategy-system/alert_policy.json` 824~835행: L2 이하 신규·추가 매수 멈춤, 해제 = 일지 검토 + 사용자 확인, 선당 하락 구간 1회, 새 HWM에서 재무장). S7·노출 한도(N < 1.85)·종목 상한·매수 요건 ①~④·주문 단계는 바꾸지 않는다.
- 성격: 매수 관문 **완화**(이 변경의 유일한 완화 경로). 매도·예산·노출 한도·주문 권한은 바뀌지 않는다.

## 근거 (2026-10-19 Cowork 세션에서 연 원문)

| 주장 | 원문 |
|---|---|
| EV4는 "총액이 선 아래인 상태"라 그동안 매일 사건이 되고, 가장 최근 사건이 기준이라 RG1(2세션)·RG3(2종가)·시간 소멸(20세션)을 채울 수 없다 | `auto_core_rules.py` 724~731행(`ev4_open`)·894~895행·`event = events[-1]` · `auto_core_decide.py` 1084~1090행 · 규칙 문서 31행 "새 이벤트가 오면 기준점을 새로 잡는다" |
| 승인 정책과 세 군데 충돌: L1은 매수 멈춤 없음, 선당 하락 구간 1회, 해제 = 일지 검토 | `alert_policy.json` 825·830·834행. 10/19 L1·L2 검토 완료(`decision_journal.json` 순번 9·12) 뒤에도 EV4는 그대로(`ev4_open`은 일지를 읽지 않음, `auto_core_decide.py` 1085행) |
| 시간 소멸 없음: 1.55배 대리 계좌가 SOX 1994~2026 세션의 87%(7,126/8,155)에서 EV4 상태, 대부분 2000-03~2021-01 한 번의 하락 | `rrec-ev4-anchor-preregistration-2026-10-18.md` 26행 · 결과 JSON `diagnostics.structure.P1_L1.55` |
| 현금 역효과: 10/16 총액 $23,695.43, 현금 $12,469.19 → EV4가 꺼지려면 총액 +20.45%, 보유분 +43.2%(선 $28,540.58 = HWM $31,711.76 × 0.9) | `workspace/outputs/auto-core/2026-10-17/reconcile.json` · S7 검토 `exposure-review/2026-10-16/portfolio-exposure-review.20261019T083103402766Z.json` `review_lines` |
| 필요성 증거 없음: 지금과 같은 상태(L2 뒤·멈춤 없음) 진단에서 EV4를 첫 닿음만 세면 120세션 결과 +8.5%p(SOX 16개, 후보 5종 71개), 후보 5종 전체 303개에서 하위 10% 역행 −38.5% → −33.7%. 꼬리를 줄인 경우는 SOX 16개(산 뒤 역행 1.6%p)뿐 | `stock-strategy-system/backtests/rrec_ev4_anchor_replay_2026-10-18_results.json` `diagnostics.D5` |
| 10/18 NO_CHANGE의 성격: 사전 기준은 "충격 다음 날 매수 대비"였고 현행(V0)도 미달. 주 판정은 S7 멈춤이 새 고점까지 안 풀린다고 가정했고 L2 이후 앵커를 뺐다 — 오늘 검토로 멈춤이 풀린 지금 상태는 주 판정 밖 | `rrec-ev4-anchor-replay-results-2026-10-18.md` 6절 85행 · 사전 등록 117·185행 |
| EV4 없는 관문(= r3 V0)의 기록: 충격 다음 날 매수 대비 SOX 1994~2010 역행 +0.97·수익 +0.28·꼬리 +1.14%p, 후보 5종 +0.26·−1.19·+0.82%p(채택 기준 +2.0 미달 — 관문 전체 문제, EV4와 무관) | `r-rec1-r3-replay-results-2026-10-16.md` 1절 · 사전 등록 27행(r3 V0 = `ev4_sessions=[]`) |
| EV4 정의의 출처: 규칙 문서는 "L1 열림(기존 S5 R4)", 운영 코드는 승인된 T2 지시문의 상태 정의 → 바꾸려면 K3 | `recovery-gate-R-REC1-2026-10-09.md` 26행 · `redesign-t2-builder-prompt-2026-10-10.md` 448행 |

## 위험과 대응

| 위험 | 대응 |
|---|---|
| 반도체 지수 밖 손실(MVLL·NBIS)로 계좌가 빠져도 L3 전까지 매수를 막지 않음 | S7 L3(지금 −6.32% 남음)에서 다시 멈춤 + 검토. 종목별 EV5·RG2(종목 EMA50)·노출 한도는 그대로 |
| 3배 SOXL 기준 검증 없음(확인 필요) | 첫 매수는 기존 첫 진입 ½ 규칙·세션당 1회·비교 모드("켜" 전 주문 입력 없음) 그대로 |
| 10/18 D2: 일찍 산 경우 상당수가 뒤에 L2까지 내려감(대리 계좌) | L2 도달 시 S7 멈춤이 다시 막음(검토 전까지) |
| 병합과 통합 점검 규칙 파일 교체 사이에 RREC:open 비교 차이(B7) | 병합 직후 같은 세션에서 규칙 파일 v3.12.8 교체(ev-rg1-hyper와 같은 방식) |

## 기본 처분

- Judge FAIL이 고쳐지지 않거나 병합 승인이 없으면 현행 유지(EV4 그대로). 결정 자체는 기록으로 남는다.
- 이 결정은 노출·예산·권한을 올리지 않는다. 매도는 어느 경우에도 막지 않는다.

## 바뀔 조건

- 3배·실제 현금 비중 계좌 리플레이(새 사전 등록)에서 매일 EV4가 꼬리를 2%p 넘게 줄이는 결과.
- 반도체 밖 손실 뒤 더 깊은 하락이 실제 계좌에서 생긴 사례(실제 계좌 이력 — 사전 등록 6절 86행).

## 사용자 손

- 일상 0회. 일회성: Builder 시작 1 · Judge 시작 1 · 병합 승인 1줄 · 병합 스크립트 1번.

## 결정 기록

- 2026-10-19 17:45 KST 사용자 원문 "결정 rrec-ev4: REMOVE" — 같은 대화 17:40 질문 "R-REC1 검토 조건이 과도하지 않은지 검토. 특히, 계좌 총액 검토조건이 꼭 필요한가?"에 대한 Cowork 검토(선택지 NO_CHANGE · REMOVE · REUSE · SIMPLIFY, 권장 REMOVE) 뒤.

## 진행 기록

- 2026-10-19 19:2x KST Builder 완료(READY_FOR_JUDGE, `.claude/worktrees/rrec-ev4-remove`, 커밋 없음). Builder 세션에서 사용자가 범위 밖 3건을 승인했다: 원문 "3건 모두 진행 (권장)".
- 2026-10-19 20:2x KST 독립 Judge **PASS**(docs/claude/rrec-ev4-remove-judge-report.md). 확인 결과:
  - 코어·계산기 동치: 글자까지 같음(400/400, 391/391), decide 22/22
  - S7 대체 장치: L2 멈춤 → 검토 뒤 풀림 → L3에서 다시 멈춤을 합성 실행으로 확인
  - 새 계산기 고정값 6a74f813…9d64
- Judge 기록: 이 변경은 "대부분 완화"이고 단조 완화는 아니다. EV4가 가리던 이전 사건의 연구 기록 공백이 드러나면 RG1이 unk가 된다(매수 쪽으로 더 막음, 코어 2건·계산기 11건 / 합성 입력).
- 2026-10-19 20:38 KST 사용자 승인 원문 "결정 rrec-ev4-remove 병합: 승인" — 아래 '병합 승인 범위' 1~6 전체.

## 병합 승인 범위 (사용자 승인 1줄 `결정 rrec-ev4-remove 병합: 승인`이 덮는 것)

1. 병합 스크립트 `docs/claude/rrec-ev4-remove-merge-2026-10-19.ps1` 1번 실행. worktree 20개 경로를 Judge가 잰 sha256 그대로 커밋하고 `--no-ff`로 병합한다. 계산기와 실행기 고정값은 한 커밋으로 함께 바뀐다.
2. 같은 세션에서 Cowork가 통합 점검 예약 지시문을 로더 v3.12.8-L+R2로 교체(재서명)한다.
   - 초안: `scheduled-prompts/pending-rrec-ev4/integrated-check-daily.txt`, sha256 91c1e762…ff9b
   - 규칙 파일: v3.12.8 `docs/claude/integrated-check-prompt-v3.12.8-2026-10-19.txt`, LF sha256 f5e4b9c8…3540 — v3.12.7과 다른 곳은 1행 머리말, 102행 EV4 구절 삭제 둘뿐
   - 로더에서 바뀌는 것: 규칙 파일 경로·해시·writer 문자열·머리말뿐
3. 문서 반영(Cowork):
   - recovery-gate-R-REC1-2026-10-09.md 1절 EV4 행 삭제 + 적용 메모
   - gate-rule-epochs.json `GATE:REQ5_RREC1` 1줄
   - t2-rc-preregistration-2026-10-14.md 변경 기록 1줄: 계산기 6a74f813… · 실행기 593a067a… · 로더 91c1e762… · 규칙 파일 f5e4b9c8…, **C1은 병합 뒤 첫 decide 세션부터 0/10, 병합 전 C2 일치는 세지 않음**(Judge 권고, ev-rg1-hyper 선례와 같음)
   - scheduled-prompts/README.md 표·변경 기록
   - CLAUDE.md R-REC1 줄에서 "account line L1," 삭제(사용자 커밋)
4. 그대로 두는 것(Judge 비차단 N1·N2): `auto_core_decide.py` 638행 공백 1칸, `auto_core_tickets.py:157`·`portfolio_exposure.py:741` 주석. 각 파일을 다음에 고칠 때 정리한다.
5. 병합 시각: 화~토 06:00~09:00 KST·매일 23:20~23:45 KST 밖. 스크립트가 시각을 확인하고, 실행 중인 예약 작업이 있으면 멈춘다.
6. 기본 처분: 승인이 없으면 병합하지 않는다(EV4 유지). 병합 뒤 점검(RRECEV4_POSTCHECK_FAILED)이 실패해도 병합은 남는다. 이때 Cowork가 원인을 확인하고, 되돌리기는 사용자 결정으로만 한다.
