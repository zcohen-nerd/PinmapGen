"""
Auto-generated MicroPython pinmap for RP2040.
Generated: 1970-01-01 00:00:00 UTC
Generator: PinmapGen

This file bundles pin constants and helper utilities.
Use them to quickly access hardware in MicroPython.
"""

from machine import Pin, I2C

# ========================================
# Pin Constants
# ========================================

# Inputs Pins
BUTTON_IN = 14  # Push Button Input (GP14)

# I2C Pins
I2C_SCL = 5  # I2C Serial Clock (I2C) (GP5)
I2C_SDA = 4  # I2C Serial Data (I2C) (GP4)

# Indicators Pins
LIGHT_ANALOG = 26  # Light Emitting Diode (GP26)
STATUS_LED = 15  # Light Emitting Diode (GP15)

# Other Pins
SENSOR_DATA = 2  # General Purpose I/O (GP2)

# ========================================
# Helper Functions
# ========================================

def pin_in(pin_num, pull=None):
    """Create a digital input with optional pull resistor."""
    return Pin(pin_num, Pin.IN, pull)

def pin_out(pin_num, value=0):
    """Create a digital output pin with initial value."""
    return Pin(pin_num, Pin.OUT, value=value)

def setup_i2c(freq=400000):
    """Setup I2C with SDA=GP4, SCL=GP5."""
    return I2C(
        0,
        sda=Pin(I2C_SDA),
        scl=Pin(I2C_SCL),
        freq=freq,
    )
