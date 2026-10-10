"""Does the original uppercase only ASCII letters before the checksum? (replica uses str.upper())

H: control is computed on ASCII-uppercased text; non-ASCII letters (even ones Unicode folds to ASCII,
such as U+00DF -> SS) are ignored like any other non-alphanumeric character.
Prediction per probe: the name is accepted (201) iff the control equals the ASCII-only value.
"""
import json, sys
sys.path.insert(0, ".")
from tools.harness import Harness
from tools.hb import Request, auth

def ctl(prefix, upper):
    r = 0
    for ch in upper(prefix):
        if "0" <= ch <= "9": e = ch
        elif "A" <= ch <= "Z": e = str(ord(ch) - 64)
        else: continue
        for d in e: r = (r * 10 + ord(d) - 48) % 97
    return 98 - (r * 100) % 97

ascii_up = lambda s: "".join(c.upper() if "a" <= c <= "z" else c for c in s)
h = Harness("probe_unicode_upper", "probe_unicode", 60)
tok = h.target.token
CHARS = {"sharp_s": "\u00df", "dotless_i": "\u0131", "long_s": "\u017f", "fi_ligature": "\ufb01", "n_apostrophe": "\u0149"}
with h.sequence():
    h.probe(Request("POST", "/__reset", auth(tok)), "unicode-upper: reset", '200 {"ok":true}')
    for name, ch in CHARS.items():
        prefix = f"ALTA;{ch}"
        for label, value in (("ascii_only", ctl(prefix, ascii_up)), ("full_upper", ctl(prefix, str.upper))):
            if label == "full_upper" and value == ctl(prefix, ascii_up):
                continue  # identical control: nothing to distinguish
            body = json.dumps({"m": f"{prefix};{value}"}, ensure_ascii=False).encode()
            expect = "201" if label == "ascii_only" else "400 E202"
            r = h.probe(Request("POST", "/msg", auth(tok) + [("Content-Type", "application/json")], body),
                        f"H(ASCII-only uppercase): {name} with the {label} control {value}", expect)
            print(f"{name:13} {label:10} control={value:2} -> {r.status} {r.body.decode()[:46]}   predicted {expect}")
