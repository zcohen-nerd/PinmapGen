"""
MicroPython emitter for PinmapGen.

Generate pinmap_micropython.py files with helper utilities.
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .roles import PinRole, analyze_roles


def emit_micropython(
    canonical_dict: dict[str, Any],
    output_path: Path | str,
) -> None:
    """
    Generate MicroPython pinmap with helper utilities.

    Args:
        canonical_dict: Canonical pinmap dictionary containing pin data.
        output_path: Filesystem location for the emitted Python module.
    """
    # Ensure we have a Path object
    if isinstance(output_path, str):
        output_path = Path(output_path)

    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate MicroPython code with role analysis
    code = generate_micropython_with_roles(canonical_dict)

    # Write to file
    with output_path.open("w", encoding="utf-8") as f:
        f.write(code)


def generate_micropython_constants(canonical_dict: dict[str, Any]) -> str:
    """
    Generate MicroPython pin constant definitions from canonical dictionary.
    
    Args:
        canonical_dict: Canonical pinmap dictionary
        
    Returns:
        MicroPython code string
    """
    lines = []

    # File header
    mcu = canonical_dict.get("mcu", "unknown").upper()
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S %Z")

    lines.extend([
        '"""',
        f"Auto-generated MicroPython pinmap for {mcu}.",
        f"Generated: {timestamp}",
        "Generator: PinmapGen",
        "",
        "Pin constants for easy hardware access.",
        '"""',
        "",
    ])

    # Generate pin constants
    if "pins" in canonical_dict:
        lines.append("# Pin Constants")

        # Sort pins by net name for consistent output
        sorted_pins = sorted(canonical_dict["pins"].items())
        mcu = canonical_dict.get("mcu", "")

        for net_name, pin_entry in sorted_pins:
            pin_name = _extract_primary_pin(pin_entry)
            if not pin_name:
                continue

            const_name = _sanitize_net_name(net_name)
            comment = _get_pin_comment(pin_name)
            literal = _micropython_pin_literal(pin_name)
            lines.append(f"{const_name} = {literal}  # {comment}")

        lines.append("")

    # Generate differential pairs if present
    if canonical_dict.get("differential_pairs"):
        lines.append("# Differential Pairs")

        pins = canonical_dict.get("pins", {})
        mcu = canonical_dict.get("mcu", "")

        for pair in canonical_dict["differential_pairs"]:
            pos_net = pair.get("positive")
            neg_net = pair.get("negative")
            if not pos_net or not neg_net:
                continue

            pos_pin = _extract_primary_pin(pins.get(pos_net))
            neg_pin = _extract_primary_pin(pins.get(neg_net))
            if not pos_pin or not neg_pin:
                continue

            pair_const = _sanitize_net_name(f"{pos_net}_{neg_net}")
            pos_literal = _micropython_pin_literal(pos_pin)
            neg_literal = _micropython_pin_literal(neg_pin)
            lines.append(
                f"{pair_const}_POS = {pos_literal}  # {pos_pin}"
            )
            lines.append(
                f"{pair_const}_NEG = {neg_literal}  # {neg_pin}"
            )

        lines.append("")

    return "\n".join(lines)


def _sanitize_net_name(net_name: str) -> str:
    """
    Sanitize net name for use as Python constant.
    
    Args:
        net_name: Raw net name from netlist
        
    Returns:
        Sanitized constant name
    """
    # Remove invalid characters and replace with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", net_name)

    # Remove leading digits
    sanitized = re.sub(r"^[0-9]+", "", sanitized)

    # Remove consecutive underscores
    sanitized = re.sub(r"_{2,}", "_", sanitized)

    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")

    # Handle empty or invalid names
    if not sanitized or sanitized == "_":
        sanitized = "UNNAMED_PIN"

    return sanitized.upper()


def _extract_primary_pin(pin_entry: Any) -> str | None:
    """Pull the primary pin string from a canonical pin entry."""
    if not pin_entry:
        return None

    if isinstance(pin_entry, dict):
        pin_value = pin_entry.get("pin")
        if isinstance(pin_value, str) and pin_value:
            return pin_value

        pins = pin_entry.get("pins")
        if isinstance(pins, list) and pins:
            candidate = pins[0]
            return candidate if isinstance(candidate, str) else str(candidate)

    if isinstance(pin_entry, list) and pin_entry:
        candidate = pin_entry[0]
        return candidate if isinstance(candidate, str) else str(candidate)

    if isinstance(pin_entry, str) and pin_entry:
        return pin_entry

    return None


def _micropython_pin_literal(pin_name: str) -> str:
    """Return the literal best suited for MicroPython Pin constructors."""
    token = pin_name.strip().upper()
    if not token:
        return '"UNKNOWN_PIN"'

    rp_match = re.fullmatch(r"GP(\d+)", token)
    if rp_match:
        return str(int(rp_match.group(1)))

    gpio_match = re.fullmatch(r"GPIO(\d+)", token)
    if gpio_match:
        return f'"GPIO{gpio_match.group(1)}"'

    stm_match = re.fullmatch(r"P[A-Z]\d+", token)
    if stm_match:
        return f'"{token}"'

    if token.isdigit():
        return token

    return f'"{pin_name}"'


def _get_pin_comment(pin: str) -> str:
    """
    Get descriptive comment for a pin.

    Args:
        pin: Pin name (e.g., 'GP24').

    Returns:
        Human-readable comment string used in emitted constants.
    """
    comments = [pin]  # Always include the pin name

    # Add special function information
    special_functions = {
        "GP24": "USB D-",
        "GP25": "USB D+",
        "GP26": "ADC0",
        "GP27": "ADC1",
        "GP28": "ADC2",
        "GP29": "ADC3",
        "GP23": "SMPS_MODE"
    }

    if pin in special_functions:
        comments.append(special_functions[pin])

    return " - ".join(comments)


def generate_micropython_with_roles(canonical_dict: dict[str, Any]) -> str:
    """
    Generate enhanced MicroPython pinmap with role-aware helper functions.

    Args:
        canonical_dict: Canonical pinmap dictionary.

    Returns:
        Enhanced MicroPython code string.
    """
    lines = []
    lines.extend(_render_file_header(canonical_dict))

    if "pins" not in canonical_dict:
        lines.extend(_render_no_pin_data())
        return "\n".join(lines)

    pins_for_analysis = _prepare_pins_for_analysis(canonical_dict)
    pin_infos, bus_groups, diff_pairs = analyze_roles(pins_for_analysis)

    lines.extend(_render_pin_constants(bus_groups))
    lines.extend(
        _render_helper_functions(pin_infos, bus_groups, diff_pairs),
    )

    return "\n".join(lines)


def _render_file_header(canonical_dict: dict[str, Any]) -> list[str]:
    mcu = canonical_dict.get("mcu", "unknown").upper()
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S %Z")
    return [
        '"""',
        f"Auto-generated MicroPython pinmap for {mcu}.",
        f"Generated: {timestamp}",
        "Generator: PinmapGen",
        "",
        "This file bundles pin constants and helper utilities.",
        "Use them to quickly access hardware in MicroPython.",
        '"""',
        "",
        "from machine import Pin, I2C, SPI, PWM, ADC",
        "",
    ]


def _render_no_pin_data() -> list[str]:
    return [
        "# No pin data available",
        "# Please check your netlist input",
        "",
    ]


def _prepare_pins_for_analysis(
    canonical_dict: dict[str, Any],
) -> dict[str, Any]:
    pins_for_analysis: dict[str, Any] = {}
    component = canonical_dict.get("mcu", "UNKNOWN")
    ref_des = canonical_dict.get("mcu_ref", "UNKNOWN")

    for net_name, pin_entry in canonical_dict["pins"].items():
        pins_for_analysis[net_name] = {
            "pin": _extract_primary_pin(pin_entry) or "UNKNOWN",
            "component": component,
            "ref_des": ref_des,
        }

    return pins_for_analysis


def _render_pin_constants(bus_groups: dict[str, list[Any]]) -> list[str]:
    if not any(bus_groups.values()):
        return []

    lines = [
        "# ========================================",
        "# Pin Constants",
        "# ========================================",
        "",
    ]

    for group_name, pins in bus_groups.items():
        if not pins:
            continue
        lines.append(f"# {group_name} Pins")
        for pin_info in pins:
            const_name = _sanitize_net_name(pin_info.net_name)
            descriptor = f"{pin_info.description} ({pin_info.pin_name})"
            literal = _micropython_pin_literal(pin_info.pin_name)
            lines.append(f"{const_name} = {literal}  # {descriptor}")
        lines.append("")

    return lines


def _render_helper_functions(
    pin_infos: list[Any],
    bus_groups: dict[str, list[Any]],
    diff_pairs: list[Any],
) -> list[str]:
    lines = [
        "# ========================================",
        "# Helper Functions",
        "# ========================================",
        "",
    ]

    lines.extend(_digital_helpers())
    lines.extend(_adc_helper(pin_infos))
    lines.extend(_pwm_helper(pin_infos))
    lines.extend(_i2c_helpers(bus_groups))
    lines.extend(_spi_helpers(bus_groups))
    lines.extend(_diff_pair_helpers(diff_pairs))

    return lines


def _digital_helpers() -> list[str]:
    return [
        "def pin_in(pin_num, pull=None):",
        '    """Create a digital input with optional pull resistor."""',
        "    return Pin(pin_num, Pin.IN, pull)",
        "",
        "def pin_out(pin_num, value=0):",
        '    """Create a digital output pin with initial value."""',
        "    return Pin(pin_num, Pin.OUT, value=value)",
        "",
    ]


def _adc_helper(pin_infos: list[Any]) -> list[str]:
    if not any(pin.role == PinRole.ADC for pin in pin_infos):
        return []

    return [
        "def adc(pin_num):",
        '    """Create an ADC object for analog reading."""',
        "    return ADC(Pin(pin_num))",
        "",
    ]


def _pwm_helper(pin_infos: list[Any]) -> list[str]:
    if not any(pin.role == PinRole.PWM for pin in pin_infos):
        return []

    return [
        "def pwm(pin_num, freq=1000):",
        '    """Create a PWM object with specified frequency."""',
        "    return PWM(Pin(pin_num), freq=freq)",
        "",
    ]


def _i2c_helpers(bus_groups: dict[str, list[Any]]) -> list[str]:
    helpers: list[str] = []
    for i2c_name, pins in bus_groups.items():
        if not i2c_name.startswith("I2C"):
            continue

        sda_pin = next(
            (pin for pin in pins if pin.role == PinRole.I2C_SDA),
            None,
        )
        scl_pin = next(
            (pin for pin in pins if pin.role == PinRole.I2C_SCL),
            None,
        )

        if not (sda_pin and scl_pin):
            continue

        i2c_num = i2c_name.replace("I2C", "").lower() or "0"
        func_name = f"setup_{i2c_name.lower()}"
        sda_const = _sanitize_net_name(sda_pin.net_name)
        scl_const = _sanitize_net_name(scl_pin.net_name)

        helper_doc = (
            f"Setup {i2c_name} with SDA={sda_pin.pin_name}, "
            f"SCL={scl_pin.pin_name}."
        )
        helpers.extend([
            f"def {func_name}(freq=400000):",
            f'    """{helper_doc}"""',
            "    return I2C(",
            f"        {i2c_num},",
            f"        sda=Pin({sda_const}),",
            f"        scl=Pin({scl_const}),",
            "        freq=freq,",
            "    )",
            "",
        ])

    return helpers


def _spi_helpers(bus_groups: dict[str, list[Any]]) -> list[str]:
    helpers: list[str] = []
    for spi_name, pins in bus_groups.items():
        if not spi_name.startswith("SPI"):
            continue

        mosi_pin = next(
            (pin for pin in pins if pin.role == PinRole.SPI_MOSI),
            None,
        )
        miso_pin = next(
            (pin for pin in pins if pin.role == PinRole.SPI_MISO),
            None,
        )
        sck_pin = next(
            (pin for pin in pins if pin.role == PinRole.SPI_SCK),
            None,
        )

        if not (mosi_pin and miso_pin and sck_pin):
            continue

        spi_num = spi_name.replace("SPI", "").lower() or "0"
        func_name = f"setup_{spi_name.lower()}"
        mosi_const = _sanitize_net_name(mosi_pin.net_name)
        miso_const = _sanitize_net_name(miso_pin.net_name)
        sck_const = _sanitize_net_name(sck_pin.net_name)

        helper_doc = (
            f"Setup {spi_name} with MOSI={mosi_pin.pin_name}, "
            f"MISO={miso_pin.pin_name}, SCK={sck_pin.pin_name}."
        )
        helpers.extend([
            f"def {func_name}(baudrate=1_000_000):",
            f'    """{helper_doc}"""',
            "    return SPI(",
            f"        {spi_num},",
            f"        mosi=Pin({mosi_const}),",
            f"        miso=Pin({miso_const}),",
            f"        sck=Pin({sck_const}),",
            "        baudrate=baudrate,",
            "    )",
            "",
        ])

    return helpers


def _diff_pair_helpers(diff_pairs: list[Any]) -> list[str]:
    body: list[str] = []
    for pair in diff_pairs:
        if pair[0].role != PinRole.USB_DP:
            continue

        pos_const = _sanitize_net_name(pair[0].net_name)
        neg_const = _sanitize_net_name(pair[1].net_name)

        body.extend([
            "class USBPins:",
            '    """USB differential pair pin definitions."""',
            f"    DP = {pos_const}  # {pair[0].description}",
            f"    DN = {neg_const}  # {pair[1].description}",
            "",
            "    @classmethod",
            "    def get_pair(cls):",
            '        """Get USB D+/D- pin tuple."""',
            "        return (cls.DP, cls.DN)",
            "",
        ])

    if not body:
        return []

    header = [
        "# ========================================",
        "# Differential Pair Classes",
        "# ========================================",
        "",
    ]
    return header + body
