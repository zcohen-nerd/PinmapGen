"""
Arduino C++ Header Emitter for PinmapGen.

Generates pinmap_arduino.h files for Arduino/PlatformIO projects with role-aware helpers.
"""

import re
from pathlib import Path
from typing import Any

from . import get_build_datetime
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


def _sanitize_net_name(
    net_name: str, seen_names: dict[str, int] | None = None
) -> str:
    """Sanitize net name for use as C++ macro.

    Args:
        net_name: Raw net name from netlist.
        seen_names: Optional dict tracking previously emitted names.
            When provided, duplicate sanitized names receive ``_2``, ``_3``,
            etc. suffixes to avoid collisions.

    Returns:
        Sanitized macro name (uppercase).
    """
    # Remove invalid characters and replace with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", net_name)

    # Prefix leading digits with underscore (preserves names like 3V3)
    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized

    # Remove consecutive underscores
    sanitized = re.sub(r"_{2,}", "_", sanitized)

    # Remove trailing underscores only (keep leading _ for digit-prefixed names)
    sanitized = sanitized.rstrip("_")

    # Handle empty or invalid names
    if not sanitized or sanitized == "_":
        sanitized = "UNNAMED_PIN"

    result = sanitized.upper()

    # Collision detection: append _2, _3, … when a tracker is provided
    if seen_names is not None:
        count = seen_names.get(result, 0) + 1
        seen_names[result] = count
        if count > 1:
            result = f"{result}_{count}"

    return result


def _get_pin_comment(pin: str, canonical_dict: dict[str, Any]) -> str:
    """Get descriptive comment for a pin.

    Wraps :func:`pin_metadata.get_pin_comment` to accept a canonical dict.
    When the canonical dict contains embedded special-function metadata
    (from TOML profiles) that data is used automatically.
    """
    mcu = canonical_dict.get("mcu", "unknown")
    return get_pin_comment(pin, mcu, canonical_dict=canonical_dict)


def _arduino_pin_literal(pin_name: str) -> str:
    """Return the Arduino-compatible pin literal for a given MCU pin name.

    RP2040:   ``GP4``    → ``4``
    ESP32:    ``GPIO21`` → ``21``
    STM32:    ``PA10``   → ``PA_10``
    nRF52840: ``P0_13``  → ``13``   (port * 32 + pin)

    Args:
        pin_name: Normalized MCU pin name.

    Returns:
        Pin literal suitable for an Arduino ``#define`` value.
    """
    token = pin_name.strip().upper()
    if not token:
        return "0"

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

    # STM32 / AVR / SAM: P<port><n> → P<port>_<n>
    stm_match = re.fullmatch(r"P([A-Z])(\d+)", token)
    if stm_match:
        return f"P{stm_match.group(1)}_{stm_match.group(2)}"

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

        # Track emitted #define names to avoid collisions
        seen_names: dict[str, int] = {}
        name_lookup: dict[str, str] = {}

        # Group constants by bus/function
        for group_name, pins in bus_groups.items():
            if pins:
                lines.append(f"// {group_name} Pins")
                for pin_info in pins:
                    pin_val = _arduino_pin_literal(pin_info.pin_name)
                    const_name = _sanitize_net_name(
                        pin_info.net_name, seen_names
                    )
                    name_lookup[pin_info.net_name] = const_name
                    comment = f"  // {pin_info.description}"
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
        pwm_pins = [p for p in pin_infos if p.role == PinRole.PWM]
        if pwm_pins:
            lines.extend(
                [
                    "// PWM helpers",
                    "#define PWM_WRITE(pin, val)     analogWrite(pin, val)",
                    "#define PWM_FREQ(pin, freq)     analogWriteFreq(freq)  // ESP32/RP2040",
                    "",
                ]
            )

        # ADC helper
        adc_pins = [p for p in pin_infos if p.role == PinRole.ADC]
        if adc_pins:
            lines.extend(
                [
                    "// ADC helpers",
                    "#define ADC_READ(pin)           analogRead(pin)",
                    "#define ADC_READ_VOLTAGE(pin)   (analogRead(pin) * 3.3f / 4095.0f)",
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

                    lines.extend(
                        [
                            f"#define {func_name}(freq) \\",
                            f"    Wire.setSDA({sda_const}); \\",
                            f"    Wire.setSCL({scl_const}); \\",
                            "    Wire.setClock(freq); \\",
                            "    Wire.begin()",
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

                    lines.extend(
                        [
                            f"#define {func_name}(freq) \\",
                            f"    SPI.setMOSI({mosi_const}); \\",
                            f"    SPI.setMISO({miso_const}); \\",
                            f"    SPI.setSCK({sck_const}); \\",
                            "    SPI.begin(); \\",
                            "    SPI.setClockDivider(SPI_CLOCK_DIV2)",
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
