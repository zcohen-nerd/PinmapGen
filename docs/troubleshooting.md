# Troubleshooting

Common problems and fixes when using PinmapGen.

---

## Installation issues

### Python not found

```
'python' is not recognized as an internal or external command
```

- Install Python 3.11+ from <https://python.org>.
- Add Python to the system PATH during installation.
- On Windows, try `py` instead of `python`.

### Import errors

```
ModuleNotFoundError: No module named 'tools.pinmapgen'
```

- Install in editable mode: `pip install -e .` from the repo root.
- Make sure the virtual environment is activated.
- Verify you are in the correct directory.

### Virtual environment problems

```bash
# Recreate if corrupted
rm -rf .venv
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
```

---

## CLI errors

### "CSV file not found"

- Check the path for typos.
- Use an absolute path if the relative one isn't resolving.
- Confirm the file exists: `ls hardware/exports/`.

### "MCU reference not found in netlist"

The reference designator passed via `--mcu-ref` doesn't appear in the CSV.

- Open the CSV and search for the MCU component.
- Common mismatches: `U1` vs `IC1`, or trailing whitespace.
- Case matters: `U1` ≠ `u1`.

### "Required columns missing"

`bom_csv.py` expects at least: `Net`, `Pin`, `Component`, `RefDes`.

- Open the CSV and check the header row.
- Fusion exports sometimes use different column names (e.g., `Designator`
  instead of `RefDes`). Rename the column or adjust the export settings.
- Remove any BOM (byte order mark) characters at the start of the file.

### Empty or partial output

- Verify the MCU reference designator matches the schematic exactly.
- Check `pinmaps/pinmap.json` to see which nets were parsed.
- If the Markdown tables are empty, the source export likely omitted nets for
  that MCU.

---

## Fusion ULP problems

### ULP not appearing in Fusion

- Confirm `PinmapGen.ulp` is in the Fusion ULP directory
  (`%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\` on Windows).
- Restart Fusion 360 after copying script files.
- Use **Automation → Run ULP… → Browse** to select the file manually.

### ULP fails to run

- Check for syntax errors in the Text Commands panel.
- Verify you are in the **Electronics** workspace, not the Design workspace.
- Try running `PinmapGen_Manual.ulp` as a fallback.

### Generated files not found after ULP run

- The output folder might be on the real Desktop, not the OneDrive-redirected
  Desktop. Check `C:\Users\<you>\Desktop`.
- Verify the output path shown in the ULP dialog before clicking Generate.

### Python / CLI errors from ULP

- Ensure Python 3.11+ is installed and on PATH.
- Verify the PinmapGen project path in the ULP matches the actual location.
- Run the equivalent CLI command manually to isolate the problem.

---

## Generated output issues

### MicroPython file won't import

```
SyntaxError: invalid syntax
```

- Open the file and check for obvious problems.
- Confirm Python 3.11+ was used for generation (older versions may produce
  incompatible output in edge cases).
- Regenerate the file from a clean CSV.

### Arduino header doesn't compile

```
error: 'PIN_XYZ' was not declared in this scope
```

- Check that `#include "pinmap_arduino.h"` uses the correct path.
- Verify the include path in your build system (e.g., `platformio.ini`
  `build_flags = -I firmware/include`).

### Pin numbers look wrong

- The emitters use the GPIO number, not the physical package pin number.
- Compare the generated output against `pinmaps/pinmap.json` and the MCU
  datasheet.

### Mermaid diagram not generated

- Pass `--mermaid` to the CLI.
- If the diagram is empty, there may be no nets to visualize for the given MCU
  reference.

---

## Validation warnings

### "Pin GPxx is a USB pin"

USB differential pair pads are flagged when used for general GPIO. Either
reserve them for USB or acknowledge the override.

### "Input-only pin used as output"

ESP32 pins 34–39 are input-only. Reassign the net to a different GPIO.

### "Strapping pin used"

ESP32 pins 0, 2, 5, 12, 15 affect boot behavior. Ensure external pull-ups or
pull-downs match the boot mode you need.

### "Differential pair incomplete"

Only one half of a pair (e.g., `USB_DP` without `USB_DM`) was found. Connect
both signals or rename the net so it isn't detected as a pair.

### "Duplicate pin assignment"

Two nets are connected to the same MCU pin. Fix the schematic or CSV.

---

## Performance

### Slow generation on large netlists

- Use `--no-mermaid` to skip diagram generation if it isn't needed.
- Split large CSVs into per-MCU files.
- Close other applications if running on limited RAM.

### File system issues

- Network drives and container-mounted volumes can be slow for file I/O. Use
  a local directory for `--out-root`.

---

## Getting help

### Self-service debugging

1. Rerun with `--verbose` to print normalization details.
2. Inspect `pinmaps/pinmap.json` → `metadata` for warnings and errors.
3. Validate the input file manually (`head`, `wc -l`, text editor).
4. Test with a minimal CSV to isolate the problem.

### Reporting issues

Include the following in bug reports:

1. Python version (`python --version`)
2. OS (Windows 10/11, macOS, Ubuntu, etc.)
3. Full command line used
4. Complete error output (not just the summary)
5. Minimal CSV or `.sch` that reproduces the problem
