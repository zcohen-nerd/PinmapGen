"""
Error handling utilities for PinmapGen Fusion add-in.
Provides user-friendly error messages and recovery options.
"""


import adsk.core


class ErrorHandler:
    """Handles errors with user-friendly messages and recovery options."""

    def __init__(self):
        """Initialize error handler."""
        self.app = adsk.core.Application.get()
        self.ui = self.app.userInterface if self.app else None

    def handle_startup_error(self, error: Exception, full_traceback: str):
        """Handle errors during add-in startup."""
        message = (
            "PinmapGen add-in failed to start.\n\n"
            f"Error: {error!s}\n\n"
            "This usually means:\n"
            "• Fusion 360 needs to be restarted\n"
            "• The add-in files may be corrupted\n"
            "• Python environment issues\n\n"
            "Please try restarting Fusion 360. If the problem persists, "
            "contact support with the error details."
        )

        if self.ui:
            self.ui.messageBox(
                message,
                "PinmapGen Startup Error",
                adsk.core.MessageBoxButtonTypes.OKButtonType,
                adsk.core.MessageBoxIconTypes.CriticalIconType
            )

    def handle_generation_error(self, error: Exception, context: str = ""):
        """Handle errors during pinmap generation."""
        # Map common errors to user-friendly messages
        error_messages = {
            "FileNotFoundError": (
                "Cannot find the required files.\n\n"
                "Make sure your Electronics design is saved and "
                "contains the selected MCU component."
            ),
            "ValueError": (
                "Invalid design data detected.\n\n"
                "This usually means:\n"
                "• MCU component not found in design\n"
                "• Pin names don't match the MCU profile\n"
                "• Missing net connections\n\n"
                "Check your schematic and try again."
            ),
            "PermissionError": (
                "Cannot write to the output folder.\n\n"
                "Make sure:\n"
                "• The folder exists and is writable\n"
                "• No files are open in other programs\n"
                "• You have permission to write to this location"
            ),
            "ConnectionError": (
                "Cannot access Fusion design data.\n\n"
                "Make sure:\n"
                "• Your design is open in Electronics workspace\n"
                "• The design is saved (not just a temporary sketch)\n"
                "• You're connected to the internet (for cloud designs)"
            )
        }

        error_type = type(error).__name__
        user_message = error_messages.get(
            error_type,
            f"An unexpected error occurred during pinmap generation.\n\n"
            f"Error: {error!s}\n\n"
            f"Context: {context}"
        )

        if self.ui:
            result = self.ui.messageBox(
                user_message + "\n\nWould you like to try again?",
                "PinmapGen Error",
                adsk.core.MessageBoxButtonTypes.YesNoButtonType,
                adsk.core.MessageBoxIconTypes.WarningIconType
            )
            return result == adsk.core.DialogResults.DialogYes

        return False

    def handle_validation_warnings(self, warnings: list) -> bool:
        """Handle validation warnings with user choice to continue."""
        if not warnings:
            return True

        warning_text = "The following issues were found in your design:\n\n"
        for i, warning in enumerate(warnings[:5], 1):  # Limit to 5 warnings
            warning_text += f"{i}. {warning}\n"

        if len(warnings) > 5:
            warning_text += f"... and {len(warnings) - 5} more warnings\n"

        warning_text += (
            "\nThese are not errors, but may affect your firmware.\n"
            "Would you like to continue generating the pinmap?"
        )

        if self.ui:
            result = self.ui.messageBox(
                warning_text,
                "Design Validation Warnings",
                adsk.core.MessageBoxButtonTypes.YesNoButtonType,
                adsk.core.MessageBoxIconTypes.WarningIconType
            )
            return result == adsk.core.DialogResults.DialogYes

        return True  # Default to continue if no UI

    def show_success_message(self, output_path: str, file_count: int):
        """Show success message with generated file info."""
        message = (
            f"Pinmap generation completed successfully!\n\n"
            f"Generated {file_count} files in:\n"
            f"{output_path}\n\n"
            "The files are ready to share with your programmer.\n"
            "Would you like to open the output folder?"
        )

        if self.ui:
            result = self.ui.messageBox(
                message,
                "PinmapGen Success",
                adsk.core.MessageBoxButtonTypes.YesNoButtonType,
                adsk.core.MessageBoxIconTypes.InformationIconType
            )
            return result == adsk.core.DialogResults.DialogYes

        return False

    def show_info_message(self, title: str, message: str):
        """Show general information message."""
        if self.ui:
            self.ui.messageBox(
                message,
                title,
                adsk.core.MessageBoxButtonTypes.OKButtonType,
                adsk.core.MessageBoxIconTypes.InformationIconType
            )
