# Demo-day pitch: 2 minutes

Kevin confirmed a two-minute slot. Hidden-set runs on `/evento/resultados` (Kevin, 3 of 3
used): #1 16:57 **88**, #2 18:22 **91**, #3 18:50 **96/100** (easy 40/40, regular 38/40,
hard 18/20; 2 status + 2 body; 2 first request + 2 later; median 520 ms).
Run #3 is the last validation, not the official post-20:00 evaluation.

Use five slides: cover → architecture → design at work → incident → results.
Aim to finish at **1:55** (~250 words). No live commands or platform actions during the pitch.
The submitted architecture diagram includes planned components; do not claim
that the spec and runtime are already one fully unified ontology.
Replica URL to say or show: **blackbox.rubrica.dev**.

## Spoken script

### 0:00–0:15 · Cover

A service has run for ten years without documentation. Rubrica learns its
behavior through experiments and builds a replacement, live at
blackbox.rubrica.dev. The target is exact: the same status and body, errors included.

### 0:15–0:45 · Architecture

We split reasoning from execution. Offline, a person and a model propose
hypotheses. The harness requires a prediction and records every request.
At runtime, a serial server applies versioned rules. The first match decides;
no model call, and no call to the original.

### 0:45–1:05 · The design at work

Each part of this diagram caught something. The canary caught the incident.
The held-out set caught a header bug our own tests never showed. And the
service itself suggested a hidden HALT command: we recorded its answer, but
never sent the confirmation, because it could stop the shared service.

### 1:05–1:35 · Incident

Our canary matched at fifteen fifty and differed at sixteen hundred.
Balances became decimal strings, and the transfer limit dropped from one
hundred thousand to fifty thousand: both with before-and-after evidence.
A lockout after three failures is confirmed now, but we never tested its
absence before, so we call that change probable. In code: three data fields.

### 1:35–1:55 · Results and close

Our last hidden-set validation scored ninety-six of a hundred, up from
eighty-eight and ninety-one. Every easy test passes; four tests still fail.
Median about half a second. The lesson: reason to discover, exact code to
execute, evidence to say what you know.

## Rehearsal and freeze checks

- Rehearse aloud with a timer; word count is not proof of duration.
- If over 1:55, drop the HALT sentence on the "design at work" slide.
- No hidden-set runs remain; 96/100 (run #3) is the number to say. Never call it the final score.
- Refresh incident evidence against the frozen main `SPEC.md` before presenting.
- SPEC/log upload is cleared only after Pi's freeze, verifier success and a matching record count.
- The platform entrypoint field still shows what Kevin submitted at 16:55; if it is not
  blackbox.rubrica.dev, decide before 20:00 whether to change it (that is Kevin's call).
