# restricted-filenames-renamer

A CLI tool, interactive TUI, and Python library that recursively renames files
and directories to be portable across operating systems. It replaces characters
that are forbidden on Windows, handles reserved device names, trailing
dots/spaces, and enforces filename length limits.

By default, restricted characters are replaced with visually similar Unicode
equivalents (fullwidth characters and Control Pictures), following the same
approach used by [rclone](https://rclone.org/overview/#restricted-characters).
This preserves readability while making filenames safe for Windows, macOS, and
Linux.

## When do you need this?

- You store files on Linux/macOS that will be shared with Windows users
  (e.g. via USB drives, network shares, or cloud sync)
- You maintain a NAS or media library accessible from multiple operating systems
- You sync files between platforms using tools like rsync, Syncthing, or rclone
- You prepare archives or datasets that must work everywhere
- You receive files from external sources with problematic names

## Installation

Requires Python 3.11+.

```shell
# Install with uv (recommended)
uv tool install restricted-filenames-renamer

# Or install with pip/pipx
pip install restricted-filenames-renamer
pipx install restricted-filenames-renamer
```

To also install the optional interactive TUI (requires
[Textual](https://textual.textualize.io/)):

```shell
pip install restricted-filenames-renamer[tui]
```

For development setup, see [docs/development.md](docs/development.md).

## Quick start

```shell
# Dry-run: see what would be renamed (no changes made)
restricted-filenames-renamer /path/to/directory

# Apply renames with interactive confirmation
restricted-filenames-renamer /path/to/directory --write

# Apply renames without confirmation
restricted-filenames-renamer /path/to/directory --write --yes

# Verbose output showing detailed issues for each file
restricted-filenames-renamer /path/to/directory --verbose

# Launch the interactive TUI (requires the 'tui' extra)
restricted-filenames-renamer-tui /path/to/directory
```

## What it fixes

| Problem | Example | Default result |
|---|---|---|
| Windows-forbidden characters | `file:name*.txt` | `file：name＊.txt` |
| Control characters in names | `file\x01name.txt` | `file␁name.txt` |
| Trailing dots | `readme.` | `readme．` |
| Trailing spaces | `file .txt` | `file␠.txt` |
| Reserved device names | `CON.txt` | `_CON.txt` |
| Names exceeding length limit | `(255+ chars).txt` | Truncated, extension preserved |

See [docs/restricted-filenames.md](docs/restricted-filenames.md) for the full
character mapping table and detailed background on cross-platform filename
restrictions.

## CLI reference

```
usage: restricted-filenames-renamer [-h] [--write] [--yes] [--replace-char REPLACE_CHAR]
                                    [--max-length MAX_LENGTH] [--follow-symlinks]
                                    [--log-file LOG_FILE] [--verbose] path
```

| Option | Description |
|---|---|
| `path` | Root directory to scan recursively |
| `--write` | Actually perform renames (without this, only a dry-run is shown) |
| `--yes`, `-y` | Skip interactive confirmation when `--write` is used |
| `--replace-char CHAR` | Replace all restricted characters with this single character instead of Unicode equivalents (e.g. `_` or `-`) |
| `--max-length N` | Maximum filename length before truncation (default: 255) |
| `--follow-symlinks` | Follow symbolic links (by default, symlinks are reported but not followed) |
| `--log-file PATH` | Custom path for the JSON rename log |
| `--verbose`, `-v` | Show detailed information about each rename |

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success (or no renames needed) |
| 1 | One or more renames failed |
| 2 | User cancelled the operation |

## Interactive TUI

An optional interactive terminal user interface is available, built with
[Textual](https://textual.textualize.io/). Install it with:

```shell
pip install restricted-filenames-renamer[tui]
```

Then launch it:

```shell
restricted-filenames-renamer-tui /path/to/directory
```

The TUI provides:

- **Settings bar** -- change replace character, max filename length, and symlink
  handling interactively, then re-scan
- **Rename table** -- browse all planned renames with kind, original/new names,
  directory, and issue count
- **Detail panel** -- select a row to see full source/destination paths and all
  issues found for that entry
- **Status log** -- see scan summaries, warnings, and per-file rename results
- **Keyboard shortcuts** -- `r` to re-scan, `a` to apply renames, `q` to quit

The TUI uses the same scan/rename engine as the CLI. All settings (replace char,
max length, symlinks) can be adjusted in the TUI and take effect on re-scan.

## Usage examples

### Dry-run to preview changes

Always run without `--write` first to review what will happen:

```shell
$ restricted-filenames-renamer ~/shared-drive
Scanned 1432 entries under /home/user/shared-drive
Found 3 entries to rename:

  [file] meeting:notes.txt -> meeting：notes.txt
         in /home/user/shared-drive/docs
  [file] budget<2024>.xlsx -> budget＜2024＞.xlsx
         in /home/user/shared-drive/finance
  [dir]  aux -> _aux
         in /home/user/shared-drive/project

Dry-run mode. Use --write to apply changes.
```

### Using a simple replacement character

If you prefer underscores instead of Unicode equivalents:

```shell
restricted-filenames-renamer ~/files --replace-char '_'
```

This replaces all forbidden characters with `_` instead of their fullwidth
Unicode counterparts. Simpler, but less readable when multiple different
characters get replaced.

### Preparing files for Windows from Linux

```shell
# Preview what needs fixing
restricted-filenames-renamer /mnt/nas/media --verbose

# Apply fixes, saving a log for auditing
restricted-filenames-renamer /mnt/nas/media --write --log-file renames.json
```

### Scripted / non-interactive usage

For use in scripts or cron jobs, skip the confirmation prompt:

```shell
restricted-filenames-renamer /data/incoming --write --yes --log-file /var/log/rename.json
```

### Handling symlinks

By default, symlinks are skipped (reported in verbose output). To follow and
rename symlink targets:

```shell
restricted-filenames-renamer /path --follow-symlinks --write
```

### Custom filename length limit

Some systems have shorter limits. To enforce a 200-character maximum:

```shell
restricted-filenames-renamer /path --max-length 200
```

## Library usage

The package can also be used as an importable Python library.

### Checking if a filename is safe

```python
from restricted_filenames_renamer import is_name_safe, sanitize_name

# Quick boolean check
assert is_name_safe("readme.md")
assert not is_name_safe("file:name.txt")

# Get the sanitized name and a list of issues
safe_name, issues = sanitize_name("file:name.txt")
print(safe_name)   # file：name.txt  (fullwidth colon)
print(issues)      # ['Replaced forbidden characters [':']']
```

### Using individual pipeline steps

```python
from restricted_filenames_renamer import (
    replace_forbidden_chars,
    strip_trailing_dots_spaces,
    handle_reserved_names,
    truncate_name,
)

# Each step returns (result, issues)
name, issues = replace_forbidden_chars("file*name?.txt")
name, issues = strip_trailing_dots_spaces("readme.")
name, issues = handle_reserved_names("CON.txt")
name, issues = truncate_name("a" * 300 + ".txt")
```

### Using a simple replacement character

```python
from restricted_filenames_renamer import sanitize_name

# Replace all restricted chars with underscore instead of Unicode
safe_name, issues = sanitize_name("file:name*.txt", replace_char="_")
print(safe_name)  # file_name_.txt
```

### Scanning a directory and building a rename plan

```python
from pathlib import Path
from restricted_filenames_renamer import build_rename_plan, format_plan_summary

plan = build_rename_plan(Path("/path/to/directory"))

# Inspect the plan
print(f"Entries scanned: {plan.total_entries_scanned}")
print(f"Renames needed: {plan.total_renames_needed}")

for action in plan.actions:
    print(f"  {action.source.name} -> {action.final_name}")

# Or use the built-in formatter
print(format_plan_summary(plan, verbose=True))
```

### Executing a rename plan

```python
from pathlib import Path
from restricted_filenames_renamer import build_rename_plan, execute_plan

plan = build_rename_plan(Path("/path/to/directory"))

if plan.has_changes:
    results = execute_plan(plan, log_file=Path("renames.json"))

    for result in results:
        if result.success:
            print(f"OK: {result.action.source.name} -> {result.action.final_name}")
        else:
            print(f"FAIL: {result.action.source.name}: {result.error_message}")
```

### Available constants

```python
from restricted_filenames_renamer import (
    FORBIDDEN_CHARS,          # frozenset of 9 Windows-forbidden chars
    CONTROL_CHARS,            # frozenset of 32 ASCII control chars
    ALL_RESTRICTED_CHARS,     # union of the above
    UNICODE_CHAR_MAP,         # dict mapping each restricted char to its Unicode replacement
    DEFAULT_MAX_NAME_LENGTH,  # 255
    WINDOWS_MAX_PATH,         # 260
)
```

## JSON log format

When `--write` is used, a JSON log is written recording every rename. Example:

```json
{
  "timestamp": "2026-02-10T14:30:00.000000+00:00",
  "root": "/home/user/shared-drive",
  "total_renames": 2,
  "total_errors": 0,
  "renames": [
    {
      "source": "/home/user/shared-drive/docs/meeting:notes.txt",
      "destination": "/home/user/shared-drive/docs/meeting：notes.txt"
    }
  ],
  "errors": []
}
```

This log can be used for auditing or building a rollback script.

## How it works

The tool processes each filename through a four-stage sanitization pipeline:

1. **Forbidden character replacement** -- Windows-forbidden characters
   (`\ / : * ? " < > |`) and ASCII control characters (0x00-0x1F) are replaced
   with visually similar Unicode equivalents
2. **Trailing dot/space handling** -- Trailing dots and spaces (which Windows
   silently strips) are replaced with fullwidth equivalents
3. **Reserved name prefixing** -- Windows reserved device names
   (`CON`, `PRN`, `AUX`, `NUL`, `COM0`-`COM9`, `LPT0`-`LPT9`) are prefixed
   with `_`
4. **Length truncation** -- Names exceeding the limit (default 255) are
   truncated while preserving the file extension

Renames are executed bottom-up (deepest entries first) so that renaming a
directory does not invalidate paths to its children. Naming collisions within
a directory are resolved automatically by appending `_1`, `_2`, etc.

## Further documentation

- [Restricted filenames reference](docs/restricted-filenames.md) -- cross-platform
  filename restrictions, full character mapping table, and caveats
- [Installation](docs/installation.md) -- installing uv and Python
- [Development](docs/development.md) -- development workflows, IDE setup, TUI
  development
- [Publishing](docs/publishing.md) -- publishing releases to PyPI

## License

MIT
