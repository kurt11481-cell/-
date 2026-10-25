# Builder: dcdev-claudemd — record decision dc-dev in CLAUDE.md and the dev pipeline README

Manual route (protected paths). Builder in worktree `dcdev-claudemd`. Docs/text only: no code, no tests change.
User decision: "결정 dc-dev: Q1 a, Q2 a" (2026-10-22 15:17 KST). Procedure doc (not yet committed, read it from the main checkout): E:\사업\##금동한\코덱스저장소\docs\claude\dc-dev-2026-10-22.md (read it first).

## Allowed files (change nothing else)
- CLAUDE.md
- tools/dev_pipeline/README.md
- docs/claude/dcdev-claudemd-report.md (new, your report)

Both files are UTF-8 with CRLF line endings. Keep CRLF, keep every other line byte-identical. Use the Edit tool only.

## Changes
1. CLAUDE.md, section "## Change classes", bullet "General change": replace the clause
   `merge = the user runs `.\tools\dev-merge.ps1 <id>` once.`
   with
   `merge: when result.json is READY_TO_MERGE (class general, tests and Judge PASS), Cowork runs `.\tools\dev-merge.ps1 <id>` on the PC itself via Desktop Commander and reports the result, never with -ApproveAuthority (user decision dc-dev Q1 a, 2026-10-22, docs/claude/dc-dev-2026-10-22.md).`
2. CLAUDE.md, same section, bullet "Authority/limit change": after `stop, user approval, independent Judge (manual route).` insert
   ` After the user's approval Cowork may launch the manual-route Builder (worktree) and a separate read-only Judge session on the PC (dc-dev Q2 a); the merge still waits for the user's decision.`
3. CLAUDE.md, section "## Session hygiene", bullet starting "Manual route": after `then a Judge in a separate session that never edits files.` insert
   ` Cowork may start both on the PC via Desktop Commander after the user's approval (dc-dev Q2 a).`
4. tools/dev_pipeline/README.md:
   - line 3: replace `사용자는 `.\tools\dev-merge.ps1 <id>` **1번**.` with `READY_TO_MERGE면 Cowork가 PC에서 `.\tools\dev-merge.ps1 <id>`를 실행한다(사장 결정 dc-dev Q1 a, 2026-10-22 — docs/claude/dc-dev-2026-10-22.md).`
   - line 11 (step 4): replace `4. 사용자: `.\tools\dev-merge.ps1 <id>` 1번 (authority면 사용자 결정 뒤 `-ApproveAuthority`).` with `4. Cowork: `.\tools\dev-merge.ps1 <id>` (authority면 사장 결정 뒤 `-ApproveAuthority`).`
   - status table row READY_TO_MERGE, column "다음": `사용자 `.\tools\dev-merge.ps1 <id>`` → `Cowork가 `.\tools\dev-merge.ps1 <id>` 실행 후 알림`
   - status table row NEEDS_APPROVAL, column "다음": `사용자 결정 → `.\tools\dev-merge.ps1 <id> -ApproveAuthority`` → `사장 결정 → Cowork가 `.\tools\dev-merge.ps1 <id> -ApproveAuthority``
   If any quoted old text is not found exactly once, stop and write BLOCKED.md in the worktree root with the reason (do not guess).

## Do not
- Change any rule other than these sentences. Do not touch safety, order, Kiwoom, reconciliation, journal or secret rules.
- Do not run dev-run, dev-merge or dev-queue. Do not push. Do not read .env* or secrets.

## Finish
- Report docs/claude/dcdev-claudemd-report.md: changed lines (before/after), byte check that line endings stayed CRLF, `git diff --stat`.
- Commit in the worktree branch: `docs(rules): dc-dev Q1 a/Q2 a — Cowork runs dev-merge and launches manual-route Builder/Judge`.

## Judge 확인 항목
- J1 Only the 3 allowed files changed; diff limited to the sentences above.
- J2 No existing constraint was loosened beyond the decision: -ApproveAuthority still only after the user's decision; authority changes still stop for user approval and an independent read-only Judge; Claude Code sessions still never run dev-run/dev-merge/dev-queue.
- J3 Wording matches docs/claude/dc-dev-2026-10-22.md 0절.
- J4 CRLF preserved, no other line changed (byte-identical outside the edits).
