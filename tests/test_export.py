import base64
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from tools.jsonlog import export,read_jsonl,validate
from tools.verify_spec import verify


def record(timestamp,body=b'{"m":"PING;64"}'):
    return {"target":"original","ts":timestamp,"seq":1,"note":"PING is deterministic",
            "req":{"method":"POST","path":"/msg","headers":[],"body_b64":base64.b64encode(body).decode()},
            "res":{"status":200,"headers":[["X-Req","1"]],"body_b64":base64.b64encode(b'{"pong":true}').decode()}}

class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        (self.root/"traces").mkdir()
    def tearDown(self):self.temp.cleanup()
    def write(self,name,rows):
        (self.root/"traces"/name).write_text("".join(json.dumps(row)+"\n" for row in rows))

    def test_ids_stay_stable_when_older_evidence_is_imported(self):
        self.write("late.jsonl",[record("2026-10-10T21:00:00+00:00")])
        first,index=export(self.root)
        self.write("early.jsonl",[record("2026-10-10T20:00:00+00:00")])
        second,index=export(self.root)
        self.assertEqual(index["entries"][0]["source"],"traces/late.jsonl:1")
        self.assertEqual(second[0]["id"],first[0]["id"])
        self.assertEqual(second[1]["id"],2)

    def test_missing_data_is_explicit_and_replica_is_excluded(self):
        original=record("2026-10-10T21:00:00+00:00",b"\xff")
        original["note"]=""
        original["res"]["headers"]=[]
        replica=record("2026-10-10T21:00:01+00:00");replica["target"]="replica"
        self.write("sample.jsonl",[original,replica])
        rows,index=export(self.root)
        self.assertEqual(len(rows),1)
        self.assertIsNone(rows[0]["x_req"])
        self.assertFalse(index["entries"][0]["hypothesis_recorded"])
        self.assertEqual(rows[0]["request"],{"_raw_body_b64":"/w=="})
        self.assertIn("no registrada",rows[0]["hipotesis"])

    def test_indexed_evidence_cannot_be_modified(self):
        row=record("2026-10-10T21:00:00+00:00")
        self.write("sample.jsonl",[row]);export(self.root)
        row["res"]["status"]=201;self.write("sample.jsonl",[row])
        with self.assertRaisesRegex(ValueError,"modified"):export(self.root)

    def test_escaped_surrogate_can_be_exported_losslessly(self):
        self.write("unicode.jsonl",[record("2026-10-10T21:00:00+00:00",b'{"m":"\\ud800"}')])
        rows,index=export(self.root)
        self.assertEqual(read_jsonl(self.root/"experimentos.jsonl")[0]["request"]["m"],"\ud800")

    def test_validation_rejects_bad_ids_and_boolean_numbers(self):
        self.write("sample.jsonl",[record("2026-10-10T21:00:00+00:00")])
        rows,index=export(self.root)
        for field,value in (("id",2),("x_req",True),("status",False),("hipotesis","")):
            bad=dict(rows[0]);bad[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate([bad])

    def test_malformed_line_names_location_without_echoing_data(self):
        path=self.root/"bad.jsonl";path.write_text('{"ok":true}\nSECRET bad json\n')
        with self.assertRaises(ValueError) as context:read_jsonl(path)
        self.assertIn("line 2",str(context.exception))
        self.assertNotIn("SECRET",str(context.exception))

class SpecVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        for name in ("experimentos.jsonl","experimentos.index.json","SPEC.md","spec-evidence.json"):
            shutil.copyfile(name,self.root/name)
        # Copy exactly the indexed evidence snapshot, not newer live canary rows.
        index=json.loads((self.root/"experimentos.index.json").read_text())
        limits={}
        for entry in index["entries"]:
            source,number=entry["source"].rsplit(":",1)
            limits[source]=max(limits.get(source,0),int(number))
        (self.root/"traces").mkdir()
        for source,limit in limits.items():
            lines=Path(source).read_text().splitlines()
            (self.root/source).write_text("\n".join(lines[:limit])+"\n")
    def tearDown(self):self.temp.cleanup()
    def test_full_artifacts_verify(self):
        self.assertGreater(verify(self.root)["claims"],30)
    def test_unexported_original_exchange_fails(self):
        path=self.root/"traces"/"new_original.jsonl"
        path.write_text(json.dumps(record("2026-10-10T22:00:00+00:00"))+"\n")
        with self.assertRaisesRegex(ValueError,"stale or incomplete"):verify(self.root)
    def test_missing_evidence_id_fails(self):
        path=self.root/"spec-evidence.json";data=json.loads(path.read_text())
        data["claims"][0]["checks"][0]["ids"]=[999999]
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,"Unknown evidence"):verify(self.root)
    def test_false_rendered_claim_fails(self):
        path=self.root/"SPEC.md";path.write_text(path.read_text().replace("GET /health autenticado responde 200","GET /health autenticado responde 201"))
        with self.assertRaisesRegex(ValueError,"Rendered spec"):verify(self.root)
    def test_modified_response_fails(self):
        path=self.root/"experimentos.jsonl";rows=read_jsonl(path)
        rows[0]["response"]={"fabricated":True}
        path.write_text("".join(json.dumps(row)+"\n" for row in rows))
        with self.assertRaisesRegex(ValueError,"body differs"):verify(self.root)
