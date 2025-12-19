"""Build orchestration for Yonhwa Magazine Sans."""

from typing import Dict
import os
import time

import fontforge  # type: ignore

import config as cfg
from cid import build_cid_name_index, find_slot
from glyph_copy import copy_from_src, remove_base_jp_coverage_and_clear
from features import (
    apply_case_baseline_offsets,
    bake_feature_substitutions,
    bake_single_glyph_alternates,
    list_gsub_feature_tags,
    load_feature_substitutions,
    refresh_quote_glyphs,
    remove_gsub_lookups_by_feature_tags,
)
from geometry import bake, has_glyph, transform_entire_font
from font_io import open_font, set_names, suppress_stderr
from ranges import in_any, iter_ranges


def now() -> float:
    """Return a monotonic timestamp for timing logs."""
    return time.perf_counter()


def stage_progress(stage_tag: str, i: int, total: int, extra: str = "") -> None:
    """Print a throttled progress line for long-running stages."""
    if total <= 0:
        return
    if i == total or (i % cfg.PROGRESS_EVERY == 0):
        pct = (i * 100.0) / float(total)
        msg = f"\r[{stage_tag}] {i}/{total} ({pct:.1f}%)"
        if extra:
            msg += " " + extra
        print(msg, flush=True, end="")


def maybe_gc(i: int) -> None:
    """Trigger FontForge GC on a fixed cadence to reduce memory pressure."""
    if cfg.GC_EVERY <= 0:
        return
    if (i % cfg.GC_EVERY) != 0:
        return
    try:
        fontforge.garbageCollect()
    except Exception:
        pass


def build_one(variant: Dict[str, str]) -> None:
    """Build a single font variant using the configured sources."""
    t_all = now()

    base = open_font(variant["base_font_path"], flatten_cid=False)
    set_names(base, variant)

    base_upm = int(base.em)
    ko_dy = int(round((cfg.BASELINE_KO_PCT / 100.0) * base_upm))
    enclosed_dy = int(round((cfg.BASELINE_ENCLOSED_PCT / 100.0) * base_upm))

    jp_pre_x = cfg.SCALE_JP_X / cfg.SCALE_BASE_X
    jp_pre_y = cfg.SCALE_JP_Y / cfg.SCALE_BASE_Y
    digit_pre_x = cfg.SCALE_DIGIT_X / cfg.SCALE_BASE_X
    digit_pre_y = cfg.SCALE_DIGIT_Y / cfg.SCALE_BASE_Y
    ko_pre_x = cfg.SCALE_KO_X / cfg.SCALE_BASE_X
    ko_pre_y = cfg.SCALE_KO_Y / cfg.SCALE_BASE_Y
    enclosed_pre_x = cfg.SCALE_ENCLOSED_X / cfg.SCALE_BASE_X
    enclosed_pre_y = cfg.SCALE_ENCLOSED_Y / cfg.SCALE_BASE_Y

    # [0] Remove JP coverage from base.
    t = now()
    rm_map, cleared = remove_base_jp_coverage_and_clear(base)
    print(f"[0 base JP] removed_map={rm_map} cleared_slots={cleared} elapsed={now()-t:.2f}s", flush=True)

    # [1] Digits (optional override).
    if cfg.PRESERVE_DIGITS:
        print("[1 digits] skipped!", flush=True)
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

        print(f"\n[1 digits] elapsed={now()-t:.2f}s", flush=True)

    # [2] Korean (Hangul) and enclosed glyphs.
    t = now()
    ko = open_font(variant["korean_font_path"])
    ko_upm = int(ko.em)

    ko_targets = list(iter_ranges(cfg.HANGUL_MAIN_RANGES))
    enclosed_targets = list(iter_ranges(cfg.ENCLOSED_RANGES))
    total = len(ko_targets) + len(enclosed_targets)
    idx = 0

    for u in ko_targets:
        idx += 1
        sw = copy_from_src(ko, base, u, cid_name_index=None)
        if sw is not None:
            ratio = float(base_upm) / float(ko_upm)
            sx_total = ratio * ko_pre_x
            sy_total = ratio * ko_pre_y
            dy = ko_dy if (0xAC00 <= u <= 0xD7A3) else 0
            bake(base, u, sx_total, sy_total, dy, sw * sx_total)
        stage_progress("2 korean", idx, total)
        maybe_gc(idx)

    for u in enclosed_targets:
        idx += 1
        sw = copy_from_src(ko, base, u, cid_name_index=None)
        if sw is not None:
            ratio = float(base_upm) / float(ko_upm)
            sx_total = ratio * enclosed_pre_x
            sy_total = ratio * enclosed_pre_y
            bake(base, u, sx_total, sy_total, enclosed_dy, sw * sx_total)
        stage_progress("2 korean", idx, total)
        maybe_gc(idx)

    ko.close()
    print(f"\n[2 korean] elapsed={now()-t:.2f}s", flush=True)

    # [3] Japanese (CID pick by subfont).
    t = now()
    jp = open_font(variant["japanese_font_path"])
    jp_upm = int(jp.em)
    jp_idx = build_cid_name_index(jp)

    jp_targets = [u for u in iter_ranges(cfg.JP_TARGET_RANGES) if not in_any(u, cfg.DIGIT_RANGES)]
    total = len(jp_targets)
    repl = 0
    for i, u in enumerate(jp_targets, 1):
        if in_any(u, cfg.HANGUL_MAIN_RANGES):
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

    print(f"\n[3 japanese] replaced={repl}/{total} elapsed={now()-t:.2f}s", flush=True)

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
    print(f"[3 jp extra] filled={filled_extra} (whitelist)", flush=True)

    # [4] Alternates and GSUB cleanup.
    t = now()
    target_tags = set(cfg.ALWAYS_ON_FEATURE_TAGS + cfg.ALWAYS_ON_SS + cfg.ALWAYS_ON_EXTRA_SUFFIX)
    if cfg.ALWAYS_ON_SWASH:
        target_tags.add("swsh")

    subs, tags_seen_tt, per_tag_counts_tt, name_to_idx, name_to_uni = load_feature_substitutions(
        variant["base_font_path"], target_tags
    )
    baked_direct, per_tag_baked = bake_feature_substitutions(base, subs, name_to_idx, name_to_uni)

    baked_gsub, baked_suffix = bake_single_glyph_alternates(base)
    tags_seen_ff = list_gsub_feature_tags(base)
    tags_seen = tags_seen_tt | tags_seen_ff
    missing_tags = target_tags - tags_seen
    removed = remove_gsub_lookups_by_feature_tags(base, cfg.REMOVE_GSUB_FEATURES)
    print(f"[4 alternates] elapsed={now()-t:.2f}s", flush=True)
    print(f"[4 alternates] GSUB removed={removed}", flush=True)
    print(f"[4 alternates] GSUB baked direct={baked_direct} via coverage={baked_gsub} via suffix={baked_suffix}", flush=True)
    print(f"[4 alternates] GSUB tags seen TT={sorted(tags_seen_tt)}", flush=True)
    print(f"[4 alternates] GSUB per-tag subs TT={per_tag_counts_tt}", flush=True)
    print(f"[4 alternates] GSUB tags baked per-tag={per_tag_baked}", flush=True)
    if missing_tags:
        print(f"[4 alternates] GSUB missing tags (not found to bake): {sorted(missing_tags)}", flush=True)
    else:
        print(f"[4 alternates] GSUB all target tags found", flush=True)

    # [5] Manual baseline tweaks for math symbols / brackets.
    t = now()
    applied_offsets = apply_case_baseline_offsets(
        base,
        base_upm,
        cfg.CASE_MATH_BASELINE_OFFSET,
        cfg.CASE_BRACKET_BASELINE_OFFSET,
        cfg.CASE_DASH_ARROW_BASELINE_OFFSET,
    )
    print(
        f"[5 baseline] math={applied_offsets.get('math',0)} bracket={applied_offsets.get('bracket',0)} dash={applied_offsets.get('dash',0)} elapsed={now()-t:.2f}s",
        flush=True,
    )

    # [6] Fix curly quote glyphs by recopying from the base font.
    t = now()
    refreshed = refresh_quote_glyphs(base, variant["base_font_path"], cfg.QUOTE_FIX_CODEPOINTS)
    print(f"[6 quotes] refreshed={refreshed} elapsed={now()-t:.2f}s", flush=True)

    # [7] Global base scale (including GPOS/kern data).
    t = now()
    transform_entire_font(base, cfg.SCALE_BASE_X, cfg.SCALE_BASE_Y)
    print(f"[7 global scale] elapsed={now()-t:.2f}s", flush=True)

    print("[AUDIT] こ(U+3053):", has_glyph(base, 0x3053), flush=True)
    print("[AUDIT] ｱ(U+FF71):", has_glyph(base, 0xFF71), flush=True)
    print("[AUDIT] 漢(U+6F22):", has_glyph(base, 0x6F22), flush=True)
    print("[AUDIT] ㉠(U+3260):", has_glyph(base, 0x3260), flush=True)

    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    base_name, ext = os.path.splitext(variant["out_font_filename"])
    ext = ext or ".ttf"
    versioned_name = f"{base_name}-{cfg.OUT_VERSION_STR}{ext}"
    out_path = os.path.join(cfg.OUTPUT_DIR, versioned_name)
    t = now()
    with suppress_stderr(cfg.SILENCE_FONTFORGE_WARNINGS):
        base.generate(out_path)
    base.close()
    print(f"[8 generate] elapsed={now()-t:.2f}s", flush=True)
    print(f"DONE: {out_path} total={now()-t_all:.2f}s", flush=True)


def build_all() -> None:
    """Build every font variant declared in config.FONT_VARIANTS."""
    print()
    for variant in cfg.FONT_VARIANTS:
        build_one(variant)
        print()
