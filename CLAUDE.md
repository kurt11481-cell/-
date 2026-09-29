# Investment_V2 — Claude Code rules

Read-only U.S. stock research and portfolio decision support. No execution authority.

## Hard safety
- Never place, modify, cancel, or schedule a brokerage order. Never call Kiwoom order tools.
- Never infer fills from price moves. Change holdings, cash, stage, cost basis, or fills only
  from explicit user confirmation or a verified read-only broker snapshot.
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
- Ignore the context-mode section of AGENTS.md (Codex only).

## Working rules
- Files are CRLF on Windows and some evidence hashes raw bytes: never bulk-convert line endings.
- Tests: python -m unittest discover -s manage-us-stock-strategy/tests -p "test_<name>.py"
  Run targeted files first; run the full suite in a subagent and report failures only.
- Schema audit: python manage-us-stock-strategy/scripts/validate_schema_contracts.py
- Identifiers, schemas, commands in English; user-facing reports in Korean.
- Do not commit or push unless asked. Never force-push.

## Compact instructions
Keep: current goal, changed files, failing tests, approvals given, open K3 items.
