# Rubrica: Implementation Roadmap (14:15 → 20:00)

**Goal at 20:00:** `blackbox.rubrica.dev` answers the hidden set like the 20:00 version of the original; `SPEC.md` and `experimentos.jsonl` are complete and every claim is verified; repo, video and entrypoint are submitted.

**Owners:** **C** = Claude (code, probes, docs) · **K** = Kevin (tokens, logins, DNS, platform, video, approvals).

## 0. Architecture in code

```
rubrica/
  engine/            # generic: knows nothing about this service
    server.py        # stdlib HTTP server, single-threaded (serial queue for free)
    contract.py      # /health, /__reset, auth, unknown routes, default answer
    registry.py      # Rule records: id, operation, precedence, match(), respond(), effect(), evidence, confidence
    core.py          # handle(state, request) -> (state, response, rule_id); first match wins
    state.py         # per-token state, reset to the rule set's initial state
  rules/
    current.py       # points at the active version
    v1/              # service-specific data + small functions (the only coupled code)
tools/
  harness.py         # gate: prediction required, cache, budget, <= 8 req/s, drops infra rate-limit answers
  jsonlog.py         # strict writer/reader; exports experimentos.jsonl in the README format
  diff.py            # official comparator (status + JSON-equal body); shows X-Rubrica-Rule per divergence
  canary.py          # 5 fixed + 5 rotating requests every 10 min; alerts on change
  fuzz.py · shrink.py · smoke.py · gen_spec.py · verify_spec.py · check_design.py
tests/               # contract tests, recorded-corpus replay, adversarial inputs, no-outbound guard
```

**Engine invariants (tests enforce them):** no import from `rules/` inside `engine/` except through the registry · no outbound network in `rubrica/` · every response carries `X-Rubrica-Rule` · the server never crashes on bad input (malformed JSON, huge body, invalid UTF-8, empty body).

## 1. Milestones

| # | Time | Milestone | Owner | Done when |
|---|---|---|---|---|
| R0 | 14:15–14:50 | **Engine + contract tests** | C | Local server passes: `/health` 200; `/__reset` restores state; auth hook; unknown route → configured default; one rule per response with `X-Rubrica-Rule`; no-outbound test; fuzzed bad inputs never crash |
| R1 | 14:50–15:10 | **Deploy skeleton** | C + K | Fly app (1 machine, always on, health check); `TEAM_TOKEN` as a Fly secret; `smoke.py` passes on `*.fly.dev`; CNAME `blackbox` → Fly; TLS issued; smoke passes on `blackbox.rubrica.dev` |
| R2 | 14:30–15:20 | **Harness + first discovery** (parallel to R0/R1) | C | `harness.py` gate and cache live; determinism check (one sequence twice); initial-state matrix: auth variants, routes/methods, body shapes, message syntax, each operation once; ≤ 300 requests |
| R3 | 15:00–15:25 | **Golden snapshot + canary before 15:30** | C | Batch sequences covering every v1 rule recorded; `canary.py` running every 10 min |
| R4 | 15:15–15:40 | **Rules v1 + validation #1** | C + K | Replica passes 100% of the recorded corpus and the 20 examples; deploy; smoke passes; **K validates** (#1) and reports category scores |
| R5 | 15:30–17:00 | **Drift response** | C | On alert: log time and request count; replay the golden snapshot; list changed rules; `rules/v2`; corpus split by version; tests green; deploy; smoke |
| R6 | ~17:15 | **Validation #2** | K | Only if the current-version exact-match rate did not drop |
| R7 | 17:00–18:45 | **Coverage push** | C | Precedence pairs; boundaries ±1; repeated operations; long sequences (6–12 steps); fuzz + shrink; held-out set from a different generator ≥ 95%; discovery rate near zero per area |
| R8 | 18:30–19:10 | **Spec + log** | C | `gen_spec.py` writes `SPEC.md` (7 README sections, `ID · Comportamiento · Evidencia · Confianza`); `verify_spec.py` passes (every claim matches its cited log lines); `experimentos.jsonl` exported with every request to the original |
| R9 | 19:10–19:30 | **Freeze + validation #3** | C + K | Final deploy; smoke on `blackbox.rubrica.dev`; `check_design.py` OK; **K validates** (#3) |
| R10 | 19:15–19:50 | **Video + submit** | K (C drafts) | 2-min script ready by 19:00; video recorded; repo URL, entrypoint, video, spec and log submitted before 20:00 |
| R11 | 20:00–23:00 | **Keep it up** | C + K | Replica stays up through demo day (no deploys after 20:00 unless it is down); debrief notes ready |

## 2. Request budget (8,000/day per token; 566 spent)

| Phase | Requests |
|---|---|
| R2 discovery (initial state first: 40 of 100 tests are single requests) | 300 |
| R3 golden snapshot | 250 |
| Canary 14:30–20:00 (33 × 10) | 330 |
| R5 drift replay + re-learning | 1,000 |
| R7 coverage + fuzz | 1,800 |
| Held-out set | 300 |
| **Reserve (after the change)** | **3,454** |

The harness refuses any request over its phase budget. A rate-limit answer from the infrastructure is dropped, never learned.

## 3. Rules for every change

1. No request without a prediction; the log answers first.
2. Every rule cites log lines; unproven behavior is *supuesto*.
3. Tests compare against **recorded** answers, never against our own rules.
4. Deploy only after local tests and `diff.py` pass; run `smoke.py` after every deploy.
5. Never edit `docs/DESIGN.*` or `site/diagram.*` (frozen; `check_design.py`).

## 4. Cut lines (if we fall behind)

| Behind at | Drop | Keep |
|---|---|---|
| 15:30 | Custom domain (submit the `fly.dev` URL) | Golden snapshot + canary |
| 17:30 | Shrinker, structure-agnostic held-out generator | Precedence pairs, sequences, drift absorbed |
| 18:45 | Long fuzz runs | Spec + `verify_spec.py`, log export |
| 19:15 | Anything new | Freeze, validation #3, video, submit |

## 5. Dependencies and blockers

| Need | From | By |
|---|---|---|
| `TEAM_TOKEN` in `.env` | K | 14:50 (R1) |
| `fly auth whoami` works | K | 14:50 (R1) |
| CNAME `blackbox` at name.com | K | 15:05 (R1) |
| Mentor answers: "otro token" meaning; is 15:30 the change; do `/__reset` calls go in the log | K | 15:30 |
| Validations #1–#3 on the platform | K | 15:40 · 17:15 · 19:30 |

## 6. Risks

| Risk | Mitigation |
|---|---|
| Deploy or DNS fails | Deploy the skeleton by 15:10; `fly.dev` URL is the fallback |
| A computed value (integrity check) is not cracked | Stop rule: 50 probes, then a documented default; prioritize what passes the most tests |
| The change is broad | Reserve budget; re-learn initial-state behaviors first |
| Budget runs out | Cache, batch sequences, a second token if a teammate joins |
| False spec claims | `verify_spec.py` before submitting |
| Replica crash in the demo window | Always-on machine, health check restart, no deploys after 20:00 |
