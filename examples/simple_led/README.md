# Simple LED Example

**Purpose:** Basic GPIO usage with LEDs and buttons on RP2040  
**Complexity:** Beginner  
**Components:** RP2040 microcontroller + LEDs + buttons + resistors

## Circuit Description

This example demonstrates a simple circuit with:
- 3 LEDs connected to GPIO pins (with current limiting resistors)
- 2 push buttons with pull-up resistors
- Power supply connections (VCC, GND)

**Use case:** Perfect for learning basic pin assignments and GPIO configuration.

## Component List

- **U1**: RP2040 microcontroller (reference designator)
- **LED1, LED2, LED3**: Status LEDs  
- **SW1, SW2**: Push buttons
- **R1-R6**: Resistors (current limiting and pull-up)

## Pin Assignments

| Net Name | Component | Pin | Function |
|----------|-----------|-----|----------|
| LED_RED | LED1 | Anode | Status LED (Red) |
| LED_GREEN | LED2 | Anode | Status LED (Green) |  
| LED_BLUE | LED3 | Anode | Status LED (Blue) |
| BUTTON_1 | SW1 | Pin 1 | User Button 1 |
| BUTTON_2 | SW2 | Pin 1 | User Button 2 |
| VCC | Multiple | Multiple | 3.3V Power |
| GND | Multiple | Multiple | Ground |

## Generated Files

After running PinmapGen, you'll get:

### MicroPython (`pinmap_micropython.py`)
```python
# Generated pin definitions for MicroPython
LED_RED = 2
LED_GREEN = 3  
LED_BLUE = 4
BUTTON_1 = 5
BUTTON_2 = 6

# Usage example
from machine import Pin
led_red = Pin(LED_RED, Pin.OUT)
button1 = Pin(BUTTON_1, Pin.IN, Pin.PULL_UP)
```

### Arduino (`pinmap_arduino.h`)
```cpp
// Generated pin definitions for Arduino
#define LED_RED 2
#define LED_GREEN 3
#define LED_BLUE 4  
#define BUTTON_1 5
#define BUTTON_2 6

// Usage example
void setup() {
    pinMode(LED_RED, OUTPUT);
    pinMode(BUTTON_1, INPUT_PULLUP);
}
```

## Testing This Example

### CLI Generation
```bash
python -m tools.pinmapgen.cli \
    --csv examples/simple_led/netlist.csv \
    --mcu rp2040 \
    --mcu-ref U1 \
    --out-root ./simple_led_output \
    --mermaid
```

### Expected Output Files
- `pinmap.json` - Machine-readable pin data
- `firmware/micropython/pinmap_micropython.py` - MicroPython definitions
- `firmware/include/pinmap_arduino.h` - Arduino headers
- `firmware/docs/PINOUT.md` - Documentation
- `firmware/docs/pinout.mmd` - Mermaid diagram

### Validation
Check that generated files contain definitions for all expected pins:
- LED_RED, LED_GREEN, LED_BLUE  
- BUTTON_1, BUTTON_2
- No conflicts or duplicate assignments

## Learning Objectives

After studying this example, you should understand:
1. How netlist CSV format represents connections
2. Basic GPIO pin assignment patterns  
3. Generated code structure for different platforms
4. How to integrate pin definitions into firmware projects

## Next Steps

Once comfortable with this example:
- Try the **sensor_hub** example for I2C/SPI communication
- Modify the netlist to add more LEDs or buttons
- Generate outputs for different MCU types (STM32G0, ESP32)