"""Startup composition: current observed v2 rules; no hot swapping."""
from .v2.rules import build_rules
from .v2.state import initial_state

__all__ = ["build_rules", "initial_state"]
