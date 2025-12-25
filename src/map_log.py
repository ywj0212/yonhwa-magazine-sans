"""Mapping issue logger for glyph copy diagnostics."""

from __future__ import annotations

from typing import Dict, Optional
import os
import time
import unicodedata

import config as cfg

_counts: Dict[str, int] = {}
_logged = 0


def _format_codepoint(u: int) -> str:
    """Format codepoint and glyph for logs."""
    try:
        ch = chr(u)
    except Exception:
        ch = ""
    if ch and ch.isprintable():
        try:
            name = unicodedata.name(ch)
        except Exception:
            name = "UNKNOWN"
        return f"U+{u:04X} '{ch}' {name}"
    return f"U+{u:04X}"


def _should_log() -> bool:
    if not cfg.LOG_MAPPING_ISSUES:
        return False
    if cfg.LOG_MAPPING_MAX_ENTRIES <= 0:
        return True
    return _logged < cfg.LOG_MAPPING_MAX_ENTRIES


def start_run() -> None:
    """Initialize the mapping log for this build."""
    if not cfg.LOG_MAPPING_ISSUES:
        return
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
    header = f"# mapping issues log ({cfg.OUT_VERSION_STR}) {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    with open(cfg.MAPPING_LOG_PATH, "w", encoding="utf-8") as f:
        f.write(header)


def count_event(kind: str) -> None:
    """Increment a summary counter without writing a log line."""
    _counts[kind] = _counts.get(kind, 0) + 1


def log_issue(kind: str, u: Optional[int] = None, detail: str = "") -> None:
    """Record a mapping issue with an optional codepoint and detail."""
    global _logged
    _counts[kind] = _counts.get(kind, 0) + 1
    if not cfg.LOG_MAPPING_VERBOSE:
        return
    if not _should_log():
        return
    prefix = f"[{kind}]"
    if u is not None:
        msg = _format_codepoint(u)
        line = f"{prefix} {msg}"
    else:
        line = prefix
    if detail:
        line += f" {detail}"
    with open(cfg.MAPPING_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    _logged += 1


def finish_run() -> None:
    """Append a summary section to the mapping log."""
    if not cfg.LOG_MAPPING_ISSUES:
        return
    with open(cfg.MAPPING_LOG_PATH, "a", encoding="utf-8") as f:
        f.write("\n# summary\n")
        for kind in sorted(_counts):
            f.write(f"{kind}={_counts[kind]}\n")
