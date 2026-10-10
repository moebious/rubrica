"""Single-request sweep of Unicode / JSON-escape / whitespace edge cases, each from the initial state.

The replica predicts; the original judges (tools/difftest.py). Controls are computed with the
replica's ASCII-only checksum, which two probes established. Every case is one request after reset.
"""
import json, sys
sys.path.insert(0, ".")
from rubrica.rules.v2.checksum import control
from tools.difftest import Seq, Step, msg, run, summarize, write_report
from tools.harness import Harness

def c(p): return f"{p};{control(p)}"
RAW = lambda body, note: Seq(note, (Step(body=body, headers=(("Content-Type", "application/json"),), note=note),), note)
M = lambda text, note: Seq(note, (msg(text, note=note),), note)

cases = [
 # whitespace and separators in the message
 M(c("ALTA;a\u00a0b"), "nbsp in name"), M(c("ALTA;a\u2003b"), "em space in name"), M(c("ALTA;a\tb"), "tab in name"),
 M(c("ALTA;a\nb"), "newline in name"), M(c("ALTA;a\u0000b"), "NUL in name"), M(c("ALTA;\u200b"), "zero-width space name"),
 M("ALTA;a;b;" + str(control("ALTA;a;b")), "extra arg"), M(c("ALTA;\uff1b"), "fullwidth semicolon name"),
 # fullwidth / lookalike letters and digits
 M(c("\uff30\uff29\uff2e\uff27"), "fullwidth PING"), M("PING;\uff16\uff14", "fullwidth control digits"),
 M(c("CONSULTA;AC-\uff10\uff10\uff10\uff11"), "fullwidth digits in id"), M(c("DEPOSITO;AC-0001;\uff11\uff10\uff10"), "fullwidth amount"),
 M("PING;6\u0664", "arabic-indic digit control"), M("PING;\u0663\u0664", "arabic digits control"),
 M(c("ALTA;ǅ"), "titlecase digraph"), M(c("ALTA;ŉ"), "n-apostrophe"), M(c("ALTA;ǰ"), "j with caron"),
 M(c("ALTA;\u0130"), "dotted capital I"), M(c("ALTA;\u212a"), "kelvin sign"), M(c("ALTA;\u017f\u017f"), "long s pair"),
 # control field forms
 M("ALTA;a;+82", "plus control"), M("ALTA;a;082", "three digit control"), M("ALTA;a;8 2", "space in control"),
 M("ALTA;a; 82", "leading space control"), M("ALTA;a;82 ", "trailing space control"), M("ALTA;a;8\u0662", "mixed digit control"),
 M("ALTA;a;0", "control zero"), M("ALTA;a;00", "control 00"), M("ALTA;a;99", "control 99"), M("ALTA;a;100", "control 100"),
 # case of command and id parts
 M(c("alta;x"), "lowercase alta"), M(c("ConSuLta;AC-0001"), "mixed consulta"), M(c("CONSULTA;ac-0001"), "lowercase id"),
 M(c("ANULA;op-0001"), "lowercase op id"), M(c("DEPOSITO;AC-0001;1_0"), "underscore amount"), M(c("DEPOSITO;AC-0001;0x10"), "hex amount"),
 # JSON escapes and structure
 RAW(b'{"m":"PING\\u003b64"}', "escaped semicolon"), RAW(b'{"m":"\\u0050ING;64"}', "escaped P"),
 RAW(b'{"m":"PING;64"}  \n', "trailing whitespace"), RAW(b'\t{"m":"PING;64"}', "leading tab"),
 RAW(b'{"m":"PING;64","m":"PING;99"}', "duplicate key last wins"), RAW(b'{"m":"PING;99","m":"PING;64"}', "duplicate key"),
 RAW(b'{"m":"\\ud800"}', "lone surrogate"), RAW(b'{"m":"PING;64\\u0000"}', "NUL after control"),
 RAW(b'{"m":"PING;64"}\x00', "NUL after body"), RAW(b'{"m":1e2}', "number m"), RAW(b'{"m":-0}', "negative zero m"),
 RAW(b'{"m":"PING;64"} {"m":"PING;64"}', "two documents"), RAW(b'{"m" : "PING;64" }', "spaces in object"),
 RAW(b"{'m':'PING;64'}", "single quotes"), RAW(b'{"m":"PING;64",}', "trailing comma"), RAW(b'{"m":"PING;64"', "unterminated"),
 RAW(b'{"m":"PING;64"}'.replace(b"m", b"\\u006d"), "escaped key"),
]
h = Harness("probe_text_edges", "probe_text_edges", 160)
result = run(h, cases, label="text-edges")
print(summarize(result)); print(write_report("text-edges", result))
for d in result.divergences:
    print(" DIVERGENCE", d["sequence"], repr(d["request"]["body"][:70]), "\n   predicted:", d["predicted"][:100], "\n   original: ", d["original"][:100])
