"""Validation of Italian tax codes."""

# Check-character weights for the 16-character codice fiscale of natural persons
# (DM 23/12/1976). Odd positions use this table; even positions use 0-9 and A=0 ... Z=25.
_CF_ODD = dict(
    zip(
        "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        [1, 0, 5, 7, 9, 13, 15, 17, 19, 21]  # 0-9
        + [1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 2, 4, 18]  # A-M
        + [20, 11, 3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23],  # N-Z
        strict=True,
    )
)


def is_valid_cf(code: str) -> bool:
    """True if code is a 16-character personal codice fiscale with a valid check character."""
    if len(code) != 16 or not code.isascii() or not code.isalnum() or code != code.upper():
        return False
    total = sum(_CF_ODD[c] for c in code[0:15:2])
    total += sum(int(c) if c.isdigit() else ord(c) - 65 for c in code[1:15:2])
    return chr(65 + total % 26) == code[15]


def is_valid_piva(code: str) -> bool:
    """True if code is an 11-digit partita IVA / numeric codice fiscale with a valid check digit."""
    if len(code) != 11 or not code.isascii() or not code.isdigit():
        return False
    digits = [int(c) for c in code]
    total = sum(digits[0:10:2])  # odd positions (1st, 3rd, ...) count as they are
    for d in digits[1:10:2]:  # even positions are doubled, minus 9 when above 9
        total += d * 2 - 9 if d > 4 else d * 2
    return (10 - total % 10) % 10 == digits[10]
