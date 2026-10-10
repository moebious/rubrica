"""Differential runner: the replica predicts, the original judges.

A sequence is: reset, then ordered steps. Before each live step the local replica computes the
expected status/body; that string is the harness prediction. The first divergence ends the
sequence (later predictions would rest on a state we no longer trust) and is written to a report.

All original access goes through Harness.sequence(): recorded, budgeted, locked.
Generators live elsewhere (tools/fuzz.py, tools/heldout.py) and only yield `Seq` values.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(ROOT))

from rubrica.engine.contract import Request as EngineRequest
from rubrica.engine.core import handle
from rubrica.engine.server import route_path
from rubrica.rules.current import build_rules, initial_state
from tools.comparator import bodies_equal
from tools.hb import Request

PRED_TOKEN = "predictor-token"
RULES = build_rules(PRED_TOKEN)
REPORTS = ROOT / ".runtime" / "fuzz"

AUTH_MODES = ("ok", "none", "wrong", "lower", "upper", "noscheme", "empty", "basic", "dup", "space2", "tab", "trail")


def auth_headers(mode: str, token: str) -> list[tuple[str, str]]:
    return {
        "ok": [("Authorization", f"Bearer {token}")],
        "none": [],
        "wrong": [("Authorization", "Bearer not-the-token")],
        "lower": [("Authorization", f"bearer {token}")],
        "upper": [("Authorization", f"BEARER {token}")],
        "noscheme": [("Authorization", token)],
        "empty": [("Authorization", "Bearer ")],
        "basic": [("Authorization", f"Basic {token}")],
        "dup": [("Authorization", f"Bearer {token}"), ("Authorization", "Bearer not-the-token")],
        "space2": [("Authorization", f"Bearer  {token}")],
        "tab": [("Authorization", f"Bearer\t{token}")],
        "trail": [("Authorization", f"Bearer {token} ")],
    }[mode]


@dataclass(frozen=True)
class Step:
    method: str = "POST"
    path: str = "/msg"
    body: bytes = b""
    auth: str = "ok"
    headers: tuple[tuple[str, str], ...] = ()
    note: str = ""

    def live(self, token: str) -> Request:
        return Request(self.method, self.path, auth_headers(self.auth, token) + list(self.headers), self.body)

    def predicted(self) -> EngineRequest:
        return EngineRequest(self.method, route_path(self.path),
                             tuple(auth_headers(self.auth, PRED_TOKEN)) + self.headers, self.body)


def msg(text, **kw) -> Step:
    """A /msg step with a JSON body {"m": text} and a JSON content type."""
    body = json.dumps({"m": text}, ensure_ascii=False).encode()
    return Step(body=body, headers=(("Content-Type", "application/json"),), **kw)


@dataclass(frozen=True)
class Seq:
    name: str
    steps: tuple[Step, ...]
    hypothesis: str = ""


def predict(state, step: Step):
    next_state, response, rule = handle(state, step.predicted(), RULES)
    body = b"" if step.method == "HEAD" else response.body
    return next_state, response.status, body, rule


def show(status: int, body: bytes) -> str:
    return f"{status} {body.decode('utf-8', 'backslashreplace')}"


@dataclass
class Result:
    sequences: int = 0
    steps: int = 0
    live_calls: int = 0
    divergences: list = field(default_factory=list)
    aborted: str = ""


def run(harness, sequences, *, label: str, stop_after: int | None = None, max_calls: int | None = None) -> Result:
    """Run sequences live. `max_calls` bounds this call independently of the harness phase budget."""
    result = Result()
    token = harness.target.token
    for seq in sequences:
        if max_calls is not None and result.live_calls + len(seq.steps) + 1 > max_calls:
            result.aborted = "call cap reached"
            break
        with harness.sequence():
            reset = harness.probe(Request("POST", "/__reset", auth_headers("ok", token)),
                                  f"{label}: reset before {seq.name}", "200 {\"ok\":true}")
            result.live_calls += 1
            if reset.status != 200:
                result.aborted = f"reset failed with {reset.status}"
                return result
            state = initial_state()
            result.sequences += 1
            for index, step in enumerate(seq.steps, 1):
                state, status, body, rule = predict(state, step)
                hypothesis = f"{label}/{seq.name} step {index}: {step.note or seq.hypothesis}"
                response = harness.probe(step.live(token), hypothesis, show(status, body))
                result.live_calls += 1
                result.steps += 1
                if any(k.lower() == "x-frontier-infra" for k, _ in response.headers):
                    result.aborted = "infrastructure rate limit"
                    return result
                ok = response.status == status and bodies_equal(response.body, body)
                if not ok:
                    result.divergences.append({
                        "sequence": seq.name, "step": index, "trace_seq": harness.seq, "rule": rule,
                        "request": {"method": step.method, "path": step.path, "auth": step.auth,
                                    "headers": list(step.headers),
                                    "body": step.body.decode("utf-8", "backslashreplace")},
                        "predicted": show(status, body),
                        "original": show(response.status, response.body)})
                    break
        if stop_after is not None and len(result.divergences) >= stop_after:
            result.aborted = "stop_after reached"
            break
    return result


def write_report(name: str, result: Result) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / f"{name}-{time.strftime('%H%M%S')}.json"
    path.write_text(json.dumps({"sequences": result.sequences, "steps": result.steps,
                                "live_calls": result.live_calls, "aborted": result.aborted,
                                "divergences": result.divergences}, indent=1, ensure_ascii=False))
    return path


def summarize(result: Result) -> str:
    rate = 100 * (result.steps - len(result.divergences)) / result.steps if result.steps else 0
    return (f"sequences={result.sequences} steps={result.steps} live_calls={result.live_calls} "
            f"divergences={len(result.divergences)} step_match={rate:.1f}%"
            + (f" aborted={result.aborted}" if result.aborted else ""))
