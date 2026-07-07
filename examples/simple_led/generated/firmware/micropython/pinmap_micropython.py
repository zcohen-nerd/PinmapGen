"""
Auto-generated MicroPython pinmap for RP2040.
Generated: 1970-01-01 00:00:00 UTC
Generator: PinmapGen

This file bundles pin constants and helper utilities.
Use them to quickly access hardware in MicroPython.
"""

from machine import Pin

# ========================================
# Pin Constants
# ========================================

# Inputs Pins
BUTTON_1 = 5  # Push Button Input (GP5)
BUTTON_2 = 6  # Push Button Input (GP6)

# Indicators Pins
LED_BLUE = 4  # Light Emitting Diode (GP4)
LED_GREEN = 3  # Light Emitting Diode (GP3)
LED_RED = 2  # Light Emitting Diode (GP2)

# ========================================
# Helper Functions
# ========================================

def pin_in(pin_num, pull=None):
    """Create a digital input with optional pull resistor."""
    return Pin(pin_num, Pin.IN, pull)

def pin_out(pin_num, value=0):
    """Create a digital output pin with initial value."""
    return Pin(pin_num, Pin.OUT, value=value)
