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

## Checksum and banking implementation

Discovered a control formula fitting all recorded valid controls: uppercase ASCII
alphanumerics, letters A=1 through Z=26, retain digits, append 00, then 98 minus
modulo 97. Unseen-input predictions succeeded across names, Unicode, IDs, operations
and amounts. Implemented incremental reduction and saved an offline fitter.

Implemented versioned observed rules for all six commands, syntax/integrity errors,
positive ten-digit amounts, transfer constraints, ID allocation and reversible
operations. Recorded probes established that PING bypasses checksum checks, duplicate
names are allowed and cancellations can yield negative balances. Unknown commands
may suggest a nearby command; this remains a probable generalization.

Verification: twenty tests pass, including all twenty official examples through
HTTP and independent recorded-corpus replay. No hidden evaluation was used and no
deployment was performed. Identifying all three incident changes remains pending.

## Incident behavior transition and response

The canary detected changed responses after an earlier matching cycle. Confirmed
current currency-string balances and a 50000 transfer ceiling with direct
historical comparisons. Characterized three-failure source lockout, E510 attempt
counts and recovery; historical absence of lockout was not covered, so its role
as the third change is probable rather than a fabricated v1 claim. Independently
replayed the changed official sequence and captured current-version expectations.

Implemented versioned policy, stateful failure counters, integer-based currency
formatting, observed 8192-byte limit and updated local HTTP smoke expectations.
Historical and current evidence are tested separately. Twenty-two tests pass;
all twenty current-version example requests match through the local HTTP adapter.
Fly deployment remains the other agent's responsibility. No hidden set invoked.

## Required log and specification artifacts

Added stable-ID export of all original exchanges with raw HTTP provenance, reset
anchors and immutable record hashes. Generated all seven specification sections
with curated evidence checks and explicitly labeled assumptions. Missing legacy
hypotheses, missing X-Req headers and the pre-reset health request remain visible;
no historical values were invented. Added adversarial tests for malformed records,
ID stability, Unicode, false claims, invalid references and modified evidence.
Current-service confirmations support reset, identifiers, parser behavior,
negative currency strings, duplicate names and suggestions. Deployment and hidden
validation are untouched by this artifact pipeline.

Verification: generated seven sections with fifty evidence-backed/assumed rows;
exported 1274 original exchanges. Thirty-three tests pass. Full verification rejects
stale exports, modified responses, bad IDs and edited claims. The whole pipeline
uses the discovery lock so canary calls cannot interleave with the snapshot.

## Delivery verification (2026-10-10, ~17:00 Bogotá)

Regenerated the log and spec with `tools/finalize_artifacts.py` (no original-service
requests; it only takes the shared sequence lock): 1382 original exchanges, 50
claims, verifier passes. Canary watcher left running and its traces untouched.
Gates: 35 tests pass; frozen design hashes match; read-only smoke check against
`https://rubrica-blackbox.fly.dev` passes 20/20 current-version examples plus
auth, routing and reset checks (max step latency 1.35 s). Documentation updated
where deployment status and the transfer ceiling were stale. The lockout's absence
in v1 remains unproved. No hidden validation was triggered; all attempts unused.

## Hidden-set validation #1 (2026-10-10, 16:57 Bogotá)

Owner-run. Score **88/100**: easy 39/40, regular 36/40, hard 13/20. Failures: 9 with a
different status, 3 with a different body; 5 failed on the first request, 7 later in the
sequence. Median 511 ms per case (limit 5 s). Entrypoint check at 16:56: health 200 in
226 ms, reset ok, public example 02 matched. The platform shows counts only. Runtime code
(`rubrica/`) was unchanged since commit `690e213`. Next: locate the failures from the
coverage gaps (never-observed cells, thin v2 cells, 6–12-step sequences) before any new
probe. Two runs remain. Details and the working agreement: `docs/process/WORKFLOW.md`.

## Post-validation findings (2026-10-10, ~17:15 Bogotá)

- **Query string (fixed on `fix/query-string`).** Recorded probes (`traces/edge_probes*.jsonl`)
  show the original answers `GET /health?probe=1` and `POST /msg?test=1` with 200, while a trailing
  slash (`/health/`, `/msg/`) stays 404. The replica 404'd the query forms. Now routes on the path
  only. This is one concrete status-mismatch source; validation #1 may have hit it. Not proven.
- **Unexplained canary cycle (22:08Z).** Steps 12–21 returned E401 "cuenta inexistente": the accounts
  created in steps 5–6 vanished between steps 11 and 12 (x-req stayed continuous 448→467). A
  confirmation replay at 22:15Z matched the pinned baseline on all 27 cases, so it is not a new
  version. No recorded harness access ran in that window, so either an unrecorded caller reset
  this token mid-sequence or the original evicts state. Not established. The cycle stays in the
  traces and the log; `tools/coverage.py` quarantines steps 12+ of that sequence, by name.
  Watcher stopped by design on the alert, confirmed transient, restarted.
- Replica deployed on Fly is still the pre-fix image until Kevin redeploys.
