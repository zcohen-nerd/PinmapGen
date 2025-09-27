"""
Pin role inference for PinmapGen.

This module analyzes net names and pin assignments to infer functional roles
like I2C, UART, PWM, ADC, etc. This metadata is used to generate richer
output with helper functions and better organization.
"""

import re
from dataclasses import dataclass
from enum import Enum


class PinRole(Enum):
    """Pin functional roles."""
    # Communication
    I2C_SDA = "i2c.sda"
    I2C_SCL = "i2c.scl"
    UART_TX = "uart.tx"
    UART_RX = "uart.rx"
    SPI_MOSI = "spi.mosi"
    SPI_MISO = "spi.miso"
    SPI_SCK = "spi.sck"
    SPI_CS = "spi.cs"

    # USB/Differential
    USB_DP = "usb.dp"
    USB_DN = "usb.dn"
    CAN_H = "can.h"
    CAN_L = "can.l"

    # Analog
    ADC = "adc"
    DAC = "dac"

    # Digital I/O
    PWM = "pwm"
    GPIO_IN = "gpio.in"
    GPIO_OUT = "gpio.out"

    # Special
    LED = "led"
    BUTTON = "button"
    RESET = "reset"
    CLOCK = "clock"
    POWER = "power"
    GROUND = "ground"

    # Unknown
    UNKNOWN = "unknown"


@dataclass
class PinInfo:
    """Enhanced pin information with inferred role."""
    net_name: str
    pin_name: str
    component: str
    ref_des: str
    role: PinRole
    bus_group: str | None = None  # e.g., "I2C0", "UART1", "SPI2"
    description: str | None = None


class RoleInferencer:
    """Infers pin roles from net names and patterns."""

    def __init__(self):
        # Pattern matching for role inference
        self.patterns = {
            # I2C patterns
            PinRole.I2C_SDA: [
                r"(?i).*i2c.*sda.*",
                r"(?i).*sda.*",
            ],
            PinRole.I2C_SCL: [
                r"(?i).*i2c.*scl.*",
                r"(?i).*scl.*",
            ],

            # UART patterns
            PinRole.UART_TX: [
                r"(?i).*uart.*tx.*",
                r"(?i).*tx.*",
                r"(?i).*serial.*tx.*",
            ],
            PinRole.UART_RX: [
                r"(?i).*uart.*rx.*",
                r"(?i).*rx.*",
                r"(?i).*serial.*rx.*",
            ],

            # SPI patterns
            PinRole.SPI_MOSI: [
                r"(?i).*spi.*mosi.*",
                r"(?i).*mosi.*",
                r"(?i).*spi.*tx.*",
            ],
            PinRole.SPI_MISO: [
                r"(?i).*spi.*miso.*",
                r"(?i).*miso.*",
                r"(?i).*spi.*rx.*",
            ],
            PinRole.SPI_SCK: [
                r"(?i).*spi.*sck.*",
                r"(?i).*sck.*",
                r"(?i).*spi.*clk.*",
            ],
            PinRole.SPI_CS: [
                r"(?i).*spi.*cs.*",
                r"(?i).*cs.*",
                r"(?i).*spi.*ss.*",
                r"(?i).*ss.*",
            ],

            # USB patterns
            PinRole.USB_DP: [
                r"(?i).*usb.*d\+.*",
                r"(?i).*usb.*dp.*",
                r"(?i).*usb.*plus.*",
            ],
            PinRole.USB_DN: [
                r"(?i).*usb.*d-.*",
                r"(?i).*usb.*dn.*",
                r"(?i).*usb.*minus.*",
            ],

            # CAN patterns
            PinRole.CAN_H: [
                r"(?i).*can.*h.*",
                r"(?i).*canh.*",
            ],
            PinRole.CAN_L: [
                r"(?i).*can.*l.*",
                r"(?i).*canl.*",
            ],

            # Analog patterns
            PinRole.ADC: [
                r"(?i).*adc.*",
                r"(?i).*analog.*in.*",
                r"(?i).*ain.*",
            ],
            PinRole.DAC: [
                r"(?i).*dac.*",
                r"(?i).*analog.*out.*",
                r"(?i).*aout.*",
            ],

            # PWM patterns
            PinRole.PWM: [
                r"(?i).*pwm.*",
                r"(?i).*pulse.*",
                r"(?i).*servo.*",
                r"(?i).*motor.*",
            ],

            # Special patterns
            PinRole.LED: [
                r"(?i).*led.*",
                r"(?i).*light.*",
            ],
            PinRole.BUTTON: [
                r"(?i).*button.*",
                r"(?i).*btn.*",
                r"(?i).*switch.*",
                r"(?i).*sw.*",
            ],
            PinRole.RESET: [
                r"(?i).*reset.*",
                r"(?i).*rst.*",
            ],
            PinRole.CLOCK: [
                r"(?i).*clock.*",
                r"(?i).*clk.*",
                r"(?i).*xtal.*",
                r"(?i).*osc.*",
            ],
        }

    def infer_role(self, net_name: str) -> PinRole:
        """Infer the role of a pin from its net name."""
        for role, patterns in self.patterns.items():
            for pattern in patterns:
                if re.match(pattern, net_name):
                    return role

        # Default to GPIO based on direction hints
        if any(keyword in net_name.lower() for keyword in ["in", "input", "sense"]):
            return PinRole.GPIO_IN
        if any(keyword in net_name.lower() for keyword in ["out", "output", "drive"]):
            return PinRole.GPIO_OUT

        return PinRole.UNKNOWN

    def extract_bus_group(self, net_name: str, role: PinRole) -> str | None:
        """Extract bus/peripheral group identifier (e.g., I2C0, UART1, SPI2)."""
        # Look for numbered peripherals
        bus_patterns = {
            PinRole.I2C_SDA: r"(?i)(i2c\d*)",
            PinRole.I2C_SCL: r"(?i)(i2c\d*)",
            PinRole.UART_TX: r"(?i)(uart\d*)",
            PinRole.UART_RX: r"(?i)(uart\d*)",
            PinRole.SPI_MOSI: r"(?i)(spi\d*)",
            PinRole.SPI_MISO: r"(?i)(spi\d*)",
            PinRole.SPI_SCK: r"(?i)(spi\d*)",
            PinRole.SPI_CS: r"(?i)(spi\d*)",
        }

        if role in bus_patterns:
            match = re.search(bus_patterns[role], net_name)
            if match:
                return match.group(1).upper()

        return None

    def generate_description(self, pin_info: PinInfo) -> str:
        """Generate a human-readable description for the pin."""
        role_descriptions = {
            PinRole.I2C_SDA: "I2C Serial Data",
            PinRole.I2C_SCL: "I2C Serial Clock",
            PinRole.UART_TX: "UART Transmit",
            PinRole.UART_RX: "UART Receive",
            PinRole.SPI_MOSI: "SPI Master Out Slave In",
            PinRole.SPI_MISO: "SPI Master In Slave Out",
            PinRole.SPI_SCK: "SPI Serial Clock",
            PinRole.SPI_CS: "SPI Chip Select",
            PinRole.USB_DP: "USB Data Positive",
            PinRole.USB_DN: "USB Data Negative",
            PinRole.CAN_H: "CAN Bus High",
            PinRole.CAN_L: "CAN Bus Low",
            PinRole.ADC: "Analog to Digital Converter",
            PinRole.DAC: "Digital to Analog Converter",
            PinRole.PWM: "Pulse Width Modulation",
            PinRole.GPIO_IN: "General Purpose Input",
            PinRole.GPIO_OUT: "General Purpose Output",
            PinRole.LED: "Light Emitting Diode",
            PinRole.BUTTON: "Push Button Input",
            PinRole.RESET: "Reset Signal",
            PinRole.CLOCK: "Clock Signal",
        }

        base_desc = role_descriptions.get(pin_info.role, "General Purpose I/O")

        if pin_info.bus_group:
            return f"{base_desc} ({pin_info.bus_group})"

        return base_desc

    def analyze_pinmap(self, canonical_pinmap: dict) -> list[PinInfo]:
        """Analyze a canonical pinmap and return enhanced pin information."""
        pin_infos = []

        for net_name, pin_data in canonical_pinmap.items():
            # Handle different canonical dictionary formats
            if isinstance(pin_data, dict):
                # New format with pin metadata
                pin_name = pin_data.get("pin", "UNKNOWN")
                component = pin_data.get("component", "UNKNOWN")
                ref_des = pin_data.get("ref_des", "UNKNOWN")
            elif isinstance(pin_data, list):
                # Original format with list of pins
                pin_name = pin_data[0] if pin_data else "UNKNOWN"
                component = "UNKNOWN"
                ref_des = "UNKNOWN"
            else:
                # Fallback
                pin_name = str(pin_data)
                component = "UNKNOWN"
                ref_des = "UNKNOWN"

            # Infer role
            role = self.infer_role(net_name)
            bus_group = self.extract_bus_group(net_name, role)

            # Create enhanced pin info
            pin_info = PinInfo(
                net_name=net_name,
                pin_name=pin_name,
                component=component,
                ref_des=ref_des,
                role=role,
                bus_group=bus_group
            )

            # Generate description
            pin_info.description = self.generate_description(pin_info)

            pin_infos.append(pin_info)

        return pin_infos

    def group_by_bus(self, pin_infos: list[PinInfo]) -> dict[str, list[PinInfo]]:
        """Group pins by their bus/peripheral."""
        groups = {}

        for pin_info in pin_infos:
            if pin_info.bus_group:
                group_key = pin_info.bus_group
            else:
                # Group by role category
                role_groups = {
                    PinRole.I2C_SDA: "I2C",
                    PinRole.I2C_SCL: "I2C",
                    PinRole.UART_TX: "UART",
                    PinRole.UART_RX: "UART",
                    PinRole.SPI_MOSI: "SPI",
                    PinRole.SPI_MISO: "SPI",
                    PinRole.SPI_SCK: "SPI",
                    PinRole.SPI_CS: "SPI",
                    PinRole.USB_DP: "USB",
                    PinRole.USB_DN: "USB",
                    PinRole.CAN_H: "CAN",
                    PinRole.CAN_L: "CAN",
                    PinRole.ADC: "Analog",
                    PinRole.DAC: "Analog",
                    PinRole.PWM: "PWM",
                    PinRole.LED: "Indicators",
                    PinRole.BUTTON: "Inputs",
                    PinRole.GPIO_IN: "GPIO",
                    PinRole.GPIO_OUT: "GPIO",
                }
                group_key = role_groups.get(pin_info.role, "Other")

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(pin_info)

        return groups

    def detect_differential_pairs(self, pin_infos: list[PinInfo]) -> list[tuple[PinInfo, PinInfo]]:
        """Detect differential pairs from enhanced pin information."""
        pairs = []

        # Group by bus to find pairs
        bus_groups = self.group_by_bus(pin_infos)

        for group_name, pins in bus_groups.items():
            if group_name == "USB":
                # Find USB D+/D- pairs
                dp_pins = [p for p in pins if p.role == PinRole.USB_DP]
                dn_pins = [p for p in pins if p.role == PinRole.USB_DN]

                for dp in dp_pins:
                    for dn in dn_pins:
                        pairs.append((dp, dn))

            elif group_name == "CAN":
                # Find CAN H/L pairs
                h_pins = [p for p in pins if p.role == PinRole.CAN_H]
                l_pins = [p for p in pins if p.role == PinRole.CAN_L]

                for h in h_pins:
                    for l in l_pins:
                        pairs.append((h, l))

        return pairs


def analyze_roles(canonical_pinmap: dict) -> tuple[list[PinInfo], dict[str, list[PinInfo]], list[tuple[PinInfo, PinInfo]]]:
    """
    Analyze pin roles from a canonical pinmap.
    
    Returns:
        - List of enhanced pin information
        - Dictionary of pins grouped by bus/peripheral
        - List of detected differential pairs
    """
    inferencer = RoleInferencer()

    # Analyze all pins
    pin_infos = inferencer.analyze_pinmap(canonical_pinmap)

    # Group by bus/peripheral
    bus_groups = inferencer.group_by_bus(pin_infos)

    # Detect differential pairs
    diff_pairs = inferencer.detect_differential_pairs(pin_infos)

    return pin_infos, bus_groups, diff_pairs


# Alias for backward compatibility and MCU profiles
PinRoleInferrer = RoleInferencer


if __name__ == "__main__":
    # Test with sample data
    sample_pinmap = {
        "I2C0_SDA": {"pin": "GP0", "component": "RP2040", "ref_des": "U1"},
        "I2C0_SCL": {"pin": "GP1", "component": "RP2040", "ref_des": "U1"},
        "LED_DATA": {"pin": "GP4", "component": "RP2040", "ref_des": "U1"},
        "BUTTON": {"pin": "GP5", "component": "RP2040", "ref_des": "U1"},
        "USB_DP": {"pin": "GP24", "component": "RP2040", "ref_des": "U1"},
        "USB_DN": {"pin": "GP25", "component": "RP2040", "ref_des": "U1"},
    }

    pin_infos, bus_groups, diff_pairs = analyze_roles(sample_pinmap)

    print("Pin Roles:")
    for pin in pin_infos:
        print(f"  {pin.net_name} -> {pin.pin_name}: {pin.role.value} ({pin.description})")

    print("\nBus Groups:")
    for group, pins in bus_groups.items():
        print(f"  {group}: {[p.net_name for p in pins]}")

    print("\nDifferential Pairs:")
    for pair in diff_pairs:
        print(f"  {pair[0].net_name} / {pair[1].net_name}")
