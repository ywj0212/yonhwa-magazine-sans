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
# USER CONFIG (edit here)
# =========================
OUTPUT_DIR = "dist"

OUT_FAMILY_NAME = "Yonhwa Magazine Sans"
OUT_VERSION_STR = "25w51d"
FONT_VARIANTS = [
    {
        "base_font_path": "./font/Pretendard-Medium.otf",
        "korean_font_path": "./font/GmarketSansTTFMedium.ttf",
        "japanese_font_path": "./font/NotoSansCJKjp-Medium.otf",
        "digit_font_path": "./font/Lato-Semibold.ttf",
        "out_font_filename": "YonhwaMagazineSans-Medium.ttf",
        "out_style_name": "Medium",
        "legacy_style_name": "Regular",
        "out_ps_name": "Yonhwa Magazine Sans Medium",
    },
    {
        "base_font_path": "./font/Pretendard-ExtraBold.otf",
        "korean_font_path": "./font/GmarketSansTTFBold.ttf",
        "japanese_font_path": "./font/NotoSansCJKjp-Black.otf",
        "digit_font_path": "./font/Lato-Black.ttf",
        "out_font_filename": "YonhwaMagazineSans-Bold.ttf",
        "out_style_name": "Bold",
        "legacy_style_name": "Bold",
        "out_ps_name": "Yonhwa Magazine Sans Bold",
    },
    {
        "base_font_path": "./font/Pretendard-ExtraLight.otf",
        "korean_font_path": "./font/GmarketSansTTFLight.ttf",
        "japanese_font_path": "./font/NotoSansCJKjp-Light.otf",
        "digit_font_path": "./font/Lato-Light.ttf",
        "out_font_filename": "YonhwaMagazineSans-Light.ttf",
        "out_style_name": "Light",
        "legacy_style_name": "Light",
        "out_ps_name": "Yonhwa Magazine Sans Light",
    },
]

PRESERVE_DIGITS = False # If True, digits are not overwritten with Lato.

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

# === JP extra glyphs (Noto Sans CJK JP) ===
JP_EXTRA_OVERWRITE = False  # If True, forcefully overwrite with Noto Sans CJK JP
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
JP_EXTRA_SET = build_jp_extra_set(JP_EXTRA_GLYPHS_EXACT)

# =========================
# Advanced settings
# =========================
ALWAYS_ON_SS = ["ss01", "ss02", "ss03", "ss06", "ss08"]
ALWAYS_ON_SWASH = False
ALWAYS_ON_SLASH_ZERO = True
ALWAYS_ON_EXTRA_SUFFIX = []
# OpenType feature tags to force-apply and bake (e.g., jp04 = JIS2004).
ALWAYS_ON_FEATURE_TAGS = ["case"]

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

NORMALIZE_ANCHORS = True  # Reduce anchor/marker warning(removes anchor)
