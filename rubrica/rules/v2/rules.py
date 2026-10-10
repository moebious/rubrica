"""Current observed rules; contract inherited from v1, ledger initialized as v2."""
from dataclasses import replace
from rubrica.engine.contract import Request, Response
from rubrica.engine.registry import Rule, RuleSet
from rubrica.rules.v1.rules import build_rules as contract_rules
from .banking import execute, validate
from .protocol import COMMANDS, decode
from .state import LedgerState, initial_state

EVIDENCE = ("traces/checksum_predictions.jsonl", "traces/message_contract.jsonl",
            "traces/bank_boundaries.jsonl", "traces/bank_limits.jsonl", "traces/bank_edges.jsonl")


def build_rules(team_token: str) -> RuleSet[LedgerState]:
    previous = contract_rules(team_token)
    rules = []
    for rule in previous.rules:
        if rule.id == "v1.ping.observed":
            continue
        if rule.id == "bootstrap.reset":
            rule = replace(rule, evaluate=lambda state, req: (initial_state(), Response.json(200, {"ok": True})))
        rules.append(rule)
    def parsing_error(code: str):
        return lambda state, req: req.method == "POST" and req.path == "/msg" and (problem := decode(req).problem) is not None and problem.code == code
    def error_response(state, req):
        problem = decode(req).problem
        assert problem is not None
        return state, problem.response()
    for index, code in enumerate(("E100", "E102", "E103", "E104", "E201", "E202", "E301", "E302")):
        rules.append(Rule("v2." + code, 40 + index, parsing_error(code), error_response,
                          "probable", EVIDENCE, "Observed parsing/integrity/command error"))
    def domain_error(code: str):
        def matches(state, req):
            parsed = decode(req)
            if parsed.problem is not None or not parsed.command:
                return False
            problem = validate(state, parsed)
            return problem is not None and problem.code == code
        return matches
    def domain_response(state, req):
        problem = validate(state, decode(req))
        assert problem is not None
        return state, problem.response()
    for index, code in enumerate(("E303", "E304", "E401", "E402", "E506", "E507")):
        rules.append(Rule("v2." + code, 60 + index, domain_error(code), domain_response,
                          "probable", EVIDENCE, "Observed business error, no state change"))
    for index, command in enumerate(COMMANDS):
        rules.append(Rule("v2." + command, 80 + index,
                          lambda state, req, command=command: decode(req).command == command,
                          lambda state, req: execute(state, decode(req)),
                          "probable", EVIDENCE, "Observed command transition"))
    return RuleSet("v2-observed", initial_state, tuple(rules), previous.fallback,
                   frozenset({"bootstrap.reset"}))
