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
8. [Fusion 360 ULP workflow](#8-fusion-360-ulp-workflow)
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
- **Fusion 360 ULP:** Designed for PCB designers who prefer a graphical workflow directly inside Fusion’s Electronics workspace.

The generated assets cover machine-readable data (`pinmaps/pinmap.json`), firmware-ready modules (MicroPython, Arduino), human-facing documentation (Markdown, Mermaid), and integration hooks (tasks, pre-commit, CI).

---

## 2. Who should read this guide

| Role | Why it matters | Suggested sections |
|------|----------------|--------------------|
| PCB designer | Learn how to generate and hand off pinmaps without leaving Fusion | [5](#5-quick-start-workflows), [8](#8-fusion-360-ulp-workflow), [9](#9-collaboration-playbooks) |
| Firmware engineer | Automate generation, understand outputs, and integrate with toolchains | [5](#5-quick-start-workflows), [7](#7-command-line-workflow), [11](#11-automation-and-continuous-integration) |
| Instructor / Lab lead | Standardize classroom workflows, enforce validation, share templates | [6](#6-preparing-design-data), [9](#9-collaboration-playbooks), [10](#10-validation-and-troubleshooting) |
| Contributor | Extend MCU support or emitters, improve docs and tooling | [7](#7-command-line-workflow), [12](#12-extending-pinmapgen) |

---

## 3. Before you begin

### Repository structure

Clone the repository (or download the release bundle) so the following directories are available:

- `hardware/exports/` — Sample CSV and schematic exports
- `tools/pinmapgen/` — Core toolchain modules (parsers, emitters)
- `tools/pinmapgen/profiles/` — The 13 built-in MCU profiles (TOML files)
- `fusion_addin/` — Fusion 360 ULP scripts and guide
- `examples/` — Three worked examples with committed outputs

Generated outputs (`pinmaps/`, `firmware/`) are created wherever
`--out-root` points; when run from the repo root they land in the root and
are deliberately gitignored.

### Runtime prerequisites

| Workflow | Requirements |
|----------|--------------|
| CLI | Python 3.11+, optional virtual environment, access to CAD exports (.csv or .sch) |
| Fusion ULP | Autodesk Fusion 360 (Electronics workspace) on Windows, Python 3.11+ installed on the same machine and on PATH, a local clone/download of this repository, write access to the output directory |

### Recommended setup steps

```bash
# (Optional) set up virtual environment in repo root
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
# .venv\Scripts\Activate.ps1      # Windows PowerShell

# Optional: editable install. Adds the `pinmapgen` command and lets the
# CLI run from any directory. PinmapGen is stdlib-only, so you can also
# skip this and run `python -m tools.pinmapgen.cli` from the repo root.
pip install -e .
```

If you plan to use the Fusion ULP, copy the `PinmapGen.ulp` script into Fusion's ULP directory. On Windows the default path is `%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\`.

```bash
# Example PowerShell copy
Copy-Item fusion_addin/PinmapGen.ulp "$env:APPDATA\Autodesk\Autodesk Fusion 360\API\ULPs\"
```

---

## 4. Key concepts

### 4.1 Canonical pinmap dictionary

Every run produces a canonical dictionary (`pinmaps/pinmap.json`) containing:

- `mcu` — MCU profile identifier (one of the 13 built-in profiles, or a custom one)
- `mcu_ref` — The reference designator the pinmap was generated for (e.g., `U1`)
- `pins` — Mapping of net names to normalized pin names
- `pin_roles` — Role inference per net (e.g., `i2c.sda`, `uart.tx`, `pwm`) with bus group and description
- `bus_groups` — Nets grouped by bus/peripheral (I2C0, SPI, UART, …)
- `differential_pairs` — List of positive/negative net pairs
- `metadata` — Counts, special pins, validation warnings/errors, dropped pins, and the profile's special-function tables
- `generated` — Timestamp and generator version

All emitters derive their outputs from this canonical structure.

### 4.2 Roles and validation

`tools/pinmapgen/roles.py` infers semantic roles based on net naming patterns. Validation distinguishes **errors** (broken pinmaps — these fail `--strict`) from **warnings** (advisories that never block generation).

Errors:

- Pin conflicts — the same MCU pin claimed by two different nets

Warnings:

- Special pins used at all — boot strapping pins, flash-voltage pins, the
  default console UART, pads not bonded on your module (from the MCU
  profile's per-pin warnings)
- Input-only pads (e.g., ESP32 GPIO34–39) carrying a net whose role
  implies an output
- Lonely differential-pair halves — a `_DP`/`_P`/`CAN_H`/`USB_D+`-style
  net with no matching partner (active-low `_N` suffixes like `RESET_N`
  are not flagged)
- Nets spanning multiple pins that don't look like power/ground rails
- Power/ground rails assigned to GPIO pins
- Bare-number pins interpreted as logical GPIO numbers
- Net names that had to be renamed to become valid identifiers

Warnings appear in CLI output, Fusion dialogs, and the JSON `metadata`.

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

### 5.2 PCB designer (Fusion ULP)

1. Copy `fusion_addin/PinmapGen.ulp` into Fusion's ULP folder (e.g., `%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\`).
2. Open your design in **Fusion 360 → Electronics** workspace.
3. Run **Automation → Run ULP → PinmapGen**.
4. On first run, enter the path to your PinmapGen folder in the
   **PinmapGen repository** field (it's remembered afterwards).
5. Pick your MCU with the quick buttons, confirm the reference designator
   (`U1` by default — the **Analyze** button checks it against the open
   schematic), choose output formats and a folder.
6. Click **Generate Pinmap**, review any warnings, then share the resulting
   output folder with your programmer.

The full walkthrough lives in `fusion_addin/ULP_GUIDE.md`.

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

- **CSV netlist:** run `fusion_addin/export_netlist.ulp` from Fusion's
  **Automation → Run ULP** — a pure export that works on Windows and
  macOS and writes exactly the format the CLI expects. (Fusion's built-in
  File → Export → Netlist does *not* produce this format.) Hand-written
  CSVs also work: `Net`, `Pin`, `RefDes` required, `Component` optional,
  headers case-insensitive with common aliases.
- **EAGLE `.sch`:** legacy EAGLE XML schematics can be passed directly
  with `--sch`.
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
  --mcu <profile-name> \
  --mcu-ref <reference-designator> \
  [--out-root <path>] \
  [--mermaid] \
  [--no-micropython] [--no-arduino] [--no-markdown] \
  [--verbose] \
  [--strict] \
  [--profile-dir <dir>] \
  [--reproducible] \
  [--log-file <path>]
```

- `--mcu` accepts any of the 13 built-in profiles — run `--list-mcus` to
  see them all with descriptions, or `profiles check <name>` to validate
  and inspect one.
- `--strict` makes the CLI exit with code 2 (writing no output) when the
  pinmap has validation errors or pins that failed to normalize —
  recommended for CI.
- `--no-micropython`, `--no-arduino`, `--no-markdown` skip individual
  output formats (the canonical `pinmap.json` is always written); Mermaid
  is opt-in via `--mermaid`.
- `--profile-dir` adds a directory of custom TOML profiles.
- `--reproducible` pins timestamps (via `SOURCE_DATE_EPOCH`) so repeated
  runs produce byte-identical output — useful for committed artifacts and
  drift checks.
- `--log-file` mirrors everything the run prints (status, warnings,
  validation errors) into a file. The Fusion ULP passes this automatically
  and displays the log when a run needs review.

### 7.2 Output management

- Organize results inside your firmware repository (`--out-root firmware/`).
- Commit generated outputs if your workflow expects firmware developers to track diffs.
- Use separate output folders per board revision or MCU (`build/rp2040_revB/`).

### 7.3 Watching for changes

```bash
python -m tools.pinmapgen.watch hardware/exports --mermaid --interval 1.0
```

- Automatically regenerates pinmaps when CSV files change.
- Accepts the same `--mcu` names as the CLI (all 13 profiles) and
  `--profile-dir` for custom ones; one watcher run uses a single MCU
  profile for every file it sees.
- Ideal for classroom labs or active firmware development sessions.

### 7.4 Handling warnings and validation

- Warnings and validation errors print to stderr; rerun with `--verbose`
  for normalization summaries and differential-pair details.
- Everything is mirrored in `pinmaps/pinmap.json` under
  `metadata.validation_warnings`, `metadata.validation_errors`, and
  `metadata.dropped_pins` (pins that could not be normalized).
- Rows in the CSV with missing required fields are skipped with a warning
  naming the line — they do not abort the run.
- By default the CLI still exits 0 when there are validation errors so you
  can inspect the output; add `--strict` to turn errors and dropped pins
  into a hard failure (exit code 2, no files written).
- Treat warnings as action items—share them during handoff or resolve in the schematic.

### 7.5 Troubleshooting CLI errors

| Message | What it means | Next steps |
|---------|----------------|------------|
| `No entries found for MCU reference 'U1'` | Reference designator missing from the export | Verify the schematic designator and rerun |
| `Warning: Dropped pin '...'` | A pin name the MCU profile doesn't recognize | Check the pin naming; see `metadata.dropped_pins` |
| `Strict mode: N validation error(s) ... no output written` | `--strict` blocked a broken pinmap | Fix the conflicts listed above the message, or rerun without `--strict` to inspect |
| `Error: CSV file not found` | Path typo or export missing | Regenerate export and confirm path |
| `Unknown MCU profile '...'` | Typo in `--mcu` | Run `--list-mcus` for the valid names |

---

## 8. Fusion 360 ULP workflow

### 8.1 Installation recap

- Copy `fusion_addin/PinmapGen.ulp` into Fusion's ULP directory (e.g., `%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\`).
- Restart Fusion; the ULP appears under **Automation → Run ULP**.
- Python 3.11+ must be installed on the machine (the ULP invokes the CLI).

### 8.2 Generating outputs inside Fusion

1. Activate the Electronics workspace and open your schematic.
2. Run **Automation → Run ULP → PinmapGen**.
3. First run only: fill in the **PinmapGen repository** field with the path
   to your cloned/downloaded PinmapGen folder. The ULP validates the path
   and saves it (with all other settings) to a file next to the ULP.
4. Choose the MCU with the quick buttons — all 13 built-in profiles are
   available — and confirm the reference designator. The **Analyze** button
   reports whether that designator exists in the open schematic and how
   many pins it has.
5. Select output formats and a destination folder, then **Generate Pinmap**.
   The ULP exports the netlist from the schematic automatically, runs the
   CLI, and opens the output folder in Explorer.
6. Review warnings/errors in the results dialog.

`PinmapGen_Manual.ulp` is a fallback for environments where the automatic
netlist export doesn't work: export the netlist CSV yourself, name it
`live_netlist.csv`, place it in the output folder, and run the manual ULP.

### 8.3 When to prefer the ULP

- Designers hand off pinmaps without opening VS Code or Python.
- Rapid iteration while wiring the schematic; results update in seconds.
- Classrooms where students are more familiar with Fusion than the command line.

Refer to `fusion_addin/ULP_GUIDE.md` for configuration tips and detailed troubleshooting steps.

---

## 9. Collaboration playbooks

### 9.1 Designer → firmware handoff

- Package the entire output folder (`pinmaps/` and `firmware/`).
- Include the latest schematic PDF and any relevant datasheets.
- Highlight warnings encountered during generation.
- Provide context (e.g., "BUTTON pads are pulled up; active low").

### 9.2 Small firmware team

- Check generated artifacts into the firmware repository. Generate with
  `--reproducible` so re-runs are byte-identical and diffs stay clean.
- Run `python -m tools.pinmapgen.cli ... --strict` as part of pull
  requests so pin conflicts fail the build instead of hiding in warnings.
- Use the VS Code tasks (`Generate Pinmap`, `Watch Pinmap`) for consistency.

### 9.3 Classroom or lab environment

- Pre-create template projects with the watcher running in a terminal.
- Encourage students to annotate warnings in lab notebooks.
- Provide printed excerpts from `firmware/docs/PINOUT.md` for wiring checks.
- Save daily snapshots (`pinmaps_2025-09-27/`) for grading traceability.

---

## 10. Validation and troubleshooting

### 10.1 Understanding the messages

The rule of thumb: **errors** (pin conflicts, dropped pins) mean the
pinmap is broken and fail `--strict`; **warnings** (special pins,
multi-pin nets, lonely pair halves, bare-number interpretation,
renamed identifiers) are advisories worth a look that never block
generation — the full list of checks is in
[section 4.2](#42-roles-and-validation).

Every message the tool prints is catalogued verbatim — with what it
means and what to do — in
[docs/troubleshooting.md § Validation messages](docs/troubleshooting.md#validation-messages),
so you can search that page for the exact text you saw.

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

Install the bundled pre-commit hook to validate netlists before they are
committed — when a commit stages CSV files under `hardware/exports/`, the
hook runs the generator against each one in a temporary directory and
blocks the commit if generation fails:

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

Two workflows run on every push and pull request:

- **`build-test.yml`** — runs the full test suite and generation
  end-to-end (with `--strict`) on Linux/Windows/macOS across Python
  3.11–3.14, plus module-import, file-watcher, and packaging
  (`pip install -e .` / wheel) checks.
- **`validate-pinmaps.yml`** — regenerates from the sample netlist with
  `--strict`, verifies output structure and content, and regenerates the
  committed `examples/` outputs with `--reproducible`, failing the build
  if they drift from the current emitters.

---

## 12. Extending PinmapGen

### 12.1 Adding a new MCU profile

1. Write a TOML profile (schema in `tools/pinmapgen/profiles/README.md`)
   and pass its directory with `--profile-dir`, or drop it into
   `tools/pinmapgen/profiles/` to make it built-in.
2. Validate with `python -m tools.pinmapgen.cli profiles check <mcu>`.
3. For behavior TOML can't express, subclass
   `tools.pinmapgen.mcu_profiles.MCUProfile` and register it via
   `profile_registry.registry.register(name, cls)`.
4. Provide sample exports and add unit tests under `tests/`.

### 12.2 Customizing emitters

- Modify or add emitters in `tools/pinmapgen/emit_*.py`.
- Emitters consume the canonical dictionary, so keep field names consistent.
- Update [`docs/output-formats.md`](docs/output-formats.md) to describe new outputs.

### 12.3 Packaging for teams

- Bundle CLI usage into shell scripts or Make targets.
- Share instructions for copying `fusion_addin/PinmapGen.ulp` into the Fusion ULP directory.
- Publish internal how-to guides referencing this user guide and the README.

---

## 13. Reference

- **README.md** — High-level project overview, installation, and highlights.
- **docs/** — Topic guides (usage, workflows, troubleshooting, FAQ, output formats, extending) — see [docs/README.md](docs/README.md) for the index.
- **fusion_addin/ULP_GUIDE.md** — Detailed Fusion workflow.
- **tests/** — Unit and regression tests illustrating the canonical data flow (inputs are built inline, no fixture files).
- **hardware/exports/sample_netlist.csv** — Reference dataset for experimentation.

If you encounter gaps or have suggestions, open an issue or pull request and reference the relevant section of this guide.
