"""Validated, ordered rule records with evidence provenance."""
from dataclasses import dataclass
from typing import Callable, Generic, Literal
from .contract import Request, Response
from .state import StateT

Confidence = Literal["confirmado", "probable", "supuesto"]

@dataclass(frozen=True)
class Rule(Generic[StateT]):
    id: str
    precedence: int
    match: Callable[[StateT, Request], bool]
    evaluate: Callable[[StateT, Request], tuple[StateT, Response]]
    confidence: Confidence
    evidence: tuple[str, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        if not self.id or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for c in self.id):
            raise ValueError("rule ID must be a safe nonempty header value")
        if self.confidence not in ("confirmado", "probable", "supuesto"):
            raise ValueError("invalid confidence")
        if self.confidence != "supuesto" and not self.evidence:
            raise ValueError("supported rules require evidence")
        if type(self.precedence) is not int:
            raise TypeError("precedence must be an integer")

@dataclass(frozen=True)
class RuleSet(Generic[StateT]):
    version: str
    initial_state: Callable[[], StateT]
    rules: tuple[Rule[StateT], ...]
    fallback: Rule[StateT]
    reset_rule_ids: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        all_rules = (*self.rules, self.fallback)
        ids = [rule.id for rule in all_rules]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate rule ID")
        if not self.reset_rule_ids.issubset(ids):
            raise ValueError("unknown reset rule ID")
        object.__setattr__(self, "rules", tuple(sorted(self.rules, key=lambda r: r.precedence)))
