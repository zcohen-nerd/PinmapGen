<!-- PinmapGen — Copilot workspace instructions -->
<!-- Last reviewed: 2026-02-24 -->

## Project Overview

PinmapGen is a **Python 3.11+ stdlib-only** toolchain that converts Fusion 360
Electronics / EAGLE CAD exports (CSV netlists, `.sch` schematics) into
firmware-ready pin-mapping artefacts: MicroPython modules, Arduino headers,
JSON, Markdown docs, and Mermaid diagrams. It targets **RP2040**, **STM32G0**,
and **ESP32** MCUs via an extensible profile system.

**Author:** Zachary Cohen  
**License:** PinmapGen Community License (free non-commercial; commercial requires license)  
**Entry point:** `python -m tools.pinmapgen.cli`  
**Package name (pyproject):** `pinmapgen`  

---

## Architecture & Data Flow

```
Input (CSV / .sch)
   │  bom_csv.parse_csv()  or  eagle_sch.parse_schematic()
   ▼
Raw nets: dict[str, list[str]]   {net_name → [pin, …]}
   │  MCUProfile.create_canonical_pinmap()
   │  ├─ normalize_pin_name()     (GPIOxx → GPxx, PAxn, etc.)
   │  ├─ validate_pinmap()        (duplicates, lonely diff pairs, multi-pin nets)
   │  ├─ detect_differential_pairs()
   │  └─ roles.RoleInferencer     (net name → PinRole enum)
   ▼
Canonical dict:
  { mcu, pins, differential_pairs, metadata }
   │
   ├──► emit_json.emit_json()           → pinmaps/pinmap.json
   ├──► emit_micropython.emit_micropython() → firmware/micropython/pinmap_micropython.py
   ├──► emit_arduino.emit_arduino_header()  → firmware/include/pinmap_arduino.h
   ├──► emit_markdown.emit_markdown_docs()  → firmware/docs/PINOUT.md
   └──► emit_mermaid.emit_mermaid_diagram() → firmware/docs/pinout.mmd  (opt-in --mermaid)
```

### Key types

- **Canonical dict** – the single source of truth passed to every emitter:
  ```python
  {
    "mcu": "rp2040",
    "pins": { "I2C0_SDA": ["GP0"], … },
    "differential_pairs": [ {"positive": …, "negative": …} ],
    "metadata": { "total_nets", "total_pins", "differential_pairs_count",
                  "special_pins_used", "validation_warnings", "validation_errors" }
  }
  ```
- **`PinRole` (enum)** – I2C_SDA, UART_TX, SPI_MOSI, ADC, PWM, LED, USB_DP, …
- **`PinInfo` (dataclass)** – per-pin capabilities, special functions, warnings
- **`MCUProfile` (ABC)** – override `_initialize_pin_definitions()`,
  `_initialize_peripherals()`, and `normalize_pin_name()`.

---

## Directory Layout

```
tools/pinmapgen/         ← core package (stdlib only)
  cli.py                 ← argparse CLI, orchestrates pipeline
  watch.py               ← polling-based SimpleFileWatcher
  bom_csv.py             ← CSV parser (csv.DictReader); columns: Net,Pin,Component,RefDes
  eagle_sch.py           ← EAGLE .sch XML parser (xml.etree)
  normalize.py           ← legacy RP2040Profile (duplicate of rp2040_profile)
  roles.py               ← PinRole enum, RoleInferencer, PinInfo dataclass
  mcu_profiles.py        ← MCUProfile ABC + PinCapability, PinInfo, PeripheralInfo
  rp2040_profile.py      ← RP2040 concrete profile
  stm32g0_profile.py     ← STM32G0 concrete profile
  esp32_profile.py       ← ESP32 concrete profile
  emit_json.py           ← JSON emitter (with role enrichment)
  emit_micropython.py    ← MicroPython .py emitter
  emit_arduino.py        ← Arduino .h emitter
  emit_markdown.py       ← PINOUT.md emitter
  emit_mermaid.py        ← Mermaid .mmd emitter

hardware/exports/        ← sample / real netlist CSVs & .sch files
tests/                   ← unittest suite (30 tests, all passing)
  fixtures/              ← minimal_netlist.csv (different column order: Part,Designator,Footprint,Quantity,Designation,Supplier and ref,Pin,Net)
examples/                ← three worked examples: simple_led, sensor_hub, communication_module
  */generated/           ← pre-generated output for each example
firmware/                ← default output location when --out-root is '.'
pinmaps/                 ← default pinmap.json location
fusion_addin/            ← Fusion 360 ULP scripts
docs/                    ← usage, troubleshooting, extending, workflows, output-formats, faq
```

---

## Module Responsibilities & Conventions

| Module | Purpose | Notes |
|--------|---------|-------|
| `bom_csv.py` | Parse Fusion/EAGLE CSV exports | Requires columns: `Net, Pin, Component, RefDes`; whitespace-stripped; empty rows skipped |
| `eagle_sch.py` | Parse EAGLE XML `.sch` files | Walks `drawing/schematic/sheets/sheet/nets/net/segment/pinref` |
| `normalize.py` | **Legacy** RP2040 normalizer | Duplicates `rp2040_profile.py`; kept for backward compat; `get_mcu_profile()` only supports rp2040 |
| `roles.py` | Net-name → PinRole inference | Regex-based pattern matching; `PinRoleInferrer` is alias for `RoleInferencer` |
| `mcu_profiles.py` | ABC for MCU profiles | `MCUProfile.create_canonical_pinmap()` is the canonical dict factory |
| `rp2040_profile.py` | RP2040 (GP0–GP29) | USB pins: GP24=DM, GP25=DP; ADC: GP26–GP29; SMPS: GP23 |
| `stm32g0_profile.py` | STM32G071 48-pin | Port-based naming (PAxn); SWD=PA13/PA14; Boot=PB2; Crystal=PC14-15, PF0-1 |
| `esp32_profile.py` | ESP32-WROOM-32 | GPIOxx naming; strapping pins 0,2,5,12,15; input-only 34-39; ADC2+WiFi conflict |
| `emit_*.py` | Output generators | All accept `(canonical_dict, output_path)`, create parent dirs, write UTF-8 |
| `cli.py` | CLI entry point | `MCU_PROFILES` registry dict; `main()` orchestrates parse → normalize → emit |
| `watch.py` | File watcher | stdlib `time.sleep` polling; invokes CLI via `subprocess.run` |

---

## CSV Format

The **primary** CSV format expected by `bom_csv.py` has these exact headers:
```
Net,Pin,Component,RefDes
```
The `fixtures/minimal_netlist.csv` uses a **different** BOM-style format with columns `Part,Designator,Footprint,Quantity,Designation,Supplier and ref,Pin,Net` — this is parsed by the same `parse_csv()` as long as `Net,Pin,Component,RefDes` subset is present; however the fixture currently uses `Designator` not `RefDes`, so it would fail with the standard parser. This is a known inconsistency; the fixture is only used for visual reference.

---

## Rules for Editing This Project

### General
1. **Stdlib only** – no third-party runtime dependencies. `pyproject.toml` has zero `[project.dependencies]`. Dev tools (pytest, ruff) are dev-only.
2. **Python 3.11+** required (uses `X | Y` type unions, `match` statements are not yet used but are available).
3. **Ruff** is the linter/formatter. Config is in `pyproject.toml` with line-length 88, double quotes, space indent. Run `ruff check` and `ruff format` before committing.
4. **All tests must pass** (`python -m pytest tests/ -v`). Currently 30 tests, 0 failures.
5. **Canonical dict is the contract** between parsers and emitters. Never change its schema without updating all emitters and tests.

### Adding a New MCU Profile
1. Create `tools/pinmapgen/<mcu>_profile.py` subclassing `MCUProfile` from `mcu_profiles.py`.
2. Implement `_initialize_pin_definitions()`, `_initialize_peripherals()`, `normalize_pin_name()`.
3. Register in `cli.py` → `MCU_PROFILES` dict.
4. Add sample netlist in `hardware/exports/` and test coverage.

### Adding a New Emitter
1. Create `tools/pinmapgen/emit_<format>.py` with a public function like `emit_<format>(canonical_dict, output_path)`.
2. Call it from `cli.py` → `generate_outputs()`.
3. Add test in `tests/test_emitters.py`.

### Editing Emitters
- Every emitter auto-creates output directories via `output_path.parent.mkdir(parents=True, exist_ok=True)`.
- Emitters that use role analysis import from `roles.py` and call `analyze_roles()`.
- Pin constants use `_sanitize_net_name()` (shared pattern: strip non-alnum, uppercase, no leading digits).
- MicroPython literals: `GP<n>` → bare int; `GPIO<n>` → quoted string; `P<port><n>` → quoted string.
- Arduino defines: always extract numeric part from pin name for `#define` value.

### Editing Parsers
- `bom_csv.py` validates required columns `{Net, Pin, Component, RefDes}` and raises `ValueError` on mismatch.
- `eagle_sch.py` validates EAGLE XML structure (root tag `eagle`, `drawing/schematic` section).
- Both return `dict[str, list[str]]` mapping net names to pin lists.

### Editing Normalization / Profiles
- `normalize.py` contains a **legacy duplicate** of RP2040 logic. The real profiles live in `*_profile.py` files.
- `mcu_profiles.py` `create_canonical_pinmap()` handles: normalization → validation → diff-pair detection → role inference → canonical dict assembly.
- Validation prints warnings but does NOT raise on validation_errors (only prints them). The legacy `normalize.py` RP2040Profile **does** raise on validation errors. This is an inconsistency.

### Testing
- Tests use `unittest.TestCase` (not pytest fixtures).
- Integration test spawns CLI as subprocess.
- Temp dirs via `tempfile.mkdtemp()` cleaned in `tearDown()`.
- Test canonical dicts use `pins` as `dict[str, list[str]]` (pre-role-enrichment format).

### Style & Conventions
- Docstrings: Google-style with Args/Returns/Raises.
- Type hints on all public function signatures using modern syntax (`Path | str`, `dict[str, list[str]]`).
- Constants: UPPER_SNAKE_CASE.
- Private methods: single underscore prefix.
- Imports: absolute from package root (`from .roles import ...`).

---

## Known Issues / Technical Debt

1. **`normalize.py` duplicates `rp2040_profile.py`** – the old `RP2040Profile` in normalize.py does not use the `mcu_profiles.MCUProfile` ABC. The CLI uses the profile-based one from `rp2040_profile.py`.
2. **`fixtures/minimal_netlist.csv` uses different column names** (`Designator` vs `RefDes`, `Part` header) — not fully compatible with `bom_csv.parse_csv()`.
3. **Validation error handling inconsistency** – `mcu_profiles.MCUProfile.create_canonical_pinmap()` prints errors; legacy `normalize.RP2040Profile.create_canonical_pinmap()` raises.
4. **Timestamps in output** prevent true deterministic/reproducible builds.
5. **`emit_arduino.py` `_get_pin_comment()` hardcodes RP2040 special pin names** — not MCU-agnostic.
6. **`emit_mermaid.py` assumes `GP<n>` pin format** in `_group_pins_by_function()` via `re.match(r"GP(\d+)", pin)`.
7. **Example netlists use inconsistent CSV column orders** — `simple_led`, `sensor_hub`, `communication_module` use `RefDes,Pin,Component,Net` order (works because DictReader is order-agnostic), but `RefDes` is column name not `Designator`.
8. **ESP32 netlist** uses `Component,RefDes,Pin,Net` column order (different from the primary `Net,Pin,Component,RefDes`). Works with DictReader but could confuse contributors.

---

## VS Code Tasks

- **Generate Pinmap** – runs CLI with sample_netlist.csv, rp2040, U1, --mermaid
- **Watch Pinmap** – runs watch.py on hardware/exports/ with --mermaid --interval 1.0
- **Test PinmapGen CLI** – runs `--help`

---

## How to Run

```powershell
# Activate venv
.\.venv\Scripts\Activate.ps1

# Run tests
python -m pytest tests/ -v

# Generate pinmaps
python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root . --mermaid -v

# Watch for changes
python -m tools.pinmapgen.watch hardware/exports/ --mermaid --interval 1.0
```
- Work through each checklist item systematically.
- Keep communication concise and focused.
- Follow development best practices.