"""Net-name sanitization shared by the PinmapGen emitters.

Converts raw CAD net names into identifiers that are valid in generated
Python and C code. Previously each emitter carried its own copy of this
logic; this module is the single implementation.
"""

import re


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
            etc. suffixes to avoid collisions.

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
