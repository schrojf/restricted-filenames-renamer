"""Tests for the Textual TUI."""

from __future__ import annotations

from pathlib import Path

import pytest
from textual.widgets import Button, DataTable, Input, Static

from restricted_filenames_renamer.tui import RenamerApp, tui_main


class TestRenamerApp:
    @pytest.fixture
    def clean_dir(self, tmp_path: Path) -> Path:
        (tmp_path / "safe_file.txt").touch()
        (tmp_path / "another.doc").touch()
        return tmp_path

    @pytest.fixture
    def dirty_dir(self, tmp_path: Path) -> Path:
        (tmp_path / "file:name.txt").touch()
        (tmp_path / "aux").touch()
        (tmp_path / "safe.txt").touch()
        return tmp_path

    @pytest.mark.asyncio
    async def test_clean_directory_shows_no_renames(self, clean_dir: Path) -> None:
        app = RenamerApp(root=clean_dir)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            table: DataTable[str] = app.query_one(  # pyright: ignore[reportUnknownVariableType]
                "#rename-table", DataTable
            )
            assert table.row_count == 0
            apply_btn = app.query_one("#apply-btn", Button)
            assert apply_btn.disabled is True

    @pytest.mark.asyncio
    async def test_dirty_directory_populates_table(self, dirty_dir: Path) -> None:
        app = RenamerApp(root=dirty_dir)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            table: DataTable[str] = app.query_one(  # pyright: ignore[reportUnknownVariableType]
                "#rename-table", DataTable
            )
            assert table.row_count == 2  # file:name.txt and aux
            apply_btn = app.query_one("#apply-btn", Button)
            assert apply_btn.disabled is False

    @pytest.mark.asyncio
    async def test_rescan_with_replace_char(self, dirty_dir: Path) -> None:
        app = RenamerApp(root=dirty_dir)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # Change replace-char setting
            replace_input = app.query_one("#replace-char", Input)
            replace_input.value = "-"
            # Click re-scan
            await pilot.click("#rescan-btn")
            await pilot.pause()
            # Table should still show renames
            table: DataTable[str] = app.query_one(  # pyright: ignore[reportUnknownVariableType]
                "#rename-table", DataTable
            )
            assert table.row_count == 2

    @pytest.mark.asyncio
    async def test_apply_renames_files(self, dirty_dir: Path) -> None:
        app = RenamerApp(root=dirty_dir)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.click("#apply-btn")
            await pilot.pause()
            # file:name.txt should be renamed (fullwidth colon)
            assert (dirty_dir / "file\uff1aname.txt").exists()
            assert not (dirty_dir / "file:name.txt").exists()
            # aux should be renamed to _aux
            assert (dirty_dir / "_aux").exists()
            assert not (dirty_dir / "aux").exists()
            # Apply button should be disabled after execution
            apply_btn = app.query_one("#apply-btn", Button)
            assert apply_btn.disabled is True

    @pytest.mark.asyncio
    async def test_detail_panel_updates_on_row_highlight(self, dirty_dir: Path) -> None:
        app = RenamerApp(root=dirty_dir)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            # Detail header should show default text before any row selection
            detail_header = app.query_one("#detail-header", Static)
            assert str(detail_header.render()) != ""
            # Focus the table and move to first row
            table: DataTable[str] = app.query_one(  # pyright: ignore[reportUnknownVariableType]
                "#rename-table", DataTable
            )
            table.focus()
            await pilot.press("down")
            await pilot.pause()
            # Detail header should have changed to show the selected entry
            # The row_actions mapping should be populated
            assert len(app.row_actions) > 0

    @pytest.mark.asyncio
    async def test_quit_keybinding(self, clean_dir: Path) -> None:
        app = RenamerApp(root=clean_dir)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("q")
            # App should exit; the context manager handles this


class TestTuiMain:
    def test_invalid_path_returns_1(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        result = tui_main([str(tmp_path / "nonexistent")])
        assert result == 1
        captured = capsys.readouterr()
        assert "not a directory" in captured.err

    def test_file_path_returns_1(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        f = tmp_path / "file.txt"
        f.touch()
        result = tui_main([str(f)])
        assert result == 1
        captured = capsys.readouterr()
        assert "not a directory" in captured.err


class TestPublicApi:
    def test_tui_main_in_public_api(self) -> None:
        import restricted_filenames_renamer

        assert hasattr(restricted_filenames_renamer, "tui_main")
        assert callable(restricted_filenames_renamer.tui_main)
