"""Glyph copy helpers and JP cleanup."""

from typing import Dict, Optional, Tuple

import config as cfg
from cid import find_slot, resolve_src_slot_cid
from geometry import worth
from font_io import suppress_stderr
from ranges import in_any, iter_ranges, jp_allowed


def clear_anchors_if_needed(g) -> None:
    """Drop anchors on a glyph when anchor normalization is enabled."""
    if not cfg.NORMALIZE_ANCHORS:
        return
    try:
        g.anchorPoints = None
    except Exception:
        pass


def copy_from_src(src_font, dst_font, u: int, cid_name_index: Optional[Dict[str, int]] = None) -> Optional[int]:
    """Copy glyph u from src to dst; return source width if copied."""
    ref = resolve_src_slot_cid(src_font, u, cid_name_index) if cid_name_index is not None else (None, find_slot(src_font, u))
    if ref is None:
        return None
    subidx, slot = ref
    if slot is None or slot == -1:
        return None

    saved = None
    if subidx is not None:
        try:
            saved = int(getattr(src_font, "cidsubfont", 0) or 0)
            src_font.cidsubfont = int(subidx)
        except Exception:
            saved = None

    try:
        sg = src_font[int(slot)]
        if not worth(sg):
            if saved is not None:
                try:
                    src_font.cidsubfont = saved
                except Exception:
                    pass
            return None
        src_w = int(sg.width)
    except Exception:
        if saved is not None:
            try:
                src_font.cidsubfont = saved
            except Exception:
                pass
        return None

    with suppress_stderr(cfg.SILENCE_FONTFORGE_WARNINGS):
        src_font.selection.none()
        src_font.selection.select(int(slot))
        src_font.copy()

        dg = dst_font.createChar(u)
        dg.clear()

        dst_font.selection.none()
        dst_font.selection.select(int(dg.encoding))
        dst_font.paste()

    dg.unicode = u
    try:
        dg.altuni = None
    except Exception:
        pass

    clear_anchors_if_needed(dg)

    try:
        dg.unlinkRef()
    except Exception:
        pass

    if saved is not None:
        try:
            src_font.cidsubfont = saved
        except Exception:
            pass

    return src_w


def unmap_unicode_and_altuni(g) -> None:
    """Remove unicode and altuni mappings from a glyph."""
    try:
        g.unicode = -1
    except Exception:
        pass
    try:
        g.altuni = None
    except Exception:
        pass


def strip_altuni_entries(g, should_remove_u) -> None:
    """Remove altuni entries that match a predicate."""
    try:
        au = getattr(g, "altuni", None)
    except Exception:
        return
    if not au:
        return
    new_au = []
    for ent in au:
        try:
            u2 = ent if isinstance(ent, int) else ent[0]
        except Exception:
            continue
        if should_remove_u(int(u2)):
            continue
        new_au.append(ent)
    try:
        g.altuni = tuple(new_au) if new_au else None
    except Exception:
        pass


def remove_base_jp_coverage_and_clear(base_font) -> Tuple[int, int]:
    """Remove JP unicode/altuni mappings and clear JP outlines from the base."""
    removed_map = 0
    cleared = 0

    def should_remove(u: int) -> bool:
        return in_any(u, cfg.JP_TARGET_RANGES) and jp_allowed(u)

    scanned = 0
    for g in base_font.glyphs("encoding"):
        scanned += 1
        if not worth(g):
            continue
        u = getattr(g, "unicode", -1)
        if u != -1 and should_remove(int(u)):
            unmap_unicode_and_altuni(g)
            removed_map += 1
        else:
            strip_altuni_entries(g, should_remove)

        if (scanned % (cfg.PROGRESS_EVERY * 2)) == 0:
            print(f"\r[0] base JP unmap scanned={scanned} removed={removed_map}", flush=True, end="")

    for u in iter_ranges(cfg.JP_TARGET_RANGES):
        if not jp_allowed(u):
            continue
        slot = find_slot(base_font, u)
        if slot == -1:
            continue
        try:
            g = base_font[slot]
            if worth(g):
                g.clear()
                cleared += 1
        except Exception:
            pass

    print()
    return removed_map, cleared
