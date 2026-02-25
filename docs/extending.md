# Extending PinmapGen

How to add new MCU support, input parsers, and output formats.

---

## Adding MCU support

### Overview

An MCU profile defines pin mappings, capabilities, normalization rules, and
validation logic for a specific microcontroller family. All profiles subclass
`MCUProfile` from `mcu_profiles.py`.

### Steps

#### 1. Create the profile class

Create `tools/pinmapgen/<mcu>_profile.py`:

```python
from .mcu_profiles import MCUProfile, PinCapability, PinInfo, PeripheralInfo

class NewChipProfile(MCUProfile):
    """Profile for NewChip MCU family."""

    def __init__(self):
        super().__init__()
        self.mcu_type = "newchip"

    def _initialize_pin_definitions(self):
        """Define physical-to-logical pin mapping and capabilities."""
        self.pin_definitions = {
            1: PinInfo("PA0", [PinCapability.GPIO, PinCapability.ADC]),
            2: PinInfo("PA1", [PinCapability.GPIO, PinCapability.ADC]),
            3: PinInfo("PA2", [PinCapability.GPIO, PinCapability.UART]),
            # ...
        }

    def _initialize_peripherals(self):
        """Define peripheral instances and their valid pin sets."""
        self.peripherals = {
            "I2C0": PeripheralInfo(sda=["PB0"], scl=["PB1"]),
            "UART0": PeripheralInfo(tx=["PA2"], rx=["PA3"]),
        }

    def normalize_pin_name(self, pin_name: str) -> str | None:
        """Convert variant pin names to canonical form.

        Examples:
            'PORTA_0' → 'PA0'
            'GPIO_A0' → 'PA0'
            'VDD'     → 'VCC'
        """
        clean = pin_name.upper().strip()

        # Direct mappings
        aliases = {
            "PORTA_0": "PA0",
            "GPIO_A0": "PA0",
            "VDD": "VCC",
            "VSS": "GND",
            "RESET": "NRST",
        }
        if clean in aliases:
            return aliases[clean]

        # Regex fallback for port-based names
        import re
        m = re.match(r"P([A-Z])(\d+)", clean)
        if m:
            canonical = f"P{m.group(1)}{m.group(2)}"
            if canonical in {p.name for p in self.pin_definitions.values()}:
                return canonical

        return None
```

#### 2. Register with the CLI

```python
# tools/pinmapgen/cli.py
from .newchip_profile import NewChipProfile

MCU_PROFILES = {
    "rp2040": RP2040Profile,
    "stm32g0": STM32G0Profile,
    "esp32": ESP32Profile,
    "newchip": NewChipProfile,
}
```

#### 3. Add tests

```python
# tests/test_newchip_profile.py
import unittest
from tools.pinmapgen.newchip_profile import NewChipProfile

class TestNewChipProfile(unittest.TestCase):
    def setUp(self):
        self.profile = NewChipProfile()

    def test_normalize_port_name(self):
        self.assertEqual(self.profile.normalize_pin_name("PORTA_0"), "PA0")

    def test_normalize_unknown_returns_none(self):
        self.assertIsNone(self.profile.normalize_pin_name("INVALID_PIN"))

    def test_pin_capabilities(self):
        pin = self.profile.pin_definitions[1]
        self.assertIn(PinCapability.ADC, pin.capabilities)
```

#### 4. Add a sample netlist

Create `hardware/exports/newchip_netlist.csv`:

```csv
RefDes,Pin,Component,Net
U1,1,NewChip1000,TEMP_SENSOR
U1,2,NewChip1000,LIGHT_SENSOR
U1,3,NewChip1000,DEBUG_TX
```

#### 5. Verify end-to-end

```bash
python -m tools.pinmapgen.cli \
  --csv hardware/exports/newchip_netlist.csv \
  --mcu newchip \
  --mcu-ref U1 \
  --out-root test_output/ \
  --mermaid

python -m pytest tests/test_newchip_profile.py -v
```

---

## Adding input parsers

PinmapGen currently supports two input formats: CSV (`bom_csv.py`) and EAGLE
schematic XML (`eagle_sch.py`). Both return `dict[str, list[str]]` mapping net
names to lists of pins.

### Writing a new parser

```python
# tools/pinmapgen/parse_kicad.py
from pathlib import Path

def parse_kicad_netlist(file_path: str | Path, mcu_ref: str) -> dict[str, list[str]]:
    """Parse a KiCad .net file and return net-to-pin mapping.

    Args:
        file_path: Path to the .net file.
        mcu_ref: Reference designator to filter (e.g., 'U1').

    Returns:
        dict mapping net names to lists of pin identifiers.

    Raises:
        ValueError: If the file isn't valid KiCad netlist format.
    """
    # KiCad netlists use S-expression format
    # Parse components and nets, filter by mcu_ref
    ...
```

### Registering with the CLI

Add an argument in `cli.py`:

```python
parser.add_argument("--kicad", help="KiCad netlist file (.net)")
```

Wire it into the main flow alongside `--csv` and `--sch`.

### Testing

- Create a minimal test fixture in `tests/fixtures/`.
- Write unit tests covering normal input, empty input, and malformed input.

---

## Adding output formats

### Emitter interface

Every emitter is a function with the signature:

```python
def emit_<format>(canonical_dict: dict, output_path: Path | str) -> None:
```

It receives the canonical dict and writes one file. It should:

1. Create parent directories: `output_path.parent.mkdir(parents=True, exist_ok=True)`
2. Write UTF-8 output.
3. Include an auto-generated header with source file, MCU, and timestamp.

### Example: YAML emitter

```python
# tools/pinmapgen/emit_yaml.py
from pathlib import Path

def emit_yaml(canonical_dict: dict, output_path: Path | str) -> None:
    """Generate a YAML pin configuration file.

    Args:
        canonical_dict: Canonical pinmap dictionary.
        output_path: Destination file path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Pin mapping for {canonical_dict['mcu']}",
        f"# AUTOMATICALLY GENERATED - DO NOT EDIT",
        "",
        f"mcu: {canonical_dict['mcu']}",
        "pins:",
    ]
    for net, pins in canonical_dict["pins"].items():
        lines.append(f"  {net}: {pins}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
```

### Registering

Call the emitter from `cli.py` → `generate_outputs()`:

```python
from .emit_yaml import emit_yaml

emit_yaml(canonical_dict, out_root / "config" / "pinmap.yaml")
```

### Testing

Add a test in `tests/test_emitters.py` that builds a minimal canonical dict,
calls the emitter, and verifies the output file content.

---

## Advanced customization

### Custom validation rules

Subclass or extend an existing profile to add project-specific checks:

```python
class StrictRP2040Profile(RP2040Profile):
    def _extra_validation(self, pinmap):
        warnings = super()._extra_validation(pinmap)
        led_count = sum(1 for net in pinmap if "LED" in net.upper())
        if led_count > 4:
            warnings.append(f"Too many LEDs ({led_count}) — check power budget")
        return warnings
```

### Template-based generation

For teams that need heavily customized output, consider a Jinja2-based emitter
(note: Jinja2 is not stdlib, so it would be a dev dependency):

```python
from jinja2 import Environment, FileSystemLoader

def emit_from_template(canonical_dict, template_name, output_path):
    env = Environment(loader=FileSystemLoader("templates/"))
    template = env.get_template(template_name)
    content = template.render(pins=canonical_dict["pins"], mcu=canonical_dict["mcu"])
    Path(output_path).write_text(content)
```

This is a non-stdlib approach, so it should only be used in project-specific
forks or behind optional imports.
