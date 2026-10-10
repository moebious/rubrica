import json, sys
sys.path.insert(0, ".")
from tools.harness import Harness
from tools.hb import Request, auth
from rubrica.rules.v2.checksum import control
def m(p): return f"{p};{control(p)}"
h = Harness("probe_owner", "probe_owner", 120)
tok = h.target.token
def send(text, hyp, pred):
    body = json.dumps({"m": text}, ensure_ascii=False).encode()
    r = h.probe(Request("POST", "/msg", auth(tok) + [("Content-Type", "application/json")], body), hyp, pred)
    return r.status, r.body.decode()
H = "H2: transfers between accounts with the same owner name skip the 50,000 ceiling (only funds are checked)"
CASES = [  # name, (nameA, nameB), setup deposits, transfer amount, prediction, extra steps
 ("same_funded_60000", ("Ana","Ana"), ["DEPOSITO;AC-0001;60000"], 60000, "200"),
 ("same_funded_exactly_50001", ("Ana","Ana"), ["DEPOSITO;AC-0001;50001"], 50001, "200"),
 ("same_short_60000", ("Ana","Ana"), ["DEPOSITO;AC-0001;100"], 60000, "E507"),
 ("case_differs", ("Ana","ana"), ["DEPOSITO;AC-0001;60000"], 60000, "E506"),
 ("trailing_space", ("Ana","Ana "), ["DEPOSITO;AC-0001;60000"], 60000, "E506"),
 ("diff_funded_60000", ("Ana","Bea"), ["DEPOSITO;AC-0001;60000"], 60000, "E506"),
]
for name, (a, b), setup, amount, pred in CASES:
    with h.sequence():
        h.probe(Request("POST", "/__reset", auth(tok)), f"owner {name}: reset", '200 {"ok":true}')
        send(m(f"ALTA;{a}"), f"{name}: open A", "201"); send(m(f"ALTA;{b}"), f"{name}: open B", "201")
        for t in setup: send(m(t), f"{name}: fund", "200")
        s, body = send(m(f"TRANSFER;AC-0001;AC-0002;{amount}"), f"{name}: {H}", pred)
        j = json.loads(body); got = j.get("error") or ("200" if s == 200 else str(s))
        print(f"{name:28} predicted {pred:5} got {got:5} {'MATCH' if got==pred else 'DIFFERENT'}")
