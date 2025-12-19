"""GSUB baking, baseline tweaks, and glyph refresh helpers."""

from typing import Dict, List, Sequence, Set, Tuple

import psMat  # type: ignore
from fontTools.ttLib import TTFont

import config as cfg
from cid import find_slot
from geometry import bake, worth
from font_io import open_font, suppress_stderr
from ranges import in_any
from glyph_copy import copy_from_src


def overwrite_outline_same_font(font, dst_g, src_g) -> None:
    """Overwrite a glyph's outline with another glyph in the same font."""
    keep_u = dst_g.unicode
    keep_w = dst_g.width
    dst_g.clear()
    with suppress_stderr(cfg.SILENCE_FONTFORGE_WARNINGS):
        font.selection.none()
        font.selection.select(int(src_g.encoding))
        font.copy()
        font.selection.none()
        font.selection.select(int(dst_g.encoding))
        font.paste()
    dst_g.unicode = keep_u
    dst_g.width = keep_w
    try:
        dst_g.altuni = None
    except Exception:
        pass


def bake_single_glyph_alternates(dst_font) -> Tuple[int, int]:
    """Bake stylistic/swash/salt alternates into base glyphs and drop lookups."""
    always_tags = set(
        cfg.ALWAYS_ON_SS
        + cfg.ALWAYS_ON_EXTRA_SUFFIX
        + cfg.ALWAYS_ON_FEATURE_TAGS
        + (["swsh"] if cfg.ALWAYS_ON_SWASH else [])
    )
    baked_gsub = 0
    baked_suffix = 0

    try:
        lookups = list(dst_font.getLookups("GSUB"))
    except Exception:
        lookups = []
    for lk in lookups:
        feats = set()
        try:
            info = dst_font.getLookupInfo(lk)
            feats_raw = info[2] if info and len(info) >= 3 else []
            for f in feats_raw:
                feats.add(f[0] if isinstance(f, (tuple, list)) and len(f) >= 1 else f)
        except Exception:
            feats = set()
        if not (feats & always_tags):
            continue

        try:
            subtables = dst_font.getLookupSubtables(lk)
        except Exception:
            subtables = []
        for sub in subtables:
            try:
                cov = dst_font.getLookupSubtableCoverage(sub)
            except Exception:
                cov = None
            if not isinstance(cov, dict):
                continue
            for src_name, dst_entry in cov.items():
                dst_name = dst_entry[0] if isinstance(dst_entry, (list, tuple)) else dst_entry
                try:
                    base_g = dst_font[src_name]
                    alt_g = dst_font[dst_name]
                except Exception:
                    continue
                try:
                    u = int(getattr(base_g, "unicode", -1) or -1)
                except Exception:
                    u = -1
                if u != -1 and ((u in DASH_PROTECT) or (u in BRACKET_PROTECT) or in_any(u, cfg.DIGIT_RANGES)):
                    continue
                if worth(alt_g):
                    overwrite_outline_same_font(dst_font, base_g, alt_g)
                    baked_gsub += 1

    suffixes = list(cfg.ALWAYS_ON_SS) + list(cfg.ALWAYS_ON_EXTRA_SUFFIX)
    if cfg.ALWAYS_ON_SWASH:
        suffixes.append("swsh")

    if cfg.ALWAYS_ON_SLASH_ZERO:
        for u0 in (0x0030, 0xFF10):
            slot = find_slot(dst_font, u0)
            if slot != -1:
                try:
                    z = dst_font[slot]
                    zalt = dst_font["zero.slash"]
                    if worth(z) and worth(zalt):
                        overwrite_outline_same_font(dst_font, z, zalt)
                except Exception:
                    pass

    for g in dst_font.glyphs():
        if not worth(g) or g.unicode == -1:
            continue
        if in_any(int(g.unicode), cfg.DIGIT_RANGES):
            continue
        base_name = getattr(g, "glyphname", None) or getattr(g, "name", "")
        if not base_name:
            continue
        for tag in suffixes:
            alt_name = f"{base_name}.{tag}"
            try:
                alt = dst_font[alt_name]
            except Exception:
                continue
            if worth(alt):
                overwrite_outline_same_font(dst_font, g, alt)
                baked_suffix += 1
    return baked_gsub, baked_suffix


def remove_gsub_lookups_by_feature_tags(font, remove_tags: Set[str]) -> int:
    """Remove GSUB lookups that match any of the provided feature tags."""
    lookups = []
    try:
        lookups = list(getattr(font, "gsub_lookups", []) or [])
    except Exception:
        lookups = []
    if not lookups:
        try:
            lookups = list(font.getLookups("GSUB"))
        except Exception:
            lookups = []

    removed = 0
    for lk in lookups:
        tags = set()
        try:
            info = font.getLookupInfo(lk)
            feats = info[2] if len(info) >= 3 else []
            for f in feats:
                if isinstance(f, (tuple, list)) and len(f) >= 1:
                    tags.add(f[0])
                elif isinstance(f, str):
                    tags.add(f)
        except Exception:
            pass
        if tags & remove_tags:
            try:
                font.removeLookup(lk)
                removed += 1
            except Exception:
                pass
    return removed


def list_gsub_feature_tags(font) -> Set[str]:
    """Collect GSUB feature tags present in the font."""
    tags: Set[str] = set()
    lookups = []
    try:
        lookups = list(getattr(font, "gsub_lookups", []) or [])
    except Exception:
        lookups = []
    if not lookups:
        try:
            lookups = list(font.getLookups("GSUB"))
        except Exception:
            lookups = []
    for lk in lookups:
        try:
            info = font.getLookupInfo(lk)
            feats = info[2] if info and len(info) >= 3 else []
            for f in feats:
                if isinstance(f, (tuple, list)) and len(f) >= 1:
                    tags.add(f[0])
                elif isinstance(f, str):
                    tags.add(f)
        except Exception:
            continue
    return tags


def load_feature_substitutions(tt_path: str, target_tags: Set[str]):
    """Load substitutions for target tags from a TT/OTF via fontTools GSUB."""
    try:
        tt = TTFont(tt_path)
    except Exception:
        return [], set(), {}, {}, {}
    if "GSUB" not in tt:
        return [], set(), {}, {}, {}

    gsub = tt["GSUB"].table
    feat_records = gsub.FeatureList.FeatureRecord if gsub.FeatureList else []
    present_tags = {fr.FeatureTag for fr in feat_records}
    glyph_order = tt.getGlyphOrder()
    name_to_idx = {n: i for i, n in enumerate(glyph_order)}
    name_to_uni: Dict[str, int] = {}
    try:
        cmap = tt.getBestCmap() or {}
        for uni, gname in cmap.items():
            name_to_uni.setdefault(gname, int(uni))
    except Exception:
        pass

    tag_to_lookups = {}
    for idx, fr in enumerate(feat_records):
        tag = fr.FeatureTag
        if tag not in target_tags:
            continue
        lookups = fr.Feature.LookupListIndex
        tag_to_lookups.setdefault(tag, []).extend(lookups)

    if not tag_to_lookups:
        return [], present_tags, {}, name_to_idx, name_to_uni

    subs: List[Tuple[str, str, str]] = []
    per_tag_counts = {tag: 0 for tag in tag_to_lookups}
    lookup_list = gsub.LookupList.Lookup if gsub.LookupList else []
    for tag, lks in tag_to_lookups.items():
        for lk_idx in lks:
            if lk_idx >= len(lookup_list):
                continue
            lk = lookup_list[lk_idx]
            lt = lk.LookupType
            if lt == 1:
                for st in lk.SubTable:
                    try:
                        mapping = st.mapping
                    except Exception:
                        continue
                    for src, dst in mapping.items():
                        subs.append((src, dst, tag))
                        per_tag_counts[tag] = per_tag_counts.get(tag, 0) + 1
            elif lt == 3:
                for st in lk.SubTable:
                    try:
                        alts = st.alternates
                    except Exception:
                        continue
                    for src, dst_list in alts.items():
                        if dst_list:
                            subs.append((src, dst_list[0], tag))
                            per_tag_counts[tag] = per_tag_counts.get(tag, 0) + 1
    return subs, present_tags, per_tag_counts, name_to_idx, name_to_uni


def bake_feature_substitutions(
    dst_font,
    subs: Sequence[Tuple[str, str, str]],
    name_to_idx: Dict[str, int],
    name_to_uni: Dict[str, int],
) -> Tuple[int, Dict[str, int]]:
    """Apply explicit glyph-name substitutions onto dst_font."""
    baked = 0
    per_tag: Dict[str, int] = {}
    total = len(list(dst_font.glyphs()))

    def pick(name: str):
        try:
            return dst_font[name]
        except Exception:
            pass
        idx = name_to_idx.get(name)
        if idx is None and name.lower().startswith("cid"):
            try:
                idx = int(name[3:])
            except Exception:
                idx = None
        if idx is not None and 0 <= idx < total:
            try:
                return dst_font[idx]
            except Exception:
                pass
        uni = name_to_uni.get(name)
        if uni is not None:
            slot = find_slot(dst_font, uni)
            if slot != -1:
                try:
                    return dst_font[slot]
                except Exception:
                    return None
        return None

    for src_name, dst_name, tag in subs:
        base_g = pick(src_name)
        alt_g = pick(dst_name)
        if base_g is None or alt_g is None:
            continue
        try:
            u = int(getattr(base_g, "unicode", -1) or -1)
        except Exception:
            u = -1
        if u != -1 and ((u in DASH_PROTECT) or (u in BRACKET_PROTECT) or in_any(u, cfg.DIGIT_RANGES)):
            continue
        if worth(alt_g):
            overwrite_outline_same_font(dst_font, base_g, alt_g)
            baked += 1
            per_tag[tag] = per_tag.get(tag, 0) + 1
    return baked, per_tag


MATH_CASE_CODEPOINTS = [
    0x2212, 0x002B, 0x00F7, 0x00B1, 0x00D7,
    0x003D, 0x2260, 0x2248, 0x007E,
    0x003C, 0x003E, 0x2264, 0x2265,
]

BRACKET_CASE_CODEPOINTS = [
    0x0028, 0x0029,
    0x003C, 0x003E,
    0x007B, 0x007D,
    0x005B, 0x005D,
    0x00AB, 0x00BB,
    0x2039, 0x203A,
]

DASH_CASE_CODEPOINTS = [
    0x002D,
    0x2013,
    0x2014,
    0x2192,
    0x2190,
    0x27F6,
    0x27F5,
    0x27FA,
]
DASH_PROTECT: Set[int] = set(DASH_CASE_CODEPOINTS)
BRACKET_PROTECT: Set[int] = set(BRACKET_CASE_CODEPOINTS)


def apply_case_baseline_offsets(font, base_upm: int, math_pct: float, bracket_pct: float, dash_pct: float):
    """Shift math symbols, brackets, and dashes vertically (percent of UPM)."""
    if not math_pct and not bracket_pct and not dash_pct:
        return {"math": 0, "bracket": 0, "dash": 0}

    math_offset = int(round((math_pct / 100.0) * base_upm))
    bracket_offset = int(round((bracket_pct / 100.0) * base_upm))
    dash_offset = int(round((dash_pct / 100.0) * base_upm))

    targets: Dict[int, Tuple[int, str]] = {}
    if math_offset:
        for u in MATH_CASE_CODEPOINTS:
            targets[u] = (math_offset, "math")
    if bracket_offset:
        for u in BRACKET_CASE_CODEPOINTS:
            targets[u] = (bracket_offset, "bracket")
    if dash_offset:
        for u in DASH_CASE_CODEPOINTS:
            targets[u] = (dash_offset, "dash")

    applied = {"math": 0, "bracket": 0, "dash": 0}
    for u, (dy, label) in targets.items():
        slot = find_slot(font, u)
        if slot == -1:
            continue
        try:
            g = font[slot]
        except Exception:
            continue
        if not worth(g):
            continue
        try:
            g.transform(psMat.translate(0, dy))
            applied[label] = applied.get(label, 0) + 1
        except Exception:
            continue
    return applied


def refresh_quote_glyphs(dst_font, src_font_path: str, codepoints: List[int]) -> int:
    """Re-copy specific quote glyphs from the source base font."""
    if not codepoints:
        return 0
    try:
        src_font = open_font(src_font_path, flatten_cid=False)
    except Exception:
        return 0
    src_upm = int(getattr(src_font, "em", 0) or 0)
    dst_upm = int(getattr(dst_font, "em", 0) or 0)
    ratio = float(dst_upm) / float(src_upm) if src_upm else 1.0

    refreshed = 0
    for u in codepoints:
        sw = copy_from_src(src_font, dst_font, u, cid_name_index=None)
        if sw is None:
            continue
        bake(dst_font, u, ratio, ratio, 0, sw * ratio)
        refreshed += 1

    src_font.close()
    return refreshed
