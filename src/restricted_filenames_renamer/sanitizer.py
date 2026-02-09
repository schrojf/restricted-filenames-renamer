"""Pure functions for sanitizing filenames to be portable across operating systems.

This module contains no filesystem access — only string transformations.
The sanitization pipeline:
  1. Replace forbidden characters (Windows-restricted + control chars)
  2. Strip trailing dots and spaces (Windows silently strips these)
  3. Handle Windows reserved device names (CON, PRN, AUX, NUL, COM0-9, LPT0-9)
  4. Truncate names exceeding the maximum length (preserving extension)
"""

from __future__ import annotations

import re

# Windows-forbidden characters in filenames.
FORBIDDEN_CHARS: frozenset[str] = frozenset('\\/:*?"<>|')

# ASCII control characters 0x00 through 0x1F.
CONTROL_CHARS: frozenset[str] = frozenset(chr(c) for c in range(0x00, 0x20))

# Union of all characters that must be replaced.
ALL_RESTRICTED_CHARS: frozenset[str] = FORBIDDEN_CHARS | CONTROL_CHARS

# Pre-compiled regex matching any single restricted character.
_RESTRICTED_CHAR_RE: re.Pattern[str] = re.compile(
    "[" + re.escape("".join(sorted(ALL_RESTRICTED_CHARS))) + "]"
)

# Windows reserved device names (case-insensitive, exact stem match).
# Covers: CON, PRN, AUX, NUL, COM0-COM9, LPT0-LPT9.
_RESERVED_NAMES_RE: re.Pattern[str] = re.compile(
    r"^(CON|PRN|AUX|NUL|COM\d|LPT\d)$",
    re.IGNORECASE,
)

# Trailing dots and/or spaces.
_TRAILING_DOTS_SPACES_RE: re.Pattern[str] = re.compile(r"[. ]+$")

DEFAULT_REPLACE_CHAR: str = "_"
DEFAULT_MAX_NAME_LENGTH: int = 255
WINDOWS_MAX_PATH: int = 260


def replace_forbidden_chars(
    name: str, replace_char: str = DEFAULT_REPLACE_CHAR
) -> tuple[str, list[str]]:
    """Replace Windows-forbidden and control characters with *replace_char*.

    Returns ``(sanitized_name, issues)`` where *issues* lists each
    category of character that was replaced.
    """
    issues: list[str] = []
    result = _RESTRICTED_CHAR_RE.sub(replace_char, name)
    if result != name:
        found_control = any(c in CONTROL_CHARS for c in name if c not in FORBIDDEN_CHARS)
        found_forbidden = any(c in FORBIDDEN_CHARS for c in name)
        parts: list[str] = []
        if found_forbidden:
            chars = sorted({c for c in name if c in FORBIDDEN_CHARS})
            parts.append(f"forbidden characters {chars!r}")
        if found_control:
            codes = sorted(
                f"0x{ord(c):02X}" for c in name if c in CONTROL_CHARS and c not in FORBIDDEN_CHARS
            )
            parts.append(f"control characters {codes}")
        issues.append(f"Replaced {', '.join(parts)}")
    return result, issues


def strip_trailing_dots_spaces(
    name: str, replace_char: str = DEFAULT_REPLACE_CHAR
) -> tuple[str, list[str]]:
    """Remove trailing dots and spaces that Windows silently strips.

    If the result would be empty (e.g. ``"..."``), returns *replace_char* instead.
    Returns ``(sanitized_name, issues)``.
    """
    issues: list[str] = []
    result = _TRAILING_DOTS_SPACES_RE.sub("", name)
    if result != name:
        stripped = name[len(result) :]
        issues.append(f"Stripped trailing characters: {stripped!r}")
    if not result:
        result = replace_char
        issues.append("Name was empty after stripping; replaced with fallback character")
    return result, issues


def handle_reserved_names(
    name: str, replace_char: str = DEFAULT_REPLACE_CHAR
) -> tuple[str, list[str]]:
    """Prefix Windows reserved device names with *replace_char*.

    Handles bare names (``CON`` -> ``_CON``) and names with extensions
    (``CON.txt`` -> ``_CON.txt``).  The match is case-insensitive on the
    stem (the part before the first dot).
    Returns ``(sanitized_name, issues)``.
    """
    issues: list[str] = []
    # Split at the first dot to get the stem.
    dot_idx = name.find(".")
    stem = name[:dot_idx] if dot_idx != -1 else name

    if _RESERVED_NAMES_RE.match(stem):
        result = replace_char + name
        issues.append(f"Reserved Windows device name: {stem!r}")
        return result, issues

    return name, issues


def truncate_name(name: str, max_length: int = DEFAULT_MAX_NAME_LENGTH) -> tuple[str, list[str]]:
    """Truncate *name* to *max_length* characters, preserving the file extension.

    If the extension alone exceeds *max_length*, the extension is truncated too.
    Returns ``(truncated_name, issues)``.
    """
    if len(name) <= max_length:
        return name, []

    issues = [f"Name length {len(name)} exceeds limit {max_length}; truncated"]

    # Split at the last dot to separate stem and extension.
    dot_idx = name.rfind(".")
    if dot_idx <= 0:
        # No extension (or hidden file with no further extension like ".longname").
        return name[:max_length], issues

    stem = name[:dot_idx]
    ext = name[dot_idx:]  # includes the dot

    if len(ext) >= max_length:
        # Extension itself is too long — truncate everything.
        return name[:max_length], issues

    # Truncate the stem to fit within max_length alongside the extension.
    max_stem = max_length - len(ext)
    return stem[:max_stem] + ext, issues


def sanitize_name(
    name: str,
    *,
    replace_char: str = DEFAULT_REPLACE_CHAR,
    max_length: int = DEFAULT_MAX_NAME_LENGTH,
) -> tuple[str, list[str]]:
    """Run the full sanitization pipeline on a single filename or directory name.

    Pipeline order:
      1. Replace forbidden / control characters
      2. Strip trailing dots and spaces
      3. Handle Windows reserved names
      4. Truncate if exceeding *max_length*

    Returns ``(sanitized_name, all_issues)``.
    """
    all_issues: list[str] = []

    name, issues = replace_forbidden_chars(name, replace_char)
    all_issues.extend(issues)

    name, issues = strip_trailing_dots_spaces(name, replace_char)
    all_issues.extend(issues)

    name, issues = handle_reserved_names(name, replace_char)
    all_issues.extend(issues)

    name, issues = truncate_name(name, max_length)
    all_issues.extend(issues)

    return name, all_issues


def is_name_safe(name: str, *, max_length: int = DEFAULT_MAX_NAME_LENGTH) -> bool:
    """Return ``True`` if *name* requires no sanitization."""
    sanitized, _ = sanitize_name(name, max_length=max_length)
    return sanitized == name
