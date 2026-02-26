# Extending PinmapGen

How to add new MCU support, input parsers, and output formats.

---

## Adding MCU support

PinmapGen supports **13 MCUs** out of the box. You can add more in two ways:

| Approach | When to use | Effort |
|----------|-------------|--------|
| **TOML profile** (recommended) | Most MCUs — data-only, no Python needed | ~5 minutes |
| **Python profile class** | Complex validation that requires code | ~30 minutes |

### Option A — TOML profile (recommended)

Create a `.toml` file and point PinmapGen at it with `--profile-dir`.

#### 1. Create the TOML file

`my_profiles/newchip.toml`:

```toml
[profile]
schema_version = 1
name         = "newchip"
display_name = "NewChip1000"
description  = "My custom MCU"
family       = "custom"

[normalization]
canonical_prefix = "P"
allow_numeric    = false

# Convert "PORTA_0" → "PA0", "GPIO_A0" → "PA0", etc.
[[normalization.patterns]]
regex  = "GPIO_?([A-Z])(\\d+)"
output = "P{0}{1}"

[[normalization.patterns]]
regex  = "PORT([A-Z])_(\\d+)"
output = "P{0}{1}"

# Fixed aliases
[normalization.aliases]
VDD  = "PA0"
NRST = "PB0"

# Pin groups — sets of pins with identical capabilities
[[pins.groups]]
range        = { prefix = "PA", start = 0, end = 7 }
capabilities = ["gpio", "adc", "pwm"]

[[pins.groups]]
range        = { prefix = "PB", start = 0, end = 7 }
capabilities = ["gpio", "uart_tx", "uart_rx"]

# Individual pin overrides
[[pins.individual]]
name                   = "PB0"
special_function       = "Reset"
special_function_short = "NRST"
warnings               = ["PB0 is the hardware reset pin"]

# Peripherals
[[peripherals]]
name     = "UART"
instance = 0
pins     = { tx = "PB2", rx = "PB3" }

[[peripherals]]
name     = "ADC"
instance = 0
pins     = { ch0 = "PA0", ch1 = "PA1" }
```

#### 2. Use it

```bash
python -m tools.pinmapgen.cli \
  --csv hardware/exports/newchip_netlist.csv \
  --mcu newchip \
  --mcu-ref U1 \
  --profile-dir ./my_profiles \
  --out-root output/ \
  --mermaid
```

Or drop the `.toml` into `tools/pinmapgen/profiles/` to make it a built-in.

#### 3. Validate the profile

Use the `profiles check` command to validate your TOML before first use:

```bash
python -m tools.pinmapgen.cli profiles --profile-dir ./my_profiles check newchip
```

This runs schema validation (required `schema_version`, types, known keys,
alias targets) and prints a summary of pin counts, peripherals, and warnings.

Use `profiles list` to see all available profiles:

```bash
python -m tools.pinmapgen.cli profiles list
```

#### Schema requirements

Every TOML profile **must** include `schema_version = 1` in the `[profile]`
section. Profiles missing this field will be rejected with a clear error.

Key validation rules:

- `profile.name` must be a safe identifier (`[a-z][a-z0-9_-]*`) and should
  match the filename stem.
- `capabilities` must be `list[str]`, never a bare string.
- Alias targets in `[normalization.aliases]` must resolve to canonical pins
  defined in `[[pins.groups]]` or `[[pins.individual]]`.
- Unknown keys in any section are rejected to prevent typos.

#### Profile resolution priority

When multiple sources provide the same profile name:

1. **Python class** (via `register()`) — always wins.
2. **User TOML** (via `--profile-dir`) — overrides built-in.
3. **Built-in TOML** (in `profiles/`) — base layer.

Within a single directory, two TOML files claiming the same `profile.name`
trigger an error listing both paths.

#### TOML schema reference

See [`tools/pinmapgen/profiles/README.md`](../tools/pinmapgen/profiles/README.md)
for the full schema specification including all capability values, pin naming
conventions, and advanced features.

### Option B — Python profile class (advanced)

For validation logic that cannot be expressed as data, subclass `MCUProfile`
and register it programmatically.

#### 1. Create the profile class

```python
# tools/pinmapgen/newchip_profile.py
from .mcu_profiles import MCUProfile, PinCapability, PinInfo, PeripheralInfo

class NewChipProfile(MCUProfile):
    """Profile for NewChip MCU family."""

    def __init__(self):
        super().__init__("newchip")

    def _initialize_pin_definitions(self):
        for i in range(8):
            self.pins[f"PA{i}"] = PinInfo(
                f"PA{i}", {PinCapability.GPIO, PinCapability.ADC}
            )
            self.pins[f"PB{i}"] = PinInfo(
                f"PB{i}", {PinCapability.GPIO, PinCapability.UART_TX}
            )

    def _initialize_peripherals(self):
        self.peripherals.append(
            PeripheralInfo("UART", 0, {"tx": "PB2", "rx": "PB3"})
        )

    def normalize_pin_name(self, pin_name: str) -> str:
        import re
        clean = pin_name.upper().strip()
        if clean in self.pins:
            return clean
        m = re.match(r"PORT([A-Z])_(\d+)", clean)
        if m:
            canonical = f"P{m.group(1)}{m.group(2)}"
            if canonical in self.pins:
                return canonical
        raise ValueError(f"Cannot normalize '{pin_name}' for NewChip")
```

#### 2. Register it

```python
from tools.pinmapgen.profile_registry import registry
from tools.pinmapgen.newchip_profile import NewChipProfile

registry.register("newchip", NewChipProfile)
```

Python profiles registered this way take priority over any TOML file with
the same name.

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
