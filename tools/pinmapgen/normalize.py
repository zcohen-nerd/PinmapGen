"""Pin Normalization for PinmapGen.

Handles MCU-specific pin name normalization and validation.
Provides backward-compatible legacy RP2040Profile that delegates
to the canonical rp2040_profile.RP2040Profile.
"""

import sys  # noqa: F401  # kept for backward-compat with downstream importers
from typing import Any


class RP2040Profile:
    """Legacy RP2040 profile — delegates to rp2040_profile.RP2040Profile.

    Kept for backward compatibility.  All real logic lives in
    ``tools.pinmapgen.rp2040_profile.RP2040Profile``.
    """

    def __init__(self):
        from .rp2040_profile import RP2040Profile as _Real

        self._delegate = _Real()

    # --- Expose common attributes via the delegate ---

    @property
    def valid_gpio_pins(self) -> set[int]:
        return {int(p.replace("GP", "")) for p in self._delegate.pins}

    @property
    def special_pins(self) -> dict[str, str]:
        return {
            name: info.special_function
            for name, info in self._delegate.pins.items()
            if info.special_function
        }

    # --- Delegated public methods ---

    def normalize_pin_name(self, pin_name: str) -> str:
        """Normalize pin name according to RP2040 conventions."""
        return self._delegate.normalize_pin_name(pin_name)

    def detect_differential_pairs(
        self, nets: dict[str, list[str]]
    ) -> list[tuple[str, str]]:
        """Detect differential pairs in net names."""
        return self._delegate.detect_differential_pairs(nets)

    def validate_pinmap(self, nets: dict[str, list[str]]) -> list[str]:
        """Validate pinmap for common issues."""
        return self._delegate.validate_pinmap(nets)

    def _is_valid_multipin_net(self, net_name: str, pins: list[str]) -> bool:
        """Check if a multi-pin net is valid (e.g., power rails)."""
        return self._delegate._is_valid_multipin_net(net_name, pins)  # noqa: SLF001

    def create_canonical_pinmap(self, nets: dict[str, list[str]]) -> dict[str, Any]:
        """Create canonical pinmap dictionary."""
        # Delegate handles all validation output; no need to re-print here.
        return self._delegate.create_canonical_pinmap(nets)



def get_mcu_profile(mcu_name: str):
    """
    Get MCU profile by name.

    Args:
        mcu_name: MCU name (e.g., "rp2040", "stm32g0", "esp32")

    Returns:
        MCU profile instance
    """
    from .esp32_profile import ESP32Profile
    from .rp2040_profile import RP2040Profile as RP2040ProfileNew
    from .stm32g0_profile import STM32G0Profile

    profiles = {
        "rp2040": RP2040ProfileNew,
        "stm32g0": STM32G0Profile,
        "esp32": ESP32Profile,
    }
    key = mcu_name.lower()
    if key in profiles:
        return profiles[key]()
    msg = f"Unsupported MCU: {mcu_name}"
    raise ValueError(msg)


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
