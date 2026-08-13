# Broker Snapshot Reconciliation

Broker screenshots are untrusted portfolio evidence, not market-price
evidence. Accept PNG, JPEG/JPG, or WEBP pages as one evidence bundle. Never
infer a fill, settlement state, complete account scope, or cash classification
from layout alone. Broker display prices may be recorded for reconciliation but
must not become completed-close, EMA, ATR, RVOL, or hard-risk evidence.

## Authority states

Use this lifecycle:

`UPLOADED_UNTRUSTED -> EXTRACTED_PENDING_USER_CONFIRMATION -> VERIFIED_USER_CONFIRMED_BROKER_SNAPSHOT`.

Uploading or extracting cannot mutate canonical portfolio state. A proposal is
eligible for atomic application only when its schema passes and the user
explicitly confirms the same `proposal_id`, evidence `bundle_id`, current state
revision, and pre-update portfolio hash. The apply step increments the revision,
writes by atomic replacement, records before/after hashes, and creates an audit
artifact. It still creates no fill record, order, or quantity authority.

## Scope rules

- `FULL_PORTFOLIO` may replace holdings and verified settled/available cash only
  after account completeness, holdings completeness, currency, and cash
  classification are all confirmed.
- `HOLDINGS_ONLY` may replace the complete holding map, average costs, and
  purchase amounts; it cannot verify cash.
- `CASH_ONLY` may update only verified settled/available cash; it cannot replace
  holdings.
- `POSITION_ONLY` may merge only explicitly confirmed ticker records; it cannot
  imply that omitted positions are absent.

Margin buying power and unsettled or unconfirmed proceeds never become
`available_cash_usd`. A cropped or partial screenshot remains incomplete.

## Privacy and retention

Mask account identifiers, exclude names, login fields, OTPs, and credentials,
and require re-upload if sensitive login or OTP content is visible. Raw images
belong under `workspace/private_inputs/broker_snapshots/` and must remain Git
ignored. Commit only sanitized structured fixtures with fictional/masked
identifiers. Keep dates as unverified when the screen does not show a capture
date; a ranking date is not a capture date.

## Snapshot requests

Request the narrowest remediable scope only when fresh broker facts could change
an otherwise viable review. Use reason codes such as stale holdings, stale cash,
holdings reconciliation, cash verification, or full-portfolio reconciliation.
Do not request a broker snapshot to repair market-data, event, policy-authority,
or provider failures. Deduplicate request delivery separately from trade-review
delivery.
