# Fusion 360 ULP User Guide

How to use the PinmapGen ULP to generate firmware pinmaps directly from the
Fusion 360 Electronics workspace.

## What is a ULP?

A ULP (User Language Program) is an automation script that runs inside Fusion
360 Electronics. Unlike add-ins, ULPs:

- Work in the Electronics workspace without special permissions
- Don't require app-store installation
- Have full access to schematic data
- Deploy with a simple file copy

## Installation

> **Windows only.** The ULP automates generation through PowerShell and
> cmd.exe; on macOS/Linux it shows a dialog pointing at the CLI workflow
> (`docs/usage.md`) instead. It needs Python 3.11+ on the machine — before
> each run it checks `python` on PATH and falls back to the `py -3`
> launcher, so it works even if "Add python.exe to PATH" was left
> unticked during the Python install.

### 1. Copy the ULP file

**Windows:**
```cmd
copy "PinmapGen.ulp" "%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\"
```

**Alternative:** Navigate to `%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\`
in Explorer and drop the file in.

### 2. Restart Fusion 360

Close and reopen Fusion so the ULP is recognized.

## Usage

### 1. Open the Electronics workspace

Make sure your schematic is open in the **Electronics** workspace.

### 2. Run the ULP

**Automation → Run ULP → PinmapGen**

### 3. Configure settings

**PinmapGen repository** — The folder where you cloned the PinmapGen repo
(the ULP invokes its CLI from there). Entered once and saved to a settings
file next to the ULP for future runs.

**MCU reference designator** — The ref des of your MCU (e.g., `U1`, `IC1`).
Must match the schematic.

**Project name** — Used for the output folder name. Defaults to a timestamped
name if left blank.

**MCU type** — Pick from the quick buttons (all 13 built-in profiles) or type
a profile name.

**Output directory** — Where generated files go. Defaults to a
`PinmapGen_Output` folder next to the ULP; you can type any custom path.

**Output formats** — Check the boxes for the formats you want (MicroPython,
Arduino, Markdown, Mermaid).

### 4. Generate

Click **Generate Pinmap**. The ULP:
1. Reads the netlist from the schematic object model.
2. Writes a temporary CSV.
3. Invokes the PinmapGen CLI, capturing its full output to
   `pinmapgen_log.txt` in the output folder.
4. Shows the result:
   - **Clean run** — a success dialog listing the generated files.
   - **Run with issues** — the CLI reported warnings, validation errors,
     or dropped pins: the dialog shows the full log so you can review
     them before trusting the generated files.
   - **Failure** — the dialog shows the log with the actual error
     (wrong MCU reference, bad netlist, and so on). If no log was
     created at all, Python never started — check that Python 3.11+ is
     installed and on PATH and the repository path is right.
5. Opens File Explorer at the output folder.

## Generated output

```
<project>/
├── pinmaps/
│   └── pinmap.json
├── firmware/
│   ├── micropython/pinmap_micropython.py
│   ├── include/pinmap_arduino.h
│   └── docs/
│       ├── PINOUT.md
│       └── pinout.mmd
├── pinmapgen_log.txt   (full CLI output from the last run)
└── auto_netlist.csv    (temporary; removed after a clean run, kept
                         after a run with issues for troubleshooting)
```

### File descriptions

| File | Purpose |
|------|---------|
| `pinmap.json` | Machine-readable pin data with metadata and validation info |
| `pinmap_micropython.py` | Python module for MicroPython/CircuitPython |
| `pinmap_arduino.h` | C++ header for Arduino IDE or PlatformIO |
| `PINOUT.md` | Markdown pinout documentation with tables |
| `pinout.mmd` | Mermaid diagram source |

## Features

### Automatic role detection

The ULP detects pin roles from net names:
- I2C (SDA, SCL)
- SPI (MOSI, MISO, SCK, CS)
- UART (TX, RX)
- PWM, GPIO, USB differential pairs, analog inputs

### MCU-specific validation

- Warns about special pins (boot, strapping, input-only)
- Detects differential pairs (USB D+/D-)
- Validates assignments against MCU capabilities

### Bus grouping

Related signals are grouped automatically: I2C buses, SPI buses, UART
channels, control groups.

## Research ULPs

Two additional ULPs are included for development/debugging:

- `ulp_schematic_access_test.ulp` — Lists accessible schematic data
  structures (nets, parts, pins).
- `direct_netlist_generator.ulp` — Generates a CSV directly from the
  schematic object model without using `EXPORT NETLIST`.

## Troubleshooting

### ULP not found

- Verify `PinmapGen.ulp` is in the Fusion ULP directory.
- Restart Fusion 360 after copying.
- Confirm you're in the **Electronics** workspace, not Design.

### Export failed

- Check that your schematic has nets connected to the specified MCU.
- Verify the reference designator exists.
- Make sure the output path is valid and writable.

### Python / CLI errors

- The failure dialog shows the CLI's own error from `pinmapgen_log.txt`
  (in the output folder) — read that first; it names the real problem.
- "Python 3.11 or newer was not found": the ULP probes `python` on PATH
  and the `py -3` launcher before each run. Install Python 3.11+ from
  python.org (the Microsoft Store's fake `python.exe` alias is
  correctly rejected).
- If the dialog says no log file was created, the "PinmapGen repository"
  field most likely doesn't point at your cloned repo (the ULP checks
  for `tools/pinmapgen/cli.py` there), or the repo copy is older than
  the ULP.
- Run the equivalent CLI command manually to isolate the issue.

### Permission errors

- Try a different output directory (Desktop instead of system folders).
- Run Fusion as administrator if necessary.
- Ensure the output directory isn't read-only.

### Files not generated

- Read `pinmapgen_log.txt` in the output folder (also shown in the
  result dialog) — dropped pins and validation errors are listed there.
- Verify the MCU ref des is correct.
- Ensure nets are properly named and connected.

## Advanced usage

### Other MCU profiles

The ULP dialog supports all 13 built-in profiles (RP2040, RP2350, ESP32,
ESP32-S3, ESP32-C3, STM32G0, STM32F411, STM32H743, nRF52840, ATmega328P,
ATmega2560, ATSAMD21, ATSAMD51). For custom TOML profiles, run the CLI
directly with `--mcu <profile> --profile-dir <dir>`.

### Version control integration

Commit generated files alongside the schematic for:
- Firmware team collaboration
- Pin assignment history
- Automated build integration

### Batch processing

For multiple projects:
1. Use the CLI with watch mode: `python -m tools.pinmapgen.watch`
2. Set up VS Code tasks for repeated generation
3. Write shell scripts for standardized workflows

## Best practices

### Schematic naming

- Use descriptive net names (`I2C_SDA`, `LED_STATUS`, `BUTTON_1`)
- Avoid generic names (`NET_1`, `N$123`)
- Be consistent across the design

### Project organization

- Use meaningful project names
- Organize output by project and version
- Keep generated files with their source schematics

### Team workflow

1. Designer creates/updates schematic
2. Designer runs ULP to generate pinmaps
3. Designer shares the output folder with the firmware team
4. Firmware team integrates generated headers/modules
5. Iterate as pin assignments change
