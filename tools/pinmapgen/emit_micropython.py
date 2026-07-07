"""
MicroPython emitter for PinmapGen.

Generate pinmap_micropython.py files with helper utilities.
"""

import re
from pathlib import Path
from typing import Any

from . import get_build_datetime
from .naming import sanitize_net_name as _sanitize_net_name
from .pin_metadata import get_pin_comment
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

    # RP2040 / RP2350: GP<n> → bare int
    rp_match = re.fullmatch(r"GP(\d+)", token)
    if rp_match:
        return str(int(rp_match.group(1)))

    # ESP32 family: GPIO<n> → bare int (the MicroPython esp32 port only
    # accepts integer pin ids; Pin("GPIO21") raises ValueError)
    gpio_match = re.fullmatch(r"GPIO(\d+)", token)
    if gpio_match:
        return str(int(gpio_match.group(1)))

    # nRF52840: P<port>_<pin> → "P<port>.<pin>" (MicroPython nrf port)
    nrf_match = re.fullmatch(r"P(\d+)_(\d+)", token)
    if nrf_match:
        return f'"P{nrf_match.group(1)}.{nrf_match.group(2)}"'

    # STM32 / AVR / SAM: P<letter><n> → quoted string
    stm_match = re.fullmatch(r"P[A-Z]\d+", token)
    if stm_match:
        return f'"{token}"'

    if token.isdigit():
        return token

    return f'"{pin_name}"'


# _get_pin_comment is now in pin_metadata.py as get_pin_comment
_get_pin_comment = get_pin_comment


def generate_micropython_with_roles(canonical_dict: dict[str, Any]) -> str:
    """
    Generate enhanced MicroPython pinmap with role-aware helper functions.

    Args:
        canonical_dict: Canonical pinmap dictionary.

    Returns:
        Enhanced MicroPython code string.
    """
    lines = []

    if "pins" not in canonical_dict:
        lines.extend(_render_file_header(canonical_dict, set()))
        lines.extend(_render_no_pin_data())
        return "\n".join(lines)

    pins_for_analysis = _prepare_pins_for_analysis(canonical_dict)
    pin_infos, bus_groups, diff_pairs = analyze_roles(pins_for_analysis)

    # Nets connected to more than one pin: the constant uses the first pin,
    # so the remaining pins are called out in the comment.
    multi_pin_nets = {
        net: pins
        for net, pins in canonical_dict["pins"].items()
        if isinstance(pins, list) and len(pins) > 1
    }

    # Determine which machine imports are actually needed
    needed_imports = _determine_machine_imports(bus_groups)
    lines.extend(_render_file_header(canonical_dict, needed_imports))

    const_lines, name_lookup = _render_pin_constants(bus_groups, multi_pin_nets)
    lines.extend(const_lines)
    lines.extend(
        _render_helper_functions(pin_infos, bus_groups, diff_pairs, name_lookup),
    )

    return "\n".join(lines)


def _determine_machine_imports(bus_groups: dict[str, list[Any]]) -> set[str]:
    """Determine which ``machine`` module imports are actually needed."""
    imports: set[str] = {"Pin"}  # Pin is always needed
    group_prefix_to_import = {
        "I2C": "I2C",
        "SPI": "SPI",
        "PWM": "PWM",
        "ANALOG": "ADC",
    }
    for group_name, pins in bus_groups.items():
        if not pins:
            continue

        upper_name = group_name.upper()
        for prefix, import_name in group_prefix_to_import.items():
            if upper_name.startswith(prefix):
                imports.add(import_name)
                break
    return imports


def _render_file_header(
    canonical_dict: dict[str, Any],
    needed_imports: set[str] | None = None,
) -> list[str]:
    mcu = canonical_dict.get("mcu", "unknown").upper()
    timestamp = get_build_datetime().strftime("%Y-%m-%d %H:%M:%S %Z")
    if needed_imports is None:
        needed_imports = {"Pin", "I2C", "SPI", "PWM", "ADC"}
    # Stable import order
    ordered = [m for m in ("Pin", "I2C", "SPI", "PWM", "ADC") if m in needed_imports]
    import_line = f"from machine import {', '.join(ordered)}"
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
        import_line,
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


def _render_pin_constants(
    bus_groups: dict[str, list[Any]],
    multi_pin_nets: dict[str, list[str]] | None = None,
) -> tuple[list[str], dict[str, str]]:
    """Render pin constant assignments and return a name lookup table.

    Args:
        bus_groups: Pins grouped by bus/function.
        multi_pin_nets: Optional map of net name → full pin list for nets
            connected to more than one pin. The constant uses the first
            pin; the others are flagged in the comment.

    Returns:
        A tuple of ``(lines, name_lookup)`` where *name_lookup* maps each
        original net name to the (possibly collision-suffixed) constant name
        that was emitted.
    """
    if multi_pin_nets is None:
        multi_pin_nets = {}
    name_lookup: dict[str, str] = {}
    if not any(bus_groups.values()):
        return [], name_lookup

    lines = [
        "# ========================================",
        "# Pin Constants",
        "# ========================================",
        "",
    ]

    # Track emitted constant names to avoid collisions
    seen_names: dict[str, int] = {}

    for group_name, pins in bus_groups.items():
        if not pins:
            continue
        lines.append(f"# {group_name} Pins")
        for pin_info in pins:
            const_name = _sanitize_net_name(pin_info.net_name, seen_names)
            name_lookup[pin_info.net_name] = const_name
            descriptor = f"{pin_info.description} ({pin_info.pin_name})"
            all_pins = multi_pin_nets.get(pin_info.net_name)
            if all_pins:
                others = ", ".join(
                    p for p in all_pins if p != pin_info.pin_name
                )
                if others:
                    descriptor += (
                        f" [WARNING: net also connects to {others}]"
                    )
            literal = _micropython_pin_literal(pin_info.pin_name)
            lines.append(f"{const_name} = {literal}  # {descriptor}")
        lines.append("")

    return lines, name_lookup


def _render_helper_functions(
    pin_infos: list[Any],
    bus_groups: dict[str, list[Any]],
    diff_pairs: list[Any],
    name_lookup: dict[str, str] | None = None,
) -> list[str]:
    if name_lookup is None:
        name_lookup = {}
    lines = [
        "# ========================================",
        "# Helper Functions",
        "# ========================================",
        "",
    ]

    lines.extend(_digital_helpers())
    lines.extend(_adc_helper(pin_infos))
    lines.extend(_pwm_helper(pin_infos))
    lines.extend(_i2c_helpers(bus_groups, name_lookup))
    lines.extend(_spi_helpers(bus_groups, name_lookup))
    lines.extend(_diff_pair_helpers(diff_pairs, name_lookup))

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


def _i2c_helpers(
    bus_groups: dict[str, list[Any]],
    name_lookup: dict[str, str] | None = None,
) -> list[str]:
    if name_lookup is None:
        name_lookup = {}
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
        sda_const = name_lookup.get(
            sda_pin.net_name, _sanitize_net_name(sda_pin.net_name)
        )
        scl_const = name_lookup.get(
            scl_pin.net_name, _sanitize_net_name(scl_pin.net_name)
        )

        helper_doc = (
            f"Setup {i2c_name} with SDA={sda_pin.pin_name}, SCL={scl_pin.pin_name}."
        )
        helpers.extend(
            [
                f"def {func_name}(freq=400000):",
                f'    """{helper_doc}"""',
                "    return I2C(",
                f"        {i2c_num},",
                f"        sda=Pin({sda_const}),",
                f"        scl=Pin({scl_const}),",
                "        freq=freq,",
                "    )",
                "",
            ]
        )

    return helpers


def _spi_helpers(
    bus_groups: dict[str, list[Any]],
    name_lookup: dict[str, str] | None = None,
) -> list[str]:
    if name_lookup is None:
        name_lookup = {}
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
        mosi_const = name_lookup.get(
            mosi_pin.net_name, _sanitize_net_name(mosi_pin.net_name)
        )
        miso_const = name_lookup.get(
            miso_pin.net_name, _sanitize_net_name(miso_pin.net_name)
        )
        sck_const = name_lookup.get(
            sck_pin.net_name, _sanitize_net_name(sck_pin.net_name)
        )

        helper_doc = (
            f"Setup {spi_name} with MOSI={mosi_pin.pin_name}, "
            f"MISO={miso_pin.pin_name}, SCK={sck_pin.pin_name}."
        )
        helpers.extend(
            [
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
            ]
        )

    return helpers


def _diff_pair_helpers(
    diff_pairs: list[Any],
    name_lookup: dict[str, str] | None = None,
) -> list[str]:
    if name_lookup is None:
        name_lookup = {}
    body: list[str] = []
    for pair in diff_pairs:
        if pair[0].role == PinRole.USB_DP:
            pos_const = name_lookup.get(
                pair[0].net_name, _sanitize_net_name(pair[0].net_name)
            )
            neg_const = name_lookup.get(
                pair[1].net_name, _sanitize_net_name(pair[1].net_name)
            )

            body.extend(
                [
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
                ]
            )

        elif pair[0].role == PinRole.CAN_H:
            pos_const = name_lookup.get(
                pair[0].net_name, _sanitize_net_name(pair[0].net_name)
            )
            neg_const = name_lookup.get(
                pair[1].net_name, _sanitize_net_name(pair[1].net_name)
            )

            body.extend(
                [
                    "class CANPins:",
                    '    """CAN differential pair pin definitions."""',
                    f"    H = {pos_const}  # {pair[0].description}",
                    f"    L = {neg_const}  # {pair[1].description}",
                    "",
                    "    @classmethod",
                    "    def get_pair(cls):",
                    '        """Get CAN H/L pin tuple."""',
                    "        return (cls.H, cls.L)",
                    "",
                ]
            )

    if not body:
        return []

    header = [
        "# ========================================",
        "# Differential Pair Classes",
        "# ========================================",
        "",
    ]
    return header + body
