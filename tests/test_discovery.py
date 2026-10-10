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

    def test_budget_day_does_not_roll_over_at_utc_midnight(self):
        from datetime import datetime, timezone
        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                current=cls(2026,10,11,0,30,tzinfo=timezone.utc)
                return current.astimezone(tz) if tz is not None else current
        with patch("tools.harness.datetime",FrozenDateTime):
            self.assertEqual(self.harness._ledger()["day"],"2026-10-10")

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


class CanaryPredictionTests(unittest.TestCase):
    def test_predictions_follow_pinned_current_baseline(self):
        from contextlib import nullcontext
        from types import SimpleNamespace
        from tools.canary import run_cycle
        with tempfile.TemporaryDirectory() as directory:
            responses=[b'{"ok":true}',b'{"saldo":"0.00"}']
            planned=[(Request("POST","/__reset"),"old reset","200 ok"),
                     (Request("POST","/msg"),"old balance","200 {saldo:0}")]
            predictions=[]
            def probe(req,hypothesis,prediction):
                predictions.append(prediction)
                return Response(200,"OK",[],responses[len(predictions)-1],1)
            harness=SimpleNamespace(target=SimpleNamespace(token="test-token"),seq="test",sequence=lambda:nullcontext(),probe=probe)
            baseline={"version":"v2-observed","cases":[{"method":item[0].method,"path":item[0].path,"status":200,"body_hex":body.hex()} for item,body in zip(planned,responses)]}
            with patch("tools.canary.cases",return_value=planned),patch("tools.canary.REPORTS",Path(directory)/"report.jsonl"):
                _,changed=run_cycle(harness,baseline)
            self.assertEqual(changed,[])
            self.assertIn('"saldo":"0.00"',predictions[1])

    def test_invalid_baseline_fails_before_original_access(self):
        from types import SimpleNamespace
        from tools.canary import run_cycle
        from unittest.mock import Mock
        probe=Mock()
        harness=SimpleNamespace(target=SimpleNamespace(token="test-token"),probe=probe)
        with patch("tools.canary.cases",return_value=[(Request("GET","/health"),"hyp","200")]):
            with self.assertRaises(RuntimeError):run_cycle(harness,{"cases":[]})
        probe.assert_not_called()

if __name__ == "__main__":
    unittest.main()
