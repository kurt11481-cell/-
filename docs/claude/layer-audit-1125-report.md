---
id: layer-audit-1125-report
date: 2026-11-25
source: docs/claude/layer-audit-1125-builder-prompt.md (K3 manual-route Builder)
---

# layer-audit-1125 ④⑤ Builder 보고서

## (a) 기준 커밋·경로·브랜치
- 기준 커밋: f90cf00558357fbabf0c1a2a26de23e6ce911eac (메인 체크아웃 HEAD, 브랜치 codex/master-recovery-expansion — 지시문의 해시와 같음, 움직이지 않음)
- 작업 폴더: E:/사업/##금동한/코덱스저장소/.claude/worktrees/friendly-rosalind-adb7d5
- 브랜치: worktree-layer-audit (`git switch -C worktree-layer-audit f90cf00…`)
- 선행 조건(메인 체크아웃): CLAUDE.md 48464bb4…a8569da, AGENTS.md 621c139f…bbb9149, apply.py 8ff54bb0…011491c — 모두 일치
- 스크립트 출력(그대로, exit 0):
  - `OK CLAUDE.md cd0868ce97165d4c605c9e558b023b85ef9dcc0575ab5000797eaae5093ad63c`
  - `OK AGENTS.md c07e509436fff943054a90f58c8f7f7bde3caddc77c953eab71de43a44ecf718`

## (b) 두 파일 전후
| 파일 | 전 sha256 | 후 sha256 | 줄 수 전→후 | CRLF 수 전→후 |
|---|---|---|---|---|
| CLAUDE.md | 48464bb4e5f462707ff0a7a42840c8affb61c48b18183332731f6efe0a8569da | cd0868ce97165d4c605c9e558b023b85ef9dcc0575ab5000797eaae5093ad63c | 155→159 | 155→159 |
| AGENTS.md | 621c139f6042ffbe8c6999eafe195170568d0ecd76b59f9e3027da542bbb9149 | c07e509436fff943054a90f58c8f7f7bde3caddc77c953eab71de43a44ecf718 | 190→192 | 190→192 |

(줄 수 = LF 개수. 모든 LF가 CRLF — 줄바꿈 유지.)

## (c) CLAUDE.md '## Hard safety' ~ '## Kiwoom query rules' 앞 바이트 해시
- 전: 87fa6d373b36a4939f8a5700d24f2e67f2b0e2b6888701b8522946242a4799b4 (바이트 1323~6864)
- 후: 87fa6d373b36a4939f8a5700d24f2e67f2b0e2b6888701b8522946242a4799b4 (바이트 1936~7477)
- 같음(구간 위치만 Precedence 문단 길이만큼 밀림).

## (d) git diff
```
 AGENTS.md | 2 ++
 CLAUDE.md | 8 ++++++--
 2 files changed, 8 insertions(+), 2 deletions(-)
```
`git diff -U0` 묶음:
- AGENTS.md `@@ -2,0 +3,2 @@` (제목 뒤 빈 줄 + Codex 안내 줄)
- CLAUDE.md `@@ -9,0 +10,2 @@` (Precedence 문단 + 빈 줄)
- CLAUDE.md `@@ -99,0 +102,2 @@` (Constitution·Scheduled tasks 위치 줄 2개, Kiwoom acceptance pin 앞)
- CLAUDE.md `@@ -109 +113 @@` (Instrument identity/calendar authority 이름 정정)
- CLAUDE.md `@@ -132 +136 @@` (SCN-27H1 줄 끝 Premise B0 효력 정지 문장)

## (e) 시험 결과 마지막 줄
1. test_reconcile_broker_state.py — `Ran 57 tests` / `OK`
2. test_cowork_to_room_k3.py — `Ran 33 tests` / `OK`
3. test_scheduled_prompt_kiwoom_profile.py — `Ran 8 tests` / `FAILED (failures=1)`
   - 실패: test_all_scheduled_prompts_state_profile_and_mode — 위반 파일 `docs/claude/scheduled-prompts/pending-wl-fetch-1122/diff.txt`.
   - 판단: 이번 변경과 무관한 기존 실패. 이 시험은 docs/claude/scheduled-prompts/ 아래 *.txt만 훑고(테스트 13·69행), 위반 파일은 기준 커밋 이전 b25f569에서 들어왔으며 이번 작업에서 바뀌지 않음(git status에 없음). CLAUDE.md·AGENTS.md 바이트는 이 시험의 입력이 아님. 처리 여부는 별도 안건(이 지시문 범위 밖이라 손대지 않음).

## (f) git status --short
```
 M AGENTS.md
 M CLAUDE.md
?? .claude/
?? workspace/outputs/lmt-instrument-registry-candidate-prep/
?? workspace/outputs/manual-portfolio-analysis/
```
(+ 이 보고서 docs/claude/layer-audit-1125-report.md. `?? .claude/`·workspace/outputs 두 폴더는 작업 전부터 있던 미추적 항목.)

커밋·푸시·병합·리셋 하지 않음. 키움·주문·정책·상태·일지·원장·비밀 접근 없음.
