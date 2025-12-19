"""Unicode range tables and helpers for glyph selection.

Notes:
- All ranges are inclusive.
- Code is grouped by script/usage so callers can include what they need.
- Comments explicitly spell out what each block covers to avoid guesswork.
"""

import unicodedata

DIGIT_RANGES = [
    (0x0030, 0x0039),
    (0xFF10, 0xFF19),
    (0x2070, 0x2079),
    (0x2080, 0x2089),
]

HANGUL_MAIN_RANGES = [
    (0xAC00, 0xD7A3),
    (0x3130, 0x318F),
    (0x1100, 0x11FF),
    (0xA960, 0xA97F),
    (0xD7B0, 0xD7FF),
]

ENCLOSED_RANGES = [
    (0x2460, 0x24FF),
    (0x3200, 0x32FF),
    (0x2776, 0x2793),
    (0x1F100, 0x1F1FF),
    (0x1F200, 0x1F2FF),
]

KANA_RANGES = [
    (0x3040, 0x309F),
    (0x30A0, 0x30FF),
    (0x31F0, 0x31FF),
    (0xFF65, 0xFF9F),
    (0x1B000, 0x1B0FF),
    (0x1B100, 0x1B12F),
    (0x1B130, 0x1B16F),
]

# CJK unified ideographs (keep as many as FontForge and source fonts support).
# Includes BMP, compatibility, and extensions B–I plus compatibility supplement.
CJK_IDEOGRAPH_RANGES = [
    (0x3400, 0x4DBF),   # Extension A (BMP)
    (0x4E00, 0x9FFF),   # Unified ideographs (BMP)
    (0xF900, 0xFAFF),   # Compatibility ideographs (BMP)
    (0x2F800, 0x2FA1F), # Compatibility Ideographs Supplement
    (0x20000, 0x2A6DF), # Extension B
    (0x2A700, 0x2B73F), # Extension C
    (0x2B740, 0x2B81F), # Extension D
    (0x2B820, 0x2CEAF), # Extension E
    (0x2CEB0, 0x2EBEF), # Extension F
    (0x30000, 0x3134F), # Extension G
    (0x31350, 0x323AF), # Extension H
    (0x2EBF0, 0x2EE5F), # Extension I
]

# Punctuation/symbol ranges that can be excluded during JP replacement.
EXCLUDE_PUNCT_SYMBOL_RANGES = [
    (0x2000, 0x206F),
    (0x3000, 0x303F),
    (0xFE10, 0xFE1F),
    (0xFE30, 0xFE4F),
    (0xFF00, 0xFF0F),
    (0xFF1A, 0xFF60),
]

JP_TARGET_RANGES = KANA_RANGES + CJK_IDEOGRAPH_RANGES


def build_jp_extra_set(jp_extra_glyphs_exact: str) -> set[int]:
    """Build a whitelist set for JP extra glyphs from the exact string."""
    exact = {ord(ch) for ch in jp_extra_glyphs_exact if not ch.isspace()}

    # Expand to related CJK compatibility/enclosed symbols for convenience.
    similar = set()

    for u in range(0x3300, 0x3400):
        try:
            unicodedata.name(chr(u))
        except Exception:
            continue
        similar.add(u)

    for u in range(0x3200, 0x3300):
        try:
            unicodedata.name(chr(u))
        except Exception:
            continue
        similar.add(u)

    return exact | similar
