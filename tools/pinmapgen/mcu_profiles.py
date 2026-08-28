"""
MCU Profile System for PinmapGen.

Provides extensible MCU profiles that define pin normalization rules,
validation logic, and MCU-specific capabilities for different microcontroller families.
"""

import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .roles import PinRoleInferrer

# Roles that imply the MCU drives the pin — used to flag output-like nets
# on input-only pads.
_OUTPUT_ROLES = frozenset({
    "gpio.out", "led", "pwm", "dac", "clock",
    "uart.tx", "spi.mosi", "spi.sck", "spi.cs",
})


class PinCapability(Enum):
    """Enumeration of pin capabilities across different MCUs."""

    GPIO = "gpio"
    ADC = "adc"
    DAC = "dac"
    PWM = "pwm"
    I2C_SDA = "i2c_sda"
    I2C_SCL = "i2c_scl"
    SPI_MOSI = "spi_mosi"
    SPI_MISO = "spi_miso"
    SPI_SCK = "spi_sck"
    SPI_CS = "spi_cs"
    UART_TX = "uart_tx"
    UART_RX = "uart_rx"
    CAN_TX = "can_tx"
    CAN_RX = "can_rx"
    USB_DP = "usb_dp"
    USB_DM = "usb_dm"
    I2S_DATA = "i2s_data"
    I2S_BCLK = "i2s_bclk"
    I2S_LRCLK = "i2s_lrclk"
    # Constraint marker, not a peripheral: the pin has no output driver
    # (e.g. ESP32 GPIO34-39). validate_pin_assignment warns when an
    # output-like role lands on such a pin.
    INPUT_ONLY = "input_only"


@dataclass
class PinInfo:
    """Information about a specific MCU pin."""

    name: str
    capabilities: set[PinCapability]
    special_function: str | None = None
    special_function_short: str | None = None
    warnings: list[str] | None = None
    alternate_names: list[str] | None = None


@dataclass
class PeripheralInfo:
    """Information about MCU peripheral instances."""

    name: str
    instance: int
    pins: dict[str, str]  # role -> pin mapping


class MCUProfile(ABC):
    """Abstract base class for MCU profiles."""

    def __init__(self, mcu_name: str):
        """Initialize MCU profile with name and capabilities."""
        self.mcu_name = mcu_name.upper()
        self.pins: dict[str, PinInfo] = {}
        self.peripherals: list[PeripheralInfo] = []
        self._initialize_pin_definitions()
        self._initialize_peripherals()

    @abstractmethod
    def _initialize_pin_definitions(self) -> None:
        """Initialize pin definitions and capabilities for this MCU."""

    @abstractmethod
    def _initialize_peripherals(self) -> None:
        """Initialize peripheral definitions for this MCU."""

    @abstractmethod
    def normalize_pin_name(self, pin_name: str) -> str:
        """
        Normalize pin name according to MCU conventions.

        Args:
            pin_name: Raw pin name from schematic/CSV

        Returns:
            Normalized pin name

        Raises:
            ValueError: If pin name cannot be normalized
        """

    def validate_pin_assignment(self, pin_name: str, role: str) -> list[str]:
        """
        Validate that a pin can fulfill the assigned role.

        Args:
            pin_name: Normalized pin name
            role: Assigned role/function

        Returns:
            List of validation warnings (empty if valid)
        """
        warnings = []

        if pin_name not in self.pins:
            warnings.append(
                f"Pin {pin_name} not found in {self.mcu_name} pin definitions"
            )
            return warnings

        pin_info = self.pins[pin_name]

        # Check if pin has warnings for general use
        if pin_info.warnings:
            warnings.extend(pin_info.warnings)

        # A net whose name is unambiguously a power/ground rail should not
        # normally land on a GPIO at all — usually a naming accident or a
        # netlist artifact worth a second look.
        if role in ("power", "ground"):
            warnings.append(
                f"net looks like a power/ground rail but is assigned to "
                f"GPIO {pin_name} - verify this connection"
            )

        # Input-only pads (no output driver) driven by an output-like role.
        if (
            PinCapability.INPUT_ONLY in pin_info.capabilities
            and role in _OUTPUT_ROLES
        ):
            warnings.append(
                f"{pin_name} is input-only, but net role '{role}' implies "
                "an output - move the signal to an output-capable pin"
            )

        # Role-specific validation
        required_capability = self._role_to_capability(role)
        if required_capability and required_capability not in pin_info.capabilities:
            warnings.append(
                f"Pin {pin_name} may not support {role} "
                f"(missing {required_capability.value} capability)"
            )

        return warnings

    def _role_to_capability(self, role: str) -> PinCapability | None:
        """Map role string to required capability."""
        role_mappings = {
            "adc": PinCapability.ADC,
            "dac": PinCapability.DAC,
            "pwm": PinCapability.PWM,
            "i2c.sda": PinCapability.I2C_SDA,
            "i2c.scl": PinCapability.I2C_SCL,
            "spi.mosi": PinCapability.SPI_MOSI,
            "spi.miso": PinCapability.SPI_MISO,
            "spi.sck": PinCapability.SPI_SCK,
            "spi.cs": PinCapability.SPI_CS,
            "uart.tx": PinCapability.UART_TX,
            "uart.rx": PinCapability.UART_RX,
            "can.tx": PinCapability.CAN_TX,
            "can.rx": PinCapability.CAN_RX,
            "can.h": PinCapability.CAN_TX,
            "can.l": PinCapability.CAN_RX,
            "usb.dp": PinCapability.USB_DP,
            "usb.dm": PinCapability.USB_DM,
            "usb.dn": PinCapability.USB_DM,
        }
        return role_mappings.get(role.lower())

    def detect_differential_pairs(
        self, nets: dict[str, list[str]]
    ) -> list[tuple[str, str]]:
        """
        Detect differential pairs in net names.

        Args:
            nets: Dictionary of net names to pins

        Returns:
            List of differential pair tuples (positive_net, negative_net)
        """
        diff_pairs = []
        net_names = set(nets.keys())

        # Common differential pair patterns. (.*) variants allow an empty
        # prefix so bare CANH/CANL pair up; the +/- variants catch raw CAD
        # names like USB_D+ / USB_D-.
        diff_patterns = [
            (r"(.+)_P$", r"(.+)_N$"),  # Signal_P / Signal_N
            (r"(.+)_DP$", r"(.+)_DN$"),  # Signal_DP / Signal_DN
            (r"(.+)_DP$", r"(.+)_DM$"),  # USB style DP/DM (DP=positive)
            (r"(.+)DP$", r"(.+)DM$"),  # USBDP / USBDM
            (r"(.+)\+$", r"(.+)-$"),  # USB_D+ / USB_D-
            (r"(.*)CAN_?H$", r"(.*)CAN_?L$"),  # CANH/CANL, CAN_H/CAN_L
            (r"(.+)_PLUS$", r"(.+)_MINUS$"),  # Signal_PLUS / Signal_MINUS
        ]

        matched_pairs = set()

        for pos_pattern, neg_pattern in diff_patterns:
            for net_name in net_names:
                if net_name in matched_pairs:
                    continue

                # Check if this net matches the positive pattern
                pos_match = re.match(pos_pattern, net_name, re.IGNORECASE)
                if pos_match:
                    base_name = pos_match.group(1)

                    # Look for corresponding negative net
                    neg_match_pattern = neg_pattern.replace(
                        r"(.+)", re.escape(base_name)
                    ).replace(r"(.*)", re.escape(base_name))
                    for other_net in net_names:
                        if other_net in matched_pairs or other_net == net_name:
                            continue
                        if re.match(neg_match_pattern, other_net, re.IGNORECASE):
                            diff_pairs.append((net_name, other_net))
                            matched_pairs.add(net_name)
                            matched_pairs.add(other_net)
                            break

        return diff_pairs

    def validate_pinmap(self, nets: dict[str, list[str]]) -> list[str]:
        """
        Validate pinmap for definite conflicts.

        Only real errors live here (they fail ``--strict``); heuristics
        that can false-positive on legitimate designs are advisories —
        see :meth:`validate_pinmap_advisories`.

        Args:
            nets: Dictionary of net names to pins

        Returns:
            List of validation error messages
        """
        errors = []
        used_pins = {}  # pin -> net_name mapping

        # Check for duplicate pin usage — two signals on one pin is always
        # a genuine conflict.
        for net_name, pins in nets.items():
            for pin in pins:
                if pin in used_pins:
                    errors.append(
                        f"Pin {pin} used by multiple nets: '{net_name}' and '{used_pins[pin]}'"
                    )
                else:
                    used_pins[pin] = net_name

        return errors

    def validate_pinmap_advisories(self, nets: dict[str, list[str]]) -> list[str]:
        """
        Heuristic checks that deserve a look but can be legitimate.

        These are warnings, not errors: they never fail ``--strict``,
        because each has real-world false positives (bus nets that fan
        out, single-ended signals with pair-like names).

        Returns:
            List of advisory warning messages
        """
        warnings = []

        # Multi-pin nets that don't look like power rails.
        for net_name, pins in nets.items():
            if len(pins) > 1 and not self._is_valid_multipin_net(net_name, pins):
                warnings.append(
                    f"Net '{net_name}' connects to multiple pins {pins} - "
                    f"fine for a shared bus, otherwise check the routing"
                )

        # Lonely differential-pair halves. Only positive-style halves (and
        # CAN H/L, which are unambiguous) are flagged: a bare *_N net is
        # far more likely an active-low signal (RESET_N, CS_N) than half a
        # differential pair, so it is deliberately never reported.
        diff_pairs = self.detect_differential_pairs(nets)
        diff_nets = set()
        for pos, neg in diff_pairs:
            diff_nets.add(pos)
            diff_nets.add(neg)

        lonely_patterns = [
            r"(.+)_DP$",
            r"(.+)_DN$",
            r"(.+)_DM$",
            r"(.+)DP$",
            r"(.+)DM$",
            r"(.*)CAN_?H$",
            r"(.*)CAN_?L$",
            r"(.+)\+$",
            r"(.+)-$",
            r"(.+)_P$",
        ]

        for net_name in nets:
            if net_name not in diff_nets:
                for pattern in lonely_patterns:
                    if re.match(pattern, net_name, re.IGNORECASE):
                        warnings.append(
                            f"Potential lonely differential pair: '{net_name}' has no partner"
                        )
                        break

        return warnings

    def _is_valid_multipin_net(self, net_name: str, pins: list[str]) -> bool:
        """Check if a multi-pin net is valid (e.g., power rails)."""
        # Power and ground nets can legitimately connect to multiple pins
        power_patterns = [
            r".*VCC.*",
            r".*VDD.*",
            r".*VBUS.*",
            r".*3V3.*",
            r".*5V.*",
            r".*12V.*",
            r".*24V.*",
            r".*1V8.*",
            r".*GND.*",
            r".*VSS.*",
            r".*GROUND.*",
            r".*VREF.*",
            r".*AVDD.*",
            r".*DVDD.*",
            r".*VIN.*",
            r".*VOUT.*",
            r".*VBAT.*",
            r".*BATT.*",
            r".*VSYS.*",
            r".*VEE.*",
            r".*VCORE.*",
            r".*PWR.*",
            r".*POWER.*",
        ]

        for pattern in power_patterns:
            if re.match(pattern, net_name, re.IGNORECASE):
                return True

        return False

    def create_canonical_pinmap(self, nets: dict[str, list[str]]) -> dict[str, Any]:
        """
        Create canonical pinmap dictionary with normalized pins and detected differential pairs.

        Args:
            nets: Raw net to pin mappings

        Returns:
            Canonical dictionary with pins, differential pairs, and metadata
        """
        # Normalize all pin names
        normalized_nets = {}
        validation_warnings = []

        role_inferrer = PinRoleInferrer()

        dropped_pins: list[dict[str, str]] = []
        # Bare-number pins ("2") are ambiguous: profiles interpret them as
        # logical GPIO numbers, but CAD exports often put the *physical
        # package pad* number in the Pin column, which would produce a
        # plausible-looking but wrong pinmap. Track them so one summary
        # warning can flag the assumption.
        numeric_pins: list[tuple[str, str]] = []

        for net_name, pins in nets.items():
            normalized_pins = []
            for pin in pins:
                try:
                    normalized_pin = self.normalize_pin_name(pin)
                    normalized_pins.append(normalized_pin)

                    raw = pin.strip()
                    if raw.isascii() and raw.isdecimal():
                        numeric_pins.append((raw, normalized_pin))

                    # Collect validation warnings for this pin assignment
                    role = role_inferrer.infer_role(net_name)
                    pin_warnings = self.validate_pin_assignment(
                        normalized_pin, role.value
                    )
                    validation_warnings.extend(pin_warnings)

                except ValueError as exc:
                    dropped_pins.append(
                        {"pin": pin, "net": net_name, "reason": str(exc)}
                    )
                    print(
                        f"Warning: Dropped pin '{pin}' on net '{net_name}': {exc}",
                        file=sys.stderr,
                    )
                    continue

            if normalized_pins:
                normalized_nets[net_name] = normalized_pins

        # Advisory heuristics (multi-pin nets, lonely pair halves): real
        # designs legitimately trip these, so they are warnings that never
        # fail --strict.
        validation_warnings.extend(
            self.validate_pinmap_advisories(normalized_nets)
        )

        # One summary warning for bare-number pins (see numeric_pins above).
        if numeric_pins:
            examples = ", ".join(
                f"'{raw}' -> {norm}" for raw, norm in numeric_pins[:3]
            )
            if len(numeric_pins) > 3:
                examples += ", ..."
            validation_warnings.append(
                f"{len(numeric_pins)} pin(s) were bare numbers and were "
                f"interpreted as logical GPIO numbers ({examples}). If the "
                "netlist's Pin column holds physical package pad numbers "
                "instead, the generated pinmap will be wrong - verify one "
                "pin against the schematic before trusting it."
            )

        # Surface advisory per-pin warnings (strapping/boot/USB/debug pins).
        # Deduplicated: the same pin warning can be collected once per net
        # that touches the pin, but repeating it adds no information.
        validation_warnings = list(dict.fromkeys(validation_warnings))
        for warning in validation_warnings:
            print(f"Warning: {warning}", file=sys.stderr)

        # Validate the normalized pinmap
        validation_errors = self.validate_pinmap(normalized_nets)
        for err in validation_errors:
            print(f"Validation error: {err}", file=sys.stderr)

        # Detect differential pairs
        diff_pairs = self.detect_differential_pairs(normalized_nets)

        # Get special pins used. Deduplicated and sorted in natural pin
        # order so the metadata (and PINOUT.md's special-pins section)
        # doesn't reshuffle when CSV rows are reordered.
        def _pin_order(pin: str) -> tuple[str, int]:
            num = re.search(r"\d+", pin)
            return (re.sub(r"\d.*$", "", pin), int(num.group()) if num else -1)

        special_pins_used = sorted(
            {
                pin
                for net_pins in normalized_nets.values()
                for pin in net_pins
                if pin in self.pins and self.pins[pin].special_function
            },
            key=_pin_order,
        )

        # Extract special-function metadata from pin definitions so that
        # emitters can use it without hard-coded look-up tables.
        special_functions_short: dict[str, str] = {}
        special_functions_long: dict[str, str] = {}
        for pin_name, pin_info in self.pins.items():
            if pin_info.special_function:
                special_functions_long[pin_name] = pin_info.special_function
                special_functions_short[pin_name] = (
                    pin_info.special_function_short
                    or pin_info.special_function
                )

        # Create canonical structure
        # Sort nets by name for deterministic, diff-friendly output.
        normalized_nets = dict(sorted(normalized_nets.items()))
        return {
            "mcu": self.mcu_name.lower(),
            "pins": normalized_nets,
            "differential_pairs": [
                {"positive": pos, "negative": neg} for pos, neg in diff_pairs
            ],
            "metadata": {
                "total_nets": len(normalized_nets),
                "total_pins": sum(len(pins) for pins in normalized_nets.values()),
                "differential_pairs_count": len(diff_pairs),
                "special_pins_used": special_pins_used,
                "validation_warnings": validation_warnings,
                "validation_errors": validation_errors,
                "dropped_pins": dropped_pins,
                "special_functions_short": special_functions_short,
                "special_functions_long": special_functions_long,
            },
        }

