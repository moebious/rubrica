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

Reading and recording this ticket locally does not acknowledge it to the staff.
The platform's “Recibido” action has not been performed by this agent.

## Initial observations

- `traces/incident_replay.jsonl`: replayed the 27-case historical baseline after
  the provider announced v2; no status/body differences were observed.
- `traces/incident_controls.jsonl`: replayed the six accepted v1 controls from
  E2 after reset. Results must be assessed separately from the full baseline.
- These checks do not identify the three changes. Broader boundary, parsing and
  state-transition experiments are required. Do not claim incident resolution.
