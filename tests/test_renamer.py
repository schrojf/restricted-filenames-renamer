"""Tests for the renamer module — plan execution and logging."""

from __future__ import annotations

import json
from pathlib import Path

from restricted_filenames_renamer.renamer import (
    execute_plan,
    format_plan_summary,
    generate_log_filename,
    write_rename_log,
)
from restricted_filenames_renamer.scanner import build_rename_plan


class TestExecutePlan:
    def test_renames_file(self, tmp_path: Path) -> None:
        """A simple file rename is executed on disk."""
        (tmp_path / "file:name.txt").touch()

        plan = build_rename_plan(tmp_path)
        results = execute_plan(plan)

        assert len(results) == 1
        assert results[0].success
        assert (tmp_path / "file_name.txt").exists()
        assert not (tmp_path / "file:name.txt").exists()

    def test_renames_directory(self, tmp_path: Path) -> None:
        (tmp_path / "bad:dir").mkdir()
        (tmp_path / "bad:dir" / "clean.txt").touch()

        plan = build_rename_plan(tmp_path)
        results = execute_plan(plan)

        assert all(r.success for r in results)
        assert (tmp_path / "bad_dir").is_dir()
        assert (tmp_path / "bad_dir" / "clean.txt").exists()

    def test_nested_renames(self, tmp_path: Path) -> None:
        """Deeply nested renames work correctly (bottom-up ordering)."""
        deep = tmp_path / "a:dir" / "b:dir"
        deep.mkdir(parents=True)
        (deep / "c:file.txt").touch()

        plan = build_rename_plan(tmp_path)
        results = execute_plan(plan)

        assert all(r.success for r in results)
        assert (tmp_path / "a_dir" / "b_dir" / "c_file.txt").exists()

    def test_writes_log_file(self, tmp_path: Path) -> None:
        (tmp_path / "file:name.txt").touch()
        log_file = tmp_path / "test_log.json"

        plan = build_rename_plan(tmp_path)
        execute_plan(plan, log_file=log_file)

        assert log_file.exists()
        data = json.loads(log_file.read_text())
        assert data["total_renames"] == 1
        assert len(data["renames"]) == 1
        assert data["renames"][0]["destination"].endswith("file_name.txt")

    def test_source_missing_records_error(self, tmp_path: Path) -> None:
        """If source disappears between scan and execute, an error is recorded."""
        f = tmp_path / "file:name.txt"
        f.touch()

        plan = build_rename_plan(tmp_path)
        # Remove the file before execution.
        f.unlink()

        results = execute_plan(plan)
        assert len(results) == 1
        assert not results[0].success
        assert "no longer exists" in (results[0].error_message or "")

    def test_no_changes_no_results(self, tmp_path: Path) -> None:
        (tmp_path / "clean.txt").touch()
        plan = build_rename_plan(tmp_path)
        results = execute_plan(plan)
        assert results == []


class TestFormatPlanSummary:
    def test_no_changes(self, tmp_path: Path) -> None:
        (tmp_path / "clean.txt").touch()
        plan = build_rename_plan(tmp_path)

        summary = format_plan_summary(plan)
        assert "1 entries" in summary or "Scanned" in summary

    def test_with_changes(self, tmp_path: Path) -> None:
        (tmp_path / "file:name.txt").touch()
        plan = build_rename_plan(tmp_path)

        summary = format_plan_summary(plan)
        assert "file:name.txt" in summary
        assert "file_name.txt" in summary

    def test_verbose_shows_issues(self, tmp_path: Path) -> None:
        (tmp_path / "file:name.txt").touch()
        plan = build_rename_plan(tmp_path)

        summary = format_plan_summary(plan, verbose=True)
        assert "forbidden" in summary.lower() or "Replaced" in summary


class TestWriteRenameLog:
    def test_log_structure(self, tmp_path: Path) -> None:
        (tmp_path / "a:b.txt").touch()
        log_file = tmp_path / "log.json"

        plan = build_rename_plan(tmp_path)
        results = execute_plan(plan)
        write_rename_log(results, tmp_path, log_file)

        data = json.loads(log_file.read_text())
        assert "timestamp" in data
        assert "root" in data
        assert "renames" in data
        assert "errors" in data
        assert data["total_renames"] == 1
        assert data["total_errors"] == 0


class TestGenerateLogFilename:
    def test_format(self) -> None:
        name = generate_log_filename()
        assert name.startswith("rename_log_")
        assert name.endswith(".json")
