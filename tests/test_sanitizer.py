"""Tests for the sanitizer module — pure function tests, no filesystem access."""

from __future__ import annotations

from restricted_filenames_renamer.sanitizer import (
    handle_reserved_names,
    is_name_safe,
    replace_forbidden_chars,
    sanitize_name,
    strip_trailing_dots_spaces,
    truncate_name,
)

# ---------------------------------------------------------------------------
# replace_forbidden_chars
# ---------------------------------------------------------------------------


class TestReplaceForbiddenChars:
    def test_backslash(self) -> None:
        result, issues = replace_forbidden_chars("file\\name")
        assert result == "file_name"
        assert len(issues) == 1

    def test_colon(self) -> None:
        result, _ = replace_forbidden_chars("file:name")
        assert result == "file_name"

    def test_asterisk(self) -> None:
        result, _ = replace_forbidden_chars("file*name")
        assert result == "file_name"

    def test_question_mark(self) -> None:
        result, _ = replace_forbidden_chars("file?name")
        assert result == "file_name"

    def test_double_quote(self) -> None:
        result, _ = replace_forbidden_chars('file"name')
        assert result == "file_name"

    def test_less_than(self) -> None:
        result, _ = replace_forbidden_chars("file<name")
        assert result == "file_name"

    def test_greater_than(self) -> None:
        result, _ = replace_forbidden_chars("file>name")
        assert result == "file_name"

    def test_pipe(self) -> None:
        result, _ = replace_forbidden_chars("file|name")
        assert result == "file_name"

    def test_control_char_null(self) -> None:
        result, issues = replace_forbidden_chars("file\x00name")
        assert result == "file_name"
        assert len(issues) == 1

    def test_control_char_tab(self) -> None:
        result, _ = replace_forbidden_chars("file\tname")
        assert result == "file_name"

    def test_control_char_newline(self) -> None:
        result, _ = replace_forbidden_chars("file\nname")
        assert result == "file_name"

    def test_multiple_forbidden(self) -> None:
        result, _ = replace_forbidden_chars("a:b*c?d")
        assert result == "a_b_c_d"

    def test_custom_replace_char(self) -> None:
        result, _ = replace_forbidden_chars("a:b", "-")
        assert result == "a-b"

    def test_no_replacement_needed(self) -> None:
        result, issues = replace_forbidden_chars("safe_file.txt")
        assert result == "safe_file.txt"
        assert issues == []

    def test_all_forbidden_chars(self) -> None:
        result, _ = replace_forbidden_chars('\\/:*?"<>|')
        assert result == "_________"

    def test_mixed_control_and_forbidden(self) -> None:
        result, issues = replace_forbidden_chars("a\x01:b")
        assert result == "a__b"
        assert len(issues) == 1
        assert "forbidden" in issues[0].lower() or "control" in issues[0].lower()


# ---------------------------------------------------------------------------
# strip_trailing_dots_spaces
# ---------------------------------------------------------------------------


class TestStripTrailingDotsSpaces:
    def test_trailing_dot(self) -> None:
        result, issues = strip_trailing_dots_spaces("file.")
        assert result == "file"
        assert len(issues) == 1

    def test_trailing_dots(self) -> None:
        result, _ = strip_trailing_dots_spaces("file...")
        assert result == "file"

    def test_trailing_space(self) -> None:
        result, issues = strip_trailing_dots_spaces("file ")
        assert result == "file"
        assert len(issues) == 1

    def test_trailing_spaces(self) -> None:
        result, _ = strip_trailing_dots_spaces("file   ")
        assert result == "file"

    def test_trailing_mixed(self) -> None:
        result, _ = strip_trailing_dots_spaces("file. .")
        assert result == "file"

    def test_leading_dot_preserved(self) -> None:
        result, issues = strip_trailing_dots_spaces(".gitignore")
        assert result == ".gitignore"
        assert issues == []

    def test_middle_dot_preserved(self) -> None:
        result, issues = strip_trailing_dots_spaces("file.txt")
        assert result == "file.txt"
        assert issues == []

    def test_only_dots_becomes_replace_char(self) -> None:
        result, issues = strip_trailing_dots_spaces("...")
        assert result == "_"
        assert len(issues) == 2  # stripped + empty fallback

    def test_only_spaces_becomes_replace_char(self) -> None:
        result, _ = strip_trailing_dots_spaces("   ")
        assert result == "_"

    def test_no_change(self) -> None:
        result, issues = strip_trailing_dots_spaces("normal")
        assert result == "normal"
        assert issues == []

    def test_extension_trailing_dot(self) -> None:
        result, _ = strip_trailing_dots_spaces("file.txt.")
        assert result == "file.txt"


# ---------------------------------------------------------------------------
# handle_reserved_names
# ---------------------------------------------------------------------------


class TestHandleReservedNames:
    def test_con(self) -> None:
        result, issues = handle_reserved_names("CON")
        assert result == "_CON"
        assert len(issues) == 1

    def test_prn(self) -> None:
        result, _ = handle_reserved_names("PRN")
        assert result == "_PRN"

    def test_aux(self) -> None:
        result, _ = handle_reserved_names("AUX")
        assert result == "_AUX"

    def test_nul(self) -> None:
        result, _ = handle_reserved_names("NUL")
        assert result == "_NUL"

    def test_com1(self) -> None:
        result, _ = handle_reserved_names("COM1")
        assert result == "_COM1"

    def test_com0(self) -> None:
        result, _ = handle_reserved_names("COM0")
        assert result == "_COM0"

    def test_lpt0(self) -> None:
        result, _ = handle_reserved_names("LPT0")
        assert result == "_LPT0"

    def test_lpt9(self) -> None:
        result, _ = handle_reserved_names("LPT9")
        assert result == "_LPT9"

    def test_case_insensitive(self) -> None:
        result, _ = handle_reserved_names("con")
        assert result == "_con"

    def test_mixed_case(self) -> None:
        result, _ = handle_reserved_names("Con")
        assert result == "_Con"

    def test_with_extension(self) -> None:
        result, _ = handle_reserved_names("CON.txt")
        assert result == "_CON.txt"

    def test_with_multiple_extensions(self) -> None:
        result, _ = handle_reserved_names("CON.log.bak")
        assert result == "_CON.log.bak"

    def test_not_reserved_conx(self) -> None:
        result, issues = handle_reserved_names("CONX")
        assert result == "CONX"
        assert issues == []

    def test_not_reserved_com10(self) -> None:
        result, issues = handle_reserved_names("COM10")
        assert result == "COM10"
        assert issues == []

    def test_not_reserved_lpt(self) -> None:
        result, issues = handle_reserved_names("LPT")
        assert result == "LPT"
        assert issues == []

    def test_normal_file(self) -> None:
        result, issues = handle_reserved_names("readme.md")
        assert result == "readme.md"
        assert issues == []

    def test_custom_replace_char(self) -> None:
        result, _ = handle_reserved_names("CON", "-")
        assert result == "-CON"


# ---------------------------------------------------------------------------
# truncate_name
# ---------------------------------------------------------------------------


class TestTruncateName:
    def test_no_truncation_needed(self) -> None:
        result, issues = truncate_name("short.txt")
        assert result == "short.txt"
        assert issues == []

    def test_truncate_long_name(self) -> None:
        name = "a" * 300
        result, issues = truncate_name(name, 255)
        assert len(result) == 255
        assert len(issues) == 1

    def test_preserves_extension(self) -> None:
        name = "a" * 260 + ".txt"
        result, _ = truncate_name(name, 255)
        assert result.endswith(".txt")
        assert len(result) == 255

    def test_no_extension(self) -> None:
        name = "a" * 300
        result, _ = truncate_name(name, 255)
        assert len(result) == 255
        assert result == "a" * 255

    def test_very_long_extension(self) -> None:
        name = "a." + "b" * 300
        result, _ = truncate_name(name, 255)
        assert len(result) == 255

    def test_exact_max_length(self) -> None:
        name = "a" * 255
        result, issues = truncate_name(name, 255)
        assert result == name
        assert issues == []

    def test_hidden_file_no_extension(self) -> None:
        # ".longname" — the dot is at index 0, so rfind returns 0, treated as no extension.
        name = "." + "a" * 300
        result, _ = truncate_name(name, 255)
        assert len(result) == 255
        assert result.startswith(".")


# ---------------------------------------------------------------------------
# sanitize_name (full pipeline)
# ---------------------------------------------------------------------------


class TestSanitizeName:
    def test_clean_name(self) -> None:
        result, issues = sanitize_name("readme.md")
        assert result == "readme.md"
        assert issues == []

    def test_forbidden_char_and_trailing_dot(self) -> None:
        result, issues = sanitize_name("file:name.")
        assert result == "file_name"
        assert len(issues) >= 2

    def test_reserved_name_after_char_replacement(self) -> None:
        # If forbidden chars are replaced and the result becomes a reserved name,
        # e.g. "CO:N" -> "CO_N" which is NOT reserved. This should pass through.
        result, _ = sanitize_name("CO:N")
        assert result == "CO_N"

    def test_reserved_name_with_extension(self) -> None:
        result, _ = sanitize_name("CON.txt")
        assert result == "_CON.txt"

    def test_combined_issues(self) -> None:
        # Forbidden chars + trailing dots + reserved name.
        result, issues = sanitize_name("CON:file...")
        # Step 1: "CON:file..." -> "CON_file..."
        # Step 2: "CON_file..." -> "CON_file"
        # Step 3: "CON_file" stem is "CON_file", not reserved -> no change
        assert result == "CON_file"
        assert len(issues) >= 2

    def test_all_issues_pipeline(self) -> None:
        # Name that triggers every step.
        # Forbidden char + trailing dot + reserved stem + over length
        name = "CON" + ":" * 260 + "."
        result, issues = sanitize_name(name, max_length=10)
        # After step 1: "CON" + "_" * 260 + "."
        # After step 2: "CON" + "_" * 260
        # After step 3: not reserved (stem is "CON___...")
        # After step 4: truncated to 10
        assert len(result) <= 10
        assert len(issues) >= 3

    def test_custom_replace_char(self) -> None:
        result, _ = sanitize_name("a:b", replace_char="-")
        assert result == "a-b"

    def test_hidden_file_preserved(self) -> None:
        result, _ = sanitize_name(".gitignore")
        assert result == ".gitignore"

    def test_dotenv_preserved(self) -> None:
        result, _ = sanitize_name(".env")
        assert result == ".env"


# ---------------------------------------------------------------------------
# is_name_safe
# ---------------------------------------------------------------------------


class TestIsNameSafe:
    def test_safe_name(self) -> None:
        assert is_name_safe("readme.md") is True

    def test_unsafe_colon(self) -> None:
        assert is_name_safe("file:name") is False

    def test_unsafe_reserved(self) -> None:
        assert is_name_safe("CON") is False

    def test_unsafe_trailing_dot(self) -> None:
        assert is_name_safe("file.") is False

    def test_unsafe_long_name(self) -> None:
        assert is_name_safe("a" * 300) is False

    def test_safe_long_name_within_limit(self) -> None:
        assert is_name_safe("a" * 255) is True
