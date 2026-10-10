import json, sys
sys.path.insert(0, ".")
from tools.harness import Harness
from tools.hb import Request, auth
from rubrica.rules.v2.checksum import control

def m(p): return f"{p};{control(p)}"
h = Harness("probe_e506", "probe_e506", 80)
tok = h.target.token
def send(text, hyp, pred):
    body = json.dumps({"m": text}, ensure_ascii=False).encode()
    r = h.probe(Request("POST", "/msg", auth(tok) + [("Content-Type", "application/json")], body), hyp, pred)
    return r.status, r.body.decode()

# (name, setup steps, final transfer amount, predicted code under H: E507 iff src<amount AND dst balance>0)
CASES = [
 ("dst1_src0_60000",  ["DEPOSITO;AC-0002;1"], 60000, "E507"),
 ("dst1_src0_50001",  ["DEPOSITO;AC-0002;1"], 50001, "E507"),
 ("dst1_src100_60000",["DEPOSITO;AC-0001;100","DEPOSITO;AC-0002;1"], 60000, "E507"),
 ("dst0after_anula",  ["DEPOSITO;AC-0002;5","ANULA;OP-0001"], 60000, "E506"),
 ("third_only",       ["ALTA;C","DEPOSITO;AC-0003;5"], 60000, "E506"),
 ("src_ok_dst1_60000",["DEPOSITO;AC-0001;60000","DEPOSITO;AC-0002;1"], 60000, "E506"),
 ("dst1_src0_50000",  ["DEPOSITO;AC-0002;1"], 50000, "E507"),
]
out = []
for name, setup, amount, pred in CASES:
    with h.sequence():
        h.probe(Request("POST", "/__reset", auth(tok)), f"E506-vs-E507 {name}: reset", '200 {"ok":true}')
        for text in ("ALTA;A", "ALTA;B"):
            send(m(text), f"{name}: open account", "201")
        for text in setup:
            send(m(text), f"{name}: setup", "200/201")
        status, body = send(m(f"TRANSFER;AC-0001;AC-0002;{amount}"),
                            f"{name}: does destination balance decide E506 vs E507 when source is short?", f"422 {pred}")
        got = json.loads(body).get("error")
        out.append((name, amount, pred, got, "MATCH" if got == pred else "DIFFERENT"))
for row in out: print(row)
