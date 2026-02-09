"""Plan execution, human-readable formatting, and JSON log writing."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from .scanner import EntryKind, RenamePlan, RenameResult


def execute_plan(plan: RenamePlan, *, log_file: Path | None = None) -> list[RenameResult]:
    """Execute all rename actions in *plan*.

    For each action where ``needs_rename`` is ``True``:
      1. Verify the source still exists.
      2. Verify the destination does not already exist.
      3. Perform ``os.rename(source, destination)``.

    Errors are recorded but do not stop execution of remaining actions.

    Args:
        plan: The rename plan to execute.
        log_file: Optional path where the JSON log will be written.

    Returns:
        A list of ``RenameResult`` for every action attempted.
    """
    results: list[RenameResult] = []

    for action in plan.actions:
        if not action.needs_rename:
            continue

        # Pre-flight checks.
        if not action.source.exists() and not action.source.is_symlink():
            results.append(
                RenameResult(
                    action=action,
                    success=False,
                    error_message=f"Source no longer exists: {action.source}",
                )
            )
            continue

        if action.destination.exists() or action.destination.is_symlink():
            results.append(
                RenameResult(
                    action=action,
                    success=False,
                    error_message=f"Destination already exists: {action.destination}",
                )
            )
            continue

        try:
            os.rename(action.source, action.destination)
            results.append(RenameResult(action=action, success=True))
        except OSError as exc:
            results.append(
                RenameResult(
                    action=action,
                    success=False,
                    error_message=str(exc),
                )
            )

    if log_file is not None:
        write_rename_log(results, plan.root, log_file)

    return results


def format_plan_summary(plan: RenamePlan, *, verbose: bool = False) -> str:
    """Format the rename plan as a human-readable string.

    In normal mode, shows a count and the list of renames.
    In verbose mode, also shows per-entry issues and all warnings.
    """
    lines: list[str] = []

    lines.append(f"Scanned {plan.total_entries_scanned} entries under {plan.root}")

    if plan.skipped_symlinks:
        lines.append(
            f"Skipped {len(plan.skipped_symlinks)} symlinks (use --follow-symlinks to process)"
        )
        if verbose:
            for sym in plan.skipped_symlinks:
                lines.append(f"  symlink: {sym}")

    if not plan.has_changes:
        return "\n".join(lines)

    lines.append(f"Found {plan.total_renames_needed} entries to rename:")
    lines.append("")

    for action in plan.actions:
        if not action.needs_rename:
            continue
        kind_label = _kind_label(action.kind)
        lines.append(f"  {kind_label} {action.source.name} -> {action.final_name}")
        lines.append(f"         in {action.source.parent}")
        if verbose and action.issues:
            for issue in action.issues:
                lines.append(f"         * {issue}")

    if plan.warnings:
        lines.append("")
        lines.append(f"Warnings ({len(plan.warnings)}):")
        for warning in plan.warnings:
            lines.append(f"  ! {warning}")

    return "\n".join(lines)


def write_rename_log(
    results: list[RenameResult],
    root: Path,
    log_file: Path,
) -> None:
    """Write a JSON log file recording all attempted renames.

    The log contains a ``renames`` array of successful renames and an
    ``errors`` array of failures, suitable for auditing or rollback.
    """
    renames: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    for result in results:
        if result.success:
            renames.append(
                {
                    "source": str(result.action.source),
                    "destination": str(result.action.destination),
                }
            )
        else:
            entry: dict[str, str] = {"source": str(result.action.source)}
            if result.error_message:
                entry["error"] = result.error_message
            errors.append(entry)

    log_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "root": str(root),
        "total_renames": len(renames),
        "total_errors": len(errors),
        "renames": renames,
        "errors": errors,
    }

    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text(json.dumps(log_data, indent=2) + "\n", encoding="utf-8")


def generate_log_filename() -> str:
    """Generate a timestamped log filename like ``rename_log_20260209_153045.json``."""
    now = datetime.now(UTC)
    return f"rename_log_{now.strftime('%Y%m%d_%H%M%S')}.json"


def _kind_label(kind: EntryKind) -> str:
    """Return a short label for display, e.g. ``[dir]`` or ``[file]``."""
    if kind == EntryKind.DIRECTORY:
        return "[dir] "
    if kind == EntryKind.SYMLINK:
        return "[link]"
    return "[file]"
