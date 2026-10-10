"""Budgeted, recorded original access with a process-wide sequence lock.

Use `with harness.sequence():` around reset plus all setup/probe steps. No cache
is implemented: live state transitions are never skipped. Legacy req/seq/sweep
tools must not run concurrently with this discovery session.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit

from tools import hb

# Budget is tied to the event day, which continues after UTC midnight.
BUDGET_ZONE = timezone(timedelta(hours=-5))

class Harness:
    def __init__(self, experiment: str, phase: str, phase_budget: int,
                 root: Path = hb.ROOT, target=None):
        if not experiment or not experiment.replace("_", "").replace("-", "").isalnum():
            raise ValueError("invalid experiment name")
        if phase_budget <= 0:
            raise ValueError("phase budget must be positive")
        self.root = root
        self.target = target or hb.Target.from_env("original")
        if self.target.name != "original" or not self.target.token:
            raise ValueError("original token required")
        if target is None and urlsplit(self.target.base_url).hostname != "caja-negra-production-c64f.up.railway.app":
            raise ValueError("original host is not allowlisted")
        self.experiment, self.phase, self.phase_budget = experiment, phase, phase_budget
        self.runtime = root / ".runtime"
        self.runtime.mkdir(mode=0o700, exist_ok=True)
        (root / "traces").mkdir(exist_ok=True)
        self.token_id = hashlib.sha256(self.target.token.encode()).hexdigest()[:16]
        self.ledger_path = self.runtime / (self.token_id + ".json")
        self.trace_path = root / "traces" / (experiment + ".jsonl")
        self.lock = None
        self.seq = ""
        self.step = 0

    @contextmanager
    def sequence(self):
        if self.lock is not None:
            raise RuntimeError("nested sequence")
        with (self.runtime / (self.token_id + ".lock")).open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            self.lock = lock
            self.seq = self.experiment + "-" + str(time.time_ns())
            self.step = 0
            try:
                yield self
            finally:
                self.lock = None
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _ledger(self):
        if self.ledger_path.exists():
            ledger = json.loads(self.ledger_path.read_text())
            if ledger["day"] != datetime.now(BUDGET_ZONE).strftime("%Y-%m-%d"):
                raise RuntimeError("daily budget ledger requires explicit reconciliation")
            return ledger
        # Reconcile historical original exchanges, including resets and failures.
        count = 0
        for path in (self.root / "traces").glob("*.jsonl"):
            for line in path.read_text().splitlines():
                record = json.loads(line)
                count += record.get("target") == "original"
        return {"day": datetime.now(BUDGET_ZONE).strftime("%Y-%m-%d"), "total": count,
                "phases": {}, "last_call": 0.0}

    def _save(self, ledger):
        temp = self.ledger_path.with_suffix(".tmp")
        temp.write_text(json.dumps(ledger))
        temp.chmod(0o600)
        os.replace(temp, self.ledger_path)

    def probe(self, req: hb.Request, hypothesis: str, prediction: str) -> hb.Response:
        if self.lock is None:
            raise RuntimeError("probe requires a coordinated sequence")
        if not hypothesis.strip() or not prediction.strip():
            raise ValueError("hypothesis and prediction required")
        ledger = self._ledger()
        spent = ledger["phases"].get(self.phase, 0)
        if ledger["total"] >= 8000 or spent >= self.phase_budget:
            raise RuntimeError("request budget exhausted")
        delay = 0.13 - (time.time() - ledger["last_call"])
        if delay > 0:
            time.sleep(delay)
        ledger["total"] += 1
        ledger["phases"][self.phase] = spent + 1
        ledger["last_call"] = time.time()
        self._save(ledger)  # Reserve before sending; failures consume budget.
        self.step += 1
        secrets = [self.target.token, os.environ.get("TEAM_TOKEN", "")]
        def redact(text):
            for secret in secrets:
                if secret:
                    text = text.replace(secret, "<TOKEN>")
            return text
        safe_request_body = req.body
        for secret in secrets:
            if secret:
                safe_request_body = safe_request_body.replace(secret.encode(), b"<TOKEN>")
        record = {"exp": self.experiment, "seq": self.seq, "step": self.step,
                  "ts": datetime.now(timezone.utc).isoformat(), "target": "original",
                  "phase": self.phase, "attempt": ledger["total"],
                  "note": hypothesis, "prediction": prediction,
                  "req": {"method": req.method, "path": redact(req.path),
                          "headers": hb._redact(req.headers, secrets),
                          **hb._body_fields(safe_request_body)}}
        try:
            response = hb.send(self.target, req, timeout=5.0)
            record["infra"] = any(k.lower() == "x-frontier-infra" and v == "rate-limit" for k, v in response.headers)
            safe_body = response.body
            for secret in secrets:
                if secret:
                    safe_body = safe_body.replace(secret.encode(), b"<TOKEN>")
            record["res"] = {"status": response.status, "reason": response.reason,
                             "headers": hb._redact(response.headers, secrets),
                             **hb._body_fields(safe_body), "elapsed_ms": response.elapsed_ms}
        except Exception as error:
            record["failure"] = type(error).__name__
            raise
        finally:
            with self.trace_path.open("a") as output:
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
                output.flush()
                os.fsync(output.fileno())
        return response
