# Extending PinmapGen

Guide for adding new MCU support, custom parsers, and output formats to PinmapGen.

---

## Adding MCU Support

### Overview

Adding a new MCU family involves creating a **profile class** that defines pin mappings, capabilities, and validation rules. MCU profiles follow a consistent interface for normalization, validation, and metadata generation.

### Required Components

1. **Pin Definitions:** Physical to logical pin mapping
2. **Capabilities:** What each pin can do (GPIO, ADC, PWM, etc.)
3. **Normalization Rules:** Handle variant pin naming conventions
4. **Validation Logic:** MCU-specific warnings and constraints
5. **Integration:** Register with CLI and tooling

### Step-by-Step Process

#### 1. Create MCU Profile Class

```python
# tools/pinmapgen/mcu_newchip.py
from .normalize import MCUProfile
from typing import Dict, List, Set, Tuple, Optional

class NewChipProfile(MCUProfile):
    """
    Profile for NewChip MCU family
    
    Supports:
    - NewChip1000: 48-pin package, 32 GPIO
    - NewChip2000: 64-pin package, 48 GPIO  
    """
    
    def __init__(self):
        super().__init__()
        self.mcu_type = "newchip"
        self.package_info = {
            "type": "QFP-48",  # Default package
            "pin_count": 48
        }
        
    def get_pin_mapping(self) -> Dict[int, str]:
        """Map physical pins to logical pin names"""
        return {
            # Format: physical_pin: logical_name
            1: "PA0",   # Port A, Pin 0
            2: "PA1",
            3: "PA2", 
            # ... continue for all pins
            7: "PB0",   # Port B, Pin 0
            8: "PB1",
            # Power pins (not GPIO)
            12: "VCC",
            24: "GND",
            # Special function pins  
            45: "NRST",  # Reset pin
            46: "BOOT0", # Boot mode
            47: "XTAL1", # Crystal oscillator
            48: "XTAL2"
        }
        
    def get_pin_capabilities(self) -> Dict[str, List[str]]:
        """Define what each logical pin can do"""
        return {
            # GPIO pins with various capabilities
            "PA0": ["gpio", "adc", "timer"],      # ADC input, timer output
            "PA1": ["gpio", "adc", "timer"],
            "PA2": ["gpio", "uart", "timer"],     # UART TX capable
            "PA3": ["gpio", "uart"],              # UART RX capable
            "PA4": ["gpio", "spi"],               # SPI CS
            "PA5": ["gpio", "spi"],               # SPI CLK
            "PA6": ["gpio", "spi"],               # SPI MISO
            "PA7": ["gpio", "spi"],               # SPI MOSI
            
            "PB0": ["gpio", "i2c"],               # I2C SDA
            "PB1": ["gpio", "i2c"],               # I2C SCL
            "PB2": ["gpio", "pwm"],               # PWM output only
            
            # Power pins - no GPIO capability
            "VCC": ["power"],
            "GND": ["power"], 
            
            # Special pins
            "NRST": ["reset"],
            "BOOT0": ["boot"],
            "XTAL1": ["clock"],
            "XTAL2": ["clock"]
        }
        
    def normalize_pin_name(self, pin_name: str) -> Optional[str]:
        """Convert various pin name formats to canonical form"""
        
        # Remove common prefixes/suffixes
        clean_name = pin_name.upper().strip()
        
        # Handle common NewChip naming variations
        normalizations = {
            # GPIO port variations
            "PORTA_0": "PA0",
            "PORT_A_0": "PA0", 
            "GPIO_A0": "PA0",
            "GPIOA_0": "PA0",
            
            # Numeric formats
            "PIN_1": "PA0",     # Assuming pin 1 maps to PA0
            "IO1": "PA0",
            "GPIO1": "PA0",
            
            # Communication interface variations  
            "UART1_TX": "PA2",  # Map to known UART-capable pin
            "UART1_RX": "PA3",
            "I2C1_SDA": "PB0",
            "I2C1_SCL": "PB1",
            "SPI1_CLK": "PA5",
            "SPI1_MISO": "PA6", 
            "SPI1_MOSI": "PA7",
            
            # Power variations
            "VDD": "VCC",
            "VDDA": "VCC", 
            "VSS": "GND",
            "VSSA": "GND",
            
            # Special pin variations
            "RESET": "NRST",
            "RST": "NRST",
            "BOOT": "BOOT0"
        }
        
        # Try direct lookup first
        if clean_name in normalizations:
            return normalizations[clean_name]
            
        # Handle port-based patterns with regex
        import re
        
        # Match patterns like "PA0", "PB15", etc.
        port_match = re.match(r'P([A-Z])(\d+)', clean_name)
        if port_match:
            port_letter, pin_num = port_match.groups()
            canonical = f"P{port_letter}{pin_num}"
            
            # Verify this is a valid pin for our MCU
            pin_mapping = self.get_pin_mapping()
            if canonical in pin_mapping.values():
                return canonical
        
        # If no normalization found, return None to indicate invalid pin
        return None
        
    def validate_pin_assignment(self, pin_name: str, net_name: str, 
                              role: str) -> Tuple[List[str], List[str]]:
        """Validate pin usage and return (warnings, errors)"""
        warnings = []
        errors = []
        
        capabilities = self.get_pin_capabilities()
        pin_caps = capabilities.get(pin_name, [])
        
        # Error conditions
        if "power" in pin_caps:
            errors.append(f"{pin_name}: Power pins cannot be used for GPIO signals")
            
        if "clock" in pin_caps:
            errors.append(f"{pin_name}: Crystal oscillator pins reserved for system clock")
            
        # Role-specific validation
        if role == "adc_input":
            if "adc" not in pin_caps:
                warnings.append(f"{pin_name}: No ADC capability, consider PA0-PA1 for analog inputs")
                
        elif role == "pwm_output":
            if "pwm" not in pin_caps and "timer" not in pin_caps:
                warnings.append(f"{pin_name}: No PWM/timer capability for smooth output control")
                
        elif role == "i2c":
            if "i2c" not in pin_caps:
                warnings.append(f"{pin_name}: No I2C capability, use PB0/PB1 for I2C interface")
                
        # NewChip-specific constraints
        if net_name.upper().startswith("USB_"):
            warnings.append(f"{pin_name}: NewChip family has no built-in USB - use external USB-serial converter")
            
        # Check for high-speed signal integrity
        if "CLK" in net_name.upper() or "CLOCK" in net_name.upper():
            if pin_name not in ["PA5"]:  # Only PA5 has good clock routing
                warnings.append(f"{pin_name}: High-speed clocks should use PA5 for optimal signal integrity")
        
        return warnings, errors
        
    def get_mcu_info(self) -> Dict:
        """Return MCU metadata for documentation"""
        return {
            "type": self.mcu_type,
            "family": "NewChip",
            "package": self.package_info["type"],
            "pin_count": self.package_info["pin_count"],
            "capabilities": {
                "gpio_pins": 32,
                "adc_channels": 2,   # PA0, PA1
                "pwm_channels": 4,   # PB2 + timer pins 
                "uart_interfaces": 1, # PA2/PA3
                "i2c_interfaces": 1,  # PB0/PB1
                "spi_interfaces": 1,  # PA4-PA7
                "usb_interfaces": 0   # No built-in USB
            },
            "voltage": "1.8V - 3.6V",
            "frequency": "80MHz max",
            "flash": "256KB",
            "ram": "64KB"
        }
        
    def get_differential_pairs(self) -> List[Tuple[str, str]]:
        """Return known differential signal pairs"""
        # NewChip doesn't have built-in differential pairs
        # But we can detect common external pairs
        return [
            # Common external differential signals
            ("CAN_H", "CAN_L"),
            ("RS485_A", "RS485_B") 
        ]
```

#### 2. Register MCU Profile

```python
# tools/pinmapgen/cli.py
from .mcu_newchip import NewChipProfile

# Add to MCU_PROFILES dictionary
MCU_PROFILES = {
    "rp2040": RP2040Profile,
    "stm32g0": STM32G0Profile, 
    "esp32": ESP32Profile,
    "newchip": NewChipProfile,  # Add new profile here
}
```

#### 3. Create Test Cases

```python
# tests/test_newchip_profile.py
import unittest
from tools.pinmapgen.mcu_newchip import NewChipProfile

class TestNewChipProfile(unittest.TestCase):
    
    def setUp(self):
        self.profile = NewChipProfile()
        
    def test_pin_normalization(self):
        """Test various pin name formats normalize correctly"""
        test_cases = [
            ("PORTA_0", "PA0"),
            ("GPIO_A0", "PA0"),
            ("UART1_TX", "PA2"), 
            ("I2C1_SDA", "PB0"),
            ("VDD", "VCC"),
            ("INVALID_PIN", None)
        ]
        
        for input_pin, expected in test_cases:
            with self.subTest(input_pin=input_pin):
                result = self.profile.normalize_pin_name(input_pin)
                self.assertEqual(result, expected)
                
    def test_pin_capabilities(self):
        """Test pin capabilities are correctly defined"""
        caps = self.profile.get_pin_capabilities()
        
        # Test ADC pins
        self.assertIn("adc", caps["PA0"])
        self.assertIn("adc", caps["PA1"]) 
        
        # Test communication pins
        self.assertIn("uart", caps["PA2"])
        self.assertIn("i2c", caps["PB0"])
        self.assertIn("spi", caps["PA5"])
        
        # Test power pins don't have GPIO capability
        self.assertNotIn("gpio", caps["VCC"])
        self.assertNotIn("gpio", caps["GND"])
        
    def test_validation_warnings(self):
        """Test MCU-specific validation rules"""
        
        # Test ADC validation
        warnings, errors = self.profile.validate_pin_assignment("PB2", "TEMP_SENSOR", "adc_input")
        self.assertTrue(any("ADC capability" in w for w in warnings))
        
        # Test power pin error
        warnings, errors = self.profile.validate_pin_assignment("VCC", "LED_DATA", "output")
        self.assertTrue(any("Power pins cannot" in e for e in errors))
        
        # Test USB warning (NewChip has no USB)
        warnings, errors = self.profile.validate_pin_assignment("PA0", "USB_DP", "usb")
        self.assertTrue(any("no built-in USB" in w for w in warnings))
        
    def test_mcu_info(self):
        """Test MCU metadata is complete"""
        info = self.profile.get_mcu_info()
        
        required_fields = ["type", "family", "package", "pin_count", "capabilities"]
        for field in required_fields:
            self.assertIn(field, info)
            
        # Test specific capabilities
        caps = info["capabilities"] 
        self.assertEqual(caps["gpio_pins"], 32)
        self.assertEqual(caps["adc_channels"], 2)
        self.assertEqual(caps["usb_interfaces"], 0)

if __name__ == "__main__":
    unittest.main()
```

#### 4. Create Sample Netlist

```csv
# hardware/exports/newchip_sample.csv  
Part Name,Designator,Pin,Net Name
NewChip1000,U1,1,PA0,TEMP_SENSOR
NewChip1000,U1,2,PA1,LIGHT_SENSOR
NewChip1000,U1,3,PA2,DEBUG_TX
NewChip1000,U1,4,PA3,DEBUG_RX
NewChip1000,U1,7,PB0,I2C_SDA
NewChip1000,U1,8,PB1,I2C_SCL
NewChip1000,U1,9,PB2,LED_STATUS
LED,D1,1,LED_STATUS
LED,D1,2,GND
TempSensor,U2,1,VCC
TempSensor,U2,2,GND
TempSensor,U2,3,TEMP_SENSOR
```

#### 5. Test Integration

```bash
# Test new MCU profile
python -m tools.pinmapgen.cli \
    --csv hardware/exports/newchip_sample.csv \
    --mcu newchip \
    --mcu-ref U1 \
    --out-root test_newchip/ \
    --mermaid

# Verify outputs generated
ls test_newchip/
# Should show: pinmaps/ firmware/ directories with generated files

# Run profile-specific tests  
python -m pytest tests/test_newchip_profile.py -v
```

#### 6. Documentation and Examples

```python
# Update CLI help text
def get_mcu_help():
    return """
    Supported MCU types:
    
    rp2040      - Raspberry Pi RP2040 (Pico, etc.)
    stm32g0     - STMicroelectronics STM32G0 series  
    esp32       - Espressif ESP32 (original)
    newchip     - NewChip MCU family (NewChip1000/2000)
    
    Use --mcu <type> to specify the target MCU for your design.
    """
```

---

## Adding Custom Parsers

### Creating Input Format Parsers

PinmapGen uses a **parser interface** to read netlists from different CAD tools. You can add support for new formats by implementing the parser protocol.

#### Parser Interface

```python  
# tools/pinmapgen/parse_interface.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class NetlistEntry:
    """Standardized netlist entry"""
    part_name: str      # Component type (e.g., "RP2040")
    designator: str     # Reference designator (e.g., "U1")
    pin: str           # Pin identifier (varies by format)  
    net_name: str      # Net/signal name
    
class NetlistParser(ABC):
    """Abstract base class for netlist parsers"""
    
    @abstractmethod
    def can_parse(self, file_path: str) -> bool:
        """Return True if this parser can handle the file format"""
        pass
        
    @abstractmethod  
    def parse(self, file_path: str) -> List[NetlistEntry]:
        """Parse file and return list of netlist entries"""
        pass
        
    @abstractmethod
    def get_format_name(self) -> str:
        """Return human-readable format name"""
        pass
```

#### Example: KiCad Parser

```python
# tools/pinmapgen/parse_kicad.py
import re
from pathlib import Path
from typing import List
from .parse_interface import NetlistParser, NetlistEntry

class KiCadNetlistParser(NetlistParser):
    """Parser for KiCad netlist files (.net format)"""
    
    def can_parse(self, file_path: str) -> bool:
        """Check if file appears to be KiCad netlist format"""
        path = Path(file_path)
        
        # Check file extension
        if path.suffix.lower() not in ['.net', '.kicad_net']:
            return False
            
        # Check file content for KiCad signatures
        try:
            with open(path, 'r', encoding='utf-8') as f:
                first_lines = f.read(1024)
                return '(export' in first_lines and '(components' in first_lines
        except Exception:
            return False
            
    def parse(self, file_path: str) -> List[NetlistEntry]:
        """Parse KiCad netlist and extract pin connections"""
        entries = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # KiCad netlists use S-expression format
        # Parse components section: (comp (ref U1) (value RP2040) ...)
        components = self._parse_components(content)
        
        # Parse nets section: (net (code 1) (name "LED_STATUS") (node (ref U1) (pin 20)) ...)
        nets = self._parse_nets(content)
        
        # Cross-reference to create netlist entries
        for net_name, nodes in nets.items():
            for ref, pin in nodes:
                if ref in components:
                    part_name = components[ref]
                    entries.append(NetlistEntry(
                        part_name=part_name,
                        designator=ref,
                        pin=pin,
                        net_name=net_name
                    ))
                    
        return entries
        
    def _parse_components(self, content: str) -> Dict[str, str]:
        """Extract component reference to part name mapping"""
        components = {}
        
        # Find components section
        comp_pattern = r'\(comp\s+\(ref\s+([^)]+)\)\s+\(value\s+([^)]+)\)'
        
        for match in re.finditer(comp_pattern, content):
            ref = match.group(1)
            value = match.group(2)
            components[ref] = value
            
        return components
        
    def _parse_nets(self, content: str) -> Dict[str, List[tuple]]:
        """Extract net connections"""
        nets = {}
        
        # Find nets section - more complex S-expression parsing
        net_pattern = r'\(net\s+\(code\s+\d+\)\s+\(name\s+"([^"]+)"\)(.*?)\)'
        
        for net_match in re.finditer(net_pattern, content, re.DOTALL):
            net_name = net_match.group(1)
            nodes_section = net_match.group(2)
            
            # Extract nodes: (node (ref U1) (pin 20))
            node_pattern = r'\(node\s+\(ref\s+([^)]+)\)\s+\(pin\s+([^)]+)\)\)'
            
            nodes = []
            for node_match in re.finditer(node_pattern, nodes_section):
                ref = node_match.group(1) 
                pin = node_match.group(2)
                nodes.append((ref, pin))
                
            if nodes:
                nets[net_name] = nodes
                
        return nets
        
    def get_format_name(self) -> str:
        return "KiCad Netlist (.net)"
```

#### Register Parser

```python
# tools/pinmapgen/cli.py  
from .parse_kicad import KiCadNetlistParser

# Add to parser registry
NETLIST_PARSERS = [
    BOMCSVParser(),        # Existing CSV parser
    EagleSchematicParser(), # Existing EAGLE parser
    KiCadNetlistParser(),   # New KiCad parser
]

def auto_detect_parser(file_path: str) -> NetlistParser:
    """Automatically detect appropriate parser for file"""
    for parser in NETLIST_PARSERS:
        if parser.can_parse(file_path):
            return parser
            
    raise ValueError(f"No parser found for file: {file_path}")
```

#### Parser Testing

```python
# tests/test_kicad_parser.py
import unittest
from pathlib import Path
from tools.pinmapgen.parse_kicad import KiCadNetlistParser

class TestKiCadParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = KiCadNetlistParser()
        
        # Create test netlist content
        self.test_netlist = '''
        (export (version D)
          (components
            (comp (ref U1)
              (value RP2040)
              (footprint Package_QFN:QFN-56-1EP_7x7mm_P0.4mm_EP5.6x5.6mm))
            (comp (ref D1)
              (value LED)
              (footprint LED_SMD:LED_0603_1608Metric)))
          (nets
            (net (code 1) (name "LED_STATUS")
              (node (ref U1) (pin 20))
              (node (ref D1) (pin 1)))
            (net (code 2) (name "GND")  
              (node (ref U1) (pin 57))
              (node (ref D1) (pin 2)))))
        '''
        
    def test_can_parse(self):
        """Test format detection"""
        # Create temporary test file
        test_file = Path("test.net")
        test_file.write_text(self.test_netlist)
        
        try:
            self.assertTrue(self.parser.can_parse(str(test_file)))
            self.assertFalse(self.parser.can_parse("test.csv"))  # Wrong format
        finally:
            test_file.unlink(missing_ok=True)
            
    def test_parse_netlist(self):
        """Test netlist parsing"""
        test_file = Path("test.net")
        test_file.write_text(self.test_netlist)
        
        try:
            entries = self.parser.parse(str(test_file))
            
            # Verify expected entries
            self.assertEqual(len(entries), 4)  # 2 nets × 2 nodes each
            
            # Check specific entries
            u1_entries = [e for e in entries if e.designator == "U1"]
            self.assertEqual(len(u1_entries), 2)
            
            led_entry = next((e for e in entries if e.net_name == "LED_STATUS" and e.designator == "U1"), None)
            self.assertIsNotNone(led_entry)
            self.assertEqual(led_entry.pin, "20")
            self.assertEqual(led_entry.part_name, "RP2040")
            
        finally:
            test_file.unlink(missing_ok=True)
```

---

## Adding Output Formats

### Creating Custom Emitters

Output formats are handled by **emitter modules** that generate specific file types from normalized pin data.

#### Emitter Interface

```python
# tools/pinmapgen/emit_interface.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from pathlib import Path

class OutputEmitter(ABC):
    """Abstract base class for output format emitters"""
    
    @abstractmethod
    def emit(self, pin_data: List[Dict], mcu_info: Dict, output_dir: Path) -> Path:
        """Generate output file and return path to created file"""
        pass
        
    @abstractmethod  
    def get_output_name(self) -> str:
        """Return base filename for this output format"""
        pass
        
    @abstractmethod
    def get_format_description(self) -> str:
        """Return human-readable format description"""
        pass
```

#### Example: YAML Emitter

```python
# tools/pinmapgen/emit_yaml.py
import yaml
from pathlib import Path
from typing import Dict, List
from .emit_interface import OutputEmitter

class YAMLEmitter(OutputEmitter):
    """Generate YAML configuration files for deployment tools"""
    
    def emit(self, pin_data: List[Dict], mcu_info: Dict, output_dir: Path) -> Path:
        """Generate YAML pinmap configuration"""
        
        output_path = output_dir / "config" / "pinmap.yaml"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert pin data to YAML-friendly structure
        yaml_data = {
            "metadata": {
                "generated_at": mcu_info.get("generated_at"),
                "mcu_type": mcu_info["type"],
                "mcu_package": mcu_info["package"]
            },
            "gpio_config": {},
            "communication": {},
            "power_management": {}
        }
        
        # Organize pins by function
        for pin in pin_data:
            pin_name = pin["logical_pin"]
            net_name = pin["net_name"] 
            role = pin["role"]
            
            if role in ["input", "output"]:
                yaml_data["gpio_config"][net_name] = {
                    "pin": pin_name,
                    "direction": role,
                    "capabilities": pin["capabilities"],
                    "physical_pin": pin["physical_pin"]
                }
                
            elif role in ["i2c", "spi", "uart"]:
                if role not in yaml_data["communication"]:
                    yaml_data["communication"][role] = {}
                    
                yaml_data["communication"][role][net_name] = {
                    "pin": pin_name,
                    "physical_pin": pin["physical_pin"]
                }
                
        # Write YAML with proper formatting
        with open(output_path, 'w') as f:
            yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False, indent=2)
            
        return output_path
        
    def get_output_name(self) -> str:
        return "pinmap.yaml"
        
    def get_format_description(self) -> str:
        return "YAML configuration for deployment automation"
```

#### Example: SystemVerilog Emitter

```python
# tools/pinmapgen/emit_systemverilog.py  
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from .emit_interface import OutputEmitter

class SystemVerilogEmitter(OutputEmitter):
    """Generate SystemVerilog parameter files for FPGA projects"""
    
    def emit(self, pin_data: List[Dict], mcu_info: Dict, output_dir: Path) -> Path:
        """Generate SystemVerilog pin definitions"""
        
        output_path = output_dir / "rtl" / "pin_definitions.sv" 
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate SystemVerilog package
        sv_content = f'''//
// Pin mapping definitions for {mcu_info["type"].upper()}
// Generated: {datetime.now().isoformat()}
// Source: {mcu_info.get("source_file", "Unknown")}
//
// ⚠️  AUTOMATICALLY GENERATED - DO NOT EDIT MANUALLY

package pin_definitions_pkg;

  // MCU Information
  parameter string MCU_TYPE = "{mcu_info["type"]}";
  parameter int MCU_PIN_COUNT = {mcu_info["pin_count"]};

  // GPIO Pin Assignments
'''

        # Group pins by role for better organization
        gpio_pins = [p for p in pin_data if p["role"] in ["input", "output"]]
        comm_pins = [p for p in pin_data if p["role"] in ["i2c", "spi", "uart"]] 
        
        # Generate GPIO constants
        if gpio_pins:
            sv_content += "  // Digital I/O Pins\n"
            for pin in gpio_pins:
                net_name = pin["net_name"].upper()
                pin_num = pin["physical_pin"]
                sv_content += f'  parameter int {net_name}_PIN = {pin_num};\n'
                
        # Generate communication interface constants  
        if comm_pins:
            sv_content += "\n  // Communication Interface Pins\n"
            for pin in comm_pins:
                net_name = pin["net_name"].upper()
                pin_num = pin["physical_pin"]
                sv_content += f'  parameter int {net_name}_PIN = {pin_num};\n'
                
        # Add validation functions
        sv_content += '''
  // Validation Functions
  function automatic bit is_valid_gpio_pin(int pin_num);
    case (pin_num)
'''
        
        for pin in pin_data:
            if "gpio" in pin["capabilities"]:
                sv_content += f'      {pin["physical_pin"]}: return 1\'b1;\n'
                
        sv_content += '''      default: return 1'b0;
    endcase
  endfunction

endpackage : pin_definitions_pkg

// Usage example:
// import pin_definitions_pkg::*;
// 
// module gpio_controller (
//   input  logic clk,
//   output logic [MCU_PIN_COUNT-1:0] gpio_out
// );
//   
//   // Use generated pin constants
//   assign gpio_out[LED_STATUS_PIN] = blink_counter[25];
//   
// endmodule
'''

        with open(output_path, 'w') as f:
            f.write(sv_content)
            
        return output_path
        
    def get_output_name(self) -> str:
        return "pin_definitions.sv"
        
    def get_format_description(self) -> str:
        return "SystemVerilog package for FPGA pin mapping"
```

#### Register Emitters

```python
# tools/pinmapgen/cli.py
from .emit_yaml import YAMLEmitter
from .emit_systemverilog import SystemVerilogEmitter

# Add to emitter registry  
OUTPUT_EMITTERS = [
    JSONEmitter(),              # Existing emitters
    MicroPythonEmitter(),
    ArduinoEmitter(), 
    MarkdownEmitter(),
    MermaidEmitter(),
    YAMLEmitter(),              # New custom emitters
    SystemVerilogEmitter(),
]

def generate_all_outputs(pin_data, mcu_info, output_dir):
    """Generate all registered output formats"""
    generated_files = []
    
    for emitter in OUTPUT_EMITTERS:
        try:
            output_file = emitter.emit(pin_data, mcu_info, Path(output_dir))
            generated_files.append((emitter.get_format_description(), output_file))
            print(f"✅ Generated {emitter.get_format_description()}: {output_file}")
        except Exception as e:
            print(f"❌ Failed to generate {emitter.get_format_description()}: {e}")
            
    return generated_files
```

---

## Advanced Customization

### Custom Validation Rules

```python
# tools/pinmapgen/validate_custom.py
from typing import List, Tuple, Dict

class CustomValidationRules:
    """Project-specific validation rules"""
    
    def __init__(self, project_config: Dict):
        self.config = project_config
        
    def validate_power_budget(self, pin_data: List[Dict]) -> List[str]:
        """Check if pin assignments exceed power budget"""
        warnings = []
        
        # Count high-power outputs
        high_power_pins = [
            pin for pin in pin_data 
            if pin["role"] == "output" and "LED" in pin["net_name"].upper()
        ]
        
        max_leds = self.config.get("max_led_outputs", 8)
        if len(high_power_pins) > max_leds:
            warnings.append(f"Too many LED outputs ({len(high_power_pins)} > {max_leds}) - check power budget")
            
        return warnings
        
    def validate_emc_compliance(self, pin_data: List[Dict]) -> List[str]:
        """Check EMC-sensitive pin assignments"""
        warnings = []
        
        # Find high-speed clock pins
        clock_pins = [pin for pin in pin_data if "CLK" in pin["net_name"].upper()]
        
        # Check if clocks are near sensitive analog pins
        analog_pins = [pin for pin in pin_data if pin["role"] == "adc_input"]
        
        for clock_pin in clock_pins:
            clock_physical = clock_pin["physical_pin"]
            for analog_pin in analog_pins:
                analog_physical = analog_pin["physical_pin"]
                
                # Check if pins are adjacent (simplified check)
                if abs(clock_physical - analog_physical) <= 2:
                    warnings.append(
                        f"Clock signal {clock_pin['net_name']} on pin {clock_physical} "
                        f"may interfere with analog input {analog_pin['net_name']} on pin {analog_physical}"
                    )
                    
        return warnings
```

### Template-Based Generation

```python
# tools/pinmapgen/emit_template.py
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from .emit_interface import OutputEmitter

class TemplateEmitter(OutputEmitter):
    """Generic template-based emitter using Jinja2"""
    
    def __init__(self, template_file: str, output_filename: str, description: str):
        self.template_file = template_file
        self.output_filename = output_filename 
        self.description = description
        
    def emit(self, pin_data, mcu_info, output_dir):
        """Generate output using Jinja2 template"""
        
        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(self.template_file)
        
        # Prepare template context
        context = {
            "pins": pin_data,
            "mcu": mcu_info,
            "timestamp": datetime.now().isoformat(),
            # Add helper functions
            "pins_by_role": lambda role: [p for p in pin_data if p["role"] == role],
            "pins_with_capability": lambda cap: [p for p in pin_data if cap in p["capabilities"]],
        }
        
        # Render template
        output_content = template.render(**context)
        
        # Write to file
        output_path = output_dir / self.output_filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(output_content)
            
        return output_path
        
    def get_output_name(self) -> str:
        return self.output_filename
        
    def get_format_description(self) -> str:
        return self.description
```

Example template file:
```jinja2
{# templates/rust_pinmap.rs.j2 #}
//! Pin mapping constants for Rust embedded projects
//! Generated: {{ timestamp }}
//! MCU: {{ mcu.type }} ({{ mcu.package }})

use embedded_hal::digital::v2::{InputPin, OutputPin};

// Pin number constants
{% for pin in pins -%}
pub const {{ pin.net_name.upper() }}: u8 = {{ pin.physical_pin }};  // {{ pin.logical_pin }}
{% endfor %}

// Pin capability traits
{% for pin in pins_by_role("output") -%}
// {{ pin.net_name }} can be used as OutputPin
{% endfor %}

{% for pin in pins_by_role("input") -%}  
// {{ pin.net_name }} can be used as InputPin
{% endfor %}

// MCU information
pub const MCU_TYPE: &str = "{{ mcu.type }}";
pub const MCU_PIN_COUNT: usize = {{ mcu.pin_count }};
```

---

## Contributing Extensions

### Submission Guidelines

1. **Follow existing patterns** - Use the same interfaces and conventions as built-in components
2. **Include comprehensive tests** - Unit tests for all major functionality
3. **Add documentation** - README sections, docstrings, usage examples
4. **Handle edge cases** - Graceful error handling and validation
5. **Performance considerations** - Efficient parsing and generation for large netlists

### Example Pull Request Structure

```
Pull Request: Add KiCad netlist support

Files changed:
+ tools/pinmapgen/parse_kicad.py       # Parser implementation
+ tests/test_kicad_parser.py           # Comprehensive test suite  
+ tests/fixtures/sample.kicad_net      # Test data
+ docs/extending.md                    # Documentation updates
~ tools/pinmapgen/cli.py               # Register new parser
~ README.md                            # Update supported formats list

Description:
Adds support for parsing KiCad netlist files (.net format) with:
- S-expression format parsing
- Component and net extraction  
- Automatic format detection
- Comprehensive test coverage
- Error handling for malformed files

Testing:
- All existing tests pass
- New parser tests achieve 95% code coverage
- Tested with KiCad 6.0 and 7.0 generated netlists
- Integration tested with sample RP2040 project

Documentation:
- Updated extending.md with parser creation guide
- Added KiCad to supported formats in README
- Included usage examples and troubleshooting tips
```

### Community Extensions Registry

**Planned community extensions:**
- **Altium Designer parser** - Support for Altium netlist exports
- **LTspice integration** - Parse SPICE netlists for analog verification
- **Rust embedded emitter** - Generate embedded-hal compatible constants  
- **FreeCAD integration** - Import pin assignments for 3D mechanical design
- **CircuitPython emitter** - Optimized constants for CircuitPython projects

Extensions can be distributed as separate packages that extend PinmapGen's core functionality while maintaining compatibility with the main toolchain.
