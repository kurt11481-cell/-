---
id: panw-k3-proposal-2026-11-28
type: proposal (K3 — 상품 승인 · 상품 등록부)
status: "수정안 — 착수 전. 이 문서로 정책·등록부·코드·예약·주문은 바뀌지 않는다"
as_of: 2026-11-28 15시대 KST
trigger: "사장 직접 입력 2026-11-28 15:17:27 KST 'PANW 신규 매수 상품 승인(K3) 진행해, 권한 자리는 cal-2027보다 먼저'(스레드 '사이버 보안 주도주 후보 미리 찾기', cmsg_0137MRzn9nuDvvQmVxm6WeX99ad5Lk4wLbMHAx675fdWpD, from=human trust=principal)"
authority: "order_authority=false · quantity_authority=none. 숫자·한도 변경 없음"
default_disposition: NO_CHANGE
conflicts_first_line: "부딪히는 결정: 권한 자리 순번 policy-a-first-1126(정책 묶음 A → cal-2027) — 사장이 15:17 입력으로 PANW를 cal-2027 앞에 둠 · 동시 권한 작업 1건(CLAUDE.md 140행) — 묶음 A는 26d5a79(11/28 14:44 KST) 병합, 12/1 07:45 코어 확인 남음 · swing-k3-1120(PLTR·CRWD 승인, 3815698) 선례"
---

# PANW 신규 매수 상품 승인 — K3 수정안

## 0. 결론 (먼저)

- **범위: PANW 한 종목.** swing-k3(PLTR·CRWD, 11/20)와 같은 네 곳을 고친다. 코드 승인 목록, 원본 상품 등록부 신원, 정책 배수·카드 핵심 목록, 병합 뒤 통합 점검 승인 목록이다.
- **NTSK는 넣지 않는다.** 카드가 수락되지 않았다(12/02 실적 뒤 다시 씀).
- **권장 순서: 12/1(화) 09:00 KST 뒤 하루에 끝낸다.** 묶음 A의 07:45 코어 확인 → 사장 착수 확인(그날) → Builder·Judge → 그날 날짜 병합 스크립트 → 사장 PowerShell. 효력일은 어느 쪽이든 12/1 이후 첫 코어다. 지금 Builder를 돌리면 3일 사이 main에 docs 밖 변경(묶음 A 보정 등)이 생길 때 병합 스크립트가 멈춰(policy-a-merge-2026-11-28.ps1 117~119행 방식) Builder·Judge를 다시 해야 한다. swing-k3는 하루에 끝났다. 12/1에 하면 오늘 23:30 커밋(PANW 카드·등록부)이 기준 커밋에 들어가 착수 조건 확인도 worktree에서 된다.
- 다른 선택지: 오늘 Builder·Judge(묶음 A를 병합으로 자리가 빈 것으로 봄 — 사장 판단) → 12/1 병합. 위 재작업 위험이 있다.
- **승인돼도 당장 주문은 없다.** 공통 관문 R-REC1(RG1~RG4)이 11/28 코어 기준 모든 매수를 막는다(그 뒤는 확인 필요). 요건 ①③④⑤를 다 통과해도 그날 새 단서(새 공식 강 근거, 또는 새 가격 묶음 2개 이상)가 있어야 주문표가 열린다(auto_core_tickets.py 817행). 단계 상한은 1/2(카드 근거 약 2종 — 테제·이벤트 반응). 12/04 갱신에서 이벤트 반응이 빠지거나 −가 되면 약 1종이라 ③도 막힌다. 종가 이력은 관심 명단 구성원이라 K3와 무관하게 코어가 첫 수집 때 최대 150일을 받는다(auto_core.py 64~67·137~139행) — 그것으로 PA 트리거가 모두 계산되는지는 확인 필요.

```
사장 15:17 직접 입력(범위·순번) → 이 수정안
   ↓ 12/1 07:45 코어 확인(묶음 A) — 이상 있으면 NO_CHANGE
   ↓ 12/1 09:00 뒤 사장 착수 확인(그날, 이 수정안을 가리키는 카드 또는 직접 입력)
Builder(worktree, 수동 경로) → 별도 읽기 전용 Judge
   ↓ 사장 병합 지시(그날)
사장 PowerShell 병합 스크립트 1줄(12/01 날짜 한정, 화~토 05:45~09:00·23:05~23:45 KST 막힘)
   ↓
통합 점검 승인 목록 1줄 → `예약 작업 변경 승인: 보유·관심 종목 통합 점검`
```

## 1. 지금 상태 (원문 확인, 2026-11-28)

| 무엇 | 지금 | 원문 |
|---|---|---|
| 승인 상품(코드) | BE·MU·NBIS·DELL·AMD·SOXL·TQQQ·DRAM·PWR·LITE·PLTR·CRWD | auto_core_tickets.py 61행 |
| 정책 배수 | PANW 없음(PLTR·CRWD 1) | alert_policy.json portfolio_exposure_policy.nominal_multipliers |
| 카드 핵심 | BE·MU·NBIS·DELL·AMD·PWR·LITE·PLTR·CRWD · add_default card_add_stock_only(묶음 A) | 같은 곳 card_stock_core |
| 원본 상품 등록부 PANW | 있음, identity_status user_supplied_pending_primary_verification · leverage_factor_status provisional · watchlist_approved false · candidate_status inactive · portfolio_bucket historical_research_registry | workspace/policies/instrument_registry.json |
| PANW 매수 준비 | 관심 명단 편입(11/28 14:50)·카드 v1 수락(15:08:45)·card-evidence-registry 등록·M6 11/28판·실적 기준표 — 모두 23:30 커밋 대기 | cyber-lead-candidates-2026-11-28.md 10·11절 |
| 권한 자리 | 묶음 A 병합 끝(26d5a79), 12/1 07:45 코어 확인 남음. 다음 순번은 원래 cal-2027(Nasdaq 2027 공지 대기) | active-decisions policy-a-first-1126 · 관제판 policy-bundle-a |

## 2. 바꿀 것 (Builder 지시문 panw-k3-builder-prompt.md)

1. auto_core_tickets.py 61행 APPROVED_BUY 끝에 "PANW"(주석에 사장 입력 날짜).
2. instrument_registry.json PANW 항목을 CRWD 항목 형식으로 verified(SEC 10-K 2026-09-10 원문 — 법인명·증권 종류·거래소). new_buy_instrument_approved는 false 유지. 다른 필드는 CRWD 판정(swing-k3 보고 소비자 표)과 같은 기준. registry_version은 바꾸지 않는다(swing-k3 BLOCKED 2번 선례 — 픽스처가 고정, 추적은 required_canonical_sha256).
3. alert_policy.json: required_canonical_sha256 다시 계산, nominal_multipliers에 "PANW": 1(QQQ 앞), card_stock_core 끝에 PANW.
4. 새 테스트 test_panw_k3_registration.py, 값을 고정한 기존 테스트 두 곳만 조정: test_swing_k3_registration.py 83·107행 기대값과 148·149행 대조 기호(PANW → 승인 밖·미검증 기호로), test_portfolio_exposure.py 105~107·112행.

## 3. 바뀌지 않는 것

주문 권한 · 노출 한도 1.9·1.85·1.55·한 종목 0.4 · 3배 상한(묶음 A) · 매수 요건 ①~⑤ · R-REC1 · 관심 명단 규칙 · 다른 종목 등록부 항목.

## 4. 위험과 되돌리기

- 새로 열리는 행동: ① card_stock_core — 새 단서 매수 제안의 NOT_AN_S5_NEW_BUY_INSTRUMENT 막힘 해제와 실적 금지 구간 판정(portfolio_exposure.py 1253·1258행), 매도 후회 다리의 재배치 순위 후보(auto_core_decide.py 1191·1268~1280행) ② APPROVED_BUY — 코어 알림 '매수 근거 후보 충족(신규) PANW'와 과매도 경보 C1+/C2+(auto_core_decide.py 342~344·377~380행). 묶음 A의 S7 채우기(카드 ADD만, portfolio_exposure.py 1507~1509·1539~1541행)는 PANW 카드가 WATCH라 대상이 아니다. 코어 밖(통합 점검)에서 카드를 넘기는 길이 있는지는 확인 필요.
- 사이버 몫 집중: 관심 명단에 PANW·NTSK(상관 0.82). 승인은 PANW만이라 실제 매수 후보는 하나.
- 되돌리기: 목록·배수·카드 핵심에서 빼면 끝(보유 전이면 영향 없음). 등록부 신원 기록은 남겨도 해가 없다.

## 5. 연결표 (analysis-linkage-map-2026-10-05.md 1절 8번)

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| APPROVED_BUY(PANW) | Builder → 사장 PowerShell 병합 | auto_core_tickets.py 61·264행 → 코어 매수 주문표 | 요건 ①③④⑤ 통과 날 PANW 매수 주문표 | 새 테스트 · 코어 result.json | 연결(병합 뒤) |
| 정책 배수·card_stock_core | 같음 | portfolio_exposure.py 1253·1258행 · auto_core_decide.py 1191·1268~1280행 | E 계산 1배 · 새 단서 매수 제안 자격 · 실적 금지 구간 · 재배치 순위 후보 | 06:15 노출 검토 | 연결(병합 뒤) |
| 등록부 PANW 신원 | 같음 | reconcile_broker_state.py 108~122행 · validate_registry_consistency.py 38행 | PANW를 사면 대조가 신원을 알아봄 | 06:15 코어 warnings | 연결(병합 뒤) |
| 통합 점검 승인 목록 | 병합 뒤 예약 작업 변경 | 통합 점검 규칙 매수 요건 ② 목록 행 | '상품 승인 없음' 막힘 풀림 | 통합 점검 자기 검사·코어와 ② 비교 | 끊김 — 메울 변경: 규칙 1줄 + 시험 + 독립 검토 · 승인 경로: 사장 직접 입력 `예약 작업 변경 승인: 보유·관심 종목 통합 점검` |
| 이 수정안 | 이 스레드 | 사장 착수 확인 | Builder 착수 | 관제판 | 끊김 — 사장 확인 대기 |

## 6. 사장 결정

- 2026-11-28 15:17:27 KST 사장 직접 입력(범위 PANW·순번 cal-2027 앞). 착수 확인은 이 수정안 뒤에 따로 받는다(CLAUDE.md 'one approval covers only the immediately preceding proposal').
- 2026-11-28 15:20:59 KST 사장 결정 카드 'NTSK도 이번 상품 승인(K3)에 함께 넣을까요?' → 'PANW만 (권장)'(cmsg_0137MRzn9nuDvvQmVxm6WeX9Xe7BHTx53gUs7B9UsGtrzL, 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH) — NTSK는 12/02 실적 뒤 카드 수락 시 다음 권한 순번에 따로.

## 검토 기록

- 2026-11-28 작성(Opus). 독립 검토(Fable, 15시대 KST): 조언 8건 — 결론 바뀜 1(권장 순서: 지금 Builder → 12/1 하루에) · 정정 7(swing-k3 테스트 148·149행, registry_version 유지, 병합 시간 창·같은 날 승인, '채우기 대상' 삭제·새 행동 3가지, 새 단서 조건·150일 수집, 착수 조건은 메인 트리 또는 커밋 뒤, 테스트 패턴 보강) · 미반영 0(작업자 약 224k 토큰·6분).
