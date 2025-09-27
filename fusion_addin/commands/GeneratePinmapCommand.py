"""
Main command for PinmapGen Fusion add-in.
Handles the user interface and orchestrates pinmap generation.
"""

import adsk.core
import adsk.fusion
import os
import sys
from typing import Optional

# Add parent directory to path for importing PinmapGen modules
_addon_path = os.path.dirname(os.path.dirname(__file__))
_project_root = os.path.dirname(_addon_path)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fusion_addin.utils.logger import Logger
from fusion_addin.utils.error_handler import ErrorHandler
from fusion_addin.core.fusion_exporter import FusionExporter
from fusion_addin.core.pinmap_generator import PinmapGeneratorWrapper


class GeneratePinmapCommand:
    """Main command for generating pinmaps from Fusion Electronics designs."""
    
    def __init__(self):
        """Initialize the command."""
        self.command_id = "PinmapGenCommand"
        self.command_name = "Generate Pinmap"
        self.command_description = "Generate firmware pinmap from Electronics design"
        self.command_tooltip = "One-click pinmap generation for programmers"
        
        # UI and state
        self.app = adsk.core.Application.get()
        self.ui = self.app.userInterface if self.app else None
        self.logger = Logger("GeneratePinmapCommand")
        self.error_handler = ErrorHandler()
        
        # Command handlers
        self.command_created_handler = None
        self.command_executed_handler = None
        
        # UI elements (will be set during dialog creation)
        self.mcu_dropdown = None
        self.mcu_ref_input = None
        self.output_path_input = None
        self.micropython_checkbox = None
        self.arduino_checkbox = None
        self.docs_checkbox = None
        self.mermaid_checkbox = None
    
    def on_create(self, context):
        """Called when the add-in is loaded."""
        try:
            # Create command definition
            cmd_def = self.ui.commandDefinitions.addButtonDefinition(
                self.command_id,
                self.command_name,
                self.command_description,
                ""  # Icon path - TODO: add icon
            )
            cmd_def.toolClipFilename = ""  # TODO: add tooltip image
            
            # Connect command handlers
            self.command_created_handler = CommandCreatedHandler(self)
            cmd_def.commandCreated.add(self.command_created_handler)
            
            self.logger.info("GeneratePinmapCommand created successfully")
            
        except Exception as e:
            self.error_handler.handle_startup_error(e, "")
    
    def on_destroy(self):
        """Clean up when the add-in is unloaded."""
        try:
            # Disconnect handlers
            if self.command_created_handler:
                cmd_def = self.ui.commandDefinitions.itemById(self.command_id)
                if cmd_def:
                    cmd_def.commandCreated.remove(self.command_created_handler)
            
            self.logger.info("GeneratePinmapCommand destroyed")
            
        except Exception as e:
            self.logger.error(f"Error destroying command: {str(e)}")
    
    def create_ui(self, args):
        """Create the main user interface dialog."""
        try:
            inputs = args.command.commandInputs
            
            # Title and description
            inputs.addTextBoxCommandInput(
                'titleText', 
                '', 
                '<b>Generate Pinmap for Programmers</b><br/>'
                'Create firmware-ready pinmap files from your Electronics design. '
                'Choose your microcontroller and output options below.',
                2,  # Number of lines
                True  # Read-only
            )
            
            # MCU Selection Group
            mcu_group = inputs.addGroupCommandInput('mcuGroup', 'Microcontroller')
            mcu_inputs = mcu_group.children
            
            # MCU Type dropdown
            self.mcu_dropdown = mcu_inputs.addDropDownCommandInput(
                'mcuType',
                'MCU Type',
                adsk.core.DropDownStyles.TextListDropDownStyle
            )
            self.mcu_dropdown.listItems.add('RP2040 (Raspberry Pi Pico)', True)
            self.mcu_dropdown.listItems.add('STM32G0 (STM32G071)', False)
            self.mcu_dropdown.listItems.add('ESP32 (ESP32-WROOM-32)', False)
            
            # MCU Reference designator
            self.mcu_ref_input = mcu_inputs.addStringValueInput(
                'mcuRef',
                'MCU Reference',
                'U1'
            )
            self.mcu_ref_input.tooltip = (
                'Component reference in your schematic (e.g., U1, U2, IC1)'
            )
            
            # Output Options Group  
            output_group = inputs.addGroupCommandInput('outputGroup', 'Output Files')
            output_inputs = output_group.children
            
            # Output formats
            self.micropython_checkbox = output_inputs.addBoolValueInput(
                'generateMicroPython', 
                'MicroPython (.py)', 
                True, 
                '', 
                True
            )
            self.micropython_checkbox.tooltip = (
                'Generate MicroPython constants and helper functions'
            )
            
            self.arduino_checkbox = output_inputs.addBoolValueInput(
                'generateArduino', 
                'Arduino (.h)', 
                True, 
                '', 
                True
            )
            self.arduino_checkbox.tooltip = (
                'Generate Arduino/C++ header file with pin definitions'
            )
            
            self.docs_checkbox = output_inputs.addBoolValueInput(
                'generateDocs', 
                'Documentation (.md)', 
                True, 
                '', 
                True
            )
            self.docs_checkbox.tooltip = (
                'Generate human-readable pinout documentation'
            )
            
            self.mermaid_checkbox = output_inputs.addBoolValueInput(
                'generateMermaid', 
                'Diagrams (.mmd)', 
                True, 
                '', 
                False
            )
            self.mermaid_checkbox.tooltip = (
                'Generate Mermaid diagrams for visualization'
            )
            
            # Output location
            self.output_path_input = output_inputs.addStringValueInput(
                'outputPath',
                'Output Folder',
                self._get_default_output_path()
            )
            
            # Browse button for output path
            output_inputs.addBoolValueInput(
                'browseOutput',
                'Browse...',
                False,
                '',
                False
            )
            
            self.logger.info("UI created successfully")
            
        except Exception as e:
            self.error_handler.handle_generation_error(e, "creating UI")
    
    def _get_default_output_path(self) -> str:
        """Get smart default output path based on current design."""
        try:
            # Try to use design location
            design = self.app.activeProduct
            if design and hasattr(design, 'dataFile') and design.dataFile:
                design_folder = os.path.dirname(design.dataFile.parentFolder.dataFiles[0].localFilePath)
                return os.path.join(design_folder, "pinmaps")
        except Exception:
            pass
        
        # Fallback to Documents folder
        return os.path.join(os.path.expanduser("~"), "Documents", "PinmapGen")
    
    def execute_generation(self, args):
        """Execute the pinmap generation process."""
        try:
            self.logger.info("Starting pinmap generation...")
            
            # Get input values
            inputs = args.command.commandInputs
            
            mcu_type_item = inputs.itemById('mcuType').selectedItem
            mcu_type_map = {
                'RP2040 (Raspberry Pi Pico)': 'rp2040',
                'STM32G0 (STM32G071)': 'stm32g0', 
                'ESP32 (ESP32-WROOM-32)': 'esp32'
            }
            mcu_type = mcu_type_map.get(mcu_type_item.name, 'rp2040')
            
            mcu_ref = inputs.itemById('mcuRef').value
            output_path = inputs.itemById('outputPath').value
            
            # Get output format flags
            generate_micropython = inputs.itemById('generateMicroPython').value
            generate_arduino = inputs.itemById('generateArduino').value
            generate_docs = inputs.itemById('generateDocs').value
            generate_mermaid = inputs.itemById('generateMermaid').value
            
            # Validate inputs
            if not mcu_ref.strip():
                self.error_handler.show_info_message(
                    "Input Required",
                    "Please enter the MCU reference designator (e.g., U1)"
                )
                return
            
            if not any([generate_micropython, generate_arduino, generate_docs]):
                self.error_handler.show_info_message(
                    "Output Required", 
                    "Please select at least one output format to generate"
                )
                return
            
            # Step 1: Export design data from Fusion
            self.logger.info("Exporting design data from Fusion...")
            exporter = FusionExporter(self.logger)
            netlist_data = exporter.extract_electronics_data(mcu_ref.strip())
            
            if not netlist_data:
                self.error_handler.show_info_message(
                    "No Design Data",
                    f"Could not find MCU '{mcu_ref}' in the active Electronics design.\n\n"
                    "Make sure:\n"
                    "• Electronics workspace is active\n"
                    "• Design contains the MCU component\n" 
                    "• Reference designator matches exactly"
                )
                return
            
            # Step 2: Generate pinmap using PinmapGen toolchain  
            self.logger.info("Generating pinmap files...")
            generator = PinmapGeneratorWrapper(self.logger)
            result = generator.generate_pinmap(
                netlist_data=netlist_data,
                mcu_type=mcu_type,
                mcu_ref=mcu_ref,
                output_path=output_path,
                formats={
                    'micropython': generate_micropython,
                    'arduino': generate_arduino,
                    'docs': generate_docs,
                    'mermaid': generate_mermaid
                }
            )
            
            # Step 3: Handle results
            if result.get('success'):
                warnings = result.get('warnings', [])
                if warnings:
                    continue_generation = self.error_handler.handle_validation_warnings(warnings)
                    if not continue_generation:
                        return
                
                # Show success message
                file_count = len(result.get('generated_files', []))
                show_folder = self.error_handler.show_success_message(output_path, file_count)
                
                if show_folder:
                    self._open_output_folder(output_path)
                    
                self.logger.info("Pinmap generation completed successfully")
                
            else:
                error_msg = result.get('error', 'Unknown error occurred')
                self.error_handler.handle_generation_error(
                    Exception(error_msg), 
                    "pinmap generation"
                )
        
        except Exception as e:
            self.error_handler.handle_generation_error(e, "execution")
    
    def _open_output_folder(self, path: str):
        """Open the output folder in the system file explorer."""
        try:
            if os.path.exists(path):
                if sys.platform == "win32":
                    os.startfile(path)
                elif sys.platform == "darwin":
                    os.system(f"open '{path}'")
                else:
                    os.system(f"xdg-open '{path}'")
        except Exception as e:
            self.logger.warning(f"Could not open folder: {str(e)}")


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    """Handler for when the command is created."""
    
    def __init__(self, command: GeneratePinmapCommand):
        super().__init__()
        self.command = command
    
    def notify(self, args):
        """Called when command is created."""
        try:
            # Create the UI
            self.command.create_ui(args)
            
            # Connect execution handler
            self.command.command_executed_handler = CommandExecutedHandler(self.command)
            args.command.execute.add(self.command.command_executed_handler)
            
        except Exception as e:
            self.command.error_handler.handle_startup_error(e, "command creation")


class CommandExecutedHandler(adsk.core.CommandExecutedEventHandler):
    """Handler for when the command is executed."""
    
    def __init__(self, command: GeneratePinmapCommand):
        super().__init__()
        self.command = command
    
    def notify(self, args):
        """Called when command is executed."""
        try:
            self.command.execute_generation(args)
        except Exception as e:
            self.command.error_handler.handle_generation_error(e, "command execution")