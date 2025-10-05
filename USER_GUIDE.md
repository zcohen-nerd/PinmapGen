# PinmapGen User Guide

A practical handbook for PCB designers, firmware engineers, and educators who rely on PinmapGen to turn Fusion Electronics (EAGLE) designs into production-ready firmware assets.

---

## Table of contents

1. [Overview](#1-overview)
2. [Who should read this guide](#2-who-should-read-this-guide)
3. [Before you begin](#3-before-you-begin)
4. [Key concepts](#4-key-concepts)
5. [Quick start workflows](#5-quick-start-workflows)
6. [Preparing design data](#6-preparing-design-data)
7. [Command-line workflow](#7-command-line-workflow)
8. [Fusion 360 add-in workflow](#8-fusion-360-add-in-workflow)
9. [Collaboration playbooks](#9-collaboration-playbooks)
10. [Validation and troubleshooting](#10-validation-and-troubleshooting)
11. [Automation and continuous integration](#11-automation-and-continuous-integration)
12. [Extending PinmapGen](#12-extending-pinmapgen)
13. [Reference](#13-reference)

---

## 1. Overview

PinmapGen bridges the gap between hardware schematics and firmware codebases. It parses Fusion Electronics (and other EAGLE-compatible) exports, normalizes pin assignments per MCU profile, validates the design, and emits synchronized artifacts for developers and educators.

Two entry points share the same engine:

- **Command-line interface (CLI):** Ideal for firmware engineers, CI pipelines, and power users.
- **Fusion 360 add-in:** Designed for PCB designers who prefer a graphical workflow directly inside Fusion’s Electronics workspace.

The generated assets cover machine-readable data (`pinmaps/pinmap.json`), firmware-ready modules (MicroPython, Arduino), human-facing documentation (Markdown, Mermaid), and integration hooks (tasks, pre-commit, CI).

---

## 2. Who should read this guide

| Role | Why it matters | Suggested sections |
|------|----------------|--------------------|
| PCB designer | Learn how to generate and hand off pinmaps without leaving Fusion | [5](#5-quick-start-workflows), [8](#8-fusion-360-add-in-workflow), [9](#9-collaboration-playbooks) |
| Firmware engineer | Automate generation, understand outputs, and integrate with toolchains | [5](#5-quick-start-workflows), [7](#7-command-line-workflow), [11](#11-automation-and-continuous-integration) |
| Instructor / Lab lead | Standardize classroom workflows, enforce validation, share templates | [6](#6-preparing-design-data), [9](#9-collaboration-playbooks), [10](#10-validation-and-troubleshooting) |
| Contributor | Extend MCU support or emitters, improve docs and tooling | [7](#7-command-line-workflow), [12](#12-extending-pinmapgen) |

---

## 3. Before you begin

### Repository structure

Clone the repository (or download the release bundle) so the following directories are available:

- `hardware/exports/` — Sample CSV and schematic exports
- `tools/pinmapgen/` — Core toolchain modules (parsers, emitters, profiles)
- `firmware/` — Generated outputs (MicroPython, Arduino, docs)
- `pinmaps/` — Canonical JSON outputs
- `fusion_addin/` — Fusion 360 add-in package and installer

### Runtime prerequisites

| Workflow | Requirements |
|----------|--------------|
| CLI | Python 3.11+, optional virtual environment, access to CAD exports (.csv or .sch) |
| Fusion add-in | Autodesk Fusion 360 (Electronics workspace), Python runtime embedded in Fusion, write access to output directory |

### Recommended setup steps

```bash
# (Optional) set up virtual environment in repo root
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\Activate.ps1      # Windows PowerShell

# Install PinmapGen in editable mode
pip install -e .
```

If you plan to use the Fusion add-in, copy the `PinmapGen.ulp` script into Fusion's ULP directory. On Windows the default path is `%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\`.

```bash
# Example PowerShell copy
Copy-Item fusion_addin/PinmapGen.ulp "$env:APPDATA\Autodesk\Autodesk Fusion 360\API\ULPs\"
```

---

## 4. Key concepts

### 4.1 Canonical pinmap dictionary

Every run produces a canonical dictionary (`pinmaps/pinmap.json`) containing:

- `mcu` — MCU profile identifier (`rp2040`, `stm32g0`, `esp32`)
- `pins` — Mapping of net names to normalized pin names
- `roles` — Role inference (e.g., `i2c.sda`, `uart.tx`, `pwm`) per net
- `differential_pairs` — List of positive/negative net pairs
- `metadata` — Counts, timestamps, special pins, validation warnings

All emitters derive their outputs from this canonical structure.

### 4.2 Roles and validation

`tools/pinmapgen/roles.py` infers semantic roles based on net naming patterns. MCU profiles (RP2040, STM32G0, ESP32) augment validation by flagging:

- Input-only pads wired as outputs
- USB differential pairs missing a partner
- Strapping pins or boot pins used unexpectedly
- ADC pins assigned to digital-only roles

Warnings appear in CLI output, Fusion dialogs, and metadata.

### 4.3 Generated artifacts

| File | Purpose |
|------|---------|
| `pinmaps/pinmap.json` | Machine-readable canonical data for tooling |
| `firmware/micropython/pinmap_micropython.py` | Importable constants and helpers for MicroPython |
| `firmware/include/pinmap_arduino.h` | C/C++ header for Arduino/PlatformIO projects |
| `firmware/docs/PINOUT.md` | Human-readable Markdown pinout with tables and examples |
| `firmware/docs/pinout.mmd` | Mermaid source for diagrams (when `--mermaid` is used) |

---

## 5. Quick start workflows

### 5.1 Firmware engineer (CLI)

```bash
# Generate pinmaps from a CSV export
python -m tools.pinmapgen.cli \
  --csv hardware/exports/sample_netlist.csv \
  --mcu rp2040 \
  --mcu-ref U1 \
  --out-root build/pinmaps \
  --mermaid

# Watch a directory and regenerate automatically
python -m tools.pinmapgen.watch hardware/exports --mermaid
```

Key takeaways:
- Use `--csv` for Fusion/EAGLE netlist exports or `--sch` for schematic files.
- `--out-root` can point to a firmware repo, classroom network share, or build directory.
- Add `--verbose` to print normalization summaries and differential pair detection.

### 5.2 PCB designer (Fusion add-in)

1. Copy `fusion_addin/PinmapGen.ulp` into Fusion's ULP folder (e.g., `%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\`).
2. Open your design in **Fusion 360 → Electronics** workspace.
3. Click **Add-Ins → PinmapGen** and choose your MCU/profile options.
4. Pick output formats (MicroPython, Arduino, docs, diagrams) and a folder.
5. Review any warnings, then share the resulting output folder with your programmer.

The full add-in walkthrough (screenshots, troubleshooting) lives in `fusion_addin/ULP_GUIDE.md`.

---

## 6. Preparing design data

### 6.1 Naming nets effectively

- Prefer descriptive names (`I2C0_SDA`, `LED_DATA`, `USB_DP`).
- Avoid autogenerated labels (`N$1`, `NetR1_1`).
- Keep bus members consistent (`UART0_TX`, `UART0_RX`).

### 6.2 Reference designators

- Confirm the MCU uses a predictable designator (e.g., `U1`).
- Update the schematic if Fusion defaults to `IC1` or `U?` before running PinmapGen.

### 6.3 Exporting source data

- **CSV netlist:** `Design Workspace → Output → Netlist (CSV)`.
- **EAGLE `.sch`:** Save the schematic and export from Fusion or legacy EAGLE.
- For multi-MCU projects, export once and run the CLI per MCU reference designator.

### 6.4 Design validation checklist

- [ ] Each required MCU pin is connected to the intended net.
- [ ] Differential pairs (USB, CAN) are fully wired.
- [ ] Power pins are explicitly connected (no floating VDD/VSS).
- [ ] Inputs and outputs align with MCU capabilities (e.g., no output on input-only pads).

---

## 7. Command-line workflow

### 7.1 Basic command anatomy

```bash
python -m tools.pinmapgen.cli \
  --csv <input.csv> | --sch <input.sch> \
  --mcu {rp2040,stm32g0,esp32} \
  --mcu-ref <reference-designator> \
  [--out-root <path>] \
  [--mermaid] \
  [--verbose]
```

### 7.2 Output management

- Organize results inside your firmware repository (`--out-root firmware/`).
- Commit generated outputs if your workflow expects firmware developers to track diffs.
- Use separate output folders per board revision or MCU (`build/rp2040_revB/`).

### 7.3 Watching for changes

```bash
python -m tools.pinmapgen.watch hardware/exports --mermaid --interval 1.0
```

- Automatically regenerates pinmaps when CSV files change.
- Ideal for classroom labs or active firmware development sessions.

### 7.4 Handling warnings and validation

- CLI prints warnings to stdout; rerun with `--verbose` to inspect details.
- Warnings are mirrored in `pinmaps/pinmap.json` under `metadata.validation_warnings`.
- Treat warnings as action items—share them during handoff or resolve in the schematic.

### 7.5 Troubleshooting CLI errors

| Message | What it means | Next steps |
|---------|----------------|------------|
| `MCU 'U1' not found` | Reference designator missing or mismatched case | Verify the schematic and rerun |
| `Pinmap files generated successfully` but empty docs | Inputs lacked nets for the specified MCU | Double-check MCU ref and export options |
| `Error: CSV file not found` | Path typo or export missing | Regenerate export and confirm path |

---

## 8. Fusion 360 add-in workflow

### 8.1 Installation recap

- Copy `fusion_addin/PinmapGen.ulp` into Fusion's ULP directory (e.g., `%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\`).
- Enable the add-in from **Tools → ADD-INS → Scripts and Add-Ins → PinmapGen**.

### 8.2 Generating outputs inside Fusion

1. Activate the Electronics workspace and open your schematic.
2. Launch PinmapGen from the toolbar or Add-Ins dialog.
3. Choose MCU profile and reference designator (defaults auto-fill when possible).
4. Select output formats and destination folder.
5. Review warnings/errors in the results dialog.

### 8.3 When to prefer the add-in

- Designers hand off pinmaps without opening VS Code or Python.
- Rapid iteration while wiring the schematic; results update in seconds.
- Classrooms where students are more familiar with Fusion than the command line.

Refer to `fusion_addin/ULP_GUIDE.md` for screenshots, configuration tips, and detailed troubleshooting steps.

---

## 9. Collaboration playbooks

### 9.1 Designer → firmware handoff

- Package the entire output folder (`pinmaps/` and `firmware/`).
- Include the latest schematic PDF and any relevant datasheets.
- Highlight warnings encountered during generation.
- Provide context (e.g., "BUTTON pads are pulled up; active low").

### 9.2 Small firmware team

- Check generated artifacts into the firmware repository.
- Run `python -m tools.pinmapgen.cli ...` as part of pull requests.
- Use the VS Code tasks (`Generate Pinmap`, `Watch Pinmap`) for consistency.

### 9.3 Classroom or lab environment

- Pre-create template projects with the watcher running in a terminal.
- Encourage students to annotate warnings in lab notebooks.
- Provide printed excerpts from `firmware/docs/PINOUT.md` for wiring checks.
- Save daily snapshots (`pinmaps_2025-09-27/`) for grading traceability.

---

## 10. Validation and troubleshooting

### 10.1 Common warnings

| Warning | Interpretation | Suggested action |
|---------|----------------|------------------|
| `Pin GP24 is a USB pin` | USB differential pair pad used for GPIO | Reserve for USB or justify override |
| `GPIO0 low at boot enters download mode` | ESP32 strapping pin hazard | Add pull-ups/pull-downs per datasheet |
| `Differential pair incomplete` | Missing partner net | Connect both `*_P` and `*_N` pins |
| `Input-only pin used as output` | Role mismatch for MCU capability | Reassign net or add level shifting |

### 10.2 Diagnosing empty or partial outputs

- Ensure the MCU reference designator matches the schematic exactly.
- Inspect `pinmaps/pinmap.json` to confirm nets are listed.
- If tables in `PINOUT.md` are empty, the source export likely omitted nets.

### 10.3 Getting more detail

- Run the CLI with `--verbose` to print normalization summaries.
- Review `metadata.validation_warnings` inside the JSON output.
- In Fusion, warnings appear in a scrollable dialog; copy/paste them into issue trackers when needed.

---

## 11. Automation and continuous integration

### 11.1 Local automation

Install the bundled pre-commit hook to regenerate pinmaps automatically when hardware exports change:

```bash
# macOS / Linux
bash .githooks/install-hooks.sh

# Windows PowerShell
pwsh .githooks/install-hooks.ps1
```

### 11.2 VS Code tasks

- **Generate Pinmap:** Runs the CLI against `hardware/exports/sample_netlist.csv`.
- **Watch Pinmap:** Monitors exports and regenerates on change.
- **Test PinmapGen CLI:** Executes the CLI help command to verify availability.

Launch tasks via `Ctrl+Shift+P → Tasks: Run Task`.

### 11.3 GitHub Actions

The `validate-pinmaps.yml` workflow regenerates outputs on every push and pull request, failing the build if committed artifacts drift from source data. It also verifies importability of each module and checks JSON structure.

---

## 12. Extending PinmapGen

### 12.1 Adding a new MCU profile

1. Subclass `tools.pinmapgen.mcu_profiles.MCUProfile`.
2. Implement normalization, role validation, and metadata augmentation.
3. Register the profile in `tools.pinmapgen.cli.MCU_PROFILES`.
4. Provide sample exports and add unit tests under `tests/`.

### 12.2 Customizing emitters

- Modify or add emitters in `tools/pinmapgen/emit_*.py`.
- Emitters consume the canonical dictionary, so keep field names consistent.
- Update documentation (`docs/output-formats.md`, once available) to describe new outputs.

### 12.3 Packaging for teams

- Bundle CLI usage into shell scripts or Make targets.
- Share instructions for copying `fusion_addin/PinmapGen.ulp` into the Fusion ULP directory.
- Publish internal how-to guides referencing this user guide and the README.

---

## 13. Reference

- **README.md** — High-level project overview, installation, and highlights.
- **MILESTONES.md** — Roadmap with current priorities (Classroom readiness & documentation sprint).
- **fusion_addin/ULP_GUIDE.md** — Detailed Fusion workflow with screenshots.
- **tests/** — Sample fixtures and unit tests illustrating the canonical data flow.
- **hardware/exports/sample_netlist.csv** — Reference dataset for experimentation.

If you encounter gaps or have suggestions, open an issue or pull request and reference the relevant section of this guide. Happy mapping!
