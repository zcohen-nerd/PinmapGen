"""
Auto-generated MicroPython pinmap for RP2040.
Generated: 1970-01-01 00:00:00 UTC
Generator: PinmapGen

This file bundles pin constants and helper utilities.
Use them to quickly access hardware in MicroPython.
"""

from machine import Pin, SPI

# ========================================
# Pin Constants
# ========================================

# UART Pins
DEBUG_RX = 1  # UART Receive (GP1)
DEBUG_TX = 0  # UART Transmit (GP0)
WIFI_RX = 9  # UART Receive (GP9)
WIFI_TX = 8  # UART Transmit (GP8)

# SPI Pins
LORA_CS = 17  # SPI Chip Select (GP17)
SD_CS = 20  # SPI Chip Select (GP20)
SPI_MISO = 18  # SPI Master In Slave Out (SPI) (GP18)
SPI_MOSI = 19  # SPI Master Out Slave In (SPI) (GP19)
SPI_SCK = 16  # SPI Serial Clock (SPI) (GP16)

# Other Pins
LORA_DIO0 = 22  # General Purpose I/O (GP22)
LORA_RST = 21  # Reset Signal (GP21)

# Indicators Pins
LORA_LED = 11  # Light Emitting Diode (GP11)
SD_LED = 12  # Light Emitting Diode (GP12)
WIFI_LED = 10  # Light Emitting Diode (GP10)

# ========================================
# Helper Functions
# ========================================

def pin_in(pin_num, pull=None):
    """Create a digital input with optional pull resistor."""
    return Pin(pin_num, Pin.IN, pull)

def pin_out(pin_num, value=0):
    """Create a digital output pin with initial value."""
    return Pin(pin_num, Pin.OUT, value=value)

def setup_spi(baudrate=1_000_000):
    """Setup SPI with MOSI=GP19, MISO=GP18, SCK=GP16."""
    return SPI(
        0,
        mosi=Pin(SPI_MOSI),
        miso=Pin(SPI_MISO),
        sck=Pin(SPI_SCK),
        baudrate=baudrate,
    )
