# Master Recovery and Expansion Validation

## Scope

This recovery adds an exact deployment-provenance counting gate, resolves the
MVLL RVOL20 data lineage, validates the Kiwoom read-only candidate-discovery
adapter, audits broker visibility, and installs non-executing future-order
contracts. Portfolio facts and live execution authority are outside scope.

## Deployment provenance

Both Codex Scheduled Tasks remain configured at 09:00 and 16:30
America/New_York. Operational recording requires the clean
`E:\사업\##금동한\runtime\stock-strategy-scheduled` exact-HEAD worktree plus
matching task, code, policy, provider-scope and cohort hashes. The Git-ignored
canonical portfolio state remains in the strategy repository and is passed by
its absolute read-only input path; it is not duplicated into the code
worktree. Until the external runtime manifest and task configuration validate,
counting fails closed.

## MVLL canonical volume lineage

The two reported RVOL20 values were caused by unstable 2026-08-13 same-day
volume observations, not two formulas. Four later Kiwoom `usa06012` pulls
converged to volume 2,847,409. The canonical signal excludes the current bar
from the 20-session denominator and produces RVOL20
`0.8924874478089728`; yfinance remains diagnostic at
`0.8657542447522418`. The approved threshold remains 1.0, so the condition is
`RVOL20_NOT_MET`. This is a data correction, not provider averaging or a
technical threshold change.

## Candidate discovery

The strict allowlist covers official U.S. condition/ranking/security-info
query endpoints and denies all order/write endpoints. Twelve REST ranking
operations succeeded in the live read-only acceptance. The WebSocket condition
list returned an empty response and remains a local partial limitation. The
operation produced research-only candidates; it did not activate the universe,
watchlist, buy approval, quantity, or an order.

## Broker visibility

The fresh audit retained verified held cash of USD 63.69 and verified holdings
visibility. Current-day fills returned an empty result, which was not converted
into a claim that no fills exist. Open orders and current realized P/L returned
API response errors. Additional official daily/period endpoints are supported
by the provider but missing from the local adapter. Read-only broker Shadow is
verified; future live execution readiness is `NOT_READY`.

## Future order Shadow

The repository now has deterministic, non-network contracts for broker-event
normalization, REST-anchored reconciliation, immutable order intent, an
independent risk decision, and gateway dry-run state. All request payloads are
null, network send is false, quantity is null, and order authority is false.
These are tested scaffolds only; real-time broker-event acceptance and live
order authority remain unverified and disabled.

## Semantic cohort

Deployment-provenance counting semantics changed, so the prior zero-count
cohort was preserved as superseded. The new cohort begins at zero with no
backfill. No manual, replay, smoke, or acceptance run was counted.
