"""Filesystem walking, rename plan building, and collision resolution.

This module scans a directory tree, computes sanitized names for every entry,
resolves naming collisions, and produces an ordered plan of rename actions
that can be executed safely (deepest entries first, bottom-up).
"""

from __future__ import annotations

import enum
import os
from dataclasses import dataclass, field
from pathlib import Path

from .sanitizer import (
    DEFAULT_MAX_NAME_LENGTH,
    WINDOWS_MAX_PATH,
    sanitize_name,
)


class EntryKind(enum.Enum):
    """Classification of a filesystem entry."""

    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"


@dataclass(frozen=True)
class RenameAction:
    """A single planned rename operation."""

    source: Path
    destination: Path
    kind: EntryKind
    original_name: str
    final_name: str
    issues: tuple[str, ...]
    needs_rename: bool


@dataclass
class RenamePlan:
    """Complete rename plan for a directory tree."""

    root: Path
    actions: list[RenameAction] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped_symlinks: list[Path] = field(default_factory=list)
    total_entries_scanned: int = 0
    total_renames_needed: int = 0

    @property
    def has_changes(self) -> bool:
        """Return ``True`` if any renames are needed."""
        return self.total_renames_needed > 0


@dataclass(frozen=True)
class RenameResult:
    """Result of executing a single rename action."""

    action: RenameAction
    success: bool
    error_message: str | None = None


def validate_path_under_root(path: Path, root: Path) -> None:
    """Raise ``ValueError`` if *path* is not under *root* after resolution."""
    resolved = path.resolve()
    root_resolved = root.resolve()
    # Use os.path.commonpath to avoid string-prefix false positives
    # (e.g. /root-other being mistaken as under /root).
    try:
        common = Path(os.path.commonpath([resolved, root_resolved]))
    except ValueError:
        # Different drives on Windows.
        raise ValueError(f"Path {path} is not under root {root}") from None
    if common != root_resolved:
        raise ValueError(f"Path {path} is not under root {root}")


def _resolve_collisions(
    planned_renames: dict[str, str],
    untouched_names: set[str],
    max_length: int = DEFAULT_MAX_NAME_LENGTH,
) -> dict[str, str]:
    """Resolve name collisions within a single directory.

    Args:
        planned_renames: Mapping of ``original_name -> desired_sanitized_name``
            for entries that need renaming.
        untouched_names: Names of entries in the same directory that do NOT
            need renaming (these occupy name slots).
        max_length: Maximum allowed name length.

    Returns:
        Mapping of ``original_name -> final_collision_free_name``.
    """
    # Names already taken (by entries that aren't being renamed).
    taken: set[str] = set(untouched_names)
    result: dict[str, str] = {}

    # Process in sorted order for deterministic results.
    for original, desired in sorted(planned_renames.items()):
        final = _find_available_name(desired, taken, max_length)
        taken.add(final)
        result[original] = final

    return result


def _find_available_name(desired: str, taken: set[str], max_length: int) -> str:
    """Find a name that doesn't collide, appending ``_1``, ``_2``, etc. if needed.

    The suffix is inserted before the file extension: ``file_1.txt``.
    """
    if desired not in taken:
        return desired

    dot_idx = desired.rfind(".")
    if dot_idx <= 0:
        stem = desired
        ext = ""
    else:
        stem = desired[:dot_idx]
        ext = desired[dot_idx:]

    counter = 1
    while True:
        suffix = f"_{counter}"
        candidate_stem = stem + suffix
        # Ensure we don't exceed max_length with the suffix.
        max_stem_len = max_length - len(ext) - len(suffix)
        if max_stem_len < 1:
            # Extreme edge case: extension + suffix alone exceed max_length.
            candidate = (stem + suffix)[:max_length]
        elif len(candidate_stem) + len(ext) > max_length:
            candidate = stem[:max_stem_len] + suffix + ext
        else:
            candidate = candidate_stem + ext

        if candidate not in taken:
            return candidate
        counter += 1


def build_rename_plan(
    root: Path,
    *,
    replace_char: str | None = None,
    max_length: int = DEFAULT_MAX_NAME_LENGTH,
    follow_symlinks: bool = False,
) -> RenamePlan:
    """Walk the filesystem under *root* and build a complete rename plan.

    The plan is ordered for safe execution: entries within each directory are
    renamed before the directory itself, processing from the deepest level up.

    Args:
        root: Root directory to scan (must exist and be a directory).
        replace_char: Character to replace forbidden characters with.
        max_length: Maximum allowed filename length.
        follow_symlinks: Whether to follow symbolic links.

    Returns:
        A ``RenamePlan`` with ordered actions.

    Raises:
        ValueError: If *root* is not a directory.
    """
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Root path is not a directory: {root}")

    plan = RenamePlan(root=root)

    # os.walk with topdown=False yields deepest directories first.
    # Within each yielded (dirpath, dirnames, filenames), we process
    # all entries (files + subdirs) in that directory.
    for dirpath_str, dirnames, filenames in os.walk(
        root, topdown=False, followlinks=follow_symlinks
    ):
        dirpath = Path(dirpath_str)

        # Collect all entries in this directory: files + subdirectories.
        entries: list[tuple[str, EntryKind]] = []

        for fname in filenames:
            fpath = dirpath / fname
            if fpath.is_symlink():
                if not follow_symlinks:
                    plan.skipped_symlinks.append(fpath)
                    plan.total_entries_scanned += 1
                    continue
                entries.append((fname, EntryKind.SYMLINK))
            else:
                entries.append((fname, EntryKind.FILE))

        for dname in dirnames:
            dpath = dirpath / dname
            if dpath.is_symlink():
                if not follow_symlinks:
                    plan.skipped_symlinks.append(dpath)
                    plan.total_entries_scanned += 1
                    continue
                entries.append((dname, EntryKind.SYMLINK))
            else:
                entries.append((dname, EntryKind.DIRECTORY))

        plan.total_entries_scanned += len(entries)

        # Sanitize each entry and separate into needs-rename vs. clean.
        planned_renames: dict[str, str] = {}  # original_name -> desired_name
        entry_info: dict[
            str, tuple[EntryKind, tuple[str, ...]]
        ] = {}  # original_name -> (kind, issues)
        untouched_names: set[str] = set()

        for name, kind in entries:
            sanitized, issues = sanitize_name(
                name, replace_char=replace_char, max_length=max_length
            )
            if sanitized != name:
                planned_renames[name] = sanitized
                entry_info[name] = (kind, tuple(issues))
            else:
                untouched_names.add(name)
                entry_info[name] = (kind, tuple(issues))

        # Resolve collisions.
        if planned_renames:
            final_names = _resolve_collisions(planned_renames, untouched_names, max_length)
        else:
            final_names = {}

        # Emit RenameActions.
        for original_name, final_name in sorted(final_names.items()):
            source = dirpath / original_name
            destination = dirpath / final_name
            kind, issues = entry_info[original_name]

            # Add collision note if the name changed during collision resolution.
            if final_name != planned_renames[original_name]:
                issues = (
                    *issues,
                    f"Name collision resolved: appended suffix to get {final_name!r}",
                )

            validate_path_under_root(destination, root)

            action = RenameAction(
                source=source,
                destination=destination,
                kind=kind,
                original_name=original_name,
                final_name=final_name,
                issues=issues,
                needs_rename=True,
            )
            plan.actions.append(action)
            plan.total_renames_needed += 1

            # Check Windows MAX_PATH.
            dest_len = len(str(destination))
            if dest_len > WINDOWS_MAX_PATH:
                plan.warnings.append(
                    f"Path length {dest_len} exceeds Windows MAX_PATH ({WINDOWS_MAX_PATH}): "
                    f"{destination}"
                )

        # Also warn about existing entries with long paths (even if not renamed).
        for name in untouched_names:
            full_path = dirpath / name
            path_len = len(str(full_path))
            if path_len > WINDOWS_MAX_PATH:
                plan.warnings.append(
                    f"Path length {path_len} exceeds Windows MAX_PATH ({WINDOWS_MAX_PATH}): "
                    f"{full_path}"
                )

    return plan
