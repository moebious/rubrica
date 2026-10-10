"""Replay official examples against a replica over HTTP; fail on any divergence."""
import argparse
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.hb import Request, Target, auth, load_env, send
from tools.comparator import bodies_equal


def replay(target: Target, corpus: Path) -> int:
    rows=[json.loads(line) for line in corpus.read_text().splitlines() if line.strip()]
    if not rows:
        raise ValueError("corpus is empty")
    headers=auth(target.token)
    reset=send(target,Request("POST","/__reset",headers),timeout=5)
    if reset.status != 200 or reset.elapsed_ms >= 5000:
        raise RuntimeError("replica reset failed")
    failures=0
    for index,row in enumerate(rows,1):
        response=send(target,Request("POST","/msg",headers+[("Content-Type","application/json")],
                                    json.dumps(row["request"],ensure_ascii=False).encode()),timeout=5)
        ok=response.status==row["status"] and bodies_equal(response.body,json.dumps(row["response"],ensure_ascii=False).encode()) and response.elapsed_ms < 5000
        failures+=not ok
        rule=next((v for k,v in response.headers if k.lower()=="x-rubrica-rule"),"unknown")
        print(f"{index}: {'PASS' if ok else 'FAIL'} status={response.status} rule={rule} latency={response.elapsed_ms}ms")
        if not ok:
            print("  body:",response.body.decode("utf-8",errors="backslashreplace"))
    print(f"{len(rows)-failures}/{len(rows)} match")
    return 1 if failures else 0


def main():
    load_env()
    parser=argparse.ArgumentParser()
    parser.add_argument("--url",default=os.environ.get("REPLICA_URL","http://127.0.0.1:8080"))
    parser.add_argument("--corpus",type=Path,default=Path("material/pruebas/ejemplos.jsonl"))
    args=parser.parse_args()
    if urlsplit(args.url).hostname == "caja-negra-production-c64f.up.railway.app":
        parser.error("diff targets the replica; use the coordinated harness for original requests")
    token=os.environ.get("TEAM_TOKEN") or os.environ.get("REPLICA_TOKEN")
    if not token:parser.error("TEAM_TOKEN or REPLICA_TOKEN required")
    try:
        return replay(Target("replica",args.url,token),args.corpus)
    except (OSError, ValueError, RuntimeError) as error:
        print("Replay failed:",type(error).__name__,file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
