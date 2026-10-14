---
id: integrated-check-v3.12.5-change
title: 통합 점검 규칙 파일 v3.12.5 변경 기록 (c3-rule)
date: 2026-10-14
class: K1 (규칙 문구 보완) — 트리거 기준·근거 강도·알림 조건·쓰기 범위·권한 불변. 코어(auto_core_rules.py) 동작과 같게 적는 것
decision: 사용자 "결정 c3-state: a"(15:27) · "c3-rule: 1"(15:40, 2026-10-14 KST, Cowork 대화) — 근거 c3-state-decision-2026-10-14.md
status: 초안 저장 + 독립 검토 PASS. 미적용 — 2026-10-15 07:35 earn-na R2 교체 세션에서 R2와 함께 한 번에 교체(사용자 승인·재서명 1회), 적용되면 10/16 06:40부터
authority: order_authority=false · quantity_authority=none · execution_quantity=null
---

# 통합 점검 규칙 파일 v3.12.5 변경 기록

## 1. 파일과 sha256
| 파일 | sha256 | 바이트 |
|---|---|---|
| docs/claude/integrated-check-prompt-v3.12.5-2026-10-14.txt (규칙 파일, LF) | 3e05c8efc1ef256acb82ec1a9c54ecca0485424f6368e40a627e859d18420ffb | 93,449 |
| docs/claude/scheduled-prompts/pending-c3rule/integrated-check-daily.txt (로더 v3.12.5-L+R2) | 206782f6584694e8143844b193576ec443438c14d1710f5d0320543998b49312 | 20,935 |
| 기준: 규칙 파일 v3.12.4(현행) | cafec5a43eca9358de006711d627f1e8eb558ef4c38278d4a9f36af672870530 | 92,520 |
| 기준: 로더 v3.12.4-L+R2(pending-earnna, 미적용) | d81ecd30a662e5f0ce571a6ef3eb85ae9f689676cbee742723b6a45dfd373659 | 20,729 |

## 2. 바뀐 것
- 규칙 파일: 1행 판 노트, 113행 "(이미 성립 중이면 "유지 중")." 뒤에 1문장 — C3±는 107행 조건으로 처음 성립한 뒤 종가가 그 세션 EMA20의 같은 쪽(C3+ >, C3- <)에 있는 동안 "유지 중" 1개, 같은 쪽이 아닌 종가(같음 포함)가 처음 나온 세션에 끝, 성립 뒤 "그 앞 종가" 조건을 다시 요구하지 않고 사건형 5세션 창도 쓰지 않음, 같은 쪽 연속이 시계열 첫 세션까지 이어지면 "유지 중(성립일 확인 필요)"으로 적고 세지 않음.
- 로더: R2(pending-earnna)와 본문이 같고 5줄만 다르다 — 1행 판 접두, 4·12행 규칙 파일 경로, 18행 해시, 75행 writer 'integrated-check 06:40 v3.12.5-L+R2'. 1단계 python 실행 결과 MATCH(2026-10-14 Cowork).

## 3. 검토
- 코어 일치(독립 검토 서브에이전트, PASS): auto_core_rules.py 141행 _cmp 엄격 부등호, 319~326행 run ≥ 2 + 앞 종가 반대쪽, 148행 시계열 밖 = None → 413행 unk, C3는 state 종류(80행).
- 충돌 없음: 107행(정의), 114~115행(같은 종류 합치기·카드 정의 우선). 카드 S4(ema20_below_twice, 484행)는 카드 정의라 이 문장의 범위 밖.
- 선택 보강 2건은 넣지 않음(결정 범위 1문장): S4 등 카드 별칭 적용 범위 명시, C3- 성립일 확인 필요일 때 강조 표시.
- 07:20 첫 실행 확인(st1014-firstrun-check.py, writer v3.12.4-L+R1 기대)은 10/15 실행만 보므로 영향 없음.

## 4. 적용 절차(10/15 07:35 earn-na 세션)
1. 07:20 확인 PASS(또는 설명되는 CHECK)일 때만.
2. 교체 직전 규칙 파일·로더 sha256 재확인 → 통합 점검 예약 작업(trig_01YWzNq847nJfNgDUnnukBqP) 지시문을 pending-c3rule 파일로 교체(사용자 승인·재서명 1회).
3. 사용자가 C3 보완을 빼고 싶다면 기존 pending-earnna(d81ecd30…)로 교체 — 이 경우 c3-rule은 NO_CHANGE.
4. 교체 뒤: scheduled-prompts/integrated-check-daily.txt 사본·README 표·이 문서 status, 관제판 earn-na·redesign-t2.
- 되돌리기: R1(b166bad2…) 또는 R2(d81ecd30…) 파일로 교체.
