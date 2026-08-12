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
