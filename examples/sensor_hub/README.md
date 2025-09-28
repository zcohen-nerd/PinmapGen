# Sensor Hub Example

This example demonstrates PinmapGen usage with multiple sensors connected to an RP2040 microcontroller. This represents a typical IoT sensor hub project with:

- **Temperature/Humidity Sensor** (DHT22)
- **Accelerometer** (MPU6050 via I2C)
- **Light Sensor** (analog input)
- **Status LED** (digital output)
- **Button Input** (with pullup)

## Hardware Setup
- RP2040 microcontroller (U1)
- DHT22 temperature sensor (U2)
- MPU6050 accelerometer (U3)
- LDR photoresistor (R1)
- Status LED (D1)
- Push button (SW1)

## Connections
- **GPIO2**: DHT22 data line
- **GPIO4/GPIO5**: I2C (SDA/SCL) for MPU6050
- **GPIO26**: Analog input for light sensor
- **GPIO15**: Status LED output
- **GPIO14**: Button input (with internal pullup)

## Generated Files
After running PinmapGen, you'll get:
- `firmware/micropython/pinmap_micropython.py` - MicroPython pin definitions
- `firmware/include/pinmap_arduino.h` - Arduino/C++ header
- `firmware/docs/PINOUT.md` - Documentation
- `pinmaps/pinmap.json` - JSON pin mapping

## Usage
```bash
python -m tools.pinmapgen.cli --csv netlist.csv --mcu rp2040 --mcu-ref U1 --out-root generated --mermaid
```

This example shows how PinmapGen handles:
- Mixed I/O types (analog, digital, I2C)
- Component references and net names
- Real-world sensor integration patterns