"""Shared pin metadata for PinmapGen emitters.

Special-function descriptions come from the MCU profiles (the same TOML
data used for normalization/validation), so there is a single source of
truth. Emitters normally pass the canonical pinmap dict, whose metadata
already embeds these tables; when it is absent, the tables are derived
from the profile registry on demand and cached.
"""

from __future__ import annotations

# Cache of mcu name → (short_table, long_table). Populated lazily so that
# importing this module does not load every profile.
_FUNCTION_TABLES: dict[str, tuple[dict[str, str], dict[str, str]]] = {}


def _function_tables(mcu: str) -> tuple[dict[str, str], dict[str, str]]:
    """Return ``(short, long)`` special-function tables for *mcu*.

    Derived from the registered profile's pin definitions. Unknown MCU
    names yield empty tables rather than raising, since callers use these
    purely for decorative comments.
    """
    key = mcu.lower()
    if key not in _FUNCTION_TABLES:
        short: dict[str, str] = {}
        long_: dict[str, str] = {}
        try:
            from .profile_registry import registry

            profile = registry.get_profile(key)
        except Exception:  # noqa: BLE001 — missing/broken profile → no labels
            profile = None
        if profile is not None:
            for pin_name, pin_info in profile.pins.items():
                if pin_info.special_function:
                    long_[pin_name] = pin_info.special_function
                    short[pin_name] = (
                        pin_info.special_function_short
                        or pin_info.special_function
                    )
        _FUNCTION_TABLES[key] = (short, long_)
    return _FUNCTION_TABLES[key]


def get_special_functions_short(mcu: str) -> dict[str, str]:
    """Return the pin → concise special-function label table for *mcu*."""
    return _function_tables(mcu)[0]


def get_special_functions_long(mcu: str) -> dict[str, str]:
    """Return the pin → verbose special-function label table for *mcu*."""
    return _function_tables(mcu)[1]


def get_pin_comment(
    pin: str,
    mcu: str = "rp2040",
    canonical_dict: dict | None = None,
) -> str:
    """Return a concise pin comment such as ``"GP24 - USB D-"``.

    When *canonical_dict* is provided the special-function data embedded in
    its ``metadata.special_functions_short`` is used. Otherwise the table is
    derived from the registered profile for *mcu*.

    Args:
        pin: Normalised pin name (e.g. ``"GP24"``, ``"PA13"``).
        mcu: MCU identifier for MCU-specific lookups.
        canonical_dict: Optional canonical pinmap dict.

    Returns:
        Human-readable comment string.
    """
    comments = [pin]
    if canonical_dict:
        mcu_funcs = (
            canonical_dict.get("metadata", {})
            .get("special_functions_short", {})
        )
    else:
        mcu_funcs = get_special_functions_short(mcu)
    if pin in mcu_funcs:
        comments.append(mcu_funcs[pin])
    return " - ".join(comments)


def get_special_function(
    pin: str,
    mcu: str = "rp2040",
    canonical_dict: dict | None = None,
) -> str:
    """Return a verbose special-function description for documentation.

    Args:
        pin: Normalised pin name.
        mcu: MCU identifier.
        canonical_dict: Optional canonical pinmap dict.

    Returns:
        Descriptive string, or ``"General Purpose I/O"`` if unknown.
    """
    if canonical_dict:
        mcu_funcs = (
            canonical_dict.get("metadata", {})
            .get("special_functions_long", {})
        )
    else:
        mcu_funcs = get_special_functions_long(mcu)
    return mcu_funcs.get(pin, "General Purpose I/O")
