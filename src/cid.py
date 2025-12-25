"""CID subfont helpers and encoding slot resolution."""

from typing import Dict, List, Optional, Tuple

import config as cfg
from ranges import in_any
from fontTools.ttLib import TTFont
from map_log import log_issue

_CID_SLOT_CACHE: Dict[int, Dict[int, Dict[int, int]]] = {}
_CID_PRESENT_CACHE: Dict[int, Dict[int, set[int]]] = {}


def _cid_slot_map(font, subidx: int) -> Dict[int, int]:
    """Build a unicode→encoding map for a CID subfont (cached per font/subfont)."""
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


def _cid_from_glyph_name(name: str) -> Optional[int]:
    """Extract CID value from a glyph name like cid12345 or CID+12345."""
    if not name:
        return None
    if name.startswith("cid") and name[3:].isdigit():
        return int(name[3:])
    if name.startswith("CID+") and name[4:].isdigit():
        return int(name[4:])
    if name.startswith("Identity.") and name[9:].isdigit():
        return int(name[9:])
    return None


def _cid_present_set(font, subidx: int) -> set[int]:
    """Return encoding slots present in the current CID subfont (cached)."""
    fid = id(font)
    submaps = _CID_PRESENT_CACHE.get(fid)
    if submaps is None:
        submaps = {}
        _CID_PRESENT_CACHE[fid] = submaps
    if subidx in submaps:
        return submaps[subidx]

    present: set[int] = set()
    try:
        for g in font.glyphs():
            try:
                present.add(int(g.encoding))
            except Exception:
                continue
    except Exception:
        pass
    submaps[subidx] = present
    return present


def build_cid_unicode_map(tt_path: str) -> Dict[int, int]:
    """Build a unicode→CID map using fontTools cmap data (CID glyphs often lack unicode)."""
    try:
        tt = TTFont(tt_path)
    except Exception:
        return {}

    cmap = tt.getBestCmap() or {}
    out: Dict[int, int] = {}
    for uni, gname in cmap.items():
        cid = _cid_from_glyph_name(gname)
        if cid is not None:
            out[int(uni)] = int(cid)
        else:
            log_issue("cid_name_unparsed", int(uni), detail=f"name={gname}")

    try:
        tt.close()
    except Exception:
        pass
    return out


def build_unicode_name_map(tt_path: str) -> Dict[int, str]:
    """Build a unicode→glyph-name map from fontTools cmap."""
    try:
        tt = TTFont(tt_path)
    except Exception:
        return {}
    cmap = tt.getBestCmap() or {}
    out = {int(uni): str(name) for uni, name in cmap.items()}
    try:
        tt.close()
    except Exception:
        pass
    return out


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
    """Return (index, name) entries for a CID font's subfonts."""
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
    """Build a name→index lookup for CID subfonts."""
    idx: Dict[str, int] = {}
    for i, n in get_cid_subfont_names(font):
        idx[n] = i
    return idx


def pick_cid_indices_by_patterns(name_index: Dict[str, int], patterns: List[str]) -> List[int]:
    """Return subfont indices whose names contain any pattern."""
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
    """Return preferred subfont indices for a given codepoint."""
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


def resolve_src_slot_cid(
    src_font,
    u: int,
    name_index: Dict[str, int],
    cid_unicode_map: Optional[Dict[int, int]] = None,
    unicode_name_map: Optional[Dict[int, str]] = None,
) -> Optional[Tuple[Optional[int], int]]:
    """Resolve a glyph slot in a CID font by trying preferred subfonts."""
    try:
        cnt = int(getattr(src_font, "cidsubfontcnt", 0) or 0)
    except Exception:
        cnt = 0
    if cnt <= 0:
        slot = None
        if cid_unicode_map is not None:
            slot = cid_unicode_map.get(u)
        if slot is None and unicode_name_map:
            gname = unicode_name_map.get(u)
            if gname:
                slot = _cid_from_glyph_name(gname)
                if slot is None:
                    try:
                        slot = int(src_font[gname].encoding)
                    except Exception:
                        slot = None
        if slot is None and cid_unicode_map is None:
            slot = find_slot(src_font, u)
        if slot is None:
            if cid_unicode_map is not None:
                log_issue("cid_map_missing", u)
            return None
        if slot != -1:
            try:
                if getattr(src_font[slot], "isWorthOutputting", lambda: False)():
                    return (None, slot)
            except Exception:
                pass
        if cid_unicode_map is not None:
            log_issue("cid_map_missing", u)
        return None

    try:
        saved = int(getattr(src_font, "cidsubfont", 0) or 0)
    except Exception:
        saved = 0

    tried = set()
    missing_subfont = False
    missing_slot: Optional[int] = None
    try:
        order, only_preferred = cid_preferred_indices(name_index, u)
        order = order or []

        for subidx in order:
            tried.add(subidx)
            try:
                src_font.cidsubfont = subidx
            except Exception:
                continue
            slot = None
            if cid_unicode_map is not None:
                slot = cid_unicode_map.get(u)
            if slot is None and unicode_name_map:
                gname = unicode_name_map.get(u)
                if gname:
                    slot = _cid_from_glyph_name(gname)
                    if slot is None:
                        try:
                            slot = int(src_font[gname].encoding)
                        except Exception:
                            slot = None
            if slot is None and cid_unicode_map is None:
                slot = find_slot(src_font, u)
            if slot == -1:
                continue
            if cid_unicode_map is not None and slot not in _cid_present_set(src_font, subidx):
                missing_subfont = True
                missing_slot = slot
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
            slot = None
            if cid_unicode_map is not None:
                slot = cid_unicode_map.get(u)
            if slot is None and unicode_name_map:
                gname = unicode_name_map.get(u)
                if gname:
                    slot = _cid_from_glyph_name(gname)
                    if slot is None:
                        try:
                            slot = int(src_font[gname].encoding)
                        except Exception:
                            slot = None
            if slot is None and cid_unicode_map is None:
                slot = find_slot(src_font, u)
            if slot == -1:
                continue
            if cid_unicode_map is not None and slot not in _cid_present_set(src_font, subidx):
                missing_subfont = True
                missing_slot = slot
                continue
            try:
                if src_font[slot].isWorthOutputting():
                    return (subidx, slot)
            except Exception:
                pass

        if cid_unicode_map is not None and missing_subfont:
            detail = f"slot={missing_slot}" if missing_slot is not None else ""
            log_issue("cid_slot_missing_subfont", u, detail=detail)
        if cid_unicode_map is not None:
            log_issue("cid_slot_not_found", u)
        return None
    finally:
        try:
            src_font.cidsubfont = saved
        except Exception:
            pass
