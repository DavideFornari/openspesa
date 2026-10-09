"""Validation of Italian tax codes."""


def is_valid_piva(code: str) -> bool:
    """True if code is an 11-digit partita IVA / numeric codice fiscale with a valid check digit."""
    if len(code) != 11 or not code.isascii() or not code.isdigit():
        return False
    digits = [int(c) for c in code]
    total = sum(digits[0:10:2])  # odd positions (1st, 3rd, ...) count as they are
    for d in digits[1:10:2]:  # even positions are doubled, minus 9 when above 9
        total += d * 2 - 9 if d > 4 else d * 2
    return (10 - total % 10) % 10 == digits[10]
