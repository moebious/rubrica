"""How does the original treat repeated Authorization headers?

Seen in held-out seed 8: POST /__reset with [Bearer <valid>, Bearer not-the-token] -> 200 (replica: 401).
Candidate rules: H1 first header wins; H2 any valid header suffices; H3 last header wins; H4 values are
joined and the first token is used. Order and route are varied so the hypotheses give different answers.
Each probe's prediction states H1 (first wins); a miss is informative.
"""
import json, sys
sys.path.insert(0, ".")
from tools.harness import Harness
from tools.hb import Request

h = Harness("probe_dup_auth", "probe_dup_auth", 60)
tok = h.target.token
V, W = f"Bearer {tok}", "Bearer not-the-token"
CASES = [  # name, header values in order, predicted status under H1 (first wins)
 ("valid_then_wrong", [V, W], 200), ("wrong_then_valid", [W, V], 401),
 ("valid_then_valid", [V, V], 200), ("wrong_then_wrong", [W, W], 401),
 ("valid_then_empty", [V, ""], 200), ("empty_then_valid", ["", V], 401),
 ("valid_then_basic", [V, "Basic abc"], 200), ("basic_then_valid", ["Basic abc", V], 401),
]
with h.sequence():
    for path, method in (("/__reset", "POST"), ("/health", "GET")):
        for name, values, pred in CASES:
            r = h.probe(Request(method, path, [("Authorization", v) for v in values]),
                        f"H1(first Authorization header wins) {method} {path} {name}", f"{pred}")
            print(f"{method:4} {path:9} {name:18} predicted {pred} got {r.status} {r.body.decode()[:34]}")
    body = json.dumps({"m": "PING;64"}).encode()
    for name, values, pred in CASES[:2]:
        r = h.probe(Request("POST", "/msg", [("Authorization", v) for v in values] + [("Content-Type", "application/json")], body),
                    f"H1 POST /msg {name}", f"{pred}")
        print(f"POST /msg      {name:18} predicted {pred} got {r.status} {r.body.decode()[:34]}")
