---
id: gitattr-bytes-proposal-2026-11-02
title: "원본 바이트로 해시하는 권한 파일을 CRLF 변환에서 빼기 — K3 수정안 (.gitattributes)"
date: 2026-11-02
status: "제안 — 사장 승인 전. 코드·설정·정책·예약 변경 없음"
source: "docs/claude/code-review-baseline-failures-2026-11-02.md ①(16건), 사장 카드 '줄바꿈 보호 수정안 쓰기'(2026-11-02 18:46 KST), 선례 56770fc(r-gitattr-artifact, 2026-10-07)"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책 내용·상태·일지·원장 쓰기 없음"
---

## 한 줄 결론
`.gitattributes`에 `-text` 4줄을 더한다. 그러면 개발 큐 작업 폴더도 키움 우선순위 증거와 종목 신원·달력 활성화 파일을 본 저장소와 같은 바이트로 받는다. 기준선 실패 16건이 없어지고, 이 권한 시험들이 다시 회귀를 잡는다.

## 원인 (확인한 것)
- 개발 큐 작업 폴더(worktree)는 텍스트 파일을 CRLF로 받는다. 확인한 worktree 5곳에서 모두 CR이 들어갔다. 어느 git 설정(core.autocrlf) 때문인지는 회사PC 전역 설정이라 **확인 필요**.
- 키움 우선순위 시험(14건)은 현재 Acceptance 파일을 **원본 바이트** sha256(835d4f46…)으로 찾는다. 시험 97행이 그렇다. worktree에서는 바이트가 바뀌어 0f9b9038…이 되고, 그래서 못 찾는다.
- 종목 신원 시험(2건)은 `workspace/policies/instrument_identity_activation.json`을 `decode_canonical_object`로 읽는다(authority_artifact_io.py 201~213행). 이 함수는 바이트가 정규형과 정확히 같아야 한다. 본 저장소 파일은 CR이 0개이고, worktree 파일은 CR이 있다. 그래서 INTEGRITY_FAILURE가 난다(instrument_identity_artifact.py 189~197행).
- 지금 `-text`는 `workspace/calendar-authority/artifacts/**`, `workspace/instrument-identity-authority/artifacts/**`만 덮는다.

## 왜 본 저장소에도 필요한가
- 본 저장소의 활성화 파일이 지금 LF인 것은 git이 그 파일을 다시 쓴 적이 없어서일 수 있다(추정).
- worktree가 CRLF로 받는다면, 병합이나 체크아웃이 활성화 파일을 다시 쓰는 날 본 저장소에도 CRLF가 들어갈 수 있다. 그러면 운영 쪽 종목 신원·달력 읽기가 INTEGRITY_FAILURE로 막힌다(fail-closed). 대시보드와 주문 의도 판정이 '확인 안 됨'으로 떨어진다.
- 이 수정은 그 위험도 함께 없앤다.

## 바꿀 내용 (안)
`.gitattributes`에 아래 4줄을 더한다. 기존 2줄은 그대로 두고, 맨 뒤에 아래 7개 예외(`text`)를 둔다.
```
workspace/research/provider-evidence/** -text
workspace/instrument-identity-authority/** -text
workspace/policies/instrument_identity_activation.json -text
workspace/policies/session_calendar_activation.json -text
```
- `workspace/policies/**` 전체는 넣지 않는다. 본 저장소의 `integrated_identity_session_activation.json`은 이미 CRLF로 있다(색인은 LF). 그래서 전체에 걸면 본 저장소가 '변경됨'으로 보일 수 있다. 이 파일은 원본 바이트를 요구하지 않는 디코더로 읽는다(integrated_authority_snapshot.py 111행 `_decode_manifest`). 그래서 이번 범위에서 뺀다.
- `manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json`도 넣지 않는다. 매니페스트에 적힌 해시가 원본 바이트 해시와 다르다. 정규화 해시로 보이며, Builder가 확인한다.

## 이미 CRLF인 지난 증거 7개는 지금 그대로 둔다 (2026-11-02 19:0x KST 정정)
- 처음 안은 병합 때 이 7개를 LF로 되돌리는 것이었다. 그런데 확인해 보니 그중 `kiwoom/2026-08-14/session-aware-priority-acceptance.json`은 **CRLF 바이트 해시(0deb88f3…)**가 지난 기록 `workspace/research/holding-overlays/2026-08-13/v2.6.14/soxl-price-evidence.json` 16행에 적혀 있다. 이 값을 검사하는 코드는 없다(scripts·tests grep). 나머지 6개는 어떤 바이트 해시도 저장소에 적혀 있지 않다.
- 그래서 LF 되돌리기는 하지 않는다. 대신 `.gitattributes` 맨 뒤에 이 7개를 `text`로 다시 적는다. 그러면 이 7개는 지금과 똑같이 받는다. 본 저장소 작업 사본도 바뀌지 않고, '변경됨'으로 보이지도 않는다.
- 7개 경로(모두 2026-08 지난 증거):
  - workspace/instrument-identity-authority/rejudge-runs/2026-08-28/k3-identity-binding-repair/run_manifest.json
  - workspace/research/provider-evidence/kiwoom/2026-08-13/acceptance-manifest.json
  - workspace/research/provider-evidence/kiwoom/2026-08-14/mvll-canonical-volume-lineage.json
  - workspace/research/provider-evidence/kiwoom/2026-08-14/mvll-volume-authority-acceptance.json
  - workspace/research/provider-evidence/kiwoom/2026-08-14/session-aware-priority-acceptance.json
  - workspace/research/provider-evidence/kiwoom/2026-08-28/k3-authority-candidate-builder-run-manifest.json
  - workspace/research/provider-evidence/kiwoom/2026-08-29/k3-normalized-candidate-repair/run_manifest.json
- 결과: 새 범위 안의 나머지 파일은 본 저장소에서 모두 이미 LF다. 그래서 병합해도 본 저장소 파일 바이트는 하나도 바뀌지 않는다(`.gitattributes` 한 파일만 바뀜).

## 시험
- 새 시험 파일 `manage-us-stock-strategy/tests/test_gitattributes_authority_bytes.py`(보호 경로 아님)를 둔다. `git check-attr text`로 위 4개 범위의 대표 파일이 `unset`인지 확인한다. 나중에 누가 줄을 지우면 잡힌다.
- Builder worktree에서 전체 시험을 한 번 돌린다. 기대 결과:
  - test_v2_6_7 14건과 신원 2건 통과
  - 새 실패 0
  - 남은 기준선 실패 13건(git 밖 파일 11, 문서 자료 2)
- 그 worktree에서 `git ls-files --eol`로 위 파일들이 `attr/-text`이고 `w/lf`인지 확인해 보고한다.

## 경로와 승인
- `.gitattributes`는 보호 이름이라 개발 큐 작업으로 못 바꾼다(devpipe.py 121~123행). 그래서 **K3 수동 경로**로 간다.
- 진행 순서:
  1. 사장 승인 카드를 받는다.
  2. 사장이 사장실에 직접 한 줄을 쓴다(예: "줄바꿈 보호 실행해"). 그래야 실행 스레드가 뜬다.
  3. 회사PC에서 Builder worktree(Opus)가 작업한다.
  4. 별도 읽기 전용 Judge가 검토한다.
  5. 사장이 PowerShell로 병합한다.
- 승인은 그날 1회만 유효하다. 날짜가 넘어가면 시작 직전에 다시 카드를 받는다.
- 되돌리기: 커밋 1개를 revert한다.

## 범위 밖
- git 밖 로컬 파일 의존 11건, diff 파일 1건, PLTR 등록부 해시 1건은 code-review-baseline-failures-2026-11-02.md에 따로 둔다.

## 사장 결정 기록 (2026-11-02)
- 카드: cmsg_0137MRzn9nuDvvQmVxm6WeX9TgpMChM1zTDtQqpkkgaTUU (이 스레드가 이 수정안 gitattr-bytes-proposal-2026-11-02에 대해 올린 카드, 질문 "권한 파일 줄바꿈 보호(.gitattributes 4줄)를 오늘 고칠까요?")
- 고른 항목: "승인, 오늘 진행" (option_index 0)
- 누른 계정: user_01KuMGKfZu1SBYxtMmg4vAiH (프로젝트 소유자 = 사장)
- 시각: 2026-11-02 18:54:38 KST (harness wake 원문 기준)
- 범위: 이 수정안 1건, 2026-11-02 하루, 1회. 지시문 docs/claude/gitattr-bytes-builder-prompt.md, docs/claude/gitattr-bytes-judge-prompt.md. 승인 뒤 바뀐 점: 위 "7개는 그대로 둔다" 정정(본 저장소 파일을 덜 건드리는 쪽, 변경 범위는 `.gitattributes` 한 파일 그대로). 병합은 별도 사장 결정.

## 실행 기록 (2026-11-02)
- 실행 지시(사장 직접 입력): 실행 스레드 시작 메시지 cmsg_0137MRzn9nuDvvQmVxm6WeX9MMcj3FaiMRdVHQ1DPUXoC9, 계정 user_01KuMGKfZu1SBYxtMmg4vAiH, 2026-11-02 18:59:43 KST, 원문 "줄바꿈 보호 실행해".
- Builder: 원격 연결에서 새 세션 시작이 거부돼 실행 스레드가 직접 했다. worktree .claude/worktrees/epic-kilby-606390, 브랜치 worktree-gitattr-bytes, 기준 6aea772, 커밋 없음. 보고서 docs/claude/gitattr-bytes-report.md(worktree 안).
- 결과: 기존 실패 16건 중 14건 통과. 남은 2건은 Acceptance 835d4f46의 구현 해시 10건 어긋남(본 저장소도 같은 10개)이라 이 수정으로 못 고친다. 위 "시험" 절의 기대(16건 통과, 남은 13건)는 틀렸고, 남는 기준선 실패는 15건으로 예상한다.
- 사장 결정(직접 입력): 같은 스레드 cmsg_0137MRzn9nuDvvQmVxm6WeX93WouHSSotdmAA2gG65aZHX, 계정 user_01KuMGKfZu1SBYxtMmg4vAiH, 2026-11-02 19:12:19 KST, 원문 "14건으로 진행". 바로 앞 질문(14건 기준으로 Judge까지 진행할지, Judge 6번 기준을 "14건 통과, 2건은 별도 원인임을 확인"으로 고칠지)에 대한 답이다.
- 뜻: Judge 지시문 6번만 그렇게 읽는다. 지시문 파일은 고치지 않고 Judge에게 주는 실행 지시에 적는다. 남은 2건의 시험 수정은 범위 밖 별도 안건이다. 병합은 별도 사장 결정.
- Judge: 별도 회사PC 세션, 8개 항목 PASS, VERDICT: PASS(docs/claude/gitattr-bytes-judge-report.md, 사장 입력에 따른 6번 읽기 + 8번 추가).
- 병합(사장 PowerShell): 2026-11-02 19:28:56 KST, 병합 커밋 52bbe81, 작업 커밋 77ab05e, 바뀐 파일 5개(6aea772 대비). 사장 보고 "병합 완료" 19:29:23 KST. 본 저장소 test_v2_6_7은 2건 실패(Acceptance 구현 해시, 별도 안건).
