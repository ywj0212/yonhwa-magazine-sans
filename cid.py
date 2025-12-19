"""CID subfont helpers and slot resolution."""

from typing import Dict, List, Optional, Tuple

import config as cfg
from ranges import in_any

_CID_SLOT_CACHE: Dict[int, Dict[int, Dict[int, int]]] = {}


def _cid_slot_map(font, subidx: int) -> Dict[int, int]:
    """Return a unicode→encoding map for a CID subfont (cached to avoid segfaults)."""
    fid = id(font)
    submaps: Optional[Dict[int, Dict[int, int]]] = _CID_SLOT_CACHE.get(fid)
    if submaps is None:
        submaps = {}
        _CID_SLOT_CACHE[fid] = submaps
    if subidx in submaps:
        return submaps[subidx]

    mapping: Dict[int, int] = {}
    try:
        for g in font.glyphs():
            try:
                enc = int(g.encoding)
            except Exception:
                continue

            try:
                u = getattr(g, "unicode", -1)
            except Exception:
                u = -1
            try:
                u = int(u)
            except Exception:
                u = -1
            if u != -1 and u not in mapping:
                mapping[u] = enc

            try:
                alts = g.altuni
            except Exception:
                alts = None
            if alts:
                for alt in alts:
                    try:
                        au = int(alt[0])
                    except Exception:
                        continue
                    if au != -1 and au not in mapping:
                        mapping[au] = enc
    except Exception:
        pass

    submaps[subidx] = mapping
    return mapping


def find_slot(font, u: int) -> int:
    """Resolve a codepoint to an encoding slot, CID-safe."""
    try:
        cnt = int(getattr(font, "cidsubfontcnt", 0) or 0)
    except Exception:
        cnt = 0
    if cnt > 1:
        try:
            subidx = int(getattr(font, "cidsubfont", 0) or 0)
        except Exception:
            subidx = 0
        try:
            return _cid_slot_map(font, subidx).get(int(u), -1)
        except Exception:
            return -1
    try:
        return font.findEncodingSlot(u)
    except Exception:
        return -1


def get_cid_subfont_names(font) -> List[Tuple[int, str]]:
    """Return list of (index, name) for a CID font's subfonts."""
    try:
        cnt = int(getattr(font, "cidsubfontcnt", 0) or 0)
    except Exception:
        cnt = 0
    if cnt <= 0:
        return []

    try:
        saved = int(getattr(font, "cidsubfont", 0) or 0)
    except Exception:
        saved = 0

    out = []
    for i in range(cnt):
        try:
            font.cidsubfont = i
        except Exception:
            out.append((i, f"subfont#{i}"))
            continue
        n = ""
        try:
            n = font.fontname or ""
        except Exception:
            n = ""
        if not n:
            try:
                n = font.fullname or ""
            except Exception:
                n = f"subfont#{i}"
        out.append((i, n))

    try:
        font.cidsubfont = saved
    except Exception:
        pass
    return out


def build_cid_name_index(font) -> Dict[str, int]:
    """Build a name->index lookup for CID subfonts."""
    idx: Dict[str, int] = {}
    for i, n in get_cid_subfont_names(font):
        idx[n] = i
    return idx


def pick_cid_indices_by_patterns(name_index: Dict[str, int], patterns: List[str]) -> List[int]:
    """Pick subfont indices whose names contain any pattern."""
    out: List[int] = []
    for pat in patterns:
        for name, i in name_index.items():
            if pat in name:
                out.append(i)
    seen = set()
    uniq: List[int] = []
    for i in out:
        if i in seen:
            continue
        seen.add(i)
        uniq.append(i)
    return uniq


def cid_preferred_indices(name_index: Dict[str, int], u: int) -> Tuple[List[int], bool]:
    """Return (preferred_indices, only_preferred) for this codepoint category."""
    if 0xFF65 <= u <= 0xFF9F:
        return pick_cid_indices_by_patterns(name_index, ["HWidth", "HKana", "Kana", "Generic"]), False
    if in_any(u, cfg.KANA_RANGES):
        return pick_cid_indices_by_patterns(name_index, ["HKana", "Kana", "VKana", "Generic"]), False
    if in_any(u, cfg.CJK_IDEOGRAPH_RANGES):
        return pick_cid_indices_by_patterns(
            name_index,
            ["Ideographs", "ProportionalCJK"],
        ), False
    return pick_cid_indices_by_patterns(name_index, ["Generic"]), False


def resolve_src_slot_cid(src_font, u: int, name_index: Dict[str, int]) -> Optional[Tuple[Optional[int], int]]:
    """Resolve a glyph slot in a CID font by trying preferred subfonts."""
    try:
        cnt = int(getattr(src_font, "cidsubfontcnt", 0) or 0)
    except Exception:
        cnt = 0
    if cnt <= 0:
        slot = find_slot(src_font, u)
        if slot != -1:
            try:
                if getattr(src_font[slot], "isWorthOutputting", lambda: False)():
                    return (None, slot)
            except Exception:
                pass
        return None

    try:
        saved = int(getattr(src_font, "cidsubfont", 0) or 0)
    except Exception:
        saved = 0

    tried = set()
    try:
        order, only_preferred = cid_preferred_indices(name_index, u)
        order = order or []

        for subidx in order:
            tried.add(subidx)
            try:
                src_font.cidsubfont = subidx
            except Exception:
                continue
            slot = find_slot(src_font, u)
            if slot == -1:
                continue
            try:
                if src_font[slot].isWorthOutputting():
                    return (subidx, slot)
            except Exception:
                pass

        if only_preferred:
            return None

        for subidx in range(cnt):
            if subidx in tried:
                continue
            try:
                src_font.cidsubfont = subidx
            except Exception:
                continue
            slot = find_slot(src_font, u)
            if slot == -1:
                continue
            try:
                if src_font[slot].isWorthOutputting():
                    return (subidx, slot)
            except Exception:
                pass

        return None
    finally:
        try:
            src_font.cidsubfont = saved
        except Exception:
            pass
