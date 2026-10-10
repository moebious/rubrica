"""Initial immutable state; account semantics are not implemented yet."""
from dataclasses import dataclass

@dataclass(frozen=True)
class LedgerState:
    accounts: tuple[tuple[str, str, int], ...] = ()
    next_account: int = 1
    next_operation: int = 1

def initial_state() -> LedgerState:
    return LedgerState()
