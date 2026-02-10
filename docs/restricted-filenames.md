# Restricted filenames reference

This document explains the cross-platform filename restrictions that
`restricted-filenames-renamer` addresses, the Unicode replacement strategy it
uses, and caveats to be aware of.

## Background

Different operating systems impose different rules on what constitutes a valid
filename. Files created on Linux or macOS may use characters that are forbidden
on Windows. When these files are copied, synced, or shared across platforms,
the problematic names cause errors, silent truncation, or data loss.

`restricted-filenames-renamer` makes filenames portable by renaming them in
place, before they cause problems on the target system.

## Platform comparison

### Windows (NTFS, FAT32, exFAT)

Windows has the most restrictive filename rules:

- **Forbidden characters:** `\ / : * ? " < > |`
- **Control characters:** bytes 0x00 through 0x1F are not allowed
- **Reserved device names:** `CON`, `PRN`, `AUX`, `NUL`, `COM0`-`COM9`,
  `LPT0`-`LPT9` (case-insensitive, with or without extensions --
  `con.txt` is equally forbidden)
- **Trailing dots and spaces:** Windows silently strips trailing `.` and space
  characters from filenames. A file saved as `readme.` becomes `readme` on disk.
- **Name length limit:** 255 characters per path component (individual filename
  or directory name)
- **Path length limit:** 260 characters total by default (`MAX_PATH`), though
  this can be extended to ~32,767 via registry/manifest settings

### macOS (APFS, HFS+)

- **Forbidden characters:** `/` and NUL (0x00) only
- **Colon restriction:** The Finder displays `:` as `/` (and vice versa) due to
  a legacy mapping from classic Mac OS. Creating a file with `:` in Terminal
  works but shows as `/` in Finder, which causes confusion.
- **Name length limit:** 255 characters (APFS) or 255 bytes in UTF-8 (HFS+)
- **No reserved names**

### Linux (ext4, Btrfs, XFS, ZFS)

- **Forbidden characters:** `/` and NUL (0x00) only
- **Name length limit:** 255 bytes (not characters) for most filesystems
- **No reserved names**
- **No trailing-character stripping**

Linux is the most permissive, which means files created on Linux are the most
likely to be problematic on other platforms.

## The Unicode replacement strategy

Instead of replacing restricted characters with a generic placeholder like `_`,
which loses information about what the original character was and can cause
collisions (e.g. `a:b` and `a*b` would both become `a_b`), this tool uses
**visually similar Unicode replacements**.

This approach is inspired by [rclone's encoding system](https://rclone.org/overview/#restricted-characters).
Each restricted character is mapped to a Unicode character that looks similar
but is not restricted on any platform.

### Forbidden character mapping

Windows-forbidden characters are replaced with their fullwidth Unicode
equivalents:

| Character | Name | Unicode replacement | Replacement name |
|---|---|---|---|
| `\` | Reverse solidus | `＼` U+FF3C | Fullwidth reverse solidus |
| `/` | Solidus | `／` U+FF0F | Fullwidth solidus |
| `:` | Colon | `：` U+FF1A | Fullwidth colon |
| `*` | Asterisk | `＊` U+FF0A | Fullwidth asterisk |
| `?` | Question mark | `？` U+FF1F | Fullwidth question mark |
| `"` | Quotation mark | `＂` U+FF02 | Fullwidth quotation mark |
| `<` | Less-than sign | `＜` U+FF1C | Fullwidth less-than sign |
| `>` | Greater-than sign | `＞` U+FF1E | Fullwidth greater-than sign |
| `\|` | Vertical line | `｜` U+FF5C | Fullwidth vertical line |

### Control character mapping

ASCII control characters (0x00-0x1F) are replaced with Unicode Control Pictures
(U+2400-U+241F):

| Character | Value | Unicode replacement |
|---|---|---|
| NUL | 0x00 | `␀` U+2400 |
| SOH | 0x01 | `␁` U+2401 |
| STX | 0x02 | `␂` U+2402 |
| ETX | 0x03 | `␃` U+2403 |
| EOT | 0x04 | `␄` U+2404 |
| ENQ | 0x05 | `␅` U+2405 |
| ACK | 0x06 | `␆` U+2406 |
| BEL | 0x07 | `␇` U+2407 |
| BS | 0x08 | `␈` U+2408 |
| HT | 0x09 | `␉` U+2409 |
| LF | 0x0A | `␊` U+240A |
| VT | 0x0B | `␋` U+240B |
| FF | 0x0C | `␌` U+240C |
| CR | 0x0D | `␍` U+240D |
| SO | 0x0E | `␎` U+240E |
| SI | 0x0F | `␏` U+240F |
| DLE | 0x10 | `␐` U+2410 |
| DC1 | 0x11 | `␑` U+2411 |
| DC2 | 0x12 | `␒` U+2412 |
| DC3 | 0x13 | `␓` U+2413 |
| DC4 | 0x14 | `␔` U+2414 |
| NAK | 0x15 | `␕` U+2415 |
| SYN | 0x16 | `␖` U+2416 |
| ETB | 0x17 | `␗` U+2417 |
| CAN | 0x18 | `␘` U+2418 |
| EM | 0x19 | `␙` U+2419 |
| SUB | 0x1A | `␚` U+241A |
| ESC | 0x1B | `␛` U+241B |
| FS | 0x1C | `␜` U+241C |
| GS | 0x1D | `␝` U+241D |
| RS | 0x1E | `␞` U+241E |
| US | 0x1F | `␟` U+241F |

### Trailing character mapping

| Trailing character | Unicode replacement | Replacement name |
|---|---|---|
| `.` (dot) | `．` U+FF0E | Fullwidth full stop |
| ` ` (space) | `␠` U+2420 | Symbol for space |

Only trailing dots and spaces are replaced. Dots and spaces in other positions
are left unchanged.

### Reserved name handling

Reserved names are prefixed with `_` rather than character-replaced:

| Original | Result |
|---|---|
| `CON` | `_CON` |
| `PRN.txt` | `_PRN.txt` |
| `aux` | `_aux` |
| `NUL` | `_NUL` |
| `com1` | `_com1` |
| `LPT3.log` | `_LPT3.log` |

The match is case-insensitive on the stem (part before the first `.`).

## Collision resolution

When sanitizing filenames produces duplicates within the same directory, the
tool resolves collisions automatically by appending `_1`, `_2`, etc. before the
file extension.

For example, if a directory contains both `a:b.txt` and `a*b.txt`, and you use
`--replace-char '_'`, both would become `a_b.txt`. The tool resolves this:

- `a:b.txt` -> `a_b.txt`
- `a*b.txt` -> `a_b_1.txt`

With the default Unicode mode, this collision does not occur because `:` and `*`
map to different Unicode characters (`：` and `＊`).

## Programmatic usage

All sanitization functions and data types are available as a Python library:

```python
from restricted_filenames_renamer import (
    # High-level API
    sanitize_name,
    is_name_safe,
    build_rename_plan,
    execute_plan,
    format_plan_summary,

    # Individual pipeline steps
    replace_forbidden_chars,
    strip_trailing_dots_spaces,
    handle_reserved_names,
    truncate_name,

    # Data types
    EntryKind,
    RenameAction,
    RenamePlan,
    RenameResult,

    # Constants
    FORBIDDEN_CHARS,
    CONTROL_CHARS,
    ALL_RESTRICTED_CHARS,
    UNICODE_CHAR_MAP,
    DEFAULT_MAX_NAME_LENGTH,
    WINDOWS_MAX_PATH,
)
```

The sanitizer functions are pure (no filesystem access) and can be used to
validate or transform individual filenames without scanning a directory. The
scanner and renamer functions provide the full directory-walking and renaming
workflow.

See the [README](../README.md#library-usage) for detailed examples.

## Caveats

### Fullwidth Unicode characters in existing filenames

If your files already contain fullwidth Unicode characters (e.g. `＊`, `？`,
`：`) -- which are common in Chinese and Japanese text -- the tool will not
modify them, since they are not restricted characters.

However, be aware of an interaction when using such files with rclone or similar
tools: rclone uses the same fullwidth characters as replacements for restricted
characters, and performs the reverse mapping when uploading. This means a file
originally named `Test：1.jpg` (with a fullwidth colon) could be converted to
`Test:1.jpg` by rclone when uploading to a remote, since rclone assumes the
fullwidth colon was a replacement it made earlier.

This edge case is inherent to any system that uses fullwidth characters as
replacements. For files with East Asian text where fullwidth punctuation is the
norm, consider using `--replace-char '_'` to avoid this ambiguity.

### One-way operation

Renaming is a one-way operation. The tool writes a JSON log of all renames
performed, which you can use to build a rollback script if needed, but there
is no built-in undo command. Always use the dry-run mode first to review
changes.

### Path length warnings

The tool warns when the full path (not just the filename) exceeds the Windows
`MAX_PATH` limit of 260 characters. This can happen even when individual
filenames are within the 255-character limit, due to deep directory nesting.

Resolving path-length issues may require restructuring directories rather than
just renaming files, which is beyond the scope of this tool.

### Symbolic links

By default, symbolic links are skipped and reported. Use `--follow-symlinks` to
process them. Note that following symlinks can cause the tool to process files
outside the specified root directory if symlinks point elsewhere.

### Filesystem encoding

This tool assumes filenames are valid UTF-8 (or the system's native encoding as
reported by Python). Filenames with invalid byte sequences (e.g. from a
latin1-encoded filesystem mounted without proper encoding options) may cause
errors. Fix the filesystem encoding or mount options first.
