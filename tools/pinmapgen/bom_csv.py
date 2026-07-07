"""
BOM CSV Parser for PinmapGen.

Parses CSV exports from Fusion Electronics BOM/netlist exports.
Uses csv.DictReader for parsing.
"""

import csv
import sys
from pathlib import Path
from typing import Any

# Maximum number of per-row skip warnings printed before summarizing.
_MAX_SKIP_WARNINGS = 10


def _normalize_refdes(value: str) -> str:
    """Normalize reference designator for stable comparisons."""
    return value.strip().upper()


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
        msg = f"CSV file not found: {csv_path}"
        raise FileNotFoundError(msg)

    rows = []
    try:
        with csv_path.open(encoding="utf-8-sig") as csvfile:
            # Use DictReader to automatically handle headers
            reader = csv.DictReader(csvfile)

            # Check if required columns exist
            required_columns = {"Net", "Pin", "Component", "RefDes"}
            if not required_columns.issubset(set(reader.fieldnames or [])):
                missing = required_columns - set(reader.fieldnames or [])
                msg = f"CSV missing required columns: {missing}"
                raise ValueError(msg)

            # Read all rows. Rows with missing required fields are skipped
            # with a warning rather than aborting the whole file — real CAD
            # exports routinely contain no-connect pins or partial rows for
            # components that aren't relevant to the pinmap.
            skipped: list[str] = []
            for row_num, row in enumerate(
                reader, start=2
            ):  # Start at 2 (header is line 1)
                # Validate row has data
                if not any(row.values()):
                    continue  # Skip empty rows

                # Clean up whitespace
                cleaned_row = {k: v.strip() if v else "" for k, v in row.items()}

                missing = sorted(
                    field
                    for field in required_columns
                    if not cleaned_row.get(field)
                )
                if missing:
                    skipped.append(
                        f"line {row_num}: empty {', '.join(missing)}"
                    )
                    continue

                rows.append(cleaned_row)

            # Cap the per-row warnings so a large export full of no-connect
            # rows doesn't flood the console.
            for entry in skipped[:_MAX_SKIP_WARNINGS]:
                print(f"Warning: Skipping CSV {entry}", file=sys.stderr)
            if len(skipped) > _MAX_SKIP_WARNINGS:
                print(
                    f"Warning: ...and {len(skipped) - _MAX_SKIP_WARNINGS} "
                    f"more rows skipped ({len(skipped)} total)",
                    file=sys.stderr,
                )

    except UnicodeDecodeError:
        msg = f"CSV file encoding error: {csv_path}"
        raise ValueError(msg) from None
    except csv.Error as e:
        msg = f"CSV parsing error: {e}"
        raise ValueError(msg) from e

    if not rows:
        msg = "CSV file contains no valid data rows"
        raise ValueError(msg)

    return rows


def parse_netlist_tuples(
    csv_path: Path | str, mcu_ref: str
) -> list[tuple[str, str, str]]:
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
    normalized_ref = _normalize_refdes(mcu_ref)
    mcu_tuples = []
    for row in csv_data:
        if _normalize_refdes(row["RefDes"]) == normalized_ref:
            net_name = row["Net"]
            refdes = row["RefDes"]
            pin = row["Pin"]
            mcu_tuples.append((net_name, refdes, pin))

    if not mcu_tuples:
        msg = f"No entries found for MCU reference '{mcu_ref}'"
        raise ValueError(msg)

    return mcu_tuples


def extract_nets(
    csv_data: list[dict[str, Any]], mcu_ref: str | None = None
) -> dict[str, list[str]]:
    """
    Extract net to pin mappings from CSV data.

    Args:
        csv_data: Parsed CSV data
        mcu_ref: Optional MCU reference to filter for. If None, processes all entries.

    Returns:
        Dictionary mapping net names to pin lists
    """
    net_to_pins = {}
    normalized_ref = _normalize_refdes(mcu_ref) if mcu_ref else None

    for row in csv_data:
        # Filter by MCU reference if specified
        if normalized_ref and _normalize_refdes(row["RefDes"]) != normalized_ref:
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
    net_map = extract_nets(csv_data, mcu_ref)
    if not net_map:
        msg = f"No entries found for MCU reference '{mcu_ref}'"
        raise ValueError(msg)
    return net_map
