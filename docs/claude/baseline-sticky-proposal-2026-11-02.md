---
id: baseline-sticky-proposal-2026-11-02
title: "기준선 감시 멈춤이 다음 기준선에서 풀리지 않게 — K3 후속 수정안 (baseline-watch-sticky)"
date: 2026-11-02
status: "제안 — 사장 승인 전. 코드·설정·예약 변경 없음"
source: "baseline-watch Judge 주의 (B) (/mnt/project-files/baseline-watch/baseline-watch-judge-report.md 26행), 병합 8615efb(2026-11-02 08:42 KST), 관제판 tasks baseline-watch-sticky(planned)"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책·상태·일지·원장 쓰기 없음"
---

## 한 줄 결론
직전 기준선을 고를 때 "멈춘 기준선"(실패가 10건 이상 늘었고 사장 승인 표식이 없는 것)은 건너뛴다. 그러면 실패를 고치거나 사장이 표식을 둘 때까지 멈춤이 이어진다.

## 지금 문제
- `previous_baseline`(tools/dev_pipeline/devpipe.py 1004~1019행)은 조상 기준선 가운데 가장 최근 것을 고른다. 그 기준선이 멈춘 기준선인지는 보지 않는다.
- 그래서 기준 커밋 X에서 실패가 +255로 늘어 멈춰도, 그 뒤 :00·:30 문서 커밋으로 기준이 Y로 옮겨지면 Y는 X와 비교해 +0이 된다. 결국 통과한다.
- 수정안(baseline-watch-proposal-2026-11-01.md)은 "원인을 고치거나 사장 표식(`_baseline/accept-<sha8>.txt`)"을 전제로 했다. 지금은 그 둘 없이도 30분 안에 풀린다.

## 바꿀 내용 (안)
1. `previous_baseline`의 후보에서 다음 기준선을 뺀다: 자기 `added_failures`가 `BASELINE_ROSE_STOP`(10) 이상이고, 그 기준 커밋의 accept 표식이 없는 것.
2. 비교 키(`added_failures`)가 없는 옛 캐시는 지금처럼 후보로 둔다(깨끗한 것으로 본다). 재귀 계산은 하지 않는다.
3. accept 표식이 있는 멈춘 기준선은 후보로 둔다. 그래서 사장이 받아들인 뒤에는 그 기준선이 새 비교점이 된다.
4. 결과: X에서 멈춘 뒤 Y로 옮겨져도, Y는 X 이전의 마지막 깨끗한 기준선 W와 비교한다. 실패가 그대로면 +255로 다시 멈춘다. 실패를 고쳐 수가 줄면 저절로 풀린다.
5. 바꾸지 않는 것: 문턱값 10, 경고·멈춤 이름, accept 표식 이름·위치, dev-merge 규칙, 그 밖의 판정.

## 시험 (test_dev_pipeline.py에 추가)
- X 멈춤(+10, 표식 없음) → 자손 Y는 W와 비교해 다시 STOP.
- X 멈춤 + accept-X → Y는 X와 비교, 경고·멈춤 없음.
- X 멈춤 뒤 Y에서 실패를 고쳐 W 수준 → 멈춤 없음.
- 비교 키 없는 옛 캐시 → 후보로 남음(기존 동작).
- 1~9건 경고뿐인 기준선 → 지금처럼 후보로 남음.

## 범위 밖 (기록만)
- 1~9건씩 여러 번 쌓이는 증가는 계속 경고만 남는다(Judge 기타 항목). 필요하면 "마지막 accept 이후 누적" 규칙을 별도 안건으로 둔다.

## 경로와 승인
- tools/ 보호 경로라 K3 수동 경로다. 사장 승인 카드를 받은 뒤, 사장이 사장실에 직접 한 줄을 보내야 실행 스레드가 뜬다(예: "기준선 멈춤 수정 실행해"). 승인은 그날 1회만 유효하다.
- 실행: 회사PC Builder worktree(Opus) → Builder 종료 → 별도 읽기 전용 Judge → 사장 PowerShell 병합. 지시문은 승인 뒤 baseline-watch 지시문을 본떠 쓴다.
- 되돌리기: 커밋 1개 revert.

## 사장 결정 기록 (2026-11-02)
- 카드: cmsg_0137MRzn9nuDvvQmVxm6WeX9C8VBvQ1bH4eg6EfpQkp8So (이 스레드가 이 수정안 baseline-sticky-proposal-2026-11-02에 대해 올린 카드, 질문 "기준선 멈춤이 저절로 풀리지 않게 고칠까요?")
- 고른 항목: "승인, 오늘 진행" (option_index 0)
- 누른 계정: user_01KuMGKfZu1SBYxtMmg4vAiH (프로젝트 소유자 = 사장)
- 시각: 2026-11-02 09:02:56 KST (harness wake 원문 기준)
- 범위: 이 수정안 1건, 2026-11-02 하루, 1회. 지시문 docs/claude/baseline-sticky-builder-prompt.md, docs/claude/baseline-sticky-judge-prompt.md

## 실행 기록 (2026-11-02)
- 실행 지시(사장 직접 입력): 사장실 회사PC 실행 스레드 '기준선 멈춤 유지 수정' 시작 메시지 cmsg_0137MRzn9nuDvvQmVxm6WeX9NYrhJUTrhPMK2WntGYx2S9, 계정 user_01KuMGKfZu1SBYxtMmg4vAiH, 2026-11-02 09:40:20 KST, 원문 "기준선 멈춤 수정 실행해".
- 결과: Builder 완료(worktree .claude/worktrees/baseline-sticky, 브랜치 worktree-baseline-sticky, 기준 8615efb, 대상 시험 150건 OK, 시험 7건 추가), 독립 Judge 9개 항목 PASS, VERDICT: PASS(docs/claude/baseline-sticky-judge-report.md).
- 병합 스크립트 준비 지시(사장 직접 입력): 같은 스레드 cmsg_0137MRzn9nuDvvQmVxm6WeX9QVm4kdN9RMBsnkRDNM2Rmw, 2026-11-02 11:38:25 KST, 원문 "진행".
- 뜻: 병합 스크립트 준비까지. 병합 자체는 사장이 자기 PowerShell에서 docs/claude/baseline-sticky-merge-2026-11-02.ps1 한 줄을 실행할 때다(2026-11-02 KST 안, 23:20~23:45 KST 피함).
- 병합(사장 PowerShell): 2026-11-02 11:45:29 KST, 병합 커밋 cae9a77, 작업 커밋 4dbb6d8, 바뀐 파일 4개(8615efb 대비). 사장 보고 "병합 완료" 13:05 KST.
