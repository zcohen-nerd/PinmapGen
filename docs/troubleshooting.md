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

- `python -m tools.pinmapgen.cli` must be run **from the repo root** (the
  folder containing `tools/`). `cd` there first — that fixes this error
  in almost every case.
- To run from any directory instead, install once in editable mode:
  `pip install -e .` from the repo root (this also adds the `pinmapgen`
  command).
- If you installed into a virtual environment, make sure it is activated.

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

### "No entries found for MCU reference"

The reference designator passed via `--mcu-ref` doesn't appear in the CSV.
The error message lists the reference designators the file *does* contain
— pick yours from that list. Matching is case-insensitive and ignores
surrounding whitespace, so `u1` finds `U1`; the usual real cause is `U1`
vs `IC1`.

### "CSV is missing required column(s)"

The parser needs `Net`, `Pin`, and `RefDes` (`Component` is optional).
Headers are matched case-insensitively, common aliases are accepted
(`Designator` → RefDes, `Net Name` → Net, `Part` → Component), the
delimiter (comma/semicolon/tab) is detected automatically, and Excel's
UTF-8 BOM is handled — so this error means the header row genuinely
lacks a recognizable Net, Pin, or RefDes column. The error message lists
the columns that were found.

- The easy fix: export with `fusion_addin/export_netlist.ulp`, which
  writes exactly the right format (works on Windows and macOS).
- For hand-made CSVs, rename the offending header to one of the accepted
  spellings.

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

- Every ULP run writes `pinmapgen_log.txt` into the output folder with the
  CLI's full output — the failure dialog shows it, and it's the first thing
  to attach to a bug report.
- If the dialog says no log file was created, Python never started: ensure
  Python 3.11+ is installed and on PATH, and the PinmapGen repository path
  in the ULP matches the actual location.
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
- Check the input side too: the CSV's `Pin` column must hold logical pin
  names (`GP15`, `GPIO4`, `PA0`). A bare number like `2` is interpreted
  as *GPIO 2* — and the CLI prints a warning when it does — but many CAD
  exports put the physical *pad* number there, which produces a
  plausible-looking pinmap that is wrong on nearly every pin (pad 2 of
  an RP2040 is GPIO 0). The Fusion ULP exports symbol pin names for
  exactly this reason.
- Compare the generated output against `pinmaps/pinmap.json` and the MCU
  datasheet.

### Mermaid diagram not generated

- Pass `--mermaid` to the CLI.
- If the diagram is empty, there may be no nets to visualize for the given MCU
  reference.

---

## Validation messages

These are the exact messages the tool prints. **Errors** fail `--strict`
(exit 2, no output written); **warnings** are advisory and never block
generation.

### Error: "Pin ... used by multiple nets: '...' and '...'"

Two signals share one MCU pin — always a genuine conflict. Fix the
schematic or CSV.

### Warning: "Net '...' connects to multiple pins [...]"

One net touches several MCU pins. Fine for a shared bus; otherwise check
the routing. (Recognized power/ground rail names are not flagged.)

### Warning: "Potential lonely differential pair: '...' has no partner"

A pair-style net (`X_DP`, `X_P`, `CAN_H`, `USB_D+`, …) has no matching
partner net. Connect and name both halves. Active-low signals like
`RESET_N` or `CS_N` are deliberately *not* flagged.

### Warning: "GPIOxx is a boot strapping pin" (and similar special-pin notes)

The pin has a special job on your chip (boot strapping, flash voltage,
default console, not bonded on your module, …). Double-check the pin is
safe for your signal or move it.

### Warning: "... is input-only, but net role '...' implies an output"

The pin has no output driver (e.g. ESP32 GPIO34–39) and the net's name
suggests the MCU drives it. Move the signal to an output-capable pin.

### Warning: "... pin(s) were bare numbers and were interpreted as logical GPIO numbers"

The Pin column held plain numbers; they were read as GPIO numbers, not
package pad numbers. Verify one pin against the schematic, or export
with pin names (`GP2`, `PA0`).

### Warning: "net '...' is emitted as constant '...'"

The net's natural identifier was reserved (`SPI`, `MOSI`, `A0`, …) or
collided with another net, so the generated constant carries a suffix.

---

## Performance

### Slow generation on large netlists

- Mermaid is opt-in — simply omit `--mermaid` if the diagram isn't
  needed; `--no-micropython` / `--no-arduino` / `--no-markdown` skip the
  other formats.
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
