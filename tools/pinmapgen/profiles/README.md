# PinmapGen MCU Profiles

This directory contains **TOML-based MCU profile definitions** that PinmapGen
uses to normalise, validate, and emit pin mappings for different
microcontrollers.

## Quick start — using built-in profiles

PinmapGen ships with profiles for these MCUs:

| Profile name  | MCU                | Family |
|---------------|--------------------|--------|
| `rp2040`      | Raspberry Pi RP2040 | rp2    |
| `rp2350`      | Raspberry Pi RP2350 | rp2    |
| `esp32`       | Espressif ESP32     | esp    |
| `esp32s3`     | Espressif ESP32-S3  | esp    |
| `esp32c3`     | Espressif ESP32-C3  | esp    |
| `stm32g0`     | ST STM32G071       | stm32  |
| `stm32f411`   | ST STM32F411       | stm32  |
| `stm32h743`   | ST STM32H743       | stm32  |
| `nrf52840`    | Nordic nRF52840    | nrf    |
| `atmega328p`  | Microchip ATmega328P | avr  |
| `atmega2560`  | Microchip ATmega2560 | avr  |
| `atsamd21`    | Microchip ATSAMD21 | sam    |
| `atsamd51`    | Microchip ATSAMD51 | sam    |

List them at any time:

```bash
python -m tools.pinmapgen.cli --list-mcus
```

---

## Creating your own profile

Drop a `.toml` file into a directory and point PinmapGen at it:

```bash
python -m tools.pinmapgen.cli \
  --csv netlist.csv --mcu my_mcu --mcu-ref U1 \
  --profile-dir ./my_profiles
```

### Minimal profile

```toml
[profile]
schema_version = 1
name = "my_mcu"
display_name = "My Custom MCU"
description = "A custom MCU for my project"

[normalization]
canonical_prefix = "P"
allow_numeric = true

[[normalization.patterns]]
regex  = "GPIO(\\d+)"
output = "P{0}"

[[pins.groups]]
range        = { prefix = "P", start = 0, end = 15 }
capabilities = ["gpio"]
```

That's it — 14 lines. PinmapGen will normalise `GPIO5` → `P5`, accept bare
`5` → `P5`, validate pin assignments, and emit all output formats.

### Full profile schema

```toml
# ── Profile metadata ──────────────────────────────────────────────────────
[profile]
schema_version = 1               # REQUIRED — must be 1
name         = "my_mcu"          # CLI identifier (lowercase, no spaces)
display_name = "My MCU"          # Human-readable name
description  = "Short blurb"    # Optional description
family       = "custom"          # Optional family tag

# ── Pin name normalisation ────────────────────────────────────────────────
[normalization]
canonical_prefix = "P"           # Prefix for canonical pin names
allow_numeric    = true          # Accept bare numbers ("0" → "P0")

# Regex patterns (tried in order, first match wins).
# Capture groups → {0}, {1}, … in output template.
# {n:0W} zero-pads group n to width W — use when canonical names are
# zero-padded (e.g. output "P{0}_{1:02}" turns P0.5 into P0_05).
[[normalization.patterns]]
regex  = "GPIO(\\d+)"
output = "P{0}"

# Direct name aliases (keys are matched case-insensitively).
[normalization.aliases]
RESET = "P0"
LED   = "P13"

# ── Pin definitions ───────────────────────────────────────────────────────

# Groups: many pins with the same capabilities.
# Use 'range' for sequential pins or 'names' for an explicit list.
[[pins.groups]]
range        = { prefix = "P", start = 0, end = 7 }
capabilities = ["gpio", "pwm"]

[[pins.groups]]
names        = ["P8", "P9", "P10"]
capabilities = ["gpio", "adc"]

# Individual pins: add/override capabilities, set special-function info.
[[pins.individual]]
name                   = "P0"
add_capabilities       = ["uart_rx"]     # added on top of group caps
special_function       = "Reset Pin"     # verbose (docs, markdown)
special_function_short = "RESET"         # concise (code comments)
warnings               = ["P0 is used for reset by default"]

# To REPLACE (not extend) capabilities, use 'capabilities' instead:
# [[pins.individual]]
# name         = "P15"
# capabilities = ["gpio"]

# ── Peripherals ───────────────────────────────────────────────────────────
[[peripherals]]
name     = "UART"
instance = 0
pins     = { tx = "P1", rx = "P0" }

[[peripherals]]
name     = "SPI"
instance = 0
pins     = { mosi = "configurable", miso = "configurable", sck = "configurable" }
```

### Capability values

Use any of these lowercase strings in the `capabilities` /
`add_capabilities` arrays:

| Value       | Meaning            |
|-------------|--------------------|
| `gpio`      | General-purpose I/O |
| `adc`       | Analog-to-digital   |
| `dac`       | Digital-to-analog   |
| `pwm`       | PWM output          |
| `i2c_sda`   | I²C data            |
| `i2c_scl`   | I²C clock           |
| `spi_mosi`  | SPI MOSI            |
| `spi_miso`  | SPI MISO            |
| `spi_sck`   | SPI clock           |
| `spi_cs`    | SPI chip-select     |
| `uart_tx`   | UART transmit       |
| `uart_rx`   | UART receive        |
| `can_tx`    | CAN transmit        |
| `can_rx`    | CAN receive         |
| `usb_dp`    | USB D+              |
| `usb_dm`    | USB D−              |
| `i2s_data`  | I²S data            |
| `i2s_bclk`  | I²S bit clock       |
| `i2s_lrclk` | I²S L/R clock       |

### Pin naming conventions

| MCU family | Canonical format | Example  |
|------------|------------------|----------|
| RP2040/2350 | `GP<n>`         | `GP0`    |
| ESP32      | `GPIO<n>`        | `GPIO21` |
| STM32      | `P<port><n>`     | `PA13`   |
| nRF52      | `P<port>_<pin>`  | `P0_13`  |
| AVR        | `P<port><n>`     | `PB5`    |
| SAM        | `P<port><nn>`    | `PA02`   |

### Tips

- **Start small.** You only need `[profile]`, `[normalization]`, and one
  `[[pins.groups]]` to get a working profile.
- **Capabilities are additive** with `add_capabilities` on individual pins.
  Use `capabilities` (without the `add_` prefix) to fully replace the set
  inherited from a group.
- **Regex patterns** use Python `re` syntax. Backslashes must be doubled in
  TOML (`\\d+`).
- **Test before using.** Run `profiles check my_mcu` to validate your profile,
  then generate output with `--verbose` to see which pins were normalised.
- **`schema_version = 1` is required.** Profiles without it are rejected
  with a clear error message.
- **Unknown keys are rejected.** Typos like `capabilties` (missing 'i') are
  caught immediately.

---

## Advanced: Python profile classes

For validation logic that cannot be expressed as data (e.g., complex
cross-pin checks), you can still subclass `MCUProfile` in Python.  Register
it programmatically:

```python
from tools.pinmapgen.profile_registry import registry
from tools.pinmapgen.mcu_profiles import MCUProfile

class MyCustomProfile(MCUProfile):
    ...

registry.register("my_mcu", MyCustomProfile)
```

Python profiles registered this way take priority over any TOML file with
the same name.
