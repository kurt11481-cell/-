---
id: redesign-t2-replay-2026-10-14
title: 재설계 T2 R1 리플레이 판정 기록 (부록 C, 사전 등록 기간)
date: 2026-10-14
class: 판정 기록(문서). 코드·정책·상태 변경 없음
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: 관제판 redesign-t2 · T2 "켜" 판정(builder-prompt 46행 R1) · open-items-review-2026-10-14.md 4절
---

# R1 리플레이 판정 (부록 C)

- 실행: 2026-10-14 17:xx KST Cowork, auto_core_replay.py(HEAD 47e35fe, c6-fix2 1a2b7d6 포함), 기간 2026-07-10~2026-10-09(사전 등록), P-R1·P-R2 각 65세션, 예외 0, 자료 없음 0, 스키마 오류 0.
- 출력: workspace/outputs/auto-core/replay/prereg1009/replay.json (sha256 bcdbedbbf48f94dea5fe3a07715056b4d005b8ef7637932350c73c772148b469), summary.md. 저장소 git 무시 경로.

## 판정
| 기준 | 판정 | 비고 |
|---|---|---|
| R-A 실제 주문 앵커 | PASS | 앵커 26개 모두 결정론 사유 코드 |
| R-B 관문 누수 | PASS(실질 0건) | 열린 세션 0 → oracle_open_checked 0, external_checked 0 |
| R-C 빈도 | NOT_MET | P-R2 매수 주문표 0 |

막힌 사유 상위 5(세션 수)
- P-R2: NO_CIRCUIT_OPEN 64 · G2:EARNINGS_DATE_UNVERIFIED 1 · G2:PEAK_REVIEW_PAUSE:REVIEW_OPEN 1 · REQ1_EARNINGS:no 1 · REQ2_EXPOSURE_CASH_PRODUCT:no 1
- P-R1: NO_CIRCUIT_OPEN 63 · REQ2_EXPOSURE_CASH_PRODUCT:no 2 · REQ5_RREC1:no 2 · G2:PEAK_REVIEW_PAUSE:REVIEW_OPEN 1 · G2:PROPOSAL_NOT_AN_INCREASE 1

## 사전 등록과 다른 점
- Cowork 외부 오라클을 리플레이 전에 커밋하지 않았고, 이 세션은 결과를 먼저 봤다. 열린 세션이 0이라 영향은 R-B 실질 검사 0건과 같은 크기.
- 실행 코드는 병합 당시가 아니라 현재 HEAD(c6-fix2 포함). c6 수정 전후 리플레이 결과는 주문표·막힘이 같다(c6-fix-review-2026-10-14.md 74행).

## 처분
- 기본 처분(builder-prompt 472행): NO_CHANGE — T2 비교 모드 유지.
- 1회 알림: 2026-10-14 Cowork 대화에서 막힌 사유 순위와 함께 사용자에게 전달.
- 해석(등급 D): 매수 회로는 새 공식 강한 근거 또는 같은 날 새 가격 단서 2종일 때만 열리고(auto_core_tickets.py 141행), 리플레이는 공식 사실 없음 가정이라 미달은 구조적으로 예상된다. 기준 대체는 K3(사용자 결정).
