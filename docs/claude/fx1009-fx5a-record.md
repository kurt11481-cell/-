---
id: fx1009-fx5a-record
title: FX-1009 fx-5a 기록 — 위험 예산 대칭 리플레이(1.0·1.32·1.55)와 채우기 기본 대상
date: 2026-10-09
class: K3 사전 등록(정책 변경 없음)
plan: docs/claude/fx1009-fix-plan-2026-10-09.md 4절(Q9 a)·5-5절·7절 · 부록 A-5
authority: order_authority=false · quantity_authority=none · execution_quantity=null
consumers: 관제판 fx-5a · fx-6 마감 점검(부록 B "기록 파일") · 사용자 결정(결과 문서 10절)
---

# 0. 상태 (2026-10-09 16:0x KST)
- 완료: 사전 등록 고정 → 계산 → 독립 재구현 대조 → 결과 문서(결정 선택지 포함)
- 결과: A 우열 미확인 · B 우열 미확인. 채택 후보가 없어 Judge 안건은 없다.
- 결정: 2026-10-09 16:05 KST 사용자 "fx-5a 결정: A-1, B-1" → NO_CHANGE(1.55·SOXL 유지). 적용 = S5 정안 12줄 1줄(수정 전 `1384001c…f39b5` → 후 `052dd987…fac2e`, 저장 직전 해시 재확인, CRLF 유지) + 관제판
- 대기: 커밋(아래 명령)
- 범위: fx-5a만. fx-5b(공통 규칙 C 기준값·R-RI1·R-REC1 재설계)는 하지 않았다.

# 1. 완료 기준 (계획 5절 표 "사전 등록 해시 → 계산 → 독립 재구현 일치 → 결과 문서")
| 기준 | 결과 | 증거 |
|---|---|---|
| 사전 등록을 계산 전에 고정 | 충족 | `docs/claude/fx1009-fx5a-preregistration-2026-10-09.md` raw = LF sha256 `12c39fe7dab6f234e2cfe6f15cc654b8203c00aea006fb22105d0217b6f27890`, 고정 15:47:07 KST(사이드카 `.sha256`). 리플레이 실행은 15:57:30 KST. 끝에서 다시 대조해도 같음 |
| 계산 | 충족 | `stock-strategy-system/backtests/fx1009_fx5a_replay_2026-10-09.py` 실행본 sha256 `76ee64ed38c74574d2b1baf3d75e0755736812c13bad4c119d3e4cfa830ce025`, 결과 `fx1009_fx5a_replay_2026-10-09_results.json` sha256 `787e60416fa3aeaeadedf8e15d094b506ba9be481730ab60f44ad6309652a023`. 입력 7개·엔진 `25f5dce8…`·앵커 `77581918…` 해시 대조 통과, 자체 시험 27개 통과, 재현 앵커(1.55 = R-REC1-X B) 차 0 |
| 독립 재구현 일치 | 충족 | 별도 에이전트(사전 등록과 입력 CSV만 읽음, 엔진·스크립트 미열람)가 새로 구현. 비교 값 458개 최대 절대 차 0, a~d 미달 목록과 시작일 이동 0~9 판정 모두 같음. 재구현 코드는 세션 임시 경로(저장소 밖)에 있었고 보관하지 않음. 그 결과 JSON sha256 `47869ab9…a1f0` |
| 결과 문서 + 결정 선택지 | 충족 | `docs/claude/fx1009-fx5a-replay-results-2026-10-09.md` 10절 |

# 2. 이탈·주의 (확인 필요 포함)
1. **자체 시험 S3 수정 2회(실행 전).** ±0.3 조정 환산 시험의 장난감 수익 경로가 조정을 3번 이상 일으키지 못했다. 엔진과 손계산의 조정일은 두 번 모두 같았다. 장난감 경로만 바꿨다(n 400 → 2000, 평균 0 → 0.002, 표준편차 0.02 → 0.04). 리플레이 계산 코드는 바꾸지 않았다. 이 수정은 독립 재구현 에이전트의 판정 요약을 받은 뒤, 내 리플레이 실행 전에 했다. 스크립트 해시 `b9667a03…` → `463dd204…` → `76ee64ed…`.
2. **파일 반영 도구 지연 1회.** 컨테이너 → 사용자 PC 복사(device_commit_files)가 "written"이라고 답했지만 PC 쪽 내용이 바뀌지 않은 적이 1번 있었다. 같은 한 줄을 PC에서 직접 고친 뒤, 양쪽 해시가 같음을 확인했다(`463dd204…`, `76ee64ed…`).
3. **상태 파일 변경(다른 세션).** `stock-strategy-system/portfolio_state.json`이 16:02:16 KST에 다른 세션의 브로커 대조 apply로 바뀌었다(`workspace/outputs/reconciliation/20261009T070141Z/apply_audit.20261009T070215880489Z.json`, 백업 r22, `OI-20261009-SOXL-2.md` 16:00 수정과 같은 시각대). 이 세션의 작업이 아니다. 나머지 정책·상태·일지·`workspace/policies/*.json` 33개는 시작(15:43)과 끝(16:02)의 해시가 같다. 결정 반영 뒤(16:08) 다시 보니 `decision_journal.json`도 16:04:10 KST에 다른 세션의 일지 제안 apply로 바뀌었다(`workspace/outputs/exposure-review/journal-proposals/20261009T070344Z/journal_proposal.json`). 이것도 이 세션의 작업이 아니다. 정책 파일(`alert_policy.json`·`workspace/policies/*.json`)과 `alert_runtime_state.json`은 끝까지 같다.
4. C.6 탐색표와 2010~ 연수익이 0.05~0.07%p 다르다(SOX 32년·최근 5년은 같음). C.6 스크립트가 저장되지 않아 원인은 확인 필요다(판정 무관).
5. 키움 외화 예수금 이자 수준은 확인 필요다. B의 2010~ 판정 방향이 현금 이자 가정에 따라 바뀐다(결과 5절).

# 3. 건드리지 않은 것
정책(`alert_policy.json`, `workspace/policies/*`), 상태·일지, 예약 작업(조회도 안 함), 키움 도구(조회 포함 사용 안 함), 확인 코드 apply, 다른 세션 파일(c-rule-replay·r_rec1_gate 등). S5 정안은 결정 A-1에 따라 1줄만 추가했다.

# 4. 커밋 (사용자가 직접 실행)
PowerShell에서 한 줄씩:
```
cd "E:\사업\##금동한\코덱스저장소"
git add docs/claude/loss-limit-review-s5-policy-proposal-2026-10-01.md docs/claude/fx1009-fx5a-preregistration-2026-10-09.md docs/claude/fx1009-fx5a-preregistration-2026-10-09.sha256 docs/claude/fx1009-fx5a-replay-results-2026-10-09.md docs/claude/fx1009-fx5a-record.md stock-strategy-system/backtests/fx1009_fx5a_replay_2026-10-09.py stock-strategy-system/backtests/fx1009_fx5a_replay_2026-10-09_results.json
git status --short
git commit -m "docs: FX-1009 fx-5a risk-budget symmetric replay (preregistration, script, results, record)"
```
- 이 파일 7개만 올린다(S5 정안은 1줄 추가). 다른 세션의 미추적 파일(c-rule-replay·r_rec1_gate·workspace/outputs 등)은 넣지 않는다.

# 5. 관제판
- fx-5a: waiting → decision(16:05) → done(결정 A-1·B-1, 커밋 전). log 2줄.
- p-s7-p2(S7 2단계): note에 B-1 입력 1줄(채우기 기본 대상 = 설계 때 결과 문서 5~7절 참고).
