"""Pure first-match decision procedure. Exceptions propagate to the I/O boundary."""
from .contract import Request, Response
from .registry import RuleSet
from .state import StateT

def handle(state: StateT, request: Request, rules: RuleSet[StateT]) -> tuple[StateT, Response, str]:
    for rule in rules.rules:
        if rule.match(state, request):
            next_state, response = rule.evaluate(state, request)
            return next_state, response, rule.id
    next_state, response = rules.fallback.evaluate(state, request)
    return next_state, response, rules.fallback.id
