import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.harness import Harness
from tools.hb import Request, Response, Target
from tools.comparator import bodies_equal

class ComparatorTests(unittest.TestCase):
    def test_exact_json_semantics(self):
        self.assertTrue(bodies_equal(b'{"a":1,"b":2}', b'{"b":2,"a":1}'))
        self.assertFalse(bodies_equal(b'{"a":true}', b'{"a":1}'))
        self.assertFalse(bodies_equal(b'[1,2]', b'[2,1]'))
        self.assertFalse(bodies_equal(b'not json ', b'not json'))
        self.assertFalse(bodies_equal(b'"1"', b'1'))
        self.assertFalse(bodies_equal(b'\xff', b'\xfe'))

class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.target = Target("original", "http://127.0.0.1", "secret-token")
        self.harness = Harness("test", "test", 2, self.root, self.target)
        self.response = Response(200, "OK", [("X-Req", "1")], b'{"ok":true}', 1)

    def tearDown(self):
        self.temp.cleanup()

    def test_gate_and_budget_fail_before_network(self):
        with patch("tools.hb.send", return_value=self.response) as send:
            with self.assertRaises(RuntimeError):
                self.harness.probe(Request("GET", "/health"), "hyp", "prediction")
            with self.harness.sequence():
                with self.assertRaises(ValueError):
                    self.harness.probe(Request("GET", "/health"), "", "prediction")
                self.harness.probe(Request("GET", "/health"), "hyp", "prediction")
                self.harness.probe(Request("GET", "/health"), "hyp", "prediction")
                with self.assertRaises(RuntimeError):
                    self.harness.probe(Request("GET", "/health"), "hyp", "prediction")
            self.assertEqual(send.call_count, 2)

    def test_failure_consumes_budget_and_is_recorded(self):
        with patch("tools.hb.send", side_effect=TimeoutError("secret-token")):
            with self.harness.sequence():
                with self.assertRaises(TimeoutError):
                    self.harness.probe(Request("POST", "/msg", [("Authorization", "Bearer secret-token")], b"\xff"), "hyp", "prediction")
        record = json.loads(self.harness.trace_path.read_text())
        self.assertEqual(record["failure"], "TimeoutError")
        self.assertNotIn("secret-token", self.harness.trace_path.read_text())
        self.assertEqual(record["req"]["body_b64"], "/w==")
        self.assertEqual(json.loads(self.harness.ledger_path.read_text())["total"], 1)

    def test_historical_usage_and_infrastructure(self):
        historical = {"target": "original"}
        (self.root / "traces" / "old.jsonl").write_text(json.dumps(historical) + "\n")
        response = Response(429, "Limit", [("X-Frontier-Infra", "rate-limit")], b"limit", 1)
        with patch("tools.hb.send", return_value=response):
            with self.harness.sequence():
                self.harness.probe(Request("GET", "/health"), "hyp", "prediction")
        record = json.loads(self.harness.trace_path.read_text())
        self.assertTrue(record["infra"])
        self.assertEqual(record["attempt"], 2)

if __name__ == "__main__":
    unittest.main()
