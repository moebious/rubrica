"""Startup composition: select an evidence-backed version, never hot-swap."""
from .v1.rules import build_rules

__all__ = ["build_rules"]
