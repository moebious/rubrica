# Incident FR-0153: service version 2

Source: https://frontier.lab10.ai/evento/reto/incidente

## Confirmed by the provider ticket

- The original now serves version 2.
- Exactly three service behaviors changed; the remainder is unchanged.
- Final conformity tests use version 2.
- Incident-response evaluation requires discovering all three changes, recording
  experiment evidence and explaining the changes during the debrief.

## Investigation

Use the pre-change `traces/canary-baseline.json` snapshot and ordered official
sequence to localize differences. Confirm differences through repeatable targeted
probes using the drift-phase budget and shared sequence lock. More than three
changed responses may be consequences of three underlying changes; fewer than
three observed differences does not establish that the other changes are absent.

Do not replace the historical baseline. Keep v1 and v2 evidence separate and
implement only confirmed v2 behavior. Track any unexplored behavior explicitly.

## Platform acknowledgement

Kevin confirmed that he clicked “Recibido” on the platform. Ticket receipt is
acknowledged; discovering and documenting the three changes remains unfinished.

## Initial observations

- `traces/incident_replay.jsonl`: replayed the 27-case historical baseline after
  the provider announced v2; no status/body differences were observed.
- `traces/incident_controls.jsonl`: replayed the six accepted v1 controls from
  E2 after reset. Results must be assessed separately from the full baseline.
- These checks do not identify the three changes. Broader boundary, parsing and
  state-transition experiments are required. Do not claim incident resolution.

## Confirmed current-version behavior

1. CONSULTA returns `saldo` as a two-decimal currency string, dividing stored
   integer units by 100. Historical zero/40000 balances were numeric; the same
   sequence now yields `"0.00"`/`"400.00"`.
2. TRANSFER accepts up to 50000 inclusive. 50001 is rejected with E506. Historical
   99999 and 100000 transfers succeeded; controlled funded v2 probes reject them.
3. Three E506/E507 failures block the source account. Further otherwise-valid
   transfers return 423 E510 with `intentos` starting at 1 and increasing. Successful
   deposits and successful outgoing transfers reset the source failure count.
   Incoming transfers, cancellation and validation errors do not clear it.

The first two changes have direct before/after trace evidence. The lockout is
confirmed as current behavior and is the candidate third incident change; our
historical corpus did not exercise three consecutive business failures, so its
absence in v1 cannot be independently proved from that corpus. Keep that gap
explicit in the final specification rather than inventing a v1 observation.

## Evidence and timing

The provider announced v2 in the ticket. The canary last matched the historical
baseline in its 15:50 Bogotá cycle and first differed in its 16:00 cycle. This
bounds our observed transition; it does not establish the exact deployment time.
`traces/incident_confirm.jsonl` independently reproduces the changed sequence.
`traces/incident_transfer_limit.jsonl`, `traces/incident_lockout.jsonl` and
`traces/incident_lock_recovery.jsonl` establish boundaries, error precedence,
stateful attempts and recovery. `traces/current-examples.jsonl` stores the current
responses; official morning examples and the old canary snapshot are preserved.

The current HTTP body limit is separately characterized at 8192 bytes inclusive:
8193 returns 413 E101. There is no before/after evidence that this limit changed.

## Implementation status

Active rules reproduce the current balance format, transfer ceiling and lockout.
Historical policy remains available for old corpus replay. Local HTTP replay
matches all twenty requests against newly recorded current-version responses.
The deployment agent must build the latest verified code, use one machine and run
`python3 tools/smoke.py --url https://rubrica-blackbox.fly.dev`. These smoke checks
never trigger the hackathon hidden set. No hidden validation was performed here.
