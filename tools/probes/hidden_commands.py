"""The original suggested HALT for LAAT, so a command outside our six exists.

Step 1: send HALT with 0, 1, 2 arguments after a reset. Replica prediction (no such command): 400 E301.
        A miss is the finding. Nothing here is irreversible: /__reset restores the token (README).
Step 2: find other hidden commands via the `sugerencia` field using random short words
        (E301 answers carry the nearest command within distance 2).
"""
import json, random, sys
sys.path.insert(0, ".")
from rubrica.rules.v2.checksum import control
from tools.harness import Harness
from tools.hb import Request, auth

h = Harness("probe_hidden_commands", "probe_hidden", 140)
tok = h.target.token
def send(text, hyp, pred):
    body = json.dumps({"m": f"{text};{control(text)}"}, ensure_ascii=False).encode()
    r = h.probe(Request("POST", "/msg", auth(tok) + [("Content-Type", "application/json")], body), hyp, pred)
    return r.status, r.body.decode()

with h.sequence():
    h.probe(Request("POST", "/__reset", auth(tok)), "hidden-commands: reset", '200 {"ok":true}')
    for text in ("HALT", "HALT;AC-0001", "HALT;AC-0001;1", "halt", "HALT;OP-0001"):
        print(f"{text:16}", send(text, f"does HALT exist? {text}", "400 E301 (replica has no HALT)"))
    rng = random.Random(21)
    known = {"PING", "ALTA", "CONSULTA", "DEPOSITO", "TRANSFER", "ANULA"}
    found = {}
    for _ in range(60):
        w = "".join(rng.choice("ABCDEFGHILMNOPRSTUV") for _ in range(rng.randint(3, 5)))
        s, b = send(w + ";X", f"suggestion discovery with random word {w}", "400 E301, no suggestion or a known command")
        sug = json.loads(b).get("sugerencia")
        if sug and sug not in known:
            found.setdefault(sug, []).append(w)
    print("hidden suggestions:", found)
