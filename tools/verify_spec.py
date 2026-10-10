"""Verify exported data, raw provenance, table rows and structured evidence checks.

This verifies observations and references. It is not a semantic proof of every
natural-language generalization or risk recommendation.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent.parent
if __package__ is None or __package__ == "":
    sys.path.insert(0,str(ROOT))
from tools.jsonlog import read_jsonl,validate,body_value
from tools.gen_spec import SECTIONS,matches,definitions
from tools.comparator import json_equal


def verify(root: Path = ROOT) -> dict:
    rows=read_jsonl(root/"experimentos.jsonl")
    validate(rows)
    index=json.loads((root/"experimentos.index.json").read_text())
    entries=index["entries"]
    if len(entries)!=len(rows):raise ValueError("Index/log record counts differ")
    by_id={entry["id"]:entry for entry in entries}
    if len(by_id)!=len(entries):raise ValueError("Duplicate index ID")
    cache={}
    observed_sources=set()
    for path in (root/"traces").glob("*.jsonl"):
        relative="traces/"+path.name
        cache[relative]=read_jsonl(path)
        for number,record in enumerate(cache[relative],1):
            if record.get("target")=="original":observed_sources.add(relative+":"+str(number))
    if observed_sources!={entry["source"] for entry in entries}:
        raise ValueError("Export is stale or incomplete; rerun the artifact pipeline")
    for row in rows:
        entry=by_id[row["id"]]
        path,number=entry["source"].rsplit(":",1)
        if path not in cache:cache[path]=read_jsonl(root/path)
        raw=cache[path][int(number)-1]
        digest=hashlib.sha256(json.dumps(raw,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        if digest!=entry["record_sha256"]:raise ValueError("Raw evidence changed for ID "+str(row["id"]))
        if raw.get("target")!="original":raise ValueError("Replica result included as original evidence")
        response=raw.get("res",{})
        headers={key.lower():value for key,value in response.get("headers",[])}
        expected_xreq=int(headers["x-req"]) if "x-req" in headers else None
        if row["x_req"]!=expected_xreq or row["status"]!=response.get("status"):
            raise ValueError("Exported header/status differs from original at ID "+str(row["id"]))
        if not json_equal(row["request"],body_value(raw["req"])) or not json_equal(row["response"],body_value(response) if response else None):
            raise ValueError("Exported body differs from original at ID "+str(row["id"]))
        if entry["seq"]!=row["seq"]:raise ValueError("Sequence mismatch")
    manifest=json.loads((root/"spec-evidence.json").read_text())["claims"]
    defined={claim["id"]:claim for claim in definitions()}
    seen=set()
    markdown=(root/"SPEC.md").read_text()
    headings=re.findall(r"^## (\d+)\. (.+)$",markdown,re.MULTILINE)
    if headings!=[(str(i),title) for i,title in enumerate(SECTIONS,1)]:
        raise ValueError("Required seven sections differ")
    if markdown.count("| ID | Comportamiento | Evidencia | Confianza |")!=12:
        raise ValueError("Missing required section/command tables")
    for claim in manifest:
        if claim["id"] in seen or claim["id"] not in defined:raise ValueError("Unknown or duplicate claim")
        seen.add(claim["id"])
        definition=defined[claim["id"]]
        if any(claim[key]!=definition[key] for key in ("behavior","section","confidence","queries","command")):
            raise ValueError("Claim differs from curated definition: "+claim["id"])
        if claim["confidence"] not in ("confirmado","probable","supuesto"):raise ValueError("Invalid confidence")
        if not claim["checks"] and claim["confidence"]!="supuesto":raise ValueError("Unsupported claim")
        ids=set()
        for check in claim["checks"]:
            if not check["ids"]:raise ValueError("Missing evidence")
            for id in check["ids"]:
                if type(id) is not int or id not in by_id:raise ValueError("Unknown evidence ID")
                if not matches(rows[id-1],by_id[id],check["query"]):raise ValueError("Evidence contradicts claim: "+claim["id"])
                ids.add(id)
        if sorted(ids)!=claim["evidence"]:raise ValueError("Evidence/check set mismatch")
        evidence=", ".join(map(str,claim["evidence"])) or "—"
        text=claim["behavior"].replace("|","\\|")
        expected=f'| {claim["id"]} | {text} | {evidence} | {claim["confidence"]} |'
        if expected not in markdown:raise ValueError("Rendered spec differs from manifest: "+claim["id"])
    if seen!=set(defined):raise ValueError("Missing curated claim")
    return {"records":len(rows),"claims":len(manifest),"missing_data":index["summary"]}

if __name__=="__main__":
    try:print(json.dumps(verify()))
    except (ValueError,KeyError,IndexError) as error:
        print("Verification failed:",str(error),file=sys.stderr)
        raise SystemExit(1)
