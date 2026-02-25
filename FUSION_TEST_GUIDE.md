# Fusion 360 ULP Testing Guide

Test plan for verifying the PinmapGen ULP inside Fusion 360. Work through
tests F1–F8 in order; earlier tests are prerequisites for later ones.

Estimated total time: ~2.5 hours.

---

## Pre-testing setup

### Step 1: Deploy the ULP

Copy the production ULP into Fusion's ULP directory:

```powershell
Copy-Item fusion_addin/PinmapGen.ulp "$env:APPDATA\Autodesk\Autodesk Fusion 360\API\ULPs\"
```

Alternative paths:
- Windows default: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\`
- macOS: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/ULPs/`

Verify:
- `PinmapGen.ulp` appears in the Fusion ULP directory
- Optionally copy `PinmapGen_Manual.ulp` as well

### Step 2: Launch the ULP

1. Open Fusion 360 and switch to the **Electronics** workspace.
2. **Automation → Run ULP…** → select **PinmapGen.ulp**.
3. Click **Open** to display the dialog.

If the ULP is missing:
- Confirm the `.ulp` file exists in the correct directory.
- Restart Fusion 360 after copying.
- Use **Browse** to select the full path manually.

---

## Test F1: ULP deployment and launch

**Objective:** Verify the ULP loads without errors.

**Steps:**
1. Copy `PinmapGen.ulp` into the Fusion ULP directory.
2. **Electronics** workspace → **Automation → Run ULP…** → select it.
3. Check the Text Commands panel for errors.

**Pass criteria:**
- ULP listed in the Run ULP dialog (or loadable via Browse)
- Dialog opens with project name, MCU, and output options
- No errors in the Text Commands console

---

## Test F2: UI validation

**Objective:** All UI elements render and respond correctly.

**Steps:**
1. Open the PinmapGen dialog.
2. Verify: MCU dropdown (RP2040, STM32G0, ESP32), output format checkboxes,
   generate button, output directory selector.
3. Toggle each checkbox; change the dropdown.

**Pass criteria:**
- All elements display
- Dropdown lists all MCU options
- Checkboxes toggle
- UI is responsive

---

## Test F3: Electronics data extraction

**Objective:** The ULP reads net/pin data from a live schematic.

**Prerequisites:** Create a simple test circuit with an RP2040 (U1), 5–10
named nets, and a mix of I2C/SPI/GPIO connections.

**Steps:**
1. Open the test design.
2. Run PinmapGen, select RP2040 / U1, click Generate.
3. Watch the Text Commands panel.

**Pass criteria:**
- Component data extracted without errors
- Nets identified and parsed
- Pin assignments detected

---

## Test F4: File generation

**Objective:** Output files are created with correct content.

**Steps:**
1. Use the same circuit from F3.
2. Select all output formats, choose an output directory, click Generate.
3. Inspect the output directory.

**Pass criteria:**
- All selected files created (JSON, MicroPython, Arduino, Markdown, Mermaid)
- Pin mappings match the schematic connections
- Success message displayed in Fusion

---

## Test F5: Error handling

Run each sub-test and verify the ULP reports a clear message without crashing.

| Sub-test | Scenario | Expected |
|----------|----------|----------|
| F5a | No active Electronics design | Error: missing Electronics design |
| F5b | MCU ref set to `U99` (doesn't exist) | Error: MCU component not found |
| F5c | No output directory selected | Error or sensible default used |
| F5d | Schematic has MCU but zero connections | Warning about no nets; no crash |

---

## Test F6: Real-world circuit

**Objective:** Process a complex, realistic design.

**Suggested circuit:**
- RP2040 (U1)
- I2C sensor on GP0/GP1
- SPI display on GP2–GP5
- UART module on GP6/GP7
- 2 LEDs on GP10/GP11
- 2 buttons on GP12/GP13
- USB connector (DP/DM)
- Power connections (VCC, GND)

**Pass criteria:**
- 15+ nets detected
- Bus groups identified (I2C, SPI, UART)
- USB differential pair detected
- Pin roles inferred correctly
- MicroPython and Arduino output have correct constants

---

## Test F7: Multi-MCU profiles

**Objective:** Different profiles produce appropriate warnings.

**Steps:**
1. Use the basic circuit from F3/F6.
2. Generate with RP2040, then STM32G0, then ESP32.

**Pass criteria:**
- RP2040: clean generation with `GPxx` names
- STM32G0: warnings about invalid GP pins, suggests `PA`/`PB` format
- ESP32: warnings about invalid pins, suggests `GPIO` format
- All three profiles produce output files

---

## Test F8: Performance and usability

**Metrics:**
- Generation completes in < 5 seconds for typical circuits
- Fusion remains responsive during processing
- Generated files < 100 KB for typical designs
- Errors are recoverable without restarting the ULP

Test with increasing complexity (10, 20, 50+ nets) and intentionally create
errors to confirm recovery.

---

## Release-blocking issues

Anything in this list must be fixed before shipping:

- ULP fails to install or load
- Data extraction fails silently
- Generated files are corrupt or empty
- ULP crashes Fusion 360
- UI is unresponsive
- Error messages are missing or misleading

Post-launch fixes are acceptable for minor UI polish, extra validation
warnings, performance tuning, and enhanced messages.

---

## Testing checklist

### Installation and setup
- [ ] `PinmapGen.ulp` copied into Fusion ULP directory
- [ ] ULP appears in **Automation → Run ULP…**
- [ ] Dialog opens and renders correctly
- [ ] No console errors on startup

### Basic functionality
- [ ] MCU dropdown works
- [ ] Output format checkboxes toggle
- [ ] Directory selection works
- [ ] Generate button triggers processing

### Data extraction
- [ ] Component references resolved (U1, U2, etc.)
- [ ] Net names captured accurately
- [ ] Pin assignments detected

### File generation
- [ ] JSON pinmap has correct structure
- [ ] MicroPython file has valid syntax and pin constants
- [ ] Arduino header has correct `#define` statements
- [ ] Markdown documentation formatted correctly
- [ ] Mermaid diagram generated (when selected)

### Error handling
- [ ] Missing Electronics design handled gracefully
- [ ] Invalid MCU ref produces clear error
- [ ] No-nets scenario handled without crash
- [ ] File write permission issues reported clearly

### Real-world testing
- [ ] Complex circuit (15+ nets) processes correctly
- [ ] Bus detection works (I2C, SPI, UART groups)
- [ ] Differential pairs identified (USB, CAN)
- [ ] Pin role inference accurate
- [ ] Multi-MCU warnings display properly

---

## Installation troubleshooting

### "Access Denied" or copy failures

```
Access is denied: 'C:\Users\...\API\ULPs\PinmapGen.ulp'
```

- Close Fusion 360 before copying files.
- Copy to a user-writable folder first, then move with elevated permissions.
- Verify the destination path exists.

### ULP not appearing in Fusion

- Confirm the `.ulp` file is in the correct directory.
- Restart Fusion 360.
- Use **Automation → Run ULP… → Browse** to select manually.
- Check the Text Commands panel for syntax errors.
