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
from typing import Any, TextIO

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
from .naming import build_name_map
from .profile_registry import registry


class _LogTee:
    """Duplicate a console stream into the --log-file handle.

    GUI front ends (the Fusion ULP in particular) cannot reliably capture
    console output, so the CLI mirrors everything it prints — status,
    warnings, errors — into a file they can read back and display.
    """

    def __init__(self, console: TextIO, log_handle: TextIO) -> None:
        self.console = console
        self._log = log_handle

    def write(self, text: str) -> int:
        # Log first: a console encoding error must not lose the log line.
        self._log.write(text)
        return self.console.write(text)

    def flush(self) -> None:
        self._log.flush()
        self.console.flush()

    def __getattr__(self, name: str) -> Any:
        # Delegate everything else (encoding, isatty, ...) to the console.
        return getattr(self.console, name)


def _install_log_tee(argv: list[str]) -> TextIO | None:
    """Mirror stdout/stderr to the file named by ``--log-file``, if given.

    Scans argv directly instead of waiting for argparse so that argparse's
    own error output (usage errors print and exit before parsing finishes)
    reaches the log as well. Returns the open log handle, or None when no
    --log-file was requested or the file could not be opened.
    """
    path_str = None
    for i, arg in enumerate(argv):
        if arg == "--log-file" and i + 1 < len(argv):
            path_str = argv[i + 1]
        elif arg.startswith("--log-file="):
            path_str = arg.split("=", 1)[1]
    if not path_str:
        return None

    log_path = Path(path_str)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Held open for the whole run; closed in main()'s finally block.
        handle = log_path.open(  # noqa: SIM115
            "w", encoding="utf-8", errors="replace"
        )
    except OSError as exc:
        print(
            f"Warning: could not open log file {log_path}: {exc}",
            file=sys.stderr,
        )
        return None

    sys.stdout = _LogTee(sys.stdout, handle)
    sys.stderr = _LogTee(sys.stderr, handle)
    return handle


def _remove_log_tee(handle: TextIO) -> None:
    """Restore the real console streams and close the log file."""
    if isinstance(sys.stdout, _LogTee):
        sys.stdout = sys.stdout.console
    if isinstance(sys.stderr, _LogTee):
        sys.stderr = sys.stderr.console
    handle.close()


def _issue_summary(canonical_dict: dict[str, Any]) -> str:
    """Build the issue-count phrase for the final status line.

    Returns an empty string when the run was clean.
    """
    metadata = canonical_dict.get("metadata", {})
    bits = []
    n_errors = len(metadata.get("validation_errors", []))
    n_dropped = len(metadata.get("dropped_pins", []))
    n_warnings = len(metadata.get("validation_warnings", []))
    if n_errors:
        bits.append(f"{n_errors} validation error(s)")
    if n_dropped:
        bits.append(f"{n_dropped} dropped pin(s)")
    if n_warnings:
        bits.append(f"{n_warnings} warning(s)")
    return ", ".join(bits)


def _version_string() -> str:
    """The single package version — see ``tools.pinmapgen.__version__``."""
    from . import __version__

    return __version__


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

Subcommands:
  profiles list [--profile-dir DIR]         table of available MCU profiles
  profiles check <name> [--profile-dir DIR] validate and inspect one profile
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
    # Output selection: pinmap.json (the canonical data) is always
    # written; the firmware/doc formats can be skipped individually.
    parser.add_argument(
        "--no-micropython",
        action="store_true",
        help="Skip the MicroPython module (pinmap_micropython.py)",
    )
    parser.add_argument(
        "--no-arduino",
        action="store_true",
        help="Skip the Arduino header (pinmap_arduino.h)",
    )
    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="Skip the Markdown pinout documentation (PINOUT.md)",
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
    # The tee itself is installed in main() by scanning argv before argparse
    # runs (see _install_log_tee); this entry documents the flag and keeps
    # argparse from rejecting it.
    parser.add_argument(
        "--log-file",
        type=Path,
        help=(
            "Mirror all console output (status, warnings, errors) to this "
            "file. The Fusion ULP passes this so it can display the run's "
            "diagnostics afterwards."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {_version_string()}",
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
        sys.exit(_print_profile_list())

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


def _print_profile_list() -> int:
    """Print a formatted table of all registered profiles.

    Used by both ``--list-mcus`` and the ``profiles list`` subcommand.
    Returns an exit code: 0, or 1 when any profile failed to parse.
    """
    profiles = registry.list_profiles()
    if not profiles:
        print("No MCU profiles found.")
        return 0

    print(
        f"{'Name':<16} {'Display':<16} {'Family':<8} "
        f"{'Source':<8} {'Schema':<8} Description"
    )
    print("-" * 88)
    broken = 0
    for name in profiles:
        # One malformed TOML must not take down the whole listing - show
        # it as broken (with the file named) and keep going.
        try:
            info = registry.get_profile_info(name)
        except ValueError as exc:
            print(f"{name:<16} [BROKEN] {exc}")
            broken += 1
            continue
        sv = info.get("schema_version")
        sv_str = str(sv) if sv is not None else "-"
        print(
            f"{info['name']:<16} "
            f"{info.get('display_name', ''):<16} "
            f"{info.get('family', ''):<8} "
            f"{info['source']:<8} "
            f"{sv_str:<8} "
            f"{info.get('description', '')}"
        )
    return 1 if broken else 0


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
    """Generate the selected output files from the canonical dictionary.

    pinmap.json is always written; --no-micropython / --no-arduino /
    --no-markdown skip the corresponding format, and Mermaid is opt-in
    via --mermaid. The emitters create their own directories.
    """
    out_root = args.out_root

    if args.verbose:
        print("Generating output files...")

    # Canonical JSON pinmap — always written
    json_path = out_root / "pinmaps" / "pinmap.json"
    emit_json.emit_json(canonical_dict, json_path)
    if args.verbose:
        print(f"  - {json_path}")

    if not getattr(args, "no_micropython", False):
        micropython_path = (
            out_root / "firmware" / "micropython" / "pinmap_micropython.py"
        )
        emit_micropython.emit_micropython(canonical_dict, micropython_path)
        if args.verbose:
            print(f"  - {micropython_path}")

    if not getattr(args, "no_arduino", False):
        arduino_path = out_root / "firmware" / "include" / "pinmap_arduino.h"
        emit_arduino.emit_arduino_header(canonical_dict, arduino_path)
        if args.verbose:
            print(f"  - {arduino_path}")

    if not getattr(args, "no_markdown", False):
        markdown_path = out_root / "firmware" / "docs" / "PINOUT.md"
        emit_markdown.emit_markdown_docs(canonical_dict, markdown_path)
        if args.verbose:
            print(f"  - {markdown_path}")

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

    # --profile-dir is accepted both before and after the subcommand, so
    # the documented `profiles check <name> --profile-dir DIR` order works.
    list_p = sub.add_parser("list", help="List available MCU profiles")
    list_p.add_argument(
        "--profile-dir", type=Path, dest="profile_dir",
        default=argparse.SUPPRESS,
    )

    check_p = sub.add_parser("check", help="Validate and inspect a profile")
    check_p.add_argument("name", help="Profile name to check")
    check_p.add_argument(
        "--profile-dir", type=Path, dest="profile_dir",
        default=argparse.SUPPRESS,
    )

    args = parser.parse_args(argv)

    # Register user profile directory if provided.
    if args.profile_dir:
        try:
            registry.add_profile_dir(args.profile_dir)
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    if args.action == "list":
        return _print_profile_list()
    if args.action == "check":
        return _profiles_check_cmd(args.name)
    return 1  # pragma: no cover


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

    try:
        info = registry.get_profile_info(key)
    except ValueError as exc:
        print(f"Validation FAILED: {exc}", file=sys.stderr)
        return 1
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
    # Install the --log-file tee before anything can print, and tear it
    # down (restoring the real streams, flushing the file) on every exit
    # path, including sys.exit() and KeyboardInterrupt.
    log_handle = _install_log_tee(sys.argv)
    try:
        _run_cli()
    finally:
        if log_handle is not None:
            _remove_log_tee(log_handle)


def _run_cli() -> None:
    """Parse arguments and run one generation (wrapped by main)."""
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

        # Enable reproducible builds. A pre-existing valid value is
        # honored (that's the SOURCE_DATE_EPOCH convention), but a
        # garbage one is replaced rather than left to poison the run.
        if args.reproducible:
            existing = os.environ.get("SOURCE_DATE_EPOCH")
            if existing is None or not existing.strip().lstrip("-").isdigit():
                os.environ["SOURCE_DATE_EPOCH"] = "0"

        # Parse input file and extract nets
        nets = parse_input_file(args)

        # Create canonical pinmap with normalization and validation
        canonical_dict = create_canonical_pinmap(nets, args.mcu, args.verbose)

        # Record the MCU reference designator so it appears in pinmap.json
        # and role metadata instead of "UNKNOWN".
        canonical_dict["mcu_ref"] = args.mcu_ref

        # The emitters rename identifiers that are reserved (a net named
        # SPI or MOSI must not shadow language/core symbols) or that
        # collide after sanitization. Surface those renames as warnings so
        # nobody hunts for a constant that was quietly renamed.
        _, rename_notes = build_name_map(list(canonical_dict.get("pins", {})))
        if rename_notes:
            metadata = canonical_dict.setdefault("metadata", {})
            warning_list = metadata.setdefault("validation_warnings", [])
            for note in rename_notes:
                print(f"Warning: {note}", file=sys.stderr)
                warning_list.append(note)

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

        # Honest final status: never print a bare success line when the
        # run produced errors, warnings, or dropped pins. The Fusion ULP
        # keys off this summary to decide which dialog to show.
        issues = _issue_summary(canonical_dict)
        prefix = "\n" if args.verbose else ""
        if issues:
            print(
                f"{prefix}Pinmap files generated with {issues} - "
                "review the messages above"
            )
        elif args.verbose:
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
