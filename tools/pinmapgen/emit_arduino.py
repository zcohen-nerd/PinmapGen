"""
Arduino C++ Header Emitter for PinmapGen.

Generates pinmap_arduino.h files for Arduino/PlatformIO projects with role-aware helpers.
"""

import re
from pathlib import Path
from typing import Any

from . import get_build_datetime
from .naming import sanitize_net_name as _sanitize_net_name
from .pin_metadata import get_pin_comment
from .roles import PinRole, analyze_roles


def emit_arduino_header(
    canonical_dict: dict[str, Any], output_path: Path | str
) -> None:
    """
    Generate Arduino C++ header file from canonical dictionary with role-aware helpers.

    Args:
        canonical_dict: Canonical pinmap dictionary with pins and differential pairs
        output_path: Path to output header file
    """
    # Ensure we have a Path object
    if isinstance(output_path, str):
        output_path = Path(output_path)

    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate header code with role analysis
    code = generate_arduino_with_roles(canonical_dict)

    # Write to file
    with output_path.open("w", encoding="utf-8") as f:
        f.write(code)


def _get_pin_comment(pin: str, canonical_dict: dict[str, Any]) -> str:
    """Get descriptive comment for a pin.

    Wraps :func:`pin_metadata.get_pin_comment` to accept a canonical dict.
    When the canonical dict contains embedded special-function metadata
    (from TOML profiles) that data is used automatically.
    """
    mcu = canonical_dict.get("mcu", "unknown")
    return get_pin_comment(pin, mcu, canonical_dict=canonical_dict)


# Sentinel emitted when a pin has no Arduino pin number on the reference
# board for its MCU (e.g. AVR crystal pins). 255 compiles everywhere and is
# obviously not a usable pin; the #define comment flags it.
_NO_ARDUINO_PIN = "255"

# Arduino Uno mapping (mirrors the D0-D13/A0-A5 aliases in atmega328p.toml).
_UNO_PIN_MAP = {
    "PD0": "0", "PD1": "1", "PD2": "2", "PD3": "3",
    "PD4": "4", "PD5": "5", "PD6": "6", "PD7": "7",
    "PB0": "8", "PB1": "9", "PB2": "10", "PB3": "11",
    "PB4": "12", "PB5": "13",
    "PC0": "A0", "PC1": "A1", "PC2": "A2",
    "PC3": "A3", "PC4": "A4", "PC5": "A5",
}

# Arduino Mega 2560 mapping (standard variant pins_arduino.h, digital 0-53
# then A0-A15). Mirrors the aliases in atmega2560.toml.
_MEGA_DIGITAL = [
    "PE0", "PE1", "PE4", "PE5", "PG5", "PE3", "PH3", "PH4", "PH5", "PH6",
    "PB4", "PB5", "PB6", "PB7", "PJ1", "PJ0", "PH1", "PH0", "PD3", "PD2",
    "PD1", "PD0", "PA0", "PA1", "PA2", "PA3", "PA4", "PA5", "PA6", "PA7",
    "PC7", "PC6", "PC5", "PC4", "PC3", "PC2", "PC1", "PC0", "PD7", "PG2",
    "PG1", "PG0", "PL7", "PL6", "PL5", "PL4", "PL3", "PL2", "PL1", "PL0",
    "PB3", "PB2", "PB1", "PB0",
]
_MEGA_ANALOG = [
    "PF0", "PF1", "PF2", "PF3", "PF4", "PF5", "PF6", "PF7",
    "PK0", "PK1", "PK2", "PK3", "PK4", "PK5", "PK6", "PK7",
]
_MEGA_PIN_MAP = {p: str(i) for i, p in enumerate(_MEGA_DIGITAL)}
_MEGA_PIN_MAP.update({p: f"A{i}" for i, p in enumerate(_MEGA_ANALOG)})

# Arduino Zero mapping (mirrors the D0-D13/A0-A5 aliases in atsamd21.toml,
# plus the Zero's SDA/SCL pins 20/21).
_ZERO_PIN_MAP = {
    "PA11": "0", "PA10": "1", "PA14": "2", "PA09": "3", "PA08": "4",
    "PA15": "5", "PA20": "6", "PA21": "7", "PA06": "8", "PA07": "9",
    "PA18": "10", "PA16": "11", "PA19": "12", "PA17": "13",
    "PA02": "A0", "PB08": "A1", "PB09": "A2",
    "PA04": "A3", "PA05": "A4", "PB02": "A5",
    "PA22": "20", "PA23": "21",
}

# Board pin maps keyed by MCU profile name. atsamd51 is absent on purpose:
# SAMD51 boards (Metro M4, Feather M4, …) each use a different mapping, so
# its pins fall back to _NO_ARDUINO_PIN rather than guessing a board.
_BOARD_PIN_MAPS = {
    "atmega328p": _UNO_PIN_MAP,
    "atmega2560": _MEGA_PIN_MAP,
    "atsamd21": _ZERO_PIN_MAP,
}


def _mcu_family(mcu: str) -> str:
    """Classify an MCU profile name into an Arduino-core family."""
    m = mcu.lower()
    if m.startswith("rp2"):
        return "rp2"
    if m.startswith("esp32"):
        return "esp"
    if m.startswith("stm32"):
        return "stm32"
    if m.startswith("atmega"):
        return "avr"
    if m.startswith("atsamd"):
        return "sam"
    if m.startswith("nrf"):
        return "nrf"
    return "unknown"


def _arduino_pin_literal(pin_name: str, mcu: str = "") -> str:
    """Return the Arduino-compatible pin literal for a given MCU pin name.

    RP2040:   ``GP4``    → ``4``
    ESP32:    ``GPIO21`` → ``21``
    STM32:    ``PA10``   → ``PA10``  (STM32duino defines these as pin numbers)
    nRF52840: ``P0_13``  → ``13``    (port * 32 + pin)
    AVR/SAMD: board map  → ``13`` / ``A4`` (Uno, Mega, Zero mappings)

    Args:
        pin_name: Normalized MCU pin name.
        mcu: MCU profile name, used to select board pin maps.

    Returns:
        Pin literal suitable for an Arduino ``#define`` value.
    """
    token = pin_name.strip().upper()
    if not token:
        return "0"

    family = _mcu_family(mcu)

    # AVR / SAMD: look up the reference-board mapping.
    if family in ("avr", "sam"):
        board_map = _BOARD_PIN_MAPS.get(mcu.lower(), {})
        return board_map.get(token, _NO_ARDUINO_PIN)

    # RP2040: GP<n> → bare number
    rp_match = re.fullmatch(r"GP(\d+)", token)
    if rp_match:
        return rp_match.group(1)

    # ESP32: GPIO<n> → bare number
    gpio_match = re.fullmatch(r"GPIO(\d+)", token)
    if gpio_match:
        return gpio_match.group(1)

    # nRF52840: P<port>_<pin> → flat number (port * 32 + pin)
    nrf_match = re.fullmatch(r"P(\d+)_(\d+)", token)
    if nrf_match:
        port = int(nrf_match.group(1))
        pin = int(nrf_match.group(2))
        return str(port * 32 + pin)

    # STM32: P<port><n> stays as-is — STM32duino cores define PA10 etc.
    # as Arduino pin numbers (PA_10 is the low-level PinName enum, which
    # is the wrong type for pinMode/digitalWrite).
    stm_match = re.fullmatch(r"P([A-Z])(\d+)", token)
    if stm_match:
        return token

    # Fallback: extract first number
    num_match = re.search(r"\d+", token)
    if num_match:
        return num_match.group()

    return "0"


def generate_arduino_with_roles(canonical_dict: dict[str, Any]) -> str:
    """
    Generate enhanced Arduino header with role-aware structures and helpers.

    Args:
        canonical_dict: Canonical pinmap dictionary

    Returns:
        Enhanced C++ header code string
    """
    lines = []

    # Header guard and includes
    guard_name = "PINMAP_ARDUINO_H"
    mcu = canonical_dict.get("mcu", "unknown").upper()
    timestamp = get_build_datetime().strftime("%Y-%m-%d %H:%M:%S")

    lines.extend(
        [
            f"#ifndef {guard_name}",
            f"#define {guard_name}",
            "",
            "/*",
            f" * Auto-generated Arduino pinmap for {mcu}",
            f" * Generated: {timestamp}",
            " * Generator: PinmapGen",
            " *",
            " * This file contains pin definitions, helper structures, and macros",
            " * for easy hardware access in Arduino/PlatformIO projects.",
            " */",
            "",
            "#include <Arduino.h>",
            "",
        ]
    )

    # Analyze roles if pins are available
    if "pins" in canonical_dict:
        # Convert canonical pins format to role analyzer format
        pins_for_analysis = {}
        for net_name, pin_list in canonical_dict["pins"].items():
            pins_for_analysis[net_name] = {
                "pin": pin_list[0] if pin_list else "UNKNOWN",
                "component": canonical_dict.get("mcu", "UNKNOWN"),
                "ref_des": canonical_dict.get("mcu_ref", "UNKNOWN"),
            }

        pin_infos, bus_groups, diff_pairs = analyze_roles(pins_for_analysis)

        # Generate pin constants grouped by role
        lines.extend(
            [
                "// ========================================",
                "// Pin Definitions",
                "// ========================================",
                "",
            ]
        )

        if _mcu_family(canonical_dict.get("mcu", "")) == "nrf":
            lines.extend(
                [
                    "// NOTE: values are raw Nordic pin numbers"
                    " (P0.13 = 13, P1.02 = 34).",
                    "// Cores that use board variant tables (e.g. the"
                    " Adafruit nRF52 core) map",
                    "// Arduino pin numbers differently - translate via your"
                    " board's variant if needed.",
                    "",
                ]
            )

        # Track emitted #define names to avoid collisions
        seen_names: dict[str, int] = {}
        name_lookup: dict[str, str] = {}

        # Nets connected to more than one pin: the #define uses the first
        # pin, so the remaining pins are called out in the comment.
        multi_pin_nets = {
            net: pin_list
            for net, pin_list in canonical_dict["pins"].items()
            if isinstance(pin_list, list) and len(pin_list) > 1
        }

        # Group constants by bus/function
        mcu_name = canonical_dict.get("mcu", "")
        for group_name, pins in bus_groups.items():
            if pins:
                lines.append(f"// {group_name} Pins")
                for pin_info in pins:
                    pin_val = _arduino_pin_literal(pin_info.pin_name, mcu_name)
                    const_name = _sanitize_net_name(
                        pin_info.net_name, seen_names
                    )
                    name_lookup[pin_info.net_name] = const_name
                    comment = f"  // {pin_info.description}"
                    if pin_val == _NO_ARDUINO_PIN:
                        comment += (
                            f" [{pin_info.pin_name}: no Arduino pin mapping"
                            " - replace manually]"
                        )
                    all_pins = multi_pin_nets.get(pin_info.net_name)
                    if all_pins:
                        others = ", ".join(
                            p for p in all_pins if p != pin_info.pin_name
                        )
                        if others:
                            comment += (
                                f" [WARNING: net also connects to {others}]"
                            )
                    lines.append(f"#define {const_name} {pin_val}{comment}")
                lines.append("")

        # Generate differential pair structures
        if diff_pairs:
            lines.extend(
                [
                    "// ========================================",
                    "// Differential Pair Structures",
                    "// ========================================",
                    "",
                ]
            )

            for pair in diff_pairs:
                if pair[0].role == PinRole.USB_DP:
                    pos_const = name_lookup.get(
                        pair[0].net_name, _sanitize_net_name(pair[0].net_name)
                    )
                    neg_const = name_lookup.get(
                        pair[1].net_name, _sanitize_net_name(pair[1].net_name)
                    )

                    lines.extend(
                        [
                            "struct USBPins {",
                            f"    static constexpr uint8_t DP = {pos_const};  // {pair[0].description}",
                            f"    static constexpr uint8_t DN = {neg_const};  // {pair[1].description}",
                            "};",
                            "",
                        ]
                    )

                elif pair[0].role == PinRole.CAN_H:
                    pos_const = name_lookup.get(
                        pair[0].net_name, _sanitize_net_name(pair[0].net_name)
                    )
                    neg_const = name_lookup.get(
                        pair[1].net_name, _sanitize_net_name(pair[1].net_name)
                    )

                    lines.extend(
                        [
                            "struct CANPins {",
                            f"    static constexpr uint8_t H = {pos_const};  // {pair[0].description}",
                            f"    static constexpr uint8_t L = {neg_const};  // {pair[1].description}",
                            "};",
                            "",
                        ]
                    )

        # Generate helper macros
        lines.extend(
            [
                "// ========================================",
                "// Helper Macros",
                "// ========================================",
                "",
            ]
        )

        # Digital I/O macros
        lines.extend(
            [
                "// Digital I/O helpers",
                "#define PIN_INPUT(pin)          pinMode(pin, INPUT)",
                "#define PIN_INPUT_PULLUP(pin)   pinMode(pin, INPUT_PULLUP)",
                "#define PIN_OUTPUT(pin)         pinMode(pin, OUTPUT)",
                "#define READ_PIN(pin)           digitalRead(pin)",
                "#define WRITE_PIN(pin, val)     digitalWrite(pin, val)",
                "",
            ]
        )

        # PWM helper
        family = _mcu_family(mcu_name)
        pwm_pins = [p for p in pin_infos if p.role == PinRole.PWM]
        if pwm_pins:
            pwm_lines = [
                "// PWM helpers",
                "#define PWM_WRITE(pin, val)     analogWrite(pin, val)",
            ]
            if family == "rp2":
                pwm_lines.append(
                    "#define PWM_FREQ(pin, freq)     analogWriteFreq(freq)"
                )
            pwm_lines.append("")
            lines.extend(pwm_lines)

        # ADC helper — voltage math depends on the core's default reference
        # and analogRead resolution.
        adc_pins = [p for p in pin_infos if p.role == PinRole.ADC]
        if adc_pins:
            if family == "avr":
                adc_expr = "(analogRead(pin) * 5.0f / 1023.0f)"
                adc_note = "// 5 V reference, 10-bit analogRead"
            elif family == "esp":
                adc_expr = "(analogRead(pin) * 3.3f / 4095.0f)"
                adc_note = "// 3.3 V reference, 12-bit analogRead (ESP32 default)"
            else:
                # RP2040, STM32, SAMD, nRF cores default analogRead to 10-bit.
                adc_expr = "(analogRead(pin) * 3.3f / 1023.0f)"
                adc_note = "// 3.3 V reference, 10-bit analogRead (core default)"
            lines.extend(
                [
                    "// ADC helpers",
                    "#define ADC_READ(pin)           analogRead(pin)",
                    f"#define ADC_READ_VOLTAGE(pin)   {adc_expr}  {adc_note}",
                    "",
                ]
            )

        # Bus setup helpers
        i2c_groups = {k: v for k, v in bus_groups.items() if k.startswith("I2C")}
        if i2c_groups:
            lines.extend(
                [
                    "// I2C setup helpers",
                    "#include <Wire.h>",
                ]
            )

            for i2c_name, pins in i2c_groups.items():
                sda_pin = next((p for p in pins if p.role == PinRole.I2C_SDA), None)
                scl_pin = next((p for p in pins if p.role == PinRole.I2C_SCL), None)

                if sda_pin and scl_pin:
                    func_name = f"SETUP_{i2c_name}"
                    sda_const = name_lookup.get(
                        sda_pin.net_name, _sanitize_net_name(sda_pin.net_name)
                    )
                    scl_const = name_lookup.get(
                        scl_pin.net_name, _sanitize_net_name(scl_pin.net_name)
                    )

                    if family in ("rp2", "stm32"):
                        # Philhower RP2040 and STM32duino support pin remap
                        # via Wire.setSDA/setSCL.
                        body = [
                            f"        Wire.setSDA({sda_const}); \\",
                            f"        Wire.setSCL({scl_const}); \\",
                            "        Wire.begin(); \\",
                            "        Wire.setClock(freq); \\",
                        ]
                    elif family == "esp":
                        body = [
                            f"        Wire.begin({sda_const}, {scl_const}, freq); \\",
                        ]
                    else:
                        # AVR / SAMD / nRF cores use fixed board I2C pins.
                        body = [
                            "        /* I2C pins are fixed by the board"
                            " variant on this core */ \\",
                            "        Wire.begin(); \\",
                            "        Wire.setClock(freq); \\",
                        ]

                    lines.extend(
                        [
                            f"#define {func_name}(freq) \\",
                            "    do { \\",
                            *body,
                            "    } while (0)",
                            "",
                        ]
                    )

        # SPI setup helpers
        spi_groups = {k: v for k, v in bus_groups.items() if k.startswith("SPI")}
        if spi_groups:
            lines.extend(
                [
                    "// SPI setup helpers",
                    "#include <SPI.h>",
                ]
            )

            for spi_name, pins in spi_groups.items():
                mosi_pin = next((p for p in pins if p.role == PinRole.SPI_MOSI), None)
                miso_pin = next((p for p in pins if p.role == PinRole.SPI_MISO), None)
                sck_pin = next((p for p in pins if p.role == PinRole.SPI_SCK), None)

                if mosi_pin and miso_pin and sck_pin:
                    func_name = f"SETUP_{spi_name}"
                    mosi_const = name_lookup.get(
                        mosi_pin.net_name, _sanitize_net_name(mosi_pin.net_name)
                    )
                    miso_const = name_lookup.get(
                        miso_pin.net_name, _sanitize_net_name(miso_pin.net_name)
                    )
                    sck_const = name_lookup.get(
                        sck_pin.net_name, _sanitize_net_name(sck_pin.net_name)
                    )

                    if family == "rp2":
                        body = [
                            f"        SPI.setMOSI({mosi_const}); \\",
                            f"        SPI.setMISO({miso_const}); \\",
                            f"        SPI.setSCK({sck_const}); \\",
                            "        SPI.begin(); \\",
                        ]
                    elif family == "stm32":
                        # STM32duino names the clock setter setSCLK.
                        body = [
                            f"        SPI.setMOSI({mosi_const}); \\",
                            f"        SPI.setMISO({miso_const}); \\",
                            f"        SPI.setSCLK({sck_const}); \\",
                            "        SPI.begin(); \\",
                        ]
                    elif family == "esp":
                        body = [
                            f"        SPI.begin({sck_const}, {miso_const}, {mosi_const}); \\",
                        ]
                    else:
                        # AVR / SAMD / nRF cores use fixed board SPI pins.
                        body = [
                            "        /* SPI pins are fixed by the board"
                            " variant on this core */ \\",
                            "        SPI.begin(); \\",
                        ]

                    lines.extend(
                        [
                            f"#define {func_name}() \\",
                            "    do { \\",
                            *body,
                            "    } while (0)",
                            "",
                        ]
                    )

    else:
        # Fallback if no pin data
        lines.extend(
            [
                "// No pin data available",
                "// Please check your netlist input",
                "",
            ]
        )

    # Close header guard
    lines.extend(
        [
            f"#endif // {guard_name}",
            "",
        ]
    )

    return "\n".join(lines)
