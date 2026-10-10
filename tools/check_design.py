"""Check that the design deliverables are byte-identical to the submitted ones.

The design doc and diagram were submitted from the frozen repo
github.com/moebious/frontier-lab10-rubrica (local remote `design`).
This repo carries the same files; this check fails if they ever drift.

  python3 tools/check_design.py
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = ("docs/DESIGN.pdf", "site/diagram.png", "site/diagram.svg")
REF = "design/main"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:12]


def main() -> int:
    subprocess.run(["git", "fetch", "-q", "design"], cwd=ROOT, check=False)
    failed = False
    for path in FILES:
        local = (ROOT / path).read_bytes()
        try:
            submitted = subprocess.run(
                ["git", "show", f"{REF}:{path}"], cwd=ROOT, capture_output=True, check=True
            ).stdout
        except subprocess.CalledProcessError:
            print(f"MISSING  {path} not found in {REF}")
            failed = True
            continue
        same = sha(local) == sha(submitted)
        failed |= not same
        print(f"{'OK      ' if same else 'DRIFTED '} {path}  local={sha(local)} submitted={sha(submitted)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
