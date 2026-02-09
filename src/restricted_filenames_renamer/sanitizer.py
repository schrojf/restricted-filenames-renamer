"""Pure functions for sanitizing filenames to be portable across operating systems.

This module contains no filesystem access — only string transformations.

By default, each restricted character is replaced with its Unicode equivalent
(fullwidth characters for Windows-forbidden chars, Unicode Control Pictures
for control chars), inspired by rclone's encoding system.  An optional
``replace_char`` override replaces all restricted characters with a single
character instead.

The sanitization pipeline:
  1. Replace forbidden characters (Windows-restricted + control chars)
  2. Replace trailing dots and spaces (Windows silently strips these)
  3. Handle Windows reserved device names (CON, PRN, AUX, NUL, COM0-9, LPT0-9)
  4. Truncate names exceeding the maximum length (preserving extension)
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Unicode replacement mapping (rclone-style)
# ---------------------------------------------------------------------------

# Windows-forbidden characters → fullwidth Unicode equivalents.
_FORBIDDEN_CHAR_MAP: dict[str, str] = {
    "\\": "\uff3c",  # ＼ FULLWIDTH REVERSE SOLIDUS
    "/": "\uff0f",  # ／ FULLWIDTH SOLIDUS
    ":": "\uff1a",  # ： FULLWIDTH COLON
    "*": "\uff0a",  # ＊ FULLWIDTH ASTERISK
    "?": "\uff1f",  # ？ FULLWIDTH QUESTION MARK
    '"': "\uff02",  # ＂ FULLWIDTH QUOTATION MARK
    "<": "\uff1c",  # ＜ FULLWIDTH LESS-THAN SIGN
    ">": "\uff1e",  # ＞ FULLWIDTH GREATER-THAN SIGN
    "|": "\uff5c",  # ｜ FULLWIDTH VERTICAL LINE
}

# ASCII control characters 0x00-0x1F → Unicode Control Pictures U+2400-U+241F.
_CONTROL_CHAR_MAP: dict[str, str] = {chr(c): chr(0x2400 + c) for c in range(0x00, 0x20)}

# Combined mapping: every restricted character → its Unicode replacement.
UNICODE_CHAR_MAP: dict[str, str] = {**_CONTROL_CHAR_MAP, **_FORBIDDEN_CHAR_MAP}

# Trailing-character replacements.
UNICODE_DOT_REPLACEMENT: str = "\uff0e"  # ．FULLWIDTH FULL STOP
UNICODE_SPACE_REPLACEMENT: str = "\u2420"  # ␠ SYMBOL FOR SPACE

# ---------------------------------------------------------------------------
# Character sets (for validation and quick checks)
# ---------------------------------------------------------------------------

FORBIDDEN_CHARS: frozenset[str] = frozenset(_FORBIDDEN_CHAR_MAP)
CONTROL_CHARS: frozenset[str] = frozenset(_CONTROL_CHAR_MAP)
ALL_RESTRICTED_CHARS: frozenset[str] = FORBIDDEN_CHARS | CONTROL_CHARS

# Pre-compiled regex matching any single restricted character.
_RESTRICTED_CHAR_RE: re.Pattern[str] = re.compile(
    "[" + re.escape("".join(sorted(ALL_RESTRICTED_CHARS))) + "]"
)

# Windows reserved device names (case-insensitive, exact stem match).
_RESERVED_NAMES_RE: re.Pattern[str] = re.compile(
    r"^(CON|PRN|AUX|NUL|COM\d|LPT\d)$",
    re.IGNORECASE,
)

# Trailing dots and/or spaces.
_TRAILING_DOTS_SPACES_RE: re.Pattern[str] = re.compile(r"[. ]+$")

DEFAULT_MAX_NAME_LENGTH: int = 255
WINDOWS_MAX_PATH: int = 260


def replace_forbidden_chars(name: str, replace_char: str | None = None) -> tuple[str, list[str]]:
    """Replace Windows-forbidden and control characters.

    When *replace_char* is ``None`` (the default), each character is replaced
    with its Unicode equivalent (fullwidth or Control Picture).  When a
    single character is given, it is used for all replacements.

    Returns ``(sanitized_name, issues)``.
    """
    issues: list[str] = []

    if replace_char is not None:
        result = _RESTRICTED_CHAR_RE.sub(replace_char, name)
    else:
        result = _replace_chars_unicode(name)

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


def strip_trailing_dots_spaces(name: str, replace_char: str | None = None) -> tuple[str, list[str]]:
    """Handle trailing dots and spaces that Windows silently strips.

    When *replace_char* is ``None`` (the default), trailing dots are replaced
    with ``．`` (fullwidth full stop) and trailing spaces with ``␠`` (symbol
    for space).  When a single character is given, trailing dots and spaces
    are stripped instead, and *replace_char* is used as fallback if the name
    becomes empty.

    Returns ``(sanitized_name, issues)``.
    """
    issues: list[str] = []
    match = _TRAILING_DOTS_SPACES_RE.search(name)
    if not match:
        return name, issues

    trailing = match.group()
    prefix = name[: match.start()]

    if replace_char is not None:
        # Simple mode: strip trailing chars.
        result = prefix
        issues.append(f"Stripped trailing characters: {trailing!r}")
        if not result:
            result = replace_char
            issues.append("Name was empty after stripping; replaced with fallback character")
    else:
        # Unicode mode: replace each trailing char with its Unicode equivalent.
        replaced_trailing = trailing.replace(".", UNICODE_DOT_REPLACEMENT).replace(
            " ", UNICODE_SPACE_REPLACEMENT
        )
        result = prefix + replaced_trailing
        issues.append(f"Replaced trailing characters: {trailing!r}")

    return result, issues


def handle_reserved_names(name: str, prefix_char: str = "_") -> tuple[str, list[str]]:
    """Prefix Windows reserved device names with *prefix_char*.

    Handles bare names (``CON`` -> ``_CON``) and names with extensions
    (``CON.txt`` -> ``_CON.txt``).  The match is case-insensitive on the
    stem (the part before the first dot).
    Returns ``(sanitized_name, issues)``.
    """
    issues: list[str] = []
    dot_idx = name.find(".")
    stem = name[:dot_idx] if dot_idx != -1 else name

    if _RESERVED_NAMES_RE.match(stem):
        result = prefix_char + name
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

    dot_idx = name.rfind(".")
    if dot_idx <= 0:
        return name[:max_length], issues

    stem = name[:dot_idx]
    ext = name[dot_idx:]

    if len(ext) >= max_length:
        return name[:max_length], issues

    max_stem = max_length - len(ext)
    return stem[:max_stem] + ext, issues


def sanitize_name(
    name: str,
    *,
    replace_char: str | None = None,
    max_length: int = DEFAULT_MAX_NAME_LENGTH,
) -> tuple[str, list[str]]:
    """Run the full sanitization pipeline on a single filename or directory name.

    When *replace_char* is ``None`` (the default), restricted characters are
    replaced with their Unicode equivalents (rclone-style).  When a single
    character is provided, it is used as a simple replacement for all restricted
    characters.

    Pipeline order:
      1. Replace forbidden / control characters
      2. Replace trailing dots and spaces
      3. Handle Windows reserved names (always prefixed with ``_``)
      4. Truncate if exceeding *max_length*

    Returns ``(sanitized_name, all_issues)``.
    """
    all_issues: list[str] = []

    name, issues = replace_forbidden_chars(name, replace_char)
    all_issues.extend(issues)

    name, issues = strip_trailing_dots_spaces(name, replace_char)
    all_issues.extend(issues)

    name, issues = handle_reserved_names(name)
    all_issues.extend(issues)

    name, issues = truncate_name(name, max_length)
    all_issues.extend(issues)

    return name, all_issues


def is_name_safe(name: str, *, max_length: int = DEFAULT_MAX_NAME_LENGTH) -> bool:
    """Return ``True`` if *name* requires no sanitization."""
    sanitized, _ = sanitize_name(name, max_length=max_length)
    return sanitized == name


def _replace_chars_unicode(name: str) -> str:
    """Replace each restricted character with its Unicode equivalent."""
    return "".join(UNICODE_CHAR_MAP.get(c, c) for c in name)
