"""
RP2040 MCU Profile for PinmapGen.

Implements RP2040-specific pin normalization, capabilities, and validation.
"""

import re

from .mcu_profiles import MCUProfile, PeripheralInfo, PinCapability, PinInfo


class RP2040Profile(MCUProfile):
    """RP2040 MCU profile with GPIO normalization and USB/ADC special functions."""

    def __init__(self):
        """Initialize RP2040 profile."""
        super().__init__("rp2040")

    def _initialize_pin_definitions(self) -> None:
        """Initialize RP2040 pin definitions and capabilities."""
        # Standard GPIO pins (0-22) with full capabilities
        for pin_num in range(23):
            capabilities = {
                PinCapability.GPIO,
                PinCapability.PWM,
                PinCapability.I2C_SDA,
                PinCapability.I2C_SCL,
                PinCapability.SPI_MOSI,
                PinCapability.SPI_MISO,
                PinCapability.SPI_SCK,
                PinCapability.SPI_CS,
                PinCapability.UART_TX,
                PinCapability.UART_RX,
            }

            self.pins[f"GP{pin_num}"] = PinInfo(
                name=f"GP{pin_num}",
                capabilities=capabilities,
                alternate_names=[f"GPIO{pin_num}", f"IO{pin_num}", str(pin_num)]
            )

        # GP23 - SMPS mode pin (limited functionality)
        self.pins["GP23"] = PinInfo(
            name="GP23",
            capabilities={PinCapability.GPIO},
            special_function="SMPS Power Mode",
            warnings=["GP23 controls SMPS power mode - use with caution"],
            alternate_names=["GPIO23", "IO23", "23"]
        )

        # GP24 - USB D- (differential pair)
        self.pins["GP24"] = PinInfo(
            name="GP24",
            capabilities={PinCapability.GPIO, PinCapability.USB_DM},
            special_function="USB D- (Data Minus)",
            warnings=["GP24 is USB D- pin - avoid for general GPIO if USB needed"],
            alternate_names=["USB_DM", "USB_DN", "USBDM", "USBDN", "GPIO24", "IO24", "24"]
        )

        # GP25 - USB D+ (differential pair)
        self.pins["GP25"] = PinInfo(
            name="GP25",
            capabilities={PinCapability.GPIO, PinCapability.USB_DP},
            special_function="USB D+ (Data Plus)",
            warnings=["GP25 is USB D+ pin - avoid for general GPIO if USB needed"],
            alternate_names=["USB_DP", "USB_DM", "USBDP", "USBDM", "GPIO25", "IO25", "25"]
        )

        # ADC pins (26-29)
        adc_pins = [
            ("GP26", "ADC Channel 0", "ADC0"),
            ("GP27", "ADC Channel 1", "ADC1"),
            ("GP28", "ADC Channel 2", "ADC2"),
            ("GP29", "ADC Channel 3", "ADC3")
        ]

        for pin_name, special_func, adc_name in adc_pins:
            pin_num = pin_name[2:]  # Extract number from GPxx
            capabilities = {
                PinCapability.GPIO,
                PinCapability.ADC,
                PinCapability.PWM,
                PinCapability.I2C_SDA,
                PinCapability.I2C_SCL,
                PinCapability.SPI_MOSI,
                PinCapability.SPI_MISO,
                PinCapability.SPI_SCK,
                PinCapability.SPI_CS,
                PinCapability.UART_TX,
                PinCapability.UART_RX,
            }

            self.pins[pin_name] = PinInfo(
                name=pin_name,
                capabilities=capabilities,
                special_function=special_func,
                alternate_names=[f"GPIO{pin_num}", f"IO{pin_num}", pin_num, adc_name]
            )

    def _initialize_peripherals(self) -> None:
        """Initialize RP2040 peripheral definitions."""
        # I2C peripherals
        self.peripherals.extend([
            PeripheralInfo("I2C", 0, {"sda": "configurable", "scl": "configurable"}),
            PeripheralInfo("I2C", 1, {"sda": "configurable", "scl": "configurable"}),
        ])

        # SPI peripherals
        self.peripherals.extend([
            PeripheralInfo("SPI", 0, {
                "mosi": "configurable", "miso": "configurable",
                "sck": "configurable", "cs": "configurable"
            }),
            PeripheralInfo("SPI", 1, {
                "mosi": "configurable", "miso": "configurable",
                "sck": "configurable", "cs": "configurable"
            }),
        ])

        # UART peripherals
        self.peripherals.extend([
            PeripheralInfo("UART", 0, {"tx": "configurable", "rx": "configurable"}),
            PeripheralInfo("UART", 1, {"tx": "configurable", "rx": "configurable"}),
        ])

        # USB peripheral
        self.peripherals.append(
            PeripheralInfo("USB", 0, {"dp": "GP25", "dm": "GP24"})
        )

        # ADC peripheral
        self.peripherals.append(
            PeripheralInfo("ADC", 0, {
                "ch0": "GP26", "ch1": "GP27", "ch2": "GP28", "ch3": "GP29"
            })
        )

    def normalize_pin_name(self, pin_name: str) -> str:
        """
        Normalize pin name according to RP2040 conventions.
        
        Args:
            pin_name: Raw pin name from schematic/CSV
            
        Returns:
            Normalized pin name (GPxx format)
            
        Raises:
            ValueError: If pin name cannot be normalized
        """
        if not pin_name:
            raise ValueError("Pin name cannot be empty")

        # Remove whitespace and convert to uppercase
        pin_name = pin_name.strip().upper()

        # Try to find pin by alternate names first
        for pin_id, pin_info in self.pins.items():
            if pin_info.alternate_names:
                for alt_name in pin_info.alternate_names:
                    if alt_name.upper() == pin_name:
                        return pin_id

        # Handle various GPIO formats
        # GPIOxx -> GPxx
        if pin_name.startswith("GPIO"):
            match = re.match(r"GPIO(\d+)", pin_name)
            if match:
                pin_num = int(match.group(1))
                normalized = f"GP{pin_num}"
                if normalized in self.pins:
                    return normalized
                raise ValueError(f"Invalid GPIO pin: {pin_name} (RP2040 valid range: GP0-GP29)")

        # IOxx -> GPxx
        elif pin_name.startswith("IO"):
            match = re.match(r"IO(\d+)", pin_name)
            if match:
                pin_num = int(match.group(1))
                normalized = f"GP{pin_num}"
                if normalized in self.pins:
                    return normalized
                raise ValueError(f"Invalid IO pin: {pin_name} (RP2040 valid range: GP0-GP29)")

        # GPxx (already normalized)
        elif pin_name.startswith("GP"):
            if pin_name in self.pins:
                return pin_name
            raise ValueError(f"Invalid GP pin: {pin_name} (RP2040 valid range: GP0-GP29)")

        # Handle numeric-only pins (assume GPIO)
        elif pin_name.isdigit():
            pin_num = int(pin_name)
            normalized = f"GP{pin_num}"
            if normalized in self.pins:
                return normalized
            raise ValueError(f"Invalid pin number: {pin_name} (RP2040 valid range: 0-29)")

        # Handle special USB pins by name
        elif pin_name in ["USB_DP", "USB_DM", "USB_DN", "USBDP", "USBDM", "USBDN"]:
            if pin_name in ["USB_DP", "USBDP"]:
                return "GP25"
            if pin_name in ["USB_DM", "USB_DN", "USBDM", "USBDN"]:
                return "GP24"

        # Handle ADC pins by name
        elif pin_name in ["ADC0", "ADC1", "ADC2", "ADC3"]:
            adc_num = int(pin_name[3])  # Extract number from ADCx
            return f"GP{26 + adc_num}"

        # Unknown format
        raise ValueError(f"Cannot normalize RP2040 pin name: {pin_name}")

    def validate_pin_assignment(self, pin_name: str, role: str) -> list[str]:
        """
        RP2040-specific pin assignment validation.
        
        Args:
            pin_name: Normalized pin name
            role: Assigned role/function
            
        Returns:
            List of validation warnings
        """
        warnings = super().validate_pin_assignment(pin_name, role)

        # RP2040-specific validation
        if pin_name == "GP23" and role != "gpio":
            warnings.append("GP23 has limited peripheral support due to SMPS function")

        if pin_name in ["GP24", "GP25"] and role.startswith("usb"):
            # This is actually good - USB pins used for USB
            pass
        elif pin_name in ["GP24", "GP25"] and not role.startswith("usb"):
            warnings.append(f"Pin {pin_name} is a USB pin - consider reserving for USB functionality")

        # ADC-specific warnings
        if pin_name in ["GP26", "GP27", "GP28", "GP29"]:
            if role == "adc":
                pass  # This is expected
            elif role in ["pwm", "gpio.out"]:
                warnings.append(f"Pin {pin_name} is an ADC pin - consider using for analog input")

        return warnings
