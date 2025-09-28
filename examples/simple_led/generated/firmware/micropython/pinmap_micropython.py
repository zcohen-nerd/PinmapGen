"""
Auto-generated MicroPython pinmap for RP2040.
Generated: 2025-09-28 05:41:11
Generator: PinmapGen

This file contains pin constants and helper functions for easy hardware access.
"""

from machine import Pin, I2C, SPI, PWM, ADC

# ========================================
# Pin Constants
# ========================================

# Indicators Pins
LED_RED = 2  # Light Emitting Diode
LED_GREEN = 3  # Light Emitting Diode
LED_BLUE = 4  # Light Emitting Diode

# Inputs Pins
BUTTON_1 = 5  # Push Button Input
BUTTON_2 = 6  # Push Button Input

# ========================================
# Helper Functions
# ========================================

def pin_in(pin_num, pull=None):
    """Create a digital input pin with optional pull resistor."""
    return Pin(pin_num, Pin.IN, pull)

def pin_out(pin_num, value=0):
    """Create a digital output pin with initial value."""
    return Pin(pin_num, Pin.OUT, value=value)
