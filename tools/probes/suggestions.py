"""E301 `sugerencia`: which command does the original suggest when several are equally close?

Replica rule: nearest by Levenshtein distance <= 2, ties broken by list order (PING, ALTA, CONSULTA,
DEPOSITO, TRANSFER, ANULA). Observed so far (31 words) is consistent with that, but also with
"alphabetical" or other tie rules in most cases. This probe uses words where the candidate tie rules
DISAGREE (list-first vs alphabetical-first vs list-last) plus distance-2/3 boundary words.
The replica predicts; the original judges (tools/difftest.py).
"""
import itertools, sys
sys.path.insert(0, ".")
from rubrica.rules.v2.checksum import control
from rubrica.rules.v2.protocol import COMMANDS, distance
from tools.difftest import Seq, msg, run, summarize, write_report
from tools.harness import Harness

def c(p): return f"{p};{control(p)}"
ALPHA = "ALTPINGCOSUDERFX"
ties = []
for n in range(1, 6):
    for w in map(''.join, itertools.product(ALPHA, repeat=n)):
        if n >= 4 and len(ties) > 4000: break
        ds = {k: distance(w, k) for k in COMMANDS}
        best = min(ds.values())
        if best > 2: continue
        cands = [k for k in COMMANDS if ds[k] == best]
        if len(cands) < 2: continue
        first, alpha, last = cands[0], sorted(cands)[0], cands[-1]
        if len({first, alpha, last}) >= 2:
            ties.append((w, cands, first, alpha, last))
import random
random.Random(5).shuffle(ties)
picked, seen_pairs = [], set()
for w, cands, first, alpha, last in ties:
    key = tuple(cands)
    if key in seen_pairs and len(picked) > 8: continue
    seen_pairs.add(key); picked.append(w)
    if len(picked) >= 24: break
boundary = ["CONSULTAXX", "ALTAXXX", "PINGGGG", "ANULAXXX", "TRANSFERXX", "DEPOSITOXX", "CONSULTAR", "TRANSFERIR", "ANULAR",
            "DEPOSITAR", "SALDO", "ALTAS", "PINGS", "CONSULTAS", "TRANSFERS", "NULA", "ULA", "TRANSFE", "DEPOS", "CONS"]
words = picked + boundary
print(len(picked), "tie words +", len(boundary), "boundary words")
seqs = [Seq(f"S{i:02d}-{w}", (msg(c(w + ";AC-0001"), note=f"suggestion for {w!r}"),), "E301 suggestion") for i, w in enumerate(words)]
h = Harness("probe_suggestions", "probe_suggestions", 120)
result = run(h, seqs, label="suggestions")
print(summarize(result)); print(write_report("suggestions", result))
for d in result.divergences:
    print(" DIVERGENCE", repr(d["request"]["body"][:50]), "\n   predicted:", d["predicted"][:110], "\n   original: ", d["original"][:110])
