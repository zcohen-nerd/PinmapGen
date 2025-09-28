# 🏆 PinmapGen - Complete Automated Solution

## 🎉 SUCCESS: Working Solution Deployed!

**Mission Accomplished!** PinmapGen is now a **fully functional, production-ready** toolchain that automatically transforms Fusion 360 Electronics schematics into firmware-ready pinmaps with **complete one-click automation**.

### 🚀 What Works Now
- ✅ **ULP Integration** - Runs directly in Fusion 360 Electronics workspace
- ✅ **Automatic Netlist Generation** - No manual CSV exports needed
- ✅ **All Output Formats** - MicroPython, Arduino, JSON, Markdown, Mermaid  
- ✅ **Production Tested** - Validated with real schematics and confirmed working
- ✅ **Complete Documentation** - Full user guides and troubleshooting

---

## About PinmapGen

PinmapGen is a production-ready Python 3.11 toolchain that automatically transforms Fusion 360 Electronics schematics into firmware-ready pinmaps with **breakthrough one-click automation**. No manual exports required!

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

## 🚀 Highlights - Production Ready!

- ✅ **COMPLETE AUTOMATION** - One-click generation from Fusion 360 Electronics schematics
- ✅ **NO MANUAL EXPORT** - ULP automatically extracts netlist data from live schematics
- ✅ **WORKING SOLUTION** - Tested and validated with real schematics generating all output formats
- **Multi-MCU aware** profiles for RP2040, STM32G0 and ESP32, with a registry designed for rapid expansion
- **Multiple output formats** (JSON, MicroPython, Arduino, Markdown and 
  Mermaid) generated in a single run.
- **Rich validation** that flags duplicate nets, lonely differential pairs and 
  MCU-specific hazards (strapping pins, input-only pads, etc.).
- **Two entry points**:
  - A CLI that integrates into existing firmware toolchains
  - A Fusion 360 ULP with a point-and-click UI that works directly in Electronics workspace
- **Automation friendly** thanks to VS Code tasks, a file watcher, pre-commit 
  hooks and GitHub Actions workflows.

---

## Who is this for?

| Role | What you get | Key docs |
|------|--------------|----------|
| PCB designer (Fusion) | One-click pinmap export directly from Electronics workspace via ULP | [Fusion ULP user guide](fusion_addin/ULP_GUIDE.md) |
| Firmware engineer | CLI for generating and validating pinmaps from CAD exports | [Command-line reference](docs/cli.md) |
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

1. Copy the ULP file to Fusion's ULP directory:
```bash
copy fusion_addin/Working.ulp "%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\"
```

2. In Fusion Electronics workspace: **Automation → Run ULP → Working**

> ULPs (User Language Programs) work directly in the Electronics workspace 
> without requiring add-in installation or permissions.

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

The ULP produces the same outputs as the CLI without requiring command-line 
knowledge and works directly in Electronics workspace. See the [Fusion ULP user guide](fusion_addin/ULP_GUIDE.md) for 
detailed instructions.

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
[`docs/cli.md`](docs/cli.md).

---

## Fusion 360 ULP workflow

The ULP (User Language Program) integrates PinmapGen directly into the Electronics 
workspace without requiring add-in installation. After copying the ULP file:

- Access via **Automation → Run ULP → Working** in Electronics workspace
- Configure project name, MCU reference designator, and output directory  
- Choose from quick location buttons (Desktop, Documents, Project Root)
- Output includes organized folder structure with all formats
- File Explorer opens automatically to show generated files

Refer to the [Fusion ULP user guide](fusion_addin/ULP_GUIDE.md) for 
step-by-step walkthroughs, troubleshooting and handoff best practices.

---

## MCU support

| MCU | Highlights | Notes |
|-----|------------|-------|
| RP2040 | GPIO normalization, USB diff pair detection, ADC role hints | Original reference implementation |
| STM32G0 | Port-based pin naming, alternate function validation, boot pin warnings | Modelled on STM32G071 reference design |
| ESP32 | GPIO matrix awareness, strapping pin warnings, ADC2 Wi-Fi guard rails | Based on ESP32-WROOM-32 module |

Adding new MCUs only requires implementing an `MCUProfile` subclass and 
registering it in the CLI. See [`docs/extending.md`](docs/extending.md) for a 
walkthrough.

---

## Troubleshooting

Common issues and solutions are documented in [`docs/troubleshooting.md`]
(docs/troubleshooting.md). Highlights:

- **"MCU 'U1' not found"** → Confirm the reference designator in your CAD
- **"Input-only pin used as output"** → Adjust assignment or choose another 
  pin supported by the MCU profile
- **"Cannot write output"** → Pick a writable folder and close open files
- **ULP not found** → Re-copy `Working.ulp` to `%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\` 
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

PinmapGen is released under the MIT License. See [`LICENSE`](LICENSE) for the 
full text.