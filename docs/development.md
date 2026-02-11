# Development

## Setting Up uv

This project is set up to use [uv](https://docs.astral.sh/uv/) to manage Python and
dependencies. First, be sure you
[have uv installed](https://docs.astral.sh/uv/getting-started/installation/).

Then
[fork the schrojf/restricted-filenames-renamer repo](https://github.com/schrojf/restricted-filenames-renamer/fork)
(having your own fork will make it easier to contribute) and
[clone it](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository).

## Basic Developer Workflows

The `Makefile` simply offers shortcuts to `uv` commands for developer convenience.
(For clarity, GitHub Actions don’t use the Makefile and just call `uv` directly.)

```shell
# First, install all dependencies and set up your virtual environment.
# This simply runs `uv sync --all-extras` to install all packages,
# including dev dependencies and optional dependencies.
make install

# Run uv sync, lint, and test:
make

# Build wheel:
make build

# Linting:
make lint

# Run tests:
make test

# Delete all the build artifacts:
make clean

# Upgrade dependencies to compatible versions:
make upgrade

# To run tests by hand:
uv run pytest   # all tests
uv run pytest -s src/module/some_file.py  # one test, showing outputs

# Build and install current dev executables, to let you use your dev copies
# as local tools:
uv tool install --editable .

# Dependency management directly with uv:
# Add a new dependency:
uv add package_name
# Add a development dependency:
uv add --dev package_name
# Update to latest compatible versions (including dependencies on git repos):
uv sync --upgrade
# Update a specific package:
uv lock --upgrade-package package_name
# Update dependencies on a package:
uv add package_name@latest

# Run a shell within the Python environment:
uv venv
source .venv/bin/activate
```

See [uv docs](https://docs.astral.sh/uv/) for details.

## Optional TUI

The project includes an optional interactive TUI built with
[Textual](https://textual.textualize.io/). Textual is declared as an optional
dependency under the `tui` extra:

```shell
# End users install the TUI with:
pip install restricted-filenames-renamer[tui]
```

For development, `make install` (which runs `uv sync --all-extras`) automatically
installs the TUI dependency along with `textual-dev` (Textual's developer tools)
and `pytest-asyncio` (for async TUI tests). No extra steps are needed.

The TUI lives in `src/restricted_filenames_renamer/tui.py` and its tests are in
`tests/test_tui.py`. Tests use Textual's
[pilot](https://textual.textualize.io/guide/testing/) framework for headless
async testing.

To run the TUI during development:

```shell
uv run restricted-filenames-renamer-tui /path/to/directory
```

## IDE setup

If you use VSCode or a fork like Cursor or Windsurf, you can install the following
extensions:

- [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)

- [Based Pyright](https://marketplace.visualstudio.com/items?itemName=detachhead.basedpyright)
  for type checking. Note that this extension works with non-Microsoft VSCode forks like
  Cursor.

## Publishing Releases

See [publishing.md](publishing.md) for instructions on publishing to PyPI.

## Documentation

- [Restricted filenames reference](restricted-filenames.md) -- cross-platform
  filename restrictions and the Unicode replacement strategy
- [uv docs](https://docs.astral.sh/uv/)
- [basedpyright docs](https://docs.basedpyright.com/latest/)

* * *

*This file was built with
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
