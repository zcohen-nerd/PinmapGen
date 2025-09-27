# 🚀 PinmapGen Fusion 360 Add-in User Guide

**One-click pinmap generation for non-programmers!**

This add-in allows PCB designers to generate firmware-ready pinmap files directly from Fusion 360 Electronics workspace, with zero programming knowledge required.

## 🎯 For PCB Designers (You!)

### What This Does
- **Analyzes your Electronics design** to find pin connections
- **Generates programmer-friendly files** in multiple formats
- **Validates your design** and warns about potential issues
- **Organizes everything** for easy handoff to software developers

### What You Get
- **MicroPython files** (.py) - For Raspberry Pi Pico projects
- **Arduino headers** (.h) - For Arduino-compatible boards
- **Documentation** (.md) - Human-readable pinout reference
- **JSON data** - For advanced programming tools
- **Diagrams** (.mmd) - Visual pinout representations (optional)

---

## 📋 Quick Start Guide

### 1. Install the Add-in

**Option A: Easy Install**
1. Download the `PinmapGen` folder
2. Run `python install.py` from command prompt
3. Start Fusion 360
4. Go to **Tools > ADD-INS**
5. Find **PinmapGen** and click **Run**

**Option B: Manual Install**
1. Copy the `PinmapGen` folder to your Fusion add-ins directory:
   - **Windows**: `%APPDATA%\\Autodesk\\Autodesk Fusion 360\\API\\AddIns\\`
   - **Mac**: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/`
2. Follow steps 3-5 above

### 2. Prepare Your Design
1. **Open Electronics workspace** in Fusion 360
2. **Make sure your schematic is complete** with:
   - MCU component properly placed and referenced (U1, U2, etc.)
   - All pins connected to nets with meaningful names
   - Design saved (not just a temporary sketch)

### 3. Generate Pinmaps
1. **Click the PinmapGen button** (in ADD-INS toolbar or Tools menu)
2. **Configure settings** in the dialog:

   **Microcontroller:**
   - Choose your MCU type (RP2040, STM32G0, ESP32)
   - Enter the reference designator (usually U1)

   **Output Files:**
   - ✅ MicroPython (.py) - Recommended for most projects
   - ✅ Arduino (.h) - For Arduino-compatible projects
   - ✅ Documentation (.md) - Always useful for reference
   - ☐ Diagrams (.mmd) - Optional visual diagrams

   **Output Location:**
   - Browse to choose where files are saved
   - Default: Creates 'pinmaps' folder next to your design

3. **Click Generate** and wait for completion

### 4. Handle Results

**✅ Success Dialog:**
- Shows number of files generated
- Click **"View Files"** to see the output
- Click **"Open in VS Code"** if programmer prefers that

**⚠️ Warnings Dialog:**
- Review any design issues found
- Usually safe to continue unless major problems
- Common warnings:
  - "Pin used multiple times" - Check for short circuits
  - "Differential pair incomplete" - Missing USB D+/D- partner
  - "ADC pin used for output" - May not work as expected

**❌ Error Dialog:**
- Read the plain-English explanation
- Most common fixes:
  - Make sure you're in Electronics workspace
  - Check MCU reference designator (U1 vs IC1)
  - Verify design is saved, not just a sketch
  - Try restarting Fusion 360

---

## 🔧 Troubleshooting

### "No active design found"
- Make sure a design is open in Fusion 360
- Switch to Electronics workspace (not Design workspace)

### "MCU 'U1' not found in design"
- Check the reference designator in your schematic
- It might be U2, IC1, or something else
- The add-in is case-sensitive: 'u1' ≠ 'U1'

### "Cannot write to output folder"
- Choose a different output location
- Make sure the folder exists and you can write to it
- Close any files that might be open in other programs

### "Electronics workspace not active"
- Click the **Electronics** workspace tab in Fusion
- If you don't see it, make sure your design has electronics data

### Add-in won't start
- Restart Fusion 360
- Go to Tools > ADD-INS and try running it again
- Check that Python is working in Fusion (try other add-ins)

---

## 📂 Understanding the Output

The add-in creates an organized folder structure:

```
📁 your-output-folder/
├── 📁 firmware/
│   ├── 📁 micropython/
│   │   └── 📄 pinmap_micropython.py    # Pin constants and helpers
│   ├── 📁 include/
│   │   └── 📄 pinmap_arduino.h         # Arduino header file
│   └── 📁 docs/
│       ├── 📄 PINOUT.md               # Human-readable documentation
│       └── 📄 pinout.mmd              # Mermaid diagram (if enabled)
└── 📁 pinmaps/
    └── 📄 pinmap.json                 # Raw data for advanced tools
```

### For Your Programmer

**Share the entire output folder** with your software developer. They'll know what to do with these files.

**Key files to point out:**
- **PINOUT.md** - Readable documentation they can reference
- **pinmap_micropython.py** - Ready to use in MicroPython projects
- **pinmap_arduino.h** - Ready to include in Arduino sketches
- **pinmap.json** - Raw data for any custom tooling they prefer

---

## 🎨 Design Best Practices

### Net Naming Tips
Use descriptive net names that indicate function:

**✅ Good Names:**
- `I2C_SDA`, `I2C_SCL` - Clearly indicates I2C pins
- `UART_TX`, `UART_RX` - Obviously UART communication
- `LED_DATA`, `LED_CLOCK` - Descriptive for LED strips
- `BUTTON_1`, `BUTTON_2` - Numbered buttons
- `ADC_BATTERY`, `ADC_TEMP` - What's being measured

**❌ Avoid:**
- `NetR1_1` - Autogenerated, not descriptive
- `N$1`, `N$2` - Fusion defaults, unhelpful
- `PIN_4` - Just repeats the pin number

### Component Reference Best Practices
- **Use standard prefixes**: U1, U2 for ICs; R1, R2 for resistors
- **Be consistent**: Don't mix U1 and IC1 in the same design
- **Start from 1**: U1, not U0 (some tools expect this)

### Design Validation
Before generating pinmaps, check:
- [ ] All MCU pins that need connections have them
- [ ] No unintended short circuits (nets with too many pins)
- [ ] Differential pairs are complete (USB D+/D- both connected)
- [ ] Power/ground connections are intentional
- [ ] Pin names match what you expect (GP4 vs GPIO4 vs P4)

---

## 🤝 Working with Programmers

### Handoff Checklist
When sharing generated files with your programmer:

1. **Share the complete output folder** (not just individual files)
2. **Include your schematic PDF** for reference
3. **Note any special requirements:**
   - "USB pins must support high-speed data"
   - "I2C pins need pull-up resistors"  
   - "ADC pin measures 0-3.3V battery voltage"
4. **Mention any warnings** from the generation process
5. **Provide component datasheets** if using unusual parts

### Communication Tips
- **"Here are the pinmaps"** - Share the output folder
- **"Pin 4 is for the user button"** - Reference by function, not just number
- **"I2C uses pins 0 and 1"** - Mention both pins for buses
- **"Check the PINOUT.md file"** - Point them to human-readable docs

---

## 🔄 Iterating Your Design

### When You Make Changes
1. **Update your schematic** in Fusion Electronics workspace
2. **Save the design** (Ctrl+S)
3. **Re-run PinmapGen** - it will overwrite old files
4. **Share updated files** with your programmer

### Version Control Tips
- **Keep old output folders** when making major changes
- **Name output folders with dates** (pinmaps_2024_09_27)
- **Note what changed** in your handoff communication

The add-in makes it easy to iterate - just click Generate again whenever your design changes!

---

## 💡 Advanced Features

### Multiple MCUs
If your design has multiple microcontrollers:
1. Run PinmapGen once for each MCU (U1, U2, etc.)
2. Use different output folders or rename them
3. Share both sets of files with your programmer

### Custom Output Locations
- **Project folder**: Keep pinmaps with your design files
- **Network drive**: Share directly with your team
- **Git repository**: Version control for software projects

### Integration with VS Code
The "Open in VS Code" button (when available) sets up a proper development environment for your programmer, with:
- Organized project structure
- Sample code using the generated pinmaps
- Development tasks and shortcuts

---

## 🆘 Getting Help

### When Something Goes Wrong
1. **Read the error message carefully** - they're written in plain English
2. **Check the troubleshooting section** above
3. **Try the suggested fixes** in the error dialog
4. **Restart Fusion 360** - fixes many temporary issues

### Reporting Issues
If you find a bug or need help:
1. **Note your Fusion version** (Help > About)
2. **Describe what you were trying to do**
3. **Include the exact error message**
4. **Share a simplified version of your design** (if possible)

### Learning More
- **PinmapGen CLI documentation** - For advanced users
- **Fusion 360 Electronics tutorials** - Improve your schematic skills
- **Microcontroller datasheets** - Understand pin capabilities

---

**🎉 Happy designing! Your programmer will love getting organized, validated pinmap files instead of having to dig through schematics.**