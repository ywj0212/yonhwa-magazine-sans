"""Font build pipeline for Yonhwa Magazine Sans.

This module orchestrates glyph merging, scaling, and output generation
using FontForge scripting and values from config.py.
"""

import contextlib
import os
import re
import sys
import time

import fontforge  # type: ignore
import psMat      # type: ignore

import config as cfg

_CID_SLOT_CACHE = {}


def now():
    """Return a monotonic timestamp for timing logs."""
    return time.perf_counter()


def in_any(u, ranges):
    """Return True if codepoint u is inside any (start, end) range."""
    for a, b in ranges:
        if a <= u <= b:
            return True
    return False


def jp_allowed(u: int) -> bool:
    """Return True if the JP replacement rule allows this codepoint."""
    if in_any(u, cfg.EXCLUDE_PUNCT_SYMBOL_RANGES) and (not in_any(u, cfg.DIGIT_RANGES)):
        return False
    return True


def worth(g):
    """Return True if the glyph is valid and worth outputting."""
    try:
        return g is not None and g.isWorthOutputting()
    except Exception:
        return False


def ps_sanitize(name: str) -> str:
    """Normalize a PostScript name to ASCII-safe characters."""
    s = name.replace(" ", "")
    s = re.sub(r"[^A-Za-z0-9\-]", "", s)
    return s if s else "Font"


@contextlib.contextmanager
def suppress_stderr(enabled: bool):
    """Optionally silence stderr to reduce noisy FontForge warnings."""
    if not enabled:
        yield
        return
    try:
        fd = sys.stderr.fileno()
    except Exception:
        yield
        return
    saved = os.dup(fd)
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, fd)
        os.close(devnull)
        yield
    finally:
        os.dup2(saved, fd)
        os.close(saved)


def open_font(path: str):
    """Open a font file and normalize encoding where safe."""
    with suppress_stderr(cfg.SILENCE_FONTFORGE_WARNINGS):
        f = fontforge.open(path, ("hidewindow", "alltables"))
    try:
        cnt = int(getattr(f, "cidsubfontcnt", 0) or 0)
    except Exception:
        cnt = 0
    if cnt <= 0:
        try:
            f.encoding = "UnicodeFull"
            f.reencode("UnicodeFull")
        except Exception:
            pass
    return f


def set_names(f, variant):
    """Apply family/style/version naming to the output font."""
    out_fontname = ps_sanitize(variant["out_ps_name"])
    f.familyname = cfg.OUT_FAMILY_NAME
    f.fullname = f"{cfg.OUT_FAMILY_NAME} {variant['out_style_name']}"
    f.fontname = out_fontname
    try:
        f.sfnt_names = ()
    except Exception:
        pass
    uid = f"{out_fontname};{cfg.OUT_VERSION_STR}"

    def add(lang, nid, s):
        try:
            f.appendSFNTName(lang, nid, s)
        except Exception:
            pass

    add("English (US)", 1, cfg.OUT_FAMILY_NAME)
    add("English (US)", 2, variant["legacy_style_name"])
    add("English (US)", 3, uid)
    add("English (US)", 4, f"{cfg.OUT_FAMILY_NAME} {variant['out_style_name']}")
    add("English (US)", 5, cfg.OUT_VERSION_STR)
    add("English (US)", 6, out_fontname)
    add("English (US)", 16, cfg.OUT_FAMILY_NAME)
    add("English (US)", 17, variant["out_style_name"])


def stage_progress(stage_tag: str, i: int, total: int, extra: str = ""):
    """Print a throttled progress line for long-running stages."""
    if total <= 0:
        return
    if i == total or (i % cfg.PROGRESS_EVERY == 0):
        pct = (i * 100.0) / float(total)
        msg = f"\r[{stage_tag}] {i}/{total} ({pct:.1f}%)"
        if extra:
            msg += " " + extra
        print(msg, flush=True, end="")


def maybe_gc(i: int):
    """Trigger FontForge GC on a fixed cadence to reduce memory pressure."""
    if cfg.GC_EVERY <= 0:
        return
    if (i % cfg.GC_EVERY) != 0:
        return
    try:
        fontforge.garbageCollect()
    except Exception:
        pass


def _cid_slot_map(font, subidx: int):
    """Build or fetch a unicode-to-encoding map for a CID subfont.

    CID fonts can segfault with findEncodingSlot; a cached map avoids that.
    """
    fid = id(font)
    submaps = _CID_SLOT_CACHE.get(fid)
    if submaps is None:
        submaps = {}
        _CID_SLOT_CACHE[fid] = submaps
    if subidx in submaps:
        return submaps[subidx]

    mapping = {}
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
    """Resolve a codepoint to an encoding slot, safely for CID fonts."""
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


def has_glyph(font, u: int) -> bool:
    """Return True if the font has a drawable glyph for u."""
    s = find_slot(font, u)
    if s == -1:
        return False
    try:
        return worth(font[s])
    except Exception:
        return False


def iter_ranges(ranges):
    """Yield every codepoint from a list of inclusive ranges."""
    for a, b in ranges:
        for u in range(a, b + 1):
            yield u


def clear_anchors_if_needed(g):
    """Drop anchors on a glyph when normalization is enabled."""
    if not cfg.NORMALIZE_ANCHORS:
        return
    try:
        g.anchorPoints = None
    except Exception:
        pass


# =========================
# CID subfont selection
# =========================

def get_cid_subfont_names(font):
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


def build_cid_name_index(font):
    """Build a name->index lookup for CID subfonts."""
    idx = {}
    for i, n in get_cid_subfont_names(font):
        idx[n] = i
    return idx


def pick_cid_indices_by_patterns(name_index, patterns):
    """Pick subfont indices whose names contain any pattern."""
    out = []
    for pat in patterns:
        for name, i in name_index.items():
            if pat in name:
                out.append(i)
    seen = set()
    uniq = []
    for i in out:
        if i in seen:
            continue
        seen.add(i)
        uniq.append(i)
    return uniq


def cid_preferred_indices(name_index, u: int):
    """Return preferred CID subfonts for a codepoint category."""
    if 0xFF65 <= u <= 0xFF9F:
        return pick_cid_indices_by_patterns(name_index, ["HWidth", "HKana", "Kana", "Generic"])
    if in_any(u, cfg.KANA_RANGES):
        return pick_cid_indices_by_patterns(name_index, ["HKana", "Kana", "VKana", "Generic"])
    if in_any(u, cfg.CJK_IDEOGRAPH_RANGES):
        return pick_cid_indices_by_patterns(
            name_index,
            ["Ideographs", "ProportionalCJK", "HWidthCJK", "Generic"],
        )
    return pick_cid_indices_by_patterns(name_index, ["Generic"])


def resolve_src_slot_cid(src_font, u: int, name_index):
    """Resolve a glyph slot in a CID font by trying preferred subfonts."""
    try:
        cnt = int(getattr(src_font, "cidsubfontcnt", 0) or 0)
    except Exception:
        cnt = 0
    if cnt <= 0:
        slot = find_slot(src_font, u)
        if slot != -1:
            try:
                if worth(src_font[slot]):
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
        order = cid_preferred_indices(name_index, u)
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
                if worth(src_font[slot]):
                    return (subidx, slot)
            except Exception:
                pass

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
                if worth(src_font[slot]):
                    return (subidx, slot)
            except Exception:
                pass

        return None
    finally:
        try:
            src_font.cidsubfont = saved
        except Exception:
            pass


# =========================
# Copy and bake helpers
# =========================

def copy_from_src(src_font, dst_font, u: int, cid_name_index=None):
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

    # Selection must use integer indices only.
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


def bake(dst_font, u: int, sx_total, sy_total, dy_units, width_final):
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


def transform_entire_font(font, sx, sy):
    """Scale the entire font, preserving positioning tables where possible."""
    if sx == 1.0 and sy == 1.0:
        return
    font.selection.all()
    try:
        font.transform(psMat.scale(sx, sy), ("round", "simplePos", "kernClasses"))
    except Exception:
        font.transform(psMat.scale(sx, sy))
    font.selection.none()


# =========================
# Remove JP coverage from base
# =========================

def unmap_unicode_and_altuni(g):
    """Remove unicode and altuni mappings from a glyph."""
    try:
        g.unicode = -1
    except Exception:
        pass
    try:
        g.altuni = None
    except Exception:
        pass


def strip_altuni_entries(g, should_remove_u):
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


def remove_base_jp_coverage_and_clear(base_font):
    """Remove JP mappings from the base font and clear JP outlines."""
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


# =========================
# Alternates and GSUB cleanup
# =========================

def overwrite_outline_same_font(font, dst_g, src_g):
    """Overwrite a glyph's outline with another glyph in the same font."""
    keep_u = dst_g.unicode
    keep_w = dst_g.width
    dst_g.clear()
    font.selection.none(); font.selection.select(int(src_g.encoding)); font.copy()
    font.selection.none(); font.selection.select(int(dst_g.encoding)); font.paste()
    dst_g.unicode = keep_u
    dst_g.width = keep_w
    try:
        dst_g.altuni = None
    except Exception:
        pass


def bake_single_glyph_alternates(dst_font):
    """Bake configured alternates into their base glyphs."""
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


def remove_gsub_lookups_by_feature_tags(font, remove_tags: set):
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


def build_one(variant):
    """Build a single font variant using the configured sources."""
    t_all = now()

    base = open_font(variant["base_font_path"])
    set_names(base, variant)

    base_upm = int(base.em)
    ko_dy = int(round((cfg.BASELINE_KO_PCT / 100.0) * base_upm))

    jp_pre_x = cfg.SCALE_JP_X / cfg.SCALE_BASE_X
    jp_pre_y = cfg.SCALE_JP_Y / cfg.SCALE_BASE_Y
    digit_pre_x = cfg.SCALE_DIGIT_X / cfg.SCALE_BASE_X
    digit_pre_y = cfg.SCALE_DIGIT_Y / cfg.SCALE_BASE_Y
    ko_pre_x = cfg.SCALE_KO_X / cfg.SCALE_BASE_X
    ko_pre_y = cfg.SCALE_KO_Y / cfg.SCALE_BASE_Y

    # [0] Remove JP coverage from base.
    t = now()
    rm_map, cleared = remove_base_jp_coverage_and_clear(base)
    print(f"[0] base JP removed_map={rm_map} cleared_slots={cleared} elapsed={now()-t:.2f}s", flush=True)

    # [1] Digits (optional override).
    if cfg.PRESERVE_DIGITS:
        print("[1] digits skipped!", flush=True)
    else:
        t = now()
        lato = open_font(variant["digit_font_path"])
        lato_upm = int(lato.em)

        digits = [u for u in iter_ranges(cfg.DIGIT_RANGES)]
        total = len(digits)
        for i, u in enumerate(digits, 1):
            sw = copy_from_src(lato, base, u, cid_name_index=None)
            if sw is not None:
                ratio = float(base_upm) / float(lato_upm)
                sx_total = ratio * digit_pre_x
                sy_total = ratio * digit_pre_y
                bake(base, u, sx_total, sy_total, 0, sw * sx_total)
            stage_progress("1 digits", i, total)
            maybe_gc(i)
        lato.close()

        for d in range(10):
            u_ascii = 0x0030 + d
            u_full = 0xFF10 + d
            try:
                srcg = base[find_slot(base, u_ascii)]
                dstg = base.createChar(u_full)
                dstg.clear()
                base.selection.none(); base.selection.select(int(srcg.encoding)); base.copy()
                base.selection.none(); base.selection.select(int(dstg.encoding)); base.paste()
                dstg.unicode = u_full
                dstg.width = srcg.width
            except Exception:
                pass

        print(f"\n[1] digits elapsed={now()-t:.2f}s", flush=True)

    # [2] Korean (Hangul + Enclosed).
    t = now()
    ko = open_font(variant["korean_font_path"])
    ko_upm = int(ko.em)

    ko_targets = list(iter_ranges(cfg.HANGUL_MAIN_RANGES)) + list(iter_ranges(cfg.ENCLOSED_RANGES))
    total = len(ko_targets)
    for i, u in enumerate(ko_targets, 1):
        sw = copy_from_src(ko, base, u, cid_name_index=None)
        if sw is not None:
            ratio = float(base_upm) / float(ko_upm)
            sx_total = ratio * ko_pre_x
            sy_total = ratio * ko_pre_y
            dy = ko_dy if (0xAC00 <= u <= 0xD7A3) else 0
            bake(base, u, sx_total, sy_total, dy, sw * sx_total)
        stage_progress("2 korean", i, total)
        maybe_gc(i)
    ko.close()
    print(f"\n[2] korean elapsed={now()-t:.2f}s", flush=True)

    # [3] Japanese (CID pick by subfont).
    t = now()
    jp = open_font(variant["japanese_font_path"])
    jp_upm = int(jp.em)
    jp_idx = build_cid_name_index(jp)

    jp_targets = [u for u in iter_ranges(cfg.JP_TARGET_RANGES) if jp_allowed(u)]
    total = len(jp_targets)
    repl = 0
    for i, u in enumerate(jp_targets, 1):
        if in_any(u, cfg.DIGIT_RANGES) or in_any(u, cfg.HANGUL_MAIN_RANGES):
            stage_progress("3 japanese", i, total, extra=f"replaced={repl}")
            continue

        sw = copy_from_src(jp, base, u, cid_name_index=jp_idx)

        if sw is not None:
            ratio = float(base_upm) / float(jp_upm)
            sx_total = ratio * jp_pre_x
            sy_total = ratio * jp_pre_y
            bake(base, u, sx_total, sy_total, 0, sw * sx_total)
            repl += 1

        stage_progress("3 japanese", i, total, extra=f"replaced={repl}")
        maybe_gc(i)

    print(f"\n[3] japanese replaced={repl}/{total} elapsed={now()-t:.2f}s", flush=True)

    filled_extra = 0
    for u in sorted(cfg.JP_EXTRA_SET):
        if in_any(u, cfg.DIGIT_RANGES) or in_any(u, cfg.HANGUL_MAIN_RANGES):
            continue

        if (not cfg.JP_EXTRA_OVERWRITE) and has_glyph(base, u):
            continue

        sw = copy_from_src(jp, base, u, cid_name_index=jp_idx)
        if sw is None:
            continue

        ratio = float(base_upm) / float(jp_upm)
        sx_total = ratio * jp_pre_x
        sy_total = ratio * jp_pre_y
        bake(base, u, sx_total, sy_total, 0, sw * sx_total)
        filled_extra += 1

    jp.close()
    print(f"[3] jp extra filled={filled_extra} (whitelist)", flush=True)

    # [4] Alternates and GSUB cleanup.
    t = now()
    bake_single_glyph_alternates(base)
    removed = remove_gsub_lookups_by_feature_tags(base, cfg.REMOVE_GSUB_FEATURES)
    print(f"[4] alternates elapsed={now()-t:.2f}s", flush=True)
    print(f"[4] GSUB removed={removed}", flush=True)

    # [5] Global base scale (including GPOS/kern data).
    t = now()
    transform_entire_font(base, cfg.SCALE_BASE_X, cfg.SCALE_BASE_Y)
    print(f"[5] global base scale elapsed={now()-t:.2f}s", flush=True)

    print("[AUDIT] こ(U+3053):", has_glyph(base, 0x3053), flush=True)
    print("[AUDIT] ｱ(U+FF71):", has_glyph(base, 0xFF71), flush=True)
    print("[AUDIT] 漢(U+6F22):", has_glyph(base, 0x6F22), flush=True)
    print("[AUDIT] ㉠(U+3260):", has_glyph(base, 0x3260), flush=True)

    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(cfg.OUTPUT_DIR, variant["out_font_filename"])
    t = now()
    with suppress_stderr(cfg.SILENCE_FONTFORGE_WARNINGS):
        base.generate(out_path)
    base.close()
    print(f"[6] generate elapsed={now()-t:.2f}s", flush=True)
    print(f"DONE: {out_path} total={now()-t_all:.2f}s", flush=True)


def build_all():
    """Build every font variant declared in config.FONT_VARIANTS."""
    for variant in cfg.FONT_VARIANTS:
        build_one(variant)
