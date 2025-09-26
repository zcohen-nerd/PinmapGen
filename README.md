# PinmapGen

A Python 3.11 toolchain that bridges Fusion Electronics (EAGLE) exports to firmware projects in VS Code. This tool treats nets in CAD as the source of truth and generates consistent pinmap definitions across multiple firmware platforms.

## Features

- **Multi-format Input**: Parse EAGLE `.sch` XML files or CSV exports
- **MCU Profiles**: Currently supports RP2040 with GPIO normalization
- **Multiple Output Formats**:
  - `pinmaps/pinmap.json` - Canonical pinmap data
  - `firmware/micropython/pinmap_micropython.py` - MicroPython constants
  - `firmware/include/pinmap_arduino.h` - Arduino C++ header
  - `firmware/docs/PINOUT.md` - Human-readable documentation
  - `firmware/docs/pinout.mmd` - Mermaid diagrams for visualization
- **Validation**: Detects duplicate pins, multi-pin nets, and differential pair issues
- **File Watching**: Automatic regeneration when source files change
- **VS Code Integration**: Tasks and code snippets for seamless workflow

## Quick Start

### Installation

```bash
# Clone and navigate to project
cd Fusion_PinMapGen

# Create virtual environment (optional but recommended)
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/macOS

# Install in development mode
pip install -e .
```

### Basic Usage

```bash
# Generate from CSV export
python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root .

# Generate from EAGLE schematic
python -m tools.pinmapgen.cli --sch hardware/exports/project.sch --mcu rp2040 --mcu-ref U1 --out-root . --mermaid

# Watch for changes and auto-regenerate
python -m tools.pinmapgen.watch hardware/exports/
```

### VS Code Integration

Use the built-in tasks:
- **Ctrl+Shift+P** → "Tasks: Run Task" → "Generate Pinmap"
- **Ctrl+Shift+P** → "Tasks: Run Task" → "Watch Pinmap"

Code snippets are available with prefixes:
- `pinmap-import` - Import PinmapGen modules
- `rp2040-pin` - Define RP2040 GPIO constants
- `mp-pin-setup` - MicroPython pin setup
- `arduino-pin-def` - Arduino pin definitions

## RP2040 Example

Given this sample netlist (`hardware/exports/sample_netlist.csv`):

```csv
Net,Pin,Component,RefDes
I2C0_SDA,GP0,RP2040,U1
I2C0_SCL,GP1,RP2040,U1
LED_DATA,GP4,RP2040,U1
BUTTON,GP5,RP2040,U1
USB_DP,GP24,RP2040,U1
USB_DN,GP25,RP2040,U1
QRD1114_A0,GP26,RP2040,U1
QRD1114_A1,GP27,RP2040,U1
```

PinmapGen generates:

**MicroPython** (`firmware/micropython/pinmap_micropython.py`):
```python
# Auto-generated pinmap for RP2040
I2C0_SDA = 0     # GP0
I2C0_SCL = 1     # GP1
LED_DATA = 4     # GP4
BUTTON = 5       # GP5
USB_DP = 24      # GP24
USB_DN = 25      # GP25
QRD1114_A0 = 26  # GP26 (ADC0)
QRD1114_A1 = 27  # GP27 (ADC1)
```

**Arduino** (`firmware/include/pinmap_arduino.h`):
```cpp
// Auto-generated pinmap for RP2040
#ifndef PINMAP_ARDUINO_H
#define PINMAP_ARDUINO_H

#define I2C0_SDA    0   // GP0
#define I2C0_SCL    1   // GP1
#define LED_DATA    4   // GP4
#define BUTTON      5   // GP5
#define USB_DP      24  // GP24
#define USB_DN      25  // GP25
#define QRD1114_A0  26  // GP26 (ADC0)
#define QRD1114_A1  27  // GP27 (ADC1)

#endif // PINMAP_ARDUINO_H
```

## Project Structure

```
Fusion_PinMapGen/
├── firmware/
│   ├── include/           # Generated Arduino headers
│   ├── micropython/       # Generated MicroPython modules
│   └── docs/             # Generated documentation
├── pinmaps/              # Canonical JSON pinmaps
├── tools/pinmapgen/      # Core toolchain modules
│   ├── cli.py           # Command-line interface
│   ├── bom_csv.py       # CSV parser
│   ├── eagle_sch.py     # EAGLE schematic parser
│   ├── normalize.py     # MCU-specific normalization
│   ├── emit_*.py        # Output format emitters
│   └── watch.py         # File watcher
├── hardware/exports/     # Source CAD exports
├── .vscode/             # VS Code tasks and snippets
├── pyproject.toml       # Python project configuration
└── README.md           # This file
```

## MCU Support

### RP2040
- **Pin Normalization**: `GPIOxx`/`IOxx` → `GPxx`
- **Differential Pairs**: Detects `_P`/`_N`, `DP`/`DM`, `CANH`/`CANL` patterns
- **Validation**: Duplicate pin usage, multi-pin nets, lonely differential pairs
- **Special Pins**: USB D+/D-, ADC channels, SPI/I2C functions

### Future MCUs (Roadmap)
- **STM32**: Port/pin notation, alternate functions
- **ESP32**: GPIO matrix, ADC/DAC channels
- **Custom**: User-defined MCU profiles

## Command Line Reference

```bash
python -m tools.pinmapgen.cli [OPTIONS]

Options:
  --sch PATH              EAGLE schematic file (.sch)
  --csv PATH              CSV netlist export  
  --mcu {rp2040}          MCU profile (required)
  --mcu-ref TEXT          MCU reference designator (e.g., U1)
  --out-root PATH         Output root directory (default: .)
  --mermaid              Generate Mermaid diagrams
  --help                 Show help message
```

## Development

PinmapGen uses Python 3.11+ with stdlib-only dependencies for maximum compatibility.

### Code Quality
```bash
# Format and lint (optional - requires ruff)
ruff format .
ruff check .
```

### Testing
```bash
# Run with sample data
python -m tools.pinmapgen.cli --csv hardware/exports/sample_netlist.csv --mcu rp2040 --mcu-ref U1 --out-root .
```

## Roadmap

### Phase 1 (Current)
- [x] Project scaffolding and structure
- [ ] CSV parser implementation
- [ ] RP2040 profile and normalization
- [ ] JSON/MicroPython/Arduino emitters
- [ ] Basic CLI functionality

### Phase 2
- [ ] EAGLE schematic parser
- [ ] File watcher implementation  
- [ ] Mermaid diagram generation
- [ ] Enhanced validation rules

### Phase 3
- [ ] STM32 MCU profile
- [ ] ESP32 MCU profile
- [ ] Plugin architecture for custom MCUs
- [ ] Web-based pinmap visualizer

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

**Note**: This is a development version. Core functionality is currently being implemented. See the `TODO` comments throughout the codebase for specific implementation tasks.