# 아침 포트폴리오 전략

## A. 핵심 위험

- NBIS: EXIT_REVIEW - 검증된 정규장 종가가 승인된 최대손실 검토 경계를 하회했습니다.

## B. 기존 보유 종목

### MVLL
- 전략 / 실행 상태: DATA_BLOCKED / DATA_BLOCKED
- 핵심 사유: 완료 세션의 검증 가격·지표·독립 종가 교차검증이 충분하지 않습니다.
- 수량 / 수량 권한: None / none
- 다음 검토 조건: NEXT_VALIDATED_COMPLETED_SESSION
- 추가매수 조건: ['none']
- 감축 조건: ['none']

### NBIS
- 전략 / 실행 상태: EXIT_REVIEW / HUMAN_REVIEW_REQUIRED
- 핵심 사유: 검증된 정규장 종가가 승인된 최대손실 검토 경계를 하회했습니다.
- 수량 / 수량 권한: None / none
- 다음 검토 조건: IMMEDIATE_HUMAN_REVIEW_BEFORE_NEXT_SESSION
- 추가매수 조건: ['none']
- 감축 조건: ['HUMAN_REVIEW_OF_APPROVED_HARD_RISK_EVENT']

### SOXL
- 전략 / 실행 상태: DATA_BLOCKED / DATA_BLOCKED
- 핵심 사유: 완료 세션의 검증 가격·지표·독립 종가 교차검증이 충분하지 않습니다.
- 수량 / 수량 권한: None / none
- 다음 검토 조건: NEXT_VALIDATED_COMPLETED_SESSION
- 추가매수 조건: ['none']
- 감축 조건: ['none']

## C. 신규 기회

- MVLL: Opportunity=DATA_BLOCKED, Execution=DATA_BLOCKED, Blocker=INDEPENDENT_COMPLETED_CLOSE
- SOXL: Opportunity=DATA_BLOCKED, Execution=DATA_BLOCKED, Blocker=INDEPENDENT_COMPLETED_CLOSE
- NBIS: Opportunity=DATA_BLOCKED, Execution=DATA_BLOCKED, Blocker=INDEPENDENT_COMPLETED_CLOSE
- BE: Opportunity=DATA_BLOCKED, Execution=DATA_BLOCKED, Blocker=INDEPENDENT_COMPLETED_CLOSE
- TOST: Opportunity=DATA_BLOCKED, Execution=DATA_BLOCKED, Blocker=INDEPENDENT_COMPLETED_CLOSE
- NOW: Opportunity=DATA_BLOCKED, Execution=DATA_BLOCKED, Blocker=INDEPENDENT_COMPLETED_CLOSE
- FSLY: Opportunity=DATA_BLOCKED, Execution=DATA_BLOCKED, Blocker=INDEPENDENT_COMPLETED_CLOSE

## D. 현금 및 자금 상태

- 검증된 가용현금: 0.0
- 예상 매도대금: None
- 미결제·미확인 대금: None
- 실행 가능 구매력: 0.0

## E. 자본 재배치

- 자금 상태: NO_VERIFIED_FUNDING
- 우선 자금 용도: KEEP_CASH
- 대안 자금 용도: None
- 현금 유지 선택지: KEEP_CASH

## F. 최종 사람 검토 항목

- NBIS: EXIT_REVIEW (HUMAN_REVIEW_REQUIRED), quantity=None

주문을 실행하거나 예약하지 않았습니다. 사람의 승인과 최신 브로커 상태가 필요합니다.
