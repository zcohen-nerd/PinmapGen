"""
PinmapGen Fusion 360 Add-in
Main entry point for the add-in that creates firmware pinmaps from Electronics designs.

This add-in provides a user-friendly interface for non-programmers to generate
firmware-ready pinmap files that can be handed off to software developers.
"""

import os
import sys
import traceback

import adsk.core
import adsk.fusion

# Add the add-in directory to Python path to import local modules
_app = adsk.core.Application.get()
_addin_path = os.path.dirname(os.path.realpath(__file__))
if _addin_path not in sys.path:
    sys.path.insert(0, _addin_path)

from .commands.GeneratePinmapCommand import GeneratePinmapCommand
from .utils.error_handler import ErrorHandler
from .utils.logger import Logger

# Global variables for cleanup
_handlers = []
_logger = None


def run(context):
    """Called when the add-in is loaded."""
    global _logger

    try:
        _logger = Logger("PinmapGen")
        _logger.info("PinmapGen add-in starting...")

        # Get the user interface
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Create the main command
        generate_cmd = GeneratePinmapCommand()
        generate_cmd.on_create(context)
        _handlers.append(generate_cmd)

        # Add to the ADD-INS panel
        addins_panel = ui.allToolbarPanels.itemById("SolidScriptsAddinsPanel")
        if not addins_panel:
            _logger.warning("ADD-INS panel not found, creating custom panel")
            # Fallback: create in Tools menu
            tools_menu = ui.allToolbarTabs.itemById("ToolsTab")
            if tools_menu:
                addins_panel = tools_menu.toolbarPanels.add(
                    "PinmapGenPanel",
                    "PinmapGen"
                )

        if addins_panel:
            # Add the button to the panel
            button_def = ui.commandDefinitions.itemById(generate_cmd.command_id)
            if button_def:
                control = addins_panel.controls.addCommand(button_def)
                control.isPromotedByDefault = True
                control.isPromoted = True

        _logger.info("PinmapGen add-in loaded successfully")

    except Exception as e:
        error_handler = ErrorHandler()
        error_handler.handle_startup_error(e, traceback.format_exc())


def stop(context):
    """Called when the add-in is unloaded."""
    global _handlers, _logger

    try:
        if _logger:
            _logger.info("PinmapGen add-in stopping...")

        # Get the user interface
        app = adsk.core.Application.get()
        ui = app.userInterface

        # Clean up command handlers
        for handler in _handlers:
            if hasattr(handler, "on_destroy"):
                handler.on_destroy()

        # Remove UI elements
        addins_panel = ui.allToolbarPanels.itemById("SolidScriptsAddinsPanel")
        if addins_panel:
            control = addins_panel.controls.itemById("PinmapGenCommand")
            if control:
                control.deleteMe()

        # Remove command definitions
        cmd_def = ui.commandDefinitions.itemById("PinmapGenCommand")
        if cmd_def:
            cmd_def.deleteMe()

        # Remove custom panel if we created one
        custom_panel = ui.allToolbarPanels.itemById("PinmapGenPanel")
        if custom_panel:
            custom_panel.deleteMe()

        if _logger:
            _logger.info("PinmapGen add-in stopped successfully")

    except Exception as e:
        if _logger:
            _logger.error(f"Error during add-in shutdown: {e!s}")
        # Don't show user error during shutdown

    finally:
        _handlers.clear()
        _logger = None


# Entry points for Fusion 360
def start():
    """Alternative entry point for older Fusion versions."""
    run({})


def end():
    """Alternative entry point for older Fusion versions."""
    stop({})
