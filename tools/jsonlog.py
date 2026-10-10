"""Export every recorded original exchange with stable IDs and honest missing data."""
from __future__ import annotations
import argparse
import base64
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ("id", "seq", "x_req", "hipotesis", "request", "status", "response")


def reject_constant(value: str):
    raise ValueError("non-JSON constant")


def read_jsonl(path: Path) -> list[dict]:
    output = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            row = json.loads(line, parse_constant=reject_constant)
        except (ValueError, RecursionError) as error:
            raise ValueError(f"Invalid JSON: {path.name}, line {number}") from error
        if not isinstance(row, dict):
            raise ValueError(f"Expected object: {path.name}, line {number}")
        output.append(row)
    return output


def body_value(container: dict):
    raw = base64.b64decode(container.get("body_b64", ""), validate=True)
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return {"_raw_body_b64": base64.b64encode(raw).decode("ascii")}


def validate(rows: list[dict]) -> None:
    for number, row in enumerate(rows, 1):
        if any(key not in row for key in REQUIRED):
            raise ValueError(f"Missing required field at line {number}")
        if type(row["id"]) is not int or row["id"] != number:
            raise ValueError(f"ID must equal line number at line {number}")
        if not isinstance(row["seq"], str) or not row["seq"]:
            raise ValueError(f"Missing sequence at line {number}")
        if not isinstance(row["hipotesis"], str) or not row["hipotesis"].strip():
            raise ValueError(f"Missing hypothesis at line {number}")
        if row["x_req"] is not None and (type(row["x_req"]) is not int or row["x_req"] < 0):
            raise ValueError(f"Invalid X-Req at line {number}")
        if row["status"] is not None and (type(row["status"]) is not int or not 100 <= row["status"] <= 599):
            raise ValueError(f"Invalid status at line {number}")


def export(root: Path = ROOT) -> tuple[list[dict], dict]:
    index_path = root / "experimentos.index.json"
    previous = json.loads(index_path.read_text()) if index_path.exists() else {"entries": []}
    entries = previous["entries"]
    if any(entry["id"] != number for number, entry in enumerate(entries, 1)):
        raise ValueError("Invalid prior ID index")
    known = {entry["source"]: entry["id"] for entry in entries}
    records = {}
    for path in sorted((root / "traces").glob("*.jsonl")):
        for number, record in enumerate(read_jsonl(path), 1):
            if record.get("target") == "original":
                records[f"traces/{path.name}:{number}"] = record
    if not set(known).issubset(records):
        raise ValueError("An indexed original trace was removed or truncated")
    def ordering(item):
        source, record = item
        return datetime.fromisoformat(record["ts"]), source
    chronological = sorted(records.items(), key=ordering)
    for source, record in chronological:
        if source not in known:
            known[source] = len(entries) + 1
            entries.append({"id": known[source], "source": source})
    sequences = {}
    reset_source = None
    for source, record in chronological:
        request, response = record["req"], record.get("res", {})
        if request["method"] == "POST" and request["path"] == "/__reset" and response.get("status") == 200:
            reset_source = source
        seq = "unanchored" if reset_source is None else "s-" + hashlib.sha256(reset_source.encode()).hexdigest()[:12]
        sequences[source] = (seq, reset_source)
    output = []
    missing_hypotheses = missing_xreq = missing_responses = unanchored = 0
    for entry in entries:
        source = entry["source"]
        record = records[source]
        digest = hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        if entry.get("record_sha256") not in (None, digest):
            raise ValueError("Previously indexed original evidence was modified: " + source)
        entry["record_sha256"] = digest
        request, response = record["req"], record.get("res", {})
        headers = {key.lower(): value for key, value in response.get("headers", [])}
        xreq = int(headers["x-req"]) if "x-req" in headers else None
        hypothesis = record.get("note", "").strip()
        recorded_hypothesis = bool(hypothesis)
        if not hypothesis:
            hypothesis = "Hipótesis no registrada en la traza original; dato histórico conservado."
            missing_hypotheses += 1
        missing_xreq += xreq is None
        missing_responses += not bool(response)
        seq, reset_key = sequences[source]
        unanchored += reset_key is None
        row = {"id": entry["id"], "seq": seq, "x_req": xreq, "hipotesis": hypothesis,
               "request": body_value(request), "status": response.get("status"),
               "response": body_value(response) if response else None}
        if not recorded_hypothesis or not response:
            row["conclusion"] = "Dato ausente conservado explícitamente; no se reconstruye una hipótesis o respuesta."
        output.append(row)
        entry.update({"seq": seq, "reset_source": reset_key, "recorded_at": record["ts"],
                      "method": request["method"], "path": request["path"],
                      "request_headers": request.get("headers", []),
                      "request_body_b64": request.get("body_b64", ""),
                      "response_body_b64": response.get("body_b64", ""),
                      "hypothesis_recorded": recorded_hypothesis,
                      "infra": bool(record.get("infra")) or "x-frontier-infra" in headers,
                      "failure": record.get("failure"), "raw_seq": record.get("seq")})
    validate(output)
    index = {"format": 1, "entries": entries,
             "summary": {"original_exchanges": len(output), "missing_hypotheses": missing_hypotheses,
                         "missing_x_req": missing_xreq, "missing_responses": missing_responses,
                         "before_first_recorded_reset": unanchored}}
    payload = "".join(json.dumps(row, ensure_ascii=True, allow_nan=False) + "\n" for row in output)
    (root / "experimentos.jsonl").write_text(payload, encoding="utf-8")
    index_path.write_text(json.dumps(index, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return output, index


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.validate:
        rows = read_jsonl(ROOT / "experimentos.jsonl")
        validate(rows)
        print(f"Validated {len(rows)} exported records.")
    else:
        from tools.harness import Harness
        with Harness("export_snapshot", "drift", 1000).sequence():
            rows, index = export()
        print(json.dumps(index["summary"]))
    return 0

if __name__ == "__main__":
    if __package__ is None or __package__ == "":
        import sys
        sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
