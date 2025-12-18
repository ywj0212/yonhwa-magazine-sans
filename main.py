#!/usr/bin/env python3
import re, os, sys, time, math, unicodedata, contextlib
import fontforge  # type: ignore
import psMat      # type: ignore
import faulthandler; faulthandler.enable(all_threads=True)

# =========================
# USER CONSTANTS
# =========================
PRESERVE_DIGITS = True

FONT_VARIANTS = [
    {
        "base_font_path": "./font/Pretendard-Medium.otf",
        "korean_font_path": "./font/GmarketSansTTFMedium.ttf",
        "japanese_font_path": "./font/NotoSansCJKjp-Medium.otf",  # CID 원본 그대로 사용
        "digit_font_path": "./font/Lato-Semibold.ttf",
        "out_font_path": "YonhwaMagazineSans-Medium.ttf",
        "out_family_name": "Yonhwa Magazine Sans",
        "out_style_name": "Medium",
        "legacy_style_name": "Regular",
        "out_ps_name": "Yonhwa Magazine Sans Medium",
        "out_version_str": "Version 1.000",
    },
    {
        "base_font_path": "./font/Pretendard-ExtraBold.otf",
        "korean_font_path": "./font/GmarketSansTTFBold.ttf",
        "japanese_font_path": "./font/NotoSansCJKjp-Black.otf",  # CID 원본 그대로 사용
        "digit_font_path": "./font/Lato-Black.ttf",
        "out_font_path": "YonhwaMagazineSans-Bold.ttf",
        "out_family_name": "Yonhwa Magazine Sans",
        "out_style_name": "Bold",
        "legacy_style_name": "Bold",
        "out_ps_name": "Yonhwa Magazine Sans Bold",
        "out_version_str": "Version 1.000",
    },
    {
        "base_font_path": "./font/Pretendard-ExtraLight.otf",
        "korean_font_path": "./font/GmarketSansTTFLight.ttf",
        "japanese_font_path": "./font/NotoSansCJKjp-Light.otf",  # CID 원본 그대로 사용
        "digit_font_path": "./font/Lato-Light.ttf",
        "out_font_path": "YonhwaMagazineSans-Light.ttf",
        "out_family_name": "Yonhwa Magazine Sans",
        "out_style_name": "Light",
        "legacy_style_name": "Light",
        "out_ps_name": "Yonhwa Magazine Sans Light",
        "out_version_str": "Version 1.000",
    },
]

BASE_FONT_PATH = ""
KOREAN_FONT_PATH = ""
JAPANESE_FONT_PATH = ""
DIGIT_FONT_PATH = ""

OUT_FONT_PATH = ""
OUT_FAMILY_NAME = ""
OUT_STYLE_NAME = ""
LEGACY_STYLE_NAME = ""
OUT_PS_NAME = ""
OUT_VERSION_STR = ""
OUT_FONTNAME = ""

SCALE_BASE_X = 0.96
SCALE_BASE_Y = 1.00

SCALE_DIGIT_X = 0.96
SCALE_DIGIT_Y = 1.00

SCALE_KO_X = 0.94 * 0.94
SCALE_KO_Y = 0.94
BASELINE_KO_PCT = 5.5

SCALE_JP_X = 0.9375 * 0.96
SCALE_JP_Y = 0.9375

ALWAYS_ON_SS = ["ss01", "ss02", "ss03", "ss05"]
ALWAYS_ON_SWASH = True
ALWAYS_ON_SLASH_ZERO = True
ALWAYS_ON_EXTRA_SUFFIX = ["salt"]
REMOVE_GSUB_FEATURES = set(ALWAYS_ON_SS + ALWAYS_ON_EXTRA_SUFFIX + (["swsh"] if ALWAYS_ON_SWASH else []))

SILENCE_FONTFORGE_WARNINGS = True
PROGRESS_EVERY = 2000
GC_EVERY = 4000

NORMALIZE_ANCHORS = True  # ✅ 앵커/마크 경고 줄이기(앵커 제거)

# =========================
# Unicode ranges
# =========================
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

# ✅ BMP 위주(속도/안정성). 필요하면 Ext B+는 나중에 추가.
CJK_IDEOGRAPH_RANGES = [
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
]

# JP 처리 시 “기호/구두점 등”은 기본 유지(원하면 끄면 됨)
EXCLUDE_PUNCT_SYMBOL_RANGES = [
    (0x2000, 0x206F),
    (0x3000, 0x303F),
    (0xFE10, 0xFE1F),
    (0xFE30, 0xFE4F),
    (0xFF00, 0xFF0F),
    (0xFF1A, 0xFF60),
]

JP_TARGET_RANGES = KANA_RANGES + CJK_IDEOGRAPH_RANGES

# === JP extra glyphs: whitelist only ===
JP_EXTRA_OVERWRITE = False  # True면 기존에 있어도 Noto로 덮어씀(원하면 켜)

JP_EXTRA_GLYPHS_EXACT = (
    "㈱㈲㍿㍑㌔㌢㌦㌧㌫"
    "｡｢｣､"
    "♠♣♦"
    "∇∈∉⊂⊃⊆⊇∧∨¬"
    "々〻〆〇"
    "〰〽〒〠〓"
    "⓵⓶⓷⓸⓹"
    "㊀㊁㊂㊃㊄"
    "㈠㈡㈢㈣㈤"
    "─━│┃┌┏┐┓└┗┘┛├┣┤┫┬┳┴┻┼╋"
    "░▒▓█▁▂▃▄▅▆▇▉▊▋▌▍▎▏"
    "⤴⤵"
    "∓≡"
)

def build_jp_extra_set():
    # 1) exact: 네가 준 글리프만
    exact = {ord(ch) for ch in JP_EXTRA_GLYPHS_EXACT if not ch.isspace()}

    # 2) similar expansion ONLY for the first group:
    #    ㈱㈲ (parenthesized ideographs) + ㍿/㍑/㌔/㌢/㌦/㌧/㌫ (square symbols)
    similar = set()

    # 0x3300..0x33FF: CJK Compatibility (㌔,㌢,㌦,㌧,㌫,㍑,㍿ 등)
    for u in range(0x3300, 0x3400):
        try:
            name = unicodedata.name(chr(u))
        except Exception:
            continue
        similar.add(u)

    # 0x3200..0x32FF: Enclosed CJK (㈱,㈲ 등)
    for u in range(0x3200, 0x3300):
        try:
            name = unicodedata.name(chr(u))
        except Exception:
            continue
        similar.add(u)

    return exact | similar
JP_EXTRA_SET = build_jp_extra_set()

# =========================
# Helpers
# =========================
def now(): return time.perf_counter()

def in_any(u, ranges):
    for a,b in ranges:
        if a <= u <= b:
            return True
    return False

def jp_allowed(u: int) -> bool:
    # digit는 제외하지 않음
    if in_any(u, EXCLUDE_PUNCT_SYMBOL_RANGES) and (not in_any(u, DIGIT_RANGES)):
        return False
    return True

def worth(g):
    try: return g is not None and g.isWorthOutputting()
    except Exception: return False

def ps_sanitize(name: str) -> str:
    s = name.replace(" ", "")
    s = re.sub(r"[^A-Za-z0-9\-]", "", s)
    return s if s else "Font"

def apply_variant(cfg):
    global BASE_FONT_PATH, KOREAN_FONT_PATH, JAPANESE_FONT_PATH, DIGIT_FONT_PATH
    global OUT_FONT_PATH, OUT_FAMILY_NAME, OUT_STYLE_NAME, LEGACY_STYLE_NAME
    global OUT_PS_NAME, OUT_VERSION_STR, OUT_FONTNAME
    BASE_FONT_PATH = cfg["base_font_path"]
    KOREAN_FONT_PATH = cfg["korean_font_path"]
    JAPANESE_FONT_PATH = cfg["japanese_font_path"]
    DIGIT_FONT_PATH = cfg["digit_font_path"]
    OUT_FONT_PATH = cfg["out_font_path"]
    OUT_FAMILY_NAME = cfg["out_family_name"]
    OUT_STYLE_NAME = cfg["out_style_name"]
    LEGACY_STYLE_NAME = cfg["legacy_style_name"]
    OUT_PS_NAME = cfg["out_ps_name"]
    OUT_VERSION_STR = cfg["out_version_str"]
    OUT_FONTNAME = ps_sanitize(OUT_PS_NAME)

apply_variant(FONT_VARIANTS[0])

@contextlib.contextmanager
def suppress_stderr(enabled: bool):
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
    with suppress_stderr(SILENCE_FONTFORGE_WARNINGS):
        f = fontforge.open(path, ("hidewindow", "alltables"))
    # ✅ CID는 reencode 하지 않음
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

def set_names(f):
    f.familyname = OUT_FAMILY_NAME
    f.fullname   = f"{OUT_FAMILY_NAME} {OUT_STYLE_NAME}"
    f.fontname   = OUT_FONTNAME
    try:
        f.sfnt_names = ()
    except Exception:
        pass
    uid = f"{OUT_FONTNAME};{OUT_VERSION_STR}"
    def add(lang, nid, s):
        try: f.appendSFNTName(lang, nid, s)
        except Exception: pass
    add("English (US)", 1,  OUT_FAMILY_NAME)
    add("English (US)", 2,  LEGACY_STYLE_NAME)
    add("English (US)", 3,  uid)
    add("English (US)", 4,  f"{OUT_FAMILY_NAME} {OUT_STYLE_NAME}")
    add("English (US)", 5,  OUT_VERSION_STR)
    add("English (US)", 6,  OUT_FONTNAME)
    add("English (US)", 16, OUT_FAMILY_NAME)
    add("English (US)", 17, OUT_STYLE_NAME)

def stage_progress(stage_tag: str, i: int, total: int, extra: str = ""):
    if total <= 0: return
    if i == total or (i % PROGRESS_EVERY == 0):
        pct = (i * 100.0) / float(total)
        msg = f"\r[{stage_tag}] {i}/{total} ({pct:.1f}%)"
        if extra:
            msg += " " + extra
        print(msg, flush=True, end="")

def maybe_gc(i: int):
    if GC_EVERY <= 0: return
    if (i % GC_EVERY) != 0: return
    try:
        fontforge.garbageCollect()
    except Exception:
        pass

_CID_SLOT_CACHE = {}

def _cid_slot_map(font, subidx: int):
    # CID 폰트는 findEncodingSlot이 자주 segfault를 유발하므로 캐시된 맵을 사용.
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
    except Exception: return -1

def has_glyph(font, u: int) -> bool:
    s = find_slot(font, u)
    if s == -1: return False
    try: return worth(font[s])
    except Exception: return False

def iter_ranges(ranges):
    for a,b in ranges:
        for u in range(a, b+1):
            yield u

def clear_anchors_if_needed(g):
    if not NORMALIZE_ANCHORS:
        return
    try:
        g.anchorPoints = None
    except Exception:
        pass

# =========================
# CID subfont selection
# =========================
def get_cid_subfont_names(font):
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
    idx = {}
    for i, n in get_cid_subfont_names(font):
        idx[n] = i
    return idx

def pick_cid_indices_by_patterns(name_index, patterns):
    out = []
    for pat in patterns:
        for name, i in name_index.items():
            if pat in name:
                out.append(i)
    seen = set()
    uniq = []
    for i in out:
        if i in seen: continue
        seen.add(i)
        uniq.append(i)
    return uniq

def cid_preferred_indices(name_index, u: int):
    # halfwidth-kana 최우선
    if 0xFF65 <= u <= 0xFF9F:
        return pick_cid_indices_by_patterns(name_index, ["HWidth", "HKana", "Kana", "Generic"])
    if in_any(u, KANA_RANGES):
        return pick_cid_indices_by_patterns(name_index, ["HKana", "Kana", "VKana", "Generic"])
    if in_any(u, CJK_IDEOGRAPH_RANGES):
        return pick_cid_indices_by_patterns(name_index, ["Ideographs", "ProportionalCJK", "HWidthCJK", "Generic"])
    return pick_cid_indices_by_patterns(name_index, ["Generic"])

def resolve_src_slot_cid(src_font, u: int, name_index):
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
# Copy / Bake (int selection only)
# =========================
def copy_from_src(src_font, dst_font, u: int, cid_name_index=None):
    """
    return (src_width) if copied else None
    """
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
                try: src_font.cidsubfont = saved
                except Exception: pass
            return None
        src_w = int(sg.width)
    except Exception:
        if saved is not None:
            try: src_font.cidsubfont = saved
            except Exception: pass
        return None

    # ✅ selection은 int만
    src_font.selection.none()
    src_font.selection.select(int(slot))
    src_font.copy()

    dg = dst_font.createChar(u)
    dg.clear()

    dst_font.selection.none()
    dst_font.selection.select(int(dg.encoding))
    dst_font.paste()

    dg.unicode = u
    try: dg.altuni = None
    except Exception: pass

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
    if sx == 1.0 and sy == 1.0:
        return
    font.selection.all()
    try:
        font.transform(psMat.scale(sx, sy), ("round", "simplePos", "kernClasses"))
    except Exception:
        font.transform(psMat.scale(sx, sy))
    font.selection.none()

# =========================
# Pretendard JP 제거(강제)
# =========================
def unmap_unicode_and_altuni(g):
    try: g.unicode = -1
    except Exception: pass
    try: g.altuni = None
    except Exception: pass

def strip_altuni_entries(g, should_remove_u):
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
    removed_map = 0
    cleared = 0

    def should_remove(u: int) -> bool:
        return in_any(u, JP_TARGET_RANGES) and jp_allowed(u)

    # 1) cmap(유니코드/altuni) 제거
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

        if (scanned % (PROGRESS_EVERY * 2)) == 0:
            print(f"\r[0] base JP unmap scanned={scanned} removed={removed_map}", flush=True, end="")

    # 2) 해당 유니코드 슬롯(있으면) outline clear → Pretendard 가나/한자 “눈에 보이게” 제거
    for u in iter_ranges(JP_TARGET_RANGES):
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
# always-on alternates + GSUB 제거
# =========================
def overwrite_outline_same_font(font, dst_g, src_g):
    keep_u = dst_g.unicode
    keep_w = dst_g.width
    dst_g.clear()
    font.selection.none(); font.selection.select(int(src_g.encoding)); font.copy()
    font.selection.none(); font.selection.select(int(dst_g.encoding)); font.paste()
    dst_g.unicode = keep_u
    dst_g.width = keep_w
    try: dst_g.altuni = None
    except Exception: pass

def bake_single_glyph_alternates(dst_font):
    suffixes = list(ALWAYS_ON_SS) + list(ALWAYS_ON_EXTRA_SUFFIX)
    if ALWAYS_ON_SWASH:
        suffixes.append("swsh")

    if ALWAYS_ON_SLASH_ZERO:
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

def build_one():
    # =========================
    # Build
    # =========================
    t_all = now()

    base = open_font(BASE_FONT_PATH)
    set_names(base)

    BASE_UPM = int(base.em)
    KO_DY = int(round((BASELINE_KO_PCT / 100.0) * BASE_UPM))

    # ✅ pre-scale (마지막에 global base scale 1회)
    JP_PRE_X    = SCALE_JP_X    / SCALE_BASE_X
    JP_PRE_Y    = SCALE_JP_Y    / SCALE_BASE_Y
    DIGIT_PRE_X = SCALE_DIGIT_X / SCALE_BASE_X
    DIGIT_PRE_Y = SCALE_DIGIT_Y / SCALE_BASE_Y
    KO_PRE_X    = SCALE_KO_X    / SCALE_BASE_X
    KO_PRE_Y    = SCALE_KO_Y    / SCALE_BASE_Y

    # [0] Pretendard JP(가나/한자) 제거
    t = now()
    rm_map, cleared = remove_base_jp_coverage_and_clear(base)
    print(f"[0] base JP removed_map={rm_map} cleared_slots={cleared} elapsed={now()-t:.2f}s", flush=True)

    # [1] digits
    if PRESERVE_DIGITS:
        print(f"[1] digits skipped!", flush=True)
    else:
        t = now()
        lato = open_font(DIGIT_FONT_PATH)
        LATO_UPM = int(lato.em)

        # 실제 존재하는 digit만 스캔(altuni 포함) 대신: 범위가 작으니 전수
        digits = [u for u in iter_ranges(DIGIT_RANGES)]
        total = len(digits)
        for i, u in enumerate(digits, 1):
            sw = copy_from_src(lato, base, u, cid_name_index=None)
            if sw is not None:
                ratio = float(BASE_UPM) / float(LATO_UPM)
                sx_total = ratio * DIGIT_PRE_X
                sy_total = ratio * DIGIT_PRE_Y
                bake(base, u, sx_total, sy_total, 0, sw * sx_total)
            stage_progress("1 digits", i, total)
            maybe_gc(i)
        lato.close()

        # fullwidth digits 없으면 ASCII에서 복제
        for d in range(10):
            u_ascii = 0x0030 + d
            u_full  = 0xFF10 + d
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

    # [2] korean (Hangul + Enclosed)
    t = now()
    ko = open_font(KOREAN_FONT_PATH)
    KO_UPM = int(ko.em)

    ko_targets = list(iter_ranges(HANGUL_MAIN_RANGES)) + list(iter_ranges(ENCLOSED_RANGES))
    total = len(ko_targets)
    for i, u in enumerate(ko_targets, 1):
        sw = copy_from_src(ko, base, u, cid_name_index=None)
        if sw is not None:
            ratio = float(BASE_UPM) / float(KO_UPM)
            sx_total = ratio * KO_PRE_X
            sy_total = ratio * KO_PRE_Y
            dy = KO_DY if (0xAC00 <= u <= 0xD7A3) else 0
            bake(base, u, sx_total, sy_total, dy, sw * sx_total)
        stage_progress("2 korean", i, total)
        maybe_gc(i)
    ko.close()
    print(f"\n[2] korean elapsed={now()-t:.2f}s", flush=True)

    # [3] japanese (CID 직접 발췌: Kana/HKana/HWidth/Ideographs 우선)
    t = now()
    jp = open_font(JAPANESE_FONT_PATH)
    JP_UPM = int(jp.em)
    jp_idx = build_cid_name_index(jp)

    # print("[AUDIT] resolve ・:", resolve_src_slot_cid(jp, 0x30FB, jp_idx), flush=True)

    # 디버그: 서브폰트 목록(필요하면)
    # for i,n in get_cid_subfont_names(jp):
    #     print(f"[JP] subfont {i}: {n}", flush=True)

    jp_targets = [u for u in iter_ranges(JP_TARGET_RANGES) if jp_allowed(u)]
    total = len(jp_targets)
    repl = 0
    for i, u in enumerate(jp_targets, 1):
        # digits/hangul은 건드리지 않음
        if in_any(u, DIGIT_RANGES) or in_any(u, HANGUL_MAIN_RANGES):
            stage_progress("3 japanese", i, total, extra=f"replaced={repl}")
            continue

        sw = copy_from_src(jp, base, u, cid_name_index=jp_idx)

        if sw is not None:
            ratio = float(BASE_UPM) / float(JP_UPM)
            sx_total = ratio * JP_PRE_X
            sy_total = ratio * JP_PRE_Y
            bake(base, u, sx_total, sy_total, 0, sw * sx_total)
            repl += 1

        stage_progress("3 japanese", i, total, extra=f"replaced={repl}")
        maybe_gc(i)

    print(f"\n[3] japanese replaced={repl}/{total} elapsed={now()-t:.2f}s", flush=True)

    filled_extra = 0
    for u in sorted(JP_EXTRA_SET):
        if in_any(u, DIGIT_RANGES) or in_any(u, HANGUL_MAIN_RANGES):
            continue

        if (not JP_EXTRA_OVERWRITE) and has_glyph(base, u):
            continue

        sw = copy_from_src(jp, base, u, cid_name_index=jp_idx)
        if sw is None:
            continue

        ratio = float(BASE_UPM) / float(JP_UPM)
        sx_total = ratio * JP_PRE_X
        sy_total = ratio * JP_PRE_Y
        bake(base, u, sx_total, sy_total, 0, sw * sx_total)
        filled_extra += 1

    jp.close()
    print(f"[3] jp extra filled={filled_extra} (whitelist)", flush=True)


    # [4] always-on alternates + GSUB 일부 제거(리가쳐 유지)
    t = now()
    bake_single_glyph_alternates(base)
    removed = remove_gsub_lookups_by_feature_tags(base, REMOVE_GSUB_FEATURES)
    print(f"[4] alternates elapsed={now()-t:.2f}s", flush=True)
    print(f"[4] GSUB removed={removed}", flush=True)

    # [5] global base scale (GPOS/Kerning 포함)
    t = now()
    transform_entire_font(base, SCALE_BASE_X, SCALE_BASE_Y)
    print(f"[5] global base scale elapsed={now()-t:.2f}s", flush=True)

    # audit
    print("[AUDIT] こ(U+3053):", has_glyph(base, 0x3053), flush=True)
    print("[AUDIT] ｱ(U+FF71):", has_glyph(base, 0xFF71), flush=True)
    print("[AUDIT] 漢(U+6F22):", has_glyph(base, 0x6F22), flush=True)
    print("[AUDIT] ㉠(U+3260):", has_glyph(base, 0x3260), flush=True)

    # generate
    t = now()
    with suppress_stderr(SILENCE_FONTFORGE_WARNINGS):
        base.generate(OUT_FONT_PATH)
    base.close()
    print(f"[6] generate elapsed={now()-t:.2f}s", flush=True)
    print(f"DONE: {OUT_FONT_PATH} total={now()-t_all:.2f}s", flush=True)

if __name__ == "__main__":
    for cfg in FONT_VARIANTS:
        apply_variant(cfg)
        build_one()
