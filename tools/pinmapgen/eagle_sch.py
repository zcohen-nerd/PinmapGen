"""
EAGLE Schematic Parser for PinmapGen.

Parses EAGLE .sch XML files using xml.etree.ElementTree.
Extracts net and pin information from schematic data.
"""

import xml.etree.ElementTree as ET
from pathlib import Path


def _available_parts(root) -> str:
    """Summarize the part names (reference designators) in a schematic."""
    names = sorted({
        pinref.get("part")
        for pinref in root.iter("pinref")
        if pinref.get("part")
    } | {
        part.get("name")
        for part in root.iter("part")
        if part.get("name")
    })
    if not names:
        return ""
    shown = ", ".join(names[:12])
    if len(names) > 12:
        shown += f", ... ({len(names)} total)"
    return shown


def _normalize_refdes(value: str) -> str:
    """Normalize reference designator for stable comparisons."""
    return value.strip().upper()


def parse_schematic(sch_path: Path | str) -> ET.Element:
    """
    Parse EAGLE schematic XML file.

    Args:
        sch_path: Path to the .sch file (Path object or string)

    Returns:
        XML root element

    Raises:
        FileNotFoundError: If schematic file doesn't exist
        ET.ParseError: If XML parsing fails
        ValueError: If file is not a valid EAGLE schematic
    """
    # Ensure we have a Path object
    if isinstance(sch_path, str):
        sch_path = Path(sch_path)

    if not sch_path.exists():
        msg = f"Schematic file not found: {sch_path}"
        raise FileNotFoundError(msg)

    try:
        tree = ET.parse(sch_path)
        root = tree.getroot()
    except ET.ParseError as e:
        msg = f"Failed to parse XML in {sch_path}: {e}"
        raise ET.ParseError(msg) from e

    # Validate this is an EAGLE schematic
    if root.tag != "eagle":
        msg = f"File {sch_path} is not a valid EAGLE file (root tag: {root.tag})"
        raise ValueError(
            msg
        )

    # Check for schematic section
    schematic = root.find("drawing/schematic")
    if schematic is None:
        msg = f"File {sch_path} does not contain schematic data"
        raise ValueError(msg)

    return root


def extract_nets_from_schematic(root: ET.Element, mcu_ref: str) -> dict[str, list[str]]:
    """
    Extract net to pin mappings from schematic XML.

    Args:
        root: XML root element from parsed EAGLE schematic
        mcu_ref: MCU reference designator (e.g., "U1")

    Returns:
        Dictionary mapping net names to pin lists
    """
    net_to_pins = {}
    normalized_ref = _normalize_refdes(mcu_ref)
    schematic = root.find("drawing/schematic")

    if schematic is None:
        return net_to_pins

    # Get all sheets
    sheets = schematic.findall("sheets/sheet")

    for sheet in sheets:
        # Find all nets in this sheet
        nets = sheet.findall("nets/net")

        for net in nets:
            net_name = net.get("name")
            if not net_name:
                continue

            # Find all segments in this net
            segments = net.findall("segment")

            for segment in segments:
                # Find pinrefs in this segment
                pinrefs = segment.findall("pinref")

                for pinref in pinrefs:
                    part_ref = pinref.get("part")
                    pin_name = pinref.get("pin")

                    if (
                        part_ref
                        and pin_name
                        and _normalize_refdes(part_ref) == normalized_ref
                    ):
                        # Add pin to net mapping
                        if net_name not in net_to_pins:
                            net_to_pins[net_name] = []

                        # Avoid duplicate pins for the same net
                        if pin_name not in net_to_pins[net_name]:
                            net_to_pins[net_name].append(pin_name)

    return net_to_pins


def get_mcu_nets_from_schematic(
    sch_path: Path | str, mcu_ref: str
) -> dict[str, list[str]]:
    """
    Convenience function to parse EAGLE schematic and extract nets for a specific MCU.

    Args:
        sch_path: Path to the .sch file
        mcu_ref: MCU reference designator (e.g., "U1")

    Returns:
        Dictionary mapping net names to pin lists for the specified MCU
    """
    root = parse_schematic(sch_path)
    net_map = extract_nets_from_schematic(root, mcu_ref)
    if not net_map:
        msg = f"No nets found for MCU reference '{mcu_ref}' in schematic"
        available = _available_parts(root)
        if available:
            msg += f". Parts in this schematic: {available}"
        raise ValueError(msg)
    return net_map
