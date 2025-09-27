"""
Pin Normalization for PinmapGen.

Handles MCU-specific pin name normalization and validation.
Currently supports RP2040 profile with GPIO aliases.
"""

import re
from typing import Any


class RP2040Profile:
    """RP2040 MCU pin profile and normalization rules."""

    def __init__(self):
        """Initialize RP2040 pin mappings and aliases."""
        # Valid RP2040 GPIO pins (0-29)
        self.valid_gpio_pins = set(range(30))

        # Special function pins that are valid but have specific uses
        self.special_pins = {
            "GP23": "SMPS_MODE",  # Power switching mode
            "GP24": "USB_DM",     # USB D-
            "GP25": "USB_DP",     # USB D+
            "GP26": "ADC0",       # ADC Channel 0
            "GP27": "ADC1",       # ADC Channel 1
            "GP28": "ADC2",       # ADC Channel 2
            "GP29": "ADC3",       # ADC Channel 3
        }

        # Common differential pair patterns
        self.diff_patterns = [
            (r"(.+)_P$", r"(.+)_N$"),      # Signal_P / Signal_N
            (r"(.+)_DP$", r"(.+)_DN$"),    # Signal_DP / Signal_DN
            (r"(.+)_DM$", r"(.+)_DP$"),    # USB style DM/DP
            (r"(.+)DP$", r"(.+)DM$"),      # USB_DP / USB_DM
            (r"(.+)CANH$", r"(.+)CANL$"),  # CAN High/Low
        ]

    def normalize_pin_name(self, pin_name: str) -> str:
        """
        Normalize pin name according to RP2040 conventions.
        
        Args:
            pin_name: Raw pin name from schematic/CSV
            
        Returns:
            Normalized pin name (GPxx format)
            
        Raises:
            ValueError: If pin name cannot be normalized or is invalid
        """
        # Remove whitespace and convert to uppercase
        pin_name = pin_name.strip().upper()

        # Handle various GPIO formats
        # GPIOxx -> GPxx
        if pin_name.startswith("GPIO"):
            match = re.match(r"GPIO(\d+)", pin_name)
            if match:
                pin_num = int(match.group(1))
                if pin_num in self.valid_gpio_pins:
                    return f"GP{pin_num}"
                raise ValueError(f"Invalid GPIO pin number: {pin_num} (valid range: 0-29)")

        # IOxx -> GPxx
        elif pin_name.startswith("IO"):
            match = re.match(r"IO(\d+)", pin_name)
            if match:
                pin_num = int(match.group(1))
                if pin_num in self.valid_gpio_pins:
                    return f"GP{pin_num}"
                raise ValueError(f"Invalid IO pin number: {pin_num} (valid range: 0-29)")

        # GPxx (already normalized)
        elif pin_name.startswith("GP"):
            match = re.match(r"GP(\d+)", pin_name)
            if match:
                pin_num = int(match.group(1))
                if pin_num in self.valid_gpio_pins:
                    return pin_name  # Already normalized
                raise ValueError(f"Invalid GP pin number: {pin_num} (valid range: 0-29)")

        # Handle numeric-only pins (assume GPIO)
        elif pin_name.isdigit():
            pin_num = int(pin_name)
            if pin_num in self.valid_gpio_pins:
                return f"GP{pin_num}"
            raise ValueError(f"Invalid pin number: {pin_num} (valid range: 0-29)")

        # Unknown format
        else:
            raise ValueError(f"Cannot normalize pin name: {pin_name}")

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

        for pos_pattern, neg_pattern in self.diff_patterns:
            matched_pairs = set()

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
                # Check if this is a valid multi-pin net (like power rails)
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
        for net_name in nets:
            if net_name not in diff_nets:
                for pos_pattern, neg_pattern in self.diff_patterns:
                    if re.match(pos_pattern, net_name) or re.match(neg_pattern, net_name):
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
            r".*GND.*", r".*VSS.*", r".*GROUND.*"
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
        for net_name, pins in nets.items():
            normalized_pins = []
            for pin in pins:
                try:
                    normalized_pin = self.normalize_pin_name(pin)
                    normalized_pins.append(normalized_pin)
                except ValueError as e:
                    # Skip invalid pins but log the error
                    print(f"Warning: {e}")
                    continue

            if normalized_pins:  # Only add nets with valid pins
                normalized_nets[net_name] = normalized_pins

        # Validate the normalized pinmap
        validation_errors = self.validate_pinmap(normalized_nets)
        if validation_errors:
            raise ValueError(f"Pinmap validation failed: {'; '.join(validation_errors)}")

        # Detect differential pairs
        diff_pairs = self.detect_differential_pairs(normalized_nets)

        # Create canonical structure
        canonical = {
            "mcu": "rp2040",
            "pins": normalized_nets,
            "differential_pairs": [
                {"positive": pos, "negative": neg}
                for pos, neg in diff_pairs
            ],
            "metadata": {
                "total_nets": len(normalized_nets),
                "total_pins": sum(len(pins) for pins in normalized_nets.values()),
                "differential_pairs_count": len(diff_pairs),
                "special_pins_used": [
                    pin for net_pins in normalized_nets.values()
                    for pin in net_pins
                    if pin in self.special_pins
                ]
            }
        }

        return canonical


def get_mcu_profile(mcu_name: str):
    """
    Get MCU profile by name.
    
    Args:
        mcu_name: MCU name (e.g., "rp2040")
        
    Returns:
        MCU profile instance
    """
    if mcu_name.lower() == "rp2040":
        return RP2040Profile()
    raise ValueError(f"Unsupported MCU: {mcu_name}")


def normalize_pinmap(nets: dict[str, list[str]], mcu_name: str) -> dict[str, Any]:
    """
    Normalize pinmap for specified MCU and return canonical dictionary.
    
    Args:
        nets: Raw net to pin mappings
        mcu_name: MCU name (e.g., "rp2040")
        
    Returns:
        Canonical pinmap dictionary with normalized pins and differential pairs
    """
    profile = get_mcu_profile(mcu_name)
    return profile.create_canonical_pinmap(nets)
