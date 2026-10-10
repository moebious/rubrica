import json, sys
sys.path.insert(0, ".")
from tools.harness import Harness
from tools.hb import Request, auth
from rubrica.rules.v2.checksum import control
def m(p): return f"{p};{control(p)}"
h = Harness("probe_e506b", "probe_e506", 120)
tok = h.target.token
def send(text, hyp, pred):
    body = json.dumps({"m": text}, ensure_ascii=False).encode()
    r = h.probe(Request("POST", "/msg", auth(tok) + [("Content-Type", "application/json")], body), hyp, pred)
    return r.status, r.body.decode()
# src(AC-0001)=0, dst(AC-0002)=D, transfer 60000. Prediction: E506 (replica rule) for every D.
for D in (50000, 20000, 10000, 1000, 100):
    with h.sequence():
        h.probe(Request("POST", "/__reset", auth(tok)), f"E506b dst={D}: reset", '200 {"ok":true}')
        for t in ("ALTA;A", "ALTA;B"): send(m(t), f"dst={D}: open", "201")
        send(m(f"DEPOSITO;AC-0002;{D}"), f"dst={D}: fund destination", "200")
        s, b = send(m("TRANSFER;AC-0001;AC-0002;60000"), f"dst={D}: src empty, amount over limit", "422 E506")
        print("dst", D, "->", json.loads(b).get("error"))
