---
id: qqq-reg-proposal-2026-11-09
title: "QQQ 등록(K3) — 권한 자리 순서 앞당김 + 착수 제안"
date: "2026-11-09"
status: "순서 변경 = 사장 직접 입력으로 확정(1절). 착수(A, 등록부까지) = 사장 결정 카드 2026-11-09 10:30:03 KST(6절). 병합 = 2026-11-09 11:27:38 KST a764e97(6절)"
authority: "order_authority=false · quantity_authority=none · 수량·가격 제안 없음 · 이 문서는 정책·예약·코어를 바꾸지 않는다"
conflicts: "strategy-1101(active-decisions.md strategy-1101 행) '정책 묶음 A는 권한 자리 dst-label·duet-q4-recon·cal-2027 뒤' 순번(strategy-revision-2026-11-01.md 9절 3행) — 이 순번에 QQQ 등록을 cal-2027 앞으로 끼움. t3-proceeds-qqq-1108 4절 ② '권한 자리 차례가 오면' — 차례를 지금으로 당김. t3-proceeds-qqq 4절 ②의 범위 중 등록부(instrument_registry.json)·통합점검 규칙은 이 제안 A에서 빼고 따로 둠(3절)"
---

# QQQ 등록(K3) — 순서 앞당김 + 착수 제안 (2026-11-09)

계좌 금액·수량은 적지 않는다.

## 0. 결론

- 권한 자리 순서: **QQQ 등록(qqq-reg) → cal-2027 → 정책 묶음 A**. dst-label·duet-q4-recon은 이미 끝나 있어서 실제로 앞당겨지는 상대는 cal-2027 하나다.
  - dst-label: dst-label2 병합 9fad610(2026-11-03, 사장 직접 입력 "결정 dst-label2 병합: 승인" 13:51 KST — active-decisions.md dst-label 행).
  - duet-q4-recon: 2026-11-04 08:54 KST 'a 유지(기록만)' — 코드·권한 변경 없음, "권한 자리 다음 = cal-2027"(active-decisions.md duet-q4-recon 행).
- 지금 진행 중인 권한·한도 작업 없음(관제판 tasks 2026-11-09 10:2x KST 조회: k가 권한·한도인 미완 작업은 모두 waiting·planned). 한 번에 1건 규칙(CLAUDE.md Concurrency cap)과 부딪히지 않는다.
- 부딪힐 수 있는 것 1가지: cal-2027 기한 2026-12-15. Nasdaq 2027 공지가 QQQ 작업 도중에 나오면 cal-2027은 QQQ 병합 뒤로 밀린다. QQQ 작업 A는 정책 2줄 + 수집 1줄이라 짧다(수일 예상 — 확인 필요). 12/01 k3-queue-check가 그대로 다시 센다.
- 서머타임 라벨 의존 없음: QQQ 종가 수집은 dst-label2 병합 뒤 판(-05:00 인정)을 그대로 쓴다.

## 1. 순서 변경 기록 (사장 결정)

- 사장 직접 입력 2026-11-09 10:19:23 KST, 사장실 스레드 'QQQ 등록(K3) 먼저 진행'(메시지 cmsg_0137MRzn9nuDvvQmVxm6WeX9X9RiLQv5xaRD9yhwKoVuQb): "dst-label·duet-q4-recon·cal-2027보다 QQQ 등록을 먼저 해줘".
- 근거 규칙: strategy-revision-2026-11-01.md 9절 3행 "순번 변경은 사장 결정".
- 바뀌는 것: 권한 자리 순번 = qqq-reg → cal-2027 → policy-bundle-a. 바뀌지 않는 것: 각 작업의 내용·승인 방식(착수·병합 모두 따로 사장 결정), 한 번에 1건, cal-2027 기한 12/15·기본 처분(미완이면 1/1부터 fail-closed 알림), 정책 묶음 A 범위.

## 2. 착수 제안 A — QQQ를 자동 코어 정책에 등록 (권한·한도, 수동 경로)

### 2-1. 바꿀 것 (REUSE — PWR·LITE 선례 6fdcf90, SPY 수집 선례 bffa588)

| 파일 | 바꿈 | 이유(원문 행) |
|---|---|---|
| stock-strategy-system/alert_policy.json `portfolio_exposure_policy.nominal_multipliers` | `"QQQ": 1` 추가 | 미등록 판정은 이 표만 본다(portfolio_exposure.py:1363~1365 `UNREGISTERED`, alert_policy.json 699행 `unregistered_instrument`). 없으면 QQQ를 드는 순간 E 없음 → 추가·신규 매수 권고 멈춤·반등 줄이기 알림 '확인 불가' |
| 같은 파일 `allowed_index_etfs` | `"QQQ"` 추가 | 매수 후보 자격(portfolio_exposure.py:1211 `NOT_AN_S5_NEW_BUY_INSTRUMENT`, auto_core_decide.py:1137 재배치 후보 집합) |
| workspace/policies/auto_core.json `symbols_extra` | `"QQQ"` 추가 | 사기 전부터 정규장 종가 이력을 쌓음(auto_core.py:348). 처음 수집은 2026-04-01부터(auto_core.py:57·352) — 60세션 최소는 넘고 252세션 전까지 'short_history' 표시(alert_policy.json sox_equivalent) |
| 새 테스트 manage-us-stock-strategy/tests/test_qqq_registration.py | QQQ 보유 가상 상태에서 E 계산·미등록 없음, 매수 자격, 기존 값 불변 | 4절 |

### 2-2. 일부러 뺀 것

- **등록부 instrument_registry.json 정식 등록·정책의 등록부 해시(alert_policy.json 175~181행)**: 코어의 미등록·매수 자격 판정이 이 파일을 쓰지 않는다(위 행). 10/01·10/08 승인한 TQQQ·MU·DELL·AMD·PWR·LITE도 아직 등록부에 없고 S7 2단계 묶음 대기다(product-approval-PWR-LITE-2026-10-08.md 5절 사실 확인 줄). t3-proceeds-qqq 4절 ②는 이것을 넣었으나 SIMPLIFY로 뺀다 — 카드에서 '등록부까지'를 고르면 넣는다.
- **통합점검 규칙(승인 상품 목록·ETF 기준·관문 통과 날 '판 몫 현금 → QQQ' 지시)**: 단계 B(3절). 예약 작업 변경이라 승인 경로가 다르다(지침 4절 ①: 사장 직접 입력 `예약 작업 변경 승인: 보유·관심 종목 통합 점검`).
- **채우기 기본 SOXL(alert_policy.json 750행 add_default)**: 정책 묶음 A 차례(t3-proceeds-qqq 4절 아래 첫 글머리).
- 문턱(E 목표 1.55·상한 1.9·채우기 1.25·줄이기 1.85)·card_stock_core·S7·R-REC1·하락장 매수 a: 그대로.

### 2-3. 이 변경 뒤 달라지는 동작 (병합하면)

- QQQ를 들어도 코어 E가 계산된다(배수 1). 미등록 fail-closed가 풀리는 것은 QQQ 한 종목뿐.
- 코어가 QQQ 매수 주문표를 스스로 내지는 않는다: 매수 대상은 관심 명단 종목(auto_core_decide.py:624~625 universe)이고 QQQ는 관심 명단 밖이다. 판 몫 QQQ 매수 지시는 단계 B 통합점검이 낸다.
- 매도·줄이기 쪽은 바뀌지 않는다. 주문·권한 줄 무변경.

### 2-4. 진행 경로 (CLAUDE.md Change classes · Session hygiene Manual route)

stock-strategy-system/**·workspace/policies/**는 개발 큐가 건드릴 수 없는 보호 경로다(tools/dev_pipeline/authority-paths.txt 8~9행). 그래서 수동 경로:

1. 사장 결정 카드 '착수' (이 스레드, 같은 날 1회 — CLAUDE.md 'Authority/limit change' 카드 조건)
2. 이 스레드가 사장 PC에 Builder(Opus, worktree qqq-reg) Remote Control 세션을 띄움 — 지시문 docs/claude/qqq-reg-builder-prompt.md
3. Builder 종료 뒤 별도 읽기 전용 Judge(Opus) 세션 — docs/claude/qqq-reg-judge-prompt.md, 보고 끝줄 `VERDICT: PASS`
4. 이 스레드가 병합 스크립트(docs/claude/qqq-reg-merge-2026-11-09.ps1, cd-guard 선례)와 병합 결정 카드를 올림
5. 사장 PowerShell 한 줄로 병합 → 다음 06:15 코어에서 QQQ 수집·정책 반영 확인

## 3. 단계 B (A 병합 뒤, 따로 승인)

- 통합점검 규칙 파일: 승인 상품 목록에 QQQ, 카드 매수 근거 표·M6 카드 요건의 ETF 기준(QQQ는 카드가 없음 — strategy-revision 9절 표 아래 둘째 글머리), 'L4·L5 닫힘 + R-REC1 관문 닫힘 + QQQ 등록'인 날 '판 몫 현금 → QQQ'(투영 E ≤ 1.55 확인, 수량은 사장 입력)와 관심 명단·카드 매수 날 'QQQ 매도 → 그 종목' 재원 지시.
- 승인: H1 시험·독립 검토 뒤 사장 직접 입력 `예약 작업 변경 승인: 보유·관심 종목 통합 점검`(지침 4절 ①·④, election-crash-1106 B 선례).
- 관문이 아직 닫히지 않았으므로 B는 급하지 않다. 다만 관문 통과 전에 끝내야 그날 지시가 빠지지 않는다.

## 4. 연결표 (analysis-linkage-map-2026-10-05.md 1절 8번)

| ① 자료·산출 | ② 만드는 주체·시각 | ③ 읽는 점검 — 원문 행 | ④ 바뀌는 행동 — 선 | ⑤ 끊기면 누가 아나 | ⑥ 상태 |
|---|---|---|---|---|---|
| QQQ 배수 1·허용 ETF (alert_policy.json) | 사장 병합(PowerShell) | portfolio_exposure.py:1363·1211, auto_core_decide.py:1137 | QQQ 보유 때 E 계산 유지 → 매수 권고·반등 줄이기 알림 계속 | 코어 fail_closed `UNREGISTERED:QQQ`(portfolio_exposure.py:1365) → 개장 전 점검 '줄이기 확인 불가' 줄 | 연결(병합 뒤) |
| QQQ 정규장 종가 이력 (auto_core.json symbols_extra) | 06:15 자동 코어 auto_core.py:348~353 | workspace/outputs/regular-session-closes/history → portfolio_exposure sox_equivalent | 관문 통과 날 E 투영 준비 | `BAR_COLLECTION_FAILED:QQQ`·`CLOSE_HISTORY_FAILED:QQQ`(auto_core.py:153·174) | 연결(병합 뒤) |
| 판 몫 → QQQ 지시·QQQ 매도 재원 지시 | 통합점검(예약) | 통합점검 규칙 파일 — 아직 없음 | 대시보드 '오늘 키움에 넣을 주문' 칸 | — | **끊김 — 단계 B · 예약 작업 변경 승인(사장 직접 입력)** |
| 채우기 기본 SOXL → (QQQ 등록 뒤) | 정책 | alert_policy.json 750행 | 채우기 권고 상품 | — | **끊김 — 정책 묶음 A(관제판 policy-bundle-a) · 그날 묶음 카드** |
| 등록부 정식 등록 | — | 코어 판정은 읽지 않음(위 ③) | 없음 | — | 끊김(표시) — 카드에서 '등록부까지'면 A에 넣음, 아니면 S7 2단계 묶음과 함께 |

## 5. 하지 않음

- 주문·키움 주문 도구·kiwoom_commands 없음. 승인류 실행·병합·apply 없음(이 스레드는 지시문·기록·RC 띄우기까지).
- 단계 A에서 통합점검·예약·대시보드·문턱·채우기 기본 변경 없음. QQQ는 병합 전 사지 않는다(t3-proceeds-qqq 3절).

## 6. 결정 기록

- 순서 변경: 1절(사장 직접 입력 2026-11-09 10:19:23 KST).
- 착수 A: **사장 결정 카드 '착수 — 등록부까지'** — 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX97AveXwLkxhJwQex9LrzAKq, 제안 id qqq-reg-proposal-2026-11-09, 고른 항목 둘째(index 1, B) '착수 — 등록부까지', 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH(프로젝트 주인 = 사장), 2026-11-09 10:30:03 KST, 사장실 스레드 'QQQ 등록(K3) 먼저 진행'. 범위 = 2-1절 표 + 등록부 정식 등록·정책의 등록부 해시(builder 지시문 D). 같은 날(2026-11-09 KST) 1회 — 날짜가 넘어가면 같은 제안으로 카드를 다시 받는다. 병합은 따로 사장 결정 + 사장 PowerShell.
- Builder 1차(2026-11-09 10:4x KST): 정책 변경 전 BLOCKED — 기존 테스트 test_portfolio_exposure.py 105~107행이 실제 정책 배수 표를 고정(PWR·LITE 때 319b48f에서 함께 고침), 사장 PC 기본 python 3.15에 tzdata 없음, RC worktree가 다른 기준. 바뀐 것 없음.
- 재착수: **사장 결정 카드 '재착수 — 보정판'** — 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9Az8kTbVPfZDuEMxbs7s6UB, 제안 = 지시문 보정 3가지(위 테스트 1곳 허용 · py -3.13 · RC 자기 worktree에서 HEAD df9b2df 확인), 고른 항목 첫째(A), 누른 계정 user_01KuMGKfZu1SBYxtMmg4vAiH(사장), 2026-11-09 10:40:11 KST. 보정 원문 /mnt/project-files/qqq-reg-1109/qqq-reg-builder-amend-2026-11-09.md(클라우드 사본).
- Builder 2차(worktree claude/great-rhodes-1951b3, df9b2df): 바뀐 파일 6개, 새 테스트 8/8, 대상 테스트 결과 바꾸기 전과 같음, 전체 3626 OK(skip 3)·실패 0(py -3.13). QQQ 신원 sec.gov(CIK 0001067839, 485BPOS 2025-12-19). 보고 docs/claude/qqq-reg-report.md.
- Judge(별도 읽기 전용, Opus): **VERDICT: PASS** 2026-11-09 11:14 KST, 해시 6개 재계산 일치, 등록부 해시 VALIDATED. 보고 docs/claude/qqq-reg-judge-report.md. 지적: ① reconcile_broker_state.py:102~116은 보유 종목 등록부 identity가 verified여야 통과 → 등록부 포함이 필요했음(2-2절 '코어 판정은 등록부를 안 읽음'은 판정 쪽만 맞음) ② QQQ에도 종목 상한 0.4(portfolio_exposure.py:1119~1124·1237~1239) — 판 몫 QQQ는 계좌의 40% 이하 ③ 단계 B 범위에 auto_core_tickets.py:61~62 APPROVED_BUY·INDEX_ETFS 추가 필요 ④ 485BPOS 본문은 Judge 쪽에서 403 — data.sec.gov로 신원 확인.
- **병합: 2026-11-09 11:27:38 KST a764e97**(worktree 커밋 2b9afc9, --no-ff), 사장 PowerShell(병합 스크립트 .claude/worktrees/mystifying-kalam-923d86/docs/claude/qqq-reg-merge-2026-11-09.ps1, sha256 394ec996…afa). 병합 뒤 본 저장소 정책·등록부·테스트 5개 sha256 = Builder 값 일치(사장실 스레드 11:3x KST 확인). 보고서 2개는 CRLF 변환만 달라 바이트 해시가 다르고 CR을 뺀 내용 해시는 일치 — 스크립트 마지막 검사가 이 차이로 QQQ_REG_CHECK_AFTER_MERGE를 낼 수 있으나 병합 결과에는 영향 없음.
- 다음: 2026-11-10 06:15 자동 코어에서 QQQ 종가 이력 생성·UNREGISTERED 없음 확인 → 단계 B(3절 + auto_core_tickets.py APPROVED_BUY·INDEX_ETFS, K3 + 예약 작업 변경). 권한 자리는 단계 B까지 QQQ가 씀(cal-2027은 그 뒤, 기한 12/15).
