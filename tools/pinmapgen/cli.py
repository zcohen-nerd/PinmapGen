#!/usr/bin/env python3
"""
PinmapGen CLI - Command Line Interface for generating pinmaps from Fusion Electronics exports.

Usage:
    python -m tools.pinmapgen.cli --sch|--csv --mcu rp2040 --mcu-ref U1 --out-root . [--mermaid]
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any

# Import parser and MCU profile modules
from . import bom_csv
from . import eagle_sch
from . import normalize
from . import emit_json
from . import emit_micropython
from . import emit_arduino
from . import emit_markdown
from . import emit_mermaid
from .mcu_profiles import MCUProfile
from .rp2040_profile import RP2040Profile
from .stm32g0_profile import STM32G0Profile
from .esp32_profile import ESP32Profile


# MCU Profile Registry
MCU_PROFILES = {
    "rp2040": RP2040Profile,
    "stm32g0": STM32G0Profile,
    "esp32": ESP32Profile,
}


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate pinmaps from Fusion Electronics exports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m tools.pinmapgen.cli --csv hardware/exports/netlist.csv --mcu rp2040 --mcu-ref U1 --out-root .
  python -m tools.pinmapgen.cli --sch hardware/exports/project.sch --mcu rp2040 --mcu-ref U1 --out-root . --mermaid
        """
    )
    
    # Input source (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--csv",
        type=Path,
        help="CSV netlist export file"
    )
    input_group.add_argument(
        "--sch", 
        type=Path,
        help="EAGLE schematic file (.sch)"
    )
    
    # MCU configuration
    parser.add_argument(
        "--mcu",
        required=True,
        choices=list(MCU_PROFILES.keys()),
        help=f"MCU profile (supports: {', '.join(MCU_PROFILES.keys())})"
    )
    parser.add_argument(
        "--mcu-ref",
        required=True,
        help="MCU reference designator (e.g., U1)"
    )
    
    # Output configuration
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path("."),
        help="Output root directory (default: current directory)"
    )
    parser.add_argument(
        "--mermaid",
        action="store_true",
        help="Generate Mermaid diagram files"
    )
    
    # Optional flags
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()


def parse_input_file(args: argparse.Namespace) -> Dict[str, List[str]]:
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


def create_canonical_pinmap(nets: Dict[str, List[str]], mcu_name: str, 
                           verbose: bool = False) -> Dict[str, Any]:
    """Create canonical pinmap dictionary with normalization and validation."""
    if verbose:
        print(f"Normalizing pins for {mcu_name}")
    
    try:
        # Get MCU profile
        if mcu_name not in MCU_PROFILES:
            raise ValueError(f"Unknown MCU profile: {mcu_name}")
        
        profile_class = MCU_PROFILES[mcu_name]
        profile = profile_class()
        
        # Create canonical pinmap using profile
        canonical_dict = profile.create_canonical_pinmap(nets)
        
        if verbose:
            metadata = canonical_dict.get('metadata', {})
            print(f"  - Total nets: {metadata.get('total_nets', 0)}")
            print(f"  - Total pins: {metadata.get('total_pins', 0)}")
            
            diff_pairs = canonical_dict.get('differential_pairs', [])
            if diff_pairs:
                print(f"  - Detected {len(diff_pairs)} differential pairs:")
                for pair in diff_pairs:
                    pos = pair.get('positive')
                    neg = pair.get('negative')
                    print(f"    • {pos} / {neg}")
            
            special_pins = metadata.get('special_pins_used', [])
            if special_pins:
                print(f"  - Special pins used: {', '.join(special_pins)}")
        
        return canonical_dict
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def generate_outputs(canonical_dict: Dict[str, Any], args: argparse.Namespace) -> None:
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


def main():
    """Main CLI entry point."""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        if args.verbose:
            print("PinmapGen - Fusion Electronics to Firmware Bridge")
            print(f"MCU: {args.mcu} (ref: {args.mcu_ref})")
            print(f"Output root: {args.out_root}")
            print()
        
        # Parse input file and extract nets
        nets = parse_input_file(args)
        
        # Create canonical pinmap with normalization and validation
        canonical_dict = create_canonical_pinmap(nets, args.mcu, args.verbose)
        
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
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()