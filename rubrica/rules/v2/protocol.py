"""Observed message syntax and precedence, separate from HTTP and ledger effects."""
from dataclasses import dataclass
import json
import re
from rubrica.engine.contract import Request, Response
from .checksum import control

COMMANDS = ("PING", "ALTA", "CONSULTA", "DEPOSITO", "TRANSFER", "ANULA")
ARITY = {"PING": 0, "ALTA": 1, "CONSULTA": 1, "DEPOSITO": 2, "TRANSFER": 3, "ANULA": 1}
MESSAGES = {
    "E100": "json inválido", "E102": "falta m", "E103": "falta control",
    "E104": "segmento vacío", "E201": "control mal formado", "E202": "control inválido",
    "E301": "comando desconocido ", "E302": "aridad inválida", "E303": "monto inválido",
    "E304": "origen y destino iguales", "E401": "cuenta inexistente",
    "E402": "operación inexistente", "E506": "límite excedido", "E507": "saldo insuficiente",
}

@dataclass(frozen=True)
class Problem:
    code: str
    status: int = 400
    suggestion: str | None = None

    def response(self) -> Response:
        payload = {"error": self.code, "mensaje": MESSAGES[self.code]}
        if self.suggestion is not None:
            payload["sugerencia"] = self.suggestion
        return Response.json(self.status, payload)

@dataclass(frozen=True)
class Parsed:
    command: str = ""
    args: tuple[str, ...] = ()
    problem: Problem | None = None


def distance(left: str, right: str) -> int:
    # Only distances <=2 are useful; avoid quadratic work on huge command strings.
    if abs(len(left) - len(right)) > 2:
        return 3
    previous = list(range(len(right) + 1))
    for i, char in enumerate(left, 1):
        row = [i]
        for j, other in enumerate(right, 1):
            row.append(min(row[-1] + 1, previous[j] + 1, previous[j-1] + (char != other)))
        previous = row
    return previous[-1]


def decode(req: Request) -> Parsed:
    def invalid_constant(value: str):
        raise ValueError("invalid JSON constant")
    try:
        payload = json.loads(req.body.decode("utf-8"), parse_constant=invalid_constant)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return Parsed(problem=Problem("E100"))
    if type(payload) is not dict or type(payload.get("m")) is not str:
        return Parsed(problem=Problem("E102"))
    parts = payload["m"].split(";")
    if len(parts) < 2:
        return Parsed(problem=Problem("E103"))
    if any(part == "" for part in parts):
        return Parsed(problem=Problem("E104"))
    command, args, supplied = parts[0].upper(), tuple(parts[1:-1]), parts[-1]
    if command != "PING":
        if re.fullmatch(r"[0-9]{1,2}", supplied) is None:
            return Parsed(problem=Problem("E201"))
        if int(supplied) != control(";".join(parts[:-1])):
            return Parsed(problem=Problem("E202"))
    if command not in ARITY:
        nearest = min(COMMANDS, key=lambda candidate: distance(command, candidate))
        suggestion = nearest if distance(command, nearest) <= 2 else None
        return Parsed(problem=Problem("E301", suggestion=suggestion))
    if len(args) != ARITY[command]:
        return Parsed(problem=Problem("E302"))
    return Parsed(command, args)
