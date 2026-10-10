"""Immutable account and operation ledger. IDs advance only on successful writes."""
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class Operation:
    id: str
    kind: Literal["deposit", "transfer"]
    source: str
    destination: str | None
    amount: int
    cancelled: bool = False

@dataclass(frozen=True)
class LedgerState:
    accounts: tuple[tuple[str, str, int], ...] = ()
    next_account: int = 1
    next_operation: int = 1
    operations: tuple[Operation, ...] = ()

    def balance(self, account_id: str) -> int | None:
        for key, name, balance in self.accounts:
            if key == account_id:
                return balance
        return None

def initial_state() -> LedgerState:
    return LedgerState()
