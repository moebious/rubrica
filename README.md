# Rubrica

**Learning a black box, one proven rule at a time.**

Rubrica learns an undocumented, stateful HTTP service through experiments and deploys a replica that answers with the same status and body. Built for Frontier · Bogotá 26, Reto 2 ("La caja negra").

| Deliverable | Where |
|---|---|
| Design doc | [docs/DESIGN.pdf](docs/DESIGN.pdf) ([source](docs/DESIGN.md)) |
| Architecture diagram | [site/diagram.png](site/diagram.png) |
| Entrypoint | `https://blackbox.rubrica.dev` (live from 20:00) |
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
| `docs/` | Design doc; `docs/process/` holds the working plan and notes |
| `site/` | Architecture diagram |
| `tools/` | Harness: recorder, sequence runner, design check |
| `traces/` | Raw record of every request sent to the original (tokens redacted) |
| `material/` | The challenge brief and its 20 example requests |

## Setup

```bash
cp .env.example .env    # then set ORIGINAL_TOKEN; .env is git-ignored
git config core.hooksPath .githooks   # blocks committed secrets
```
