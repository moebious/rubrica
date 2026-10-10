"""Bootstrap rules. Only the exact observed PING case has service evidence.

Health/reset bodies, auth failures and route errors have recorded evidence.
Unknown message semantics and transport limits remain scaffold assumptions.
"""
import hmac
import json
from rubrica.engine.contract import Request, Response
from rubrica.engine.registry import Rule, RuleSet
from .state import LedgerState, initial_state


def is_observed_ping(request: Request) -> bool:
    if request.method != "POST" or request.path != "/msg":
        return False
    try:
        payload = json.loads(request.body.decode("utf-8"), parse_constant=lambda _: None)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return False
    return type(payload) is dict and payload == {"m": "PING;64"}


def build_rules(team_token: str) -> RuleSet[LedgerState]:
    if not team_token or any(c.isspace() for c in team_token):
        raise ValueError("TEAM_TOKEN must be nonempty and contain no whitespace")
    expected = ("Bearer " + team_token).encode("utf-8")

    def unauthorized(state: LedgerState, req: Request) -> bool:
        values = req.header_values("Authorization")
        return len(values) != 1 or not hmac.compare_digest(values[0].encode("utf-8"), expected)

    def unchanged(response: Response):
        return lambda state, req: (state, response)

    rules = (
        Rule("v1.route", 0,
             lambda state, req: (req.method, req.path) not in {
                 ("GET", "/health"), ("POST", "/__reset"), ("POST", "/msg")},
             unchanged(Response.json(404, {"error": "E404", "mensaje": "ruta desconocida"})),
             "probable", ("traces/canary.jsonl:23", "traces/canary.jsonl:24", "traces/canary.jsonl:25", "traces/contract.jsonl:2", "traces/contract.jsonl:4"),
             "Observed route-before-auth responses; generalization to all other routes/methods provisional"),
        Rule("bootstrap.auth", 10, unauthorized,
             unchanged(Response.json(401, {"error": "E001", "mensaje": "no autorizado"})), "probable",
             ("traces/canary.jsonl:26", "traces/canary.jsonl:27", "traces/contract.jsonl:3", "traces/contract.jsonl:5", "traces/contract.jsonl:6"),
             "Missing/invalid/lowercase auth rejected on known routes; duplicate-header behavior unverified"),
        Rule("bootstrap.health", 20, lambda state, req: req.method == "GET" and req.path == "/health",
             unchanged(Response.json(200, {"ok": True})), "probable",
             ("traces/E1.jsonl:1", "traces/canary.jsonl:2"),
             "Authenticated health returns observed body"),
        Rule("bootstrap.reset", 30, lambda state, req: req.method == "POST" and req.path == "/__reset",
             lambda state, req: (initial_state(), Response.json(200, {"ok": True})), "probable",
             ("traces/E1.jsonl:2", "traces/canary.jsonl:1"),
             "Authenticated reset returns observed body; initial state follows brief"),
        Rule("v1.ping.observed", 40, lambda state, req: is_observed_ping(req),
             unchanged(Response.json(200, {"pong": True})), "probable",
             ("material/pruebas/ejemplos.jsonl:1",),
             "Exact observed request; no assertion about other controls or state"),
    )
    fallback = Rule("bootstrap.unmatched", 1000, lambda state, req: True,
                    unchanged(Response.json(501, {"error": "unimplemented"})), "supuesto",
                    description="Explicit bootstrap default; not an observed original response")
    return RuleSet("bootstrap-v1", initial_state, rules, fallback,
                   frozenset({"bootstrap.reset"}))
