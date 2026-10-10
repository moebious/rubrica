# Working agreement (from the first hidden-set run onward)

Status: adopted 2026-10-10, after validation #1. Complements `AGENTS.md` (rules) and
`ROADMAP.md` (scope). This file records how we decide, not what the service does.

## 1. Validations are scarce, owner-run and logged
- Only Kevin starts a hidden-set run. No agent or script triggers, clicks or automates it.
- Run only when the replica changed for a reason we can name, and our own corpus did not
  get worse (`python3 tools/coverage.py` reports 0 mismatches; unit tests pass).
- Every run gets one row in the ledger below **before** the next change starts:
  time, commit, deployed image, score, categories, failure split and the decision it caused.
- The platform shows counts only, never test inputs. Treat each failure count as a lead,
  not as a diagnosis.

### Validation ledger
| # | Time (Bogotá) | Commit | Score | Easy / Regular / Hard | Status ≠ / Body ≠ | Fail at 1st request / later | Median |
|---|---|---|---|---|---|---|---|
| 1 | 16:57 | `9714e88` or earlier; runtime code identical to `690e213` (last `rubrica/` change) | **88/100** | 39/40 · 36/40 · 13/20 | 9 / 3 | 5 / 7 | 511 ms |

Entrypoint check at 16:56: `/health` 200 in 226 ms, `/__reset` ok, public example 02 matched.
2 of 3 runs remain. Run #2 is for Kevin to schedule.

## 2. Failure-first loop (no original requests until step 3)
1. **Locate.** From the counts, list the replica behaviors that could produce the failure
   split. Reproduce against the replica only. Cost: 0 requests.
2. **Rank.** Use the gap list from `tools/coverage.py` (cells never observed, thin v2 cells,
   long sequences). Rank by hidden-test weight: 40 single requests, 45 short sequences,
   15 long ones.
3. **Probe.** Only through `Harness.sequence()`. Each probe has a hypothesis and a prediction
   taken from the replica before sending. A mismatch is a finding, not a failure of the tool.
4. **Change.** A rule change goes on a short branch. Merge only after: unit tests pass,
   `tools/coverage.py` has 0 mismatches, the corpus replay passes. The new observation is
   added as a recorded trace test (expected values come from the original, never from our rules).
5. **Ship.** Kevin redeploys; the agent runs `tools/smoke.py` and reports the actual result.
6. **Record.** Regenerate log and spec, add a `BUILD_LOG.md` row, update the ledger.

## 3. Roles
| Who | Does | Never does |
|---|---|---|
| Kevin | Hidden-set runs, Fly/DNS, video, delivery form, final decisions | |
| Agent | Code, tests, probes through the harness, log/spec, smoke checks, commits | Run a validation, change Fly/DNS, probe outside the harness, rewrite history |

## 4. Commit and evidence rules
See "Git and evidence hygiene" in `AGENTS.md`. In short: small commits, canary traces batched
into their own commit, rules on branches, tag the submitted commit, never force-push.

## 5. Stop rule
Each unknown area gets at most 50 probes. After that it becomes a documented *supuesto*
and we move on. Freeze starts at 19:15; after it, nothing new except availability recovery.
