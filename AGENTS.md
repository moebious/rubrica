# Frontier Lab10 Hackathon — Agent Engineering Guidelines

## Objective
Build hiring-loop-grade, production-ready software evaluated against **hidden test suites**, strict engineering standards, and real-world system architecture benchmarks.

## Core Rules for Code Generation
1. **Pass Hidden Test Suites**:
   - Never write code that only satisfies happy paths or visible sample cases.
   - Always guard against empty inputs, null pointers, off-by-one indices, type mismatches, and network/timeout failures.
   - For async code, ensure re-entrancy safety, deadlock prevention, and proper error propagation.
2. **Architecture & Foundation**:
   - Write strongly typed code with modular boundaries and explicit interfaces.
   - Separate pure business logic from I/O and external adapters for trivial testability.
3. **Comprehensive Testing**:
   - For every feature implemented, write adversarial test cases covering edge and boundary conditions.

## Model Strategy in Pi (`Ctrl + P` to switch)
- `openrouter/openai/o3-mini-high`: Cracking failing edge-case tests & algorithmic logic.
- `openrouter/google/gemini-3.1-pro-preview`: Ingesting entire specs, docs, and whole-repo audits.
- `openrouter/x-ai/grok-4.7`: Generating adversarial test suites to uncover hidden bugs.

## Rubrica implementation rules
- Follow `docs/process/ROADMAP.md` for active scope and acceptance gates.
- Keep learned service behavior in versioned rules. Cite recorded evidence and label untested defaults as assumptions.
- Preserve exact statuses, bodies and observed validation order. Expected test outputs come from original recordings.
- Keep the pure core free of I/O; perform original-service requests only through recorded discovery tools.
- Keep credentials out of Git, logs and Docker images. Preserve frozen design and diagram artifacts.
- Verify changes with `python3 -m unittest discover -s tests -v`; replay the corpus before deployment and smoke-test the public endpoint afterward.

## Git and evidence hygiene
- Raw traces are evidence: the log, spec, coverage audit and tests are built from `traces/*.jsonl`. Never gitignore, truncate, reformat or rewrite them.
- The canary appends to `traces/canary*.jsonl` every ~10 minutes. Do not commit per cycle. Commit canary traces only together with a regenerated log/spec (`python3 tools/finalize_artifacts.py`) or at milestones (drift response, validation, freeze), in a commit of their own.
- Keep commits small and single-purpose, with conventional messages (`feat`, `fix`, `test`, `docs`). Do not mix canary traces with code changes.
- Changes under `rubrica/rules/` go on a short branch. Merge only after the unit tests, `python3 tools/coverage.py` (zero mismatches) and the corpus replay pass.
- Never force-push or rewrite published history. Never touch the frozen design remote.
- Tag the submitted commit at freeze (`submission-20h00`).
- Original-service access goes through `Harness.sequence()` only, with a recorded hypothesis and prediction. Never use the legacy `tools/req.py`, `tools/seq.py` or `tools/sweep.py` against the original.
- Never trigger a platform hidden-set validation; only the owner does. Do not change Fly or DNS settings.
