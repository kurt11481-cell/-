---
id: rrec-rg1-judge-prompt
title: rrec-rg1 독립 Judge (읽기 전용)
date: 2026-10-13
model: Opus · xhigh · 새 세션(메인 체크아웃, worktree 아님) — Builder 세션과 다른 세션
---

[Claude Code 실행 권장] 모델: Opus · 추론 노력: xhigh · 세션: 새 세션(메인 체크아웃) · 이유: K3 독립 Judge

너는 이 변경을 만들지 않은 독립 검토자다. **파일을 고치지 않는다.** 쓰는 파일은 맨 끝의 보고서 1개뿐이다.

## 읽을 것

1. 지시문: docs/claude/rrec-rg1-builder-prompt.md (메인 체크아웃)
2. Builder 보고: .claude/worktrees/rrec-rg1/docs/claude/rrec-rg1-report.md
3. 변경: 메인 체크아웃과 worktree의 같은 경로 파일 비교
   - manage-us-stock-strategy/scripts/auto_core_rules.py (`rrec1`)
   - 새 파일 .claude/worktrees/rrec-rg1/manage-us-stock-strategy/tests/test_auto_core_rrec_bootstrap.py
   - manage-us-stock-strategy/tests/test_auto_core_compare_fix3.py (지시문 "추가 범위": 한 테스트의 research_sessions 입력·주석만)
   - worktree `git status`로 바뀐 파일이 이 4개(코드 1 + 새 테스트 1 + 기존 테스트 1 + 보고서)뿐인지 확인
4. 근거: auto_core_decide.py 910~916행(rrec1 호출), auto_core_compare.py `_rg1_record_gap`, auto_core_inputs.py 연구 기록 sessions, docs/claude/recovery-gate-R-REC1-2026-10-09.md, docs/claude/buy-unblock-review-2026-10-13.md 3절

## 돌려도 되는 것

- worktree 안에서: `PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s manage-us-stock-strategy/tests -p "test_auto_core*.py"` (Claude Code 설정상 "auto_core.py"가 들어간 명령은 거부되니 이 패턴으로만).
- 파일을 쓰지 않는 python으로 rrec1 재계산(실데이터 확인 재현).
- 키움·auto_core.py·run_auto_core.ps1·dev-run·dev-merge·reconcile apply 실행 금지. 커밋·병합 금지.

## 판정 항목

지시문 "Judge 확인 항목" 1~6 + 아래:

7. fail-open 점검: 이 변경이 RG1 말고 다른 경로로 매수 관문을 넓히지 않나(예: first 계산이 coverage None/빈 목록/평가 세션 이후 날짜에서 엉뚱하게 넓어지는 경우).
9. test_auto_core_compare_fix3.py 변경이 입력 한 줄·주석뿐이고 단언은 그대로이며, 고친 입력이 첫 기록 이후의 진짜 공백을 만들어 원래 목적(rrec1 출력의 공백을 _rg1_record_gap이 읽는다)을 지키는가.
10. fail-open 경계: 창 시작 쪽 기록이 있었지만 무효(INVALID)였던 날은 "첫 유효 기록 이전"으로 빠진다(auto_core_inputs.load_research는 유효 기록만 sessions에 넣는다). 이 경우의 위험을 의견으로 적는다(결정 B 범위 안인지).
8. 실데이터 2026-10-12 결과가 지시문 기대와 같은가(RG1 ok·RG2 no·RG3 no·RG4 ok, before_first_record [2026-10-09]).

## 출력

- 한국어 표 `| 항목 | PASS/FAIL | 근거(파일:줄) |`, 고칠 최소 항목(있으면), 마지막 줄은 정확히 `VERDICT: PASS` 또는 `VERDICT: FAIL`.
- 같은 내용을 **새 파일 하나** `docs/claude/rrec-rg1-judge-report.md`(메인 체크아웃)에 저장한다. 그 밖의 파일은 쓰지 않는다.
