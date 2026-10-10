"""Pure validation and ledger transitions learned from recorded experiments."""
from dataclasses import replace
import re
from rubrica.engine.contract import Response
from .protocol import Parsed, Problem
from .state import LedgerState, Operation
from .policy import Policy, V2


def amount(text: str) -> int | None:
    if re.fullmatch(r"[1-9][0-9]{0,9}", text) is None:
        return None
    return int(text)


def validate(state: LedgerState, parsed: Parsed, policy: Policy = V2) -> Problem | None:
    command, args = parsed.command, parsed.args
    if command == "HALT":
        # Observed (traces/probe_hidden_commands.jsonl): one argument of any kind, before any lookup.
        # The confirmation that would let it proceed is unknown and is NOT implemented (supuesto).
        return Problem("E520", 409)
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
        count = state.failure_count(args[0])
        if policy.lock_after_failures is not None and count >= policy.lock_after_failures:
            return Problem("E510", 423, attempts=count - policy.lock_after_failures + 1)
        # Observed (traces/probe_owner.jsonl): the ceiling does not apply when both accounts have
        # exactly the same owner name; name comparison is exact (case and spaces matter).
        same_owner = state.owner(args[0]) == state.owner(args[1])
        if value > policy.transfer_limit and not same_owner:
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


def update_failures(state: LedgerState, account_id: str, count: int) -> LedgerState:
    failures = dict(state.transfer_failures)
    if count:
        failures[account_id] = count
    else:
        failures.pop(account_id, None)
    return replace(state, transfer_failures=tuple(sorted(failures.items())))


def currency(balance: int) -> str:
    magnitude = abs(balance)
    sign = "-" if balance < 0 else ""
    return f"{sign}{magnitude // 100}.{magnitude % 100:02d}"


def execute(state: LedgerState, parsed: Parsed, policy: Policy = V2) -> tuple[LedgerState, Response]:
    problem = validate(state, parsed, policy)
    if problem:
        updated = state
        if policy.lock_after_failures is not None and problem.code in ("E506", "E507", "E510"):
            updated = update_failures(state, parsed.args[0], state.failure_count(parsed.args[0]) + 1)
        return updated, problem.response()
    command, args = parsed.command, parsed.args
    if command == "PING":
        return state, Response.json(200, {"pong": True})
    if command == "ALTA":
        key = f"AC-{state.next_account:04d}"
        return replace(state, accounts=state.accounts + ((key, args[0], 0),),
                       next_account=state.next_account + 1), Response.json(201, {"cuentaId": key})
    if command == "CONSULTA":
        balance = state.balance(args[0])
        assert balance is not None
        return state, Response.json(200, {"cuenta_id": args[0], "saldo": currency(balance) if policy.currency_balance else balance})
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
        if policy.lock_after_failures is not None:
            updated = update_failures(updated, args[0], 0)
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
