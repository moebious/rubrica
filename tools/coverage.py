"""Zero-request audit: replay every recorded original exchange through the replica and map coverage.

Reads traces/*.jsonl only. Never contacts the original or a replica.

Era is assigned from timestamps bracketing the observed change: the canary last matched the
pinned v1 baseline at the cycle ending ~20:50:13Z and first differed in the cycle starting
21:00:07Z. Exchanges in between are "uncertain" and must match under at least one policy.

  python3 tools/coverage.py            # mismatch report + coverage matrix
  python3 tools/coverage.py --json     # machine-readable
"""
from __future__ import annotations

import argparse
import base64
import collections
import glob
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(ROOT))

from rubrica.engine.contract import Request
from rubrica.engine.core import handle
from rubrica.rules.v2.policy import V1, V2
from rubrica.rules.v2.rules import build_rules
from rubrica.rules.v2.state import initial_state
from tools.comparator import bodies_equal

V1_UNTIL = "2026-10-10T20:50:13"
V2_FROM = "2026-10-10T21:00:07"
TOKEN = "audit-token"
COMMANDS = ("PING", "ALTA", "CONSULTA", "DEPOSITO", "TRANSFER", "ANULA")
# Outcomes each command can produce, per the observed pipeline (the "expected matrix").
EXPECTED = {
    "PING": ("200", "E103", "E104", "E302"),
    "ALTA": ("201", "E104", "E201", "E202", "E302"),
    "CONSULTA": ("200", "E201", "E202", "E302", "E401"),
    "DEPOSITO": ("200", "E201", "E202", "E302", "E303", "E401"),
    "TRANSFER": ("200", "E201", "E202", "E302", "E303", "E304", "E401", "E506", "E507", "E510"),
    "ANULA": ("200:ok", "200:ya anulada", "E201", "E202", "E302", "E402"),
}


def era(ts: str) -> str:
    stamp = ts[:19]
    if stamp <= V1_UNTIL:
        return "v1"
    return "v2" if stamp >= V2_FROM else "uncertain"


def load() -> list[dict]:
    rows = []
    for path in glob.glob(str(ROOT / "traces" / "*.jsonl")):
        name = Path(path).name
        lines = Path(path).read_text().splitlines()
        for number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                if number == len(lines):  # a live watcher may be mid-append
                    continue
                raise
            if row.get("target") != "original" or row.get("infra") or "res" not in row:
                continue
            row["_src"] = f"{name}:{number}"
            rows.append(row)
    rows.sort(key=lambda r: (r["ts"], r["_src"]))
    return rows


def to_request(row: dict) -> Request:
    headers = tuple((k, v.replace("<TOKEN>", TOKEN)) for k, v in row["req"]["headers"])
    return Request(row["req"]["method"], row["req"]["path"], headers, base64.b64decode(row["req"]["body_b64"]))


def outcome(command: str, status: int, body) -> str:
    if status in (200, 201) and command == "ANULA" and isinstance(body, dict):
        return "200:ok" if body.get("ok") is True else "200:ya anulada"
    if isinstance(body, dict) and "error" in body:
        return str(body["error"])
    return str(status)


def replay(rows: list[dict]) -> tuple[list[dict], dict]:
    rulesets = {"v1": build_rules(TOKEN, V1), "v2": build_rules(TOKEN, V2)}
    states = {"v1": initial_state(), "v2": initial_state()}
    mismatches, cells = [], collections.Counter()
    for row in rows:
        request, expected_status = to_request(row), row["res"]["status"]
        expected_body = base64.b64decode(row["res"]["body_b64"])
        label = era(row["ts"])
        verdicts = {}
        for version, rules in rulesets.items():
            states[version], response, rule = handle(states[version], request, rules)
            verdicts[version] = (response.status == expected_status and bodies_equal(response.body, expected_body), rule)
        ok = {"v1": verdicts["v1"][0], "v2": verdicts["v2"][0],
              "uncertain": verdicts["v1"][0] or verdicts["v2"][0]}[label]
        if not ok:
            mismatches.append({"src": row["_src"], "era": label, "request": row["req"].get("body_text", "")[:90],
                               "expected": row["res"]["body_text"][:100], "status": expected_status,
                               "v1": verdicts["v1"], "v2": verdicts["v2"]})
        if request.path == "/msg" and request.method == "POST" and label != "uncertain":
            try:
                message = json.loads(row["req"]["body_text"]).get("m")
                command = message.split(";")[0].upper() if isinstance(message, str) else "?"
                body = json.loads(expected_body)
            except (ValueError, AttributeError, TypeError):
                continue
            cells[(label, command, outcome(command, expected_status, body))] += 1
    return mismatches, cells


def gaps(cells: collections.Counter, version: str) -> list[tuple[str, str]]:
    return [(command, code) for command in COMMANDS for code in EXPECTED[command]
            if cells[(version, command, code)] == 0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    rows = load()
    mismatches, cells = replay(rows)
    report = {"exchanges": len(rows),
              "eras": dict(collections.Counter(era(r["ts"]) for r in rows)),
              "mismatches": mismatches,
              "gaps": {v: gaps(cells, v) for v in ("v1", "v2")},
              "cells": {f"{v}|{c}|{o}": n for (v, c, o), n in sorted(cells.items())}}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return 1 if mismatches else 0
    print(f"{len(rows)} original exchanges; eras: {report['eras']}")
    print(f"\nREPLAY MISMATCHES: {len(mismatches)}")
    for item in mismatches[:40]:
        print(" ", item)
    for version in ("v2", "v1"):
        print(f"\n{version.upper()} outcome matrix (count per command x outcome); '.' = never observed")
        for command in COMMANDS:
            cols = "  ".join(f"{code}={cells[(version, command, code)] or '.'}" for code in EXPECTED[command])
            print(f"  {command:<9}{cols}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
