import json
from pathlib import Path
import unittest
from rubrica.rules.v2.checksum import control

class ChecksumTests(unittest.TestCase):
    def test_independent_recorded_controls(self):
        rows=[json.loads(x) for x in Path("material/pruebas/ejemplos.jsonl").read_text().splitlines()]
        for row in rows:
            prefix, supplied = row["request"]["m"].rsplit(";",1)
            if row["response"].get("error") in ("E201", "E202"):
                continue
            with self.subTest(prefix=prefix):
                self.assertEqual(control(prefix), int(supplied))
        for row in map(json.loads,Path("traces/checksum_predictions.jsonl").read_text().splitlines()):
            if row["req"]["path"] != "/msg": continue
            message=json.loads(row["req"]["body_text"])["m"]
            prefix,supplied=message.rsplit(";",1)
            self.assertNotEqual(json.loads(row["res"]["body_text"]).get("error"), "E202")
            self.assertEqual(control(prefix),int(supplied))

    def test_large_input_and_equivalent_normalization(self):
        self.assertEqual(control("CONSULTa;AC-0001"),14)
        self.assertEqual(control("CONSULTA;AC0001"),14)
        self.assertEqual(control("PING"),64)
        result=control("A" * 100000)
        self.assertTrue(2 <= result <= 98)
        with self.assertRaises(TypeError): control(None)
