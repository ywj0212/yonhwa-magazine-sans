"""I/O helpers: opening fonts, naming, and stderr suppression."""

from typing import Dict
import contextlib
import os
import re
import sys

import fontforge  # type: ignore

import config as cfg


@contextlib.contextmanager
def suppress_stderr(enabled: bool):
    """Context manager to silence stderr when noisy FontForge warnings occur."""
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


def ps_sanitize(name: str) -> str:
    """Normalize a PostScript name to ASCII-safe characters."""
    s = name.replace(" ", "")
    s = re.sub(r"[^A-Za-z0-9-]", "", s)
    return s if s else "Font"


def open_font(path: str, flatten_cid: bool = False):
    """Open a font file and normalize encoding where safe.

    flatten_cid is accepted for API compatibility; CID handling relies on
    FontForge's native open behavior.
    """
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


def set_names(f, variant: Dict[str, str]) -> None:
    """Apply family/style/version naming to the output font."""
    out_fontname = ps_sanitize(variant["out_ps_name"])
    version_label = f"Version {cfg.OUT_VERSION_STR}"
    f.familyname = cfg.OUT_FAMILY_NAME
    f.fullname = f"{cfg.OUT_FAMILY_NAME} {variant['out_style_name']}"
    f.fontname = out_fontname
    try:
        f.sfnt_names = ()
    except Exception:
        pass
    uid = f"{out_fontname};{version_label}"

    def add(lang, nid, s):
        try:
            f.appendSFNTName(lang, nid, s)
        except Exception:
            pass

    add("English (US)", 1, cfg.OUT_FAMILY_NAME)
    add("English (US)", 2, variant["legacy_style_name"])
    add("English (US)", 3, uid)
    add("English (US)", 4, f"{cfg.OUT_FAMILY_NAME} {variant['out_style_name']}")
    add("English (US)", 5, version_label)
    add("English (US)", 6, out_fontname)
    add("English (US)", 16, cfg.OUT_FAMILY_NAME)
    add("English (US)", 17, variant["out_style_name"])
