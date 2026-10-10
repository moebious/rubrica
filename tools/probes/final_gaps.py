"""Last-hour gap probes: token shapes (H1), leading-zero controls (H3), HALT variants, ANULA on locked accounts.
The replica predicts; the original judges. Tokens are derived at runtime and never printed or stored in clear."""
import json, sys
sys.path.insert(0, ".")
from rubrica.rules.v2.checksum import control
from tools.difftest import Seq, Step, msg, run, summarize, write_report
from tools.harness import Harness

def c(p): return f"{p};{control(p)}"
h = Harness("probe_final_gaps", "probe_final_gaps", 140)
tok = h.target.token
flip = tok[:-1] + ("0" if tok[-1] != "0" else "1")
fakes = {"wellformed_fake": "-".join(("cn", "p", "a" * 16, "b" * 16)), "team_last_char_changed": flip,
         "team_uppercased": tok.upper(), "team_with_trailing_space": tok + " ", "team_prefix_only": tok[:12]}
seqs = []
for name, value in fakes.items():
    for method, path, body in (("POST", "/__reset", b""), ("GET", "/health", b""), ("POST", "/msg", b'{"m":"PING;64"}')):
        seqs.append(Seq(f"H1-{name}-{path}", (Step(method, path, body, "none", (("Authorization", f"Bearer {value}"),) + ((("Content-Type", "application/json"),) if body else ()),
                                                 f"token shape {name} on {path}"),), "H1 token shapes"))
# H3 leading zero controls (control of ALTA;Mateo is 3)
seqs += [Seq("H3-alta-03", (msg("ALTA;Mateo;03", note="control 3 written as 03"),), "H3"),
         Seq("H3-alta-003", (msg("ALTA;Mateo;003", note="control 3 written as 003"),), "H3"),
         Seq("H3-consulta-014", (msg(c("ALTA;Lucia")), msg("CONSULTA;AC-0001;014", note="control 14 as 014")), "H3"),
         Seq("H3-ping-064", (msg("PING;064", note="PING with 064"), msg("PING;0", note="PING;0")), "H3")]
# HALT variants
seqs += [Seq("HALT-variants", (msg(c("HALT;AC-0001"), note="HALT valid"), msg("HALT;AC-0001;00", note="HALT bad control"),
                               msg("HALT;AC-0001;5X", note="HALT malformed control"), msg("HALT;;" + str(control("HALT;")), note="HALT empty arg"),
                               msg(c("halt;AC-0001"), note="HALT lowercase"), msg(c("HALT;AC-0001;AC-0002"), note="HALT 2 args"),
                               msg(c("HALT;ni siquiera existe"), note="HALT arbitrary arg"), msg(c("ALTA;Z"), note="service still answers after HALT"),
                               msg(c("PING"), note="ping after halt"), msg("PING;64", note="PING;64")), "HALT")]
# ANULA on locked accounts
lock = [msg(c("ALTA;A")), msg(c("ALTA;B")), msg(c("DEPOSITO;AC-0001;1000"))] + [msg(c("TRANSFER;AC-0001;AC-0002;60000"), note="fail to lock") for _ in range(3)]
seqs += [Seq("H4-cancel-deposit-while-locked", tuple(lock) + (msg(c("ANULA;OP-0001"), note="cancel the deposit of a locked account"), msg(c("CONSULTA;AC-0001")),
                                                             msg(c("TRANSFER;AC-0001;AC-0002;1"), note="transfer after cancel while locked"), msg(c("DEPOSITO;AC-0001;5000"), note="deposit clears lock?"),
                                                             msg(c("TRANSFER;AC-0001;AC-0002;1"), note="transfer after unlock")), "H4"),
         Seq("H4-cancel-incoming-to-locked", tuple(lock[:2]) + (msg(c("DEPOSITO;AC-0002;1000")), msg(c("TRANSFER;AC-0002;AC-0001;500")),
                                                              ) + tuple(msg(c("TRANSFER;AC-0001;AC-0002;60000"), note="fail to lock") for _ in range(3)) + (
                                                              msg(c("ANULA;OP-0002"), note="cancel incoming transfer on locked destination"), msg(c("CONSULTA;AC-0001")), msg(c("CONSULTA;AC-0002")),
                                                              msg(c("TRANSFER;AC-0001;AC-0002;1"), note="still locked")), "H4")]
print(len(seqs), "sequences,", sum(len(s.steps) + 1 for s in seqs), "calls")
result = run(h, seqs, label="final-gaps")
print(summarize(result)); print(write_report("final-gaps", result))
for d in result.divergences:
    print(" DIVERGENCE", d["sequence"], "step", d["step"], d["request"]["body"][:50] or d["request"]["path"], "\n   predicted:", d["predicted"][:100], "\n   original: ", d["original"][:100])
