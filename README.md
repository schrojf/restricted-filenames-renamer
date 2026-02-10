# restricted-filenames-renamer

A CLI tool that recursively renames files and directories to be portable across
operating systems. It replaces characters that are forbidden on Windows, handles
reserved device names, trailing dots/spaces, and enforces filename length limits.

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
- [Development](docs/development.md) -- development workflows, IDE setup
- [Publishing](docs/publishing.md) -- publishing releases to PyPI

## License

MIT
