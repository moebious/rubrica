"""Reproduce the offline checksum fit; no network calls or service imports."""
import itertools
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent


def points():
    examples=[json.loads(line) for line in (ROOT/"material/pruebas/ejemplos.jsonl").read_text().splitlines()]
    result=[]
    for sample in examples:
        if sample["response"].get("error") in ("E201","E202"): continue
        prefix,value=sample["request"]["m"].rsplit(";",1)
        result.append((prefix,int(value)))
    for row in map(json.loads,(ROOT/"traces/E2.jsonl").read_text().splitlines()):
        if "E202" in row["res"]["body_text"]:continue
        prefix,value=json.loads(row["req"]["body_text"])["m"].rsplit(";",1)
        result.append((prefix,int(value)))
    return list(dict.fromkeys(result))


def predict(prefix,scope,letter_start,case):
    text=prefix if scope=="message" else prefix.partition(";")[2]
    text=text.upper() if case=="upper" else text
    numeric=""
    for char in text:
        if "0"<=char<="9":numeric+=char
        elif "A"<=char<="Z":numeric+=str(ord(char)-65+letter_start)
    return 98-(int(numeric or "0")*100)%97


def main():
    observations=points()
    survivors=[]
    for scope,start,case in itertools.product(("message","arguments"),(0,1,10),("raw","upper")):
        if all(predict(prefix,scope,start,case)==value for prefix,value in observations):
            survivors.append({"scope":scope,"letter_start":start,"case":case})
    print(json.dumps({"unique_observations":len(observations),"survivors":survivors},indent=2))
    return 0 if len(survivors)==1 else 1

if __name__=="__main__":raise SystemExit(main())
