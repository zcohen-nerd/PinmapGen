"""
TOML-based MCU Profile Loader for PinmapGen.

Loads MCU pin definitions, normalization rules, and peripheral descriptions
from declarative TOML files so that users can add MCU support without writing
any Python.  The resulting ``TOMLProfile`` instances are fully compatible with
the existing ``MCUProfile`` ABC.

Requires Python 3.11+ (stdlib ``tomllib``).
"""

from __future__ import annotations

import logging
import re
import tomllib
from pathlib import Path
from typing import Any

from .mcu_profiles import MCUProfile, PeripheralInfo, PinCapability, PinInfo
from .profile_schema import validate_profile_toml

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CAPABILITY_MAP: dict[str, PinCapability] = {c.value: c for c in PinCapability}


def _parse_capability(name: str) -> PinCapability:
    """Convert a lowercase capability string to the ``PinCapability`` enum.

    Raises:
        ValueError: If *name* is not a recognised capability.
    """
    cap = _CAPABILITY_MAP.get(name.lower())
    if cap is None:
        valid = ", ".join(sorted(_CAPABILITY_MAP))
        msg = f"Unknown pin capability '{name}'. Valid values: {valid}"
        raise ValueError(msg)
    return cap


def _parse_capabilities(names: list[str]) -> set[PinCapability]:
    return {_parse_capability(n) for n in names}


def _expand_range(range_cfg: dict[str, Any]) -> list[str]:
    """Expand a range config ``{prefix, start, end}`` into pin name strings."""
    prefix = range_cfg["prefix"]
    start = int(range_cfg["start"])
    end = int(range_cfg["end"])
    return [f"{prefix}{i}" for i in range(start, end + 1)]


# ---------------------------------------------------------------------------
# Compiled normalisation pattern
# ---------------------------------------------------------------------------

# Placeholder syntax: {0}, {1}, … insert capture groups verbatim;
# {0:02} zero-pads the group to the given width (needed by profiles whose
# canonical names are zero-padded, e.g. nRF52840 "P0_05", SAMD "PA02").
_PLACEHOLDER_RE = re.compile(r"\{(\d+)(?::0(\d+))?\}")


class _NormPattern:
    """A single regex → output-template normalisation rule."""

    __slots__ = ("compiled", "output")

    def __init__(self, regex: str, output: str) -> None:
        self.compiled: re.Pattern[str] = re.compile(regex, re.IGNORECASE)
        self.output = output

    def try_match(self, text: str) -> str | None:
        """Return the formatted output if *text* matches, else ``None``."""
        m = self.compiled.fullmatch(text)
        if m is None:
            return None
        groups = m.groups()

        def _substitute(placeholder: re.Match[str]) -> str:
            index = int(placeholder.group(1))
            if index >= len(groups) or groups[index] is None:
                return placeholder.group(0)
            value = groups[index]
            width = placeholder.group(2)
            return value.zfill(int(width)) if width else value

        return _PLACEHOLDER_RE.sub(_substitute, self.output)


# ---------------------------------------------------------------------------
# TOMLProfile
# ---------------------------------------------------------------------------

class TOMLProfile(MCUProfile):
    """An ``MCUProfile`` whose pin data is loaded entirely from a TOML file.

    TOML schema
    -----------
    See ``profiles/README.md`` for the full specification.  The top-level
    keys are ``[profile]``, ``[normalization]``, ``[[pins.groups]]``,
    ``[[pins.individual]]``, and ``[[peripherals]]``.
    """

    def __init__(self, toml_path: Path | str) -> None:
        self._toml_path = Path(toml_path)
        self._config = self._load_toml(self._toml_path)

        # Validate schema BEFORE hydration — fail fast with clear errors.
        self.validation_warnings = validate_profile_toml(
            self._config, self._toml_path,
        )
        for w in self.validation_warnings:
            _logger.warning("%s: %s", self._toml_path.name, w)

        profile_cfg = self._config.get("profile", {})
        name: str = profile_cfg.get("name", self._toml_path.stem)

        # Normalization helpers (populated before super().__init__ calls
        # _initialize_pin_definitions / _initialize_peripherals).
        norm_cfg = self._config.get("normalization", {})
        self._canonical_prefix: str = norm_cfg.get("canonical_prefix", "")
        self._allow_numeric: bool = norm_cfg.get("allow_numeric", False)
        self._aliases: dict[str, str] = {
            k.upper(): v for k, v in norm_cfg.get("aliases", {}).items()
        }
        self._patterns: list[_NormPattern] = [
            _NormPattern(p["regex"], p["output"])
            for p in norm_cfg.get("patterns", [])
        ]

        # Store display metadata for downstream use.
        self.display_name: str = profile_cfg.get("display_name", name.upper())
        self.description: str = profile_cfg.get("description", "")
        self.family: str = profile_cfg.get("family", "")

        super().__init__(name)

    # -- TOML loading -------------------------------------------------------

    @staticmethod
    def _load_toml(path: Path) -> dict[str, Any]:
        with path.open("rb") as fh:
            return tomllib.load(fh)

    # -- MCUProfile abstract implementations --------------------------------

    def _initialize_pin_definitions(self) -> None:
        pins_cfg = self._config.get("pins", {})

        # 1. Process groups first (range or explicit names).
        for group in pins_cfg.get("groups", []):
            caps = _parse_capabilities(group.get("capabilities", ["gpio"]))

            if "range" in group:
                names = _expand_range(group["range"])
            elif "names" in group:
                names = list(group["names"])
            else:
                continue

            for pin_name in names:
                self.pins[pin_name] = PinInfo(
                    name=pin_name,
                    capabilities=caps.copy(),
                )

        # 2. Process individual pins (may extend or override groups).
        for pin in pins_cfg.get("individual", []):
            name = pin["name"]

            if name in self.pins:
                info = self.pins[name]
            else:
                info = PinInfo(name=name, capabilities=set())
                self.pins[name] = info

            # Full replacement of capabilities.
            if "capabilities" in pin:
                info.capabilities = _parse_capabilities(pin["capabilities"])

            # Additive capabilities (on top of group or existing).
            if "add_capabilities" in pin:
                info.capabilities |= _parse_capabilities(pin["add_capabilities"])

            if "special_function" in pin:
                info.special_function = pin["special_function"]
            if "special_function_short" in pin:
                info.special_function_short = pin["special_function_short"]
            if "warnings" in pin:
                info.warnings = list(pin["warnings"])
            if "alternate_names" in pin:
                info.alternate_names = list(pin["alternate_names"])

    def _initialize_peripherals(self) -> None:
        for peri in self._config.get("peripherals", []):
            self.peripherals.append(
                PeripheralInfo(
                    name=peri["name"],
                    instance=peri.get("instance", 0),
                    pins=dict(peri.get("pins", {})),
                )
            )

    def normalize_pin_name(self, pin_name: str) -> str:
        """Normalize *pin_name* using the rules declared in the TOML file.

        Order of precedence:
        1. Direct alias lookup.
        2. Exact match against known canonical pin names.
        3. Regex patterns (tried in declaration order).
        4. Bare-number expansion (if ``allow_numeric`` is true).

        Raises:
            ValueError: If *pin_name* cannot be normalised.
        """
        if not pin_name:
            msg = "Pin name cannot be empty"
            raise ValueError(msg)

        cleaned = pin_name.strip().upper()

        # 1. Direct aliases.
        if cleaned in self._aliases:
            canonical = self._aliases[cleaned]
            if canonical in self.pins:
                return canonical

        # 2. Already a known pin name.
        if cleaned in self.pins:
            return cleaned

        # 3. Regex patterns.
        for pat in self._patterns:
            candidate = pat.try_match(cleaned)
            if candidate is not None and candidate in self.pins:
                return candidate

        # 4. Bare numeric.
        if self._allow_numeric and cleaned.isdigit():
            candidate = f"{self._canonical_prefix}{int(cleaned)}"
            if candidate in self.pins:
                return candidate

        msg = (
            f"Cannot normalize pin name '{pin_name}' "
            f"for {self.mcu_name}"
        )
        raise ValueError(msg)

    # -- Convenience --------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"TOMLProfile({self._toml_path.name!r}, "
            f"pins={len(self.pins)}, peripherals={len(self.peripherals)})"
        )
