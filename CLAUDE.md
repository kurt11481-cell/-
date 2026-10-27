# Investment_V2 — Claude Code rules

U.S. stock portfolio system moving to automated operation (redesign 2026-10-10). Broker access is read-only;
no order execution authority until order stage 2 is approved (redesign 3-6).
Order stage 1 (user decision A7 a; redesign T2 merged 2026-10-12): the auto-core decide run issues LOC order tickets
(quantity_authority "ORDER_TICKET_HUMAN_ENTRY", tickets only) that the user enters in Kiwoom; everything else keeps
quantity_authority "none" and execution_quantity null. While decision_mode is compare (until the user's "켜"), tickets
are labeled 비교 중 and are not entered.

## Goal (user decision 2026-10-10, docs/claude/automation-redesign-2026-10-10.md)
- Automated operation is the top priority: a deterministic daily auto-core (collect -> reconcile -> compute ->
  order ticket -> journal -> exception alert). LLMs work at the edge (research, explanation, development) and
  their failure never blocks the core. The user receives results only.
- If an automation design is blocked or a routine step needs the user, treat it as a severe defect and fix it by
  removing human steps, not adding them. Read-only work the session can do itself is done, not handed to the user.
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
  `portfolio_review_journal.py`, or by the auto-core decide run in recording mode only (decision_mode apply; entries
  core_decision, order_ticket, ticket_outcome with AUTO_CORE). In Cowork the user's explicit decision message in the current
  conversation is the confirmation: propose, then apply in the same session with that proposal's own code,
  `--confirmed-via COWORK_CHAT_USER_MESSAGE` and the user's decision text verbatim (redesign A3, 2026-10-10). Never
  apply for a decision the user did not state. Claude Code, Codex and Judge sessions never apply or edit the journal.
  Exception, 사장실 회사PC 스레드 (interactive Claude Code project thread; journal-venue 2026-10-27): the user's own decision
  message typed in that thread, or the user's own tap on a decision card that thread posted (the four record items in
  Change classes), is the confirmation; the same session runs propose -> apply -> verify with that proposal's own code,
  `--confirmed-via PROJECT_THREAD_USER_DECISION` and user_message `<message or card id> | <account id> | <KST time> |
  <verbatim text or card option>`. One decision covers only the immediately preceding proposal, the same day, once.
  Holding-card S7b entries (card_decision, card_user_decision) only. A card closed by Claude, quotes relayed by a
  coordinator or another Claude, a card from another thread or an earlier day, summaries and scheduled turns are not
  confirmation.
- Never edit approved policy (stock-strategy-system/alert_policy.json, workspace/policies/*)
  or portfolio state without explicit user approval in this session. The auto-core reconciliation under the
  redesign 3-5 invariants (after T1) is the approved exception for holdings, cash and cost basis only.
- Never read or print secrets (.env*, tokens, account numbers).
- Missing or stale data stays visible and fails closed. Deterministic rules outrank LLM output.
- The only LLM input to the auto-core is the research record written by the 06:40 integrated check
  (workspace/outputs/research-records/<KST date>/research-record.json, schema auto-core-research-record). A missing or
  invalid record blocks every buy ticket, never sells. An interactive session (never a Judge session, scheduled task
  or subagent) that changes or accepts a card updates docs/claude/card-evidence-registry.json in the same session
  (otherwise that symbol gets no ticket).

## Kiwoom query rules (standing user rule 2026-10-07)
- Every read-only `kiwoom_query` call (Cowork, Claude Code, Codex, scheduled tasks, Manual runs) must pass options `"profile": "실전계좌"` and `"mode": "real"`. Without the profile the call uses an old token and fails with 8005. Bridge code reads the same alias from policy key `token_profile_alias` in workspace/policies/kiwoom-readonly-policy.json.
- On 8005 or any auth error: do not run auth, login or token reissue (it can invalidate another task's token). Mark that query failed, keep the gap visible (fail closed) and report it.
- This fixes the token profile only. It adds no authority: never inject `confirm`, never call order tools, and targets and filters stay as approved.
- New scheduled tasks and manual calls follow the same rule (checklist: docs/claude/analysis-linkage-map-2026-10-05.md). Evidence: docs/claude/kiwoom-profile-prompt-change-2026-10-06.md.

## Change classes (redesign A5, 2026-10-10)
- General change (old K0-K2): dev pipeline (redesign T3, tools/dev_pipeline/README.md). Cowork writes docs/claude/<id>-builder-prompt.md
  with a dev-run block and queues docs/claude/_dev-queue/<id>.txt; Windows task InvestmentV2-DevQueue runs tools/dev-run.ps1 (headless
  Builder, deterministic scope/test checks vs a measured baseline, headless Judge, one fix retry); merge: when result.json is READY_TO_MERGE (class general, tests and Judge PASS), Cowork runs
  `.\tools\dev-merge.ps1 <id>` on the PC itself via Desktop Commander and reports the result, never with -ApproveAuthority
  (user decision dc-dev Q1 a, 2026-10-22, docs/claude/dc-dev-2026-10-22.md). Docs-only changes need no Judge.
- Authority/limit change (old K3: order stage, order tools, budget/ceiling/caps, approved products, reconciliation
  invariants, kill switch): stop, user approval, independent Judge (manual route). After the user's approval stated in the current conversation Cowork may launch
  the manual-route Builder (worktree) and a separate read-only Judge session on the PC (dc-dev Q2 a); the merge still waits for
  the user's decision. If the pipeline escalates a run to authority,
  dev-merge needs -ApproveAuthority, used only after the user's decision stated in the current conversation (never from an older
  record or memory).
  In this item, the current conversation may also be the user's own message typed directly in the interactive Claude Code project thread
  (harness mark from=human trust=principal), or the user's own tap on a decision card (request_decision) that the same thread posted for
  that proposal. A tap counts only when the thread's decision record shows, taken from the harness wake for that card (not a summary):
  the card's message id and the proposal id it names, the option label chosen, the tapping member's account id equal to the project
  owner's, and the KST time of the tap. Quotes relayed by a coordinator or another Claude, any other button or card (including a card closed by Claude
  with close_decision or posted in another thread or on an earlier day), summaries and scheduled turns are not approval. One approval covers only the
  immediately preceding proposal, the same day, once.
  After the user's approval, the interactive Claude Code project thread may also start the manual-route Builder (worktree) and
  a separate read-only Judge session; merge still waits for the user's PowerShell line.
  The official route for approvals that need a script is one PowerShell line the user types in their own terminal; the session
  gives the exact line (dev-merge.ps1 <id> -ApproveAuthority, or --confirmed-via USER_TERMINAL).
- Kiwoom acceptance pin: retired by redesign T1 (merged 510961a). manage-us-stock-strategy/assets/kiwoom-acceptance-pin-scope.json
  has status RETIRED and is kept as the list of formerly pinned files. Editing one of them no longer invalidates an
  acceptance; instead every auto-core run records the git commit SHA and dirty paths, and in apply mode an uncommitted edit to a guarded
  file (former pin list, the core's own files, tracked files under manage-us-stock-strategy/scripts, schemas, assets) fails before any read (docs/claude/redesign-t1-builder-report-2026-10-10.md F6).

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
  Claude Code denies any command containing "auto_core.py" (settings.json, 2026-10-10): run those tests with -p "test_auto_core*".
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
- Recovery gate R-REC1 (user instruction 2026-10-09, docs/claude/recovery-gate-R-REC1-2026-10-09.md): while a shock event is open (SOXX close <= -2 sigma60, 20-session drawdown >= 3 sigma60, user/check-designated root-thesis news shock, or a candidate's own -2 sigma60 day), every exposure-increasing buy needs RG1 thesis (2 sessions after the event and no uncleared official root-thesis damage in the 60-session window; a damage fact clears only when the candidate's card is accepted again, registry accepted.date, ev-rg1-hyper 2026-10-18), RG2 trend (benchmark and candidate close >= EMA50), RG3 shock absorbed (2 closes above event close, no new low below the event-day low), RG4 volatility normalized. It only blocks or delays buys: never blocks sells, never counts as trade evidence, never raises the budget; missing data fails closed for buys. Rule candidate until replay + Judge (K3). Replay 2026-10-09: criterion a not met; user kept it as candidate (D).
- Scenario guideline SCN-27H1 (user decision 2026-10-09, docs/claude/market-scenario-27h1-2026-10-09.md, valid until 2027-06-30): system-wide market premise B0 = late-cycle bull market through 1H27 (conditional). Before a card, M6, order-instruction council or discovery acceptance, Cowork/Claude Code sessions run docs/claude/scn27h1-triggers.py in the cloud container (FRED) and write its first line "시나리오 SCN-27H1: 🟢|🟠|🔴 (…)"; on 🔴 ask the user once (keep / suspend, default suspend). Premise and display only: evidence weight 0, never raises budget, exposure ceiling or authority, never blocks sells, no automatic trades. FX-1009 freeze exception (user 2026-10-09 22:05): linked in the integrated check (loader 3단계), Next SanDisk monthly (step 10) and watchlist re-score (추가 단계) prompts; any later swap of those prompts (e.g. fx-2 v3.12.3-L) must carry the block (docs/claude/scheduled-prompts/README.md 변경 기록).
- Decision journal: when a holding-card position decision (ADD/HOLD/TRIM/EXIT, or the user's own action on it) is accepted in Cowork or in the 사장실 회사PC 스레드, record the S7b entry in the same session as described in Hard safety (no separate confirmation code). A watch-card (non-held) acceptance is recorded in docs/claude/card-evidence-registry.json (accepted) and watchlist-registry.json (cardStatus), not in the journal; new buys of non-held symbols are journaled by the auto-core (order_ticket/ticket_outcome, recording mode) and issued tickets are scored by score_decision_journal.py; watchlist R2.1 scores are post-scored against later returns by docs/claude/watchlist_forward_score.py.
- Default disposition (user decision 2026-10-09 Q1, docs/claude/ops-dev-touch-reduction-2026-10-09.md R4): every replay, review or rule candidate pre-registers its default outcome. Criterion not met, or no user answer by the stated deadline → NO_CHANGE (current rule and policy kept); Cowork records it and only notifies. Ask the user only when the result proposes a change. A default never raises exposure, budget or authority; changes to policy, state, authority or orders still need explicit approval.
- Review stability (user 2026-10-13, docs/claude/review-stability-2026-10-13.md; Cowork and interactive Claude Code only: pipeline/manual-route Builder and Judge, scheduled tasks and all subagents keep their own output contracts, and subagent output is a pointer): a first review must leave nothing for a re-review to find. Before a review or analysis concludes: (V1) every claim cites a source opened in this session (file:line, query time, commit, or the user's words/tool output in a chat turn opened in this session), including the definition lines of terms it relies on; notes, board text, summaries, earlier answers, memory and subagent output only point to sources; check what is checkable read-only and recompute numbers; what stays unreachable is shown as "확인 필요" and anything resting on it fails closed (trading: blocks buys, never sells; rules/dev: NO_CHANGE); (V2) use the most precise reachable data (bars over a one-time quote, final over provisional) with as-of; (V3) dev/rule reviews walk NO_CHANGE→REMOVE/SIMPLIFY→REUSE→REPLACE→ADD; check every block both as rule application and as a defect; resolve in-scope items that need no policy, state, scheduled-task, authority, order or code change (code goes through the change classes); (V4) name the evidence that would change each conclusion; (V5) if it recommends, asks for a decision, defers or proposes a change, run the section 3-1 re-review subagent (non-Haiku; Opus for authority/limit/K3), re-verify each finding at its source and fix the draft; if a conclusion changed, run one more round on the changes only; leftovers are 미해결 under default disposition (notify only); other reviews do the L1-L6 check in-session. End with "검토 완결: 원문 확인 n/m · 내장 재검토 r회(반영 k건) · 미해결 j · 자료 시점 … · 바뀔 조건 …". On a user re-review, read the earlier record first, re-check changed inputs and run L1-L6 on the earlier record against its sources (no fresh analysis from scratch); change a conclusion only for changed input, a factual error shown from the source, a first-pass omission or new user information (else "유지 — 새 근거 없음"); report 처음 판단 | 재검토 | 이유 | 원문 and log the missed lens in section 2.
- Concurrency cap: At most 3 active development tasks and 1 authority/limit change in progress at a time.
- Doc-only commits (user decision 2026-10-09 Q5, automated by redesign T3 2026-10-10): when an interactive session leaves docs/claude/ changes, write docs/claude/_pending/<task-id>.txt (line 1 = commit message, then one repo-relative path per line, docs/claude/ only). Windows task InvestmentV2-DocsCommit commits them daily at 23:30 (dev-queue also runs commit-docs before a run); do not ask the user to run it. Files outside docs/claude/ still get an explicit commit block.
- Artifact page design (user 2026-10-14): before editing or republishing the HTML of 미국주식 현황판, 개발 관제판 or 통합점검, read the live version and keep the 투자_V2 design-system colors, type and touch sizes in docs/claude/artifact-design-rules-2026-10-14.md. Display only: no data, rule or authority change; the 통합점검 order panel keeps Kiwoom buy red / sell blue (--buy/--sell), separate from price up green / down red.

## Session hygiene (투자_V2 setup guide, apply automatically)
- Model and effort: Ask the user to restart only when authority/limit
  or Judge work runs on a non-Opus model; otherwise proceed (redesign 2026-10-10). Never suggest switching model
  mid-session (it rebuilds the prompt cache). Effort may change mid-session only in Claude Code on Opus 5.5 /
  Sonnet 5.5 (`/effort`, cache kept); elsewhere restart (docs/claude/prompt-caching-review-2026-10-09.md).
- Before multi-file edits, present a plan first (or ask the user to press Shift+Tab for plan mode).
- Manual route (authority/limit changes, pipeline-protected paths such as tools/**, .claude/**, CLAUDE.md, AGENTS.md, .gitignore, or a
  stopped pipeline run): Builder in a worktree (claude --worktree <name>), then a Judge in a separate session that never edits files.
  Cowork may start both on the PC via Desktop Commander after the user's approval (dc-dev Q2 a); the merge still waits for the user's decision.
  Claude Code sessions never run dev-run/dev-merge/dev-queue and never edit .claude/settings*.json (deny); Cowork makes settings
  changes with user approval.
- Cowork 세션 또는 사장과 대화 중인 사장실 회사PC 스레드(대화형 Claude Code)에서 작업 상태가 바뀌었으면(완료·시작·새 재개 조건), 세션 끝에 한 번 docs/claude/dev-dashboard-protocol.md대로 관제판의 바뀐 작업만 갱신한다. 변화가 없으면 갱신하지 않는다. Judge·예약 작업·하위 에이전트는 갱신하지 않는다.
- Shared docs (design, rules files, cards, OI): record sha256 before editing and re-check just before saving; if it changed, re-read and merge.

## Compact instructions
Keep: current goal, changed files, failing tests, approvals given, open K3 items.
