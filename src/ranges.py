"""Range helpers and JP eligibility checks."""

from typing import Iterable, Tuple

import config as cfg


def in_any(u: int, ranges: Iterable[Tuple[int, int]]) -> bool:
    """True if codepoint u falls inside any inclusive (start, end) pair."""
    for a, b in ranges:
        if a <= u <= b:
            return True
    return False


def iter_ranges(ranges: Iterable[Tuple[int, int]]):
    """Yield every codepoint from a list of inclusive ranges."""
    for a, b in ranges:
        for u in range(a, b + 1):
            yield u


def jp_allowed(u: int) -> bool:
    """True if JP replacement is allowed for this codepoint."""
    if in_any(u, cfg.EXCLUDE_PUNCT_SYMBOL_RANGES) and (not in_any(u, cfg.DIGIT_RANGES)):
        return False
    return True
