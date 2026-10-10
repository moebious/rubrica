# Build Log

Chronological record of what we built, the decisions we made, and why. Times are Bogotá (UTC-5), 2026-10-10.

| Time | Phase | Entry |
|---|---|---|
| 10:00 | Choice | Read both briefs. Reto 1 = screen agent (noVNC, full GUI, unseen app, 5 min/task). Reto 2 = black-box HTTP replacement (exact-match, `/__reset` before each test). |
| 10:10 | Choice | Ran two adversarial reviews of our reasoning. Accepted: don't pick the problem to fit a stack; self-healing by replaying checkpoints is unsafe on a UI with side effects; keep the shrinker simple. Rejected: "100% on our corpus = identical" (coverage is the real risk); DOM injection for Reto 1 (noVNC exposes only pixels). |
| 10:19 | Design | Drafted `docs/DESIGN.md`: pure `handle(state, req)` core, actor-model serialization, hosting chosen by fingerprinting the original's edge headers (Cloudflare and Fly proxies inject headers). |

## Bootstrap scaffold

Implemented generic request/response values, pure ordered rule execution,
immutable initial ledger state, versioned bootstrap rules and bounded serial
HTTP handling. Only the exact observed PING request has service evidence;
auth/error defaults and health/reset response bodies remain assumptions.
Added runtime-only non-root Docker packaging and project implementation rules.

Verification: nine adversarial unit/HTTP/packaging tests pass; Python compilation
passes; frozen PDF and diagram hashes match the submitted design. Local Python
is 3.14; the container targets 3.12. Deployment and all-20-example equivalence
remain pending. No live original requests or hidden validations were used.

## Adversarial contract review and baseline

Recorded a reset-based baseline: all 20 official examples still match the live
original. Observed health/reset bodies agree with historical E1 traces. Captured
route E404 and auth E001 responses, including unknown-route-before-auth behavior;
updated versioned contract rules with trace references. Invalid auth cannot reset
or mutate replica state. The original's personal-token isolation does not require
accepting arbitrary tokens on the team-token replica.

Added recorded, rate/budget-limited discovery with a cross-process sequence lock,
a bool-safe exact comparator, and a reset-based drift watcher. The full baseline
uses 27 calls; canary allocation is now 820, transferring 490 from the reserve.
Watcher diagnostics persist in `.runtime/canary-watch.log` and observations in
`traces/canary-results.jsonl`. Legacy tools must not bypass the harness.

Verification: recorded contract regressions failed before the fix and pass after;
14 tests pass and compilation succeeds. Fly CLI confirms remote builds are
supported. No deployment or hidden validation was performed. Banking commands
remain unimplemented; monitor differences require controlled confirmation.

## Repository history consolidation

Consolidated execution-repository design iterations into one baseline commit,
followed by separate discovery, replica and documentation commits. Preserved the
original history in a local backup reference and verified Git bundle, with a
snapshot of pending workspace files. The submitted-design remote stays untouched.
Discovery and replica commits were tested from independent archived checkouts:
four discovery tests and fourteen combined tests pass respectively.
