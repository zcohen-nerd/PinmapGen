# Usage Guide

Detailed CLI usage, ULP workflow, and integration patterns.

---

## CLI basics

### Minimal invocation

```bash
python -m tools.pinmapgen.cli \
  --csv hardware/exports/sample_netlist.csv \
  --mcu rp2040 \
  --mcu-ref U1 \
  --out-root .
```

### Full option reference

```bash
python -m tools.pinmapgen.cli [OPTIONS]

Required:
  --sch PATH | --csv PATH     Input schematic or CSV file
  --mcu NAME                  MCU profile (13 built-in — use --list-mcus)
  --mcu-ref TEXT              Reference designator (e.g., U1)

Optional:
  --out-root PATH             Output directory (default: current dir)
  --mermaid                   Also generate Mermaid diagram
  --verbose, -v               Print normalization summary
  --strict                    Exit non-zero on validation errors or
                              dropped pins (recommended for CI)
  --profile-dir PATH          Additional directory with custom TOML profiles
  --reproducible              Fixed timestamps for reproducible builds
  --log-file PATH             Mirror all console output (status, warnings,
                              errors) to a file — used by the Fusion ULP
```

### Examples by MCU

```bash
# RP2040
python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root . --mermaid -v

# STM32G0
python -m tools.pinmapgen.cli --csv hardware/exports/stm32g0_netlist.csv --mcu stm32g0 --mcu-ref U1 --out-root .

# ESP32
python -m tools.pinmapgen.cli --csv hardware/exports/esp32_netlist.csv --mcu esp32 --mcu-ref U1 --out-root . --mermaid
```

The CSV needs the columns `Net`, `Pin`, `Component`, `RefDes` (extra
columns are ignored). The `Pin` column must hold the chip's **logical pin
name** (`GP15`, `GPIO4`, `PA0`), not the physical package pad number — a
bare number like `2` is interpreted as GPIO 2, and the CLI warns when it
makes that assumption.

### EAGLE schematic input

```bash
python -m tools.pinmapgen.cli --sch hardware/exports/sample_schematic.sch --mcu rp2040 --mcu-ref U1 --out-root .
```

---

## File watcher

The watcher polls a directory for CSV changes and regenerates outputs
automatically.

```bash
python -m tools.pinmapgen.watch hardware/exports/ --interval 1.0 --mermaid
```

The watcher accepts the same `--mcu` names as the CLI (all 13 built-in
profiles) plus `--profile-dir` for custom TOML profiles. A single watcher
run uses one MCU profile for every file it watches — if a directory mixes
netlists for different MCUs, point the watcher at a single file instead:

```bash
python -m tools.pinmapgen.watch hardware/exports/sample_netlist.csv --mcu rp2040
```

Useful during active schematic iteration or in classroom labs where students
save CSV files to a shared folder.

---

## ULP workflow

### Installation

Copy `PinmapGen.ulp` to Fusion's ULP directory:

```powershell
Copy-Item fusion_addin/PinmapGen.ulp "$env:APPDATA\Autodesk\Autodesk Fusion 360\API\ULPs\"
```

### Running

1. Open your schematic in the **Electronics** workspace.
2. **Automation → Run ULP → PinmapGen**.
3. Set project name, MCU type, MCU reference, and output directory.
4. Click **Generate Pinmaps**.

The ULP reads the schematic object model directly — no manual CSV export is
needed. It writes a temporary CSV, invokes the CLI, and opens the output
folder.

Every run also writes `pinmapgen_log.txt` into the output folder with the
CLI's full output. If the run produced warnings, validation errors, or
dropped pins, the ULP shows that log in a dialog instead of a plain success
message — review it before trusting the generated files.

### Preview mode

Click **Preview** before generating to see a summary of detected components,
nets, and which files will be created.

### Settings persistence

The ULP remembers your last-used MCU type, output directory, and format
selections between runs.

See [ULP_GUIDE.md](../fusion_addin/ULP_GUIDE.md) for screenshots and
troubleshooting.

---

## VS Code tasks

Three tasks are configured in `.vscode/tasks.json`:

| Task | What it does |
|------|-------------|
| Generate Pinmap | Runs CLI on `hardware/exports/sample_netlist.csv` with RP2040 |
| Watch Pinmap | Starts the file watcher on `hardware/exports/` |
| Test PinmapGen CLI | Runs `--help` to verify the CLI is available |

Launch via **Ctrl+Shift+P → Tasks: Run Task**.

---

## Team workflows

### Designer → firmware handoff

1. Designer exports or generates pinmaps (ULP or CLI).
2. Package `pinmaps/` and `firmware/` into the repo or a ZIP.
3. Include any validation warnings from the CLI output.
4. Firmware engineer imports the generated constants into their project.

### Multi-board product family

Maintain one CSV per board variant and generate into separate output
directories:

```bash
python -m tools.pinmapgen.cli --csv boards/rev_a/netlist.csv --mcu rp2040 --mcu-ref U1 --out-root build/rev_a
python -m tools.pinmapgen.cli --csv boards/rev_b/netlist.csv --mcu rp2040 --mcu-ref U1 --out-root build/rev_b
```

Firmware can use `#ifdef` or build-system variables to select the right header.

### Code review checklist for pin changes

**Hardware reviewer:**
- Semantic net names used (not bare `GP0`, `GPIO1`)
- Differential pairs correctly wired
- Power/ground nets excluded from GPIO
- Pin capabilities match signal requirements

**Firmware reviewer:**
- Generated constants compile without errors
- Pin changes don't break existing drivers
- Tested on hardware

---

## Classroom usage

### Lab setup

1. Prepare template CSVs for each exercise.
2. Start the watcher in a terminal so students get instant feedback.
3. Provide printed excerpts from `firmware/docs/PINOUT.md` for wiring checks.

### Assessment ideas

- Semantic naming (descriptive vs generic)
- Pin capability matching (ADC for sensors, PWM for LEDs)
- Proper differential pair usage
- Documentation completeness

---

## CI/CD integration

### GitHub Actions

```yaml
name: Validate Pinmaps
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    # PinmapGen is stdlib-only — no install step needed when running
    # from the repo root.
    - run: >
        python -m tools.pinmapgen.cli
        --csv hardware/exports/sample_netlist.csv
        --mcu rp2040 --mcu-ref U1 --out-root generated --strict
```

`--strict` fails the build (exit 2) on validation errors or dropped pins.
To also catch drift in **committed** generated outputs, regenerate them
with `--reproducible` into their committed location and then
`git diff --exit-code -- <that path>` — the path must be tracked by git.
(The root-level `pinmaps/` and `firmware/` outputs are gitignored, so
diffing those never fails and gates nothing; this repo's own workflow
diffs the committed `examples/` outputs instead.)

### Pre-commit hook

```bash
bash .githooks/install-hooks.sh   # Linux/macOS
pwsh -File .githooks/install-hooks.ps1  # Windows
```

The hook regenerates pinmaps when files in `hardware/exports/` change and
stages the updated outputs automatically.

---

## PlatformIO integration

Add the generated Arduino header to your include path:

```ini
[env:rp2040]
platform = raspberrypi
board = pico
framework = arduino
build_flags = -I firmware/include
```

Then `#include "pinmap_arduino.h"` in your source files.

---

## Best practices

### Net naming

- Use descriptive names: `TEMP_SENSOR`, `I2C0_SDA`, `LED_STATUS`
- Avoid autogenerated labels: `N$1`, `NetR1_1`
- Keep bus members consistent: `UART0_TX` / `UART0_RX`

### MCU references

- Standardize across your team (always `U1` for the main MCU, for example).
- Update the schematic if Fusion defaults to `IC1` or `U?`.

### Output management

```
project/
├── hardware/exports/netlist.csv
├── firmware/
│   ├── include/pinmap_arduino.h
│   ├── micropython/pinmap_micropython.py
│   └── docs/
│       ├── PINOUT.md
│       └── pinout.mmd
└── pinmaps/pinmap.json
```

Commit generated files if your team expects firmware developers to track diffs.
Use separate output folders per board revision when managing variants.
