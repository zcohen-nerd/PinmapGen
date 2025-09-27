"""
ESP32 MCU Profile for PinmapGen.

Implements ESP32-specific pin normalization, IO matrix validation, and strapping pins.
"""

import re

from .mcu_profiles import MCUProfile, PeripheralInfo, PinCapability, PinInfo


class ESP32Profile(MCUProfile):
    """ESP32 MCU profile with flexible GPIO matrix and strapping pin warnings."""

    def __init__(self):
        """Initialize ESP32 profile."""
        super().__init__("esp32")

    def _initialize_pin_definitions(self) -> None:
        """Initialize ESP32 pin definitions and capabilities."""
        # ESP32 has flexible GPIO matrix - most pins can be assigned to most functions
        # Using ESP32-WROOM-32 pinout as reference

        # Define all available GPIO pins
        gpio_pins = [
            0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23,
            25, 26, 27, 32, 33, 34, 35, 36, 37, 38, 39
        ]

        # Input-only pins (no output capability)
        input_only_pins = {34, 35, 36, 37, 38, 39}

        # ADC1 pins
        adc1_pins = {32, 33, 34, 35, 36, 37, 38, 39}

        # ADC2 pins (note: ADC2 not available when WiFi is used)
        adc2_pins = {0, 2, 4, 12, 13, 14, 15, 25, 26, 27}

        # Touch sensor pins
        touch_pins = {0, 2, 4, 12, 13, 14, 15, 27, 32, 33}

        # DAC pins
        dac_pins = {25, 26}

        for pin_num in gpio_pins:
            pin_name = f"GPIO{pin_num}"

            # Base capabilities
            capabilities = {PinCapability.GPIO}

            # Output capability (most pins except input-only)
            if pin_num not in input_only_pins:
                # Most peripherals available via GPIO matrix
                capabilities.update({
                    PinCapability.PWM,
                    PinCapability.I2C_SDA,
                    PinCapability.I2C_SCL,
                    PinCapability.SPI_MOSI,
                    PinCapability.SPI_MISO,
                    PinCapability.SPI_SCK,
                    PinCapability.SPI_CS,
                    PinCapability.UART_TX,
                    PinCapability.UART_RX,
                })

            # ADC capability
            if pin_num in adc1_pins or pin_num in adc2_pins:
                capabilities.add(PinCapability.ADC)

            # DAC capability
            if pin_num in dac_pins:
                capabilities.add(PinCapability.DAC)

            # Special function and warnings
            special_function = self._get_esp32_special_function(pin_num)
            warnings = self._get_esp32_pin_warnings(pin_num)

            self.pins[pin_name] = PinInfo(
                name=pin_name,
                capabilities=capabilities,
                special_function=special_function,
                warnings=warnings,
                alternate_names=[f"IO{pin_num}", str(pin_num)]
            )

    def _get_esp32_special_function(self, pin_num: int) -> str:
        """Get special function description for ESP32 pins."""
        special_functions = {
            0: "Strapping Pin / Boot Mode / ADC2_CH1 / Touch1",
            1: "UART0 TX (Console)",
            2: "Strapping Pin / Boot Mode / ADC2_CH2 / Touch2",
            3: "UART0 RX (Console)",
            5: "Strapping Pin / VSPI CS0",
            12: "Strapping Pin / Boot Voltage / ADC2_CH5 / Touch5",
            15: "Strapping Pin / Boot Silence / ADC2_CH3 / Touch3",
            25: "DAC1 / ADC2_CH8",
            26: "DAC2 / ADC2_CH9",
            34: "ADC1_CH6 (Input Only)",
            35: "ADC1_CH7 (Input Only)",
            36: "ADC1_CH0 / VP (Input Only)",
            37: "ADC1_CH1 (Input Only)",
            38: "ADC1_CH2 (Input Only)",
            39: "ADC1_CH3 / VN (Input Only)"
        }
        return special_functions.get(pin_num)

    def _get_esp32_pin_warnings(self, pin_num: int) -> list[str]:
        """Get ESP32-specific pin warnings."""
        warnings = []

        # Strapping pins - affect boot behavior
        strapping_pins = {0, 2, 5, 12, 15}
        if pin_num in strapping_pins:
            warnings.append("Strapping pin - state at boot affects ESP32 behavior")

        # Boot-critical pins
        if pin_num == 0:
            warnings.append("GPIO0 low at boot enters download mode")
        elif pin_num == 2:
            warnings.append("GPIO2 must be low/floating at boot")
        elif pin_num == 12:
            warnings.append("GPIO12 controls boot voltage - keep low for 3.3V VDD")
        elif pin_num == 15:
            warnings.append("GPIO15 controls boot message silence")

        # UART pins
        if pin_num in [1, 3]:
            warnings.append("UART0 pin - used for programming and console output")

        # Input-only pins
        if pin_num in [34, 35, 36, 37, 38, 39]:
            warnings.append("Input-only pin - no output or pull-up capability")

        # ADC2 limitations
        adc2_pins = {0, 2, 4, 12, 13, 14, 15, 25, 26, 27}
        if pin_num in adc2_pins:
            warnings.append("ADC2 not available when WiFi is active")

        # High-frequency limitations
        if pin_num in [6, 7, 8, 9, 10, 11]:  # Connected to flash
            warnings.append("Connected to SPI flash - avoid using")

        return warnings

    def _initialize_peripherals(self) -> None:
        """Initialize ESP32 peripheral definitions."""
        # ESP32 GPIO matrix allows most pins to be assigned to most peripherals
        # These are just common/recommended assignments

        # I2C peripherals (can use any GPIO via matrix)
        self.peripherals.extend([
            PeripheralInfo("I2C", 0, {
                "recommended_sda": ["GPIO21", "GPIO4", "GPIO15"],
                "recommended_scl": ["GPIO22", "GPIO5", "GPIO2"]
            }),
            PeripheralInfo("I2C", 1, {
                "recommended_sda": ["GPIO33", "GPIO32", "GPIO26"],
                "recommended_scl": ["GPIO25", "GPIO27", "GPIO14"]
            }),
        ])

        # SPI peripherals
        self.peripherals.extend([
            PeripheralInfo("SPI", 2, {  # HSPI
                "default_mosi": "GPIO13", "default_miso": "GPIO12",
                "default_sck": "GPIO14", "default_cs": "GPIO15"
            }),
            PeripheralInfo("SPI", 3, {  # VSPI
                "default_mosi": "GPIO23", "default_miso": "GPIO19",
                "default_sck": "GPIO18", "default_cs": "GPIO5"
            }),
        ])

        # UART peripherals
        self.peripherals.extend([
            PeripheralInfo("UART", 0, {
                "default_tx": "GPIO1", "default_rx": "GPIO3",
                "note": "Used for programming and console"
            }),
            PeripheralInfo("UART", 1, {
                "recommended_tx": ["GPIO4", "GPIO9", "GPIO10"],
                "recommended_rx": ["GPIO5", "GPIO6", "GPIO16"]
            }),
            PeripheralInfo("UART", 2, {
                "recommended_tx": ["GPIO16", "GPIO17"],
                "recommended_rx": ["GPIO4", "GPIO9"]
            }),
        ])

        # ADC peripherals
        self.peripherals.extend([
            PeripheralInfo("ADC", 1, {
                "channels": {
                    0: "GPIO36", 1: "GPIO37", 2: "GPIO38", 3: "GPIO39",
                    6: "GPIO34", 7: "GPIO35"
                },
                "note": "Always available"
            }),
            PeripheralInfo("ADC", 2, {
                "channels": {
                    1: "GPIO0", 2: "GPIO2", 3: "GPIO15", 4: "GPIO13",
                    5: "GPIO12", 6: "GPIO14", 7: "GPIO27", 8: "GPIO25", 9: "GPIO26"
                },
                "note": "Not available when WiFi is active"
            }),
        ])

        # DAC peripheral
        self.peripherals.append(
            PeripheralInfo("DAC", 0, {
                "channel1": "GPIO25", "channel2": "GPIO26"
            })
        )

        # Touch sensor
        self.peripherals.append(
            PeripheralInfo("TOUCH", 0, {
                "channels": {
                    0: "GPIO4", 1: "GPIO0", 2: "GPIO2", 3: "GPIO15",
                    4: "GPIO13", 5: "GPIO12", 6: "GPIO14", 7: "GPIO27",
                    8: "GPIO33", 9: "GPIO32"
                }
            })
        )

    def normalize_pin_name(self, pin_name: str) -> str:
        """
        Normalize pin name according to ESP32 conventions.
        
        Args:
            pin_name: Raw pin name from schematic/CSV
            
        Returns:
            Normalized pin name (GPIOnn format)
            
        Raises:
            ValueError: If pin name cannot be normalized
        """
        if not pin_name:
            raise ValueError("Pin name cannot be empty")

        # Remove whitespace and convert to uppercase
        pin_name = pin_name.strip().upper()

        # Try exact match first
        if pin_name in self.pins:
            return pin_name

        # Handle IOnn format -> GPIOnn
        io_match = re.match(r"IO(\d+)", pin_name)
        if io_match:
            pin_num = int(io_match.group(1))
            normalized = f"GPIO{pin_num}"
            if normalized in self.pins:
                return normalized

        # Handle numeric-only format -> GPIOnn
        if pin_name.isdigit():
            pin_num = int(pin_name)
            normalized = f"GPIO{pin_num}"
            if normalized in self.pins:
                return normalized

        # Handle GPIOnn format (already normalized)
        if pin_name.startswith("GPIO"):
            if pin_name in self.pins:
                return pin_name

        # Check alternate names
        for pin_id, pin_info in self.pins.items():
            if pin_info.alternate_names and pin_name in pin_info.alternate_names:
                return pin_id

        # Unknown format
        raise ValueError(f"Cannot normalize ESP32 pin name: {pin_name}")

    def validate_pin_assignment(self, pin_name: str, role: str) -> list[str]:
        """
        ESP32-specific pin assignment validation.
        
        Args:
            pin_name: Normalized pin name
            role: Assigned role/function
            
        Returns:
            List of validation warnings
        """
        warnings = super().validate_pin_assignment(pin_name, role)

        # Extract pin number for checks
        pin_match = re.match(r"GPIO(\d+)", pin_name)
        if not pin_match:
            return warnings

        pin_num = int(pin_match.group(1))

        # ESP32-specific validation
        strapping_pins = {0, 2, 5, 12, 15}
        if pin_num in strapping_pins and role != "strapping":
            warnings.append(f"GPIO{pin_num} is a strapping pin - may affect boot behavior")

        # UART0 pins
        if pin_num in [1, 3] and not role.startswith("uart"):
            warnings.append(f"GPIO{pin_num} is UART0 - may interfere with programming/console")

        # Input-only pins used for output
        input_only = {34, 35, 36, 37, 38, 39}
        if pin_num in input_only and role in ["gpio.out", "pwm", "spi.mosi", "uart.tx"]:
            warnings.append(f"GPIO{pin_num} is input-only - cannot drive outputs")

        # ADC2 pins with WiFi
        adc2_pins = {0, 2, 4, 12, 13, 14, 15, 25, 26, 27}
        if pin_num in adc2_pins and role == "adc":
            warnings.append(f"GPIO{pin_num} ADC2 not available when WiFi is active")

        # Flash pins
        flash_pins = {6, 7, 8, 9, 10, 11}
        if pin_num in flash_pins:
            warnings.append(f"GPIO{pin_num} connected to SPI flash - avoid using")

        return warnings
