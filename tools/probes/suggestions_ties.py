"""Confirm the E301 tie rule after the fix: ties go to the alphabetically first command.
Words tie between PING and ALTA, where list order (PING) and alphabetical order (ALTA) disagree.
Prediction (replica after the fix): sugerencia = ALTA for every word."""
import sys
sys.path.insert(0, ".")
from rubrica.rules.v2.checksum import control
from tools.difftest import Seq, msg, run, summarize, write_report
from tools.harness import Harness
def c(p): return f"{p};{control(p)}"
words = ["AINA", "PLTG", "PLNA", "ALNG", "AITG", "PITA", "NLA", "ALTNG"]
seqs = [Seq(f"T{i}-{w}", (msg(c(w + ";AC-0001"), note=f"tie word {w}"),), "E301 tie") for i, w in enumerate(words)]
result = run(Harness("probe_suggestions_ties", "probe_suggestion_ties", 30), seqs, label="suggestion-ties")
print(summarize(result))
for d in result.divergences:
    print(" DIVERGENCE", d["request"]["body"][:40], "pred", d["predicted"][-30:], "orig", d["original"][-30:])
