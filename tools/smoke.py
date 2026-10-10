"""Public replica contract gate. Never invokes platform hidden evaluations."""
import argparse
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit
if __package__ is None or __package__ == "":
    sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from tools.hb import Request, Target, auth, load_env, send
from tools.diff import replay
from tools.comparator import bodies_equal


def smoke(target: Target) -> int:
    failures=0
    def check(label,request,status,body):
        nonlocal failures
        response=send(target,request,timeout=5)
        ok=response.status==status and bodies_equal(response.body,json.dumps(body,ensure_ascii=False).encode()) and response.elapsed_ms < 5000
        print(f"{label}: {'PASS' if ok else 'FAIL'} status={response.status} latency={response.elapsed_ms}ms")
        failures+=not ok
    check("health",Request("GET","/health",auth(target.token)),200,{"ok":True})
    corpus=Path("traces/current-examples.jsonl")
    failures+=replay(target,corpus)
    rows=[json.loads(line) for line in corpus.read_text().splitlines()]
    balance_probe=next(row for row in reversed(rows) if row["request"]["m"].startswith("CONSULTA;AC-0002;"))
    for label,headers in (("missing auth",[]),("invalid auth",auth("invalid-token")),("lowercase scheme",auth(target.token,"bearer"))):
        check(label,Request("GET","/health",headers),401,{"error":"E001","mensaje":"no autorizado"})
    check("unknown route",Request("GET","/rubrica-missing",auth(target.token)),404,{"error":"E404","mensaje":"ruta desconocida"})
    check("unknown route without auth",Request("GET","/rubrica-missing"),404,{"error":"E404","mensaje":"ruta desconocida"})
    check("invalid reset token",Request("POST","/__reset",auth("invalid-token")),401,{"error":"E001","mensaje":"no autorizado"})
    check("invalid reset preserves state",Request("POST","/msg",auth(target.token)+[("Content-Type","application/json")],json.dumps(balance_probe["request"]).encode()),200,balance_probe["response"])
    check("reset",Request("POST","/__reset",auth(target.token)),200,{"ok":True})
    check("reset clears state",Request("POST","/msg",auth(target.token)+[("Content-Type","application/json")],b'{"m":"CONSULTA;AC-0002;11"}'),404,{"error":"E401","mensaje":"cuenta inexistente"})
    print("Smoke gate:","PASS" if not failures else "FAIL")
    return 1 if failures else 0


def main():
    load_env()
    parser=argparse.ArgumentParser()
    parser.add_argument("--url",required=True)
    args=parser.parse_args()
    if urlsplit(args.url).hostname=="caja-negra-production-c64f.up.railway.app":
        parser.error("smoke checks target the replica only")
    token=os.environ.get("TEAM_TOKEN")
    if not token:parser.error("TEAM_TOKEN required")
    try:return smoke(Target("replica",args.url,token))
    except (OSError,ValueError,RuntimeError) as error:
        print("Smoke failed:",type(error).__name__,file=sys.stderr)
        return 1

if __name__=="__main__":raise SystemExit(main())
