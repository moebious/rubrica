"""Does the original match command names with ASCII-only case folding?

The replica uppercases the command with str.upper(), so "p\u0131ng" (dotless i) and "con\u017fulta"
(long s) become PING and CONSULTA. H: the original compares ASCII-case-insensitively, so these are
unknown commands (400 E301, or E202 if the control is wrong). The control is the checksum of the text
as sent (ASCII-only uppercase), which the previous probe established.
Prediction: 400 E301 for every probe. Each is sent from the initial state.
"""
import json, sys
sys.path.insert(0, ".")
from tools.harness import Harness
from tools.hb import Request, auth
from rubrica.rules.v2.checksum import control

h = Harness("probe_unicode_command", "probe_unicode", 120)
tok = h.target.token
CASES = [("p\u0131ng", "PING", "p\u0131ng;64"), ("con\u017fulta", "CONSULTA", None), ("depo\u017fito", "DEPOSITO", None),
         ("tran\u017ffer", "TRANSFER", None), ("\u0131", "-", None)]
with h.sequence():
    h.probe(Request("POST", "/__reset", auth(tok)), "unicode-command: reset", '200 {"ok":true}')
    for cmd, folds_to, fixed in CASES:
        if cmd == "\u0131":
            continue
        text = fixed or f"{cmd};AC-0001;{control(cmd + ';AC-0001')}"
        body = json.dumps({"m": text}, ensure_ascii=False).encode()
        r = h.probe(Request("POST", "/msg", auth(tok) + [("Content-Type", "application/json")], body),
                    f"H(ASCII-only command match): {cmd!r} (folds to {folds_to}) is an unknown command", "400 E301")
        print(f"{cmd!r:16} folds_to={folds_to:9} -> {r.status} {r.body.decode()[:60]}")
