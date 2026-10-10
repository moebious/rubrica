"""Expected answers are original recordings, not generated rule outputs."""
import base64
import json
from pathlib import Path
import unittest
from rubrica.engine.contract import Request
from rubrica.engine.core import handle
from rubrica.rules.current import build_rules
from rubrica.rules.v1.state import LedgerState

class ContractEvidenceTests(unittest.TestCase):
    def test_recorded_health_reset_auth_and_routes(self):
        rules = build_rules("test-token")
        rows = [json.loads(line) for line in Path("traces/canary.jsonl").read_text().splitlines()]
        selected = [rows[index] for index in (0, 1, 22, 23, 24, 25, 26)]
        selected += [json.loads(line) for line in Path("traces/contract.jsonl").read_text().splitlines()]
        for index, row in enumerate(selected):
            headers = tuple((key, value.replace("<TOKEN>", "test-token")) for key, value in row["req"]["headers"])
            req = Request(row["req"]["method"], row["req"]["path"], headers,
                          base64.b64decode(row["req"]["body_b64"]))
            before = LedgerState((("AC-0001", "Name", 10),), 2, 3)
            with self.subTest(index=index):
                after, response, rule = handle(before, req, rules)
                self.assertEqual(response.status, row["res"]["status"])
                self.assertEqual(json.loads(response.body), json.loads(row["res"]["body_text"]))
                if response.status == 401:
                    self.assertEqual(after, before, "unauthorized request must not reset or modify state")
                elif req.path == "/__reset":
                    self.assertEqual(after.accounts, ())

if __name__ == "__main__":
    unittest.main()
