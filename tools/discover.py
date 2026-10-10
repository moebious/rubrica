"""Small typed probe interface around the coordinated budgeted harness."""
import json
from tools.harness import Harness
from tools.hb import Request, Response, auth

def candidate_control(prefix: str) -> int:
    remainder = 0
    for char in prefix.upper():
        digits = char if "0" <= char <= "9" else str(ord(char) - 64) if "A" <= char <= "Z" else ""
        for digit in digits:
            remainder = (remainder * 10 + int(digit)) % 97
    return 98 - (remainder * 100) % 97

def reset(harness: Harness) -> Response:
    return harness.probe(Request("POST", "/__reset", auth(harness.target.token)),
                         "Reset before an independent banking experiment", "200 {ok:true}")

def message(harness: Harness, prefix: str, hypothesis: str, prediction: str,
            *, control: str | None = None) -> Response:
    suffix = str(candidate_control(prefix)) if control is None else control
    body = json.dumps({"m": prefix + ";" + suffix}, ensure_ascii=False).encode()
    return harness.probe(Request("POST", "/msg", auth(harness.target.token) + [("Content-Type", "application/json")], body), hypothesis, prediction)
