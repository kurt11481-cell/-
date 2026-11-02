---
id: gitattr-bytes-builder-prompt
title: "권한 파일 CRLF 변환 막기 — gitattr-bytes Builder"
date: 2026-11-02
class: "K3 수동 경로(.gitattributes 보호 이름). 회사PC worktree Builder(Opus) → 별도 읽기 전용 Judge → 병합은 사장 결정 뒤 사장 PowerShell"
source: "docs/claude/gitattr-bytes-proposal-2026-11-02.md, 사장 결정 카드 cmsg_0137MRzn9nuDvvQmVxm6WeX9TgpMChM1zTDtQqpkkgaTUU '승인, 오늘 진행' 2026-11-02 18:54 KST"
authority: "order_authority=false · quantity_authority 값 변경 없음 · 키움 호출 없음 · 정책 내용·상태·일지·원장 쓰기 없음"
---

## 목표
worktree가 원본 바이트로 해시·정규형 검사하는 권한 파일을 CRLF로 받지 않게 한다. 그러면 개발 큐 기준선 실패 16건(test_v2_6_7_session_aware_kiwoom_priority 14, test_instrument_identity_authority test_15, test_materialize_instrument_identity_artifact test_candidate_support_does_not_replace_active_registry)이 통과해야 한다.

## 바꿀 파일 (이 3개만)
- .gitattributes
- manage-us-stock-strategy/tests/test_gitattributes_authority_bytes.py (새 파일)
- docs/claude/gitattr-bytes-report.md (보고)

## 구현 요구
1. `.gitattributes`의 기존 줄은 그대로 둔다. 아래 4줄을 기존 `-text` 2줄 뒤에 더한다.
```
workspace/research/provider-evidence/** -text
workspace/instrument-identity-authority/** -text
workspace/policies/instrument_identity_activation.json -text
workspace/policies/session_calendar_activation.json -text
```
2. 파일 맨 뒤에 주석 1줄과 아래 7줄을 둔다. 이 7개는 본 저장소에 이미 CRLF로 있는 2026-08 지난 증거다. 그중 하나는 CRLF 바이트 해시가 다른 기록에 적혀 있다. 그래서 받는 방식을 지금 그대로 유지한다.
```
workspace/instrument-identity-authority/rejudge-runs/2026-08-28/k3-identity-binding-repair/run_manifest.json text
workspace/research/provider-evidence/kiwoom/2026-08-13/acceptance-manifest.json text
workspace/research/provider-evidence/kiwoom/2026-08-14/mvll-canonical-volume-lineage.json text
workspace/research/provider-evidence/kiwoom/2026-08-14/mvll-volume-authority-acceptance.json text
workspace/research/provider-evidence/kiwoom/2026-08-14/session-aware-priority-acceptance.json text
workspace/research/provider-evidence/kiwoom/2026-08-28/k3-authority-candidate-builder-run-manifest.json text
workspace/research/provider-evidence/kiwoom/2026-08-29/k3-normalized-candidate-repair/run_manifest.json text
```
3. `workspace/policies/**` 전체, `manage-us-stock-strategy/assets/**`, `workspace/policies/integrated_identity_session_activation.json`에는 걸지 않는다.
4. worktree의 파일을 새 속성대로 다시 받는다. 이 명령 한 번만, 글자 그대로 쓴다: `git checkout -- workspace/research/provider-evidence workspace/instrument-identity-authority workspace/policies/instrument_identity_activation.json workspace/policies/session_calendar_activation.json`. 실행한 뒤 `git status --short`에 위 3개 파일 말고 다른 변경이 없어야 한다. 다른 변경이 있으면 BLOCKED.md에 적고 멈춘다.
5. 새 시험 `test_gitattributes_authority_bytes.py`를 만든다. 대표 파일마다 `git check-attr text -- <path>`의 값이 `unset`인지 확인한다. 대표 파일은 아래 4개다.
   - kiwoom/2026-10-07/835d4f46…/session-aware-priority-acceptance-inactive-superseding-candidate.json
   - workspace/policies/instrument_identity_activation.json
   - workspace/policies/session_calendar_activation.json
   - workspace/instrument-identity-authority 아래 source-packets 파일 1개

   같은 시험에서 위 7개 예외 중 1개는 값이 `set`인지 확인한다. git은 subprocess로 저장소 루트(`Path(__file__).resolve().parents[2]`)에서 부른다. git이 없으면 시험이 실패해야 한다(skip 금지).
6. 기존 시험 파일·단언은 바꾸지 않는다.

## 시험 (이 4줄만, 글자 그대로)
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_gitattributes_authority_bytes.py"`
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_v2_6_7_session_aware_kiwoom_priority.py"`
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_instrument_identity_authority.py"`
- `python -m unittest discover -s manage-us-stock-strategy/tests -p "test_materialize_instrument_identity_artifact.py"`

전체 스위트는 돌리지 않는다. git은 status·diff·log·ls-files·check-attr, 그리고 위 4번 checkout 한 번만 쓴다. `python -c` 같은 다른 셸 작업은 하지 않는다.

## 지켜야 할 것
- 위 3개 파일 밖은 손대지 않는다. tools/·.claude/·.gitignore·.worktreeinclude·정책 내용·상태 금지.
- `.gitattributes`의 원래 줄바꿈을 지킨다.
- 주문·키움·정책·상태·일지·원장·예약과 무관하다. auto_core.py·kiwoomcli 실행 금지. git commit·push·병합 없음.
- 판단이 안 되면 BLOCKED.md(첫 줄 = 이유)를 쓰고 멈춘다.

## 보고 docs/claude/gitattr-bytes-report.md
- (a) `.gitattributes` 바뀐 줄
- (b) checkout 뒤 `git ls-files --eol` 결과: 대표 파일 4개와 예외 1개의 i/·w/·attr 칸
- (c) 시험 4개 각각의 마지막 3줄. 특히 기존 실패 16건이 통과했는지
- (d) `git status --short` 결과
- (e) 7개 예외 말고 새 범위 안에서 w/crlf인 파일이 남았는지(파일 이름만)

수량·금액·주문 표지 문자열은 적지 않는다("표지 없음").
