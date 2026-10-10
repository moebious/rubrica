"""Official status/body semantics, without Python's bool == int shortcut."""
import json


def json_equal(left, right):
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(json_equal(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(json_equal(a, b) for a, b in zip(left, right))
    return left == right


def bodies_equal(left: bytes, right: bytes) -> bool:
    def reject(value):
        raise ValueError("non-JSON constant")
    try:
        a = json.loads(left.decode("utf-8"), parse_constant=reject)
        b = json.loads(right.decode("utf-8"), parse_constant=reject)
    except (UnicodeDecodeError, ValueError, RecursionError):
        return left == right
    return json_equal(a, b)
