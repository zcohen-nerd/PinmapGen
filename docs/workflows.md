# Workflow Guide

Common PinmapGen usage patterns for solo developers, teams, classrooms, and
production environments.

---

## Solo developer workflows

### Rapid prototyping

1. Create a minimal CSV with your current pin assignments.
2. Optionally start the file watcher for automatic regeneration:
   ```bash
   python -m tools.pinmapgen.watch hardware/exports/ --interval 0.5
   ```
3. Edit the CSV, save, and the watcher regenerates outputs.
4. Copy constants into your MicroPython or Arduino code and test on hardware.

Tips:
- Use semantic net names from the start (`LED_DATA`, not `NET1`).
- Start with a handful of pins and add more as the design grows.
- Back up working CSVs before major changes.

### Migrating from hardcoded pins

Replace scattered magic numbers with generated constants:

**Before:**
```python
LED_PIN = 15
BUTTON_PIN = 16
I2C_SDA = 4
I2C_SCL = 5
```

**After:**
1. Catalog current pin usage (`grep -n "Pin.*=" src/*.py`).
2. Build a CSV that matches the current assignments.
3. Generate the pinmap.
4. Replace hardcoded values with imports:
   ```python
   from pinmap_micropython import *
   led = Pin(LED_DATA, Pin.OUT)
   i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL))
   ```

Now pin changes only require a CSV update and regeneration.

---

## Team development workflows

### Hardware–firmware collaboration

**Phase 1 — Initial pin assignment:**
1. Hardware engineer designs the schematic with semantic net names.
2. Exports CSV and runs PinmapGen.
3. Commits CSV + generated files to the shared repo.

**Phase 2 — Firmware development:**
1. Firmware developers pull the latest pin assignments.
2. Use generated constants in their code.
3. Feed back requirements (e.g., "need a PWM-capable pin for LED dimming").

**Phase 3 — Iteration:**
1. Hardware changes trigger regeneration (via CI or pre-commit hook).
2. Firmware developers get notified of pin changes through PRs.
3. Repeat until the system works.

### Multi-board product family

Maintain variant-specific configs:

```
products/
├── common/src/           # Shared firmware code
├── board_a/
│   ├── hardware/exports/sample_netlist.csv
│   └── pinmaps/          # Board A constants
├── board_b/
│   ├── hardware/exports/sample_netlist.csv
│   └── pinmaps/          # Board B constants
└── build/
```

Build system selects the right header:

```c
#ifdef BOARD_A
#include "board_a/pinmap_arduino.h"
#elif BOARD_B
#include "board_b/pinmap_arduino.h"
#endif
```

### Code review checklist

**Hardware reviewer:**
- [ ] Semantic net names (not `GP0`, `GPIO1`)
- [ ] Differential pairs correctly wired
- [ ] Power/ground excluded from GPIO assignments
- [ ] Pin capabilities match signal requirements

**Firmware reviewer:**
- [ ] Generated constants compile cleanly
- [ ] Pin changes don't break existing drivers
- [ ] New assignments tested on hardware
- [ ] Backward compatibility considered for field updates

**CI validation:**
```yaml
- name: Validate pins
  run: |
    python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root temp/
    diff -u firmware/micropython/pinmap_micropython.py temp/firmware/micropython/pinmap_micropython.py
```

---

## Educational workflows

### Classroom lab setup

**Instructor prep:**
1. Create template CSVs for each exercise (basic GPIO, ADC, I2C, etc.).
2. Set up a shared workspace with the watcher running.
3. Provide printed excerpts from `PINOUT.md` for wiring checks.

**Student workflow:**
1. Pick a template CSV and modify it for their project.
2. Run the CLI or save to the watched folder.
3. Use generated constants in their firmware.
4. Review validation warnings.

**Progressive exercises:**

| Weeks | Focus | New CSV content |
|-------|-------|-----------------|
| 1–2 | Basic GPIO | LEDs, buttons |
| 3–4 | ADC and sensors | Potentiometer, temperature sensor |
| 5–6 | Communication | I2C, SPI |
| 7–8 | Student projects | Custom designs |

### Common student issues

| Symptom | Check |
|---------|-------|
| LED won't turn on | `grep LED firmware/micropython/pinmap_micropython.py` — verify pin constant |
| I2C device not detected | Confirm pins are I2C-capable (`GP4`/`GP5` on RP2040) |
| ADC readings wrong | Pin must be ADC-capable (GP26–GP28 on RP2040); check voltage range |

---

## Production workflows

### Manufacturing and testing

Package for manufacturing:

1. Tag releases with hardware revision:
   ```bash
   git tag -a v1.2-hw_rev_c -m "Production release for hardware rev C"
   ```
2. Regenerate from the tagged CSV.
3. Use generated constants in factory test firmware:
   ```python
   from pinmap_micropython import *
   def test_all_pins():
       for name, num in [("LED_STATUS", LED_STATUS), ("LED_ERROR", LED_ERROR)]:
           gpio = Pin(num, Pin.OUT)
           gpio.on()
           results[name] = measure_voltage(num) > 2.5
   ```

### Field diagnostics

Load `pinmaps/pinmap.json` on the device for runtime introspection:

```python
import json
with open("pinmaps/pinmap.json") as f:
    pinmap = json.load(f)
print(f"MCU: {pinmap['mcu']}, pins: {len(pinmap['pins'])}")
```

### Compliance documentation

- Generated `PINOUT.md` provides traceability for safety certifications.
- Mermaid diagrams visualize signal routing for EMC review.
- `pinmap.json` metadata feeds automated compliance-checking tools.

---

## CI/CD integration

### GitHub Actions

```yaml
name: Hardware Integration
on:
  push:
    paths: ['hardware/exports/**']

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - run: pip install -e .
    - run: |
        python -m tools.pinmapgen.cli \
          --csv hardware/exports/sample_netlist.csv \
          --mcu rp2040 --mcu-ref U1 --out-root . --mermaid
    - run: git diff --exit-code pinmaps/ firmware/
```

### Pre-commit hook

See [.githooks/README.md](../.githooks/README.md) for installation. The hook
regenerates pinmaps when `hardware/exports/` files are staged and automatically
adds the updated outputs to the commit.
