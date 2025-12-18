"""Unicode range tables and helpers for glyph selection."""

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

# Prefer BMP for speed/stability; add extensions later if needed.
CJK_IDEOGRAPH_RANGES = [
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
]

# Keep punctuation/symbols by default during JP replacement unless excluded.
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
