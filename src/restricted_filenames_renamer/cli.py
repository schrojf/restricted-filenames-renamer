"""Command-line interface and main entry point for restricted-filenames-renamer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .renamer import execute_plan, format_plan_summary, generate_log_filename
from .sanitizer import ALL_RESTRICTED_CHARS, DEFAULT_MAX_NAME_LENGTH, DEFAULT_REPLACE_CHAR
from .scanner import build_rename_plan


def create_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser."""

    parser = argparse.ArgumentParser(
        prog="restricted-filenames-renamer",
        description=(
            "Recursively rename files and directories to be portable across "
            "operating systems (UNIX / Windows / macOS). Replaces characters "
            "that are forbidden on Windows, handles reserved device names, "
            "trailing dots/spaces, and name-length limits."
        ),
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Root directory to scan recursively.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        default=False,
        help="Actually perform renames. Without this flag, only a dry-run is shown.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        default=False,
        help="Skip interactive confirmation when --write is used.",
    )
    parser.add_argument(
        "--replace-char",
        type=str,
        default=DEFAULT_REPLACE_CHAR,
        help=f"Character to replace forbidden characters with (default: '{DEFAULT_REPLACE_CHAR}').",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=DEFAULT_MAX_NAME_LENGTH,
        help=f"Maximum filename length before truncation (default: {DEFAULT_MAX_NAME_LENGTH}).",
    )
    parser.add_argument(
        "--follow-symlinks",
        action="store_true",
        default=False,
        help="Follow symbolic links. By default, symlinks are reported but not followed.",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Custom path for the JSON rename log. Default: rename_log_<timestamp>.json",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Show detailed information about each rename.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code: 0 on success, 1 on error, 2 on user cancellation.
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Extract typed values from argparse namespace.
    root_arg: Path = args.path
    write: bool = args.write
    yes: bool = args.yes
    replace_char: str = args.replace_char
    max_length: int = args.max_length
    follow_symlinks: bool = args.follow_symlinks
    log_file_arg: Path | None = args.log_file
    verbose: bool = args.verbose

    # Validate root path.
    root = root_arg.resolve()
    if not root.is_dir():
        print(f"Error: '{root_arg}' is not a directory.", file=sys.stderr)
        return 1

    # Validate replace_char.
    if len(replace_char) != 1:
        print("Error: --replace-char must be a single character.", file=sys.stderr)
        return 1

    if replace_char in ALL_RESTRICTED_CHARS:
        print(
            f"Error: --replace-char '{replace_char}' is itself a restricted character.",
            file=sys.stderr,
        )
        return 1

    # Build the rename plan.
    plan = build_rename_plan(
        root,
        replace_char=replace_char,
        max_length=max_length,
        follow_symlinks=follow_symlinks,
    )

    # Display the plan.
    summary = format_plan_summary(plan, verbose=verbose)
    print(summary)

    if not plan.has_changes:
        print("\nNo renames needed. All filenames are already portable.")
        return 0

    if not write:
        print("\nDry-run mode. Use --write to apply changes.")
        return 0

    # Interactive confirmation.
    if not yes:
        try:
            response = input(f"\nRename {plan.total_renames_needed} entries? [y/N] ")
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return 2
        if response.strip().lower() not in ("y", "yes"):
            print("Cancelled.")
            return 2

    # Execute the plan.
    log_file = log_file_arg if log_file_arg is not None else Path(generate_log_filename())
    results = execute_plan(plan, log_file=log_file)

    # Report results.
    successes = sum(1 for r in results if r.success)
    failures = sum(1 for r in results if not r.success)

    print(f"\nDone: {successes} renamed, {failures} errors.")
    if failures > 0:
        for r in results:
            if not r.success:
                print(f"  ERROR: {r.action.source} -> {r.error_message}", file=sys.stderr)

    print(f"Log written to: {log_file}")

    return 1 if failures > 0 else 0
