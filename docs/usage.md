# PinmapGen Usage Guide

This guide provides detailed workflows and advanced examples for using PinmapGen effectively in various scenarios.

---

## Table of Contents

1. [Basic Workflows](#basic-workflows)
2. [Advanced ULP Usage](#advanced-ulp-usage)
3. [CLI Power User Guide](#cli-power-user-guide)
4. [Team Workflows](#team-workflows)
5. [Educational Usage](#educational-usage)
6. [Troubleshooting Scenarios](#troubleshooting-scenarios)
7. [Integration Examples](#integration-examples)

---

## Basic Workflows

### Workflow 1: Fusion 360 One-Click Generation

**Perfect for:** PCB designers who want immediate firmware handoff

```
1. Open schematic in Fusion 360 Electronics
2. Tools → Run ULP → PinmapGen.ulp
3. Configure:
   - Project name: "MyProject"
   - MCU: RP2040 (or STM32G0/ESP32)
   - Output formats: Select all
   - Path: Desktop (or custom)
4. Click "Generate Pinmap"
5. Files appear in Desktop/MyProject/
```

**Output:** Complete firmware-ready pin definitions in multiple formats.

### Workflow 2: CLI Batch Processing

**Perfect for:** Firmware engineers processing multiple designs

```bash
# Process multiple netlists
python -m tools.pinmapgen.cli --csv design1.csv --mcu rp2040 --mcu-ref U1 --out-root ./output1
python -m tools.pinmapgen.cli --csv design2.csv --mcu stm32g0 --mcu-ref IC1 --out-root ./output2
python -m tools.pinmapgen.cli --csv design3.csv --mcu esp32 --mcu-ref U2 --out-root ./output3 --mermaid
```

---

## Advanced ULP Usage

### Project Organization Strategies

**Timestamped Projects:**
```
1. Set project name to base name: "ProductionBoard"
2. Click "Add Timestamp" → "ProductionBoard_1727496234"
3. Generates: Desktop/ProductionBoard_1727496234/
```

**Version Control Integration:**
```
1. Set output directory to your git repo: "C:/Projects/MyFirmware"
2. Project name: "v2.1-pinouts"
3. Generated files go directly into version control
```

### Multi-MCU Projects

**For designs with multiple MCUs:**

```
Run 1: MCU Reference = "U1" (Main processor)
Run 2: MCU Reference = "U2" (Co-processor)
Run 3: MCU Reference = "U3" (Sensor hub)
```

Each run generates separate pin definitions for each MCU in the same project.

### Preview and Validation Workflow

**Before generating files:**

```
1. Click "🔍 Preview Generation" - Review what will be created
2. Click "Analyze" next to MCU Reference - Validate schematic
3. Check warnings for:
   - Missing MCU reference
   - No components/nets
   - Pin conflicts
4. Fix issues in schematic if needed
5. Generate with confidence
```

---

## CLI Power User Guide

### Advanced CLI Options

**Verbose Output for Debugging:**
```bash
python -m tools.pinmapgen.cli --csv netlist.csv --mcu rp2040 --mcu-ref U1 --out-root ./output --verbose
```

**Include Visual Diagrams:**
```bash
python -m tools.pinmapgen.cli --csv netlist.csv --mcu rp2040 --mcu-ref U1 --out-root ./output --mermaid
```

### VS Code Integration

**Use built-in tasks:**
```bash
# In VS Code terminal
Ctrl+Shift+P → "Tasks: Run Task" → "Generate Pinmap"
```

**Watch mode for development:**
```bash
# Auto-regenerate when netlists change
Ctrl+Shift+P → "Tasks: Run Task" → "Watch Pinmap"
```

### Custom MCU Profiles

**Adding new MCU support:**

1. Create a profile module alongside the existing profiles (e.g., `tools/pinmapgen/newchip_profile.py`).
2. Implement the class by subclassing `MCUProfile` from `tools.pinmapgen.mcu_profiles` and defining pin mappings plus validation rules.
3. Register the profile in `MCU_PROFILES` inside `tools/pinmapgen/cli.py` so the CLI exposes it via `--mcu`.
4. Add fixtures and tests under `tests/` to validate normalization and emitter outputs.

---

## Team Workflows

### Design → Firmware Handoff

**PCB Designer workflow:**
```
1. Complete schematic in Fusion 360
2. Run ULP with standardized settings:
   - Project: "[Product]-[Version]-[Date]"  
   - MCU: [Agreed upon type]
   - All formats enabled
3. Zip output folder and share with firmware team
```

**Firmware Developer workflow:**
```
1. Extract shared pinmap files
2. Copy relevant files to project:
   - `pinmap_micropython.py` → src/
   - `pinmap_arduino.h` → include/
   - `PINOUT.md` → docs/
3. Import and use in code
```

### Continuous Integration

**GitHub Actions example:**
```yaml
- name: Validate Pinmaps
  run: |
    python -m tools.pinmapgen.cli --csv hardware/netlist.csv --mcu rp2040 --mcu-ref U1 --out-root ./generated
    # Compare with committed versions
    git diff --exit-code generated/ || echo "Pinmaps need update"
```

### Code Review Integration

**Include in PR reviews:**
```
1. Generate pinmaps from updated schematic
2. Commit generated files to PR
3. Review changes in pin assignments
4. Validate against design requirements
```

---

## Educational Usage

### Lab Exercise Workflow

**Instructor setup:**
```
1. Create template schematic with MCU
2. Students add their own components and connections
3. Students run ULP to generate pin definitions
4. Immediate feedback on design choices
```

**Student learning progression:**
```
Week 1: Basic LED connections → Simple pin assignments
Week 2: Sensor integration → I2C/SPI pin roles
Week 3: Communication modules → UART/USB differential pairs
Week 4: Complete system → Multi-protocol pin validation
```

### Assessment Integration

**Automated grading:**
```python
# Check if student's pin assignment meets requirements
def grade_pinmap(student_json):
    pinmap = load_json(student_json)
    score = 0
    
    # Check required connections
    if 'LED_PIN' in pinmap: score += 10
    if 'I2C_SDA' in pinmap and 'I2C_SCL' in pinmap: score += 20
    # ... additional checks
    
    return score
```

---

## Troubleshooting Scenarios

### Scenario 1: "MCU Reference Not Found"

**Problem:** ULP shows MCU reference 'U1' not found in schematic

**Solution:**
```
1. Click "Analyze" button to see what references exist
2. Check schematic for actual reference designators
3. Update ULP MCU Reference field to match (e.g., "IC1", "PROC1")
4. Ensure MCU component is connected to nets (not floating)
```

### Scenario 2: "No Files Generated"

**Problem:** ULP runs successfully but no output files appear

**Troubleshooting steps:**
```
1. Check actual Desktop location (not OneDrive Desktop)
2. Run with different output directory (e.g., C:/temp)
3. Check Windows permissions on output directory
4. Look for error messages in ULP dialog
5. Verify Python installation and PinmapGen CLI accessibility
```

### Scenario 3: "Generated Files Are Empty"

**Problem:** Files are created but contain no pin definitions

**Debugging:**
```
1. Check the generated CSV netlist in output directory
2. Verify schematic has connected components (not just placed)
3. Ensure nets have names (not anonymous)
4. Try with simpler test schematic first
```

### Scenario 4: "Python CLI Failed"

**Problem:** ULP reports CLI execution error

**Solutions:**
```
1. Verify Python installation: python --version
2. Check PinmapGen installation path in ULP source
3. Test CLI manually:
   python -m tools.pinmapgen.cli --help
4. Update hardcoded paths in ULP if needed
```

---

## Integration Examples

### MicroPython Project Integration

**Generated file:** `pinmap_micropython.py`

**Usage in code:**
```python
from pinmap_micropython import *

# Use generated pin definitions
led = Pin(LED_PIN, Pin.OUT)
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

# I2C with generated pins
i2c = I2C(0, scl=Pin(I2C_SCL), sda=Pin(I2C_SDA))
```

### Arduino Project Integration

**Generated file:** `pinmap_arduino.h`

**Usage in code:**
```cpp
#include "pinmap_arduino.h"

void setup() {
    // Use generated pin definitions
    pinMode(LED_PIN, OUTPUT);
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    
    // Initialize hardware with correct pins
    Wire.begin(I2C_SDA, I2C_SCL);
    Serial.begin(115200);
}
```

### PlatformIO Integration

**platformio.ini:**
```ini
[env:rp2040]
platform = raspberrypi
board = pico
framework = arduino
build_flags = -I firmware/include
```

**Code automatically finds:** `firmware/include/pinmap_arduino.h`

### Documentation Website Integration

**Use generated Markdown:**
```markdown
<!-- Include generated PINOUT.md in documentation -->
{{#include firmware/docs/PINOUT.md}}
```

**Use Mermaid diagrams:**
```markdown
<!-- Include generated diagrams -->
{{#include firmware/docs/pinout.mmd}}
```

### Version Control Workflows

**Git hooks integration:**
```bash
# Pre-commit hook regenerates pinmaps
#!/bin/sh
if [ -f hardware/exports/netlist.csv ]; then
    python -m tools.pinmapgen.cli --csv hardware/exports/netlist.csv --mcu rp2040 --mcu-ref U1 --out-root .
    git add firmware/ pinmaps/
fi
```

---

## Best Practices

### Naming Conventions

**Project names:**
- Use descriptive names: "SensorBoard_v2.1" not "Test"
- Include version info: "ProductionBoard_2025Q1"
- Avoid spaces: Use underscores or hyphens

**MCU references:**
- Standardize across team: Always use "U1" for main MCU
- Document conventions in team guidelines
- Be consistent with reference designator numbering

### Output Management

**Directory structure:**
```
project/
├── hardware/
│   └── exports/
│       └── netlist.csv
├── firmware/
│   ├── include/
│   │   └── pinmap_arduino.h
│   ├── micropython/
│   │   └── pinmap_micropython.py
│   └── docs/
│       ├── PINOUT.md
│       └── pinout.mmd
└── pinmaps/
    └── pinmap.json
```

### Quality Assurance

**Validation checklist:**
- [ ] All required pins are defined
- [ ] No duplicate pin assignments
- [ ] Differential pairs are correctly identified
- [ ] I2C/SPI/UART pins follow MCU constraints
- [ ] Power pins are excluded from GPIO lists
- [ ] Documentation matches implementation

---

This usage guide covers comprehensive workflows from basic one-click generation to advanced team integration scenarios. For additional help, refer to the main documentation and troubleshooting guides.