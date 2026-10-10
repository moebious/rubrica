"""Reset-based, budgeted drift monitor. Baseline is data, not replica predictions."""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import time

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.harness import Harness
from tools.hb import Request, auth
from tools.comparator import bodies_equal

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / "traces" / "canary-baseline.json"
REPORTS = ROOT / "traces" / "canary-results.jsonl"


def cases(token):
    headers = auth(token)
    out = [(Request("POST", "/__reset", headers), "Reset creates reproducible initial state", "200 {ok:true}"),
           (Request("GET", "/health", headers), "Authenticated health is ready", "200 {ok:true}")]
    for line in (ROOT / "material/pruebas/ejemplos.jsonl").read_text().splitlines():
        sample = json.loads(line)
        out.append((Request("POST", "/msg", headers + [("Content-Type", "application/json")],
                            json.dumps(sample["request"], ensure_ascii=False).encode()),
                    "Official sequence still has its recorded behavior at step " + str(sample["n"]),
                    str(sample["status"]) + " " + json.dumps(sample["response"], ensure_ascii=False)))
    for method, path, headers in (("GET", "/rubrica-missing", auth(token)),
                                 ("GET", "/", auth(token)),
                                 ("GET", "/msg", auth(token)),
                                 ("GET", "/health", []),
                                 ("POST", "/__reset", auth("invalid-token"))):
        out.append((Request(method, path, headers), "Characterize route/auth behavior: " + method + " " + path,
                    "404 for absent route, 405 for method mismatch, 401 for missing/invalid auth (unverified)"))
    return out


def run_cycle(harness, baseline=None):
    results = []
    with harness.sequence():
        for req, hypothesis, prediction in cases(harness.target.token):
            res = harness.probe(req, hypothesis, prediction)
            if any(k.lower() == "x-frontier-infra" for k, v in res.headers):
                raise RuntimeError("infrastructure response; baseline is invalid")
            results.append({"method": req.method, "path": req.path,
                            "status": res.status, "body_hex": res.body.hex()})
            if len(results) == 1 and res.status != 200:
                raise RuntimeError("reset failed; sequence aborted")
    changed = []
    if baseline is not None:
        if len(baseline["cases"]) != len(results):
            raise RuntimeError("canary case set changed; recapture baseline explicitly")
        for step, (old, new) in enumerate(zip(baseline["cases"], results), 1):
            if (old["method"], old["path"]) != (new["method"], new["path"]):
                raise RuntimeError("canary request order changed")
            if old["status"] != new["status"] or not bodies_equal(bytes.fromhex(old["body_hex"]), bytes.fromhex(new["body_hex"])):
                changed.append(step)
    report = {"ts": datetime.now(timezone.utc).isoformat(), "seq": harness.seq,
              "changed_steps": changed, "cases": len(results)}
    with REPORTS.open("a") as output:
        output.write(json.dumps(report) + "\n")
    print(json.dumps(report), flush=True)
    return results, changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=600)
    parser.add_argument("--budget", type=int, default=820)
    args = parser.parse_args()
    if args.interval <= 0:
        parser.error("interval must be positive")
    harness = Harness("canary", "canary", args.budget)
    if args.capture:
        if BASELINE.exists():
            parser.error("baseline already exists; preserve it before recapture")
        data, _ = run_cycle(harness)
        BASELINE.write_text(json.dumps({"captured": datetime.now(timezone.utc).isoformat(),
                                       "version": "observed-baseline", "cases": data}, indent=2) + "\n")
        print("Baseline captured.", flush=True)
    if args.watch:
        baseline = json.loads(BASELINE.read_text())
        captured = datetime.fromisoformat(baseline["captured"])
        cutoff = captured.replace(hour=1, minute=0, second=0, microsecond=0) + timedelta(days=1)
        while datetime.now(timezone.utc) < cutoff:
            try:
                _, changed = run_cycle(harness, baseline)
                if changed:
                    print("DRIFT DETECTED; see recorded differing steps. Confirmation required.", flush=True)
                    break
            except Exception as error:
                print("Canary stopped: " + type(error).__name__, flush=True)
                raise
            time.sleep(args.interval)
    elif not args.capture:
        run_cycle(harness, json.loads(BASELINE.read_text()))

if __name__ == "__main__":
    main()
