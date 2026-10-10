"""Held-out measurement set. Built to NOT share the blind spots of the fuzzer (tools/fuzz.py).

Two independent sources, both seeded and deterministic:
  A. mutations of the README examples: a prefix of the official sequence, then one mutated step;
  B. structure-agnostic noise: random methods, paths, headers and bodies with no knowledge of the
     message grammar.

Rule (from the design): this set only MEASURES. Run it before a fix and after it. Once a
divergence from it guides a fix, those sequences become regression evidence and a new held-out set
(new seed) replaces them.

  python3 tools/heldout.py --seed 7 --dry                 # list, no network
  python3 tools/heldout.py --seed 7 --max-calls 400       # live, through the harness
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parent.parent
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(ROOT))

from tools.difftest import AUTH_MODES, Seq, Step, msg, run, summarize, write_report

EXAMPLES = [json.loads(line)["request"]["m"]
            for line in (ROOT / "material/pruebas/ejemplos.jsonl").read_text().splitlines() if line.strip()]

METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRACE")
PATHS = ("/msg", "/msg/", "/MSG", "/Msg", "//msg", "/msg/x", "/msg?a=1", "/msg#f", "/", "/health", "/health/",
         "/__reset", "/__reset/", "/__RESET", "/%6dsg", "/msg%20", "/admin", "/favicon.ico", "/.env", "/api/msg")
CONTENT_TYPES = ("application/json", "application/json; charset=utf-8", "text/plain", "application/x-www-form-urlencoded",
                 "APPLICATION/JSON", "application/jsonx", "multipart/form-data", "")
BODIES = (b"", b"{}", b"[]", b"null", b"0", b'""', b"{", b'{"m":', b'{"m":null}', b'{"m":1}', b'{"m":true}',
          b'{"m":[]}', b'{"m":{}}', b'{"m":""}', b'{"m":" "}', b'{"m":";"}', b'{"m":";;"}', b'{"M":"PING;64"}',
          b'{"m":"PING;64","x":1}', b'{"m":"PING;64","m":"PING;64"}', b'{"m":"PING;64"} ', b'\xef\xbb\xbf{"m":"PING;64"}',
          b'{"m":"PING;64"}garbage', b"\xff\xfe", b'{"m":"\xff"}', b'{"m":"PING;64"}\n', b" {\"m\":\"PING;64\"}",
          b'{"m":"PING\\u003b64"}', b'{"m":"p\\u0069ng;64"}', b'{"m":NaN}', b'{"m":"PING;64",}', b"[\"PING;64\"]")


def mutate(rng: random.Random, text: str) -> tuple[str, str]:
    """One syntactic mutation of a message string. Returns (mutated, description)."""
    parts = text.split(";")
    choice = rng.randrange(14)
    if choice == 0:
        return text.lower(), "lowercase whole message"
    if choice == 1:
        i = rng.randrange(len(text))
        return text[:i] + text[i].swapcase() + text[i + 1:], "flip case of one character"
    if choice == 2 and len(parts) > 2:
        i = rng.randrange(1, len(parts) - 1)
        parts[i] = parts[i][:-1] if parts[i] else parts[i]
        return ";".join(parts), "drop last character of an argument"
    if choice == 3:
        return ";".join(parts[:-1]) + ";" + str((int(parts[-1]) + 1) % 100 if parts[-1].isdigit() else 0), "control + 1"
    if choice == 4:
        return text + ";", "trailing separator"
    if choice == 5:
        return ";" + text, "leading separator"
    if choice == 6:
        return " " + text, "leading space"
    if choice == 7:
        return text + " ", "trailing space"
    if choice == 8 and len(parts) > 2:
        parts.insert(1, rng.choice(("", "X", "AC-0001", "1")))
        return ";".join(parts), "insert an argument"
    if choice == 9 and len(parts) > 2:
        del parts[1]
        return ";".join(parts), "remove first argument"
    if choice == 10:
        return text.replace(";", ";;", 1), "double separator"
    if choice == 11:
        return text.replace("AC-000", "AC-00", 1) if "AC-000" in text else text + "0", "alter an ID"
    if choice == 12:
        return parts[0] + ";" + parts[-1], "command and control only"
    return text[::-1], "reverse the message"


def examples_mutations(rng: random.Random, count: int) -> list[Seq]:
    out = []
    for n in range(count):
        cut = rng.randrange(0, len(EXAMPLES))
        prefix = tuple(msg(m, note="official example prefix") for m in EXAMPLES[:cut])
        target = EXAMPLES[cut]
        mutated, what = mutate(rng, target)
        step = msg(mutated, note=f"mutation of example {cut + 1}: {what}")
        out.append(Seq(f"A{n:03d}-ex{cut + 1}", prefix + (step,), "mutation of an official example"))
    return out


def noise(rng: random.Random, count: int) -> list[Seq]:
    out = []
    for n in range(count):
        method = rng.choice(METHODS)
        path = rng.choice(PATHS)
        body = rng.choice(BODIES) if method not in ("GET", "HEAD") or rng.random() < 0.2 else b""
        ctype = rng.choice(CONTENT_TYPES)
        headers = (("Content-Type", ctype),) if ctype else ()
        if rng.random() < 0.15:
            headers += (("X-Req", "9"),)
        auth = rng.choice(AUTH_MODES) if rng.random() < 0.4 else "ok"
        step = Step(method, path, body, auth, headers,
                    f"noise: {method} {path} auth={auth} ctype={ctype!r} body={body[:24]!r}")
        out.append(Seq(f"B{n:03d}", (step,), "structure-agnostic noise"))
    return out


def build(seed: int, a_count: int = 45, b_count: int = 55) -> list[Seq]:
    rng = random.Random(seed)
    return examples_mutations(rng, a_count) + noise(rng, b_count)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--a", type=int, default=45)
    parser.add_argument("--b", type=int, default=55)
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--max-calls", type=int, default=400)
    parser.add_argument("--budget", type=int, default=450, help="harness phase budget")
    args = parser.parse_args()
    seqs = build(args.seed, args.a, args.b)
    if args.dry:
        calls = sum(len(s.steps) + 1 for s in seqs)
        print(f"{len(seqs)} sequences, {calls} live calls would be needed")
        for s in seqs[:12] + seqs[-6:]:
            print(" ", s.name, len(s.steps), s.steps[-1].note[:100])
        return 0
    from tools.harness import Harness
    harness = Harness(f"heldout_seed{args.seed}", f"heldout{args.seed}", args.budget)
    result = run(harness, seqs, label=f"heldout-{args.seed}", max_calls=args.max_calls)
    print(summarize(result))
    print("report:", write_report(f"heldout-{args.seed}", result))
    for d in result.divergences:
        print(" DIVERGENCE", d["sequence"], d["request"]["method"], d["request"]["path"], d["request"]["auth"],
              repr(d["request"]["body"][:70]), "\n    predicted:", d["predicted"][:100], "\n    original: ", d["original"][:100])
    return 1 if result.divergences else 0


if __name__ == "__main__":
    raise SystemExit(main())
