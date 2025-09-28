"""
Auto-generated MicroPython pinmap for RP2040.
Generated: 2025-09-28 05:43:28
Generator: PinmapGen

This file contains pin constants and helper functions for easy hardware access.
"""

from machine import Pin, I2C, SPI, PWM, ADC

# ========================================
# Pin Constants
# ========================================

# Other Pins
SENSOR_DATA = 2  # General Purpose I/O

# I2C Pins
I2C_SDA = 4  # I2C Serial Data (I2C)
I2C_SCL = 5  # I2C Serial Clock (I2C)

# Indicators Pins
LIGHT_ANALOG = 26  # Light Emitting Diode
STATUS_LED = 15  # Light Emitting Diode

# Inputs Pins
BUTTON_IN = 14  # Push Button Input

# ========================================
# Helper Functions
# ========================================

def pin_in(pin_num, pull=None):
    """Create a digital input pin with optional pull resistor."""
    return Pin(pin_num, Pin.IN, pull)

def pin_out(pin_num, value=0):
    """Create a digital output pin with initial value."""
    return Pin(pin_num, Pin.OUT, value=value)

def setup_i2c(freq=400000):
    """Setup I2C with SDA=GP4, SCL=GP5."""
    return I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=freq)
