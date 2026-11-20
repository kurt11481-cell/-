---
id: swing-product-approval-k3-2026-11-20
type: proposal (K3 — 상품 승인 · 상품 등록부)
status: 범위 결정(2026-11-20 15:39:42 KST 사장 카드 'PLTR·CRWD+등록부 정리'). 착수 전. 이 문서로 정책·등록부·코드·예약·주문은 바뀌지 않는다
as_of: 2026-11-20 15시대 KST
parent: "masterplan-recovery-amendment-2026-11-19.md 12-5·12-6 · swing-live-path-proposal-2026-11-19.md 4절 · pick-redesign-design-2026-11-19.md 8절 · pick-skill-registration-agenda-2026-11-19.md 4절(안건 ④)"
trigger: "사장 직접 입력 2026-11-20 15:21 KST '스윙종목 승인 확대 진행해줘.'(사장실 스레드 '스윙 종목 상품 승인 넓히기')"
authority: "order_authority=false · quantity_authority=none. 숫자·한도는 정하지 않음(선택지만). 정책 파일 쓰기·apply 없음"
default_disposition: NO_CHANGE
conflicts_first_line: "부딪히는 결정: S7 승인 ⑤(active-decisions.md 194행 — 신규 매수 상품 8개) · 상품 승인 PWR·LITE(106행) · pltr-card-q3 '하지 않음: 상품 승인(별도 권한·한도 변경)'(136행 — 이 안이 그 별도 경로) · 권한 자리 1건·순번 cal-2027 → 정책 묶음 A(144행 qqq-first-1109 · 129행 k3-queue-check) · postapply-d4 '하지 않음: instrument_registry.json 수정'(140행 — 그때 범위 밖이었을 뿐, 이 안이 사장 승인으로 여는 것) · pick-redesign-1119 '하지 않음: 상품 승인 변경'(161행 — P2 초안은 'K3 묶음이 이 판정을 따름') · masterplan-recovery-1119 '하지 않음: 상품 승인 변경'(160행 — 설계 방향 단계의 금지, 사장 15:21 지시로 이 안건을 엶)"
---

# 스윙 종목 상품 승인 넓히기 — K3 수정안

## 0. 결론 (먼저)

- **권장: 1차 = PLTR·CRWD를 사장이 직접 승인(PWR·LITE 10/08 선례처럼 등록 후보 관문 J1~J4 없이, CRWD는 카드 수락 뒤에만).** 장비 3·소프트웨어 3(AMAT·LRCX·KLAC·NOW·SNOW·DDOG)은 2차로 미룬다.
- **따로 묻는 것: 상품 등록부 정리(이미 승인됐는데 등록부에 없는 6종목 LITE·PWR·MU·DELL·AMD·TQQQ의 신원 기록)를 같은 개발 1건에 묶을지.** 권장은 묶기. 사장 지시는 승인 확대뿐이고 11/05 결정(140행)이 등록부 수정을 범위 밖으로 둔 만큼 사장이 정한다.
- 까닭: 승인을 받아도 실제로 사려면 **카드 수락 · 실적일 표 · 매수 요건 행 · 종가 이력**이 모두 있어야 한다. PLTR은 넷 다 있고(행은 관심 명단에 있는 동안만, 카드 판단은 WATCH·확신 낮음), CRWD는 카드만 없다. 6종목은 넷 다 없어 지금 승인하면 '이름만 승인'이다.
- 등록부를 묶는 까닭: 11/06부터 매일 나오는 경고 `LITE: canonical instrument registry record is missing or unverified`의 원인이 **원본 상품 등록부에 LITE 기록이 아예 없는 것**이다. PLTR·CRWD를 넣으려면 같은 파일과 정책의 등록부 해시를 어차피 고쳐야 한다(QQQ 선례 2b9afc9).
- 승인돼도 **당장 주문은 없다.** 하드 상한 띠는 풀렸지만(11/20 09:26 재계산 WITHIN_BAND) 새 매수 멈춤이 남아 있다(검토선 상태 없음·신고 안 된 현금 흐름 등 fail-closed 사유, R-REC1). 멈춤이 풀린 뒤 첫 신호부터 쓰인다.

```
사장 카드(범위)
   ↓
CRWD 카드 수락(따로 카드, 권장안일 때만)
   ↓
권한 자리 차례 → Builder(worktree) → 독립 Judge → 사장 PowerShell 병합
   ↓
통합 점검 매수 요건 ② 목록 1줄 → `예약 작업 변경 승인: 보유·관심 종목 통합 점검`
   ↓
스윙 실전 대상에 PLTR(·CRWD) 추가 — 다음 날 코어·통합 점검부터
```

## 1. 지금 상태 (원문 확인, 2026-11-20)

| 무엇 | 지금 | 원문 |
|---|---|---|
| 승인 상품(코드) | BE·MU·NBIS·DELL·AMD·SOXL·TQQQ·DRAM·PWR·LITE | auto_core_tickets.py 61행 `APPROVED_BUY` |
| 승인 상품(통합 점검) | 같은 10개, 없으면 "막힘 — 상품 승인 없음" | integrated-check-prompt-v3.12.18 134행 |
| 정책 배수·카드 핵심 | PWR·LITE·MU·DELL·AMD 배수 1, card_stock_core 7종목 | alert_policy.json portfolio_exposure_policy |
| **원본 상품 등록부** | 21종목. **승인 상품 중 LITE·PWR·MU·DELL·AMD·TQQQ 기록 없음**. PLTR·CRWD는 있으나 신원 미검증·watchlist_approved=false·candidate_status=inactive·leverage_factor_status=provisional. 모든 종목 `new_buy_instrument_approved=false`(승인은 코드·지시문 목록으로 운영) | workspace/policies/instrument_registry.json · product-approval-PWR-LITE-2026-10-08.md 5절 '④ S7 2단계 대기' |
| 정책이 요구하는 등록부 해시 | 등록부를 고치면 alert_policy의 `required_canonical_sha256`도 같이 고쳐야 함(어긋나면 실행 검토 fail_closed) | alert_policy.json decision_harness.instrument_registry_authority · validate_registry_consistency.py 38행 |
| LITE 경고 | 11/06부터 매일 `POST_APPLY_ALERT_ENGINE_CHECK_FAILED` + `LITE: … missing or unverified`. 판정·주문표 영향 없음(표시) | workspace/outputs/auto-core/2026-11-06~11-20 result.json · reconcile_broker_state.py 108~122행 · postapply-d4-report.md 81행 "LITE 줄을 없애려면 원본 등록부에 LITE 신원 기록 필요(사장 승인 사항)" |
| 권한 자리 | 한 번에 1건. 순번 cal-2027(기한 12/15, Nasdaq 공지 대기) → 정책 묶음 A. swing-bars는 11/20 병합(af40710)으로 끝남 | CLAUDE.md 136행 · active-decisions.md 129·144행 |
| 새 매수 멈춤 | 띠 WITHIN_BAND·block_all_new_buys false, 그러나 new_buy·add 멈춤(FAIL_CLOSED: 노출·자본 값 없음 · HWM 선·멈춤 상태 없음 · 신고 안 된 현금 흐름) | workspace/outputs/auto-core/2026-11-20/s7-rerun-0926 portfolio-exposure-review |

## 2. 종목별 표 — 승인하면 바로 쓸 수 있나

| 종목 | 뿌리 | 카드 | 실적일 표(①) | 매수 요건 행 | 종가 이력(코어) | 등록부 신원 | 유동성·키움 거래 가능 | 판단 |
|---|---|---|---|---|---|---|---|---|
| PLTR | AI 소프트웨어 | **수락** v2(11/04) | 있음 | 있음(관심 members) | 141세션 연속 | 미검증(SEC 확인 필요) | 시총 큼(관심 명단 값 $428B, 10월 기준) · 키움 확인 필요 | **승인 뒤 매수 요건 판정 대상**(행은 관심 명단에 있는 동안만, 카드 WATCH) |
| CRWD | 사이버보안 | **초안·미수락**(11/14) | 있음 | 있음(관심 members) | 112세션 연속 · 07/02 4:1 분할 전 값 섞임(분할 반영 확인 필요) | 미검증 | 키움 확인 필요 | 카드 수락 뒤 가능 |
| AMAT | 반도체 장비 | 없음 | 없음 | 없음 | 0(swing-bars 첫 수집 11/21 06:15 예정 — 확인 필요) | 기록 없음 | 확인 필요 | 2차 |
| LRCX | 반도체 장비 | 없음 | 없음 | 없음 | 0(같음) | 기록 없음 | 확인 필요 | 2차 |
| KLAC | 반도체 장비 | 없음 | 없음 | 없음 | 0(같음) | 기록 없음 | 확인 필요 | 2차 |
| NOW | 소프트웨어 | 없음 | 없음 | 없음 | 0(같음) | **검증됨**(SEC 10-K) | 확인 필요 | 2차 |
| SNOW | 소프트웨어 | 없음 | 없음 | 없음 | 0(같음) | 미검증 | 확인 필요 | 2차 |
| DDOG | 소프트웨어 | 없음 | 없음 | 없음 | 0(같음) | 미검증 | 확인 필요 | 2차 |

- 실적일 표가 없으면 매수 요건 ①이 늘 막힌다(earnings-anchors.json maintenance 줄). 행이 없으면 재량 주문 대상도 아니다(swing-live-path 8절 '상품 승인·매수 요건 행이 있는 종목만').
- 6종목에 행을 주는 길은 P2 '행 대상 넓힘'(안 X, 사전 등록 초안 3판, **고정 전**) 또는 관심 명단 편입이다. 둘 다 이 K3 밖이다.
- 유동성·키움 거래 가능 여부는 이 스레드에서 키움을 조회하지 않아 모두 **확인 필요**다(조회는 사장이 이 스레드에 직접 요청할 때만, 지침 1절). Builder 단계에서 공식 신원(SEC)과 함께 확인한다.

## 3. 선택지 비교

| | A. PLTR·CRWD 직접 승인 (권장) | B. PLTR만 직접 승인 | C. 8종목 전부 | D. 승인은 P2 관문 고정 뒤(등록 후보로 올라온 종목부터) |
|---|---|---|---|---|
| 등록 후보 관문 J1~J4 | 건너뜀 — PWR·LITE 10/08 선례처럼 사장 직접 승인. 원래 계획(swing-live-path 85행 '관문 통과 후보부터')보다 앞섬 | 같음 | 같음 | 따름(P2 초안 J1·J2 문턱 미고정 — 고정 시기 확인 필요) |
| 매수 요건 판정에 들어가는 종목 | PLTR(CRWD는 카드 수락 뒤) | PLTR | PLTR(나머지는 카드·실적표·행 뒤) | 없음(관문 고정 전) |
| 뿌리 분산 | AI 반도체·인프라 밖 2뿌리(소프트웨어·보안) | 1뿌리 | 4뿌리 | 그대로 |
| 일의 양 | 등록부 2종목(묶으면 +6) + 코드·지시문 1줄 | 1종목(묶으면 +6) + 1줄 | 13종목 + 카드 6장·실적표 6줄·행 대상 변경(P2) | P2 고정·관문 판정 뒤 |
| 위험 | CRWD 분할 이력·카드 미수락 / 종목 수 늘어 '더 좋은 후보' 매도 압박(E1 원칙 지켜야) | 같은 위험 작음 | '이름만 승인'이 6개 — 그림자 판정 전에 실전 길만 넓어짐 | 실전 몫이 한동안 승인 종목(거의 한 뿌리)에 묶임 |
| 그림자 장부와 관계 | 모집단 7종목 안(이미 고정) | 같음 | 6종목은 11/20 넓힌 모집단(판정 전) | 같음 |
| 기본 처분 | — | — | — | (답 없으면 NO_CHANGE = 지금 그대로) |

- C를 권하지 않는 이유: 6종목은 사려면 필요한 준비 4가지(카드·실적표·행·이력)가 하나도 없고, 넓히기 제안이 '실전은 상품 승인 K3로 따로'라고 정해 두었다(swing-widen-proposal 27행). 준비가 생긴 뒤 2차로 올린다.
- B 대신 A를 권하는 이유: CRWD는 사장이 10/17에 'AI 밖 뿌리 비교' 몫으로 넣은 종목이고 행·실적표·이력이 이미 있다. 남은 것은 카드 수락 하나다.
- D 대신 A를 권하는 이유: 사장이 오늘 '진행'을 지시했고, PLTR·CRWD는 J1(공식 실적 근거)·J4(카드 kill을 공식 자료로)를 이미 카드로 거쳤다. J2·J3(QQQ 대비 손해 하한·계좌 적합)는 문턱이 고정되지 않아 지금 적용할 수 없다 — 이 점을 알고 건너뛰는 것이다.

## 4. A안을 고르면 할 일 (K3 수동 경로, PWR·LITE·QQQ 선례)

| 순서 | 할 일 | 주체 | 승인 |
|---|---|---|---|
| ① | 사장 결정을 이 문서 7절과 active-decisions.md에 기록 | 이 스레드 | 이 카드 |
| ② | CRWD 카드 v0 → v1(공식 8-K로 다시 씀) 수락 카드 | 카드 스레드 | 사장 카드 |
| ③ | 개발 지시문(authority): `instrument_registry.json`에 (등록부 묶기를 고르면) LITE·PWR·MU·DELL·AMD·TQQQ 신원(SEC·운용사 공식 출처) + PLTR·CRWD 신원을 verified로. 필드: `new_buy_instrument_approved`는 **지금처럼 전 종목 false 유지**(승인은 코드·지시문 목록으로 운영 — true로 바꾸면 validate_decision_record.py 278행 관문이 달라져 따로 K3), PLTR·CRWD의 watchlist_approved·candidate_status·leverage_factor_status 값은 지시문에서 정하고 Judge가 확인 + alert_policy.json 등록부 해시(정책 사본 instrument_registry는 건드리지 않음) · nominal_multipliers에 PLTR·CRWD 1 · card_stock_core에 PLTR·CRWD · `APPROVED_BUY`에 PLTR·CRWD · 시험(LITE 경고가 사라지는지, 승인 밖 종목은 그대로 막히는지) | Builder(worktree, 수동 경로 — 정책·등록부는 개발 큐 보호 경로) → 독립 Judge | 착수 = 사장 카드, 병합 = 사장 PowerShell 병합 스크립트 · 초안 swing-k3-builder-prompt.md |
| ④ | 통합 점검 134행 목록 1줄에 `PLTR·CRWD(2026-11-xx 사장 승인)` 추가 + H1 시험 + 독립 검토 | 이 프로젝트 | 사장 직접 입력 `예약 작업 변경 승인: 보유·관심 종목 통합 점검` |
| ⑤ | 스윙 실전 대상(swing-live-path 8절) 표에 반영, 관제판 swing-1119 갱신 | 이 프로젝트 | 기록 |

- 순번: 권한 자리는 한 번에 1건, 지금 줄은 cal-2027 → 정책 묶음 A다. 이 안은 그 뒤에 선다. 앞당기려면 사장이 순번을 바꾸는 직접 입력이 필요하다(qqq-first-1109 선례).
- (2026-11-20 15:59:32 KST CRWD 카드 v1 수락 — crwd-card-1120, CRWD 포함 확정. 남은 막힘: 07/02 4:1 분할 공식 기록이 corporate-actions.json에 없어 코어가 SPLIT_SUSPECTED로 CRWD 주문표를 막음 — 별도 기록 경로 필요) CRWD 카드가 수락되지 않으면 ③에서 CRWD를 빼고 PLTR만 진행한다(B로 자동 축소).
- 되돌리기: 목록·코드에서 빼면 끝(보유 전이면 영향 없음). 등록부 신원 기록은 남겨도 해가 없다.

## 5. 바뀌지 않는 것

주문 권한(order_authority=false · quantity_authority=none) · 노출 한도 1.9·1.85·1.55·한 종목 0.4 · 매수 요건 ①~⑤ · R-REC1 · S7 멈춤 · 실전 몫 5%·새 현금만 · 그림자 사전 등록(고정값) · 관심 명단 규칙. 후보가 늘어도 '후보 우위는 매도 근거가 아니다'(E1).

## 6. 연결표 (analysis-linkage-map-2026-10-05.md 1절 8번)

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| 상품 승인 목록(코드) | 개발 큐 병합(사장 PowerShell) | auto_core_tickets.py 61행 → 코어 매수 주문표 | PLTR·CRWD 매수 주문표가 나올 수 있음 | 코어 시험·Judge | 연결(병합 뒤) |
| 상품 승인 목록(통합 점검) | 예약 작업 변경 | 통합 점검 134행 ② | 행이 "막힘 — 상품 승인 없음"에서 풀림 → 스윙 재량 주문 대상 | 통합 점검 324행 자기 검사 · H1 | 연결(교체 뒤) |
| 원본 상품 등록부(묶기를 고를 때) | 개발 큐 병합 | reconcile_broker_state.py 108~122행 · validate_registry_consistency.py 38행 | LITE 매일 경고가 사라짐 · 새 종목을 사면 대조가 신원을 알아봄 | 06:15 코어 result.json warnings | 연결(병합 뒤) — **지금 끊김**(LITE 기록 없음, 11/06~) |
| CRWD 카드 수락 | 카드 스레드 | card-evidence-registry.json → 매수 요건 ③ | CRWD 근거 칸이 셈에 들어감 | 통합 점검 '카드 재검토' 줄 | 끊김 — 사장 카드(4절 ②) |
| 이 수정안 | 이 스레드 1회 | 사장 카드 → 권한 자리 순번(143행) | K3 착수 여부 | 관제판 k3-queue-check(12/01 권한 대기열 점검) | 끊김 — 사장 카드(이 문서) |
| 6종목 2차 묶음 | 그림자 판정·P2 고정 뒤 | pick-eligibility-p2 초안 · swing-widen 27행 | 2차 승인 안건 | 관제판 swing-1119 next 칸 | 의도적 보류 — 사장이 A·B·D를 고를 때 C와 나란히 본 결정이 근거 |

## 7. 사장 결정

- 2026-11-20 15:39:42 KST 사장 결정 카드 **'PLTR·CRWD+등록부 정리'**(권장안, cmsg_0137MRzn9nuDvvQmVxm6WeX9MtfKVr9UJDdDuor4zcUGZP). = A안 + 등록부 정리 묶기. 정한 것은 범위뿐 — 착수·병합·통합 점검 목록 변경은 4절 순서대로 각각 따로.
- 다음: ② CRWD 카드 다시 쓰기·수락 카드 → ③ 개발 지시문 초안(권한 자리 차례에 큐 등록 카드).
- **착수 2026-11-20 16:04:53 KST 사장 직접 입력 '지금 착수해줘'**(이 스레드, 메시지 cmsg_0137MRzn9nuDvvQmVxm6WeX9CaqACF7UqZK1cTudyJJMSL, from=human trust=principal, 계정 = 사장) — 바로 앞 제안 = 수동 경로 Builder 지시문 swing-k3-builder-prompt.md 착수. 권한 자리: 진행 중인 권한·한도 작업 없음(관제판 active 3건 모두 일반·K0, 16:0x 확인). cal-2027은 Nasdaq 공지 대기라 이 착수가 먼저 감(사장 직접 지시 — 순번 변경). Builder(worktree) → 별도 읽기 전용 Judge → 병합은 사장 PowerShell(CLAUDE.md 83~98행).

## 결론을 바꿀 조건

- CRWD 카드 수락이 거절되면 B로 줄인다. · PLTR 공식 신원(SEC)이나 키움 거래 가능 확인이 실패하면 그 종목을 뺀다. · P2가 고정되고 6종목 카드·실적표가 생기면 2차 묶음을 올린다. · 권한 자리 순번이 바뀌면 4절 순번을 다시 쓴다.

## 검토 기록

- 2026-11-20 작성(Opus). Fable 조언 1회(high) 8건 중 8건 반영: ① 'S7 하드 상한 멈춤' 낡음 → 띠 풀림·fail-closed 멈춤(s7-rerun-0926 원문 확인) ② 등록부에 없는 승인 상품 6개(TQQQ 포함) ③ active-decisions 줄 번호 106·129·144, 136행 추가 ④ 등록부 필드 값(new_buy_instrument_approved false 유지) ⑤ 등록부 묶기를 사장에게 따로 물음 ⑥ J1~J4 건너뜀을 표·D안으로 드러냄 ⑦ C 반대 이유 교체 ⑧ PLTR '바로 가능' 낮춤. 확인 필요로 남김: 키움 거래 가능·CRWD 분할 반영·validate_decision_record.py 278행 내용(조언 인용, 원문 미대조).
