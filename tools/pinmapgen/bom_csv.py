"""
BOM CSV Parser for PinmapGen.

Parses CSV exports from Fusion Electronics BOM/netlist exports.
Uses csv.DictReader for parsing.
"""

import csv
from pathlib import Path
from typing import Any


def parse_csv(csv_path: Path | str) -> list[dict[str, Any]]:
    """
    Parse CSV netlist export.
    
    Args:
        csv_path: Path to the CSV file (Path object or string)
        
    Returns:
        List of dictionaries containing net information
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValueError: If CSV has invalid format
    """
    # Ensure we have a Path object
    if isinstance(csv_path, str):
        csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    rows = []
    try:
        with open(csv_path, encoding="utf-8") as csvfile:
            # Use DictReader to automatically handle headers
            reader = csv.DictReader(csvfile)

            # Check if required columns exist
            required_columns = {"Net", "Pin", "Component", "RefDes"}
            if not required_columns.issubset(set(reader.fieldnames or [])):
                missing = required_columns - set(reader.fieldnames or [])
                raise ValueError(f"CSV missing required columns: {missing}")

            # Read all rows
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is line 1)
                # Validate row has data
                if not any(row.values()):
                    continue  # Skip empty rows

                # Clean up whitespace
                cleaned_row = {k: v.strip() if v else "" for k, v in row.items()}

                # Validate required fields are not empty
                for field in required_columns:
                    if not cleaned_row.get(field):
                        raise ValueError(f"Empty {field} at line {row_num}")

                rows.append(cleaned_row)

    except UnicodeDecodeError:
        raise ValueError(f"CSV file encoding error: {csv_path}")
    except csv.Error as e:
        raise ValueError(f"CSV parsing error: {e}")

    if not rows:
        raise ValueError("CSV file contains no valid data rows")

    return rows


def parse_netlist_tuples(csv_path: Path | str, mcu_ref: str) -> list[tuple[str, str, str]]:
    """
    Parse CSV netlist into (net_name, refdes, pin) tuples, filtering for the MCU ref.
    
    Args:
        csv_path: Path to the CSV file
        mcu_ref: MCU reference designator to filter for (e.g., "U1")
        
    Returns:
        List of (net_name, refdes, pin) tuples for the specified MCU
        
    Raises:
        ValueError: If no entries found for the specified MCU reference
    """
    csv_data = parse_csv(csv_path)

    # Filter for the specified MCU reference and extract tuples
    mcu_tuples = []
    for row in csv_data:
        if row["RefDes"] == mcu_ref:
            net_name = row["Net"]
            refdes = row["RefDes"]
            pin = row["Pin"]
            mcu_tuples.append((net_name, refdes, pin))

    if not mcu_tuples:
        raise ValueError(f"No entries found for MCU reference '{mcu_ref}'")

    return mcu_tuples


def extract_nets(csv_data: list[dict[str, Any]], mcu_ref: str = None) -> dict[str, list[str]]:
    """
    Extract net to pin mappings from CSV data.
    
    Args:
        csv_data: Parsed CSV data
        mcu_ref: Optional MCU reference to filter for. If None, processes all entries.
        
    Returns:
        Dictionary mapping net names to pin lists
    """
    net_to_pins = {}

    for row in csv_data:
        # Filter by MCU reference if specified
        if mcu_ref and row["RefDes"] != mcu_ref:
            continue

        net_name = row["Net"]
        pin = row["Pin"]

        # Add pin to net mapping
        if net_name not in net_to_pins:
            net_to_pins[net_name] = []

        # Avoid duplicate pins for the same net
        if pin not in net_to_pins[net_name]:
            net_to_pins[net_name].append(pin)

    return net_to_pins


def get_mcu_nets(csv_path: Path | str, mcu_ref: str) -> dict[str, list[str]]:
    """
    Convenience function to parse CSV and extract nets for a specific MCU.
    
    Args:
        csv_path: Path to the CSV file
        mcu_ref: MCU reference designator (e.g., "U1")
        
    Returns:
        Dictionary mapping net names to pin lists for the specified MCU
    """
    csv_data = parse_csv(csv_path)
    return extract_nets(csv_data, mcu_ref)
