I l# Fusion 360 ULP User Guide

This guide shows how to use the PinmapGen ULP (User Language Program) to generate firmware pinmaps directly from Fusion 360 Electronics workspace.

## What is a ULP?

A ULP (User Language Program) is a powerful automation script that runs directly inside Fusion 360 Electronics. Unlike add-ins, ULPs:
- Work in Electronics workspace without special permissions
- Don't require installation through app stores
- Have full access to schematic data and netlist export
- Run with a simple copy-and-execute workflow

## Installation

### 1. Copy the ULP file

Copy `Working.ulp` to your Fusion 360 ULPs directory:

**Windows:**
```cmd
copy "Working.ulp" "%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\"
```

**Alternative method:**
1. Navigate to `%APPDATA%\Autodesk\Autodesk Fusion 360\API\ULPs\`
2. Copy the `Working.ulp` file into this directory

### 2. Restart Fusion 360

Close and reopen Fusion 360 for the ULP to be recognized.

## Usage

### 1. Open Electronics Workspace

Make sure you're in the **Electronics** workspace with your schematic open.

### 2. Run the ULP

Navigate to: **Automation → Run ULP → Working**

### 3. Configure Settings

The ULP dialog provides several configuration options:

#### MCU Reference Designator
- Enter the reference designator of your MCU (e.g., "U1", "IC1")
- This should match what you used in your schematic

#### Project Name
- Give your project a descriptive name
- This will be used in file organization and output folder names
- Defaults to timestamped name if left blank

#### Output Directory
- Specify where to save the generated files
- Use the quick buttons for common locations:
  - **Desktop** - Creates folder on your Desktop
  - **Documents** - Creates folder in Documents
  - **Project Root** - Creates folder in PinmapGen project directory

#### Custom Path
- Edit the output directory path directly for custom locations
- Use forward slashes (/) or double backslashes (\\\\) in paths

### 4. Generate Pinmaps

Click **Generate Pinmaps** to:
1. Export the netlist from your schematic
2. Run PinmapGen CLI with proper parameters
3. Generate all output formats
4. Open File Explorer to show results

## Generated Output

The ULP creates an organized folder structure:

```
YourProject/
├── pinmaps/
│   └── pinmap.json                    # Machine-readable pinmap data
├── firmware/
│   ├── micropython/
│   │   └── pinmap_micropython.py      # MicroPython pin definitions
│   ├── include/
│   │   └── pinmap_arduino.h           # Arduino/C++ header file
│   └── docs/
│       ├── PINOUT.md                  # Human-readable documentation
│       └── pinout.mmd                 # Mermaid diagram source
└── temp/                              # Temporary files (auto-cleaned)
```

### File Descriptions

- **pinmap.json**: Complete pin mapping data with metadata, validation warnings, and bus groupings
- **pinmap_micropython.py**: Python module for MicroPython/CircuitPython projects
- **pinmap_arduino.h**: C++ header for Arduino IDE or PlatformIO projects  
- **PINOUT.md**: Markdown documentation with tables and descriptions
- **pinout.mmd**: Mermaid diagram source for visual pin mapping diagrams

## Features

### Automatic Role Detection
The ULP automatically detects pin roles based on net names:
- I2C signals (SDA, SCL)
- SPI signals (MOSI, MISO, SCK, CS)
- PWM outputs
- GPIO inputs/outputs
- USB differential pairs
- Analog inputs

### MCU-Specific Validation
- Warns about special pins (boot, strapping, input-only)
- Detects differential pairs (USB D+/D-)
- Validates pin assignments against MCU capabilities
- Suggests alternative pins for problematic assignments

### Bus Grouping
Related signals are automatically grouped:
- Communication buses (I2C, SPI, UART)
- Control groups (buttons, LEDs, sensors)
- Power and ground connections

## Research: Automatic Netlist Generation

I've created two research ULPs to investigate if we can bypass the manual export process entirely:

### 1. Schematic Access Test (`ulp_schematic_access_test.ulp`)
Tests what schematic data is accessible through the ULP object model:
- Lists nets, segments, and pinrefs
- Shows parts and pin information
- Helps understand available data structures

### 2. Direct Netlist Generator (`direct_netlist_generator.ulp`)
Attempts to generate CSV netlist directly from schematic objects:
- Scans all parts and pins on all sheets
- Extracts net connections without EXPORT NETLIST
- Generates CSV compatible with PinmapGen
- **This could eliminate the manual export step entirely!**

To test these ULPs:
1. Open your schematic in Fusion Electronics
2. Go to Automation → Run ULP
3. Select either test ULP
4. Report results - this will determine if we can automate the entire process!

## Troubleshooting

### ULP Not Found
- Verify `Working.ulp` is in the correct ULPs directory
- Restart Fusion 360 after copying the file
- Check that you're in Electronics workspace, not Design workspace

### Export Failed
- Ensure your schematic has nets connected to the MCU
- Verify the MCU reference designator exists in your schematic
- Check that output directory path is valid and writable

### Python/CLI Errors
- Ensure Python 3.11+ is installed and in PATH
- Verify PinmapGen project is in the expected location
- Check that all required Python modules are available

### Permission Errors
- Try running Fusion 360 as administrator
- Choose a different output directory (Desktop instead of system folders)
- Ensure the output directory isn't read-only

### File Not Generated
- Check the verbose output in the ULP dialog for error messages
- Verify your schematic has the correct MCU reference designator
- Ensure nets are properly named and connected

## Advanced Usage

### Custom MCU Profiles
The ULP currently supports RP2040, but the underlying PinmapGen CLI supports:
- RP2040 (Raspberry Pi Pico)
- STM32G0 series
- ESP32 modules

To use different MCUs, modify the ULP script or use the CLI directly.

### Integration with Version Control
Generated files can be committed to version control for:
- Firmware team collaboration
- Pin assignment history tracking
- Automated build integration
- Documentation generation

### Batch Processing
For multiple projects:
1. Use the CLI with watch mode: `python -m tools.pinmapgen.watch`
2. Set up VS Code tasks for repeated generation
3. Create shell scripts for standardized workflows

## Best Practices

### Schematic Naming
- Use descriptive net names that indicate function
- Follow consistent naming conventions (I2C_SDA, BUTTON_1, LED_STATUS)
- Avoid generic names like NET_1, N$123

### Project Organization  
- Use meaningful project names
- Organize output folders by project and version
- Keep generated files with source schematics

### Team Workflow
1. Designer creates/updates schematic in Fusion Electronics
2. Designer runs ULP to generate current pinmaps
3. Designer shares output folder with firmware team
4. Firmware team integrates generated headers/modules
5. Iterate as needed with pin assignment changes

## Support

For issues specific to the ULP:
- Check this guide first
- Verify ULP installation steps
- Test with a simple schematic

For issues with pin mapping or MCU profiles:
- See main PinmapGen documentation
- Use CLI directly for debugging
- Check generated JSON for validation warnings

## Version History

- **v1.0**: Initial ULP implementation with full PinmapGen integration
- Working directly in Electronics workspace
- Support for custom output directories
- Automatic file organization and cleanup