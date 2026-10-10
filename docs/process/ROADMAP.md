# Rubrica: Implementation Roadmap

**Status: LOCKED FOR EXECUTION.** This roadmap is the active implementation plan; it supersedes conflicting implementation details in `PLAN.md` and `CANDIDATES.md`. Lock means the architecture, scope and verification gates below are agreed, not that discoveries are forbidden. Change behavior only with evidence; record scope changes and their reasons here. Milestones describe acceptance criteria, not completed work; do not assume the announced incident changes the service.

**Goal:** `blackbox.rubrica.dev` answers the hidden set like the final evaluation version of the original; `SPEC.md` and `experimentos.jsonl` are complete and every claim is verified; repo, video and entrypoint are submitted.

## 0. Architecture in code

```
rubrica/
  engine/            # generic: knows nothing about this service
    server.py        # stdlib HTTP server, single-threaded (serial queue for free)
    contract.py      # generic contract interfaces; observed behavior supplied by versioned rules
    registry.py      # Rule records: id, operation, precedence, match(), respond(), effect(), evidence, confidence
    core.py          # handle(state, request) -> (state, response, rule_id); first match wins
    state.py         # generic state interfaces; bank-specific state and initializer live in rules/v1/
  rules/
    current.py       # points at the active version
    v1/              # service-specific data + small functions (the only coupled code)
tools/
  harness.py         # prediction gate, context-aware evidence lookup, budget, <= 8 req/s
  jsonlog.py         # strict writer/reader; exports experimentos.jsonl in the README format
  diff.py            # official comparator (status + JSON-equal body); shows X-Rubrica-Rule per divergence
  canary.py          # 5 fixed + 5 rotating requests every 10 min; alerts on change
  fuzz.py · shrink.py · smoke.py · gen_spec.py · verify_spec.py · check_design.py
tests/               # contract tests, recorded-corpus replay, adversarial inputs, no-outbound guard
```

**Engine invariants (tests enforce them):** no import from `rules/` inside `engine/` except through the registry · no outbound network in `rubrica/` · every response carries `X-Rubrica-Rule` · the server never crashes on bad input (malformed JSON, huge body, invalid UTF-8, empty body).

The startup composition point may load the active rule set and inject it into the engine. No service-specific imports belong in the decision core. The trace header applies to application responses; transport failures may prevent any response from being sent.

## 1. Milestones

| # | Milestone | Done when |
| --- | --- | --- |
| R0 | **Engine + contract tests** | Local server passes: `/health` 200; `/__reset` restores state; auth hook; unknown route → configured default; one rule per response with `X-Rubrica-Rule`; no-outbound test; fuzzed bad inputs never crash |
| R1 | **Deploy skeleton** | Fly app (1 machine, always on, health check); `TEAM_TOKEN` as a Fly secret; `smoke.py` passes on `*.fly.dev`; CNAME `blackbox` → Fly; TLS issued; smoke passes on `blackbox.rubrica.dev` |
| R2 | **Harness + first discovery** (parallel to R0/R1) | `harness.py` gate and cache live; determinism check (one sequence twice); initial-state matrix: auth variants, routes/methods, body shapes, message syntax, each operation once; ≤ 300 requests |
| R3 | **Golden snapshot + canary** | Reproducible reset/setup sequences capture available pre-change behavior; coordinated `canary.py` runs within budget; retain version provenance and record the first confirmed change |
| R4 | **Rules v1 + validation #1** | Replica passes 100% of the current-version recorded corpus; replay all 20 official examples and explain any differences established by live change evidence; public smoke checks and per-step latency gate pass; validate on the platform (#1) and record category scores |
| R5 | **Drift response** | On alert: log time and request count; replay the golden snapshot; list changed rules; `rules/v2`; corpus split by version; tests green; deploy; smoke |
| R6 | **Validation #2** | Only if the current-version exact-match rate did not drop |
| R7 | **Coverage push** | Precedence pairs; boundaries ±1; repeated operations; long sequences (6–12 steps); fuzz + shrink; held-out set from a different generator ≥ 95%; discovery rate near zero per area |
| R8 | **Spec + log** | `SPEC.md` has all 7 README sections and required tables; strict log/schema checks pass; cited exported IDs exist and support each claim; every original request is accounted for, with infrastructure failures distinguished |
| R9 | **Freeze + validation #3** | Final-version corpus replay, strict log/spec checks and frozen-design check pass; public smoke and per-step latency gates pass on the submitted URL; validate on the platform (#3) |
| R10 | **Video + submit** | 2-min script ready; video recorded; repo URL, entrypoint, video, spec and log submitted before the execution deadline |
| R11 | **Keep it up** | Replica stays up through demo day (deploy only for availability recovery after submission); debrief notes ready |

## 2. Request budget (8,000/day per token; 566 spent)

| Phase | Requests |
| --- | --- |
| R2 discovery (initial state first: 40 of 100 tests are single requests) | 300 |
| R3 golden snapshot | 250 |
| Canary allocation (including full-sequence setup and resets) | 820 |
| R5 drift replay + re-learning | 1,000 |
| R7 coverage + fuzz | 1,800 |
| Held-out set | 300 |
| **Reserve (after the change)** | **2,964** |

The harness refuses any request over its phase budget. Count all live calls, including resets, auth probes, canary setup and infrastructure failures. Preserve infrastructure rate-limit responses in raw logs, but exclude them from learned service behavior. The historical 566-call figure must be reconciled with traces before live probing; recompute the remaining budget and reserve from the actual ledger. Canary allocation includes sequence setup and resets; reduce frequency or rotating coverage if needed to stay within its allocation.

## 3. Rules for every change

1. No request without a prediction; the log answers first.
2. Every rule cites log lines; unproven behavior is *supuesto*.
3. Tests compare against **recorded** answers, never against our own rules.
4. Deploy only after local tests and `diff.py` pass; run `smoke.py` after every deploy.
5. Never edit `docs/DESIGN.*` or `site/diagram.*` (frozen; `check_design.py`).

## 4. Cut lines (if we fall behind)

| When | Drop | Keep |
| --- | --- | --- |
| Deployment threatens baseline capture | Custom domain (submit the `fly.dev` URL) | Golden snapshot + canary |
| Coverage work threatens specification completion | Shrinker, structure-agnostic held-out generator | Precedence pairs, sequences, drift absorbed |
| Finalization begins | Long fuzz runs | Spec + `verify_spec.py`, log export |
| Submission freeze begins | Anything new | Freeze, validation #3, video, submit |

## 5. Dependencies and blockers

| Need | Required for |
| --- | --- |
| `TEAM_TOKEN` in `.env` | Replica configuration (present locally) |
| `fly auth whoami` works | Deployment |
| CNAME `blackbox` at name.com | Custom-domain smoke check |
| Mentor answers: "otro token" meaning; log representation for resets, non-JSON and non-message requests | Behavioral discovery and exact log export; preserve all raw exchanges while resolving representation |
| Validations #1–#3 on the platform | Evaluation milestones |

## 6. Risks

| Risk | Mitigation |
| --- | --- |
| Deploy or DNS fails | Deploy the skeleton early; `fly.dev` URL is the fallback |
| A computed value (integrity check) is not cracked | Stop rule: 50 probes, then a documented default; prioritize what passes the most tests |
| The change is broad | Reserve budget; re-learn initial-state behaviors first |
| Budget runs out | Cache, batch sequences, a second token if a teammate joins |
| False spec claims | `verify_spec.py` before submitting |
| Replica crash in the demo window | Always-on machine, health check restart, availability recovery only after submission |

## 7. Locked implementation decisions and acceptance gates

### Runtime and scaffold

- Python 3.12 deployment target, standard-library runtime; no LangGraph or Pydantic dependency in the initial scaffold. Validate input types explicitly; annotations and frozen dataclasses do not enforce runtime types or deep immutability. Add a development-only static type checker and document its command separately from runtime dependencies.
- Functional core: `handle(state, request) -> (new_state, response, rule_id)` has no I/O and does not mutate its input state. Commit the returned state only after successful rule evaluation. Serialization and reset behavior must have adversarial tests.
- Implement the smallest runnable slice first: HTTP adapter, generic contract/core/registry/state interfaces, versioned rules, one evidence-backed behavior, tests and deployment packaging. Expand discovery tooling incrementally; creating every planned tool is not a prerequisite for the first deployment.
- Auth, JSON parsing, checksum, command validation, errors and their precedence are observable service behavior supplied by the active rules. Do not hard-code mod 97, a guessed validation order, or invented error bodies as confirmed behavior. Defaults and transport-limit responses remain explicit assumptions until probed. Avoid process crashes while preserving observed HTTP 500 responses when applicable.
- Single-threaded HTTP handling requires finite socket timeouts, bounded body reads, explicit handling of malformed framing/UTF-8/JSON and client disconnects, and recovery for the next request. Verify slow/incomplete requests cannot block the process indefinitely. Choose and document safeguards without claiming they match untested original limits.
- Configuration fails clearly when the team token is missing; never print credentials. Keep `.env` ignored. Add `.dockerignore`; copy only runtime files into the image and run as a non-root user. Do not include credentials, traces or development materials. Use one always-on deployment instance and verify the health-check/auth interaction.
- No-outbound verification covers exercised runtime paths and checks forbidden imports/call sites; it is not proof that the process lacks network capabilities. Production code must never call the original or another replica.

### Stateful evidence lookup

- Cache/corpus lookup retrieves evidence; it does not simulate a live state transition. Never skip a request needed to prepare the original's state.
- Identify cached evidence by service-version observation, token/session context, reset boundary, ordered preceding requests, and the exact method/path/headers/body relevant to behavior. When context or version is uncertain, do not reuse it as a current live answer.
- Test identical requests after different histories, version invalidation and required setup calls. Repeated live probes are allowed for determinism and drift verification; "never repeat" is not a correctness rule.

### Canary and incident response

- Every canary case specifies reset, setup sequence and expected recorded outputs. Use a separate token if available; otherwise serialize the entire reset/setup/probe sequence with all discovery access to that token. Independent processes must share the same coordination mechanism.
- All canary calls pass through the recorder and budget gate. Confirm mismatches with controlled replay; distinguish infrastructure failures from service responses. Never ignore a differing field without evidence that it is volatile, and retain exact bodies for evaluation.
- Create a new rule version only after evidence establishes changed behavior. The ten-minute detection interval applies to covered cases when the monitor is healthy; 45-minute repair is a target. Neither guarantees coverage of all changes.

### Tests and coverage

- Final-version behavior takes priority over the morning examples. Keep older recordings as versioned historical evidence, never merge conflicting expectations into the active corpus, and cite live evidence for any changed example. If a change cannot be verified before original access ends, label the uncertainty explicitly.
- Through the public submitted URL, measure every step of reset/setup, authenticated health, command/error probes and representative 6–12-step sequences. Every received response must arrive in less than five seconds; timeout, connection failure or an over-limit step fails the deployment gate. Use the exact status/body comparator as well as timing checks. Passing representative probes is evidence, not a guarantee about unseen inputs.
- The ontology selects evidence and generates test organization; expected status and body come exclusively from independently recorded original responses. Tests must not compute their expected answers from implementation rules.
- Preserve comparator distinctions: JSON object key order is irrelevant, array order matters, booleans are not numbers, strings are exact, and non-JSON bodies require exact text comparison. Include adversarial comparator tests.
- Include malformed/empty input, nulls and wrong types, Unicode, large values, boundary values, conflicting errors, repeated operations, failed-operation state effects, reset isolation and long sequences.
- Hold out a separate corpus for measurement. Once used to guide a fix, it becomes regression evidence and is replaced for future held-out measurement. A discovery rate near zero is a stopping heuristic, not proof of completeness; 95% is a target, not a predicted hidden score.

### Rule publication and handoff

- Validate `experimentos.jsonl` against the material README: one parseable JSON object per line; required fields `id`, `seq`, `x_req`, `hipotesis`, `request`, `status`, `response`; optional `conclusion`. Require unique integer IDs equal to one-based exported line numbers, nonempty sequence/hypothesis strings, integer HTTP statuses and observed X-Req values where present. Preserve response JSON or exact non-JSON text without coercion. Never invent a missing X-Req value; retain the raw exchange and resolve its export representation explicitly.
- Each exported sequence must identify its reset boundary and ordered setup requests in a provenance index. Reconcile exported records with all raw original exchanges, including resets and infrastructure responses; distinguish infrastructure responses from service evidence. Spec evidence must reference stable exported integer IDs, not source-file line numbers. Check all seven sections and every `ID | Comportamiento | Evidencia | Confianza` table; permitted confidence values are `confirmado`, `probable`, `supuesto`. Check evidence references mechanically and assess whether each cited observation supports the claim; schema validation alone does not establish behavioral truth.
- "Shared memory" means a versioned artifact loaded at startup, not a live mutable table shared with discovery. Deploy code, rules and initial-state schema together; do not hot-swap rules during a request. Each recorded corpus carries version provenance; uncertain transition-period evidence is labeled explicitly.
- Before deployment: adversarial tests, recorded-corpus replay, no-outbound checks and frozen-design verification pass. After deployment: remote smoke checks pass through the submitted URL. Report remaining assumed behavior rather than claiming complete equivalence.
- During scaffold work, add concise project-specific rules to `AGENTS.md`: evidence/confidence, exact responses, runtime/discovery separation, secret handling, independent tests, frozen artifacts and verification commands. Preserve its existing engineering requirements.
- Optional tools remain subject to the existing cut lines. Required final outputs remain replica, spec, complete experiment log, repository, entrypoint and video. Prefer the working provider URL if DNS delays submission.

## 8. Execution start checklist

1. Next execution priority: reconcile existing traces/budget and establish the recorded, budgeted baseline/canary path. A rule change has been confirmed as forthcoming; capture available pre-change behavior immediately, or document that the baseline window was missed. Do not infer the new behavior from the announcement alone.
2. Verify credentials without printing them, assign stable exportable log IDs and preserve reset/sequence provenance. Coordinate all original access; no unrecorded or unbudgeted live probes.
3. Complete R0's remaining scaffold gates and deployment access checks while baseline monitoring is established. Retain tests and explicitly labeled assumptions.
4. Deploy the slice, run remote smoke checks, then expand evidence-backed rules and coverage. Keep unsupported auth/parsing defaults visible as assumptions.
5. Record milestone completion with test results and outstanding assumptions; adjust remaining work without weakening submission gates.

## Baseline execution decision

The initial canary replays the complete 20-example sequence, reset, health and
five route/auth probes (27 calls per cycle). This favors reproducible state over
premature sequence minimization. Its phase allocation is increased from 330 to
820 calls by moving 490 from the reserve; the total daily allocation is unchanged.
The watcher stops on a mismatch, exhausted budget, infrastructure/network failure
or the original-access deadline. Any mismatch requires confirmation before
publishing a new rule version. Alerts and raw observations are persisted locally.
Legacy `req.py`, `seq.py` and `sweep.py` must not access the original during this
session; all new original access uses `Harness.sequence()` and its shared lock.
The replica accepts only the team token: personal-token isolation on the original
does not authorize additional tokens on the replica. Unauthorized requests cannot
alter/reset its state; multi-principal storage is deferred unless evidence makes
it part of the replacement contract.
