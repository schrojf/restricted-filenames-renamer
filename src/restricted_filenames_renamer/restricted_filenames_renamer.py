"""Public API — re-exports all public symbols from the package.

The package ``__init__.py`` re-exports everything from here via
``from .restricted_filenames_renamer import *``.
"""

from __future__ import annotations

# CLI entry point
from .cli import main

# Renamer — plan execution and logging
from .renamer import (
    execute_plan,
    format_plan_summary,
    generate_log_filename,
    write_rename_log,
)

# Sanitizer — pure functions and constants
from .sanitizer import (
    ALL_RESTRICTED_CHARS,
    CONTROL_CHARS,
    DEFAULT_MAX_NAME_LENGTH,
    FORBIDDEN_CHARS,
    UNICODE_CHAR_MAP,
    UNICODE_DOT_REPLACEMENT,
    UNICODE_SPACE_REPLACEMENT,
    WINDOWS_MAX_PATH,
    handle_reserved_names,
    is_name_safe,
    replace_forbidden_chars,
    sanitize_name,
    strip_trailing_dots_spaces,
    truncate_name,
)

# Scanner — filesystem walking and data classes
from .scanner import (
    EntryKind,
    RenameAction,
    RenamePlan,
    RenameResult,
    build_rename_plan,
    validate_path_under_root,
)

# TUI entry point (optional — requires 'tui' extra)
try:
    from .tui import tui_main
except ImportError:

    def tui_main(
        argv: list[str] | None = None,  # pyright: ignore[reportUnusedParameter]
    ) -> int:
        """Stub that prints an install hint when Textual is not available."""
        import sys  # noqa: I001

        print(
            "Error: The TUI requires the 'tui' extra. "
            "Install with: pip install restricted-filenames-renamer[tui]",
            file=sys.stderr,
        )
        return 1


__all__ = [
    # CLI
    "main",
    # Sanitizer functions
    "sanitize_name",
    "is_name_safe",
    "replace_forbidden_chars",
    "strip_trailing_dots_spaces",
    "handle_reserved_names",
    "truncate_name",
    # Sanitizer constants
    "FORBIDDEN_CHARS",
    "CONTROL_CHARS",
    "ALL_RESTRICTED_CHARS",
    "UNICODE_CHAR_MAP",
    "UNICODE_DOT_REPLACEMENT",
    "UNICODE_SPACE_REPLACEMENT",
    "DEFAULT_MAX_NAME_LENGTH",
    "WINDOWS_MAX_PATH",
    # Scanner classes
    "EntryKind",
    "RenameAction",
    "RenamePlan",
    "RenameResult",
    # Scanner functions
    "build_rename_plan",
    "validate_path_under_root",
    # Renamer functions
    "execute_plan",
    "format_plan_summary",
    "generate_log_filename",
    "write_rename_log",
    # TUI
    "tui_main",
]

if __name__ == "__main__":
    raise SystemExit(main())
