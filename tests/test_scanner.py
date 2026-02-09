"""Tests for the scanner module — filesystem walking and plan building."""

from __future__ import annotations

from pathlib import Path

import pytest

from restricted_filenames_renamer.scanner import (
    EntryKind,
    build_rename_plan,
    validate_path_under_root,
)


class TestBuildRenamePlan:
    def test_clean_directory(self, tmp_path: Path) -> None:
        """Directory with all safe names produces no renames."""
        (tmp_path / "readme.md").touch()
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").touch()

        plan = build_rename_plan(tmp_path)

        assert not plan.has_changes
        assert plan.total_renames_needed == 0
        assert plan.total_entries_scanned == 3

    def test_forbidden_char_in_filename(self, tmp_path: Path) -> None:
        """Files with forbidden characters are planned for renaming."""
        (tmp_path / "file:name.txt").touch()

        plan = build_rename_plan(tmp_path)

        assert plan.has_changes
        assert plan.total_renames_needed == 1
        assert plan.actions[0].original_name == "file:name.txt"
        assert plan.actions[0].final_name == "file\uff1aname.txt"  # fullwidth colon

    def test_forbidden_char_override_mode(self, tmp_path: Path) -> None:
        """With replace_char override, uses simple replacement."""
        (tmp_path / "file:name.txt").touch()

        plan = build_rename_plan(tmp_path, replace_char="_")

        assert plan.actions[0].final_name == "file_name.txt"

    def test_reserved_name(self, tmp_path: Path) -> None:
        """Reserved Windows names are planned for renaming."""
        (tmp_path / "CON").touch()

        plan = build_rename_plan(tmp_path)

        assert plan.has_changes
        assert plan.actions[0].final_name == "_CON"

    def test_reserved_name_with_extension(self, tmp_path: Path) -> None:
        (tmp_path / "CON.txt").touch()

        plan = build_rename_plan(tmp_path)

        assert plan.has_changes
        assert plan.actions[0].final_name == "_CON.txt"

    def test_trailing_dot(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt.").touch()

        plan = build_rename_plan(tmp_path)

        assert plan.has_changes
        assert plan.actions[0].final_name == "file.txt\uff0e"  # fullwidth dot

    def test_nested_directories_bottom_up(self, tmp_path: Path) -> None:
        """Deepest entries should appear first in the plan."""
        deep = tmp_path / "level:1" / "level:2"
        deep.mkdir(parents=True)
        (deep / "file:deep.txt").touch()

        plan = build_rename_plan(tmp_path)

        assert plan.has_changes
        names = [a.original_name for a in plan.actions]
        assert "file:deep.txt" in names
        assert "level:2" in names
        assert "level:1" in names

        idx_deep_file = names.index("file:deep.txt")
        idx_level2 = names.index("level:2")
        idx_level1 = names.index("level:1")
        assert idx_deep_file < idx_level1
        assert idx_level2 < idx_level1

    def test_collision_two_files_same_target(self, tmp_path: Path) -> None:
        """Two files that sanitize to the same name get collision suffixes."""
        (tmp_path / "a:b.txt").touch()
        (tmp_path / "a*b.txt").touch()

        plan = build_rename_plan(tmp_path)

        # Both map to different fullwidth chars, so NO collision in Unicode mode.
        final_names = {a.final_name for a in plan.actions}
        assert len(final_names) == 2
        assert "a\uff1ab.txt" in final_names  # fullwidth colon
        assert "a\uff0ab.txt" in final_names  # fullwidth asterisk

    def test_collision_in_override_mode(self, tmp_path: Path) -> None:
        """In override mode, two files mapping to same name get suffixes."""
        (tmp_path / "a:b.txt").touch()
        (tmp_path / "a*b.txt").touch()

        plan = build_rename_plan(tmp_path, replace_char="_")

        final_names = {a.final_name for a in plan.actions}
        assert len(final_names) == 2
        assert "a_b.txt" in final_names
        other = final_names - {"a_b.txt"}
        assert other.pop().startswith("a_b")

    def test_collision_with_existing_clean_file_override(self, tmp_path: Path) -> None:
        """In override mode, a dirty file colliding with a clean file gets a suffix."""
        (tmp_path / "a_b.txt").touch()
        (tmp_path / "a:b.txt").touch()

        plan = build_rename_plan(tmp_path, replace_char="_")

        assert plan.total_renames_needed == 1
        action = plan.actions[0]
        assert action.original_name == "a:b.txt"
        assert action.final_name == "a_b_1.txt"

    def test_symlink_skipped_by_default(self, tmp_path: Path) -> None:
        """Symlinks are reported but not processed by default."""
        target = tmp_path / "target.txt"
        target.touch()
        link = tmp_path / "link:name.txt"
        link.symlink_to(target)

        plan = build_rename_plan(tmp_path)

        assert len(plan.skipped_symlinks) == 1
        assert plan.skipped_symlinks[0] == link

    def test_directory_rename(self, tmp_path: Path) -> None:
        """Directories with forbidden chars are planned for renaming."""
        (tmp_path / "bad:dir").mkdir()
        (tmp_path / "bad:dir" / "clean_file.txt").touch()

        plan = build_rename_plan(tmp_path)

        assert plan.total_renames_needed == 1
        assert plan.actions[0].kind == EntryKind.DIRECTORY
        assert plan.actions[0].final_name == "bad\uff1adir"  # fullwidth colon

    def test_custom_replace_char(self, tmp_path: Path) -> None:
        (tmp_path / "a:b.txt").touch()

        plan = build_rename_plan(tmp_path, replace_char="-")

        assert plan.actions[0].final_name == "a-b.txt"

    def test_empty_directory(self, tmp_path: Path) -> None:
        plan = build_rename_plan(tmp_path)

        assert not plan.has_changes
        assert plan.total_entries_scanned == 0

    def test_hidden_files_preserved(self, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").touch()
        (tmp_path / ".env").touch()

        plan = build_rename_plan(tmp_path)

        assert not plan.has_changes


class TestValidatePathUnderRoot:
    def test_valid_path(self, tmp_path: Path) -> None:
        child = tmp_path / "subdir" / "file.txt"
        validate_path_under_root(child, tmp_path)  # Should not raise.

    def test_path_outside_root(self, tmp_path: Path) -> None:
        outside = tmp_path.parent / "outside"
        with pytest.raises(ValueError, match="not under root"):
            validate_path_under_root(outside, tmp_path)

    def test_root_itself(self, tmp_path: Path) -> None:
        validate_path_under_root(tmp_path, tmp_path)  # Should not raise.

    def test_similar_prefix_not_confused(self, tmp_path: Path) -> None:
        """'/root-other' must not be accepted as under '/root'."""
        fake = Path(str(tmp_path) + "-other")
        with pytest.raises(ValueError, match="not under root"):
            validate_path_under_root(fake, tmp_path)
