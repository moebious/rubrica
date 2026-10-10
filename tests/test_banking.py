"""Current-version corpus replay and state-transition regression tests."""
import base64
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from rubrica.engine.contract import Request
from rubrica.engine.core import handle
from rubrica.engine.server import route_path
from rubrica.rules.current import build_rules
from rubrica.rules.v2.state import initial_state
from tools.comparator import bodies_equal

class BankingReplayTests(unittest.TestCase):
    def setUp(self):
        self.rules = build_rules("test-token")

    def test_official_historical_sequence_all_twenty(self):
        from rubrica.rules.v2.rules import build_rules
        from rubrica.rules.v2.policy import V1
        historical_rules=build_rules("test-token", V1)
        state=initial_state()
        with patch("socket.create_connection", side_effect=AssertionError("outbound forbidden")):
            for sample in map(json.loads, Path("material/pruebas/ejemplos.jsonl").read_text().splitlines()):
                req=Request("POST", "/msg", (("Authorization", "Bearer test-token"),),json.dumps(sample["request"]).encode())
                with self.subTest(step=sample["n"]):
                    state,response,rule=handle(state,req,historical_rules)
                    self.assertEqual(response.status,sample["status"])
                    self.assertTrue(bodies_equal(response.body,json.dumps(sample["response"],ensure_ascii=False).encode()))
        self.assertEqual(state.balance("AC-0001"),210000)
        self.assertEqual(state.balance("AC-0002"),40700)
        self.assertEqual(state.next_operation,5)

    def test_recorded_banking_and_parser_corpus(self):
        from rubrica.rules.v2.rules import build_rules
        from rubrica.rules.v2.policy import V1
        historical_rules=build_rules("test-token", V1)
        names=("checksum_predictions", "bank_boundaries", "message_contract", "bank_limits", "bank_edges", "bank_final_edges")
        for name in names:
            state=initial_state()
            for index,line in enumerate(Path("traces",name+".jsonl").read_text().splitlines(),1):
                row=json.loads(line)
                if row.get("infra") or "res" not in row: continue
                headers=tuple((key,value.replace("<TOKEN>","test-token")) for key,value in row["req"]["headers"])
                req=Request(row["req"]["method"],row["req"]["path"],headers,base64.b64decode(row["req"]["body_b64"]))
                before=state
                with self.subTest(corpus=name,line=index):
                    state,response,rule=handle(state,req,historical_rules)
                    self.assertEqual(response.status,row["res"]["status"])
                    self.assertTrue(bodies_equal(response.body,base64.b64decode(row["res"]["body_b64"])),(rule,response.body,row["res"]["body_text"]))
                    if response.status>=400:self.assertEqual(state,before)

    def test_current_version_incident_corpus(self):
        names=("incident_uncovered_limits", "incident_transfer_limit", "incident_lockout",
               "incident_lock_recovery", "incident_body_boundary", "incident_confirm", "spec_confirmations", "spec_text_edges",
               "probe_owner", "probe_e506", "probe_e506b", "fuzz_seed11", "heldout_seed7")
        for name in names:
            state=initial_state()
            for index,line in enumerate(Path("traces",name+".jsonl").read_text().splitlines(),1):
                row=json.loads(line)
                if row.get("infra") or "res" not in row:continue
                headers=tuple((key,value.replace("<TOKEN>","test-token")) for key,value in row["req"]["headers"])
                req=Request(row["req"]["method"],route_path(row["req"]["path"]),headers,base64.b64decode(row["req"]["body_b64"]))
                before=state
                with self.subTest(corpus=name,line=index):
                    state,response,rule=handle(state,req,self.rules)
                    self.assertEqual(response.status,row["res"]["status"])
                    body=b"" if req.method=="HEAD" else response.body  # the HTTP adapter sends no body for HEAD
                    self.assertTrue(bodies_equal(body,base64.b64decode(row["res"]["body_b64"])),(rule,response.body,row["res"]["body_text"]))
                    if response.status>=400:
                        self.assertEqual(state.accounts,before.accounts)
                        self.assertEqual(state.operations,before.operations)
                        self.assertEqual(state.next_operation,before.next_operation)

    def test_same_owner_transfer_skips_the_ceiling(self):
        # Recorded: traces/probe_owner.jsonl and traces/fuzz_seed11.jsonl (original, v2).
        from rubrica.rules.v2.checksum import control
        def send(state, text):
            body = json.dumps({"m": text + ";" + str(control(text))}).encode()
            state, response, _ = handle(state, Request("POST", "/msg", (("Authorization", "Bearer test-token"),), body), self.rules)
            return state, json.loads(response.body)
        for names, funded, amount, expected in (
                (("Ana", "Ana"), 60000, 60000, "recieved"),
                (("Ana", "ana"), 60000, 60000, "E506"),
                (("Ana", "Ana "), 60000, 60000, "E506"),
                (("Ana", "Bea"), 60000, 60000, "E506"),
                (("Ana", "Ana"), 100, 60000, "E507")):
            state = initial_state()
            for name in names:
                state, _ = send(state, "ALTA;" + name)
            state, _ = send(state, f"DEPOSITO;AC-0001;{funded}")
            state, body = send(state, f"TRANSFER;AC-0001;AC-0002;{amount}")
            with self.subTest(names=names, funded=funded):
                self.assertEqual(body.get("error") or body.get("status"), expected)

    def test_no_mutation_and_reset_isolation(self):
        from rubrica.rules.v2.checksum import control
        def send(state,prefix):
            req=Request("POST","/msg",(("Authorization","Bearer test-token"),),json.dumps({"m":prefix+";"+str(control(prefix))}).encode())
            return handle(state,req,self.rules)
        empty=initial_state()
        left,_,_=send(empty,"ALTA;Left")
        right,_,_=send(empty,"ALTA;Right")
        deposited,_,_=send(left,"DEPOSITO;AC-0001;10")
        self.assertEqual(empty.accounts,())
        self.assertEqual(left.balance("AC-0001"),0)
        self.assertEqual(right.balance("AC-0001"),0)
        self.assertEqual(deposited.balance("AC-0001"),10)
        reset,_,_=handle(deposited,Request("POST","/__reset",(("Authorization","Bearer test-token"),)),self.rules)
        self.assertEqual(reset,empty)
        self.assertEqual(deposited.balance("AC-0001"),10)

class HTTPBankingTests(unittest.TestCase):
    def test_official_sequence_through_http_adapter(self):
        import threading
        from rubrica.engine.server import ReplicaServer
        from tools.diff import replay
        from tools.hb import Target
        server=ReplicaServer(("127.0.0.1",0),build_rules("test-token"))
        thread=threading.Thread(target=server.serve_forever,kwargs={"poll_interval":0.01})
        thread.start()
        try:
            self.assertEqual(replay(Target("replica",f"http://127.0.0.1:{server.server_port}","test-token"),Path("traces/current-examples.jsonl")),0)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

if __name__ == "__main__":
    unittest.main()
