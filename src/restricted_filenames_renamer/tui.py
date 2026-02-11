"""Interactive TUI for restricted-filenames-renamer (requires the 'tui' extra)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Static,
    Switch,
)
from textual.widgets.data_table import RowKey

from .renamer import execute_plan, generate_log_filename
from .sanitizer import ALL_RESTRICTED_CHARS, DEFAULT_MAX_NAME_LENGTH
from .scanner import EntryKind, RenameAction, RenamePlan, build_rename_plan


def _kind_label(kind: EntryKind) -> str:
    if kind == EntryKind.DIRECTORY:
        return "[dir]"
    if kind == EntryKind.SYMLINK:
        return "[link]"
    return "[file]"


class RenamerApp(App[int]):
    """Interactive TUI for scanning and renaming files for cross-OS portability."""

    TITLE = "Restricted Filenames Renamer"  # pyright: ignore[reportUnannotatedClassAttribute]

    CSS: ClassVar[str] = """
    #settings-bar {
        height: auto;
        padding: 1 2;
        background: $surface;
        align: left middle;
    }

    #settings-bar Label {
        padding: 0 1;
    }

    #settings-bar Input {
        width: 16;
    }

    #settings-bar Switch {
        margin: 0 1;
    }

    #settings-bar Button {
        margin: 0 1;
    }

    #content-area {
        height: 1fr;
    }

    #rename-table {
        width: 2fr;
    }

    #detail-panel {
        width: 1fr;
        border-left: solid $accent;
        padding: 1 2;
        overflow-y: auto;
    }

    #detail-header {
        text-style: bold;
        margin-bottom: 1;
    }

    #detail-content {
        height: auto;
    }

    #status-area {
        height: 10;
        border-top: solid $accent;
    }

    #log-output {
        height: 1fr;
    }
    """

    BINDINGS = [  # pyright: ignore[reportUnannotatedClassAttribute]
        Binding("q", "quit", "Quit"),
        Binding("r", "rescan", "Re-scan"),
        Binding("a", "apply", "Apply Renames"),
    ]

    def __init__(self, root: Path) -> None:
        super().__init__()
        self.root: Path = root  # pyright: ignore[reportUnannotatedClassAttribute]
        self.current_plan: RenamePlan | None = None
        self.row_actions: dict[RowKey, RenameAction] = {}

    def compose(self) -> ComposeResult:  # pyright: ignore[reportImplicitOverride]
        yield Header()
        with Vertical():
            with Horizontal(id="settings-bar"):
                yield Label("Replace char:")
                yield Input(
                    id="replace-char",
                    placeholder="unicode default",
                    max_length=1,
                )
                yield Label("Max length:")
                yield Input(
                    id="max-length",
                    value=str(DEFAULT_MAX_NAME_LENGTH),
                    type="integer",
                )
                yield Label("Follow symlinks:")
                yield Switch(id="follow-symlinks", value=False)
                yield Button("Re-scan", id="rescan-btn", variant="default")
                yield Button("Apply Renames", id="apply-btn", variant="warning", disabled=True)
            with Horizontal(id="content-area"):
                yield DataTable(id="rename-table", cursor_type="row")
                with Vertical(id="detail-panel"):
                    yield Static("Select a row to see details", id="detail-header")
                    yield Static("", id="detail-content")
            with Vertical(id="status-area"):
                yield RichLog(id="log-output", max_lines=200, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        table: DataTable[str] = self.query_one(  # pyright: ignore[reportUnknownVariableType]
            "#rename-table", DataTable
        )
        table.add_columns("Kind", "Original Name", "Renamed To", "Directory", "Issues")
        self.action_rescan()

    def _read_settings(self) -> tuple[str | None, int, bool] | None:
        """Read and validate settings from widgets. Returns None on validation error."""
        log = self.query_one("#log-output", RichLog)

        replace_char_input = self.query_one("#replace-char", Input)
        replace_char: str | None = replace_char_input.value or None
        if replace_char is not None:
            if len(replace_char) != 1:
                log.write("[red]Error:[/red] Replace char must be a single character.")
                return None
            if replace_char in ALL_RESTRICTED_CHARS:
                log.write("[red]Error:[/red] Replace char cannot be a restricted character.")
                return None

        max_length_input = self.query_one("#max-length", Input)
        try:
            max_length = (
                int(max_length_input.value) if max_length_input.value else DEFAULT_MAX_NAME_LENGTH
            )
        except ValueError:
            log.write("[red]Error:[/red] Max length must be an integer.")
            return None
        if max_length < 1:
            log.write("[red]Error:[/red] Max length must be at least 1.")
            return None

        follow_symlinks = self.query_one("#follow-symlinks", Switch).value

        return replace_char, max_length, follow_symlinks

    def action_rescan(self) -> None:
        settings = self._read_settings()
        if settings is None:
            return
        replace_char, max_length, follow_symlinks = settings

        self.query_one("#rename-table", DataTable).loading = True
        self.query_one("#apply-btn", Button).disabled = True
        self.run_scan(replace_char, max_length, follow_symlinks)

    def action_apply(self) -> None:
        if self.current_plan is None or not self.current_plan.has_changes:
            log = self.query_one("#log-output", RichLog)
            log.write("Nothing to apply.")
            return
        self.query_one("#apply-btn", Button).disabled = True
        self.query_one("#rescan-btn", Button).disabled = True
        self.run_apply()

    @work(exclusive=True, thread=True)
    def run_scan(
        self,
        replace_char: str | None,
        max_length: int,
        follow_symlinks: bool,
    ) -> None:
        plan = build_rename_plan(
            self.root,
            replace_char=replace_char,
            max_length=max_length,
            follow_symlinks=follow_symlinks,
        )
        self.call_from_thread(self._populate_table, plan)

    def _populate_table(self, plan: RenamePlan) -> None:
        self.current_plan = plan
        table: DataTable[str] = self.query_one(  # pyright: ignore[reportUnknownVariableType]
            "#rename-table", DataTable
        )
        table.clear()
        self.row_actions.clear()

        for action in plan.actions:
            if not action.needs_rename:
                continue
            try:
                rel_dir = str(action.source.parent.relative_to(plan.root))
            except ValueError:
                rel_dir = str(action.source.parent)
            row_key = table.add_row(  # pyright: ignore[reportUnknownMemberType]
                _kind_label(action.kind),
                action.original_name,
                action.final_name,
                rel_dir if rel_dir != "." else "(root)",
                str(len(action.issues)),
            )
            self.row_actions[row_key] = action

        table.loading = False
        self.query_one("#apply-btn", Button).disabled = not plan.has_changes

        # Update detail panel
        header = self.query_one("#detail-header", Static)
        content = self.query_one("#detail-content", Static)
        header.update("Select a row to see details")
        content.update("")

        log = self.query_one("#log-output", RichLog)
        log.write(
            f"Scanned {plan.total_entries_scanned} entries under {plan.root}, "
            f"{plan.total_renames_needed} renames needed."
        )
        if plan.skipped_symlinks:
            log.write(f"Skipped {len(plan.skipped_symlinks)} symlinks.")
        if plan.warnings:
            for warning in plan.warnings:
                log.write(f"[yellow]Warning:[/yellow] {warning}")

    @work(exclusive=True, thread=True)
    def run_apply(self) -> None:
        plan = self.current_plan
        if plan is None:
            return

        log_path = plan.root / generate_log_filename()
        results = execute_plan(plan, log_file=log_path)

        def update_ui() -> None:
            log = self.query_one("#log-output", RichLog)
            successes = 0
            failures = 0
            for r in results:
                if r.success:
                    successes += 1
                    log.write(
                        f"[green]OK[/green] {r.action.original_name} -> {r.action.final_name}"
                    )
                else:
                    failures += 1
                    log.write(f"[red]FAIL[/red] {r.action.original_name}: {r.error_message}")
            log.write(f"\nDone: {successes} renamed, {failures} errors. Log: {log_path}")

            self.query_one("#apply-btn", Button).disabled = True
            self.query_one("#rescan-btn", Button).disabled = False
            self.current_plan = None

        self.call_from_thread(update_ui)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        action = self.row_actions.get(event.row_key)
        if action is None:
            return
        header = self.query_one("#detail-header", Static)
        content = self.query_one("#detail-content", Static)
        header.update(f"{_kind_label(action.kind)} {action.original_name}")
        lines = [
            f"Source:      {action.source}",
            f"Destination: {action.destination}",
            f"Kind:        {action.kind.value}",
            "",
            "Issues:",
        ]
        if action.issues:
            for issue in action.issues:
                lines.append(f"  - {issue}")
        else:
            lines.append("  (none)")
        content.update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "rescan-btn":
            self.action_rescan()
        elif event.button.id == "apply-btn":
            self.action_apply()


def tui_main(argv: list[str] | None = None) -> int:
    """CLI entry point for the TUI."""
    parser = argparse.ArgumentParser(
        prog="restricted-filenames-renamer-tui",
        description="Interactive TUI for renaming files for cross-OS portability.",
    )
    parser.add_argument("path", type=Path, help="Root directory to scan.")
    args = parser.parse_args(argv)

    root: Path = args.path.resolve()
    if not root.is_dir():
        print(f"Error: '{args.path}' is not a directory.", file=sys.stderr)
        return 1

    app = RenamerApp(root=root)
    result = app.run()
    return result if result is not None else 0
