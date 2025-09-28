# Communication Module Example

This example demonstrates PinmapGen with multiple communication protocols on an RP2040. This represents a typical communication hub with:

- **WiFi Module** (ESP8266 via UART)
- **LoRa Radio** (RFM95W via SPI)
- **SD Card** (via SPI, shared bus)
- **Debug UART** (USB serial)
- **Status Indicators** (multiple LEDs)

## Hardware Setup
- RP2040 microcontroller (U1)
- ESP8266 WiFi module (U2)
- RFM95W LoRa radio (U3)
- SD Card socket (U4)
- Status LEDs (D1, D2, D3)

## Communication Protocols
- **UART0**: Debug/USB serial (GPIO0/GPIO1)
- **UART1**: ESP8266 communication (GPIO8/GPIO9)
- **SPI0**: Shared bus for LoRa and SD Card (GPIO16/GPIO18/GPIO19)
- **GPIO**: Chip selects and control signals

## Pin Assignments
- **GPIO0/GPIO1**: UART0 (USB debug)
- **GPIO8/GPIO9**: UART1 (ESP8266)
- **GPIO16**: SPI0 SCK (shared)
- **GPIO18**: SPI0 MISO (shared)  
- **GPIO19**: SPI0 MOSI (shared)
- **GPIO17**: LoRa chip select
- **GPIO20**: SD Card chip select
- **GPIO21**: LoRa reset
- **GPIO22**: LoRa DIO0 (interrupt)
- **GPIO10**: WiFi status LED
- **GPIO11**: LoRa status LED
- **GPIO12**: SD Card status LED

## Generated Files
PinmapGen will create organized firmware files for this complex multi-protocol setup, making it easy to manage all the communication interfaces.

## Usage
```bash
python -m tools.pinmapgen.cli --csv netlist.csv --mcu rp2040 --mcu-ref U1 --out-root generated --mermaid
```

This example demonstrates PinmapGen's ability to handle:
- Multiple communication protocols
- Shared SPI bus with chip selects
- Complex pin relationships
- Professional communication module organization