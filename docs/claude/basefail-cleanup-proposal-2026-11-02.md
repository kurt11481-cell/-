---
id: basefail-cleanup-proposal-2026-11-02
title: "기준선 남은 실패 정리 — ② git 밖 지난 파일 11건 · ④ Acceptance 옛 구현 해시 2건 수정안"
date: 2026-11-02
status: "제안 — 사장 결정 전. 코드·설정·정책·예약 변경 없음"
source: "사장 직접 입력 '2. 기준선 남은 실패 정리(로컬 파일 11건, Acceptance 2건) 진행'(사장실, 2026-11-02 19:44:06 KST), docs/claude/code-review-baseline-failures-2026-11-02.md ②·④"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책 내용·상태·일지·원장 쓰기 없음"
---

## 한 줄 결론
- ②는 그 지난 파일들을 개발 큐 작업 폴더에 **복사해 넣는** 목록(`.worktreeinclude`)에 더해 고친다. git에는 아무 자료도 올라가지 않는다. 보호 이름이라 K3 경로다.
- ④는 검증기를 그대로 두고 **시험 2개만** 고친다. T1(키움 pin 폐지) 뒤에는 구현 파일이 바뀌는 게 정상이기 때문이다. 기존 단언을 바꾸는 일이라 사장 결정이 먼저 필요하다. 그 뒤에는 개발 큐 일반 작업으로 간다.
- 둘 다 끝나면 기준선 실패는 15건에서 약 2건(③ 문서 자료)으로 줄 것으로 본다(확인 필요).

## ② git 밖 지난 파일 11건
### 확인한 것
- 11건이 읽는 파일은 모두 회사PC 본 저장소 디스크에 있다. 날짜는 모두 2026-08(8/13·8/14·8/29)의 지난 산출물이라 앞으로 바뀌지 않는다. 실제 상태 파일(P-1)과는 다르다.
- 이미 알려진 파일:
  - workspace/outputs/activation/ 아래(.gitignore 17행): nbis-v2-shadow 영수증, kiwoom-session-aware-priority 8/14 산출물들, holding-valuation-shadow 8/13 스냅샷, Acceptance 835d4f46의 source_artifacts 9개
  - workspace/outputs/portfolio-strategy/2026-08-13/ 아래 2개(.gitignore 73행)
  - stock-strategy-system/market_snapshot.example.json(.gitignore 39행)
  - workspace/outputs/lmt-instrument-registry-candidate-prep/lmt-instrument-registry-patch-candidate-v1.json(**ignore 안 됨**, 본 저장소에서 `??`)
  - workspace/outputs/manual-portfolio-analysis/manual-20260829T153208101909Z-c32341e4e7f3/manual-portfolio-analysis.json(대시보드 시험, **ignore 안 됨**)
- setUpClass 오류 3건은 처음 없는 파일 하나만 보여 준다. 그래서 전체 목록은 Builder가 시험을 돌려 끝까지 찾아야 한다.
- 일부 파일은 수 MB이고, 계좌 관련 칸이 있는 것도 있다(예: market_snapshot.example.json의 account_value 칸). 그래서 git에 올리는 방법(fixture로 커밋)은 쓰지 않는다. 23:30 자동 커밋이 GitHub로 보내기 때문이다.

### 고치는 법 (안)
1. devpipe는 기준선 worktree를 만들 때 `.worktreeinclude`의 정확한 경로를 복사한다(tools/dev_pipeline/devpipe.py 1105~1127행 `prepare_baseline_worktree`, 1393행 `include_candidates`. 별표 패턴은 받지 않는다). 여기에 위 파일들의 **정확한 경로**를 더한다.
2. ignore 안 된 두 경로(lmt 후보 폴더, manual-portfolio-analysis 폴더)는 `.gitignore`에 더한다. 그래야 worktree에 복사돼도 Builder 범위 검사에 '새 파일'로 잡히지 않는다. 본 저장소에서도 `??`가 사라진다.
3. 바꾸지 않는 것: 시험 파일·단언, devpipe 코드, 기존 `.worktreeinclude` 2줄(portfolio_state·alert_runtime_state).
4. 복사본은 매 기준선마다 sha256이 기록된다(`include_snapshot`). Builder가 그 파일을 고치면 지금처럼 보호 위반으로 멈춘다.

### 위험
- 이 시험들은 계속 회사PC 한 대의 파일에 기댄다. 다른 PC나 GitHub에서 돌리면 여전히 실패한다. 근본 해결(합성 fixture)은 시험마다 다시 써야 해서 크고, 이번 범위 밖이다.
- 복사량이 약 수십 MB다(확인 필요). 기준선마다 복사가 몇 초 늘 수 있다.

### 경로
- `.worktreeinclude`·`.gitignore`는 보호 이름이다(devpipe.py 121~123행). 그래서 **K3 수동 경로**로 간다. 순서는 사장 승인 카드, 사장실 한 줄, 실행 스레드 Builder(전체 목록 찾기 + 두 파일 수정), 별도 Judge, 사장 PowerShell 병합이다.
- 되돌리기: 커밋 1개 revert.

## ④ Acceptance 옛 구현 해시 2건
### 확인한 것
- 시험: test_v2_6_7 `test_extended_provider_scope_candidate_validates_without_activation`(310행), `test_guarded_priority_requires_locked_acceptance_manifest`(425행).
- 두 시험은 **실제 현재 Acceptance**(835d4f46, 2026-10-07)를 운영 검증기 `validate_acceptance`(validate_kiwoom_session_aware_acceptance.py)로 검사해 오류 0을 기대한다.
- 검증기는 Acceptance에 적힌 구현 파일의 정규화 해시를 지금 파일과 비교한다(같은 파일 66~76행). 10/07 이후 바뀐 구현 파일 10개가 어긋난다.
- CLAUDE.md 83~86행에 따르면 pin은 T1(510961a, 2026-10-10)로 폐지됐다(pin-scope status RETIRED). 구현 파일을 고치는 것은 이제 정상이다.
- 검증기를 바꾸는 방법은 쓰지 않는다. test_materialize_kiwoom_session_aware_acceptance_candidate 248행(test_09a)이 "검증기는 구현 해시 어긋남을 잡아야 한다"를 단언하기 때문이다. 검증기를 풀면 그 계약이 깨진다.
- 이 검증기는 Acceptance 후보 스크립트와 시험에서만 쓰인다. 자동 코어와 예약 지시문에서는 쓰지 않는다(grep). 운영 영향은 없다.

### 고치는 법 (안)
1. 두 시험에서만, 실제 manifest를 임시 사본으로 만들고 `implementation_hashes`를 지금 파일의 정규화 해시로 다시 채운 뒤 검증한다(test_09b와 같은 방식). 그러면 시험은 원래 보려던 것(scope·정책·Acceptance 묶음)을 계속 본다.
2. 같은 시험에 단언을 하나 더한다. 실제 manifest 그대로 검증했을 때 나오는 오류가 **모두** `implementation hash mismatch:`로 시작하는지 본다. 그러면 구현 해시 말고 다른 어긋남이 생겨도 숨겨지지 않는다.
3. 바꾸지 않는 것: 검증기 코드, Acceptance·정책 파일, 다른 시험.
4. 바꿀 파일은 test_v2_6_7_session_aware_kiwoom_priority.py 1개다. authority-paths나 보호 경로가 아니다. 그래서 **개발 큐 일반 작업**으로 간다(Builder → Judge → READY_TO_MERGE → 사장 병합). 기존 단언을 바꾸는 일이라 이 카드의 사장 결정을 결정 기록으로 둔다.
5. 되돌리기: 커밋 1개 revert.

## 순서
- ④(개발 큐)를 먼저, ②(K3)를 뒤에 한다. 두 작업 모두 docs/claude 밖을 바꾸므로 나중 병합은 STOP_BASE_MOVED가 날 수 있다(dev-queue-prompt-commit 기억). 그런데 ④는 다시 돌리기 싸고, ②는 K3라 비싸다. 그래서 ②를 ④ 병합 뒤 최신 기준에서 시작한다.

## 사장 결정 기록 (2026-11-02)
- 카드: cmsg_0137MRzn9nuDvvQmVxm6WeX9BrPM94W22naif7qV4EC7RF (이 스레드가 이 수정안 basefail-cleanup-proposal-2026-11-02에 대해 올린 카드, 질문 "기준선 남은 실패 13건을 이 수정안대로 고칠까요?")
- 고른 항목: "둘 다 승인, 오늘 진행" (option_index 0)
- 누른 계정: user_01KuMGKfZu1SBYxtMmg4vAiH (프로젝트 소유자 = 사장)
- 시각: 2026-11-02 19:53:58 KST (harness wake 원문 기준)
- 범위: 이 수정안 1건(② K3 복사 목록 + ④ 시험 2개), 2026-11-02 하루, 1회. ④는 개발 큐 일반 작업 acc-implhash(지시문 docs/claude/acc-implhash-builder-prompt.md). ②는 ④ 병합 뒤 사장실 한 줄로 K3 실행. 병합은 각각 별도 사장 결정.

## 정정 (2026-11-02 20:0x KST, 승인 직후 지시문 쓰며 확인)
- ④ 고치는 법 1번("임시 사본에 구현 해시를 다시 채워 검증")은 그대로는 안 된다. 검증기가 manifest 파일의 정규화 해시를 정책의 Acceptance 묶음과 대조하기 때문이다(validate_kiwoom_session_aware_acceptance.py 25행). 사본을 고치면 묶음이 깨진다.
- 그래서 두 시험은 실제 manifest를 그대로 검증한다. 그 결과에서 `implementation hash mismatch: <경로>` 오류만 따로 뗀다. 남은 오류가 0인지, 뗀 오류의 경로가 모두 manifest의 `implementation_hashes` 키 안에 있는지 확인한다.
- 위 2번(어긋남은 구현 해시뿐) 단언과 뜻이 같다. 검증기·다른 시험은 그대로다. 승인 범위(시험 2개만, 검증기 불변) 안이다.

## ④ 실행·병합 결정 기록 (2026-11-02)
- 1차 acc-implhash: BLOCKED(2026-11-02 20:11 KST). 시험 파일이 git에 CRLF·LF 혼합(i/mixed)으로 있어 편집 도구가 전체를 LF로 바꿨고, "줄바꿈 지키기" 규칙에 걸렸다. 내용 수정과 대상 42건 통과는 됐다.
- 2차 acc-implhash2(지시문 docs/claude/acc-implhash2-builder-prompt.md, 이 파일만 LF 허용): NEEDS_APPROVAL, Judge 2회차 PASS(1회차 FAIL은 보고서 (b) 경로 목록 누락), 새 실패 0, 기준선 실패 15→13, ran 3513→3513 (2026-11-02 20:57 KST, docs/claude/dev-runs/acc-implhash2.md).
- 등급 authority 사유: REMOVED_LINE:order_authority. 줄바꿈 전체 변경 때문에 생긴 오탐이다. Judge가 지운 8줄과 더한 8줄의 글자가 같음을 확인했다.
- 공개: Builder가 임시 스크립트 실행과 파이프 1회를 시도했다가 거부됐다. diff에는 흔적이 없다(Judge G2).
- 카드: cmsg_0137MRzn9nuDvvQmVxm6WeX9N7KFJusrmeTe1aV6hYiXGs (질문 "시험 2개 수정(acc-implhash2)을 병합할까요?", 위 두 공개 사항을 알린 뒤)
- 고른 항목: "병합 승인" (option_index 0)
- 누른 계정: user_01KuMGKfZu1SBYxtMmg4vAiH (프로젝트 소유자 = 사장)
- 시각: 2026-11-02 21:08:47 KST (harness wake 원문 기준)
- 실행: 사장이 직접 연 대화형 PowerShell에서 `.\tools\dev-merge.ps1 acc-implhash2 -ApproveAuthority` 실행 후 Enter 한 번. 이 스레드는 실행하지 않는다.
- 병합 결과: `DEV-MERGE acc-implhash2 MERGED sha=c81ac2e6 mode=ff`(사장 붙여 넣기, 2026-11-02 21:43:54 KST). 커밋 c81ac2e 21:41:45 KST, 파일 2개.
