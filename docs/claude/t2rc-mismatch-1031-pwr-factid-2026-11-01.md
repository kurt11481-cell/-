# 10/31 독립 대조 MISMATCH — PWR 사실 번호의 두 판 (2026-11-01)

status: 사장 결정 기록 (D 설명 기록 + B 후보 등록, 결정 카드 2026-11-01 12:45 KST)
작성: 사장실 회사PC 스레드(읽기 진단). 코드·정책·예약 변경 없음.

## 1. 무엇이 어긋났나
- 출처: workspace/outputs/auto-core/2026-10-31/t2rc-check.json (verdict MISMATCH, counts_for_c1 true, 평가 세션 2026-10-30).
- 계산기: PWR 매수 회로 열림(new_basis_met true, 새 공식 강 근거 `PWR-20261029-q3-8k`). 코어: 후보 0, PWR buy official [] · new_basis_met false.
- 주문 영향 0: 코어는 E 1.9861 ≥ 1.85·현금 부족으로 PWR 매수를 어차피 막음, 주문표 없음(비교 모드).

## 2. 원인
- 같은 fact_id가 연구 기록 두 날에 다른 판으로 들어감.
  - research-records/2026-10-30: SEC 8-K(sec.gov), criterion_a **false**
  - research-records/2026-10-31: 회사 보도자료(investors.quantaservices.com), criterion_a **true**
- 코어: 같은 fact_id는 기록 날 순 **첫 판**(auto_core_inputs.py 312행 `facts.setdefault`) → criterion_a false → 강 근거 아님.
- 계산기: 오늘 사실은 **그날 기록의 판**(t2rc-oracle.py 1546~1550행 validate_facts(rr …)) → criterion_a true → 강 근거.
- "첫 판" 규칙은 의도된 것: ev-rg1-hyper에서 계산기의 훼손 사실만 코어에 맞춤(ev-rg1-hyper-builder-prompt.md 110행 ③), 오늘 사실은 범위 밖으로 남김(ev-rg1-hyper-report.md 70·130행 "드물어 낮음").
- 연구 기록 규칙은 "같은 사실은 날마다 같은 id"(scheduled-prompts/integrated-check-daily.txt 37행) — 판정이 바뀐 날에도 id를 유지하게 되어 있어 이 차이가 생김.
- 별개: 코어 next_action_for_cowork "판정 차이 4건 — 설명 기록 필요"는 통합 점검(LLM)과의 비교(F9) 쪽이며 이 문서 범위 밖(redesign-t2-compare-explained.json은 건드리지 않음).

## 3. 결정 (사장 결정 카드 2026-11-01 12:45 KST, "D 설명 기록 + B 후보 등록")
- D: 지금은 코어·계산기·규칙을 바꾸지 않고, 이 차이를 이 문서로 설명 기록한다. 원인 분류 = 사실 판 선택 규칙 차이(코어 버그 아님, 계산기 오류 아님).
- B 후보: "판정(criterion_a·방향·kind)이 바뀌면 새 fact_id" 규칙을 다음 통합 점검 규칙 파일 개정 묶음(close-confirm a·ic-rerun-core·rule-rev-ledger-trig와 같은 판) 후보로 관제판에 등록. 개정은 H1 시험·독립 검토·사장 직접 입력 '예약 작업 변경 승인' 경로.
- 하지 않음: A(코어 최신 판 우선, 권한 경로·훼손 사실 규칙 동시 변경), C(계산기를 첫 판에 맞춤) — 같은 일이 다시 나면 그때 B·C 중 다시 정한다.

## 4. 확인 필요
- 이 MISMATCH가 공식 C1 셈(t2-rc, 2/10)을 다시 시작하게 하는지 — c1-keep2 규칙으로 다음 t2-rc 갱신 때 확인.

## 결론을 바꿀 조건
같은 유형(같은 fact_id 다른 판) MISMATCH가 한 번 더 나거나, 매수 회로가 실제로 열릴 수 있는 날(E < 1.85·현금 있음)에 이 차이가 나면 B 또는 C를 바로 다시 묻는다.
