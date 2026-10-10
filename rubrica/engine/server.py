"""Bounded single-process HTTP adapter; no discovery clients or outbound calls."""
from __future__ import annotations
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import socket
from typing import Generic
from .contract import Request, Response
from .core import handle
from .registry import RuleSet
from .state import StateT

class ReplicaServer(HTTPServer, Generic[StateT]):
    def __init__(self, address: tuple[str, int], rules: RuleSet[StateT], *,
                 socket_timeout: float = 2.0, max_body: int = 65536):
        if socket_timeout <= 0 or max_body <= 0:
            raise ValueError("transport limits must be positive")
        self.rules = rules
        self.state = rules.initial_state()
        self.socket_timeout = socket_timeout
        self.max_body = max_body
        super().__init__(address, Handler)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(self.socket_timeout)
        return connection, address

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server: ReplicaServer

    def log_message(self, format: str, *args: object) -> None:
        # Avoid logging request paths, headers or credentials.
        pass

    def _reply(self, response: Response, rule_id: str) -> None:
        self.close_connection = True
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        self.send_header("X-Rubrica-Rule", rule_id)
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(response.body)

    def send_error(self, code: int, message=None, explain=None) -> None:
        self._reply(Response.json(code, {"error": "transport_error"}), "transport.parser")

    def _dispatch(self) -> None:
        try:
            lengths = self.headers.get_all("Content-Length", [])
            if self.headers.get_all("Transfer-Encoding", []) or len(lengths) > 1:
                self._reply(Response.json(400, {"error": "unsupported_framing"}), "transport.framing")
                return
            raw_length = lengths[0] if lengths else "0"
            if not raw_length.isascii() or not raw_length.isdecimal() or len(raw_length) > 10:
                self._reply(Response.json(400, {"error": "invalid_length"}), "transport.length")
                return
            size = int(raw_length)
            if size > self.server.max_body:
                self._reply(Response.json(413, {"error": "body_too_large"}), "transport.limit")
                return
            body = self.rfile.read(size)
            if len(body) != size:
                self._reply(Response.json(400, {"error": "incomplete_body"}), "transport.incomplete")
                return
            req = Request(self.command, self.path, tuple(self.headers.items()), body)
            next_state, response, rule_id = handle(self.server.state, req, self.server.rules)
            # State effects commit even if the client disconnects during delivery.
            self.server.state = next_state
            self._reply(response, rule_id)
        except (TimeoutError, socket.timeout):
            try:
                self._reply(Response.json(408, {"error": "request_timeout"}), "transport.timeout")
            except OSError:
                pass
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            self._reply(Response.json(500, {"error": "internal_error"}), "transport.internal")

    def __getattr__(self, name: str):
        if name.startswith("do_"):
            return self._dispatch
        raise AttributeError(name)

def main() -> None:
    # Only startup imports the selected service implementation.
    from rubrica.rules.current import build_rules
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8080")))
    args = parser.parse_args()
    token = os.environ.get("TEAM_TOKEN", "")
    if not token:
        parser.error("TEAM_TOKEN is required")
    with ReplicaServer((args.host, args.port), build_rules(token)) as server:
        print(f"Replica listening on port {server.server_port}; rules={server.rules.version}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
