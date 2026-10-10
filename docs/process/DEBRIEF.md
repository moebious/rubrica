# Debrief notes: likely judge questions

Short answers for the debrief: a 10-minute slot with one judge, between 19:00 and 20:00 (check your slot time on /evento). Every fact here is in the repo; the source is
in brackets. If Pi's final freeze changes a number (score, claim count, log size), use the
new number from `docs/process/WORKFLOW.md` or the regenerated `SPEC.md`.

**Latest validation:** run #3 (last of 3), **96/100**, at 18:50 Bogotá, on
`/evento/resultados` (Kevin): easy 40/40, regular 38/40, hard 18/20; 2 status and
2 body failures; 2 first-request and 2 later failures; median 520 ms per case.
Progression: 88 (16:57) → 91 (18:22) → 96 (18:50). This is not the final score: the
platform runs once more after 20:00 on the last entrypoint submitted on time.

## 1. "What were the three incident changes, and how do you know?"

| # | Change | Evidence (log IDs, `SPEC.md` §6) | Confidence |
|---|---|---|---|
| 1 | CONSULTA balance: number → two-decimal string of units / 100 (`40000` → `"400.00"`) | 11 (v1), 1164 (v2) | confirmado |
| 2 | Transfer limit: 100000 accepted in v1 → E506 in v2; current ceiling 50000 inclusive, 50001 → E506 | 13 (v1), 1026, 1050 (v2) | confirmado |
| 3 | Source-account lockout: three E506/E507 failures → later valid transfers get 423 E510 with `intentos` 1, 2, … | 1059, 1060 (v2) | **probable** |

- **How we detected it:** the drift canary replays a pinned baseline every ~10 min. It still
  matched in the 15:50 Bogotá cycle and differed in the 16:00 cycle. That is an observation
  window, not the deploy time. [`INCIDENT.md`]
- **How we absorbed it:** the whole change is three fields in `rubrica/rules/v2/policy.py`:
  `V1 = Policy("v1-observed", 100000, False, None)` and `V2 = Policy("v2-observed", 50000, True, 3)`.
  V1 stays, so the historical traces still replay and pass.
- **The honest gap (say it before they ask):** the lockout is confirmed as *current*
  behavior (MEM-LOCK, MEM-UNLOCK are confirmado), but our v1 corpus never had three
  business failures in a row. We cannot prove it was absent before 16:00, so CHANGE-LOCK
  is *probable* and we did not invent a v1 observation. It is the only v2 difference we
  found beyond the first two, and the ticket says there are exactly three.
- **Follow-up if asked "what resets the lockout?":** a successful deposit or outgoing
  transfer from that account. Incoming transfers and ANULA do not; E303/E304/E401/E202 do
  not count as failures. [`SPEC.md` MEM-UNLOCK]

## 2. "Why rules, not an LLM, at runtime?"

- The protocol is formal: a checksum, fixed error order, exact strings (including the
  service's own misspelling `recieved`). There is nothing to perceive; an exact table is
  exact and repeatable, an LLM is neither. [`DESIGN.md` §3, decisions table]
- Latency: median 520 ms per case on hidden run #3 (510 on #2). The limit is 5 s **per step**;
  a case median alone does not prove every step meets it. [`WORKFLOW.md` ledger]
- We do use a model, offline, in System 2: a person and a reasoning model propose
  hypotheses and probes. The model never decides an answer; the original does.
- Record-and-replay was also rejected: it fails on any input it has not seen.

## 3. "How do you know you are not overfitting your own tests?" (Goodhart)

- Two different sets. The **recorded corpus** guides fixes. A **held-out set**, made by a
  different generator (mutations of the README examples and structure-agnostic fuzz), only
  measures. [`DESIGN.md` §4]
- Test expectations come only from recorded original responses, never from our rules, so a
  wrong rule cannot make its own test pass. [`AGENTS.md`]
- **It worked:** held-out seed 8 found a bug our corpus never showed. With two
  Authorization headers, the original uses the first one; the replica returned 401. Pi
  confirmed it with 18 recorded probes and fixed it (commit `4b4d92e`). Seed 8 is now
  regression evidence. Main `BUILD_LOG.md` reports fresh held-out seed 9:
  278/278 steps match. Do not invent a before/after improvement.
- Hidden-set runs were spent only on measured improvement: #1 88/100, #2 91/100 (hard
  13 → 16), #3 96/100 (easy 40/40, regular 38/40, hard 18/20). [`/evento/resultados`]

## 4. "Your design says the spec is generated from the ontology. Is it?"

Be direct: **not fully yet**. These gaps remain in main at `0ebd1d5`,
before the final freeze. Refresh this table after Pi's freeze:

| Design doc says | Observed implementation | Status |
|---|---|---|
| One source (ontology) runs the replica, writes `SPEC.md` and builds tests | `SPEC.md` is rendered from a separately curated claims list; the verifier checks log IDs and structured queries, not runtime rule links | Gap remains; do not claim `rule_id` linkage is implemented |
| A rule is proven by log lines | V2 parsing, domain and command rules share a tuple of nine trace-file references (`EVIDENCE`) | Per-rule exported experiment IDs are not implemented |

What already holds: every spec row cites integer IDs in `experimentos.jsonl`; the verifier
rejects a stale export, a modified response, a bad ID or an edited claim; and assumptions
are labelled *supuesto*. Update this table at freeze with what Pi actually merged; do not
claim a fix that is not in `git log`.

## 5. Other likely questions

- **"How many requests did you spend?"** Read the record count from the final
  main `experimentos.jsonl` (`wc -l`). The current export contains **5,039 records**,
  but the verifier fails as stale, so that is neither the final count nor the
  current request-budget spend. Wait for Pi's committed freeze snapshot.
- **"Biggest mistake?"** An early blind sweep of checksum controls 0–99 cost 543 requests
  for six accepted points. That is why the harness now refuses a request without a
  hypothesis and a prediction. The formula (letters A=1…Z=26, digits kept, append 00,
  98 − mod 97) was then fitted offline and confirmed on unseen inputs. [`ADVERSARIAL_HANDOFF.md`, `SPEC.md` IT-CONTROL]
- **"What are the 4 remaining hidden failures?"** We do not know: the platform shows counts
  only (run #3: 2 status, 2 body; 2 at the first request, 2 later). After run #1 we found and
  fixed four behaviors: query strings routed to 404, duplicate Authorization headers, E301
  suggestion ties (alphabetical), and the hidden HALT command. We do not claim which hidden
  tests each fix recovered; we only know the counts went 88 → 91 → 96. [`git log`, `/evento/resultados`]
- **"You found a hidden command?"** Yes. For the typo LAAT, the original itself suggested
  HALT. HALT with one argument answers 409 E520 ("operacion destructiva: detiene el
  servicio; reenvia con confirmacion"); other arities give E302. A 71-name sweep found no
  other hidden command. We deliberately **never sent the confirmation**: it could stop the
  shared original. The replica never executes it; that part is a *supuesto*. [commit `595b955`]
- **"A canary cycle failed at 22:08Z. Was that a new version?"** No. Accounts vanished
  mid-sequence once; a replay at 22:15Z matched all 27 baseline cases. Cause not
  established; those steps are quarantined in `tools/coverage.py`, by name. [`BUILD_LOG.md`]
- **"What would a new client not inherit?"** Negative balances after ANULA, blind retries
  that trigger lockout, a balance type that changed between versions. [`SPEC.md` §7]
- **"Does the replica call the original?"** No. It has no outbound connection; tests check
  it on exercised paths. [`README.md`, `BANKING_FINDINGS.md`]
