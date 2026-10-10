# Rubrica

**Learning a black box, one proven rule at a time.**

Rubrica learns an undocumented, stateful HTTP service through experiments and deploys a replica that answers with the same status and body. Built for Frontier · Bogotá 26, Reto 2 ("La caja negra").

| Deliverable | Where |
|---|---|
| Design doc | [docs/DESIGN.pdf](docs/DESIGN.pdf) ([source](docs/DESIGN.md)) |
| Architecture diagram | [site/diagram.png](site/diagram.png) |
| Entrypoint | `https://rubrica-blackbox.fly.dev` (Fly.io, one always-on machine) |
| Specification | `SPEC.md` (generated from the service ontology) |
| Experiment log | `experimentos.jsonl` (one line per request to the original) |

The design doc and diagram are identical to the versions submitted at 12:00; `python3 tools/check_design.py` verifies it.

## How it works

- **System 2 (offline discovery):** a person and a reasoning model probe the original service through a harness that records every request with its hypothesis and refuses requests without a prediction.
- **Service ontology:** the versioned model of the black box: rules with their evidence and confidence. It runs the replica, generates the spec and produces the tests.
- **System 1 (the replica):** a minimal HTTP server that applies the current version of the rules. The first matching rule decides; unmatched inputs get a documented default.
- **Verification:** a differential test replays recorded sequences against the replica, and a drift canary watches the original for changes.

## Layout

| Path | Contents |
|---|---|
| `rubrica/` | The replica: `engine/` (HTTP adapter, pure core, registry) and `rules/` (versioned service behavior, `v1` and `v2`) |
| `tests/` | Unit, adversarial and recorded-corpus replay tests |
| `tools/` | Harness (budgeted, locked access to the original), canary, differential runner, fuzzer, held-out generator, coverage audit, log/spec pipeline, smoke and design checks |
| `tools/probes/` | The targeted probe scripts behind each discovered behavior |
| `traces/` | Raw record of every request sent to the original (tokens redacted) |
| `SPEC.md`, `experimentos.jsonl`, `experimentos.index.json`, `spec-evidence.json` | Delivered specification, experiment log, and their provenance |
| `docs/` | Frozen design doc; `docs/process/` holds the roadmap, workflow, incident notes and build log |
| `site/` | Architecture diagram |
| `material/` | The challenge brief and its 20 example requests |

## Setup

```bash
cp .env.example .env    # then set ORIGINAL_TOKEN; .env is git-ignored
git config core.hooksPath .githooks   # blocks committed secrets
```

## Replica implementation

The active `v2-observed` rules implement PING, ALTA, CONSULTA, DEPOSITO,
TRANSFER and ANULA, including the discovered control formula and observed
validation order. The official requests pass **20/20 through the local HTTP server against
current-version recorded answers**. The historical responses are preserved and
verified using the earlier policy. Additional recorded boundary and state-transition experiments are
replayed independently in tests. This is evidence for covered behavior, not a
claim of complete hidden-test equivalence. The incident findings and historical
evidence gap are documented in `docs/process/INCIDENT.md`.

Run locally (the server reads the process environment):

```bash
set -a
source .env
set +a
python3 -m rubrica.engine.server --host 127.0.0.1 --port 8080
```

Verify:

```bash
python3 -m unittest discover -s tests -v
python3 tools/solve_checksum.py
python3 tools/diff.py --url http://127.0.0.1:8080
```

`diff.py` targets the replica, checks exact status/body and per-step latency,
and exits nonzero on divergence. Use the recorded harness for original access.
The observed body limit is 8192 bytes. Duplicate auth headers and broader
unobserved protocol behavior still require evidence. Current rules include the
50,000 transfer ceiling, currency-string balances and source-account lockout.

The Docker image copies only `rubrica/` and runs as a non-root user. Supply
`TEAM_TOKEN` at runtime. Rule versions are selected at startup in
`rubrica/rules/current.py`; there is no live rule mutation.

## Recorded discovery and drift detection

Use `python3 -m tools.canary --capture` once to establish a reset-based baseline.
Use `python3 -m tools.canary --watch --baseline traces/current-canary-baseline.json`
to monitor the current version. The historical baseline remains intact. The monitor
records every call, enforces rate/phase/daily budgets and locks complete sequences
against other callers using `tools.harness.Harness`. Results are in
`traces/canary-results.jsonl`; the watcher stops on a mismatch or failure for
investigation. Legacy request/sweep tools bypass this coordination and must not
access the original while the monitoring session is active.

The Fly CLI supports `flyctl deploy --remote-only`; local Docker is not required.
Deployment still requires account access, app configuration and runtime secrets.

## Deployment

Fly app: `rubrica-blackbox`. Deploy with
`flyctl deploy --remote-only --ha=false --strategy immediate`.
Use one machine and keep auto-stop disabled. The configuration has no unauthenticated HTTP health check. Verify
authenticated readiness and behavior with `python3 tools/smoke.py --url https://rubrica-blackbox.fly.dev`.
A successful smoke check does not invoke the hackathon hidden set.

## Specification and experiment log

`SPEC.md` contains the seven required sections and cites integer IDs in
`experimentos.jsonl`. `experimentos.index.json` preserves raw HTTP provenance,
reset boundaries, stable IDs and hashes. `spec-evidence.json` records the curated
checks behind each table row.

```bash
python3 tools/finalize_artifacts.py
python3 tools/verify_spec.py
```

Export includes every recorded original exchange, including resets and failed
HTTP responses; replica replays are excluded. Missing X-Req is null. Older calls
without a recorded hypothesis are marked as missing rather than reconstructed.
Empty bodies are null; non-JSON bodies use `_raw_body_b64`; the provenance index
retains exact bytes and distinguishes empty bodies from JSON null. One health
call precedes the first recorded reset. These historical gaps remain explicit.

The verifier checks schema, immutable raw evidence, references and structured
observations; it does not prove every natural-language generalization. Run this
pipeline again before submission to include the latest canary observations while
preserving existing IDs.
