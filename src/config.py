from unicode_ranges import (
    CJK_IDEOGRAPH_RANGES,
    DIGIT_RANGES,
    ENCLOSED_RANGES,
    EXCLUDE_PUNCT_SYMBOL_RANGES,
    HANGUL_MAIN_RANGES,
    JP_TARGET_RANGES,
    KANA_RANGES,
    build_jp_extra_set,
)

# =========================
# User-facing config (edit here)
# =========================
OUTPUT_DIR = "dist"

OUT_FAMILY_NAME = "Yonhwa Magazine Sans"
OUT_VERSION_STR = "25w51e"
FONT_VARIANTS = [
    {
        "base_font_path": "./src/font/Pretendard-Medium.otf",
        "korean_font_path": "./src/font/GmarketSansTTFMedium.ttf",
        "japanese_font_path": "./src/font/NotoSansCJKjp-Medium.otf",
        "digit_font_path": "./src/font/Lato-Semibold.ttf",
        "out_font_filename": "YonhwaMagazineSans-Medium.ttf",
        "out_style_name": "Medium",
        "legacy_style_name": "Regular",
        "out_ps_name": "Yonhwa Magazine Sans Medium",
    },
    {
        "base_font_path": "./src/font/Pretendard-ExtraBold.otf",
        "korean_font_path": "./src/font/GmarketSansTTFBold.ttf",
        "japanese_font_path": "./src/font/NotoSansCJKjp-Black.otf",
        "digit_font_path": "./src/font/Lato-Black.ttf",
        "out_font_filename": "YonhwaMagazineSans-Bold.ttf",
        "out_style_name": "Bold",
        "legacy_style_name": "Bold",
        "out_ps_name": "Yonhwa Magazine Sans Bold",
    },
    {
        "base_font_path": "./src/font/Pretendard-ExtraLight.otf",
        "korean_font_path": "./src/font/GmarketSansTTFLight.ttf",
        "japanese_font_path": "./src/font/NotoSansCJKjp-Light.otf",
        "digit_font_path": "./src/font/Lato-Light.ttf",
        "out_font_filename": "YonhwaMagazineSans-Light.ttf",
        "out_style_name": "Light",
        "legacy_style_name": "Light",
        "out_ps_name": "Yonhwa Magazine Sans Light",
    },
]

# If True, keep the base font's digits instead of overwriting with Lato.
PRESERVE_DIGITS = False

SCALE_BASE_X = 0.96
SCALE_BASE_Y = 1.00

SCALE_DIGIT_X = 0.96
SCALE_DIGIT_Y = 1.00

SCALE_KO_X = 0.94 * 0.94
SCALE_KO_Y = 0.94
BASELINE_KO_PCT = 5.5

SCALE_ENCLOSED_X = SCALE_KO_X * 0.8957
SCALE_ENCLOSED_Y = SCALE_KO_Y * 0.8957
BASELINE_ENCLOSED_PCT = 10

SCALE_JP_X = 0.9375 * 0.96
SCALE_JP_Y = 0.9375

# === JP extra glyph whitelist (Noto Sans CJK JP) ===
# If True, forcefully overwrite the base even when a glyph already exists.
JP_EXTRA_OVERWRITE = False
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
    "⇄⇆⇋⇌"
    "∩∪∴∵∝∟∠∃∀"
    "▫♤♧♢♡"
    "⊕⊗⊙⊠⊥⊖⊘"
    "┌┍┎┏┐┑┒┓└┕┖┗┘┙┚┛├┝┞┟┤┥┦┧"
    "┬┭┮┯┰┱┲┳┴┵┶┷┸┹┺┻┼┽┾┿╀╁╂╃╄╅╆╇╈╉╊╋"
    "▣▤▥▦▧▨▩▱✂"
    "ᆞᆢ"
)
JP_EXTRA_SET = build_jp_extra_set(JP_EXTRA_GLYPHS_EXACT)

# =========================
# Advanced settings
# =========================
ALWAYS_ON_SS = ["ss01", "ss02", "ss03", "ss06", "ss08"]
ALWAYS_ON_SWASH = False
ALWAYS_ON_SLASH_ZERO = True
ALWAYS_ON_EXTRA_SUFFIX = []
# OpenType feature tags to bake into base glyphs (e.g., jp04 = JIS2004).
ALWAYS_ON_FEATURE_TAGS = ["case"]
# Codepoint ranges that must never be overwritten by GSUB baking.
GSUB_PROTECT_RANGES = [
    (0x0020, 0x007E),  # Basic Latin
    (0x00A0, 0x00FF),  # Latin-1 Supplement
    (0x0100, 0x017F),  # Latin Extended-A
    (0x0180, 0x024F),  # Latin Extended-B
    (0x1E00, 0x1EFF),  # Latin Extended Additional
    (0x2000, 0x206F),  # General Punctuation (e.g., ‰)
    (0x20A0, 0x20CF),  # Currency Symbols
    (0x2100, 0x214F),  # Letterlike Symbols
    (0x2150, 0x218F),  # Number Forms (Roman numerals)
]

# Baseline tweaks (percent of UPM; positive moves glyphs upward).
# math symbols: − + ÷ ± × = ≠ ≈ ~ < > ≤ ≥ ∓ ∞ √ ∑ ∫ ∂ (excluding *)
CASE_MATH_BASELINE_OFFSET = 7.78
# halfwidth brackets / quotes: () <> {} [] « » ‹ ›
CASE_BRACKET_BASELINE_OFFSET = 7.78
# dashes/hyphens & arrows: - ‐ – — → ← ↕ ⟶ ⟵ ⟺ ⇐ ⇒
CASE_DASH_ARROW_BASELINE_OFFSET = 5.8

# Codepoints to refresh from the base font to fix bad outlines/widths.
QUOTE_FIX_CODEPOINTS = [0x2018, 0x2019, 0x201C, 0x201D]

REMOVE_GSUB_FEATURES = set(
    ALWAYS_ON_SS
    + ALWAYS_ON_EXTRA_SUFFIX
    + ALWAYS_ON_FEATURE_TAGS
    + (["swsh"] if ALWAYS_ON_SWASH else [])
)

SILENCE_FONTFORGE_WARNINGS = True
PROGRESS_EVERY = 100
GC_EVERY = 4000

# Drop anchors to avoid noisy FontForge warnings during copy/paste.
NORMALIZE_ANCHORS = True
