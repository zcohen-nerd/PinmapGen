# PinmapGen — Fusion Electronics Pinmap Toolchain

[![License: Custom](https://img.shields.io/badge/License-PinmapGen%20Community-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![CI/CD](https://img.shields.io/github/actions/workflow/status/zcohen-nerd/PinmapGen/ci.yml?branch=main&label=CI%2FCD)](https://github.com/zcohen-nerd/PinmapGen/actions)
[![Issues](https://img.shields.io/github/issues/zcohen-nerd/PinmapGen)](https://github.com/zcohen-nerd/PinmapGen/issues)

PinmapGen converts Fusion 360 Electronics / EAGLE CAD exports (CSV netlists,
`.sch` schematics) into firmware-ready pin-mapping artifacts: MicroPython
modules, Arduino headers, JSON, Markdown docs, and Mermaid diagrams. It ships
with **13 MCU profiles** (RP2040, RP2350, ESP32, ESP32-S3, ESP32-C3, STM32G0,
STM32F411, STM32H743, nRF52840, ATmega328P, ATmega2560, ATSAMD21, ATSAMD51) and
supports adding new MCUs via declarative TOML files — no Python required.

---

## Table of contents

1. [Highlights](#highlights)
2. [Who is this for?](#who-is-this-for)
3. [Installation](#installation)
4. [Quick starts](#quick-starts)
5. [Generated outputs](#generated-outputs)
6. [Command-line workflow](#command-line-workflow)
7. [Fusion 360 ULP workflow](#fusion-360-ulp-workflow)
8. [MCU support](#mcu-support)
9. [Troubleshooting](#troubleshooting)
10. [Project roadmap](#project-roadmap)
11. [Contributing](#contributing)
12. [License](#license)

---

## Highlights

- **Fusion ULP integration** — ULP prompts for metadata, exports the netlist, and launches the CLI without leaving Fusion
- **MCU-aware validation** — Detects conflicting pin assignments, special-function usage, and likely differential pairs
- **Multiple entry points** — CLI for automation and CI; ULP for designers who prefer a graphical workflow
- **Automation friendly** — VS Code tasks, a polling watcher, and a pytest suite for regression coverage
- **Extensible profiles** — Add new MCUs with a short TOML file (`--profile-dir`) or by subclassing `MCUProfile` in Python
- **Schema-validated profiles** — TOML profiles are validated on load with actionable error messages for typos, missing fields, and type mismatches

---

## Who is this for?

| Role | What you get | Key docs |
|------|--------------|----------|
| PCB designer (Fusion) | Guided pinmap export from the Electronics workspace via ULP | [ULP guide](fusion_addin/ULP_GUIDE.md) |
| Firmware engineer | CLI for generating and validating pinmaps from CAD exports | [Usage guide](docs/usage.md) |
| Educator / Lab lead | Repeatable workflows, warnings, classroom-ready outputs | [Team workflows](docs/workflows.md) |

---

## Installation

### Clone the repository

```bash
git clone https://github.com/zcohen-nerd/PinmapGen.git
cd PinmapGen
```

### Python environment (developers)

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/macOS
pip install -e .
```

### Fusion 360 ULP (designers)

1. Copy the production ULP to Fusion's ULP directory:
```bash
copy fusion_addin/PinmapGen.ulp "%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\"
```

2. In the Electronics workspace: **Automation → Run ULP → PinmapGen**

`PinmapGen_Manual.ulp` is available when file dialogs are restricted or you
prefer to launch the CLI yourself.

---

## Quick starts

### Firmware engineer (CLI)

```bash
# Generate pinmaps from a CSV netlist (RP2040)
python -m tools.pinmapgen.cli \
  --csv hardware/exports/sample_netlist.csv \
  --mcu rp2040 \
  --mcu-ref U1 \
  --out-root build/pinmaps

# Watch a directory for new exports
python -m tools.pinmapgen.watch hardware/exports --mermaid
```

### PCB designer (Fusion ULP)

1. Open your design in the **Electronics** workspace.
2. **Automation → Run ULP → PinmapGen**.
3. Configure project name, MCU reference, and output directory.
4. Click **Generate Pinmaps** — the ULP exports the netlist and runs the CLI.
5. Generated files open in Explorer for handoff to the firmware team.

See the [ULP guide](fusion_addin/ULP_GUIDE.md) for full instructions.

---

## Generated outputs

```
pinmaps/
└── pinmap.json                # Canonical machine-readable pinmap

firmware/
├── include/pinmap_arduino.h   # Arduino/PlatformIO header
├── micropython/pinmap_micropython.py
└── docs/
    ├── PINOUT.md              # Human-readable pinout
    └── pinout.mmd             # Mermaid diagram source
```

Each file includes generation metadata and role annotations. See
[`docs/output-formats.md`](docs/output-formats.md) for details.

---

## Command-line workflow

The CLI accepts either EAGLE `.sch` files or CSV exports from Fusion.

```bash
python -m tools.pinmapgen.cli [OPTIONS]

Required arguments:
  --sch PATH | --csv PATH     Input schematic or CSV export
  --mcu NAME                  MCU profile name (use --list-mcus to see all)
  --mcu-ref TEXT              Reference designator (e.g., U1)

Useful flags:
  --out-root PATH             Output directory (default: current dir)
  --mermaid                   Emit Mermaid diagram
  --verbose, -v               Print normalization summary
  --reproducible              Fixed timestamps for reproducible builds
  --profile-dir PATH          Additional directory with custom TOML profiles
  --list-mcus                 List all available MCU profiles and exit

Profile management:
  profiles list               List all registered profiles with metadata
  profiles check <name>       Validate and inspect a profile
```

More examples (STM32G0, ESP32, watch mode) are in
[`docs/usage.md`](docs/usage.md).

---

## Fusion 360 ULP workflow

The ULP integrates PinmapGen into the Electronics workspace without requiring
add-in installation. After copying the ULP file:

- Access via **Automation → Run ULP → PinmapGen**
- Confirm MCU reference designator, project name, and output directory
- Trigger the export; the ULP invokes the CLI and streams warnings back
- Open the generated folder for review or firmware handoff

See the [ULP guide](fusion_addin/ULP_GUIDE.md) for step-by-step walkthroughs
and troubleshooting.

---

## MCU support

PinmapGen ships with **13 built-in TOML profiles**:

| Family | Profiles | Highlights |
|--------|----------|------------|
| RP2 | `rp2040`, `rp2350` | GPIO normalization, USB diff pair detection, ADC hints |
| ESP | `esp32`, `esp32s3`, `esp32c3` | GPIO matrix, strapping pin warnings, ADC2 Wi-Fi guard |
| STM32 | `stm32g0`, `stm32f411`, `stm32h743` | Port-based naming, alternate functions, boot/SWD warnings |
| nRF | `nrf52840` | BLE/USB, NFC pin detection, port.pin naming |
| AVR | `atmega328p`, `atmega2560` | Arduino digital/analog aliases, port-based naming |
| SAM | `atsamd21`, `atsamd51` | ARM Cortex-M0+/M4F, port-based naming |

List them at any time:

```bash
python -m tools.pinmapgen.cli --list-mcus
# or with detailed metadata:
python -m tools.pinmapgen.cli profiles list
```

Validate a profile before first use:

```bash
python -m tools.pinmapgen.cli profiles check rp2040
```

### Adding new MCUs

Drop a TOML file into a directory and point PinmapGen at it — no Python needed:

```bash
python -m tools.pinmapgen.cli \
  --csv netlist.csv --mcu my_mcu --mcu-ref U1 \
  --profile-dir ./my_profiles
```

See [`docs/extending.md`](docs/extending.md) for the full TOML schema and
advanced Python profile classes.

---

## Troubleshooting

Common issues are documented in
[`docs/troubleshooting.md`](docs/troubleshooting.md). Quick pointers:

- **"MCU 'U1' not found"** — Confirm the reference designator in your CAD
- **"Input-only pin used as output"** — Choose another pin supported by the
  MCU profile
- **"Cannot write output"** — Pick a writable folder and close open handles
- **ULP not found** — Re-copy `PinmapGen.ulp` to the Fusion ULP directory and
  restart Fusion 360

---

## Project roadmap

A milestone-driven roadmap is maintained in [`MILESTONES.md`](MILESTONES.md).

---

## Contributing

Pull requests and issues are welcome. Start with
[`CONTRIBUTING.md`](CONTRIBUTING.md), then:

1. Create a feature branch: `git checkout -b feature/my-update`
2. Make changes and run the test suite: `pytest` (or `python -m pytest`)
3. Use conventional commits when possible
4. Submit a pull request with context and screenshots when relevant

Pre-commit hooks and GitHub Actions validate that generated pinmaps stay in
sync.

---

## License

PinmapGen is released under the **PinmapGen Community License** with
dual-licensing:

- **Free for non-commercial use** — Personal projects, education, open source
- **Commercial license required** — Business use, client work, commercial
  products

See [`LICENSE`](LICENSE) for complete terms.
