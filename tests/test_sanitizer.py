"""Tests for the sanitizer module — pure function tests, no filesystem access."""

from __future__ import annotations

from restricted_filenames_renamer.sanitizer import (
    UNICODE_CHAR_MAP,
    handle_reserved_names,
    is_name_safe,
    replace_forbidden_chars,
    sanitize_name,
    strip_trailing_dots_spaces,
    truncate_name,
)

# ---------------------------------------------------------------------------
# replace_forbidden_chars  (default = Unicode mode)
# ---------------------------------------------------------------------------


class TestReplaceForbiddenChars:
    def test_backslash(self) -> None:
        result, issues = replace_forbidden_chars("file\\name")
        assert result == "file\uff3cname"  # ＼
        assert len(issues) == 1

    def test_colon(self) -> None:
        result, _ = replace_forbidden_chars("file:name")
        assert result == "file\uff1aname"  # ：

    def test_asterisk(self) -> None:
        result, _ = replace_forbidden_chars("file*name")
        assert result == "file\uff0aname"  # ＊

    def test_question_mark(self) -> None:
        result, _ = replace_forbidden_chars("file?name")
        assert result == "file\uff1fname"  # ？

    def test_double_quote(self) -> None:
        result, _ = replace_forbidden_chars('file"name')
        assert result == "file\uff02name"  # ＂

    def test_less_than(self) -> None:
        result, _ = replace_forbidden_chars("file<name")
        assert result == "file\uff1cname"  # ＜

    def test_greater_than(self) -> None:
        result, _ = replace_forbidden_chars("file>name")
        assert result == "file\uff1ename"  # ＞

    def test_pipe(self) -> None:
        result, _ = replace_forbidden_chars("file|name")
        assert result == "file\uff5cname"  # ｜

    def test_control_char_null(self) -> None:
        result, issues = replace_forbidden_chars("file\x00name")
        assert result == "file\u2400name"  # ␀
        assert len(issues) == 1

    def test_control_char_tab(self) -> None:
        result, _ = replace_forbidden_chars("file\tname")
        assert result == "file\u2409name"  # ␉

    def test_control_char_newline(self) -> None:
        result, _ = replace_forbidden_chars("file\nname")
        assert result == "file\u240aname"  # ␊

    def test_multiple_forbidden(self) -> None:
        result, _ = replace_forbidden_chars("a:b*c?d")
        assert result == "a\uff1ab\uff0ac\uff1fd"

    def test_no_replacement_needed(self) -> None:
        result, issues = replace_forbidden_chars("safe_file.txt")
        assert result == "safe_file.txt"
        assert issues == []

    def test_all_forbidden_chars(self) -> None:
        result, _ = replace_forbidden_chars('\\/:*?"<>|')
        for c in result:
            assert c not in '\\/:*?"<>|'
        assert len(result) == 9

    def test_mixed_control_and_forbidden(self) -> None:
        result, issues = replace_forbidden_chars("a\x01:b")
        assert result == "a\u2401\uff1ab"
        assert len(issues) == 1
        assert "forbidden" in issues[0].lower() or "control" in issues[0].lower()

    def test_each_char_maps_to_unique_unicode(self) -> None:
        """Every restricted char should map to a distinct Unicode character."""
        values = list(UNICODE_CHAR_MAP.values())
        assert len(values) == len(set(values))


# ---------------------------------------------------------------------------
# replace_forbidden_chars  (override with --replace-char)
# ---------------------------------------------------------------------------


class TestReplaceForbiddenCharsOverride:
    def test_custom_replace_char(self) -> None:
        result, _ = replace_forbidden_chars("a:b", "-")
        assert result == "a-b"

    def test_underscore_replace_char(self) -> None:
        result, _ = replace_forbidden_chars("file:name", "_")
        assert result == "file_name"

    def test_all_forbidden_same_char(self) -> None:
        result, _ = replace_forbidden_chars('\\/:*?"<>|', "_")
        assert result == "_________"


# ---------------------------------------------------------------------------
# strip_trailing_dots_spaces  (default = Unicode mode)
# ---------------------------------------------------------------------------


class TestStripTrailingDotsSpaces:
    def test_trailing_dot_unicode(self) -> None:
        result, issues = strip_trailing_dots_spaces("file.")
        assert result == "file\uff0e"  # ．
        assert len(issues) == 1

    def test_trailing_dots_unicode(self) -> None:
        result, _ = strip_trailing_dots_spaces("file...")
        assert result == "file\uff0e\uff0e\uff0e"

    def test_trailing_space_unicode(self) -> None:
        result, issues = strip_trailing_dots_spaces("file ")
        assert result == "file\u2420"  # ␠
        assert len(issues) == 1

    def test_trailing_spaces_unicode(self) -> None:
        result, _ = strip_trailing_dots_spaces("file   ")
        assert result == "file\u2420\u2420\u2420"

    def test_trailing_mixed_unicode(self) -> None:
        result, _ = strip_trailing_dots_spaces("file. .")
        assert result == "file\uff0e\u2420\uff0e"

    def test_only_dots_unicode(self) -> None:
        result, _ = strip_trailing_dots_spaces("...")
        assert result == "\uff0e\uff0e\uff0e"

    def test_only_spaces_unicode(self) -> None:
        result, _ = strip_trailing_dots_spaces("   ")
        assert result == "\u2420\u2420\u2420"

    def test_leading_dot_preserved(self) -> None:
        result, issues = strip_trailing_dots_spaces(".gitignore")
        assert result == ".gitignore"
        assert issues == []

    def test_middle_dot_preserved(self) -> None:
        result, issues = strip_trailing_dots_spaces("file.txt")
        assert result == "file.txt"
        assert issues == []

    def test_no_change(self) -> None:
        result, issues = strip_trailing_dots_spaces("normal")
        assert result == "normal"
        assert issues == []

    def test_extension_trailing_dot_unicode(self) -> None:
        result, _ = strip_trailing_dots_spaces("file.txt.")
        assert result == "file.txt\uff0e"


# ---------------------------------------------------------------------------
# strip_trailing_dots_spaces  (override with --replace-char)
# ---------------------------------------------------------------------------


class TestStripTrailingDotsSpacesOverride:
    def test_trailing_dot_stripped(self) -> None:
        result, _ = strip_trailing_dots_spaces("file.", "_")
        assert result == "file"

    def test_trailing_dots_stripped(self) -> None:
        result, _ = strip_trailing_dots_spaces("file...", "_")
        assert result == "file"

    def test_trailing_space_stripped(self) -> None:
        result, _ = strip_trailing_dots_spaces("file ", "_")
        assert result == "file"

    def test_only_dots_becomes_replace_char(self) -> None:
        result, issues = strip_trailing_dots_spaces("...", "_")
        assert result == "_"
        assert len(issues) == 2  # stripped + empty fallback

    def test_only_spaces_becomes_replace_char(self) -> None:
        result, _ = strip_trailing_dots_spaces("   ", "_")
        assert result == "_"


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

    def test_custom_prefix_char(self) -> None:
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
        name = "." + "a" * 300
        result, _ = truncate_name(name, 255)
        assert len(result) == 255
        assert result.startswith(".")


# ---------------------------------------------------------------------------
# sanitize_name (full pipeline, Unicode mode)
# ---------------------------------------------------------------------------


class TestSanitizeName:
    def test_clean_name(self) -> None:
        result, issues = sanitize_name("readme.md")
        assert result == "readme.md"
        assert issues == []

    def test_forbidden_char_and_trailing_dot(self) -> None:
        result, issues = sanitize_name("file:name.")
        assert result == "file\uff1aname\uff0e"
        assert len(issues) >= 2

    def test_reserved_name_with_extension(self) -> None:
        result, _ = sanitize_name("CON.txt")
        assert result == "_CON.txt"

    def test_colon_becomes_fullwidth(self) -> None:
        result, _ = sanitize_name("file:name.txt")
        assert result == "file\uff1aname.txt"

    def test_combined_issues(self) -> None:
        # Forbidden chars + trailing dots.
        result, issues = sanitize_name("CON:file...")
        # Step 1: "CON：file..."
        # Step 2: "CON：file．．．"
        # Step 3: stem before first dot is "CON：file．．．" -> not reserved
        assert "\uff1a" in result  # fullwidth colon present
        assert len(issues) >= 2

    def test_hidden_file_preserved(self) -> None:
        result, _ = sanitize_name(".gitignore")
        assert result == ".gitignore"

    def test_dotenv_preserved(self) -> None:
        result, _ = sanitize_name(".env")
        assert result == ".env"


# ---------------------------------------------------------------------------
# sanitize_name (override mode with --replace-char)
# ---------------------------------------------------------------------------


class TestSanitizeNameOverride:
    def test_custom_replace_char(self) -> None:
        result, _ = sanitize_name("a:b", replace_char="-")
        assert result == "a-b"

    def test_underscore_override(self) -> None:
        result, _ = sanitize_name("file:name.", replace_char="_")
        assert result == "file_name"

    def test_reserved_name_still_prefixed(self) -> None:
        result, _ = sanitize_name("CON.txt", replace_char="_")
        assert result == "_CON.txt"

    def test_trailing_stripped_in_override(self) -> None:
        result, _ = sanitize_name("file...", replace_char="_")
        assert result == "file"

    def test_all_issues_pipeline_override(self) -> None:
        name = "CON" + ":" * 260 + "."
        result, issues = sanitize_name(name, replace_char="_", max_length=10)
        assert len(result) <= 10
        assert len(issues) >= 3


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
