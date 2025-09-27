"""
Logger utility for PinmapGen Fusion add-in.
Provides structured logging for debugging and user support.
"""

import datetime
import os

import adsk.core


class Logger:
    """Simple logger for Fusion add-in with file and UI output."""

    def __init__(self, name: str):
        """Initialize logger with name and file output."""
        self.name = name
        self.app = adsk.core.Application.get()

        # Create log file in user's temp directory
        temp_dir = self.app.preferences.generalPreferences.tempFolder
        log_dir = os.path.join(temp_dir, "PinmapGen")
        os.makedirs(log_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        self.log_file = os.path.join(log_dir, f"pinmapgen_{timestamp}.log")

        # Initialize log file
        self.info(f"Logger initialized for {name}")

    def _write_log(self, level: str, message: str, show_ui: bool = False):
        """Write log entry to file and optionally show in UI."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"

        # Write to file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except Exception:
            pass  # Don't fail if logging fails

        # Show in UI if requested and not too verbose
        if show_ui and self.app and self.app.userInterface:
            try:
                self.app.userInterface.messageBox(
                    message,
                    f"PinmapGen {level}",
                    adsk.core.MessageBoxButtonTypes.OKButtonType
                )
            except Exception:
                pass  # Don't fail if UI fails

    def info(self, message: str, show_ui: bool = False):
        """Log info message."""
        self._write_log("INFO", message, show_ui)

    def warning(self, message: str, show_ui: bool = True):
        """Log warning message."""
        self._write_log("WARNING", message, show_ui)

    def error(self, message: str, show_ui: bool = True):
        """Log error message."""
        self._write_log("ERROR", message, show_ui)

    def debug(self, message: str):
        """Log debug message (file only)."""
        self._write_log("DEBUG", message, False)

    def get_log_file_path(self) -> str:
        """Get the path to the current log file."""
        return self.log_file
