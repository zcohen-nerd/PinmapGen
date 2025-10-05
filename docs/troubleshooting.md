# Troubleshooting Guide

Common issues, solutions, and debugging techniques for PinmapGen users.

---

## Table of contents

1. [Installation issues](#installation-issues)
2. [CLI errors](#cli-errors)
3. [Fusion add-in problems](#fusion-add-in-problems)
4. [Generated output issues](#generated-output-issues)
5. [Validation warnings](#validation-warnings)
6. [Performance and reliability](#performance-and-reliability)
7. [Getting help](#getting-help)

---

## Installation issues

### Python environment conflicts

**Problem:** `ModuleNotFoundError` when running CLI commands.

**Solution:**
```bash
# Verify Python installation
python --version  # Should be 3.11+

# Check if PinmapGen is installed
python -c "import tools.pinmapgen.cli; print('OK')"

# Reinstall in development mode
pip install -e .
```

### Virtual environment issues

**Problem:** Commands work in one terminal but not another.

**Solution:**
```bash
# Activate your virtual environment consistently
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\Activate.ps1  # Windows PowerShell

# Verify environment
which python  # Should point to .venv
```

### Missing dependencies

**Problem:** `ImportError` for pytest, ruff, or other development tools.

**Solution:**
```bash
# Install test dependencies
pip install pytest ruff
```

---

## CLI errors

### MCU not found errors

**Error:** `MCU 'U1' not found in design`

**Cause:** Reference designator mismatch between CLI argument and schematic.

**Solution:**
1. Check your schematic for the actual MCU reference (U1, U2, IC1, etc.)
2. Update the `--mcu-ref` argument to match exactly
3. Ensure case sensitivity: `U1` ≠ `u1`

### Invalid pin errors

**Error:** `Invalid GPIO pin: GP99 (RP2040 valid range: GP0-GP29)`

**Cause:** Pin name in netlist doesn't match MCU profile expectations.

**Solution:**
1. Verify the net is connected to the correct MCU pin in your schematic
2. Check for typos in pin names (GP4 vs G4P)
3. Confirm MCU profile matches your actual part (RP2040 vs RP2350)

### File not found errors

**Error:** `CSV file not found: hardware/exports/netlist.csv`

**Cause:** Path doesn't exist or is incorrect.

**Solution:**
```bash
# Check file exists
ls hardware/exports/

# Use absolute path if needed
python -m tools.pinmapgen.cli --csv "C:\full\path\to\netlist.csv" --mcu rp2040 --mcu-ref U1

# Re-export from Fusion if missing
```

### Permission errors

**Error:** `Permission denied: Cannot write to pinmaps/`

**Cause:** Output directory is read-only or files are open elsewhere.

**Solution:**
```bash
# Check permissions
ls -la pinmaps/

# Close files in VS Code/text editors
# Change output directory
python -m tools.pinmapgen.cli --csv ... --out-root /tmp/pinmaps
```

---

## Fusion add-in problems

### Add-in not appearing

**Problem:** PinmapGen button missing from Fusion toolbar.

**Solution:**
1. Copy `fusion_addin/PinmapGen.ulp` into `%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\`.
2. Restart Fusion 360 completely.
3. Check **Tools → ADD-INS → Scripts and Add-Ins → PinmapGen → Run**.
4. Verify you're in **Electronics** workspace, not **Design**.

### Python runtime errors in Fusion

**Problem:** Add-in crashes with Python import errors.

**Solution:**
1. Ensure Fusion 360 has Python enabled (usually automatic).
2. Try other Python add-ins to test Fusion's Python environment.
3. Re-copy the ULP scripts to refresh the deployment.
4. Check Fusion logs: **Help → Show Data Panel → Text Commands → Show Data Panel**.

### Electronics workspace errors

**Error:** `Electronics workspace not active`

**Cause:** Currently in Design workspace instead of Electronics.

**Solution:**
1. Click **Electronics** tab at top of Fusion window
2. If tab is missing, check that your design has electronics data
3. Switch to a design that includes schematic or PCB data

### Output folder issues

**Problem:** Generated files appear in unexpected locations.

**Solution:**
1. Use **Browse** button to select specific output folder
2. Avoid network drives if possible (can be slow/unreliable)
3. Choose a folder you have write permissions for
4. Check **Recent** → **View Files** to see actual output location

---

## Generated output issues

### Empty or missing files

**Problem:** CLI succeeds but output files are empty.

**Cause:** Usually no nets found for specified MCU reference.

**Debugging:**
```bash
# Run with verbose output
python -m tools.pinmapgen.cli --csv ... --mcu rp2040 --mcu-ref U1 --verbose

# Check JSON output for debugging info
cat pinmaps/pinmap.json | jq '.metadata'

# Verify CSV contains expected data
head -5 hardware/exports/sample_netlist.csv
```

### Incorrect pin mappings

**Problem:** Generated constants don't match expected pins.

**Solution:**
1. Check `pinmaps/pinmap.json` for raw mapping data
2. Verify net names in original schematic
3. Review MCU profile pin definitions for special cases
4. Consider USB differential pairs (GP24/GP25 on RP2040)

### Format-specific issues

**Problem:** MicroPython imports fail or Arduino compilation errors.

**Solution:**
```bash
# Test MicroPython syntax
python -c "exec(open('firmware/micropython/pinmap_micropython.py').read()); print('Syntax OK')"

# Test Arduino compilation with minimal sketch
# Include generated header in simple Arduino program

# Check for invalid C identifiers
grep -E '^[^A-Za-z_]' firmware/include/pinmap_arduino.h
```

---

## Validation warnings

### USB differential pair warnings

**Warning:** `Pin GP24 is a USB pin - consider reserving for USB functionality`

**Interpretation:** You're using USB pins for general GPIO, which conflicts with USB operation.

**Action:**
- If you need USB, reassign the net to a different pin.
- If no USB needed, acknowledge the warning and continue.
- Document the design decision for firmware and validation reviews.

### Strapping pin warnings (ESP32)

**Warning:** `GPIO0 low at boot enters download mode`

**Interpretation:** ESP32 boot behavior depends on pin state at power-on.

**Action:**
- Add appropriate pull-up/pull-down resistors per ESP32 datasheet
- Avoid driving these pins low during boot unless intentional
- Document boot sequence requirements for firmware team

### Input-only pin warnings

**Warning:** `Input-only pin used as output`

**Interpretation:** MCU pin physically cannot drive output.

**Action:**
- Reassign net to a bidirectional pin
- Add external buffer/level shifter if needed
- Update schematic to use appropriate pins

### Multi-pin net warnings

**Warning:** `Net 'POWER' connects to multiple pins - may indicate routing error`

**Interpretation:** Single net connects to multiple MCU pins.

**Action:**
- For power/ground nets: Normal, warning can be ignored
- For signal nets: Usually indicates schematic error, check connections
- Split net if pins should be independent

---

## Performance and reliability

### Slow generation times

**Problem:** CLI takes >30 seconds to complete.

**Debugging:**
```bash
# Profile with timing
time python -m tools.pinmapgen.cli --csv ... --verbose

# Check input file size
wc -l hardware/exports/sample_netlist.csv

# Simplify for testing
head -20 hardware/exports/sample_netlist.csv > test_small.csv
```

**Solution:**
- Large CSV files (>10k rows) may be slow
- Consider filtering CSV to relevant components only
- Upgrade to SSD storage for faster I/O

### File watcher issues

**Problem:** `python -m tools.pinmapgen.watch` doesn't detect changes.

**Solution:**
```bash
# Verify file permissions
ls -la hardware/exports/

# Test manual trigger
touch hardware/exports/sample_netlist.csv

# Use shorter polling interval
python -m tools.pinmapgen.watch hardware/exports --interval 0.5

# Check for filesystem-specific issues (network drives, containers)
```

### Memory usage

**Problem:** Python process uses excessive memory.

**Solution:**
- Close other applications if running on limited RAM
- Split large CSV files into smaller chunks
- Use `--no-mermaid` to skip diagram generation if not needed

---

## Getting help

### Self-service debugging

1. **Enable verbose output** with `--verbose` flag
2. **Check logs** in `pinmaps/pinmap.json` metadata section
3. **Validate input** files with `head`, `wc -l`, text editor inspection
4. **Test minimal cases** with simplified CSV data

### Reporting issues

When opening issues, include:

1. **PinmapGen version:** `python -m tools.pinmapgen.cli --help` (check version info)
2. **Python version:** `python --version`
3. **Operating system:** Windows 10, macOS 13, Ubuntu 22.04, etc.
4. **Full command line:** Exact `python -m tools.pinmapgen.cli` command used
5. **Error messages:** Complete error text, not just summary
6. **Sample data:** Minimal CSV that reproduces the problem

### Community resources

- **GitHub Issues:** Report bugs and request features
- **Discussions:** Ask questions and share workflows
- **Documentation:** This troubleshooting guide, user guide, README
- **Sample data:** Use `hardware/exports/sample_netlist.csv` for testing

### Professional support

For mission-critical or commercial deployments:
- Consider maintaining internal forks for stability
- Implement automated testing of your specific MCU/netlist patterns
- Document organization-specific workflows and edge cases
- Train multiple team members on both CLI and Fusion workflows