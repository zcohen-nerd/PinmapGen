# Frequently Asked Questions

Answers to common questions about PinmapGen workflows, design decisions, and best practices.

---

## General concepts

### Why not just name nets GPx in the schematic?

**Short answer:** PinmapGen supports both approaches but encourages semantic naming.

**Long answer:** 
- **Semantic names** (`I2C0_SDA`, `LED_DATA`) are self-documenting and survive schematic changes
- **Pin-based names** (`GP0`, `GP4`) break when you move nets to different pins
- **Role inference** works better with descriptive names, enabling validation warnings
- **Team collaboration** benefits from meaningful names that explain function
- **Fusion integration** becomes more powerful when nets describe intent, not just connectivity

### How does PinmapGen compare to manual pinout management?

| Approach | Pros | Cons |
|----------|------|------|
| **Manual spreadsheets** | Simple, universal tool | Error-prone, no validation, hard to sync |
| **Hardcoded constants** | Fast to write | Brittle, no traceability to hardware |
| **PinmapGen** | Automated, validated, multiple formats | Learning curve, toolchain dependency |

PinmapGen shines when:
- Multiple people work on hardware and firmware
- You need consistent outputs across MicroPython and Arduino
- Pin assignments change frequently during development
- Validation (USB pairs, strapping pins) prevents costly mistakes

### What MCUs will be supported in the future?

Current support: **RP2040, STM32G0, ESP32**

Likely additions based on demand:
- **STM32G4** (higher performance STM32)
- **ESP32-S3** (dual-core with camera support)
- **nRF52** (Bluetooth Low Energy)
- **SAMD21** (Arduino Zero family)

Community contributions welcome! Adding MCU profiles involves implementing pin normalization, capabilities, and validation rules. See [`docs/extending.md`](extending.md) (planned).

---

## Workflow questions

### Should I commit generated files to version control?

**Recommended approach:** Yes, commit generated outputs.

**Benefits:**
- Firmware developers see exactly what changed between commits
- CI/CD can validate that generated files stay in sync with CAD exports
- Rollbacks work cleanly without regenerating from old CAD files
- Team members without CAD tools can still build firmware

**Implementation:**
```bash
# Add to .gitignore (don't commit these)
hardware/exports/*.bak
*.tmp

# Do commit these
git add pinmaps/ firmware/
```

**Alternative:** Use CI/CD to generate on demand, but requires all contributors to have access to CAD exports.

### How do I handle multiple board revisions?

**Option 1: Separate output directories**
```bash
# Generate for each revision
python -m tools.pinmapgen.cli --csv rev_a.csv --mcu rp2040 --mcu-ref U1 --out-root build/rev_a
python -m tools.pinmapgen.cli --csv rev_b.csv --mcu rp2040 --mcu-ref U1 --out-root build/rev_b

# Firmware code can select at compile time
#ifdef BOARD_REV_A
#include "rev_a/pinmap_arduino.h"
#endif
```

**Option 2: Version-controlled branches**
```bash
# Hardware changes on hardware branch
git checkout hardware_rev_b
# Update CAD files and regenerate
git commit -am "Rev B: Move I2C to different pins"

# Merge to firmware when stable
git checkout main
git merge hardware_rev_b
```

**Option 3: Runtime board detection**
```python
# MicroPython example
board_rev = detect_board_revision()  # Read GPIO, ADC, etc.
if board_rev == "A":
    from pinmap_rev_a import *
elif board_rev == "B":
    from pinmap_rev_b import *
```

### Can I use PinmapGen with KiCad or other EDA tools?

**Current status:** PinmapGen expects Fusion Electronics or EAGLE formats.

**Workarounds:**
- **Export to CSV:** Most EDA tools can export netlists as CSV with columns for Part, Designator, Pin, Net
- **Format conversion:** Write scripts to convert from your EDA's native format to PinmapGen-compatible CSV
- **Manual CSV:** For small projects, hand-write the CSV netlist

**Future plans:** Community interest in KiCad support is noted. Parsers for other formats could be added following the same pattern as `eagle_sch.py` and `bom_csv.py`.

---

## Technical details

### What happens during "normalization"?

**Pin name normalization** converts various ways of referring to pins into canonical form:

**RP2040 examples:**
- `GPIO0` → `GP0`
- `IO15` → `GP15`
- `USB_DP` → `GP25`
- `ADC0` → `GP26`

**STM32G0 examples:**
- `PA0` → `PA0` (already canonical)
- `PORTA_0` → `PA0`
- `GPIO_A_0` → `PA0`

**ESP32 examples:**
- `IO2` → `GPIO2`
- `GPIO_02` → `GPIO2`

This handles schematic symbol variations and alternate naming conventions from different CAD libraries.

### How does differential pair detection work?

PinmapGen looks for **naming patterns** that indicate differential signals:

**Detected patterns:**
- `USB_DP` / `USB_DM`
- `CAN_H` / `CAN_L`
- `SIGNAL_P` / `SIGNAL_N`
- `DATA_DP` / `DATA_DN`

**Not detected:**
- Arbitrary pin pairs without naming convention
- Differential pairs split across multiple nets in unusual ways

**Validation rules:**
- Warns if only one half of a pair is found
- Checks that both pins are capable of the detected signal type
- Suggests impedance control requirements in generated documentation

### Why are some pins marked as "input-only"?

**ESP32 specifics:** GPIO34-GPIO39 are input-only due to silicon design.

**Validation purpose:** 
- Prevents assigning output signals (LEDs, motor control) to input-only pins
- Suggests alternative pins that support bidirectional operation
- Warns about pull-up resistor limitations on input-only pins

**Override behavior:** PinmapGen warns but doesn't block generation, allowing for external buffers or level shifters.

---

## Classroom and educational use

### How do I set up PinmapGen for a lab environment?

**Recommended setup:**
1. **Install on lab machines:** Use `pip install -e .` in shared directory
2. **Pre-created templates:** Provide starter CSV files with common RP2040 configurations
3. **File watcher demo:** Show `python -m tools.pinmapgen.watch` for instant feedback
4. **VS Code tasks:** Configure lab machines with PinmapGen tasks pre-loaded

**Student workflow:**
1. Design circuit and schematic in Fusion 360
2. Export CSV netlist to `hardware/exports/`
3. Run PinmapGen via VS Code task or Fusion add-in
4. Copy generated MicroPython constants to firmware project
5. Test with actual hardware

### What validation rules help students avoid common mistakes?

**RP2040-specific:**
- **USB pin usage:** Warns when GP24/GP25 used for GPIO instead of USB
- **Power pin detection:** Flags VCC/GND nets that connect to GPIO pins (usually wrong)
- **ADC pin optimization:** Suggests using ADC-capable pins for sensor inputs

**General validation:**
- **Duplicate pin usage:** Catches copy-paste errors in netlists
- **Unconnected nets:** Identifies nets that don't connect to the specified MCU
- **Naming consistency:** Warns about unusual pin name patterns

### How do I grade or assess PinmapGen outputs?

**Automated checking:**
```bash
# Verify students generated outputs
test -f pinmaps/pinmap.json && echo "JSON OK"
test -f firmware/micropython/pinmap_micropython.py && echo "MicroPython OK"

# Check for expected pin usage
grep "I2C.*SDA" firmware/docs/PINOUT.md && echo "I2C found"
grep "LED" firmware/micropython/pinmap_micropython.py && echo "LED constant found"
```

**Manual review points:**
- Semantic net naming (not just GP0, GP1, etc.)
- Appropriate pin choices for function (ADC for sensors, PWM-capable for LEDs)
- Proper differential pair usage for high-speed signals
- Documentation completeness in generated PINOUT.md

---

## Integration and automation

### How do I integrate PinmapGen with CI/CD?

**GitHub Actions example:**
```yaml
name: Validate Pinmaps
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install PinmapGen
      run: pip install -e .
    - name: Regenerate pinmaps
      run: python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root .
    - name: Check for changes
      run: git diff --exit-code pinmaps/ firmware/
```

**Pre-commit hook:**
```bash
# Install pre-commit hook
bash .githooks/install-hooks.sh

# Now commits automatically regenerate if hardware/ changes
```

### Can I customize the generated output formats?

**Current approach:** Modify emitter modules in `tools/pinmapgen/emit_*.py`.

**Customization examples:**
- **Add company header:** Modify `emit_arduino.py` to include copyright notice
- **Change naming conventions:** Update identifier generation in emitters
- **Additional file formats:** Create new `emit_custom.py` following existing patterns
- **Filter outputs:** Skip certain nets or pins based on custom logic

**Future plans:** Template-based generation system for easier customization without code changes.

### How do I add support for my company's custom MCU?

**Process overview:**
1. **Subclass MCUProfile:** Create new profile class in `tools/pinmapgen/`
2. **Implement pin definitions:** Map physical pins to capabilities and alternate names
3. **Add normalization rules:** Handle your MCU's pin naming conventions
4. **Register profile:** Add to CLI's `MCU_PROFILES` dictionary
5. **Test and validate:** Create test cases and sample netlists

**Detailed guide:** See [`docs/extending.md`](extending.md) (planned) for step-by-step instructions.

**Community contributions:** Pull requests welcome for popular MCU families!

---

## Troubleshooting and support

### What information should I include when reporting bugs?

**Essential information:**
1. **Complete command line:** Full `python -m tools.pinmapgen.cli` command that failed
2. **Error message:** Full Python traceback, not just the summary line
3. **Input data:** Minimal CSV file that reproduces the problem
4. **Environment:** OS, Python version, PinmapGen version/commit
5. **Expected vs actual:** What you expected to happen vs what actually happened

**Helpful extras:**
- Generated `pinmaps/pinmap.json` content (if any)
- Screenshots for Fusion add-in issues
- Output of `python -m tools.pinmapgen.cli --help`

### Where can I get help with complex workflows?

**Community resources:**
- **GitHub Discussions:** Ask questions and share solutions
- **Issue tracker:** Report bugs and request features  
- **Documentation:** User guide, troubleshooting, examples
- **Sample projects:** Use provided examples as starting points

**Professional support:**
For commercial or mission-critical usage, consider:
- Maintaining internal forks with your specific requirements
- Contributing improvements back to the community
- Training multiple team members on the toolchain
- Documenting your organization's specific workflows and conventions