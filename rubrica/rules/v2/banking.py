"""Pure validation and ledger transitions learned from recorded experiments."""
from dataclasses import replace
import re
from rubrica.engine.contract import Response
from .protocol import Parsed, Problem
from .state import LedgerState, Operation


def amount(text: str) -> int | None:
    if re.fullmatch(r"[1-9][0-9]{0,9}", text) is None:
        return None
    return int(text)


def validate(state: LedgerState, parsed: Parsed) -> Problem | None:
    command, args = parsed.command, parsed.args
    if command in ("DEPOSITO", "TRANSFER"):
        value = amount(args[-1])
        if value is None:
            return Problem("E303")
        if command == "TRANSFER" and args[0] == args[1]:
            return Problem("E304")
    if command in ("CONSULTA", "DEPOSITO", "TRANSFER"):
        ids = args[:2] if command == "TRANSFER" else args[:1]
        if any(state.balance(key) is None for key in ids):
            return Problem("E401", 404)
    if command == "TRANSFER":
        value = amount(args[-1])
        assert value is not None
        if value > 100000:
            return Problem("E506", 422)
        balance = state.balance(args[0])
        assert balance is not None
        if balance < value:
            return Problem("E507", 422)
    if command == "ANULA" and not any(op.id == args[0] for op in state.operations):
        return Problem("E402", 404)
    return None


def apply_deltas(state: LedgerState, deltas: dict[str, int]) -> LedgerState:
    return replace(state, accounts=tuple((key, name, balance + deltas.get(key, 0))
                                        for key, name, balance in state.accounts))


def execute(state: LedgerState, parsed: Parsed) -> tuple[LedgerState, Response]:
    problem = validate(state, parsed)
    if problem:
        return state, problem.response()
    command, args = parsed.command, parsed.args
    if command == "PING":
        return state, Response.json(200, {"pong": True})
    if command == "ALTA":
        key = f"AC-{state.next_account:04d}"
        return replace(state, accounts=state.accounts + ((key, args[0], 0),),
                       next_account=state.next_account + 1), Response.json(201, {"cuentaId": key})
    if command == "CONSULTA":
        return state, Response.json(200, {"cuenta_id": args[0], "saldo": state.balance(args[0])})
    if command in ("DEPOSITO", "TRANSFER"):
        value = amount(args[-1])
        assert value is not None
        key = f"OP-{state.next_operation:04d}"
        if command == "DEPOSITO":
            operation = Operation(key, "deposit", args[0], None, value)
            updated = apply_deltas(state, {args[0]: value})
        else:
            operation = Operation(key, "transfer", args[0], args[1], value)
            updated = apply_deltas(state, {args[0]: -value, args[1]: value})
        return replace(updated, operations=state.operations + (operation,),
                       next_operation=state.next_operation + 1), Response.json(
                           200, {"status": "recieved", "operacionId": key})
    if command == "ANULA":
        operation = next(op for op in state.operations if op.id == args[0])
        if operation.cancelled:
            return state, Response.json(200, {"ok": False, "motivo": "ya anulada"})
        deltas = {operation.source: -operation.amount if operation.kind == "deposit" else operation.amount}
        if operation.destination is not None:
            deltas[operation.destination] = -operation.amount
        updated = apply_deltas(state, deltas)
        return replace(updated, operations=tuple(replace(op, cancelled=True) if op.id == operation.id else op
                                                for op in state.operations)), Response.json(
                                                    200, {"ok": True, "anulada": operation.id})
    raise ValueError("execute requires a validated known command")
