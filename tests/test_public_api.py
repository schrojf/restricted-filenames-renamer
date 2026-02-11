"""Tests that the public API is accessible from the top-level package."""

from __future__ import annotations


class TestPublicAPI:
    def test_sanitizer_functions_importable(self) -> None:
        from restricted_filenames_renamer import (
            handle_reserved_names,
            is_name_safe,
            replace_forbidden_chars,
            sanitize_name,
            strip_trailing_dots_spaces,
            truncate_name,
        )

        assert callable(sanitize_name)
        assert callable(is_name_safe)
        assert callable(replace_forbidden_chars)
        assert callable(strip_trailing_dots_spaces)
        assert callable(handle_reserved_names)
        assert callable(truncate_name)

    def test_sanitizer_constants_importable(self) -> None:
        from restricted_filenames_renamer import (
            ALL_RESTRICTED_CHARS,
            CONTROL_CHARS,
            DEFAULT_MAX_NAME_LENGTH,
            FORBIDDEN_CHARS,
            UNICODE_CHAR_MAP,
            UNICODE_DOT_REPLACEMENT,
            UNICODE_SPACE_REPLACEMENT,
            WINDOWS_MAX_PATH,
        )

        assert len(FORBIDDEN_CHARS) == 9
        assert len(CONTROL_CHARS) == 32
        assert ALL_RESTRICTED_CHARS == FORBIDDEN_CHARS | CONTROL_CHARS
        assert len(UNICODE_CHAR_MAP) == 41  # 9 + 32
        assert isinstance(UNICODE_DOT_REPLACEMENT, str)
        assert isinstance(UNICODE_SPACE_REPLACEMENT, str)
        assert DEFAULT_MAX_NAME_LENGTH == 255
        assert WINDOWS_MAX_PATH == 260

    def test_scanner_classes_importable(self) -> None:
        from restricted_filenames_renamer import (
            EntryKind,
            RenameAction,
            RenamePlan,
            RenameResult,
        )

        assert EntryKind.FILE.value == "file"
        assert RenameAction is not None
        assert RenamePlan is not None
        assert RenameResult is not None

    def test_scanner_functions_importable(self) -> None:
        from restricted_filenames_renamer import build_rename_plan, validate_path_under_root

        assert callable(build_rename_plan)
        assert callable(validate_path_under_root)

    def test_renamer_functions_importable(self) -> None:
        from restricted_filenames_renamer import (
            execute_plan,
            format_plan_summary,
            generate_log_filename,
            write_rename_log,
        )

        assert callable(execute_plan)
        assert callable(format_plan_summary)
        assert callable(generate_log_filename)
        assert callable(write_rename_log)

    def test_main_still_importable(self) -> None:
        from restricted_filenames_renamer import main

        assert callable(main)

    def test_all_is_complete(self) -> None:
        import restricted_filenames_renamer

        expected = {
            "main",
            "sanitize_name",
            "is_name_safe",
            "replace_forbidden_chars",
            "strip_trailing_dots_spaces",
            "handle_reserved_names",
            "truncate_name",
            "FORBIDDEN_CHARS",
            "CONTROL_CHARS",
            "ALL_RESTRICTED_CHARS",
            "UNICODE_CHAR_MAP",
            "UNICODE_DOT_REPLACEMENT",
            "UNICODE_SPACE_REPLACEMENT",
            "DEFAULT_MAX_NAME_LENGTH",
            "WINDOWS_MAX_PATH",
            "EntryKind",
            "RenameAction",
            "RenamePlan",
            "RenameResult",
            "build_rename_plan",
            "validate_path_under_root",
            "execute_plan",
            "format_plan_summary",
            "generate_log_filename",
            "write_rename_log",
            "tui_main",
        }
        actual = set(restricted_filenames_renamer.__all__)
        assert actual == expected
