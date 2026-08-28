"""Net-name sanitization shared by the PinmapGen emitters.

Converts raw CAD net names into identifiers that are valid in generated
Python and C code. Previously each emitter carried its own copy of this
logic; this module is the single implementation.
"""

import re

# Identifiers a generated constant must never shadow. One combined set is
# used for every output format so the same net gets the same constant in
# pinmap_micropython.py, pinmap_arduino.h, and PINOUT.md.
#
# Sanitized names are always uppercase, so only uppercase collisions
# matter. Sources:
# - MicroPython: the classes the generated module imports from `machine`
#   (a net named SPI would rebind the class and crash the helpers).
# - Arduino: core macros and globals that `#define SPI 4` would textually
#   rewrite inside <SPI.h>/<Wire.h>/pins_arduino.h, breaking compilation —
#   pin aliases (A0-A15, MOSI/MISO/SCK/SS/SDA/SCL, LED_BUILTIN, the SPI
#   object) and mode/state/interrupt macros.
RESERVED_IDENTIFIERS = frozenset(
    {
        # MicroPython machine classes
        "PIN", "I2C", "SPI", "PWM", "ADC", "UART",
        # Arduino SPI/I2C pin aliases and objects
        "MOSI", "MISO", "SCK", "SS", "SDA", "SCL", "SPI1", "SPI2",
        # Arduino pin/state/mode macros
        "LED_BUILTIN", "HIGH", "LOW",
        "INPUT", "OUTPUT", "INPUT_PULLUP", "INPUT_PULLDOWN",
        "RISING", "FALLING", "CHANGE",
        "DEFAULT", "EXTERNAL", "INTERNAL",
        "PI",
    }
    | {f"A{i}" for i in range(16)}  # Arduino analog pin aliases
)

# Suffix applied when a net's natural identifier is reserved.
_RESERVED_SUFFIX = "_PIN"


def sanitize_net_name(
    net_name: str, seen_names: dict[str, int] | None = None
) -> str:
    """Sanitize a net name for use as a Python constant / C macro.

    A trailing ``+`` or ``-`` is treated as a differential polarity marker
    and becomes a ``_P`` / ``_N`` suffix (so ``USB_D+``/``USB_D-`` yield
    ``USB_D_P``/``USB_D_N`` instead of colliding as ``USB_D``/``USB_D_2``).

    Args:
        net_name: Raw net name from the netlist.
        seen_names: Optional dict tracking previously emitted names.
            When provided, duplicate sanitized names receive ``_2``, ``_3``,
            etc. suffixes to avoid collisions. Compat-only: no production
            caller supplies it (collision handling lives in
            :func:`build_name_map`, which is reserved-name-aware and fair) —
            fold this parameter away at v0.2.0.

    Returns:
        Sanitized identifier (uppercase).
    """
    base = net_name.strip()

    # Preserve differential polarity markers before they would be lost.
    polarity = ""
    if base.endswith("+"):
        base, polarity = base[:-1], "_P"
    elif base.endswith("-"):
        base, polarity = base[:-1], "_N"

    # Remove invalid characters and replace with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", base)

    # Prefix leading digits with underscore (preserves names like 3V3)
    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized

    # Remove consecutive underscores
    sanitized = re.sub(r"_{2,}", "_", sanitized)

    # Remove trailing underscores only (keep leading _ for digit-prefixed
    # names), then re-attach the polarity suffix.
    sanitized = sanitized.rstrip("_") + polarity

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


def build_name_map(
    net_names: list[str] | tuple[str, ...],
    reserved: frozenset[str] = RESERVED_IDENTIFIERS,
) -> tuple[dict[str, str], list[str]]:
    """Map every net name to a unique, non-reserved identifier.

    All emitters build this map from the same canonical net list, so the
    same net gets the same constant name in every output file — and the
    result does not depend on iteration order:

    - A net whose natural identifier is reserved (``SPI``, ``MOSI``,
      ``A0``, …) gets a ``_PIN`` suffix instead of shadowing the language
      or Arduino-core symbol.
    - When several nets sanitize to the same identifier, the net that
      already *is* that identifier keeps it (``LED_1`` keeps ``LED_1``
      even when ``LED-1`` is present); the others get ``_2``, ``_3``, …
      suffixes in sorted order, and the suffixed result is re-checked so
      it can never silently collide with yet another net.

    Returns:
        (mapping, notes): the net→identifier mapping, plus one
        human-readable note per net that was renamed away from its
        natural sanitized form.
    """
    # Group nets by their natural sanitized identifier.
    groups: dict[str, list[str]] = {}
    for raw in sorted(set(net_names)):
        groups.setdefault(sanitize_net_name(raw), []).append(raw)

    # Every group's base is spoken for by its own nets: a synthetic _2/_3
    # suffix must never take a name some net naturally sanitizes to.
    natural_bases = set(groups)

    mapping: dict[str, str] = {}
    notes: list[str] = []
    used: set[str] = set()

    def _free(candidate: str, own_base: str) -> bool:
        if candidate in used:
            return False
        return candidate not in natural_bases or candidate == own_base

    for base in sorted(groups):
        raws = groups[base]
        # The net that already equals its sanitized form has first claim
        # on the clean name; the rest follow in sorted order.
        raws.sort(key=lambda raw: (raw != base, raw))

        effective_base = base
        if base in reserved:
            effective_base = base + _RESERVED_SUFFIX

        next_suffix = 2
        for i, raw in enumerate(raws):
            if i == 0 and _free(effective_base, base):
                final = effective_base
            else:
                while not _free(f"{effective_base}_{next_suffix}", base):
                    next_suffix += 1
                final = f"{effective_base}_{next_suffix}"
                next_suffix += 1
            used.add(final)
            mapping[raw] = final
            if final != base:
                if base in reserved:
                    reason = f"'{base}' is reserved in generated code"
                else:
                    reason = "identifier collides with another net"
                notes.append(
                    f"net '{raw}' is emitted as constant '{final}' ({reason})"
                )

    return mapping, notes
