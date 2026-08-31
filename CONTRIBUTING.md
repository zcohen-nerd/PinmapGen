# Contributing to PinmapGen

Thanks for your interest. This document covers the development workflow,
coding standards, and conventions for contributing to PinmapGen.

## Quick start

1. **Fork and clone:**
   ```bash
   git clone https://github.com/your-username/PinmapGen.git
   cd PinmapGen
   ```

2. **Set up the dev environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # .venv\Scripts\activate     # Windows

   # Optional but recommended: editable install. PinmapGen itself is
   # stdlib-only and runs fine from the repo root without it — this adds
   # the `pinmapgen` command and lets `python -m tools.pinmapgen.cli`
   # work from any directory.
   pip install -e .

   # Optional dev tools (pytest, ruff):
   pip install -e ".[dev]"

   # Install git hooks
   bash .githooks/install-hooks.sh  # Linux/macOS
   pwsh -File .githooks/install-hooks.ps1  # Windows
   ```

3. **Verify everything works:**
   ```bash
   python -m tools.pinmapgen.cli --help
   python -m unittest discover -s tests -v
   ```

## Development workflow

### Creating a feature or fix

1. **Branch off main:**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/issue-description
   ```

2. **Make your changes** following the coding standards below.

3. **Run tests:**
   ```bash
   python -m unittest discover -s tests -v
   python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root . --mermaid
   ```

4. **Commit:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```
   The pre-commit hook validates staged `hardware/exports/*.csv` netlists
   by generating from them in a temp directory - it blocks the commit on
   failure but never stages anything itself.

5. **Push and open a PR:**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit message format

Use conventional commits:

- `feat:` — New features
- `fix:` — Bug fixes
- `docs:` — Documentation changes
- `style:` — Formatting only (no functional changes)
- `refactor:` — Restructuring (no functional changes)
- `test:` — Adding or updating tests
- `chore:` — Build/tooling changes

## Coding standards

### Python style

**Import order:**
```python
# stdlib
import re
import json
from pathlib import Path

# local
from .normalize import normalize_pin_name
from .roles import infer_pin_role
```

**Docstrings** — Google-style with Args/Returns/Raises:
```python
def emit_arduino_header(canonical_dict: dict[str, Any], output_path: Path | str) -> None:
    """Generate Arduino C++ header file from canonical dictionary.

    Args:
        canonical_dict: Canonical pinmap dictionary with pins and metadata.
        output_path: Path to output .h file.

    Raises:
        FileNotFoundError: If output directory cannot be created.
    """
```

**General conventions:**
- Keep functions focused; aim for under 50 lines when practical
- Descriptive names: `pin_assignments` not `pa`, `is_differential_pair` not `is_diff`
- Type hints on all public function signatures (use modern `X | Y` syntax)
- Constants in `UPPER_SNAKE_CASE`; private helpers with leading underscore

**Error handling:**
```python
# Prefer specific exceptions
try:
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
except FileNotFoundError:
    print(f"Error: CSV file not found: {csv_file}")
    return None
except UnicodeDecodeError:
    print(f"Error: Invalid encoding in CSV file: {csv_file}")
    return None
```

### File structure patterns

| Module type | Convention |
|-------------|-----------|
| Parser (`bom_csv.py`, `eagle_sch.py`) | Returns `dict[str, list[str]]` mapping net names to pins. Validates input format and raises on bad data. |
| Emitter (`emit_*.py`) | Accepts `(canonical_dict, output_path)`. Creates parent dirs. Writes UTF-8. Includes auto-generated header. |
| Profile (`profiles/*.toml`) | Declarative pin/peripheral data loaded by `profile_loader.py`; Python `MCUProfile` subclasses are the escape hatch for behavior TOML can't express (registered via `profile_registry`). |

## Adding new features

### New MCU profile

1. Create `tools/pinmapgen/profiles/<mcu>.toml` (schema in `profiles/README.md`) — the registry auto-discovers it.
2. For behavior TOML can't express, subclass `MCUProfile` and register it via `profile_registry.registry.register(name, cls)`.
3. Validate with `python -m tools.pinmapgen.cli profiles check <mcu>`.
4. Add a sample netlist in `hardware/exports/` and test coverage under `tests/`.

### New input format

1. Create a parser module (e.g., `tools/pinmapgen/parse_kicad.py`).
2. Return the standard `dict[str, list[str]]` structure.
3. Wire it into `cli.py` with a new `--kicad` (or similar) argument.
4. Add tests.

### New output format

1. Create `tools/pinmapgen/emit_<format>.py` with a public function like
   `emit_<format>(canonical_dict, output_path)`.
2. Call it from `cli.py` → `generate_outputs()`.
3. Add tests in `tests/test_emitters.py`.

## Testing

All tests use `unittest.TestCase` and need no third-party packages. Run
them with:

```bash
python -m unittest discover -s tests -v
```

(pytest also works if you installed the dev extras: `python -m pytest tests/ -v`.)

When adding tests:
- File naming: `test_<module>.py`
- Method naming: `test_<function>_<condition>`
- Include docstrings explaining what the test validates
- Test edge cases (empty input, malformed data, etc.)
- Keep test data in `tests/fixtures/`

## Documentation

- Update `README.md` when adding major features or CLI flags.
- Keep code docstrings current.
- Add or update guides in `docs/` when workflows change.

## Bug reports

Include:
1. OS, Python version, and PinmapGen commit or version
2. Exact command that triggered the issue
3. Full error output / traceback
4. Minimal CSV or `.sch` that reproduces the problem
5. Expected vs. actual behavior

## Dev tools

- **VS Code tasks** — `Generate Pinmap`, `Watch Pinmap`, `Test PinmapGen CLI`
- **Pre-commit hooks** — Validate staged `hardware/exports/*.csv` netlists (block-on-failure, never stage anything)
- **GitHub Actions** — CI validates outputs stay in sync and tests pass
- **Ruff** — Linter/formatter (config in `pyproject.toml`, line-length 88, double quotes)

## Cutting a release

Releases are built by `.github/workflows/release.yml`, triggered by a
version tag:

1. Bump `[project] version` in `pyproject.toml` (the workflow refuses a
   tag that doesn't match it) and update `_FALLBACK_VERSION` in
   `tools/pinmapgen/cli.py` to the same value.
2. Make sure `main` is green.
3. Tag and push:

   ```bash
   git tag v0.5.0
   git push origin v0.5.0
   ```

The workflow runs the test suite, regenerates the sample outputs with
`--strict`, and publishes a GitHub Release with the source archive, an
installable wheel, and an example bundle. (It can also be run manually
from the Actions tab via *workflow_dispatch*.)
