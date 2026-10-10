# Video script: Rubrica in 2 minutes

Hard limit 2:00. Rehearse to 1:55, leaving five seconds of margin.
The video is a required deliverable (public link); slides are not. So the video is mostly
**repo proof** (real files, real terminal), with three slides from `docs/pitch/` as title
and summary cards. Every command runs against the **replica** or local files only. Nothing
here sends a request to the original service.

## Prep (off camera, ~5 min)

Open each of these in its own window, in shot order:

1. **Deck:** `docs/pitch/index.html` in a browser, full screen (press `F`). Go to slide 1.
   The deck is on the `docs/delivery-material` worktree branch until merged:
   `~/Work/rubrica-demo/.claude/worktrees/delivery-material/docs/pitch/index.html`.
2. **Diagram:** `site/diagram.png` in Preview, full screen.
3. **Editor:** `SPEC.md` scrolled to section 1 (the `Evidencia` column visible), and a second
   tab on `rubrica/rules/v2/policy.py`. Use files from the **main checkout**:
   this delivery worktree contains older implementation and artifact snapshots.
4. **Terminal** at the repo root, font size ≥ 18, `clear`ed. Load the token now:
   `set -a; source .env; set +a`, then `clear`. Never `cat .env` or echo the token.
   `smoke.py` prints only PASS/FAIL, status and latency.

Dry-run both commands once so you know how long they take:

```bash
python3 -m unittest discover -s tests
```

```bash
python3 tools/smoke.py --url https://blackbox.rubrica.dev
```

## Script: 6 shots

| Time | Shot | On screen | Spoken (words) |
|---|---|---|---|
| 0:00–0:12 | Slide 1 (cover) | "Rubrica: Learning a black box, one proven rule at a time." | "A service has run for ten years and nobody knows what it does. Our job: build a replacement that answers with exactly the same status and body, errors included." (31) |
| 0:12–0:40 | Repo: `site/diagram.png` | Point left → middle → right. | "Rubrica uses two systems. System 2 is slow and offline: a person and a reasoning model probe the original through a harness. Every request is recorded with its hypothesis, and the harness refuses a request without a prediction. What we learn goes into a versioned service ontology: rules, evidence and confidence. System 1 is the deployed replica, a compiled rule table. The first matching rule decides. No model at runtime." (70) |
| 0:40–1:00 | Repo: `SPEC.md`, then terminal `unittest` | Scroll a few rows of the Evidencia column; then the tests finish with `OK`. | "The judge is exact: the original itself. Every claim in our spec cites experiment IDs from the log, and a verifier checks them. Tests take their expected answers only from recorded original responses, never from our own rules." (38) |
| 1:00–1:35 | Slide 4 (incident), then repo `policy.py` | The V1/V2 table; cut to the editor and highlight the `V1 =` and `V2 =` lines. | "Our canary matched at 15:50 and saw differences at 16:00. That is an observation window, not the exact deployment time. Balances became decimal strings, and the transfer limit dropped from one hundred thousand to fifty thousand, both confirmed before and after. A lockout after three failures is confirmed now, but we cannot prove it was absent before, so that change stays probable. In code, the incident is three data fields: V1 versus V2." |
| 1:35–1:50 | Repo: terminal `smoke.py` | Output scrolls and ends in `Smoke gate: PASS`. | "This is the live replica at blackbox dot rubrica dot dev, checked against the recorded examples, auth, routing and reset." (16) |
| 1:50–1:58 | Slide 5 (results) | Run 3 of 3: 96/100, 520 ms. | "Our last validation scored ninety-six of a hundred, up from eighty-eight and ninety-one. Every easy test passes." |

If you run long, cut the 1:35 line and let the smoke output play silently.
Use a completed smoke recording only if it actually passed on the candidate shown.
The separate demo-day pitch is also two minutes: see `PITCH_SCRIPT.md`.

**Score rule:** all 3 runs are used; say 96/100 (run #3) and never call it the final score. If anything changes,
say that score and update the slide (`docs/pitch/slides/results.html`, then
`python3 docs/pitch/build.py`). Never say a number that is not in the ledger.

## Recording checklist

- [ ] Do Not Disturb on; close Slack and mail; hide any window showing `.env`, tokens or the `/evento` card.
- [ ] QuickTime Player → File → New Screen Recording → Options: microphone on → record full screen.
- [ ] Switch windows with ⌘-Tab between shots; one continuous take is fine, cuts are optional.
- [ ] Read with a timer. Stop at 2:00 even mid-sentence on a retake.
- [ ] Trim in QuickTime (Edit → Trim) to ≤ 2:00. Export 1080p.
- [ ] Upload to YouTube as **Unlisted** (or Public), or Loom / Google Drive with "anyone with the link can view".
- [ ] Open the link in a private window: it must play without sign-in.
- [ ] Paste the link into the "Video de 2 minutos" field before 20:00 (see `docs/process/SUBMISSION.md`).

## Claims check (all from the repo)

| Claim in the video | Source |
|---|---|
| Harness refuses requests without a prediction | `docs/DESIGN.md` §3.1; `Harness.sequence()` in `tools/harness.py` |
| First matching rule decides; no model at runtime | `docs/DESIGN.md` §3.3; `README.md` |
| Spec claims cite log IDs; verifier | `SPEC.md`; `tools/verify_spec.py` |
| Tests use recorded original answers only | `AGENTS.md`; `docs/process/HANDOFF_PI.md` §8 |
| Canary 15:50 match / 16:00 diff | `docs/process/INCIDENT.md`; `SPEC.md` §6 |
| Balance string, 100000 → 50000 confirmado; lockout probable | `SPEC.md` §6 (CHANGE-BALANCE, CHANGE-LIMIT, CHANGE-LOCK) |
| Three data fields V1 vs V2 | `rubrica/rules/v2/policy.py` |
| Smoke checks examples, auth, routing, reset | `tools/smoke.py` |
| Runs 88 → 91 → 96/100; run #3 median 520 ms, 40/40 easy | `/evento/resultados` (Kevin, 3 of 3 runs used) |
