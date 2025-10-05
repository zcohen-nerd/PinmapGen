# 🏆 PinmapGen - Fusion Electronics Pinmap Toolchain

[![License: Custom](https://img.shields.io/badge/License-PinmapGen%20Community-blue.svg)](LICENSE)
[![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready-green.svg)](README.md)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![CI/CD](https://img.shields.io/github/actions/workflow/status/zcohen-nerd/PinmapGen/ci.yml?branch=main&label=CI%2FCD)](https://github.com/zcohen-nerd/PinmapGen/actions)
[![Issues](https://img.shields.io/github/issues/zcohen-nerd/PinmapGen)](https://github.com/zcohen-nerd/PinmapGen/issues)
[![Documentation](https://img.shields.io/badge/docs-comprehensive-brightgreen.svg)](docs/)

## 🎉 Project status

PinmapGen is an actively developed toolchain that transforms Fusion 360 Electronics or EAGLE designs into firmware-ready pinmaps. The CLI and emitters are stable for CSV exports, while schematic parsing, Fusion automation, and expanded MCU support continue to evolve.

### 🚀 What works today
- ✅ **Fusion ULP helpers** – `PinmapGen.ulp` guides designers through exporting netlists without leaving the workspace
- ✅ **CSV & schematic ingestion** – CLI accepts Fusion CSV exports and EAGLE `.sch` files
- ✅ **Multiple output formats** – MicroPython, Arduino, JSON, Markdown, and optional Mermaid artifacts
- ✅ **MCU profile library** – RP2040, STM32G0, and ESP32 normalization with validation warnings
- ✅ **Comprehensive docs** – User guide, troubleshooting, and workflows maintained under `docs/`

---

## About PinmapGen

PinmapGen is a Python 3.11 toolchain that converts Fusion 360 Electronics exports into consistent firmware assets. Designers run a ULP to package project metadata and netlists; firmware engineers use the CLI to normalize pins, validate assignments, and generate libraries for their target platform.

---

## Table of contents

1. [Highlights](#highlights)
2. [Who is this for?](#who-is-this-for)
3. [Installation](#installation)
4. [Quick starts](#quick-starts)
5. [Generated outputs](#generated-outputs)
6. [Command-line workflow](#command-line-workflow)
7. [Fusion 360 add-in workflow](#fusion-360-add-in-workflow)
8. [MCU support](#mcu-support)
9. [Troubleshooting](#troubleshooting)
10. [Project roadmap](#project-roadmap)
11. [Contributing](#contributing)
12. [License](#license)

---

## 🚀 Highlights

- ✅ **Streamlined exports** – Fusion ULP prompts for metadata, runs the netlist export, and launches the CLI
- ✅ **MCU-aware validation** – Detects conflicting pin assignments, special-function usage, and likely differential pairs
- ✅ **Multiple entry points** – Command-line automation plus Fusion workspace integration via ULP
- ✅ **Automation friendly** – VS Code tasks, a polling watcher, and pytest suite for regression coverage
- **Extensible profiles** – Add new MCUs by subclassing `MCUProfile` and registering with the CLI

---

## Who is this for?

| Role | What you get | Key docs |
|------|--------------|----------|
| PCB designer (Fusion) | Guided pinmap export directly from the Electronics workspace via ULP | [Fusion ULP user guide](fusion_addin/ULP_GUIDE.md) |
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

2. In Fusion Electronics workspace: **Automation → Run ULP → PinmapGen**

`PinmapGen_Manual.ulp` is available when file dialogs are restricted or you prefer to launch the CLI manually.

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

1. Open your design in the **Electronics** workspace
2. Click **Automation → Run ULP → Working**
3. Configure project name, MCU reference, and output directory
4. Click **Generate Pinmaps** to export netlist and create all output formats
5. Files open automatically in Explorer for easy handoff to firmware team

The ULP orchestrates the same CLI workflow without requiring command-line knowledge. See the [Fusion ULP user guide](fusion_addin/ULP_GUIDE.md) for detailed instructions and screenshots.

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
  --mcu {rp2040,stm32g0,esp32}
  --mcu-ref TEXT              Reference designator (e.g., U1)

Useful flags:
  --out-root PATH             Output directory (default: current dir)
  --mermaid                   Emit Mermaid diagram
  --verbose, -v               Print normalization summary
```

Additional examples, including STM32G0 and ESP32 workflows, are documented in 
[`docs/usage.md`](docs/usage.md).

---

## Fusion 360 ULP workflow

The ULP (User Language Program) integrates PinmapGen directly into the Electronics workspace without requiring add-in installation. After copying the ULP file:

- Access via **Automation → Run ULP → PinmapGen** in the Electronics workspace
- Confirm project metadata, MCU reference designator, and output directory  
- Trigger the export; the ULP invokes the CLI and streams warnings back into Fusion
- Open the generated folder for quick review or firmware handoff

Refer to the [Fusion ULP user guide](fusion_addin/ULP_GUIDE.md) for step-by-step walkthroughs, troubleshooting, and handoff best practices.

---

## MCU support

| MCU | Highlights | Notes |
|-----|------------|-------|
| RP2040 | GPIO normalization, USB diff pair detection, ADC role hints | Reference implementation used in automated tests |
| STM32G0 | Port-based pin naming, alternate function validation, boot pin warnings | Modelled on STM32G071 reference design |
| ESP32 | GPIO matrix awareness, strapping pin warnings, ADC2 Wi-Fi guard rails | Based on ESP32-WROOM-32 module |

Adding new MCUs only requires implementing an `MCUProfile` subclass and 
registering it in the CLI. See [`docs/extending.md`](docs/extending.md) for a 
walkthrough.

---

## Troubleshooting

Common issues and solutions are documented in [`docs/troubleshooting.md`](docs/troubleshooting.md). Highlights:

- **"MCU 'U1' not found"** → Confirm the reference designator in your CAD
- **"Input-only pin used as output"** → Adjust assignment or choose another 
  pin supported by the MCU profile
- **"Cannot write output"** → Pick a writable folder and close open files
- **ULP not found** → Re-copy `PinmapGen.ulp` to `%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\` 
  and restart Fusion 360

---

## Project roadmap

A milestone-driven roadmap is maintained in [`MILESTONES.md`](MILESTONES.md). 
Current focus: **Milestone 6 – Classroom / Team Readiness**.

---

## Contributing

We welcome pull requests and issues. Start with the 
[`CONTRIBUTING.md`](CONTRIBUTING.md) guide, then:

1. Create a feature branch: `git checkout -b feature/my-update`
2. Make changes and run the test suite: `pytest` (or `python -m pytest`)
3. Commit with conventional commits if possible
4. Submit a pull request with context and screenshots when relevant

Pre-commit hooks and GitHub Actions will validate that generated pinmaps are 
up to date.

---

## License

PinmapGen is released under the **PinmapGen Community License** with dual-licensing:

- **Free for Non-Commercial Use** - Personal projects, education, open source
- **Commercial License Required** - Business use, client work, commercial products

See [`LICENSE`](LICENSE) for complete terms and commercial licensing information.