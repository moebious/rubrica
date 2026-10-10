"""Observed control: uppercase ASCII alphanumerics, A=1..Z=26, ISO-style mod 97.

Incremental reduction avoids constructing enormous integers. Punctuation and
non-ASCII letters are ignored; only ASCII letters are uppercased, as verified by probes.
Evidence: traces/checksum_predictions.jsonl and the official example sequence.
"""

def control(prefix: str) -> int:
    if not isinstance(prefix, str):
        raise TypeError("checksum prefix must be a string")
    remainder = 0
    # Only ASCII letters are uppercased: str.upper() would fold U+00DF to "SS", U+0131 to "I", etc.,
    # but the original ignores those characters (traces/probe_unicode_upper.jsonl).
    for char in prefix:
        if "a" <= char <= "z":
            char = chr(ord(char) - 32)
        if "0" <= char <= "9":
            encoded = char
        elif "A" <= char <= "Z":
            encoded = str(ord(char) - 64)
        else:
            continue
        for digit in encoded:
            remainder = (remainder * 10 + ord(digit) - 48) % 97
    return 98 - (remainder * 100) % 97
