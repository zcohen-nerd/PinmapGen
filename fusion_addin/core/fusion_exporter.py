"""
Fusion Electronics data exporter for PinmapGen.
Extracts netlist data from Fusion 360 Electronics designs.
"""

import adsk.core
import adsk.fusion
from typing import Dict, List, Optional, Any


class FusionExporter:
    """Extracts netlist data from Fusion Electronics designs."""
    
    def __init__(self, logger):
        """Initialize the exporter with logger."""
        self.logger = logger
        self.app = adsk.core.Application.get()
    
    def extract_electronics_data(self, mcu_ref: str) -> Optional[Dict[str, Any]]:
        """
        Extract netlist data from the active Electronics design.
        
        Args:
            mcu_ref: MCU reference designator (e.g., 'U1')
            
        Returns:
            Dictionary with netlist data or None if extraction fails
        """
        try:
            # Get the active design
            design = self.app.activeProduct
            if not design:
                self.logger.error("No active design found")
                return None
            
            # Check if we're in Electronics workspace
            if not self._is_electronics_workspace():
                self.logger.error("Electronics workspace not active")
                return None
            
            # Get the electronics data
            electronics = design.electronics
            if not electronics:
                self.logger.error("No electronics data in design")
                return None
            
            # Extract schematic nets and components
            nets_data = self._extract_nets_data(electronics, mcu_ref)
            
            if not nets_data:
                self.logger.warning(f"No nets found for MCU '{mcu_ref}'")
                return None
            
            self.logger.info(f"Extracted {len(nets_data)} nets for {mcu_ref}")
            return {
                'nets': nets_data,
                'mcu_ref': mcu_ref,
                'design_name': design.rootComponent.name
            }
            
        except Exception as e:
            self.logger.error(f"Failed to extract electronics data: {str(e)}")
            return None
    
    def _is_electronics_workspace(self) -> bool:
        """Check if Electronics workspace is currently active."""
        try:
            workspace = self.app.userInterface.activeWorkspace
            return workspace.id == 'ElectronicsWorkspace'
        except Exception:
            return False
    
    def _extract_nets_data(self, electronics, mcu_ref: str) -> Dict[str, List[str]]:
        """
        Extract net connections for the specified MCU.
        
        Args:
            electronics: Fusion electronics object
            mcu_ref: MCU reference designator
            
        Returns:
            Dictionary mapping net names to pin lists
        """
        nets_data = {}
        
        try:
            # Get all schematics in the design
            for schematic in electronics.schematics:
                self.logger.debug(f"Processing schematic: {schematic.name}")
                
                # Find nets connected to the MCU
                for net in schematic.nets:
                    mcu_pins = self._get_mcu_pins_on_net(net, mcu_ref)
                    if mcu_pins:
                        # Store net with all connected pins
                        all_pins = []
                        for pin in net.pins:
                            component_name = pin.component.refDes
                            pin_name = pin.name
                            all_pins.append(f"{component_name}.{pin_name}")
                        
                        nets_data[net.name] = all_pins
                        
                        self.logger.debug(
                            f"Net '{net.name}': {len(all_pins)} pins, "
                            f"MCU pins: {mcu_pins}"
                        )
            
            return nets_data
            
        except Exception as e:
            self.logger.error(f"Error extracting nets: {str(e)}")
            return {}
    
    def _get_mcu_pins_on_net(self, net, mcu_ref: str) -> List[str]:
        """
        Get MCU pins connected to the given net.
        
        Args:
            net: Fusion net object
            mcu_ref: MCU reference designator
            
        Returns:
            List of MCU pin names on this net
        """
        mcu_pins = []
        
        try:
            for pin in net.pins:
                if pin.component.refDes == mcu_ref:
                    mcu_pins.append(pin.name)
        except Exception as e:
            self.logger.debug(f"Error getting MCU pins: {str(e)}")
        
        return mcu_pins
    
    def get_available_mcus(self) -> List[Dict[str, str]]:
        """
        Get list of available MCUs in the current design.
        
        Returns:
            List of dictionaries with MCU info: {'ref': 'U1', 'name': 'RP2040'}
        """
        mcus = []
        
        try:
            design = self.app.activeProduct
            if not design or not design.electronics:
                return mcus
            
            # Common MCU part names to look for
            mcu_patterns = [
                'rp2040', 'rp2350',  # Raspberry Pi
                'stm32g0', 'stm32g4', 'stm32f4',  # STMicroelectronics
                'esp32', 'esp32-s3', 'esp32-c3',  # Espressif
                'atmega', 'attiny',  # Microchip/Atmel
                'pic',  # Microchip PIC
                'nrf52', 'nrf91',  # Nordic
            ]
            
            for schematic in design.electronics.schematics:
                for component in schematic.components:
                    part_name = component.name.lower()
                    ref_des = component.refDes
                    
                    # Check if this looks like an MCU
                    for pattern in mcu_patterns:
                        if pattern in part_name:
                            mcus.append({
                                'ref': ref_des,
                                'name': component.name,
                                'type': self._guess_mcu_type(part_name)
                            })
                            break
            
        except Exception as e:
            self.logger.error(f"Error finding MCUs: {str(e)}")
        
        return mcus
    
    def _guess_mcu_type(self, part_name: str) -> str:
        """Guess MCU type from part name for auto-selection."""
        part_name = part_name.lower()
        
        if 'rp2040' in part_name or 'rp2350' in part_name:
            return 'rp2040'
        elif 'stm32g0' in part_name:
            return 'stm32g0'
        elif 'esp32' in part_name:
            return 'esp32'
        else:
            return 'rp2040'  # Default fallback