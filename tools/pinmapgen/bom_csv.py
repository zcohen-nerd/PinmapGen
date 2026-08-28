"""
BOM CSV Parser for PinmapGen.

Parses CSV netlist exports. Deliberately forgiving about the things CAD
tools and spreadsheets get wrong: headers are matched case-insensitively
with common aliases (``Designator`` for ``RefDes``, ``Net Name`` for
``Net``), the delimiter is sniffed (comma, semicolon, or tab), ragged
rows are skipped with a line-numbered warning instead of crashing, and
only ``Net``/``Pin``/``RefDes`` are actually required.
"""

import csv
import re
import sys
from pathlib import Path
from typing import Any

# Maximum number of per-row skip warnings printed before summarizing.
_MAX_SKIP_WARNINGS = 10

# Columns the parser needs. Component is carried through when present but
# is not required - nothing downstream reads it.
_REQUIRED_COLUMNS = ("Net", "Pin", "RefDes")
_ALL_COLUMNS = ("Net", "Pin", "Component", "RefDes")

# Accepted header spellings, matched after lowercasing and collapsing
# whitespace/underscores. Covers the names CAD tools actually emit.
_HEADER_ALIASES = {
    "net": "Net",
    "net name": "Net",
    "netname": "Net",
    "signal": "Net",
    "signal name": "Net",
    "pin": "Pin",
    "pin name": "Pin",
    "pinname": "Pin",
    "pin number": "Pin",
    "pin no": "Pin",
    "refdes": "RefDes",
    "ref des": "RefDes",
    "ref": "RefDes",
    "reference": "RefDes",
    "reference designator": "RefDes",
    "designator": "RefDes",
    "component": "Component",
    "component name": "Component",
    "part": "Component",
    "part name": "Component",
    "device": "Component",
}


def _normalize_refdes(value: str) -> str:
    """Normalize reference designator for stable comparisons."""
    return value.strip().upper()


def _normalize_header(header: str) -> str:
    """Lowercase a header and collapse whitespace/underscores."""
    return re.sub(r"[\s_]+", " ", header.strip().strip('"').lower())


def _sniff_delimiter(header_line: str) -> str:
    """Pick the delimiter from the header line: comma, semicolon, or tab.

    European Excel saves semicolon-delimited "CSV"; some tools export
    TSV. Counting candidates in the header line is more predictable than
    csv.Sniffer for these short, regular files.
    """
    counts = {d: header_line.count(d) for d in (",", ";", "\t")}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] > 0 else ","


def _format_available_refs(rows: list[dict[str, Any]], limit: int = 12) -> str:
    """Summarize the reference designators a CSV actually contains."""
    refs = sorted({_normalize_refdes(r["RefDes"]) for r in rows if r["RefDes"]})
    if not refs:
        return ""
    shown = ", ".join(refs[:limit])
    if len(refs) > limit:
        shown += f", ... ({len(refs)} total)"
    return shown


def parse_csv(csv_path: Path | str) -> list[dict[str, Any]]:
    """
    Parse CSV netlist export.

    Args:
        csv_path: Path to the CSV file (Path object or string)

    Returns:
        List of row dictionaries with the keys Net, Pin, Component,
        RefDes (Component is "" when the file has no such column).

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

    try:
        # utf-8-sig strips the BOM Excel puts on UTF-8 exports.
        text = csv_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        msg = (
            f"CSV file encoding error: {csv_path} - expected UTF-8. "
            "In Excel, save as 'CSV UTF-8'; from other tools, re-export "
            "with UTF-8 encoding."
        )
        raise ValueError(msg) from None

    lines = text.splitlines()
    first_content = next((ln for ln in lines if ln.strip()), "")
    delimiter = _sniff_delimiter(first_content)

    rows: list[dict[str, Any]] = []
    skipped: list[str] = []
    try:
        raw_rows = list(csv.reader(lines, delimiter=delimiter))
    except csv.Error as e:
        msg = f"CSV parsing error: {e}"
        raise ValueError(msg) from e

    # Locate the header row (first non-empty row).
    header_idx = next(
        (i for i, row in enumerate(raw_rows) if any(c.strip() for c in row)),
        None,
    )
    if header_idx is None:
        msg = "CSV file contains no valid data rows"
        raise ValueError(msg)

    header = [cell.strip() for cell in raw_rows[header_idx]]
    # Map column index -> canonical name via the alias table.
    column_of: dict[int, str] = {}
    for i, cell in enumerate(header):
        canonical = _HEADER_ALIASES.get(_normalize_header(cell))
        if canonical and canonical not in column_of.values():
            column_of[i] = canonical

    missing = [c for c in _REQUIRED_COLUMNS if c not in column_of.values()]
    if missing:
        msg = (
            f"CSV is missing required column(s): {', '.join(missing)}. "
            f"Found columns: {', '.join(header) or '(none)'}. "
            "Headers are matched case-insensitively, and common aliases "
            "are accepted (e.g. 'Designator' for RefDes, 'Net Name' for "
            "Net); the Component column is optional."
        )
        raise ValueError(msg)

    for line_num, raw in enumerate(
        raw_rows[header_idx + 1 :], start=header_idx + 2
    ):
        if not any(cell.strip() for cell in raw):
            continue  # Skip empty rows

        # A row with extra non-empty cells beyond the header means an
        # unquoted delimiter shifted the fields - the row can't be
        # trusted, so skip it with a pointer instead of crashing.
        extra = raw[len(header):]
        if any(cell.strip() for cell in extra):
            skipped.append(
                f"line {line_num}: more fields than the header "
                f"({len(raw)} vs {len(header)}) - unquoted "
                f"'{delimiter}' in a value?"
            )
            continue

        cleaned_row = dict.fromkeys(_ALL_COLUMNS, "")
        for i, canonical in column_of.items():
            value = raw[i] if i < len(raw) else ""
            cleaned_row[canonical] = value.strip()

        # Rows with missing required fields are skipped with a warning
        # rather than aborting the whole file - real CAD exports contain
        # no-connect pins and partial rows.
        empty = sorted(
            field for field in _REQUIRED_COLUMNS if not cleaned_row[field]
        )
        if empty:
            skipped.append(f"line {line_num}: empty {', '.join(empty)}")
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
        available = _format_available_refs(csv_data)
        if available:
            msg += f". Reference designators in this file: {available}"
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
        available = _format_available_refs(csv_data)
        if available:
            msg += f". Reference designators in this file: {available}"
        raise ValueError(msg)
    return net_map
