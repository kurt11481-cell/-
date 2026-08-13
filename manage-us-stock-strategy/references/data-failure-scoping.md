# Data Failure Scoping

Classify a failure before deriving a portfolio conclusion.

Global failures include official-session verification failure, canonical
registry authority failure, total market-snapshot failure, provider-wide
independent-close outage, invalid policy version, and a missing/invalid
post-market baseline. They may make the applicable phase globally
`DATA_INCOMPLETE`.

Ticker-specific failures include one missing OHLCV row, one price mismatch,
one corporate-action conflict, one identity conflict, one event conflict, or
one independent-close mismatch. Mark only that ticker `DATA_BLOCKED`; valid
unrelated candidates continue. A report may be `PARTIAL` and still surface a
valid READY candidate. Do not convert a data failure into `NO_TRADE`.

Provider-wide incidents are emitted once with affected tickers, provider,
failure type, last success, retry timing when known, and the next review
trigger. Do not retry every ticker after the circuit is open.

Under v2.5, provider unavailability matters only when the selective
decision-changing queue is non-empty. It changes queued execution to
`VERIFICATION_PENDING` and creates one aggregated incident; it does not erase
primary-validated opportunity or strategy states. An empty queue is
`NOT_REQUIRED`. A validated direct price conflict remains ticker-specific.
