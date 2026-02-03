"""Path utilities for tool implementations."""

import os
import re
import unicodedata
from pathlib import Path

# Unicode spaces that should be normalized to regular space
UNICODE_SPACES = re.compile(r"[\u00A0\u2000-\u200A\u202F\u205F\u3000]")
NARROW_NO_BREAK_SPACE = "\u202F"


def _normalize_unicode_spaces(s: str) -> str:
    """Replace various unicode space characters with regular space."""
    return UNICODE_SPACES.sub(" ", s)


def _try_macos_screenshot_path(file_path: str) -> str:
    """Try macOS screenshot path variant with narrow no-break space before AM/PM."""
    return re.sub(r" (AM|PM)\.", f"{NARROW_NO_BREAK_SPACE}\\1.", file_path)


def _try_nfd_variant(file_path: str) -> str:
    """Try NFD (decomposed) form - macOS stores filenames in NFD."""
    return unicodedata.normalize("NFD", file_path)


def _try_curly_quote_variant(file_path: str) -> str:
    """
    Try curly quote variant.
    macOS uses U+2019 (right single quotation mark) in screenshot names like "Capture d'écran"
    Users typically type U+0027 (straight apostrophe)
    """
    return file_path.replace("'", "\u2019")


def _file_exists(file_path: str) -> bool:
    """Check if a file exists."""
    return os.path.exists(file_path)


def expand_path(file_path: str) -> str:
    """Expand ~ to home directory and normalize unicode spaces."""
    normalized = _normalize_unicode_spaces(file_path)
    if normalized == "~":
        return str(Path.home())
    if normalized.startswith("~/"):
        return str(Path.home() / normalized[2:])
    return normalized


def resolve_to_cwd(file_path: str, cwd: str | Path) -> str:
    """
    Resolve a path relative to the given cwd.
    Handles ~ expansion and absolute paths.
    """
    expanded = expand_path(file_path)
    expanded_path = Path(expanded)

    if expanded_path.is_absolute():
        return str(expanded_path)

    return str(Path(cwd) / expanded)


def resolve_read_path(file_path: str, cwd: str | Path) -> str:
    """
    Resolve a path for reading, trying various filename variants.
    Handles macOS screenshot naming quirks.
    """
    resolved = resolve_to_cwd(file_path, cwd)

    if _file_exists(resolved):
        return resolved

    # Try macOS AM/PM variant (narrow no-break space before AM/PM)
    am_pm_variant = _try_macos_screenshot_path(resolved)
    if am_pm_variant != resolved and _file_exists(am_pm_variant):
        return am_pm_variant

    # Try NFD variant (macOS stores filenames in NFD form)
    nfd_variant = _try_nfd_variant(resolved)
    if nfd_variant != resolved and _file_exists(nfd_variant):
        return nfd_variant

    # Try curly quote variant (macOS uses U+2019 in screenshot names)
    curly_variant = _try_curly_quote_variant(resolved)
    if curly_variant != resolved and _file_exists(curly_variant):
        return curly_variant

    # Try combined NFD + curly quote (for French macOS screenshots like "Capture d'écran")
    nfd_curly_variant = _try_curly_quote_variant(nfd_variant)
    if nfd_curly_variant != resolved and _file_exists(nfd_curly_variant):
        return nfd_curly_variant

    return resolved
