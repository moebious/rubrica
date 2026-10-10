# Banking discovery: current observed service

These findings describe observations after the v2 announcement. They do not
establish which three behaviors changed from v1. Raw evidence below must be
mapped to stable exported experiment IDs before the final specification.

## Integrity and syntax

- Uppercase the entire prefix before the final semicolon/control field. Keep only
  ASCII letters A–Z and digits 0–9; map letters to decimal 1–26 and retain digits.
  Append 00 and return `98 - (numeric_value mod 97)`. Incremental reduction avoids
  integer-size limits. The offline fitter has one surviving encoding among its
  enumerated candidates; unseen-input probes confirm it across operations,
  arbitrary IDs, names, Unicode, punctuation and amounts.
- PING requires zero arguments but bypasses control format/value validation.
  Empty segments are rejected even for PING. Commands are case-insensitive;
  surrounding whitespace is not trimmed. Account and operation IDs are exact.
- Observed order: JSON syntax → m string shape → control field existence → empty
  segments → control format/value (except PING) → command → arity → amount →
  same-account transfer → lookup → transfer limit → insufficient funds.
- Unknown commands may include a `sugerencia` field. Edit distance at most two
  fits observed cases and tie handling; broader generalization remains probable.

Evidence: `traces/checksum_predictions.jsonl`, `traces/message_contract.jsonl`,
`traces/bank_edges.jsonl`, `traces/bank_final_edges.jsonl`.

## Accounts and money

- ALTA accepts duplicate names and whitespace-only names. A truly empty field
  fails before command handling. Account IDs start AC-0001 and advance on success.
- Deposits/transfers accept canonical positive ASCII decimal integers with one
  to ten digits. No leading zeros, signs, whitespace, decimals or exponent syntax.
  9,999,999,999 is accepted; 10,000,000,000 is rejected with E303.
- A transfer to the same ID returns E304, even when that ID is absent. Amount
  validation precedes that error; missing-account lookup precedes the limit.
- Transfer amounts above 100,000 return E506. Otherwise insufficient balance
  returns E507. Successful writes return the exact misspelling `recieved`.
- Successful deposits/transfers allocate OP IDs. Failed writes do not consume IDs;
  cancellation does not create an operation ID.
- ANULA reverses the saved deltas without requiring funds for reversal. Balances
  can become negative. Repeated cancellation returns `ok:false`/`ya anulada`.
  Unknown operation IDs return E402. Reset replaces accounts, operations and ID
  counters without mutating prior state objects.

Evidence: `traces/bank_boundaries.jsonl`, `traces/bank_limits.jsonl`,
`traces/bank_edges.jsonl`; official examples remain matching current observations.

## Verification and remaining scope

The replica passes the twenty official requests in order through its HTTP adapter,
and pure-core replay matches all newly recorded banking/parser sequences. Tests
cover immutable state, reset isolation, malformed inputs, exact JSON semantics and
no outbound network on exercised paths. Deployment/public latency verification,
final log/spec export and identifying the three incident changes remain pending.
