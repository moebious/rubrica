"""Observed control: uppercase ASCII alphanumerics, A=1..Z=26, ISO-style mod 97.

Incremental reduction avoids constructing enormous integers. Punctuation and
non-ASCII letters are removed after uppercase conversion, as verified by probes.
Evidence: traces/checksum_predictions.jsonl and the official example sequence.
"""

def control(prefix: str) -> int:
    if not isinstance(prefix, str):
        raise TypeError("checksum prefix must be a string")
    remainder = 0
    for char in prefix.upper():
        if "0" <= char <= "9":
            encoded = char
        elif "A" <= char <= "Z":
            encoded = str(ord(char) - 64)
        else:
            continue
        for digit in encoded:
            remainder = (remainder * 10 + ord(digit) - 48) % 97
    return 98 - (remainder * 100) % 97
