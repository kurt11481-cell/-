# Development Incident Analysis

Use this procedure for an explicitly requested investment_V2 development
incident, failed validation, or debugging task. If the user asked for diagnosis,
produce a diagnosis. If they asked for a fix, continue through the authorized
minimum repair and targeted verification.

Adapted from gstack's root-cause investigation, hypothesis testing, and narrow
repair sequence. Upstream freeze hooks, automatic external reviews, and
unconditional test or commit flows are excluded. Follow repository AGENTS.md
and its relevant local guidance. Source and license:
[gstack-NOTICE.md](gstack-NOTICE.md).

## Establish evidence

Identify the failing operation, expected and observed behavior, candidate
revision, environment, input identity, timestamps, and the first useful error.
Reuse existing logs and validated artifacts. Redact secrets and avoid
collecting unrelated user data.

Distinguish a local initialization or schema defect, a failed source-access
path, a provider outage, invalid evidence, and a policy rejection. An empty
completed-close queue is not an outage. A blocked validator does not imply
that the data would have passed.

A reproduction must fit the current permissions and write scope. Prefer an
offline fixture or existing captured evidence when it answers the question.
No Broker or order call is authorized by this procedure. A previous one-use
Broker authorization cannot be reused because the investigation is unfinished.
Do not widen permissions or copy external sources into the repository to
bypass a source-access failure.

## Form and challenge a hypothesis

Trace the failing path to its relevant owner. State the strongest supported
cause, the evidence that supports it, and a plausible alternative if material.
Separate verified facts, inference, and unknowns.

Choose the smallest discriminating check: inspect a boundary value, compare
the captured inputs with their contract, trace a caller, or run an authorized
isolated reproduction. Do not patch a symptom before testing the cause.

Stop unchanged retries after the same failure provides no new information.
Reconsider the hypothesis or identify the missing input instead of repeatedly
calling a provider. Time passing alone does not fix a local protocol or
configuration error.

## Repair only within the current task

For diagnosis-only work, stop at the evidence-backed finding and proposed
repair. If a fix is authorized, change the narrowest owner of the defect and
preserve unrelated work.

Do not weaken a validator, update approved policy hashes, fabricate an event
or session, infer a fill, or promote Shadow evidence to obtain a passing result.
A proposed policy or authority change follows its existing approval contract.

Apply edit restrictions using the actual host permissions where available.
Do not claim that gstack's Claude freeze/careful hooks enforce Codex writes.

## Verify and report

Verify the original failure and the relevant normal path. When behavior
changes, use an existing meaningful regression or add one that distinguishes
the faulty and corrected behavior. Do not add tests for low-impact,
meaning-preserving text edits merely to satisfy a debugging template.

Report the cause, evidence, permitted repair, checks actually run, unresolved
limitations, and the next action that could change the conclusion. If the
cause remains unverified, say so; a plausible fix is not a confirmed fix.

If authorization, source access, or an external prerequisite blocks repair,
complete unaffected analysis and preserve the evidence. Return only the
specific missing decision or access condition. Do not declare production
recovery from a fixture, local smoke test, or corrected document.
