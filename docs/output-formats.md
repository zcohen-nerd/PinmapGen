# Output Formats

Reference for every file PinmapGen generates.

---

## JSON

**File:** `pinmaps/pinmap.json`

The canonical machine-readable representation. All other formats are derived
from this structure.

### Structure

```json
{
  "mcu": "rp2040",
  "pins": {
    "LED_STATUS": ["GP15"],
    "I2C_SDA": ["GP4"],
    "I2C_SCL": ["GP5"],
    "USB_DP": ["GP24"],
    "USB_DM": ["GP25"]
  },
  "differential_pairs": [
    { "positive": "USB_DP", "negative": "USB_DM" }
  ],
  "metadata": {
    "total_nets": 5,
    "total_pins": 5,
    "differential_pairs_count": 1,
    "special_pins_used": ["GP24", "GP25"],
    "validation_warnings": [],
    "validation_errors": []
  }
}
```

### Usage

```python
import json

with open("pinmaps/pinmap.json") as f:
    pinmap = json.load(f)

for net, pins in pinmap["pins"].items():
    print(f"{net}: {pins}")
```

---

## MicroPython

**File:** `firmware/micropython/pinmap_micropython.py`

Importable Python module with pin constants and optional helpers.

### Structure

```python
# Pin mapping constants for MicroPython
# Generated from: hardware/exports/sample_netlist.csv
# MCU: RP2040 (Reference: U1)
#
# AUTOMATICALLY GENERATED - DO NOT EDIT MANUALLY

LED_STATUS = 15      # GP15
I2C_SDA = 4          # GP4
I2C_SCL = 5          # GP5
USB_DP = 24          # GP24
USB_DM = 25          # GP25
```

RP2040 pins use bare integers (`GP15` → `15`). STM32 and ESP32 pins use quoted
strings (`"PA0"`, `"GPIO4"`).

### Usage

```python
from machine import Pin, I2C
from pinmap_micropython import *

led = Pin(LED_STATUS, Pin.OUT)
button = Pin(BUTTON_INPUT, Pin.IN, Pin.PULL_UP)
i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL))
```

---

## Arduino

**File:** `firmware/include/pinmap_arduino.h`

C/C++ header with `#define` constants.

### Structure

```c
/**
 * Pin mapping constants for Arduino/C++
 * Generated from: hardware/exports/sample_netlist.csv
 * MCU: RP2040 (Reference: U1)
 *
 * AUTOMATICALLY GENERATED - DO NOT EDIT MANUALLY
 */

#ifndef PINMAP_ARDUINO_H
#define PINMAP_ARDUINO_H

#define LED_STATUS     15
#define I2C_SDA        4
#define I2C_SCL        5
#define USB_DP         24
#define USB_DM         25

#endif // PINMAP_ARDUINO_H
```

### Usage

```cpp
#include "pinmap_arduino.h"

void setup() {
    pinMode(LED_STATUS, OUTPUT);
    pinMode(BUTTON_INPUT, INPUT_PULLUP);
    Wire.begin(I2C_SDA, I2C_SCL);
}
```

### PlatformIO

Add the include path in `platformio.ini`:

```ini
[env:rp2040]
platform = raspberrypi
board = pico
framework = arduino
build_flags = -I firmware/include
```

### Compile-time validation

```cpp
// Optional guard in your own code
#if !defined(LED_STATUS) || !defined(BUTTON_INPUT)
#error "Required pins not defined in pinmap_arduino.h"
#endif
```

---

## Markdown

**File:** `firmware/docs/PINOUT.md`

Human-readable pinout documentation with tables, role annotations, and
validation results.

### Contents

- Pin summary table (net name, physical pin, logical pin, role, capabilities)
- Per-pin detail sections
- Communication interface summaries (I2C, SPI, UART)
- Differential pair listings
- Validation warnings and errors
- MCU capability summary
- Code examples for MicroPython and Arduino

Useful for design reviews, lab handouts, and project documentation.

---

## Mermaid

**File:** `firmware/docs/pinout.mmd`

Generated only when `--mermaid` is passed to the CLI.

### Structure

A `graph TB` diagram with nodes for each net, grouped by function, and styled
by direction (input, output, bidirectional, USB).

### Viewing

- GitHub and GitLab render `.mmd` files inline.
- VS Code with the Mermaid extension previews diagrams.
- Embed in HTML:
  ```html
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <div class="mermaid">
    <!-- paste pinout.mmd content here -->
  </div>
  ```

---

## Format comparison

| Aspect | JSON | MicroPython | Arduino | Markdown | Mermaid |
|--------|------|-------------|---------|----------|---------|
| Machine-readable | Yes | Partial | Partial | No | No |
| Human-readable | No | Good | Good | Excellent | Visual |
| Code integration | High | High | High | Low | Low |
| Documentation | Low | Medium | Medium | High | High |

All formats are generated from the same canonical dict, so they are always
consistent with each other.

---

## Customization

### Adding a company header

Modify the relevant `emit_*.py` module to prepend your copyright notice.

### Changing naming conventions

Update the identifier-generation logic in the emitter (look for
`_sanitize_net_name()` patterns).

### Creating a new format

See [extending.md](extending.md) for emitter implementation patterns.
