"""
MCU Profile System for PinmapGen.

Provides extensible MCU profiles that define pin normalization rules, 
validation logic, and MCU-specific capabilities for different microcontroller families.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


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


@dataclass
class PinInfo:
    """Information about a specific MCU pin."""
    name: str
    capabilities: set[PinCapability]
    special_function: str | None = None
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

    def get_pin_capabilities(self, pin_name: str) -> set[PinCapability]:
        """Get capabilities for a specific pin."""
        normalized_pin = self.normalize_pin_name(pin_name)
        if normalized_pin in self.pins:
            return self.pins[normalized_pin].capabilities
        return set()

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
            warnings.append(f"Pin {pin_name} not found in {self.mcu_name} pin definitions")
            return warnings

        pin_info = self.pins[pin_name]

        # Check if pin has warnings for general use
        if pin_info.warnings:
            warnings.extend(pin_info.warnings)

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
            "usb.dp": PinCapability.USB_DP,
            "usb.dm": PinCapability.USB_DM,
        }
        return role_mappings.get(role.lower())

    def detect_differential_pairs(self, nets: dict[str, list[str]]) -> list[tuple[str, str]]:
        """
        Detect differential pairs in net names.
        
        Args:
            nets: Dictionary of net names to pins
            
        Returns:
            List of differential pair tuples (positive_net, negative_net)
        """
        diff_pairs = []
        net_names = set(nets.keys())

        # Common differential pair patterns
        diff_patterns = [
            (r"(.+)_P$", r"(.+)_N$"),      # Signal_P / Signal_N
            (r"(.+)_DP$", r"(.+)_DN$"),    # Signal_DP / Signal_DN
            (r"(.+)_DM$", r"(.+)_DP$"),    # USB style DM/DP
            (r"(.+)DP$", r"(.+)DM$"),      # USB_DP / USB_DM
            (r"(.+)CANH$", r"(.+)CANL$"),  # CAN High/Low
            (r"(.+)_PLUS$", r"(.+)_MINUS$"), # Signal_PLUS / Signal_MINUS
        ]

        matched_pairs = set()

        for pos_pattern, neg_pattern in diff_patterns:
            for net_name in net_names:
                if net_name in matched_pairs:
                    continue

                # Check if this net matches the positive pattern
                pos_match = re.match(pos_pattern, net_name)
                if pos_match:
                    base_name = pos_match.group(1)

                    # Look for corresponding negative net
                    neg_match_pattern = neg_pattern.replace(r"(.+)", re.escape(base_name))
                    for other_net in net_names:
                        if other_net in matched_pairs or other_net == net_name:
                            continue
                        if re.match(neg_match_pattern, other_net):
                            diff_pairs.append((net_name, other_net))
                            matched_pairs.add(net_name)
                            matched_pairs.add(other_net)
                            break

        return diff_pairs

    def validate_pinmap(self, nets: dict[str, list[str]]) -> list[str]:
        """
        Validate pinmap for common issues.
        
        Args:
            nets: Dictionary of net names to pins
            
        Returns:
            List of validation error messages
        """
        errors = []
        used_pins = {}  # pin -> net_name mapping

        # Check for duplicate pin usage
        for net_name, pins in nets.items():
            for pin in pins:
                if pin in used_pins:
                    errors.append(
                        f"Pin {pin} used by multiple nets: '{net_name}' and '{used_pins[pin]}'"
                    )
                else:
                    used_pins[pin] = net_name

        # Check for multi-pin nets on single-pin resources
        for net_name, pins in nets.items():
            if len(pins) > 1:
                if not self._is_valid_multipin_net(net_name, pins):
                    errors.append(
                        f"Net '{net_name}' connects to multiple pins {pins} - "
                        f"may indicate routing error"
                    )

        # Check for lonely differential pairs
        diff_pairs = self.detect_differential_pairs(nets)
        diff_nets = set()
        for pos, neg in diff_pairs:
            diff_nets.add(pos)
            diff_nets.add(neg)

        # Look for nets that seem like differential pairs but don't have partners
        diff_patterns = [
            r"(.+)_P$", r"(.+)_N$", r"(.+)_DP$", r"(.+)_DN$",
            r"(.+)_DM$", r"(.+)DP$", r"(.+)DM$", r"(.+)CANH$", r"(.+)CANL$"
        ]

        for net_name in nets:
            if net_name not in diff_nets:
                for pattern in diff_patterns:
                    if re.match(pattern, net_name):
                        errors.append(
                            f"Potential lonely differential pair: '{net_name}' has no partner"
                        )
                        break

        return errors

    def _is_valid_multipin_net(self, net_name: str, pins: list[str]) -> bool:
        """Check if a multi-pin net is valid (e.g., power rails)."""
        # Power and ground nets can legitimately connect to multiple pins
        power_patterns = [
            r".*VCC.*", r".*VDD.*", r".*VBUS.*", r".*3V3.*", r".*5V.*", r".*1V8.*",
            r".*GND.*", r".*VSS.*", r".*GROUND.*", r".*VREF.*", r".*AVDD.*", r".*DVDD.*"
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

        for net_name, pins in nets.items():
            normalized_pins = []
            for pin in pins:
                try:
                    normalized_pin = self.normalize_pin_name(pin)
                    normalized_pins.append(normalized_pin)

                    # Collect validation warnings for this pin assignment
                    from .roles import PinRoleInferrer
                    role_inferrer = PinRoleInferrer()
                    role = role_inferrer.infer_role(net_name)
                    pin_warnings = self.validate_pin_assignment(normalized_pin, role.name)
                    validation_warnings.extend(pin_warnings)

                except ValueError as e:
                    print(f"Warning: {e}")
                    continue

            if normalized_pins:
                normalized_nets[net_name] = normalized_pins

        # Validate the normalized pinmap
        validation_errors = self.validate_pinmap(normalized_nets)
        if validation_errors:
            print(f"Validation errors found: {'; '.join(validation_errors)}")

        # Detect differential pairs
        diff_pairs = self.detect_differential_pairs(normalized_nets)

        # Get special pins used
        special_pins_used = []
        for net_pins in normalized_nets.values():
            for pin in net_pins:
                if pin in self.pins and self.pins[pin].special_function:
                    special_pins_used.append(pin)

        # Create canonical structure
        canonical = {
            "mcu": self.mcu_name.lower(),
            "pins": normalized_nets,
            "differential_pairs": [
                {"positive": pos, "negative": neg}
                for pos, neg in diff_pairs
            ],
            "metadata": {
                "total_nets": len(normalized_nets),
                "total_pins": sum(len(pins) for pins in normalized_nets.values()),
                "differential_pairs_count": len(diff_pairs),
                "special_pins_used": special_pins_used,
                "validation_warnings": validation_warnings,
                "validation_errors": validation_errors
            }
        }

        return canonical
