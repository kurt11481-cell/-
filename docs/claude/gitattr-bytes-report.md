---
id: gitattr-bytes-report
title: "권한 파일 CRLF 변환 막기 — Builder 보고"
date: 2026-11-02
class: "K3 수동 경로 Builder. Judge 전, 커밋 없음"
source: "docs/claude/gitattr-bytes-builder-prompt.md, docs/claude/gitattr-bytes-proposal-2026-11-02.md"
authority: "주문·키움 호출 없음 · 정책 내용·상태·일지·원장 쓰기 없음"
---

## 한 줄 결론
`.gitattributes` 수정은 지시문대로 끝났고 새 범위 25개가 기대한 상태가 됐다. **기존 실패 16건 중 14건만 통과했다.** 남은 2건은 줄바꿈이 아니라 Acceptance가 묶은 구현 파일 10개가 2026-10-07 뒤에 바뀐 탓이라 `.gitattributes`로 고칠 수 없다. 기준 커밋 6aea772, 브랜치 worktree-gitattr-bytes. BLOCKED 없음.

## (a) .gitattributes 바뀐 줄
기존 4줄은 그대로다. 그 뒤에 지시문의 `-text` 4줄, 주석 1줄, `text` 7줄을 더했다. `workspace/policies/**` 전체, `manage-us-stock-strategy/assets/**`, `integrated_identity_session_activation.json`에는 걸지 않았다.

## (b) checkout 뒤 git ls-files --eol
| 파일 | i/ | w/ | attr |
|---|---|---|---|
| workspace/research/provider-evidence/kiwoom/2026-10-07/835d4f46…/session-aware-priority-acceptance-inactive-superseding-candidate.json | lf | lf | -text |
| workspace/policies/instrument_identity_activation.json | lf | lf | -text |
| workspace/policies/session_calendar_activation.json | lf | lf | -text |
| workspace/instrument-identity-authority/source-packets/0e12b713…/us-equity-instrument-identity-current-v1.sources.json | lf | lf | -text |
| 예외: workspace/research/provider-evidence/kiwoom/2026-08-14/session-aware-priority-acceptance.json | lf | crlf | text |

새 범위 전체는 25개다. `attr/-text` + `w/lf` 18개, `attr/text` + `w/crlf` 7개다.

## (c) 시험 결과
| 시험 | 수정 전 | 수정 뒤 마지막 3줄 |
|---|---|---|
| test_gitattributes_authority_bytes.py | 새 파일 | Ran 2 tests in 0.302s / 빈 줄 / OK |
| test_v2_6_7_session_aware_kiwoom_priority.py | 42건 중 14건 실패 | Ran 42 tests in 0.452s / 빈 줄 / FAILED (failures=2) |
| test_instrument_identity_authority.py | 24건 중 1건 실패 | Ran 24 tests in 0.368s / 빈 줄 / OK |
| test_materialize_instrument_identity_artifact.py | 62건 중 1건 실패 | Ran 62 tests in 2.349s / 빈 줄 / OK |

기존 실패 16건 중 14건 통과, 2건 실패(아래 절).

## 남은 2건 (제안서 기대와 다른 점)
- 시험: `InvariantAndContractTests.test_extended_provider_scope_candidate_validates_without_activation`(시험 파일 324행), `InvariantAndContractTests.test_guarded_priority_requires_locked_acceptance_manifest`(435행).
- 실패 문구: `implementation hash mismatch` 10건.
- 비교 방식: validate_kiwoom_session_aware_acceptance.py 75~76행이 `normalized_text_sha256`으로 비교한다. 이 함수는 CRLF를 LF로 바꾼 뒤 해시한다(validate_skill_deployment.py 23~26행). 그래서 줄바꿈은 원인이 아니다.
- 확인: Acceptance 835d4f46의 `implementation_hashes` 27개를 같은 방식으로 다시 쟀다. 이 worktree 10개, 본 저장소 10개가 어긋났고 두 목록이 같다.
- 어긋난 10개와 마지막 변경 커밋(Acceptance 커밋 e25edd1, 2026-10-07 뒤):
  - 510961a (2026-10-10): assets/kiwoom-acceptance-pin-scope.json, schemas/kiwoom-acceptance-pin-scope.schema.json, schemas/kiwoom-cash-flow-evidence.schema.json, schemas/kiwoom-reconciliation-proposal.schema.json, scripts/apply_user_confirmed_broker_snapshot.py, scripts/cash_flow_evidence.py, scripts/kiwoom_broker_shadow.py, scripts/manual_data_guards.py
  - 9bfc7f4 (2026-10-25): scripts/kiwoom_account_readonly_bridge.py
  - 2aa1535 (2026-10-25): scripts/reconcile_broker_state.py
- 왜 지금 보였나: 수정 전에는 두 시험이 `current_acceptance_manifest_path`(92~100행)에서 먼저 실패해 이 검사까지 가지 못했다. 파일을 찾게 되자 뒤의 검사가 드러났다. 그래서 본 저장소에서도 같은 2건이 실패할 것이다(해시 비교로 확인, 본 저장소에서 시험을 돌리지는 않음).
- 관련 규칙: CLAUDE.md는 Kiwoom acceptance pin이 T1로 폐지됐다고 적는다. 이 2건은 폐지 뒤에도 옛 구현 해시를 요구한다. 시험 수정은 이 작업의 범위 밖이라 하지 않았다.
- 결과: 병합 뒤 남는 기준선 실패는 제안서의 13건이 아니라 15건으로 예상한다(29 − 14).

## (d) git status --short
```
 M .gitattributes
?? docs/claude/gitattr-bytes-report.md
?? manage-us-stock-strategy/tests/test_gitattributes_authority_bytes.py
```

## (e) 7개 예외 말고 새 범위 안의 w/crlf
없음.

## 지시문과 다른 점
1. 작업 위치: 새 세션을 원격 연결에서 시작할 수 없어, 실행 스레드의 기존 worktree(.claude/worktrees/epic-kilby-606390)를 6aea772로 옮겨 새 브랜치 worktree-gitattr-bytes를 만들고 여기서 작업했다. 그 worktree에는 자기 커밋도 변경도 없었다.
2. 4번 앞 명령 1개 추가: `git ls-files -s -- <4번과 같은 경로> | git update-index --index-info`. 임시 저장소에서 색인 stat이 깨끗하면 `git checkout -- <경로>`가 파일을 다시 쓰지 않고 w/crlf로 남는 것을 재현했다. 이 worktree에서도 속성을 바꾼 뒤 `git status`에는 `.gitattributes`만 보여 같은 상태였다. 이 명령은 색인의 시각 정보만 비우고 파일 내용은 바꾸지 않는다. 4번 checkout은 글자 그대로 한 번 실행했다.
3. 지시문이 허용하지 않은 읽기 전용 확인: 수정 전 시험 3줄 실행, 남은 2건 원인을 찾으려고 `python -`로 해시 비교와 시험 1건 재실행, `git show`·`git log`·`git rev-list`·`git branch`·`git config --show-origin`. 파일은 고치지 않았다.
4. 원인 확인: 회사PC git 시스템 설정이 `core.autocrlf=true`다(C:/Program Files/Git/etc/gitconfig). 제안서의 "확인 필요"가 풀렸다.

## 사장 결정 (2026-11-02)
- 원문: "14건으로 진행". 사장 직접 입력, 실행 스레드 메시지 cmsg_0137MRzn9nuDvvQmVxm6WeX93WouHSSotdmAA2gG65aZHX, 계정 user_01KuMGKfZu1SBYxtMmg4vAiH, 2026-11-02 19:12:19 KST.
- 뜻: 16건 중 14건 회복을 기준으로 Judge까지 진행한다. Judge 지시문 6번은 "14건 통과, 2건은 별도 원인임을 확인"으로 읽는다. 남은 2건의 시험 수정은 범위 밖 별도 안건이다. 병합은 별도 사장 결정.

표지 없음.
