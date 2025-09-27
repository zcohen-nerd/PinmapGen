# PinmapGen Fusion 360 Add-in

This directory contains the Fusion 360 add-in for PinmapGen - a one-click solution for generating firmware pinmaps from Electronics workspace designs.

## 🎯 Design Goals

**For Non-Programmers (PCB Designers):**
- Simple, intuitive interface with clear labels
- One-click operation with smart defaults
- Comprehensive error messages in plain English
- Visual feedback and progress indicators
- No technical jargon or command-line knowledge required

**For Programmers (Handoff):**
- Multiple output formats (MicroPython, Arduino, JSON, Docs)
- Direct VS Code integration
- Organized project structure
- Validation reports with actionable warnings

## 📁 Structure

```
fusion_addin/
├── PinmapGen.py              # Main add-in entry point
├── PinmapGen.manifest        # Add-in metadata and configuration  
├── commands/
│   ├── GeneratePinmapCommand.py    # Main generation command
│   └── SettingsCommand.py          # Settings and preferences
├── ui/
│   ├── PinmapGenPanel.py     # Main UI panel
│   ├── resources/            # Icons, images, layouts
│   └── dialogs/             # Progress, error, and result dialogs
├── core/
│   ├── fusion_exporter.py    # Extract data from Fusion design
│   ├── pinmap_generator.py   # Interface to PinmapGen toolchain
│   └── project_creator.py    # Generate organized output structure
└── utils/
    ├── error_handler.py      # User-friendly error reporting
    ├── validation.py         # Design validation helpers
    └── logger.py            # Logging for debugging
```

## 🚀 User Experience Flow

1. **Open Electronics Workspace** - User has their PCB design ready
2. **Click PinmapGen Button** - Simple toolbar button or ADD-INS menu
3. **Quick Configuration Dialog:**
   - MCU Type: Dropdown (RP2040, STM32G0, ESP32)
   - MCU Reference: Auto-detected or manual entry (U1, U2, etc.)
   - Output Formats: Checkboxes (MicroPython ✓, Arduino ✓, Docs ✓)
   - Output Location: Browse button with smart default
4. **One-Click Generate** - Progress bar with clear status messages
5. **Results Dialog:**
   - Success summary with file locations
   - Validation warnings in plain English
   - "Open in VS Code" button for programmer handoff
   - "View Files" button to see generated outputs

## 🔧 Technical Requirements

- **Fusion 360 API**: Electronics workspace integration
- **Python 3.x**: Compatible with Fusion's Python environment
- **Error Recovery**: Graceful handling of design issues
- **Cross-Platform**: Windows/Mac support
- **No Dependencies**: Bundle PinmapGen toolchain locally

## 🎨 UI Design Principles

- **Minimal Clicks**: Default to most common options
- **Progressive Disclosure**: Advanced options hidden initially
- **Clear Feedback**: Every action has visible response
- **Undo/Retry**: Easy recovery from errors
- **Help Integration**: Contextual help and tooltips