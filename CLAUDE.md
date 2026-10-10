# Investment_V2 — Claude Code rules

U.S. stock portfolio system moving to automated operation (redesign 2026-10-10). Broker access is read-only;
no order execution authority until order stage 2 is approved (redesign 3-6).

## Goal (user decision 2026-10-10, docs/claude/automation-redesign-2026-10-10.md)
- Automated operation is the top priority: a deterministic daily auto-core (collect -> reconcile -> compute ->
  order ticket -> journal -> exception alert). LLMs work at the edge (research, explanation, development) and
  their failure never blocks the core. The user receives results only.
- If an automation design is blocked or a routine step needs the user, treat it as a severe defect and fix it by
  removing human steps, not adding them. Read-only work Cowork can do itself is done, not handed to the user.
- Routine user touches target 0, except Kiwoom order entry until order stage 2.

## Hard safety
- Never place, modify, cancel, or schedule a brokerage order. Never call Kiwoom order tools.
- Never infer fills from price moves; fills come only from broker fill records. Change holdings, cash or cost
  basis only from a verified read-only broker snapshot; stage and strategy fields never change from a snapshot.
  Cash = Kiwoom order-available amount (fc_ord_alowa; user 2026-10-09/10-10: sale proceeds are usable right after the fill).
- Broker reconciliation writes state only through the auto-core when every invariant in
  docs/claude/automation-redesign-2026-10-10.md 3-5 passes; otherwise state stays unchanged and an alert is sent (no human code).
  Transition until T1 recording is switched on: `reconcile_broker_state.py apply` runs in Cowork after the user sends
  "확인 <code>" for that proposal in the current conversation, or by the user in their own terminal; never type or guess
  the code or reuse one. Claude Code, Codex, scheduled LLM tasks and Judge sessions never run apply. Before applying,
  read manage-us-stock-strategy/references/broker-snapshot-reconciliation.md.
- Review-journal entries (stock-strategy-system/decision_journal.json) are append-only and written only through
  `portfolio_review_journal.py` (later the auto-core). In Cowork the user's explicit decision message in the current
  conversation is the confirmation: propose, then apply in the same session with that proposal's own code,
  `--confirmed-via COWORK_CHAT_USER_MESSAGE` and the user's decision text verbatim (redesign A3, 2026-10-10). Never
  apply for a decision the user did not state. Claude Code, Codex and Judge sessions never apply or edit the journal.
- Never edit approved policy (stock-strategy-system/alert_policy.json, workspace/policies/*)
  or portfolio state without explicit user approval in this session. The auto-core reconciliation under the
  redesign 3-5 invariants (after T1) is the approved exception for holdings, cash and cost basis only.
- Never read or print secrets (.env*, tokens, account numbers).
- Missing or stale data stays visible and fails closed. Deterministic rules outrank LLM output.

## Kiwoom query rules (standing user rule 2026-10-07)
- Every read-only `kiwoom_query` call (Cowork, Claude Code, Codex, scheduled tasks, Manual runs) must pass options `"profile": "실전계좌"` and `"mode": "real"`. Without the profile the call uses an old token and fails with 8005. Bridge code reads the same alias from policy key `token_profile_alias` in workspace/policies/kiwoom-readonly-policy.json.
- On 8005 or any auth error: do not run auth, login or token reissue (it can invalidate another task's token). Mark that query failed, keep the gap visible (fail closed) and report it.
- This fixes the token profile only. It adds no authority: never inject `confirm`, never call order tools, and targets and filters stay as approved.
- New scheduled tasks and manual calls follow the same rule (checklist: docs/claude/analysis-linkage-map-2026-10-05.md). Evidence: docs/claude/kiwoom-profile-prompt-change-2026-10-06.md.

## Change classes (redesign A5, 2026-10-10)
- General change (old K0-K2): targeted tests + 0 new failures vs baseline + independent Judge (headless pipeline
  after T3); merge = 1 user click. Docs-only changes need no Judge.
- Authority/limit change (old K3: order stage, order tools, budget/ceiling/caps, approved products, reconciliation
  invariants, kill switch): stop, user approval, independent Judge.
- Transition: the Kiwoom acceptance pin (manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json) is retired
  by redesign T1 and replaced by recording the git commit SHA in every run. Until that change is merged, editing a
  pinned file still invalidates the active acceptance: bundle such edits into the T1 Builder change.

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
- Option layer for order prices (2026-10-07, narrowed by redesign 2026-10-10): when option data exists, show the O1~O4 cross-check (일치 / 경고 + 이유 1줄, snapshot time) next to a proposed price; when it is missing, omit it. Display only: never a trade reason or price-formula input.
- Council (decision-council skill; redesign 2026-10-10 replaces the 2026-10-08 per-order rule): only for policy, limit or authority changes. Order tickets rely on deterministic gates. The council can only lower, hold or require confirmation and is not trade evidence.
- Recovery gate R-REC1 (user instruction 2026-10-09, docs/claude/recovery-gate-R-REC1-2026-10-09.md): while a shock event is open (SOXX close <= -2 sigma60, 20-session drawdown >= 3 sigma60, user/check-designated root-thesis news shock, account line L1, or a candidate's own -2 sigma60 day), every exposure-increasing buy needs RG1 thesis (no official damage within 2 sessions), RG2 trend (benchmark and candidate close >= EMA50), RG3 shock absorbed (2 closes above event close, no new low below the event-day low), RG4 volatility normalized. It only blocks or delays buys: never blocks sells, never counts as trade evidence, never raises the budget; missing data fails closed for buys. Rule candidate until replay + Judge (K3). Replay 2026-10-09: criterion a not met; user kept it as candidate (D).
- FX-1009 (user decision 2026-10-09, amended 2026-10-10 by redesign A2): until fx-6 of docs/claude/fx1009-fix-plan-2026-10-09.md, do not add new rule candidates or replay topics. Automation and redesign work (new scheduled or Windows tasks included) is allowed now.
- Scenario guideline SCN-27H1 (user decision 2026-10-09, docs/claude/market-scenario-27h1-2026-10-09.md, valid until 2027-06-30): system-wide market premise B0 = late-cycle bull market through 1H27 (conditional). Before a card, M6, order-instruction council or discovery acceptance, Cowork/Claude Code sessions run docs/claude/scn27h1-triggers.py in the cloud container (FRED) and write its first line "시나리오 SCN-27H1: 🟢|🟠|🔴 (…)"; on 🔴 ask the user once (keep / suspend, default suspend). Premise and display only: evidence weight 0, never raises budget, exposure ceiling or authority, never blocks sells, no automatic trades. FX-1009 freeze exception (user 2026-10-09 22:05): linked in the integrated check (loader 3단계), Next SanDisk monthly (step 10) and watchlist re-score (추가 단계) prompts; any later swap of those prompts (e.g. fx-2 v3.12.3-L) must carry the block (docs/claude/scheduled-prompts/README.md 변경 기록).
- Decision journal: when a card or order decision is accepted in Cowork, record the S7b entry in the same session as described in Hard safety (no separate confirmation code).
- Default disposition (user decision 2026-10-09 Q1, docs/claude/ops-dev-touch-reduction-2026-10-09.md R4): every replay, review or rule candidate pre-registers its default outcome. Criterion not met, or no user answer by the stated deadline → NO_CHANGE (current rule and policy kept); Cowork records it and only notifies. Ask the user only when the result proposes a change. A default never raises exposure, budget or authority; changes to policy, state, authority or orders still need explicit approval.
- Touch budget (2026-10-09 Q2, superseded 2026-10-10 by Goal): routine user touches target 0 except order entry. Every proposal states its weekly user-touch cost and may not add a routine touch. At most 3 active development tasks and 1 authority/limit change in progress at a time.
- Doc-only commits (user decision 2026-10-09 Q5; until the redesign T3 auto-commit task exists): when a Cowork session leaves docs/claude/ changes, write docs/claude/_pending/<task-id>.txt (line 1 = commit message, then one repo-relative path per line, docs/claude/ only) and tell the user to run `tools\commit-docs.ps1`. Files outside docs/claude/ still get an explicit commit block.

## Session hygiene (투자_V2 setup guide, apply automatically)
- At task start, state the recommended model/effort in one line: simple = low, routine = medium,
  analysis/dev = high, cross-file design / K3 / Judge = Opus xhigh. Ask the user to restart only when authority/limit
  or Judge work runs on a non-Opus model; otherwise proceed (redesign 2026-10-10). Never suggest switching model
  mid-session (it rebuilds the prompt cache). Effort may change mid-session only in Claude Code on Opus 5.5 /
  Sonnet 5.5 (`/effort`, cache kept); elsewhere restart (docs/claude/prompt-caching-review-2026-10-09.md).
- When the topic changes, tell the user to run /clear; if the task continues but context is long,
  suggest /compact at a natural stopping point.
- Before multi-file edits, present a plan first (or ask the user to press Shift+Tab for plan mode).
- Builder work runs in a worktree (claude --worktree <name>); a Judge runs in a separate session (headless
  pipeline after redesign T3) and never edits files.
- Talk to the user in Korean, one step at a time, giving the exact command to type.
- Cowork 세션에서 작업 상태가 바뀌었으면(완료·시작·새 재개 조건), 세션 끝에 한 번 docs/claude/dev-dashboard-protocol.md대로 관제판의 바뀐 작업만 갱신한다. 변화가 없으면 갱신하지 않는다. Claude Code·Judge·예약 작업은 갱신하지 않는다.
- Shared docs (design, rules files, cards, OI): record sha256 before editing and re-check just before saving; if it changed, re-read and merge.

## Compact instructions
Keep: current goal, changed files, failing tests, approvals given, open K3 items.
