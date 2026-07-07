#!/usr/bin/env python3
"""
PinmapGen CLI - Command Line Interface for generating pinmaps from Fusion Electronics exports.

Usage:
    python -m tools.pinmapgen.cli --sch|--csv --mcu rp2040 --mcu-ref U1 --out-root . [--mermaid]
    python -m tools.pinmapgen.cli --list-mcus
    python -m tools.pinmapgen.cli profiles list [--profile-dir DIR]
    python -m tools.pinmapgen.cli profiles check <name> [--profile-dir DIR]
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any

# Import parser and MCU profile modules
from . import (
    bom_csv,
    eagle_sch,
    emit_arduino,
    emit_json,
    emit_markdown,
    emit_mermaid,
    emit_micropython,
)
from .profile_registry import registry

# Legacy MCU_PROFILES dict kept for backward compatibility.  Code that
# imports ``cli.MCU_PROFILES`` will still work; the registry is the
# canonical source of truth at runtime.
MCU_PROFILES = {name: name for name in registry.list_profiles()}


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    available = registry.list_profiles()

    parser = argparse.ArgumentParser(
        description="Generate pinmaps from Fusion Electronics exports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tools.pinmapgen.cli --csv hardware/exports/netlist.csv --mcu rp2040 --mcu-ref U1 --out-root .
  python -m tools.pinmapgen.cli --sch hardware/exports/project.sch --mcu rp2040 --mcu-ref U1 --out-root . --mermaid
  python -m tools.pinmapgen.cli --list-mcus
  python -m tools.pinmapgen.cli --csv netlist.csv --mcu my_mcu --mcu-ref U1 --profile-dir ./my_profiles
        """,
    )

    # Input source (mutually exclusive) — not required when --list-mcus
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument("--csv", type=Path, help="CSV netlist export file")
    input_group.add_argument("--sch", type=Path, help="EAGLE schematic file (.sch)")

    # MCU configuration
    parser.add_argument(
        "--mcu",
        help=(
            "MCU profile name. Built-in profiles: "
            + ", ".join(available)
            + ". Use --list-mcus to see all available."
        ),
    )
    parser.add_argument(
        "--mcu-ref", help="MCU reference designator (e.g., U1)"
    )

    # Profile discovery
    parser.add_argument(
        "--profile-dir",
        type=Path,
        help="Additional directory containing custom TOML MCU profiles",
    )
    parser.add_argument(
        "--list-mcus",
        action="store_true",
        help="List all available MCU profiles and exit",
    )

    # Output configuration
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path(),
        help="Output root directory (default: current directory)",
    )
    parser.add_argument(
        "--mermaid", action="store_true", help="Generate Mermaid diagram files"
    )

    # Optional flags
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit with a non-zero status (2) if the pinmap has validation "
            "errors or pins that failed to normalize, instead of only "
            "printing warnings. Recommended for CI."
        ),
    )
    parser.add_argument(
        "--reproducible",
        action="store_true",
        help="Produce reproducible output (fixed timestamps)",
    )
    parser.add_argument(
        "--version", action="version", version="%(prog)s 0.1.0",
    )

    args = parser.parse_args()

    # Register user profile directory before validation.
    if args.profile_dir:
        try:
            registry.add_profile_dir(args.profile_dir)
        except FileNotFoundError as exc:
            parser.error(str(exc))

    # Handle --list-mcus early.
    if args.list_mcus:
        _print_profile_list()
        sys.exit(0)

    # When not listing, --csv/--sch, --mcu, and --mcu-ref are required.
    if not args.csv and not args.sch:
        parser.error("one of --csv or --sch is required")
    if not args.mcu:
        parser.error("--mcu is required")
    if not args.mcu_ref:
        parser.error("--mcu-ref is required")

    # Validate MCU name against registry.
    if args.mcu.lower() not in registry:
        available_now = registry.list_profiles()
        parser.error(
            f"Unknown MCU profile '{args.mcu}'. "
            f"Available: {', '.join(available_now)}"
        )

    return args


def _print_profile_list() -> None:
    """Print a formatted list of available MCU profiles."""
    profiles = registry.list_profiles()
    if not profiles:
        print("No MCU profiles found.")
        return

    print(f"{'Name':<16} {'Display':<16} {'Family':<8} {'Source':<8} Description")
    print("-" * 80)
    for name in profiles:
        info = registry.get_profile_info(name)
        print(
            f"{info['name']:<16} "
            f"{info.get('display_name', ''):<16} "
            f"{info.get('family', ''):<8} "
            f"{info['source']:<8} "
            f"{info.get('description', '')}"
        )


def parse_input_file(args: argparse.Namespace) -> dict[str, list[str]]:
    """Parse input file and extract net-to-pin mappings."""
    if args.csv:
        if args.verbose:
            print(f"Parsing CSV file: {args.csv}")

        # Check if file exists
        if not args.csv.exists():
            print(f"Error: CSV file not found: {args.csv}", file=sys.stderr)
            sys.exit(1)

        # Parse CSV and extract nets for the specified MCU
        nets = bom_csv.get_mcu_nets(args.csv, args.mcu_ref)

    elif args.sch:
        if args.verbose:
            print(f"Parsing EAGLE schematic: {args.sch}")

        # Check if file exists
        if not args.sch.exists():
            print(f"Error: Schematic file not found: {args.sch}", file=sys.stderr)
            sys.exit(1)

        # Parse schematic and extract nets for the specified MCU
        nets = eagle_sch.get_mcu_nets_from_schematic(args.sch, args.mcu_ref)

    else:
        print("Error: No input file specified", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Found {len(nets)} nets")

    return nets


def create_canonical_pinmap(
    nets: dict[str, list[str]], mcu_name: str, verbose: bool = False
) -> dict[str, Any]:
    """Create canonical pinmap dictionary with normalization and validation."""
    if verbose:
        print(f"Normalizing pins for {mcu_name}")

    try:
        # Get MCU profile from registry
        profile = registry.get_profile(mcu_name)

        # Create canonical pinmap using profile
        canonical_dict = profile.create_canonical_pinmap(nets)

        if verbose:
            metadata = canonical_dict.get("metadata", {})
            print(f"  - Total nets: {metadata.get('total_nets', 0)}")
            print(f"  - Total pins: {metadata.get('total_pins', 0)}")

            diff_pairs = canonical_dict.get("differential_pairs", [])
            if diff_pairs:
                print(f"  - Detected {len(diff_pairs)} differential pairs:")
                for pair in diff_pairs:
                    pos = pair.get("positive")
                    neg = pair.get("negative")
                    print(f"    • {pos} / {neg}")

            special_pins = metadata.get("special_pins_used", [])
            if special_pins:
                print(f"  - Special pins used: {', '.join(special_pins)}")

        return canonical_dict

    except (ValueError, KeyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def generate_outputs(canonical_dict: dict[str, Any], args: argparse.Namespace) -> None:
    """Generate all output files from canonical dictionary."""
    out_root = args.out_root

    # Ensure output directories exist
    (out_root / "pinmaps").mkdir(parents=True, exist_ok=True)
    (out_root / "firmware" / "micropython").mkdir(parents=True, exist_ok=True)
    (out_root / "firmware" / "include").mkdir(parents=True, exist_ok=True)
    (out_root / "firmware" / "docs").mkdir(parents=True, exist_ok=True)

    if args.verbose:
        print("Generating output files...")

    # Generate canonical JSON pinmap
    json_path = out_root / "pinmaps" / "pinmap.json"
    emit_json.emit_json(canonical_dict, json_path)
    if args.verbose:
        print(f"  - {json_path}")

    # Generate MicroPython module
    micropython_path = out_root / "firmware" / "micropython" / "pinmap_micropython.py"
    emit_micropython.emit_micropython(canonical_dict, micropython_path)
    if args.verbose:
        print(f"  - {micropython_path}")

    # Generate Arduino header
    arduino_path = out_root / "firmware" / "include" / "pinmap_arduino.h"
    emit_arduino.emit_arduino_header(canonical_dict, arduino_path)
    if args.verbose:
        print(f"  - {arduino_path}")

    # Generate Markdown documentation
    markdown_path = out_root / "firmware" / "docs" / "PINOUT.md"
    emit_markdown.emit_markdown_docs(canonical_dict, markdown_path)
    if args.verbose:
        print(f"  - {markdown_path}")

    # Generate Mermaid diagram (if requested)
    if args.mermaid:
        mermaid_path = out_root / "firmware" / "docs" / "pinout.mmd"
        emit_mermaid.emit_mermaid_diagram(canonical_dict, mermaid_path)
        if args.verbose:
            print(f"  - {mermaid_path}")


def _profiles_main(argv: list[str]) -> int:
    """Handle the ``profiles`` subcommand (list / check).

    Returns an exit code (0 = success).
    """
    parser = argparse.ArgumentParser(
        prog="pinmapgen profiles",
        description="Profile management utilities",
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        help="Additional directory containing custom TOML MCU profiles",
    )
    sub = parser.add_subparsers(dest="action")
    sub.required = True

    sub.add_parser("list", help="List available MCU profiles")

    check_p = sub.add_parser("check", help="Validate and inspect a profile")
    check_p.add_argument("name", help="Profile name to check")

    args = parser.parse_args(argv)

    # Register user profile directory if provided.
    if args.profile_dir:
        try:
            registry.add_profile_dir(args.profile_dir)
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if args.action == "list":
        return _profiles_list_cmd()
    if args.action == "check":
        return _profiles_check_cmd(args.name)
    return 1  # pragma: no cover


def _profiles_list_cmd() -> int:
    """Print a formatted table of all registered profiles."""
    profiles = registry.list_profiles()
    if not profiles:
        print("No MCU profiles found.")
        return 0

    # Table header
    print(
        f"{'Name':<16} {'Source':<8} {'Schema':<8} "
        f"{'Family':<8} Description"
    )
    print("-" * 76)
    for name in profiles:
        info = registry.get_profile_info(name)
        sv = info.get("schema_version")
        sv_str = str(sv) if sv is not None else "-"
        print(
            f"{info['name']:<16} "
            f"{info['source']:<8} "
            f"{sv_str:<8} "
            f"{info.get('family', ''):<8} "
            f"{info.get('description', '')}"
        )
    return 0


def _profiles_check_cmd(name: str) -> int:
    """Validate and summarise a single profile."""
    key = name.lower()
    if key not in registry:
        print(f"Error: Unknown profile '{name}'.", file=sys.stderr)
        available = registry.list_profiles()
        if available:
            print(
                f"Available: {', '.join(available)}", file=sys.stderr,
            )
        return 1

    info = registry.get_profile_info(key)
    print(f"Profile:         {info['name']}")
    print(f"Source:          {info['source']}")
    if info.get("path"):
        print(f"Path:            {info['path']}")
    if info.get("class"):
        print(f"Class:           {info['class']}")
    sv = info.get("schema_version")
    print(f"Schema version:  {sv if sv is not None else '-'}")
    print(f"Family:          {info.get('family', '') or '-'}")
    print(f"Display name:    {info.get('display_name', '') or '-'}")
    desc = info.get("description", "")
    if desc:
        print(f"Description:     {desc}")

    # Attempt full instantiation to catch validation / hydration errors.
    try:
        profile = registry.get_profile(key)
    except Exception as exc:
        print(f"\nValidation FAILED: {exc}", file=sys.stderr)
        return 1

    # Summary statistics.
    pin_count = len(profile.pins)
    peripheral_count = len(profile.peripherals)
    special_pins = [
        p.name for p in profile.pins.values()
        if p.special_function
    ]

    print(f"Pin count:       {pin_count}")
    print(f"Peripherals:     {peripheral_count}")
    if special_pins:
        print(f"Special pins:    {len(special_pins)} ({', '.join(special_pins)})")

    # If TOML, report validation warnings from the loader.
    if hasattr(profile, "validation_warnings") and profile.validation_warnings:
        print(f"\nWarnings ({len(profile.validation_warnings)}):")
        for w in profile.validation_warnings:
            print(f"  - {w}")
    else:
        print("\nValidation OK — no warnings.")

    return 0


def main():
    """Main CLI entry point."""
    # Check for ``profiles`` subcommand before normal argparse.
    if len(sys.argv) > 1 and sys.argv[1] == "profiles":
        sys.exit(_profiles_main(sys.argv[2:]))

    args = None
    try:
        # Parse command line arguments
        args = parse_arguments()

        if args.verbose:
            print("PinmapGen - Fusion Electronics to Firmware Bridge")
            print(f"MCU: {args.mcu} (ref: {args.mcu_ref})")
            print(f"Output root: {args.out_root}")
            print()

        # Enable reproducible builds
        if args.reproducible:
            os.environ.setdefault("SOURCE_DATE_EPOCH", "0")

        # Parse input file and extract nets
        nets = parse_input_file(args)

        # Create canonical pinmap with normalization and validation
        canonical_dict = create_canonical_pinmap(nets, args.mcu, args.verbose)

        # In strict mode, refuse to write outputs from a pinmap with
        # validation errors or dropped pins (details were already printed
        # to stderr during normalization).
        if args.strict:
            metadata = canonical_dict.get("metadata", {})
            validation_errors = metadata.get("validation_errors", [])
            dropped_pins = metadata.get("dropped_pins", [])
            if validation_errors or dropped_pins:
                print(
                    f"Strict mode: {len(validation_errors)} validation "
                    f"error(s), {len(dropped_pins)} dropped pin(s) — "
                    "no output written. Fix the netlist or rerun without "
                    "--strict.",
                    file=sys.stderr,
                )
                sys.exit(2)

        # Generate all output files
        generate_outputs(canonical_dict, args)

        if args.verbose:
            print("\nPinmap generation completed successfully!")
        else:
            print("Pinmap files generated successfully")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args is not None and args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
