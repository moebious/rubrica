import http.client
import json
from pathlib import Path
import socket
import threading
import time
import unittest
from unittest.mock import patch

from rubrica.engine.contract import Request, Response
from rubrica.engine.core import handle
from rubrica.engine.registry import Rule, RuleSet
from rubrica.engine.server import ReplicaServer
from rubrica.rules.current import build_rules
from rubrica.rules.v2.state import initial_state

TOKEN = "test-token"
AUTH = (("Authorization", "Bearer " + TOKEN),)

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.rules = build_rules(TOKEN)

    def test_observed_ping_uses_recorded_expectation_without_network(self):
        example = json.loads(Path("material/pruebas/ejemplos.jsonl").read_text().splitlines()[0])
        request = Request("POST", "/msg", AUTH, json.dumps(example["request"]).encode())
        with patch("socket.socket", side_effect=AssertionError("outbound socket forbidden")), patch("socket.create_connection", side_effect=AssertionError("outbound connection forbidden")):
            state, response, rule = handle(initial_state(), request, self.rules)
        self.assertEqual(response.status, example["status"])
        self.assertEqual(json.loads(response.body), example["response"])
        self.assertEqual(state, initial_state())
        self.assertEqual(rule, "v2.PING")

    def test_bad_inputs_do_not_mutate_state(self):
        for body in (b"", b'{"m":', b"null", b"[]", b'{"m":null}', b'{"m":1}', b"\xff\xfe", b"[" * 2000):
            with self.subTest(body=body[:20]):
                before = initial_state()
                after, response, rule = handle(before, Request("POST", "/msg", AUTH, body), self.rules)
                self.assertEqual(after, before)
                self.assertTrue(rule.startswith("v2.E"))

    def test_auth_variants(self):
        wrong = (("Authorization", "Bearer wrong"),)
        for headers in ((), (("Authorization", "bearer " + TOKEN),), wrong, wrong + AUTH, (("Authorization", ""),) + AUTH):
            with self.subTest(headers=headers):
                _, response, rule = handle(initial_state(), Request("GET", "/health", headers), self.rules)
                self.assertEqual(rule, "bootstrap.auth")
                self.assertEqual(response.status, 401)
        # Recorded: traces/probe_dup_auth.jsonl. Only the FIRST Authorization header counts.
        for headers in (AUTH + AUTH, AUTH + wrong, AUTH + (("Authorization", ""),)):
            with self.subTest(headers=headers):
                _, response, rule = handle(initial_state(), Request("GET", "/health", headers), self.rules)
                self.assertEqual((rule, response.status), ("bootstrap.health", 200))

    def test_order_reset_and_evaluation_failure(self):
        def fail(state, req):
            raise ValueError("rule failure")
        rules = RuleSet("test", lambda: 0, (
            Rule("later", 10, lambda s, r: True, lambda s, r: (s + 10, Response.json(200, {})), "supuesto"),
            Rule("first", 0, lambda s, r: True, lambda s, r: (s + 1, Response.json(200, {})), "supuesto"),
        ), Rule("default", 99, lambda s, r: True, fail, "supuesto"))
        self.assertEqual(handle(4, Request("POST", "/"), rules)[0], 5)
        with self.assertRaises(ValueError):
            Rule("unsupported", 0, lambda s, r: True, fail, "confirmado")
        with self.assertRaises(ValueError):
            Rule("bad\r\nheader", 0, lambda s, r: True, fail, "supuesto")
        with self.assertRaises(ValueError):
            RuleSet("test", lambda: 0, (rules.rules[0],), rules.rules[0])
        from rubrica.rules.v2.state import LedgerState
        before = LedgerState((("AC-0001", "Name", 10),), 2, 4)
        after, _, rule = handle(before, Request("POST", "/__reset", AUTH), self.rules)
        self.assertEqual(after, initial_state())
        self.assertEqual(before.next_account, 2)
        self.assertEqual(rule, "bootstrap.reset")

class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.server = ReplicaServer(("127.0.0.1", 0), build_rules(TOKEN), socket_timeout=0.15, max_body=128)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01})
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.assertFalse(self.thread.is_alive())

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        try:
            connection.request(method, path, body, headers or {"Authorization": "Bearer " + TOKEN})
            response = connection.getresponse()
            return response.status, response.read(), response.getheader("X-Rubrica-Rule")
        finally:
            connection.close()

    def test_methods_paths_and_head(self):
        self.assertEqual(self.request("GET", "/health")[0], 200)
        self.assertEqual(self.request("HEAD", "/health")[1], b"")
        for method in ("GET", "PUT", "OPTIONS", "CUSTOM"):
            self.assertEqual(self.request(method, "/missing")[2], "v1.route")
        self.assertEqual(self.request("POST", "/msg", b'{"m":"PING;64"}')[2], "v2.PING")

    def test_query_string_does_not_change_route(self):
        # Recorded: traces/edge_probes.jsonl. The original ignores the query on /health and /msg.
        self.assertEqual(self.request("GET", "/health?probe=1")[:2], (200, b'{"ok":true}'))
        status, body, rule = self.request("POST", "/msg?test=1", b'{"m":"PING;64"}')
        self.assertEqual((status, body, rule), (200, b'{"pong":true}', "v2.PING"))
        # Recorded: traces/probe_urls.jsonl. Query and fragment on /__reset still reset (200).
        self.assertEqual(self.request("POST", "/__reset?test=1")[:2], (200, b'{"ok":true}'))
        self.assertEqual(self.request("POST", "/__reset#frag")[:2], (200, b'{"ok":true}'))
        # Recorded: a trailing slash is a different path and stays unknown.
        self.assertEqual(self.request("GET", "/health/")[2], "v1.route")
        self.assertEqual(self.request("POST", "/msg/", b'{"m":"PING;64"}')[2], "v1.route")
        # Auth is still enforced when a query is present.
        self.assertEqual(self.request("GET", "/health?x=1", headers={"X-Probe": "1"})[0], 401)

    def test_size_bad_length_and_recovery(self):
        self.assertEqual(self.request("POST", "/msg", b"x" * 129)[0], 413)
        self.assertEqual(self.request("POST", "/msg", headers={"Content-Length": "-1"})[0], 400)
        self.assertEqual(self.request("POST", "/msg", headers={"Transfer-Encoding": "chunked"})[0], 400)
        self.assertEqual(self.request("GET", "/health")[0], 200)

    def test_slow_body_times_out_and_next_client_works(self):
        with socket.create_connection(self.server.server_address, timeout=2) as connection:
            connection.sendall(b"POST /msg HTTP/1.0\r\nContent-Length: 10\r\n\r\nx")
            reply = connection.recv(4096)
            self.assertIn(b"408", reply)
        self.assertEqual(self.request("GET", "/health")[0], 200)

    def test_failed_rule_preserves_state(self):
        def fail(state, req):
            raise ValueError("failure")
        self.server.rules = RuleSet("failing", initial_state, (), Rule("fail", 0, lambda s, r: True, fail, "supuesto"))
        before = self.server.state
        self.assertEqual(self.request("GET", "/")[0], 500)
        self.assertIs(self.server.state, before)

class PackagingTests(unittest.TestCase):
    def test_runtime_has_no_network_clients_or_original_hostname(self):
        forbidden = ("http.client", "urllib.request", "requests", "caja-negra-production", "create_connection(")
        for file in Path("rubrica").rglob("*.py"):
            source = file.read_text()
            for item in forbidden:
                self.assertNotIn(item, source, str(file))
        dockerfile = Path("Dockerfile").read_text()
        self.assertNotIn("COPY . .", dockerfile)
        self.assertIn("USER 65534:65534", dockerfile)

if __name__ == "__main__":
    unittest.main()
