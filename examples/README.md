# PinmapGen Examples

This directory contains comprehensive examples demonstrating PinmapGen's capabilities across different project types and complexity levels.

## Example Projects

### 1. Simple LED (`simple_led/`)
**Complexity**: Beginner | **Focus**: Basic GPIO usage with LEDs and buttons

A straightforward example perfect for learning PinmapGen basics. Shows simple digital outputs (LEDs), digital inputs (buttons), clean minimal netlist structure, and all generated output file types.

**Use Case**: Learning PinmapGen, simple blinky projects, educational workshops

### 2. Sensor Hub (`sensor_hub/`)
**Complexity**: Intermediate | **Focus**: Mixed I/O types and sensor integration

A typical IoT sensor project with temperature/humidity sensor (DHT22), I2C communication (MPU6050 accelerometer), analog input (light sensor), and mixed digital I/O (LED, button).

**Use Case**: IoT projects, environmental monitoring, sensor data collection

### 3. Communication Module (`communication_module/`)
**Complexity**: Advanced | **Focus**: Multiple communication protocols

A complex communication hub with multiple UART interfaces (debug, WiFi), shared SPI bus with chip selects (LoRa, SD Card), multiple status indicators, and professional protocol organization.

**Use Case**: Communication gateways, data loggers, wireless sensor networks

## Quick Start Examples

### Basic LED and Button (RP2040)
```bash
cd basic_usage/led_button_rp2040/
python -m tools.pinmapgen.cli --csv netlist.csv --mcu rp2040 --mcu-ref U1 --out-root .
```

### Multi-Sensor IoT Project (ESP32)  
```bash
cd basic_usage/iot_sensors_esp32/
python -m tools.pinmapgen.cli --csv sensors.csv --mcu esp32 --mcu-ref U1 --out-root . --mermaid
```

### Communication Interfaces (STM32G0)
```bash
cd basic_usage/comm_interfaces_stm32g0/
python -m tools.pinmapgen.cli --csv interfaces.csv --mcu stm32g0 --mcu-ref U1 --out-root .
```

## Integration Examples

### Flask Web Interface
```bash
cd integration/flask_web_ui/
pip install -r requirements.txt
python app.py
# Visit http://localhost:5000 to upload netlists via web interface
```

### GitHub Actions CI/CD
```bash
# Copy .github/workflows/ files to your project
# Automatic pinmap validation on netlist changes
```

### VS Code Extension
```bash
cd integration/vscode_extension/
npm install
code --install-extension .
# Use Ctrl+Shift+P > "PinmapGen: Generate from CSV"
```

## Custom Profile Examples

### Adding New MCU Support
```bash
cd custom_profiles/example_mcu/
# Study the implementation in mcu_profile.py
python test_profile.py  # Run profile tests
```

### Extending Validation Rules
```bash
cd custom_profiles/custom_validation/
# See custom_rules.py for project-specific validation
```

## Templates and Starters

### Educational Lab Setup
```bash
cd templates/educational_lab/
# Complete setup for classroom use with RP2040
```

### Production IoT Project
```bash
cd templates/production_iot/
# Multi-board template with CI/CD integration
```

### Fusion 360 Add-in Template
```bash
cd templates/fusion_addin/
# Template for creating Fusion 360 add-ins with PinmapGen
```

## Advanced Examples

### Multi-Board Product Family
```bash
cd advanced/multi_board_family/
# Manage pin assignments across hardware variants
```

### Enterprise Workflow
```bash
cd advanced/enterprise_workflow/
# Large team collaboration with automated validation
```

## Running Examples

Each example directory contains:
- `README.md` - Specific setup and usage instructions
- Sample input files (CSV netlists, schematics)
- Expected output files for reference
- Installation/dependency requirements
- Troubleshooting tips

To run any example:
1. Navigate to the example directory
2. Follow the README.md instructions
3. Install any additional dependencies
4. Run the provided commands
5. Compare outputs with expected results

## Contributing Examples

We welcome community contributions of new examples! See [CONTRIBUTING.md](../docs/CONTRIBUTING.md) for guidelines on:
- Adding new integration examples
- Creating educational templates
- Sharing real-world workflows
- Documenting best practices

Examples help demonstrate PinmapGen's capabilities and provide starting points for new users and use cases.