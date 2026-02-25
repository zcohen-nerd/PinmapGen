"""Shared pin metadata for PinmapGen emitters.

Single source of truth for MCU-specific special-function descriptions.
All emitters import from here rather than maintaining their own copies.
"""

# Concise labels used by emit_arduino, emit_micropython, and emit_mermaid.
SPECIAL_FUNCTIONS_SHORT: dict[str, dict[str, str]] = {
    "rp2040": {
        "GP23": "SMPS_MODE",
        "GP24": "USB D-",
        "GP25": "USB D+",
        "GP26": "ADC0",
        "GP27": "ADC1",
        "GP28": "ADC2",
        "GP29": "ADC3",
    },
    "stm32g0": {
        "PA13": "SWDIO",
        "PA14": "SWCLK",
        "PB2": "BOOT1",
        "PC14": "LSE",
        "PC15": "LSE",
        "PF0": "HSE_IN",
        "PF1": "HSE_OUT",
        "PF2": "NRST",
    },
    "esp32": {
        "GPIO0": "BOOT_MODE",
        "GPIO1": "UART0_TX",
        "GPIO2": "BOOT_MODE",
        "GPIO3": "UART0_RX",
        "GPIO5": "VSPI_CS0",
        "GPIO12": "BOOT_VOLTAGE",
        "GPIO15": "BOOT_SILENCE",
        "GPIO25": "DAC1",
        "GPIO26": "DAC2",
        "GPIO36": "VP",
        "GPIO39": "VN",
    },
}

# Verbose, documentation-quality labels used by emit_markdown.
SPECIAL_FUNCTIONS_LONG: dict[str, dict[str, str]] = {
    "rp2040": {
        "GP23": "SMPS Power Mode",
        "GP24": "USB D- (Data Minus)",
        "GP25": "USB D+ (Data Plus)",
        "GP26": "ADC Channel 0",
        "GP27": "ADC Channel 1",
        "GP28": "ADC Channel 2",
        "GP29": "ADC Channel 3",
    },
    "stm32g0": {
        "PA13": "SWD Debug IO (SWDIO)",
        "PA14": "SWD Debug Clock (SWCLK)",
        "PB2": "Boot1 Pin",
        "PC14": "LSE Crystal (32kHz)",
        "PC15": "LSE Crystal (32kHz)",
        "PF0": "HSE Crystal Input",
        "PF1": "HSE Crystal Output",
        "PF2": "NRST (Reset)",
    },
    "esp32": {
        "GPIO0": "Strapping Pin / Boot Mode",
        "GPIO1": "UART0 TX (Console)",
        "GPIO2": "Strapping Pin / Boot Mode",
        "GPIO3": "UART0 RX (Console)",
        "GPIO5": "Strapping Pin / VSPI CS0",
        "GPIO12": "Strapping Pin / Boot Voltage",
        "GPIO15": "Strapping Pin / Boot Silence",
        "GPIO25": "DAC1",
        "GPIO26": "DAC2",
        "GPIO36": "VP (Input Only)",
        "GPIO39": "VN (Input Only)",
    },
}


def get_pin_comment(pin: str, mcu: str = "rp2040") -> str:
    """Return a concise pin comment such as ``"GP24 - USB D-"``.

    Args:
        pin: Normalised pin name (e.g. ``"GP24"``, ``"PA13"``).
        mcu: MCU identifier for MCU-specific lookups.

    Returns:
        Human-readable comment string.
    """
    comments = [pin]
    mcu_funcs = SPECIAL_FUNCTIONS_SHORT.get(mcu.lower(), {})
    if pin in mcu_funcs:
        comments.append(mcu_funcs[pin])
    return " - ".join(comments)


def get_special_function(pin: str, mcu: str = "rp2040") -> str:
    """Return a verbose special-function description for documentation.

    Args:
        pin: Normalised pin name.
        mcu: MCU identifier.

    Returns:
        Descriptive string, or ``"General Purpose I/O"`` if unknown.
    """
    mcu_funcs = SPECIAL_FUNCTIONS_LONG.get(mcu.lower(), {})
    return mcu_funcs.get(pin, "General Purpose I/O")
