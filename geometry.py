"""Geometry helpers: worth checks, scaling, and transforms."""

import psMat  # type: ignore

from cid import find_slot


def has_glyph(font, u: int) -> bool:
    """True if the font has a drawable glyph for codepoint u."""
    slot = find_slot(font, u)
    if slot == -1:
        return False
    try:
        return worth(font[slot])
    except Exception:
        return False


def worth(g) -> bool:
    """True if the glyph exists and is drawable."""
    try:
        return g is not None and g.isWorthOutputting()
    except Exception:
        return False


def bake(dst_font, u: int, sx_total: float, sy_total: float, dy_units: float, width_final: float) -> None:
    """Apply transforms and width to a single glyph in the destination."""
    slot = find_slot(dst_font, u)
    if slot == -1:
        return
    try:
        g = dst_font[slot]
    except Exception:
        return
    if not worth(g):
        return
    if sx_total != 1.0 or sy_total != 1.0:
        g.transform(psMat.scale(sx_total, sy_total))
    if dy_units:
        g.transform(psMat.translate(0, dy_units))
    g.width = int(round(width_final))


def transform_entire_font(font, sx: float, sy: float) -> None:
    """Scale the entire font, preserving positioning tables where possible."""
    if sx == 1.0 and sy == 1.0:
        return
    font.selection.all()
    try:
        font.transform(psMat.scale(sx, sy), ("round", "simplePos", "kernClasses"))
    except Exception:
        font.transform(psMat.scale(sx, sy))
    font.selection.none()
