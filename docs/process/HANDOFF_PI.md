# Handoff to the execution agent (Pi): final strategy, 17:30 → 20:00

**Roles.** Pi executes: code, discovery against the original, tests, deploys, spec and log. The Claude Code session orchestrates architecture and reviews; it does not edit `rubrica/`, `tools/` or the evidence files. Kevin owns platform actions (validations, submission, DNS, video).

**Hard deadline.** 20:00 Bogotá: execution submission closes and participant tokens stop working against the original. Plan every live probe to finish by **19:10**.

## 1. Where we are (verified at 17:26)

| Item | State |
|---|---|
| Hidden run #1 (16:57) | **88/100**: easy 39/40 · regular 36/40 · hard 13/20 |
| The 12 failures | **9 status mismatches, 3 body mismatches**; **5 fail on the first request, 7 later in a sequence** |
| Latency | Median 511 ms per case (limit 5 s per request) |
| Runs left | **2**. #2 only after measured improvement; #3 reserved for the final candidate |
| Entrypoint | `https://rubrica-blackbox.fly.dev` (submitted and validated by the platform at 16:56) |
| Repo | `github.com/moebious/rubrica` (submitted 16:55) |
| Tests / spec | 35 tests pass; `verify_spec.py` passes; 50 claims (18 confirmado, 29 probable, 3 supuesto) |
| Budget | ≈ 1,500 of 8,000 original requests used → **≈ 6,500 left** |
| Incident FR-0153 | v2 live since the 16:00 canary cycle. Changes: balance as decimal string (confirmado), transfer limit 100,000 → 50,000 (confirmado), lockout after 3 failures (probable: v1 absence unproven) |
| Frozen | `docs/DESIGN.*`, `site/diagram.*` (`tools/check_design.py` must stay OK) |

## 2. Strategy

Two problems, solved in order:

1. **Score first (the 12 failing hidden tests).** Use the design's own discovery loop: stateful fuzzer → probe gate → original → differential comparison against the replica → shrink → rule with evidence → new version → deploy.
2. **Then make the code match the design doc for the human judges** (spec reviewers and the debrief): "one source, three jobs" for the ontology, evidence at log-ID granularity, no false claims.

Score is first because it needs the original, which closes at 20:00. The ontology closure needs no live requests except to confirm claims.

## 3. Phase A — differential fuzzing (now → 18:15)

**Goal:** find concrete inputs where the replica differs from the current original.

Method (complies with the design: the replica's answer *is* the prediction required by the probe gate):
- All live calls through `Harness.sequence()` (prediction, budget, shared lock, recording). Never use legacy `req.py`/`seq.py`/`sweep.py` against the original.
- For each generated sequence: reset → steps → compare every step's status and body with the local replica using the official comparator.
- Every divergence: shrink to the minimal failing sequence, confirm with one repeat, then implement and add a regression test whose expected answers come **only** from the recorded original responses.

**Priority 1: stateful sequences (likely the 7 late failures, hard tier).**
- Lockout: which failures count (E506, E507, validation errors?), what resets the counter, `intentos` growth, several accounts locked at once, lockout of the destination vs. source, interaction with ANULA (reversing ops of a locked account, ANULA of a failed op), incoming transfers.
- Balances after ANULA of deposits and transfers; negative balances in the decimal-string format; large values.
- ID allocation after failures, lockout rejections and cancellations.
- Any other v2 difference: the third change is only *probable*. Look for it in 6–12-step sequences.

**Priority 2: first-request status (likely the 5 early failures).** Single requests after a reset, mutating:
- method on `/msg` (GET, PUT, DELETE, HEAD, OPTIONS, PATCH) and on other paths;
- path (trailing slash, case, `/msg/x`, query string, double slash);
- headers (Content-Type absent/other, auth scheme case, extra spaces, empty token, duplicate Authorization);
- body (empty, non-object JSON, extra keys, `m` as number/null/array, empty `m`, whitespace, Unicode, invalid UTF-8, near and over the 8192-byte limit).

9 of 12 failures are **status** mismatches: suspect error class and precedence before message text.

**Budget for phase A:** ≤ 1,500 requests (≈ 900 stateful, ≈ 300 first-request, ≈ 300 confirmations).

## 4. Measurement gates (required by the design doc)

- **Held-out slice (anti-Goodhart).** Before fixing anything, record a held-out set of ≈ 150 requests from a *different generator* (mutations of the README examples and structure-agnostic fuzz). Never use it to guide a fix. Report the exact-match rate on it before and after the fixes.
- **Discovery rate.** Report new divergences per 100 probes for each round. Stop fuzzing an area when it reaches zero; that is the stop criterion, not the clock.
- **Report per round:** probes used, divergences found, divergences fixed, held-out rate before → after, tests passing.

## 5. Validation #2 decision (~18:20)

Propose run #2 to Kevin only if **all** hold:
1. All tests green; current-version corpus 100%; `check_design.py` OK.
2. Held-out exact-match rate improved over the pre-fix measurement.
3. Deployed to `rubrica-blackbox.fly.dev`; `tools/smoke.py` passes on the public URL; per-step latency < 5 s.

If the held-out set did not improve, skip run #2 and keep both runs for later.

## 6. Phase B — round 2 + ontology closure (18:20 → 19:10)

Round 2 targets whatever run #2 (or the held-out set) still shows. In parallel, close the gap between the design doc and the code:

| The design doc promises | Current code | Required change |
|---|---|---|
| `SPEC.md` is generated from the ontology (one source, three jobs) | Spec comes from a separately curated claims list | Every spec claim carries the `rule_id` that implements it; `verify_spec.py` fails if a claim has no rule or a rule has no claim |
| A rule is proven by log lines | Every v2 rule cites the same 9 trace files | Each rule cites the **experiment IDs** (from `experimentos.jsonl`) that prove it |
| Confidence per rule | All v2 rules are `probable`; the spec has 18 `confirmado` | Rule confidence and claim confidence must agree, derived from evidence |
| Uses: compare versions, find gaps | No mechanism | Add `tools/ontology.py`: prints rules by operation, precedence, confidence and evidence count; the v1 → v2 policy diff; rules or operations with no or thin evidence |

Keep `rubrica/rules/v2/policy.py` as is: the three incident changes as three data fields (`transfer_limit`, `currency_balance`, `lock_after_failures`) are the clearest proof of "a behavior change is new data". Extend it if new changes appear.

**Spec risk ("a false claim subtracts"):** review the 29 `probable` and 3 `supuesto` claims. For each: confirm with a targeted probe (budget allows), or narrow the wording to what the evidence shows, or remove it. Keep the lockout's v1 gap explicit; never invent historical evidence.

## 7. Freeze and final (19:10 → 19:45)

1. **19:10:** stop all live probing. Final `jsonlog.py` → `gen_spec.py` → `verify_spec.py` (must include the latest observations; stable IDs).
2. Full gates: tests, current-version corpus replay, `check_design.py`, deploy, public smoke + latency.
3. Commit with clear messages; Kevin pushes (`git push`; pushes to the frozen design repo are blocked by the hook).
4. **~19:20:** tell Kevin the candidate is frozen → he runs **validation #3**.
5. No deploys after 20:00 except to restore availability; the replica must stay up through demo day.

## 8. Rules that do not change

1. No request without a prediction; the log answers first; everything recorded and budgeted.
2. Expected answers in tests come only from recorded original responses, never from our own rules.
3. Every rule and claim cites evidence; unproven behavior is `supuesto`.
4. Never edit `docs/DESIGN.*` or `site/diagram.*`; never commit `.env` or tokens (the pre-commit hook blocks them).
5. Rate-limit responses from the infrastructure are kept in raw logs and never learned as service behavior.
6. The replica never opens outbound connections.

## 9. Reporting to the orchestrator

At ~18:15, ~19:10 and on any blocker, write a short status (in chat to Kevin, or appended to `docs/process/BUILD_LOG.md`): probes used, discovery rate, divergences found/fixed, held-out rate, gates status, recommendation on the next hidden run.
