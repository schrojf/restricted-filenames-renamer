"""Tests for the CLI module — end-to-end integration tests."""

from __future__ import annotations

from pathlib import Path

from restricted_filenames_renamer.cli import main


class TestCLIDryRun:
    def test_dry_run_no_write(self, tmp_path: Path) -> None:
        """Without --write, no files should be renamed."""
        (tmp_path / "file:name.txt").touch()

        exit_code = main([str(tmp_path)])

        assert exit_code == 0
        assert (tmp_path / "file:name.txt").exists()
        assert not (tmp_path / "file_name.txt").exists()

    def test_dry_run_clean_directory(self, tmp_path: Path) -> None:
        (tmp_path / "clean.txt").touch()

        exit_code = main([str(tmp_path)])

        assert exit_code == 0


class TestCLIWrite:
    def test_write_with_yes(self, tmp_path: Path) -> None:
        """--write --yes renames files without prompting."""
        (tmp_path / "file:name.txt").touch()

        exit_code = main([str(tmp_path), "--write", "--yes"])

        assert exit_code == 0
        assert (tmp_path / "file_name.txt").exists()
        assert not (tmp_path / "file:name.txt").exists()

    def test_write_creates_log(self, tmp_path: Path) -> None:
        (tmp_path / "file:name.txt").touch()
        log_file = tmp_path / "test_log.json"

        exit_code = main([str(tmp_path), "--write", "--yes", "--log-file", str(log_file)])

        assert exit_code == 0
        assert log_file.exists()


class TestCLIValidation:
    def test_invalid_path(self) -> None:
        exit_code = main(["/nonexistent/path/12345"])
        assert exit_code == 1

    def test_invalid_replace_char_multi(self) -> None:
        """--replace-char must be a single character."""
        exit_code = main(["/tmp", "--replace-char", "ab"])
        assert exit_code == 1

    def test_invalid_replace_char_restricted(self, tmp_path: Path) -> None:
        """--replace-char must not be a restricted character."""
        exit_code = main([str(tmp_path), "--replace-char", ":"])
        assert exit_code == 1


class TestCLIOptions:
    def test_custom_replace_char(self, tmp_path: Path) -> None:
        (tmp_path / "a:b.txt").touch()

        exit_code = main([str(tmp_path), "--write", "--yes", "--replace-char", "-"])

        assert exit_code == 0
        assert (tmp_path / "a-b.txt").exists()

    def test_verbose(self, tmp_path: Path) -> None:
        (tmp_path / "file:name.txt").touch()

        exit_code = main([str(tmp_path), "--verbose"])

        assert exit_code == 0

    def test_max_length(self, tmp_path: Path) -> None:
        # Use a name within the OS limit (255) but exceeding our custom --max-length.
        (tmp_path / ("a" * 50 + ".txt")).touch()
        log_file = tmp_path / "log.json"

        exit_code = main(
            [
                str(tmp_path),
                "--write",
                "--yes",
                "--max-length",
                "20",
                "--log-file",
                str(log_file),
            ]
        )

        assert exit_code == 0
        txt_files = [f for f in tmp_path.iterdir() if f.suffix == ".txt"]
        assert len(txt_files) == 1
        assert len(txt_files[0].name) <= 20
