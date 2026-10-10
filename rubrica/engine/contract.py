"""Transport values. Response bytes are owned by versioned service rules."""
from dataclasses import dataclass
import json

@dataclass(frozen=True)
class Request:
    method: str
    path: str
    headers: tuple[tuple[str, str], ...] = ()
    body: bytes = b""

    def header_values(self, name: str) -> tuple[str, ...]:
        return tuple(value for key, value in self.headers if key.lower() == name.lower())

@dataclass(frozen=True)
class Response:
    status: int
    body: bytes
    content_type: str = "application/json; charset=utf-8"

    def __post_init__(self) -> None:
        if type(self.status) is not int or not 100 <= self.status <= 599:
            raise ValueError("invalid HTTP status")
        if not isinstance(self.body, bytes):
            raise TypeError("response body must be bytes")

    @classmethod
    def json(cls, status: int, payload: object) -> "Response":
        return cls(status, json.dumps(payload, ensure_ascii=False, allow_nan=False,
                                     separators=(",", ":")).encode("utf-8"))
