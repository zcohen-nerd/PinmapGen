"""
Auto-generated MicroPython pinmap for RP2040.
Generated: 2025-09-28 05:43:31
Generator: PinmapGen

This file contains pin constants and helper functions for easy hardware access.
"""

from machine import Pin, I2C, SPI, PWM, ADC

# ========================================
# Pin Constants
# ========================================

# UART Pins
DEBUG_TX = 0  # UART Transmit
DEBUG_RX = 1  # UART Receive
WIFI_TX = 8  # UART Transmit
WIFI_RX = 9  # UART Receive

# SPI Pins
SPI_SCK = 16  # SPI Serial Clock (SPI)
SPI_MISO = 18  # SPI Master In Slave Out (SPI)
SPI_MOSI = 19  # SPI Master Out Slave In (SPI)
LORA_CS = 17  # SPI Chip Select
SD_CS = 20  # SPI Chip Select

# Other Pins
LORA_RST = 21  # Reset Signal
LORA_DIO0 = 22  # General Purpose I/O

# Indicators Pins
WIFI_LED = 10  # Light Emitting Diode
LORA_LED = 11  # Light Emitting Diode
SD_LED = 12  # Light Emitting Diode

# ========================================
# Helper Functions
# ========================================

def pin_in(pin_num, pull=None):
    """Create a digital input pin with optional pull resistor."""
    return Pin(pin_num, Pin.IN, pull)

def pin_out(pin_num, value=0):
    """Create a digital output pin with initial value."""
    return Pin(pin_num, Pin.OUT, value=value)

def setup_spi(baudrate=1000000):
    """Setup SPI with MOSI=GP19, MISO=GP18, SCK=GP16."""
    return SPI(0, mosi=Pin(SPI_MOSI), miso=Pin(SPI_MISO), sck=Pin(SPI_SCK), baudrate=baudrate)
