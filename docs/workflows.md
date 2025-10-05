# Workflow Guide

Detailed workflows for common PinmapGen usage patterns across different team structures and project phases.

---

## Solo developer workflows

### Rapid prototyping workflow

**Use case:** Testing pin assignments quickly during breadboard development.

**Tools needed:**
- Text editor or spreadsheet software
- PinmapGen CLI
- File watcher (optional)

**Steps:**
1. **Create minimal CSV:**
```csv
Part Name,Designator,Pin,Net Name
RP2040,U1,20,GP15
RP2040,U1,21,GP16
RP2040,U1,25,GP19
LED,D1,1,LED_DATA
LED,D1,2,GND
Button,SW1,1,BUTTON_INPUT
Button,SW1,2,GND
```

2. **Enable file watching:**
```bash
cd /path/to/project
python -m tools.pinmapgen.watch hardware/exports/ --interval 0.5
```

3. **Edit and test cycle:**
   - Edit CSV file in spreadsheet or text editor
   - Save changes
   - PinmapGen automatically regenerates outputs
   - Copy constants to MicroPython/Arduino code
   - Test on hardware
   - Repeat

**Pro tips:**
- Use semantic net names from the start (`LED_DATA` not `NET1`)
- Start with fewer pins and add more as the design grows
- Keep a backup of working CSV files before major changes

### Migration from hardcoded pins

**Use case:** Converting existing firmware from hardcoded pin numbers to PinmapGen.

**Before:**
```python
# Old hardcoded approach
LED_PIN = 15
BUTTON_PIN = 16
I2C_SDA = 4
I2C_SCL = 5
```

**Migration steps:**
1. **Catalog current pin usage:**
```bash
# Find all hardcoded pin references
grep -n "Pin.*=" src/*.py
grep -n "GPIO[0-9]" src/*.py
```

2. **Create CSV from current assignments:**
```csv
Part Name,Designator,Pin,Net Name
RP2040,U1,20,GP15,LED_DATA
RP2040,U1,21,GP16,BUTTON_INPUT
RP2040,U1,6,GP4,I2C_SDA
RP2040,U1,7,GP5,I2C_SCL
```

3. **Generate PinmapGen constants:**
```bash
python -m tools.pinmapgen.cli --csv current_pins.csv --mcu rp2040 --mcu-ref U1 --out-root .
```

4. **Replace hardcoded values:**
```python
# New PinmapGen approach
from pinmap_micropython import *

# Now pin changes only require CSV update
led = Pin(LED_DATA, Pin.OUT)
button = Pin(BUTTON_INPUT, Pin.IN, Pin.PULL_UP)
i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL))
```

---

## Team development workflows

### Hardware-firmware collaboration

**Team structure:**
- **Hardware engineer:** Designs PCB, exports netlists
- **Firmware developers:** Write MicroPython/Arduino code
- **Systems integrator:** Validates complete system

**Workflow:**

**Phase 1: Initial pin assignment**
1. Hardware engineer creates schematic with semantic net names
2. Exports CSV netlist from CAD tool
3. Runs PinmapGen to generate initial constants
4. Commits CSV + generated files to shared repository

**Phase 2: Firmware development**  
1. Firmware developers pull latest pin assignments
2. Use generated constants in code development
3. Provide feedback on pin requirements (ADC needed, PWM capability, etc.)
4. Hardware engineer adjusts assignments and re-exports

**Phase 3: Iteration and testing**
1. Hardware changes trigger automatic PinmapGen regeneration via CI/CD
2. Firmware developers get notifications of pin changes via pull requests
3. Testing reveals integration issues, pin assignments refined
4. Process repeats until system works correctly

**Communication protocol:**
```
# Git commit messages for pin changes
hardware: Move I2C to GP4/GP5 for easier routing
firmware: Add LED brightness control (needs PWM pin)
integration: USB pins conflict with debug signals
```

### Multi-board product family

**Challenge:** Maintaining firmware compatibility across hardware variants.

**Strategy: Variant-specific configurations**

**Directory structure:**
```
products/
├── common/
│   └── src/              # Shared firmware code
├── board_a/
│   ├── hardware/exports/sample_netlist.csv
│   └── pinmaps/         # Generated A-specific constants
├── board_b/
│   ├── hardware/exports/sample_netlist.csv  
│   └── pinmaps/         # Generated B-specific constants
└── build/
    ├── board_a_firmware.uf2
    └── board_b_firmware.uf2
```

**Build system integration:**
```bash
# Makefile example
BOARD ?= board_a

build: generate_pinmap compile_firmware

generate_pinmap:
	cd $(BOARD) && python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root .

compile_firmware:
	# Include board-specific pin definitions
	gcc -I$(BOARD)/firmware/include -DBOARD=$(BOARD) common/src/*.c -o build/$(BOARD)_firmware.uf2
```

**Firmware abstraction:**
```c
// common/src/hardware_abstraction.c
#ifdef BOARD_A
#include "board_a/pinmap_arduino.h"
#elif BOARD_B  
#include "board_b/pinmap_arduino.h"
#endif

void init_leds() {
    pinMode(LED_STATUS, OUTPUT);  // Pin number varies by board
    pinMode(LED_ERROR, OUTPUT);   // But functionality is consistent
}
```

### Code review and validation

**Review checklist for pin changes:**

**Hardware reviewer:**
- [ ] Semantic net names used (not GP0, GPIO1, etc.)
- [ ] Differential pairs correctly identified and routed
- [ ] Power and ground nets excluded from GPIO assignments
- [ ] Pin capabilities match signal requirements (ADC, PWM, etc.)

**Firmware reviewer:**
- [ ] Generated constants compile without errors
- [ ] Pin changes don't break existing driver code
- [ ] New pin assignments tested on actual hardware
- [ ] Backward compatibility considered for field updates

**CI/CD validation:**
```yaml
# .github/workflows/validate_pins.yml
- name: Validate pin assignments
  run: |
    # Regenerate and check for drift
    python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root temp/
    diff -u firmware/micropython/pinmap_micropython.py temp/firmware/micropython/pinmap_micropython.py
    
    # Compile test with generated constants
    cd firmware && python -m py_compile pinmap_micropython.py
```

---

## Educational workflows

### Classroom lab setup

**Scenario:** Teaching embedded systems with 20-30 students using RP2040 boards.

**Instructor preparation:**
1. **Create starter templates:**
```bash
# templates/basic_iot.csv - Common IoT sensors
Part Name,Designator,Pin,Net Name
RP2040,U1,31,GP26,TEMP_SENSOR
RP2040,U1,32,GP27,LIGHT_SENSOR  
RP2040,U1,20,GP15,LED_STATUS
RP2040,U1,6,GP4,I2C_SDA
RP2040,U1,7,GP5,I2C_SCL
```

2. **Set up shared workspace:**
```bash
# Lab computers setup script
git clone <course_repo>
cd embedded_systems_lab
pip install -e .

# Pre-configure VS Code with PinmapGen tasks
code --install-extension ms-python.python
```

**Student workflow:**
1. **Choose project template:** Select from basic_iot.csv, motor_control.csv, sensor_array.csv
2. **Modify pin assignments:** Add/remove components based on their project
3. **Generate code constants:** Use VS Code task or command line
4. **Write and test firmware:** Immediate feedback from generated constants
5. **Document design decisions:** Generated Markdown provides starting point

**Assessment rubric:**
- **Pin planning (25%):** Appropriate pin choices for component types
- **Documentation (25%):** Generated pinout documentation completeness  
- **Code quality (25%):** Proper use of generated constants vs hardcoding
- **Validation (25%):** Firmware works correctly with generated pin assignments

### Student project progression

**Week 1-2: Basic GPIO**
```csv
# Students start simple
Part Name,Designator,Pin,Net Name
RP2040,U1,20,GP15,LED_RED
RP2040,U1,21,GP16,LED_GREEN  
RP2040,U1,22,GP17,BUTTON_A
```

**Week 3-4: ADC and sensors**
```csv
# Add analog inputs
RP2040,U1,31,GP26,POTENTIOMETER
RP2040,U1,32,GP27,TEMP_SENSOR
RP2040,U1,34,GP28,FORCE_SENSOR
```

**Week 5-6: Communication protocols**
```csv
# Add I2C, SPI
RP2040,U1,6,GP4,I2C_SDA
RP2040,U1,7,GP5,I2C_SCL
RP2040,U1,16,GP12,SPI_MISO
RP2040,U1,17,GP13,SPI_CS
```

**Week 7-8: Complex projects**
- Students design their own pin assignments
- Multiple communication protocols
- PinmapGen validation catches common mistakes
- Generated documentation helps in project presentations

### Troubleshooting common student issues

**Issue:** "My LED won't turn on"
```bash
# Check generated constants
grep "LED" firmware/micropython/pinmap_micropython.py
# Verify pin assignment in CSV
grep "LED" hardware/exports/sample_netlist.csv
# Test with known-good pin
```

**Issue:** "I2C device not detected"
```python
# Validate pin capabilities
from machine import Pin, I2C
from pinmap_micropython import I2C_SDA, I2C_SCL

# Check if pins support I2C
print(f"SDA pin: {I2C_SDA}")  # Should be GP4, GP6, GP10, etc.
print(f"SCL pin: {I2C_SCL}")  # Should be GP5, GP7, GP11, etc.
```

**Issue:** "ADC readings are wrong"
- Check if pin is ADC-capable (GP26-GP28 on RP2040)
- Verify voltage range (0-3.3V)
- PinmapGen warnings highlight non-ADC pins used for analog inputs

---

## Production workflows

### Manufacturing and testing

**Challenge:** Ensuring firmware matches manufactured hardware exactly.

**Solution: Traceable pin assignments**

**Manufacturing data package:**
1. **Gerber files** with drill data  
2. **CSV netlist** from final schematic
3. **Generated pinmap files** with version tags
4. **Test firmware** using generated constants

**Version control strategy:**
```bash
# Tag releases with hardware and firmware versions
git tag -a v1.2-hw_rev_c -m "Production release for hardware revision C"

# Manufacturing uses exact tagged versions
git checkout v1.2-hw_rev_c
python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root .
```

**Factory test integration:**
```python
# test_fixture.py - Uses generated constants
from pinmap_micropython import *

def test_all_pins():
    """Validate all pin assignments match hardware"""
    test_results = {}
    
    # Test digital outputs
    for pin_name, pin_num in [("LED_STATUS", LED_STATUS), ("LED_ERROR", LED_ERROR)]:
        gpio = Pin(pin_num, Pin.OUT)
        gpio.on()
        test_results[pin_name] = measure_voltage(pin_num) > 2.5
    
    # Test analog inputs  
    adc = ADC(Pin(TEMP_SENSOR))
    test_results["TEMP_SENSOR"] = 100 < adc.read_u16() < 60000
    
    return test_results
```

### Field service and diagnostics

**Use case:** Supporting deployed hardware with multiple revisions in the field.

**Diagnostic strategy:**
```python
# diagnostic_tool.py
import json
from pinmap_micropython import *

def hardware_report():
    """Generate hardware configuration report for field service"""
    
    # Load pin mapping metadata
    with open('pinmaps/pinmap.json', 'r') as f:
        pinmap = json.load(f)
    
    metadata = pinmap.get("metadata", {})
    report = {
        "mcu": pinmap.get("mcu", "unknown"),
        "pin_count": len(pinmap.get("pins", {})),
        "differential_pairs": metadata.get("differential_pairs_count", 0),
        "warnings": metadata.get("validation_warnings", []),
    }
    
    # Test critical functions
    try:
        i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL))
        devices = i2c.scan()
        report["i2c_devices"] = [hex(addr) for addr in devices]
    except Exception as e:
        report["i2c_error"] = str(e)
    
    return report

# Field technician runs this to identify board revision
print(json.dumps(hardware_report(), indent=2))
```

**Remote update workflow:**
1. **Identify board revision** using diagnostic script
2. **Download appropriate firmware** based on pin mapping version
3. **Validate compatibility** before flashing
4. **Verify operation** using generated test sequences

### Compliance and documentation

**Regulatory documentation:**
- Generated pinout documentation provides traceability for safety certifications
- Mermaid diagrams visualize signal routing for EMC compliance
- JSON metadata enables automated compliance checking tools

**Change control:**
```bash
# Document all pin changes for change control boards
git log --oneline --grep="hardware:" --since="2024-01-01" > pin_change_log.txt

# Generate compliance report
python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root . --mermaid
# Submit generated docs/PINOUT.md and pinout.mmd with regulatory submissions
```

---

## Advanced automation

### CI/CD integration patterns

**Full automation pipeline:**
```yaml
# .github/workflows/hardware_integration.yml
name: Hardware Integration
on:
  push:
    paths: ['hardware/exports/**']
    
jobs:
  validate_and_deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Generate pin mappings
      run: |
        python -m tools.pinmapgen.cli \
          --csv hardware/exports/sample_netlist.csv \
          --mcu rp2040 --mcu-ref U1 \
          --out-root . --mermaid
    
    - name: Validate firmware compatibility
      run: |
        cd firmware
        python -c "import pinmap_micropython; print('Import OK')"
        # Test compile Arduino code
        arduino-cli compile --fqbn rp2040:rp2040:rpipico .
    
    - name: Update documentation site
      run: |
        cp firmware/docs/PINOUT.md docs/site/hardware/
        cp firmware/docs/pinout.mmd docs/site/diagrams/
    
    - name: Deploy firmware builds
      run: |
        # Build and upload firmware artifacts
        make all BOARD=production
        # Upload to artifact storage or deployment system
```

**Slack/Teams integration:**
```python
# hooks/pin_change_notifier.py
import json
import requests
import subprocess

def notify_pin_changes():
    """Send notifications when pin assignments change"""
    
    # Check for pinmap changes in last commit  
    result = subprocess.run(['git', 'diff', 'HEAD~1', '--name-only'], 
                          capture_output=True, text=True)
    
    if 'pinmaps/' in result.stdout or 'firmware/' in result.stdout:
        # Load current pinmap for details
        with open('pinmaps/pinmap.json', 'r') as f:
            pinmap = json.load(f)
        
        message = {
            "text": f"🔧 Pin assignments updated for {pinmap['mcu']['type']}",
            "blocks": [
                {
                    "type": "section", 
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Hardware changes detected. Firmware team please review:\n• MCU: {pinmap['mcu']['type']}\n• Pins updated: {len(pinmap['pins'])}\n• <{os.environ['GITHUB_SERVER_URL']}/{os.environ['GITHUB_REPOSITORY']}/commit/{os.environ['GITHUB_SHA']}|View changes>"
                    }
                }
            ]
        }
        
        requests.post(os.environ['SLACK_WEBHOOK_URL'], json=message)

if __name__ == "__main__":
    notify_pin_changes()
```

**Multi-repository sync:**
```bash
# sync_hardware_changes.sh
#!/bin/bash

# When hardware repo updates, sync pinmaps to firmware repos
HARDWARE_REPO="company/product-hardware"  
FIRMWARE_REPOS=("company/product-firmware" "company/product-bootloader")

for repo in "${FIRMWARE_REPOS[@]}"; do
    echo "Syncing pin changes to $repo"
    
    # Clone or update firmware repo
    if [ -d "$repo" ]; then
        cd "$repo" && git pull
    else
        git clone "https://github.com/$repo.git"
        cd "$repo"
    fi
    
    # Copy generated pinmaps
    cp ../pinmaps/* ./pinmaps/
    cp ../firmware/include/* ./include/
    cp ../firmware/micropython/* ./src/
    
    # Commit and push if changes detected
    if ! git diff --quiet; then
        git add .
        git commit -m "Sync pin assignments from hardware@$(git -C .. rev-parse --short HEAD)"
        git push
    fi
    
    cd ..
done
```

This comprehensive workflow guide covers the major usage patterns teams encounter when integrating PinmapGen into their development processes. Each workflow can be adapted based on specific organizational needs, tooling preferences, and project requirements.