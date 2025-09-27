"""
PinmapGen toolchain wrapper for Fusion add-in.
Integrates the PinmapGen CLI functionality into the Fusion interface.
"""

import csv
import os
import sys
import tempfile
from typing import Any


class PinmapGeneratorWrapper:
    """Wrapper around PinmapGen toolchain for Fusion integration."""

    def __init__(self, logger):
        """Initialize wrapper with logger."""
        self.logger = logger

        # Add PinmapGen tools to path
        addon_path = os.path.dirname(os.path.dirname(__file__))
        project_root = os.path.dirname(addon_path)
        tools_path = os.path.join(project_root, "tools")

        if tools_path not in sys.path:
            sys.path.insert(0, tools_path)

    def generate_pinmap(self, netlist_data: dict[str, Any], mcu_type: str,
                       mcu_ref: str, output_path: str,
                       formats: dict[str, bool]) -> dict[str, Any]:
        """
        Generate pinmap using PinmapGen toolchain.
        
        Args:
            netlist_data: Extracted netlist from Fusion
            mcu_type: MCU profile type (rp2040, stm32g0, esp32)
            mcu_ref: MCU reference designator
            output_path: Output directory path
            formats: Dictionary of format flags
            
        Returns:
            Generation result with success status and file paths
        """
        try:
            # Create output directory
            os.makedirs(output_path, exist_ok=True)

            # Convert Fusion data to PinmapGen format
            csv_data = self._convert_to_csv_format(netlist_data, mcu_ref)

            # Create temporary CSV file
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".csv",
                delete=False,
                newline=""
            ) as temp_file:
                writer = csv.writer(temp_file)
                writer.writerows(csv_data)
                temp_csv_path = temp_file.name

            try:
                # Import PinmapGen modules
                from pinmapgen import (
                    emit_arduino,
                    emit_json,
                    emit_markdown,
                    emit_mermaid,
                    emit_micropython,
                )

                # Read the temporary CSV
                from pinmapgen.bom_csv import get_mcu_nets
                from pinmapgen.cli import create_canonical_pinmap
                nets = get_mcu_nets(temp_csv_path, mcu_ref)

                # Generate canonical pinmap
                canonical_dict = create_canonical_pinmap(nets, mcu_type, True)

                generated_files = []

                # Generate requested output formats
                if formats.get("micropython", True):
                    micropython_path = os.path.join(
                        output_path,
                        "firmware",
                        "micropython",
                        "pinmap_micropython.py"
                    )
                    os.makedirs(os.path.dirname(micropython_path), exist_ok=True)
                    emit_micropython.generate_micropython(
                        canonical_dict,
                        micropython_path
                    )
                    generated_files.append(micropython_path)

                if formats.get("arduino", True):
                    arduino_path = os.path.join(
                        output_path,
                        "firmware",
                        "include",
                        "pinmap_arduino.h"
                    )
                    os.makedirs(os.path.dirname(arduino_path), exist_ok=True)
                    emit_arduino.generate_arduino(canonical_dict, arduino_path)
                    generated_files.append(arduino_path)

                if formats.get("docs", True):
                    docs_path = os.path.join(
                        output_path,
                        "firmware",
                        "docs",
                        "PINOUT.md"
                    )
                    os.makedirs(os.path.dirname(docs_path), exist_ok=True)
                    emit_markdown.generate_markdown(canonical_dict, docs_path)
                    generated_files.append(docs_path)

                # Always generate JSON for programmer reference
                json_path = os.path.join(output_path, "pinmaps", "pinmap.json")
                os.makedirs(os.path.dirname(json_path), exist_ok=True)
                emit_json.generate_json(canonical_dict, json_path)
                generated_files.append(json_path)

                # Generate Mermaid if requested
                if formats.get("mermaid", False):
                    mermaid_path = os.path.join(
                        output_path,
                        "firmware",
                        "docs",
                        "pinout.mmd"
                    )
                    os.makedirs(os.path.dirname(mermaid_path), exist_ok=True)
                    emit_mermaid.generate_mermaid(canonical_dict, mermaid_path)
                    generated_files.append(mermaid_path)

                # Extract warnings from metadata
                warnings = []
                metadata = canonical_dict.get("metadata", {})
                if "warnings" in metadata:
                    warnings = metadata["warnings"]

                return {
                    "success": True,
                    "generated_files": generated_files,
                    "warnings": warnings,
                    "output_path": output_path
                }

            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_csv_path)
                except Exception:
                    pass  # Don't fail if cleanup fails

        except Exception as e:
            self.logger.error(f"Generation failed: {e!s}")
            return {
                "success": False,
                "error": str(e),
                "generated_files": []
            }

    def _convert_to_csv_format(self, netlist_data: dict[str, Any],
                              mcu_ref: str) -> list[list[str]]:
        """
        Convert Fusion netlist data to CSV format for PinmapGen.
        
        Args:
            netlist_data: Netlist data from Fusion
            mcu_ref: MCU reference designator
            
        Returns:
            CSV data as list of rows
        """
        csv_rows = [["Component", "RefDes", "Pin", "Net"]]  # Header

        nets = netlist_data.get("nets", {})

        for net_name, pins in nets.items():
            for pin_spec in pins:
                # Parse "RefDes.PinName" format
                if "." in pin_spec:
                    ref_des, pin_name = pin_spec.split(".", 1)

                    # Determine component type
                    if ref_des == mcu_ref:
                        component_type = "MCU"
                    elif ref_des.startswith("R"):
                        component_type = "Resistor"
                    elif ref_des.startswith("C"):
                        component_type = "Capacitor"
                    elif ref_des.startswith("L"):
                        component_type = "Inductor"
                    elif ref_des.startswith("D"):
                        component_type = "Diode"
                    elif ref_des.startswith("Q"):
                        component_type = "Transistor"
                    elif ref_des.startswith("U") or ref_des.startswith("IC"):
                        component_type = "IC"
                    else:
                        component_type = "Component"

                    csv_rows.append([component_type, ref_des, pin_name, net_name])

        return csv_rows

    def validate_mcu_support(self, mcu_type: str) -> dict[str, Any]:
        """
        Validate that the MCU type is supported.
        
        Args:
            mcu_type: MCU type string
            
        Returns:
            Validation result
        """
        supported_mcus = ["rp2040", "stm32g0", "esp32"]

        if mcu_type not in supported_mcus:
            return {
                "valid": False,
                "error": f"MCU type '{mcu_type}' not supported. "
                        f"Supported types: {', '.join(supported_mcus)}"
            }

        return {"valid": True}
