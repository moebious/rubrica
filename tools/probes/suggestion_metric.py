"""E301 suggestion metric: plain Levenshtein (replica) or Damerau (adjacent swap costs 1)?

Words below have Levenshtein distance > 2 to every command but Damerau distance <= 2 to one of them.
Replica prediction (plain Levenshtein): no `sugerencia`. If the original uses Damerau it suggests the command.
"""
import sys
sys.path.insert(0, ".")
from rubrica.rules.v2.checksum import control
from tools.difftest import Seq, msg, run, summarize, write_report
from tools.harness import Harness
def c(p): return f"{p};{control(p)}"
words = ["IPGN", "LAAT", "OCSNULTA", "CNOUSLTA", "COSNLUTA", "EDOPSITO", "DPESOITO", "DEOPISTO"]
seqs = [Seq(f"M{i}-{w}", (msg(c(w + ";AC-0001"), note=f"metric word {w}"),), "E301 metric") for i, w in enumerate(words)]
result = run(Harness("probe_suggestion_metric", "probe_suggestion_metric", 30), seqs, label="suggestion-metric")
print(summarize(result))
for d in result.divergences:
    print(" DIVERGENCE", d["request"]["body"][:34], "| replica:", d["predicted"][-34:], "| original:", d["original"][-40:])
