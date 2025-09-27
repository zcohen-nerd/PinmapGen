"""
EAGLE Schematic Parser for PinmapGen.

Parses EAGLE .sch XML files using xml.etree.ElementTree.
Extracts net and pin information from schematic data.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


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
        raise FileNotFoundError(f"Schematic file not found: {sch_path}")

    try:
        tree = ET.parse(sch_path)
        root = tree.getroot()
    except ET.ParseError as e:
        raise ET.ParseError(f"Failed to parse XML in {sch_path}: {e}")

    # Validate this is an EAGLE schematic
    if root.tag != "eagle":
        raise ValueError(f"File {sch_path} is not a valid EAGLE file (root tag: {root.tag})")

    # Check for schematic section
    schematic = root.find("drawing/schematic")
    if schematic is None:
        raise ValueError(f"File {sch_path} does not contain schematic data")

    return root


def parse_schematic_tuples(sch_path: Path | str, mcu_ref: str) -> list[tuple[str, str, str]]:
    """
    Parse EAGLE schematic file and return (net_name, refdes, pin) tuples.
    
    Args:
        sch_path: Path to the .sch file
        mcu_ref: MCU reference designator to filter for (e.g., "U1")
        
    Returns:
        List of (net_name, refdes, pin) tuples for the specified MCU
        
    Raises:
        ValueError: If no nets found for the specified MCU reference
    """
    root = parse_schematic(sch_path)

    # Find all nets in the schematic
    nets_data = []
    schematic = root.find("drawing/schematic")

    if schematic is None:
        raise ValueError("No schematic section found in EAGLE file")

    # Get all sheets (EAGLE can have multi-sheet schematics)
    sheets = schematic.findall("sheets/sheet")
    if not sheets:
        raise ValueError("No sheets found in schematic")

    # Process each sheet
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
                # Find pinrefs in this segment (these connect to component pins)
                pinrefs = segment.findall("pinref")

                for pinref in pinrefs:
                    part_ref = pinref.get("part")
                    pin_name = pinref.get("pin")

                    if part_ref and pin_name:
                        # Filter for the specified MCU reference
                        if part_ref == mcu_ref:
                            nets_data.append((net_name, part_ref, pin_name))

    if not nets_data:
        raise ValueError(f"No nets found for MCU reference '{mcu_ref}' in schematic")

    return nets_data


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

                    if part_ref and pin_name and part_ref == mcu_ref:
                        # Add pin to net mapping
                        if net_name not in net_to_pins:
                            net_to_pins[net_name] = []

                        # Avoid duplicate pins for the same net
                        if pin_name not in net_to_pins[net_name]:
                            net_to_pins[net_name].append(pin_name)

    return net_to_pins


def get_mcu_nets_from_schematic(sch_path: Path | str, mcu_ref: str) -> dict[str, list[str]]:
    """
    Convenience function to parse EAGLE schematic and extract nets for a specific MCU.
    
    Args:
        sch_path: Path to the .sch file
        mcu_ref: MCU reference designator (e.g., "U1")
        
    Returns:
        Dictionary mapping net names to pin lists for the specified MCU
    """
    root = parse_schematic(sch_path)
    return extract_nets_from_schematic(root, mcu_ref)


def get_schematic_info(sch_path: Path | str) -> dict[str, Any]:
    """
    Extract general information from EAGLE schematic.
    
    Args:
        sch_path: Path to the .sch file
        
    Returns:
        Dictionary with schematic metadata
    """
    root = parse_schematic(sch_path)

    info = {
        "eagle_version": root.get("version", "unknown"),
        "sheets": [],
        "parts": [],
        "nets_count": 0
    }

    schematic = root.find("drawing/schematic")
    if schematic is None:
        return info

    # Get sheet information
    sheets = schematic.findall("sheets/sheet")
    for i, sheet in enumerate(sheets):
        sheet_info = {
            "index": i + 1,
            "nets": len(sheet.findall("nets/net")),
            "instances": len(sheet.findall("instances/instance"))
        }
        info["sheets"].append(sheet_info)
        info["nets_count"] += sheet_info["nets"]

    # Get parts information from first sheet (usually contains the parts list)
    if sheets:
        first_sheet = sheets[0]
        instances = first_sheet.findall("instances/instance")

        for instance in instances:
            part_name = instance.get("part")
            gate = instance.get("gate")
            if part_name:
                info["parts"].append({
                    "name": part_name,
                    "gate": gate or "A"
                })

    return info
