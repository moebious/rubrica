"""Versioned behavioral policy; v1 is retained for historical corpus replay."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Policy:
    version: str
    transfer_limit: int
    currency_balance: bool
    lock_after_failures: int | None

V1 = Policy("v1-observed", 100000, False, None)
V2 = Policy("v2-observed", 50000, True, 3)
