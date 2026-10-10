"""One coordinated snapshot for final log, spec and evidence verification."""
from pathlib import Path
import json
import sys
ROOT=Path(__file__).resolve().parent.parent
if __package__ is None or __package__ == "":sys.path.insert(0,str(ROOT))
from tools.harness import Harness
from tools.jsonlog import export
from tools.gen_spec import generate
from tools.verify_spec import verify


def main():
    with Harness("artifact_snapshot","drift",1000).sequence():
        export()
        generate()
        result=verify()
    print(json.dumps(result))
    return 0

if __name__=="__main__":raise SystemExit(main())
