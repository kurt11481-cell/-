# Investment_V2 — Claude Code rules

Read-only U.S. stock research and portfolio decision support. No execution authority.

## Hard safety
- Never place, modify, cancel, or schedule a brokerage order. Never call Kiwoom order tools.
- Never infer fills from price moves. Change holdings, cash, stage, cost basis, or fills only
  from a verified read-only broker snapshot AND the user's explicit confirmation of that proposal.
- Broker reconciliation writes state only through `reconcile_broker_state.py apply`, run in Cowork
  after the user sends "확인 <code>" for that proposal in the current conversation, or by the user
  in their own terminal. Never type or guess the code and never reuse an earlier confirmation.
  Claude Code, Codex, scheduled tasks and Judge sessions never run apply. Before applying, read
  manage-us-stock-strategy/references/broker-snapshot-reconciliation.md.
- Never edit approved policy (stock-strategy-system/alert_policy.json, workspace/policies/*)
  or portfolio state without explicit user approval in this session.
- Never read or print secrets (.env*, tokens, account numbers).
- Missing or stale data stays visible and fails closed. Deterministic rules outrank LLM output.

## Change classes
- K0 wording / K1 output behavior / K2 runtime contract or validator (targeted tests) /
  K3 production semantics or authority (stop, ask the user, independent Judge).
- Kiwoom acceptance manifests pin implementation hashes. Editing a pinned script
  (e.g. run_manual_portfolio_analysis.py) invalidates the acceptance: treat it as K3.

## Repo map
- Skill source: manage-us-stock-strategy/ (SKILL.md, scripts/, schemas/, tests/, references/)
- State: stock-strategy-system/portfolio_state.json
- Policy: stock-strategy-system/alert_policy.json; runtime: alert_runtime_state.json
- Production authority: workspace/policies/integrated_identity_session_activation.json
- Code map (locator only, never evidence): graphify-out/GRAPH_REPORT.md
- Procedures, read only when needed: manage-us-stock-strategy/references/
  development-*.md, kiwoom-*.md, jay-earnings-discovery.md
- Handover and review notes: docs/claude/ (read when resuming work)
- Ignore the context-mode section of AGENTS.md (Codex only).

## Working rules
- Files are CRLF on Windows and some evidence hashes raw bytes: never bulk-convert line endings.
- Tests: python -m unittest discover -s manage-us-stock-strategy/tests -p "test_<name>.py"
  Run targeted files first; run the full suite in a subagent and report failures only.
- Schema audit: python manage-us-stock-strategy/scripts/validate_schema_contracts.py
- Identifiers, schemas, commands in English; user-facing reports in Korean.
- Do not commit or push unless asked. Never force-push.

## Session hygiene (투자_V2 setup guide, apply automatically)
- At task start, state the recommended model/effort in one line: simple = low, routine = medium,
  analysis/dev = high, cross-file design / K3 / Judge = Opus xhigh. If the session differs, ask the
  user to restart with it; never suggest switching model or effort mid-session.
- When the topic changes, tell the user to run /clear; if the task continues but context is long,
  suggest /compact at a natural stopping point.
- Before multi-file edits, present a plan first (or ask the user to press Shift+Tab for plan mode).
- Builder work runs in a worktree (claude --worktree <name>); a Judge runs in a separate session
  and never edits files.
- Talk to the user in Korean, one step at a time, giving the exact command to type.
- Cowork 세션에서 작업 상태가 바뀌었으면(완료·시작·새 재개 조건), 세션 끝에 한 번 docs/claude/dev-dashboard-protocol.md대로 관제판의 바뀐 작업만 갱신한다. 변화가 없으면 갱신하지 않는다. Claude Code·Judge·예약 작업은 갱신하지 않는다.

## Compact instructions
Keep: current goal, changed files, failing tests, approvals given, open K3 items.
