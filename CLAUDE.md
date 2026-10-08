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
- Review-journal entries (stock-strategy-system/decision_journal.json) are written only through `portfolio_review_journal.py apply`, run in Cowork after the user sends "확인 <code>" for that proposal in the current conversation, or by the user in their own terminal. Claude Code, Codex, scheduled tasks and Judge sessions never run apply or edit the journal directly; never type or guess the code or reuse an earlier confirmation.
- Never edit approved policy (stock-strategy-system/alert_policy.json, workspace/policies/*)
  or portfolio state without explicit user approval in this session.
- Never read or print secrets (.env*, tokens, account numbers).
- Missing or stale data stays visible and fails closed. Deterministic rules outrank LLM output.

## Kiwoom query rules (standing user rule 2026-10-07)
- Every read-only `kiwoom_query` call (Cowork, Claude Code, Codex, scheduled tasks, Manual runs) must pass options `"profile": "실전계좌"` and `"mode": "real"`. Without the profile the call uses an old token and fails with 8005. Bridge code reads the same alias from policy key `token_profile_alias` in workspace/policies/kiwoom-readonly-policy.json.
- On 8005 or any auth error: do not run auth, login or token reissue (it can invalidate another task's token). Mark that query failed, keep the gap visible (fail closed) and report it.
- This fixes the token profile only. It adds no authority: never inject `confirm`, never call order tools, and targets and filters stay as approved.
- New scheduled tasks and manual calls follow the same rule (checklist: docs/claude/analysis-linkage-map-2026-10-05.md). Evidence: docs/claude/kiwoom-profile-prompt-change-2026-10-06.md.

## Change classes
- K0 wording / K1 output behavior / K2 runtime contract or validator (targeted tests) /
  K3 production semantics or authority (stop, ask the user, independent Judge).
- Kiwoom acceptance pins the files listed in manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json
  (normalized text hashes). Editing a listed file invalidates the active acceptance: treat it as K3.
  run_manual_portfolio_analysis.py is not pinned; its guards live in pinned manual_data_guards.py and scheduled_input_gate.py.

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
  Run targeted files first; run the full suite with the `test-runner` subagent (Haiku) and report failures only.
- Haiku subagents (user approval 2026-10-08, docs/claude/haiku-5-5-review-2026-10-08.md): `test-runner` and
  `summarizer` (in Cowork: Agent model "haiku") only for mechanical work: test runs, log/JSON/file summaries,
  locating files. Never for investment judgment, cards, order prices/quantities, K2/K3 review or Judge.
  Their output is a locator, not evidence: re-read the source before deciding. Do not set CLAUDE_CODE_SUBAGENT_MODEL*.
- Schema audit: python manage-us-stock-strategy/scripts/validate_schema_contracts.py
- Identifiers, schemas, commands in English; user-facing reports in Korean.
- Do not commit or push unless asked. Never force-push.
- Every analysis/inquiry/discovery output must be linked: write results where other tasks read them and name at least one consumer (docs/claude/analysis-linkage-map-2026-10-05.md, user standing rule 2026-10-05).
- Option layer for order prices (user approval 2026-10-07, docs/claude/order-instruction-design-2026-10-06.md section 7-5): every buy or sell price proposed in any session (limit, LOC cap or floor, ladder, ad-hoc price suggestion) is checked against option layer O1~O4 (CBOE delayed chain, Yahoo fallback, snapshot time shown), and the result (일치 / 경고 + 이유 1줄) is written next to the price. It is a cross-check and warning, not a trade reason and not a price-formula input; changing the formula is K3. If option data is missing write "옵션 층: 확인 필요(사유)" and continue.
- Council before any order recommendation (user approval 2026-10-08, docs/claude/order-instruction-design-2026-10-06.md section 6): every buy or sell recommendation or instruction that carries a quantity or price (official, pilot, Cowork ad-hoc recommendation, user manual-decision instruction) goes through the decision-council BEFORE it is shown to the user for a decision. Lite by default; Full when the order is >= 10% of equity, a sell-only product, or uses a first-time rule or exception (e.g. user-recognized evidence). Write the 4 voice lines, strongest dissent, pre-mortem and pre-celebration into the instruction; without that section do not issue it. The council can only lower, hold or require confirmation, never raise, and is not trade evidence. Not required for analysis or scenario comparison without quantity/price, or for scheduled checks.
- Recovery gate R-REC1 (user instruction 2026-10-09, docs/claude/recovery-gate-R-REC1-2026-10-09.md): while a shock event is open (SOXX close <= -2 sigma60, 20-session drawdown >= 3 sigma60, user/check-designated root-thesis news shock, account line L1, or a candidate's own -2 sigma60 day), every exposure-increasing buy needs RG1 thesis (no official damage within 2 sessions), RG2 trend (benchmark and candidate close >= EMA50), RG3 shock absorbed (2 closes above event close, no new low below the event-day low), RG4 volatility normalized. It only blocks or delays buys: never blocks sells, never counts as trade evidence, never raises the budget; missing data fails closed for buys. Rule candidate until replay + Judge (K3).

## Session hygiene (투자_V2 setup guide, apply automatically)
- At task start, state the recommended model/effort in one line: simple = low, routine = medium,
  analysis/dev = high, cross-file design / K3 / Judge = Opus xhigh. If the model differs, ask the
  user to restart with it; never suggest switching model mid-session (it rebuilds the prompt cache).
  Effort may change mid-session only in Claude Code on Opus 5.5 / Sonnet 5.5 (`/effort`, cache kept);
  elsewhere restart (docs/claude/prompt-caching-review-2026-10-09.md).
- When the topic changes, tell the user to run /clear; if the task continues but context is long,
  suggest /compact at a natural stopping point.
- Before multi-file edits, present a plan first (or ask the user to press Shift+Tab for plan mode).
- Builder work runs in a worktree (claude --worktree <name>); a Judge runs in a separate session
  and never edits files.
- Talk to the user in Korean, one step at a time, giving the exact command to type.
- Cowork 세션에서 작업 상태가 바뀌었으면(완료·시작·새 재개 조건), 세션 끝에 한 번 docs/claude/dev-dashboard-protocol.md대로 관제판의 바뀐 작업만 갱신한다. 변화가 없으면 갱신하지 않는다. Claude Code·Judge·예약 작업은 갱신하지 않는다.

## Compact instructions
Keep: current goal, changed files, failing tests, approvals given, open K3 items.
