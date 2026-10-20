---
id: input-archive-review-2026-10-20
title: "입력 보관" 개발 검토 — decide 그날 입력 재현 장치
date: 2026-10-20
class: 검토 기록(문서만). 코드·정책·상태·예약 작업 변경 없음
decision_request: 사용자 "입력 보관 개발을 검토"(2026-10-20 15:46 KST, Cowork)
consumers: 관제판 input-archive · 다음 C1 초기화가 생길 때의 재현 판단(c1-keep류) · 독립 Judge 재현 절차
결론: NO_CHANGE(새 보관 장치 만들지 않음) + 사전 등록 계기 1개
---

# "입력 보관" 개발 검토

## 1. 물음
C1 초기화 때 지난 세션을 "그날 입력"으로 다시 돌려 볼 수 있어야 한다. 그날 입력을 그날 보관하는 장치가 필요한가?

## 2. 원문 확인 (이 세션, 2026-10-20 15:5x KST)
- 그날 decision.json이 이미 남기는 것: inputs 9개 경로·sha256, calendar sha, commit_sha, dirty_paths(auto-core/<날>/decision.json).
- 10-13~10-20 decide 6회 모두 inputs.registry.committed = true, dirty_paths에 입력 파일(등록부·관심 명단·R-REC1 문서·카드·state) 없음 → 추적 문서는 그날 commit_sha의 blob으로 복원된다.
- portfolio_state.json(git 미추적): stock-strategy-system/backups에 리비전마다 사본 r14~r28 15개(240K)가 있다. 삭제·정리 코드는 찾지 못했다(grep backups — apply_user_confirmed_broker_snapshot.py만). 현재 리비전은 작업 파일 자체.
- 30분봉 페이지는 파일 이름이 날짜라 "≤ 실행일"로 거르면 된다. 원장(jsonl)·결정 일지는 덧붙이기 전용이라 앞 n줄·n건으로 복원되고, 그날 S7 기록의 sha로 검증된다.
- 독립 Judge(c1-keep-judge-report.md "재현 방법"·N3)는 이 원천만으로 10-16·10-17을 그날 판과 정확히 같게 복원했다(read_files 포함, 34~40개 검사 일치).

## 3. 검토 순서
| 단계 | 판단 |
|---|---|
| NO_CHANGE | 그날 입력은 이미 결정론적으로 복원된다(2절). 빠진 것은 "보관"이 아니라 "복원 절차"이고, 이번엔 Judge가 수작업으로 했다 |
| REMOVE/SIMPLIFY | 없앨 것 없음 |
| REUSE | 복원 절차를 스크립트로 만들면 기존 기록(commit_sha·backups·날짜 이름·덧붙이기 전용 파일)을 그대로 쓴다. 코어·계산기 변경 없음 |
| REPLACE | 해당 없음 |
| ADD(매일 보관) | 코어나 실행기를 바꿔야 한다 → 권한 경로(K3) 또는 계산기 고정값 변경(실행기 sha, 사전 등록 49행). 지금 복원으로 충분하므로 이익 없음 |

## 4. 결론
- **NO_CHANGE**: 매일 보관 장치는 만들지 않는다.
- 복원 스크립트(REUSE)도 지금은 만들지 않는다. 쓰임이 C1 재현 하나뿐이고, "재현되면 유지"는 상시 규칙이 아니라 매번 K3 결정이다(c1-keep b 미채택). 또 입력이 완벽해도 코어 변경이 결과를 바꾸면 재현은 실패한다(c1-keep 10-16, hwm-fix).
- 주간 사용자 손: 0(변경 없음).

## 5. 사전 등록 계기와 기본 처분
- 계기 1: "켜" 전에 C1 초기화가 한 번 더 생기고 사용자가 복원을 원하면 → 그때 복원 스크립트(docs/claude 또는 tools, 일반 변경 = 개발 파이프라인, 코어·계산기 무변경)를 만든다.
- 계기 2: decide 날 dirty_paths에 입력 파일이 나타나거나, backups 사본이 지워진 것이 확인되면 → 그날은 복원 불가(NOT_VERIFIED, fail closed)로 표시하고 보관 장치를 다시 검토한다.
- 기본 처분: 계기가 없으면 NO_CHANGE 유지, 알림만.

## 6. 바뀔 조건
backups 정리 코드나 미커밋 입력으로 decide가 돈 날이 발견되면(2절 전제가 깨지면) 결론이 ADD 쪽으로 바뀐다.

## 7. 확인 필요
- backups 사본 보존 기간(삭제 코드는 못 찾았지만, 사람이 지우는 경우는 확인 못 함).
- r13 이전 리비전 사본이 없는 이유(9월 이전, 이번 C1 범위와 무관).
