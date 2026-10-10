"""State is supplied by a rule version, not interpreted by the engine.

Rule evaluators must return a new immutable value without modifying their input.
"""
from typing import TypeVar

StateT = TypeVar("StateT")
