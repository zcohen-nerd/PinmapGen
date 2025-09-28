# 🎯 Fusion 360 Add-in Testing Guide

This guide walks through comprehensive testing of the PinmapGen Fusion 360 add-in to ensure it works correctly in the real Fusion environment.

---

## 🛠️ Pre-Testing Setup

### **Step 1: Install the Add-in**

**🎯 Quick Install (Recommended)**:
```bash
# Navigate to the fusion add-in directory
cd fusion_addin

# Try development mode first (usually works without admin)
python install.py --dev
```

**🔧 If You Get Permission Errors**:
```bash
# Option 1: Run PowerShell as Administrator, then:
python install.py

# Option 2: Force copy method
python install.py --force-copy

# Option 3: Get help for admin installation
python install.py --admin
```

**Expected Results**:
- ✅ Files copied to `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\PinmapGen\` (normal install)
- ✅ Files copied to `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\PinmapGen_Dev\` (dev mode)

### **Step 2: Enable the Add-in in Fusion**
1. Open Fusion 360
2. Go to **Utilities** → **Add-ins**
3. Find **PinmapGen** or **PinmapGen_Dev** in the list (depending on install method)
4. Click **Run** to enable it
5. Verify the **PinmapGen** panel appears in the toolbar

**🚨 Troubleshooting**: If you don't see the add-in:
- Check the "My Add-ins" tab in the Add-ins dialog
- Look for error messages in Fusion's Text Commands panel
- Try refreshing the add-ins list or restarting Fusion

---

## 🧪 Fusion Add-in Test Suite

### **Test F1: Add-in Installation & Loading**

**Objective**: Verify the add-in installs and loads without errors

**Steps**:
1. Install add-in using `python install.py`
2. Open Fusion 360
3. Enable PinmapGen add-in
4. Check for any error messages in Fusion's Text Commands panel

**Expected Results**:
- ✅ Add-in appears in Utilities → Add-ins list
- ✅ Add-in runs without errors
- ✅ PinmapGen toolbar/panel is visible
- ✅ No error messages in console

---

### **Test F2: User Interface Validation**

**Objective**: Verify all UI elements work correctly

**Steps**:
1. Click the PinmapGen button/panel
2. Verify all UI elements are present:
   - MCU selection dropdown (RP2040, STM32G0, ESP32)
   - Output format checkboxes (JSON, MicroPython, Arduino, Markdown, Mermaid)
   - Generate button
   - Output directory selection
3. Test dropdown functionality
4. Test checkbox toggling

**Expected Results**:
- ✅ All UI elements display correctly
- ✅ Dropdown shows all MCU options
- ✅ Checkboxes toggle properly
- ✅ UI is responsive and intuitive

---

### **Test F3: Electronics Data Extraction**

**Objective**: Test the add-in's ability to extract data from Fusion Electronics

**Prerequisites**: 
- Create a simple test circuit in Fusion Electronics with:
  - RP2040 component (named U1)
  - At least 5-10 nets connected to different pins
  - Mix of I2C, SPI, GPIO connections

**Steps**:
1. Open the test Electronics design
2. Run PinmapGen add-in
3. Select RP2040 as MCU
4. Set MCU reference to "U1"
5. Click Generate
6. Monitor Fusion's Text Commands for any errors

**Expected Results**:
- ✅ Add-in successfully extracts component data
- ✅ Nets are identified and parsed correctly
- ✅ Pin assignments are detected
- ✅ No extraction errors reported

---

### **Test F4: Pinmap Generation Integration**

**Objective**: Verify the add-in generates files correctly

**Steps**:
1. Use the same test circuit from F3
2. Select all output formats (JSON, MicroPython, Arduino, Markdown, Mermaid)
3. Choose an output directory
4. Click Generate
5. Check the output directory for generated files

**Expected Results**:
- ✅ All selected output files are created
- ✅ Files contain correct pin mappings from the Electronics design
- ✅ Generated code matches the actual component connections
- ✅ Success message displayed in Fusion

---

### **Test F5: Error Handling in Fusion**

**Objective**: Test error scenarios within Fusion environment

**Test Cases**:

**F5a: No Electronics Design**
1. Open Fusion with no active Electronics design
2. Run PinmapGen
3. Try to generate pinmap

**Expected**: Clear error message about missing Electronics design

**F5b: Invalid MCU Reference**
1. Open Electronics design with components
2. Set MCU reference to non-existent component (e.g., "U99")
3. Try to generate

**Expected**: Error message about MCU component not found

**F5c: No Output Directory**
1. Run generation without selecting output directory
2. Try to generate

**Expected**: Error message or default directory used

**F5d: No Pin Connections**
1. Open Electronics design with MCU but no connections
2. Try to generate

**Expected**: Warning about no nets found, but should not crash

---

### **Test F6: Real-World Circuit Testing**

**Objective**: Test with a complex, realistic Electronics design

**Create Test Circuit**:
```
Components needed in Fusion Electronics:
- RP2040 microcontroller (U1)
- I2C sensor (U2) - connected to GP0 (SDA), GP1 (SCL)
- SPI display (U3) - connected to GP2 (MOSI), GP3 (MISO), GP4 (SCK), GP5 (CS)
- UART module (U4) - connected to GP6 (TX), GP7 (RX)
- LEDs (D1, D2) - connected to GP10, GP11
- Buttons (SW1, SW2) - connected to GP12, GP13
- USB connector - connected to USB_DP, USB_DN
- Power connections (VCC, GND)
```

**Steps**:
1. Create the above circuit in Fusion Electronics
2. Ensure all nets are properly named and connected
3. Run PinmapGen add-in
4. Generate all output formats
5. Verify the generated files match the actual circuit

**Expected Results**:
- ✅ All 15+ nets detected correctly
- ✅ Bus groups identified (I2C, SPI, UART)
- ✅ Differential pair detected (USB_DP/USB_DN)
- ✅ Pin roles inferred correctly (I2C SDA/SCL, SPI MOSI/MISO/etc.)
- ✅ Generated MicroPython code has proper pin constants
- ✅ Generated Arduino code has correct #define statements
- ✅ Documentation shows proper pin assignments

---

### **Test F7: Multi-MCU Testing in Fusion**

**Objective**: Test different MCU profiles within Fusion

**Steps**:
1. Create the same basic circuit
2. Test with RP2040 profile - should work perfectly
3. Test with STM32G0 profile - should show warnings about invalid pin names
4. Test with ESP32 profile - should show similar warnings
5. Verify warnings are displayed clearly in Fusion interface

**Expected Results**:
- ✅ RP2040: Clean generation with GP pin names
- ✅ STM32G0: Warnings about invalid GP pins, suggests PA/PB format
- ✅ ESP32: Warnings about invalid pins, suggests GPIO format
- ✅ All profiles generate output files even with warnings

---

### **Test F8: Performance & Usability**

**Objective**: Evaluate real-world usability

**Metrics to Test**:
- **Speed**: Time from clicking Generate to completion
- **Responsiveness**: Does Fusion remain responsive during generation?
- **File Size**: Are generated files reasonable sizes?
- **Error Recovery**: Can user fix errors and re-generate easily?

**Steps**:
1. Time several generation cycles
2. Test with increasingly complex circuits (10, 20, 50+ nets)
3. Intentionally create errors and test recovery
4. Test multiple rapid generations

**Expected Results**:
- ✅ Generation completes in <5 seconds for typical circuits
- ✅ Fusion remains responsive during processing
- ✅ Generated files are appropriately sized (<100KB typically)
- ✅ Errors are recoverable without restarting add-in

---

## 🚨 **Critical Issues That Block Release**

**Immediate fix required if:**
- Add-in fails to install or load in Fusion
- Electronics data extraction fails silently
- Generated files are corrupt or empty
- Add-in crashes Fusion 360
- UI is unresponsive or broken
- Error messages are unclear or missing

**Can be addressed post-launch:**
- Minor UI polish improvements
- Additional validation warnings
- Performance optimizations
- Enhanced error messages

---

## 📋 **Fusion Testing Checklist**

### **Installation & Setup**
- [ ] Add-in installs without errors using install.py
- [ ] Add-in loads successfully in Fusion 360
- [ ] UI elements display correctly
- [ ] No console errors during startup

### **Basic Functionality**
- [ ] MCU dropdown works and shows all options
- [ ] Output format checkboxes toggle correctly
- [ ] File directory selection works
- [ ] Generate button triggers processing

### **Data Extraction**
- [ ] Electronics design data extracted correctly
- [ ] Component references resolved (U1, U2, etc.)
- [ ] Net names captured accurately
- [ ] Pin assignments detected properly

### **File Generation**
- [ ] JSON pinmap created with correct structure
- [ ] MicroPython file has valid syntax and pin constants
- [ ] Arduino header has proper #define statements
- [ ] Markdown documentation is formatted correctly
- [ ] Mermaid diagrams generated (if selected)

### **Error Handling**
- [ ] Missing Electronics design handled gracefully
- [ ] Invalid MCU reference produces clear error
- [ ] No nets scenario handled without crashing
- [ ] File write permissions issues reported clearly

### **Real-World Testing**
- [ ] Complex circuit (15+ nets) processes correctly
- [ ] Bus detection works (I2C, SPI, UART groups)
- [ ] Differential pairs identified (USB, CAN)
- [ ] Pin role inference accurate
- [ ] Multi-MCU warnings display properly

---

## 🎯 **Testing Priority Order**

1. **F1-F2**: Installation and UI (15 minutes) - Must work or nothing else matters
2. **F3-F4**: Basic functionality (30 minutes) - Core workflow validation  
3. **F5**: Error handling (20 minutes) - Robustness verification
4. **F6**: Real-world circuit (45 minutes) - Production readiness
5. **F7**: Multi-MCU testing (20 minutes) - Feature completeness
6. **F8**: Performance evaluation (15 minutes) - User experience validation

**Total estimated time: ~2.5 hours**

---

## 📝 **Test Results Documentation**

As you test each section, document:
- ✅ **Pass**: Feature works as expected
- ⚠️ **Warning**: Works but has minor issues
- ❌ **Fail**: Blocking issue that needs immediate fix
- 📝 **Notes**: Any observations or improvements needed

This will help prioritize any fixes needed before public release!

---

## 🚨 **Installation Troubleshooting**

### **"Access Denied" Errors**
```
❌ [WinError 5] Access is denied: 'C:\Users\...\API\AddIns\PinmapGen\commands'
```

**Solutions**:
1. **Try Development Mode**: `python install.py --dev` (recommended)
2. **Run as Administrator**: Right-click PowerShell → "Run as Administrator"
3. **Close Fusion First**: Make sure Fusion 360 is completely closed
4. **Manual Installation**: Copy files manually (installer will show instructions)

### **Add-in Not Appearing in Fusion**
- ✅ Check "My Add-ins" tab in Utilities → Add-ins
- ✅ Look for "PinmapGen" or "PinmapGen_Dev" 
- ✅ Check Text Commands panel for error messages
- ✅ Try restarting Fusion 360
- ✅ Reinstall with: `python install.py --dev`

### **Permission vs. Admin Mode**
- **Development Mode** (`--dev`): Usually works without admin rights
- **Normal Install**: May require administrator permissions on some systems
- **Manual Install**: Always works but requires copy/paste

---

**Ready to test! Your add-in is now installed. Start with F1 (installation check) and work through systematically.** 🚀