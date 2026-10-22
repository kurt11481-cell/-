# dcdev-claudemd Builder report (2026-10-22)

Builder: Cowork (Desktop Commander edits in worktree `dcdev-claudemd`). The headless Claude Code Builder (`claude -p --worktree dcdev-claudemd`, sonnet high) ran first and stopped without changes: project settings `.claude/settings.json` put `Edit(/CLAUDE.md)`, `Edit(/tools/**)` and `Bash(git commit:*)` under "ask", which a non-interactive session cannot answer, and it did not work around that (its output: workspace/outputs/dev-runs/_manual/dcdev-claudemd-builder.txt, UTF-16).

Decision: "결정 dc-dev: Q1 a, Q2 a" (2026-10-22 15:17 KST), procedure docs/claude/dc-dev-2026-10-22.md.

## Changes
- CLAUDE.md Change classes / General change: "merge = the user runs `dev-merge` once" -> Cowork runs `.\tools\dev-merge.ps1 <id>` itself when READY_TO_MERGE (class general), never with -ApproveAuthority (dc-dev Q1 a).
- CLAUDE.md Change classes / Authority change: added "After the user's approval Cowork may launch the manual-route Builder (worktree) and a separate read-only Judge session on the PC (dc-dev Q2 a); the merge still waits for the user's decision."
- CLAUDE.md Session hygiene / Manual route: added "Cowork may start both on the PC via Desktop Commander after the user's approval (dc-dev Q2 a)."
- tools/dev_pipeline/README.md: line 3, step 4, status table rows READY_TO_MERGE and NEEDS_APPROVAL ("사용자" -> "Cowork", authority after 사장 결정).

## Checks
- Line endings: each edit kept CRLF; count of bare LF unchanged in both files (python check at write time).
- Sizes: CLAUDE.md 17,498 -> 18,028 B (sha256 bb8e44b066c1...), README 10,882 -> 11,003 B (2a49004eece6...).
- Unchanged on purpose: "Claude Code sessions never run dev-run/dev-merge/dev-queue", settings deny/ask rules, all safety/order/reconciliation/journal rules.

## Fix round 1 (after Judge PASS with findings, 2026-10-22 15:4x)
- Judge finding 1 (important): -ApproveAuthority and the authority approval now require the user's decision stated in the current conversation (CLAUDE.md Change classes; README step 4 and NEEDS_APPROVAL row) — never from an older record or memory.
- Judge finding 2: Manual route line now also says the merge waits for the user's decision.
- Judge finding 5: stale "user runs dev-merge" wording fixed in tools/dev_pipeline/builder-rules.md and docs/claude/dev-dashboard-protocol.md. tools/dev-merge.ps1 header comment left as is (script file, comment only — not worth touching a protected script).
- Judge finding 4: docs/claude/dc-dev-2026-10-22.md is untracked in the main checkout and is committed by the 23:30 docs commit (adding it to this branch would block the fast-forward merge).
- Judge finding 6: recorded in dc-dev-2026-10-22.md section 3 by Cowork (headless Builder cannot edit ask-protected paths; settings change needs a separate user decision).
