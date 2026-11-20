---
id: recon-dayfill-k3-builder-prompt
title: "계좌 대조 — 키움 주간거래 체결 인정 — recon-dayfill-k3 Builder"
date: 2026-11-20
class: "K3 수동 경로(reconciliation invariants). 회사PC worktree Builder(Opus) → 별도 읽기 전용 Judge → 병합은 사장 결정 뒤 -ApproveAuthority"
source: "docs/claude/recon-dayfill-k3-proposal-2026-11-20.md(수정안 id recon-dayfill-k3-proposal-2026-11-20), 승인 = 실행 당일 그 수정안 id를 단 사장 결정 카드(수정안 0절)"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

## 목표
수정안 1절대로 parse_fills의 체결 시각 창을 D−1 20:00 ET 초과 ~ D 20:00 ET 이하로 넓히고, D 04:00 ET 미만 체결에 `"segment": "DAY_SESSION"`을 붙인다. 나머지 대조 규칙은 수정안 2절대로 바꾸지 않는다.

## 바꿀 파일 (이것만)
수정안 9절 목록. 그 밖의 파일을 고쳐야 하면 BLOCKED.md에 이유를 쓰고 멈춘다.

## 구현 요구
1. auto_core_reconcile.py 315~319행: 체결 창 아래 끝을 `datetime.combine(order_day - timedelta(days=1), US_DAY_CLOSE, tzinfo=ET)`, `low_open=True`로. 위 끝은 그대로.
2. 323~325행 `FILL_SESSION_DATE_MISMATCH` 검사: segment는 moment < D 04:00 ET일 때만 DAY_SESSION. 정규·시간외면 moment의 ET 날짜 == D, DAY_SESSION이면 ∈ {D−1, D}. 그 밖은 지금처럼 오류.
2-1. fill_settlement 557행: `first_day = min(max(item["last_fill_day"], date.fromisoformat(item["session_date"]) + timedelta(days=1)) for item in sessions)`(수정안 1-2절). 독스트링의 'A date can only hold fills from earlier KST days' 문장을 새 기준일로 고친다.
3. item에 `segment`는 DAY_SESSION일 때만 넣는다(정규·시간외 행의 dict는 지금과 바이트 단위로 같게 — FILL_ROW_DUPLICATE_CONFLICT 비교와 기존 시험 보호).
4. 270~274행 독스트링, 96행 근처 주석, 참조 문서 broker-snapshot-reconciliation.md 241~250행 문장을 새 규칙(관측 2026-11-19 SOXL, ord_dt = 체결 KST 날짜 = ET 다음 거래일)으로 고친다.
5. fill_sessions·fill_settlement의 first_day 밖 부분·_assign·plan_reads·OPEN_ORDERS·B2-N unverified_outflow·ledger_days·I1·I4·I5는 손대지 않는다.

## 시험
수정안 4절 T1~T12(T3b 포함)를 새 파일에, 기존 파일은 4절의 4개 단언과 주석만. 기준선 실패 수(작업 전 `python -m pytest manage-us-stock-strategy/tests -q` 결과)와 작업 뒤를 보고에 적는다. 새 실패 0이어야 한다.

## 보고 (docs/claude/recon-dayfill-k3-report.md)
바뀐 줄(파일:행), 시험 결과(기준선·이후 실패 수, 새 시험 이름), 기존 단언 변경 4개와 이유, 수정안 9절 미해결 3개를 그대로 옮김, 남은 위험.

## 금지
주문·정정·취소, 키움 도구 호출, apply, auto_core.py 실행, .env·토큰·계좌번호 읽기, 정책·상태·원장·일지 쓰기, 기존 시험 약화.
