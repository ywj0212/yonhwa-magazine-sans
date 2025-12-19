# Yonhwa Magazine Sans

Composite CJK/Latin/Korean/Japanese font built from multiple upstream sources. Current outputs: Light, Medium, Bold.

## What this repo does
- Merges Pretendard (base), Gmarket Sans (Hangul), Noto Sans CJK JP (JP/CJK), and Lato (digits).
- Applies always-on OpenType alternates (case, ssXX, salt, etc.) by baking GSUB into the base glyphs so apps without OT support still render alternates.
- Scales/positions per-script outlines to fit a common metrics frame; optionally nudges math/bracket/dash baselines and enclosed glyphs.
- Generates versioned TTFs into `dist/`.

## Prerequisites
- FontForge with Python bindings in PATH (`fontforge -lang=py -v`).
- Python 3.11+ (3.14 used here) with `fontTools` installed (already vendored in `venv` if you use `run.sh`).
- Upstream font files present in `font/` (paths configured in `config.py`).

## How to build
```bash
./run.sh   # activates venv, runs FontForge with main.py
```
Outputs land in `dist/` as `YonhwaMagazineSans-<Style>-<OUT_VERSION_STR>.ttf`.

## Configuration (`config.py`)
- `FONT_VARIANTS`: per-style source paths and names (base/korean/japanese/digit fonts, output names).
- Scaling & baselines: `SCALE_BASE_*`, `SCALE_KO_*`, `BASELINE_KO_PCT`, `SCALE_ENCLOSED_*`, `BASELINE_ENCLOSED_PCT`, `SCALE_JP_*`, `SCALE_DIGIT_*`.
- Alternates: `ALWAYS_ON_FEATURE_TAGS`, `ALWAYS_ON_SS`, `ALWAYS_ON_EXTRA_SUFFIX`, `ALWAYS_ON_SWASH`, `ALWAYS_ON_SLASH_ZERO`, `QUOTE_FIX_CODEPOINTS`.
- Baseline tweaks: `CASE_MATH_BASELINE_OFFSET`, `CASE_BRACKET_BASELINE_OFFSET`, `CASE_DASH_ARROW_BASELINE_OFFSET` (percent of UPM).
- JP extras/whitelist: `JP_EXTRA_SET`, `JP_EXTRA_OVERWRITE`.
- Output: `OUT_FAMILY_NAME`, `OUT_VERSION_STR`, `OUTPUT_DIR`.

## Code layout
- `pipeline.py`: orchestrates build stages.
- `font_io.py`: opening fonts, naming, stderr suppression.
- `cid.py`: CID-safe slot resolution and subfont helpers.
- `geometry.py`: worth check, bake, global transform, glyph presence.
- `glyph_copy.py`: copying glyphs between fonts, clearing JP coverage.
- `features.py`: GSUB load/bake, baseline tweaks, quote refresh.
- `ranges.py`: range helpers and JP eligibility.
- `unicode_ranges.py`: Unicode range definitions and JP extra builder.
- `main.py`: entrypoint that runs `build_all()`.

## Upstream components (OFL-1.1)
- Lato
- Noto Sans CJK JP
- Gmarket Sans
- Pretendard

See `THIRD_PARTY_NOTICES` for notices and `LICENSE`/`OFL_USAGE.md` for usage guidance. Yonhwa Magazine Sans is not endorsed by upstream authors; Reserved Font Names are not used as the primary name.***
