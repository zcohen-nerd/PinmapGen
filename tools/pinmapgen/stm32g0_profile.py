"""
STM32G0 MCU Profile for PinmapGen.

Implements STM32G0-specific pin normalization, alternate functions, and validation.
"""

import re

from .mcu_profiles import MCUProfile, PeripheralInfo, PinCapability, PinInfo


class STM32G0Profile(MCUProfile):
    """STM32G0 MCU profile with port-based GPIO and alternate functions."""

    def __init__(self):
        """Initialize STM32G0 profile."""
        super().__init__("stm32g0")

    def _initialize_pin_definitions(self) -> None:
        """Initialize STM32G0 pin definitions and capabilities."""
        # Define GPIO ports and their pin counts (varies by package)
        # Using STM32G071 as reference (48-pin package)

        port_configs = {
            "A": list(range(16)),  # PA0-PA15
            "B": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],  # PB0-PB15
            "C": [6, 13, 14, 15],  # PC6, PC13-PC15
            "D": [0, 1, 2, 3, 8, 9],  # PD0-PD3, PD8-PD9
            "F": [0, 1, 2]  # PF0-PF2
        }

        for port, pins in port_configs.items():
            for pin_num in pins:
                pin_name = f"P{port}{pin_num}"

                # Base capabilities for all GPIO pins
                capabilities = {PinCapability.GPIO}

                # Add specific capabilities based on pin
                capabilities.update(self._get_stm32g0_pin_capabilities(port, pin_num))

                special_function = self._get_stm32g0_special_function(port, pin_num)
                warnings = self._get_stm32g0_pin_warnings(port, pin_num)

                self.pins[pin_name] = PinInfo(
                    name=pin_name,
                    capabilities=capabilities,
                    special_function=special_function,
                    warnings=warnings,
                    alternate_names=[f"GPIO{port}{pin_num}", f"{port}{pin_num}"]
                )

    def _get_stm32g0_pin_capabilities(self, port: str, pin_num: int) -> set:
        """Get STM32G0-specific pin capabilities based on alternate functions."""
        capabilities = set()

        # PWM capabilities (TIM1, TIM2, TIM3, TIM14, TIM15, TIM16, TIM17)
        pwm_pins = {
            ("A", 0): True, ("A", 1): True, ("A", 2): True, ("A", 3): True,
            ("A", 6): True, ("A", 7): True, ("A", 8): True, ("A", 9): True,
            ("A", 10): True, ("A", 11): True, ("B", 0): True, ("B", 1): True,
            ("B", 3): True, ("B", 4): True, ("B", 5): True, ("B", 6): True,
            ("B", 7): True, ("B", 8): True, ("B", 9): True, ("B", 14): True,
            ("B", 15): True, ("C", 6): True
        }
        if (port, pin_num) in pwm_pins:
            capabilities.add(PinCapability.PWM)

        # ADC capabilities (ADC1)
        adc_pins = {
            ("A", 0), ("A", 1), ("A", 2), ("A", 3), ("A", 4), ("A", 5),
            ("A", 6), ("A", 7), ("B", 0), ("B", 1), ("B", 2), ("B", 10),
            ("B", 11), ("B", 12), ("C", 4), ("C", 5)
        }
        if (port, pin_num) in adc_pins:
            capabilities.add(PinCapability.ADC)

        # DAC capabilities (DAC1)
        if (port, pin_num) in [("A", 4), ("A", 5)]:
            capabilities.add(PinCapability.DAC)

        # I2C capabilities
        i2c_pins = {
            # I2C1
            ("A", 9): {PinCapability.I2C_SCL}, ("A", 10): {PinCapability.I2C_SDA},
            ("B", 6): {PinCapability.I2C_SCL}, ("B", 7): {PinCapability.I2C_SDA},
            ("B", 8): {PinCapability.I2C_SCL}, ("B", 9): {PinCapability.I2C_SDA},
            # I2C2
            ("A", 11): {PinCapability.I2C_SCL}, ("A", 12): {PinCapability.I2C_SDA},
            ("B", 10): {PinCapability.I2C_SCL}, ("B", 11): {PinCapability.I2C_SDA},
            ("B", 13): {PinCapability.I2C_SCL}, ("B", 14): {PinCapability.I2C_SDA}
        }
        if (port, pin_num) in i2c_pins:
            capabilities.update(i2c_pins[(port, pin_num)])

        # SPI capabilities
        spi_pins = {
            # SPI1
            ("A", 5): {PinCapability.SPI_SCK}, ("A", 6): {PinCapability.SPI_MISO},
            ("A", 7): {PinCapability.SPI_MOSI}, ("A", 15): {PinCapability.SPI_CS},
            ("B", 3): {PinCapability.SPI_SCK}, ("B", 4): {PinCapability.SPI_MISO},
            ("B", 5): {PinCapability.SPI_MOSI}, ("A", 4): {PinCapability.SPI_CS},
            # SPI2
            ("B", 13): {PinCapability.SPI_SCK}, ("B", 14): {PinCapability.SPI_MISO},
            ("B", 15): {PinCapability.SPI_MOSI}, ("B", 12): {PinCapability.SPI_CS},
            ("C", 7): {PinCapability.SPI_SCK}, ("C", 2): {PinCapability.SPI_MISO},
            ("C", 3): {PinCapability.SPI_MOSI}, ("B", 9): {PinCapability.SPI_CS}
        }
        if (port, pin_num) in spi_pins:
            capabilities.update(spi_pins[(port, pin_num)])

        # UART capabilities
        uart_pins = {
            # USART1
            ("A", 9): {PinCapability.UART_TX}, ("A", 10): {PinCapability.UART_RX},
            ("B", 6): {PinCapability.UART_TX}, ("B", 7): {PinCapability.UART_RX},
            # USART2
            ("A", 2): {PinCapability.UART_TX}, ("A", 3): {PinCapability.UART_RX},
            ("A", 14): {PinCapability.UART_TX}, ("A", 15): {PinCapability.UART_RX},
            # USART3
            ("B", 10): {PinCapability.UART_TX}, ("B", 11): {PinCapability.UART_RX},
            ("C", 4): {PinCapability.UART_TX}, ("C", 5): {PinCapability.UART_RX}
        }
        if (port, pin_num) in uart_pins:
            capabilities.update(uart_pins[(port, pin_num)])

        return capabilities

    def _get_stm32g0_special_function(self, port: str, pin_num: int) -> str:
        """Get special function description for STM32G0 pins."""
        special_functions = {
            ("A", 13): "SWD Debug IO (SWDIO)",
            ("A", 14): "SWD Debug Clock (SWCLK)",
            ("B", 2): "Boot1 Pin",
            ("C", 14): "LSE Crystal (32kHz)",
            ("C", 15): "LSE Crystal (32kHz)",
            ("F", 0): "HSE Crystal Input",
            ("F", 1): "HSE Crystal Output",
            ("F", 2): "NRST (Reset)"
        }
        return special_functions.get((port, pin_num))

    def _get_stm32g0_pin_warnings(self, port: str, pin_num: int) -> list[str]:
        """Get STM32G0-specific pin warnings."""
        warnings = []

        # Debug interface pins
        if (port, pin_num) in [("A", 13), ("A", 14)]:
            warnings.append("SWD debug pin - avoid using for GPIO if debugging needed")

        # Boot pin
        if (port, pin_num) == ("B", 2):
            warnings.append("Boot1 pin - state affects boot mode")

        # Crystal pins
        if (port, pin_num) in [("C", 14), ("C", 15)]:
            warnings.append("LSE crystal pin - avoid if external 32kHz crystal used")

        if (port, pin_num) in [("F", 0), ("F", 1)]:
            warnings.append("HSE crystal pin - avoid if external crystal/oscillator used")

        # Reset pin
        if (port, pin_num) == ("F", 2):
            warnings.append("NRST reset pin - typically connected to reset circuit")

        return warnings

    def _initialize_peripherals(self) -> None:
        """Initialize STM32G0 peripheral definitions."""
        # I2C peripherals with specific pin assignments
        self.peripherals.extend([
            PeripheralInfo("I2C", 1, {
                "scl_pins": ["PA9", "PB6", "PB8"],
                "sda_pins": ["PA10", "PB7", "PB9"]
            }),
            PeripheralInfo("I2C", 2, {
                "scl_pins": ["PA11", "PB10", "PB13"],
                "sda_pins": ["PA12", "PB11", "PB14"]
            }),
        ])

        # SPI peripherals
        self.peripherals.extend([
            PeripheralInfo("SPI", 1, {
                "sck_pins": ["PA5", "PB3"],
                "miso_pins": ["PA6", "PB4"],
                "mosi_pins": ["PA7", "PB5"],
                "cs_pins": ["PA4", "PA15"]
            }),
            PeripheralInfo("SPI", 2, {
                "sck_pins": ["PB13", "PC7"],
                "miso_pins": ["PB14", "PC2"],
                "mosi_pins": ["PB15", "PC3"],
                "cs_pins": ["PB9", "PB12"]
            }),
        ])

        # UART peripherals
        self.peripherals.extend([
            PeripheralInfo("USART", 1, {
                "tx_pins": ["PA9", "PB6"], "rx_pins": ["PA10", "PB7"]
            }),
            PeripheralInfo("USART", 2, {
                "tx_pins": ["PA2", "PA14"], "rx_pins": ["PA3", "PA15"]
            }),
            PeripheralInfo("USART", 3, {
                "tx_pins": ["PB10", "PC4"], "rx_pins": ["PB11", "PC5"]
            }),
        ])

        # ADC peripheral
        self.peripherals.append(
            PeripheralInfo("ADC", 1, {
                "channels": {
                    0: "PA0", 1: "PA1", 2: "PA2", 3: "PA3", 4: "PA4",
                    5: "PA5", 6: "PA6", 7: "PA7", 8: "PB0", 9: "PB1",
                    10: "PB2", 11: "PB10", 12: "PB11", 15: "PB12"
                }
            })
        )

        # DAC peripheral
        self.peripherals.append(
            PeripheralInfo("DAC", 1, {"out1": "PA4", "out2": "PA5"})
        )

    def normalize_pin_name(self, pin_name: str) -> str:
        """
        Normalize pin name according to STM32G0 conventions.
        
        Args:
            pin_name: Raw pin name from schematic/CSV
            
        Returns:
            Normalized pin name (PXnn format)
            
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

        # Handle GPIOXnn format -> PXnn
        gpio_match = re.match(r"GPIO([A-F])(\d+)", pin_name)
        if gpio_match:
            port, pin_num = gpio_match.groups()
            normalized = f"P{port}{pin_num}"
            if normalized in self.pins:
                return normalized

        # Handle Xnn format -> PXnn (e.g., A5 -> PA5)
        port_match = re.match(r"([A-F])(\d+)", pin_name)
        if port_match:
            port, pin_num = port_match.groups()
            normalized = f"P{port}{pin_num}"
            if normalized in self.pins:
                return normalized

        # Handle PXnn format (already normalized)
        if re.match(r"P[A-F]\d+", pin_name):
            if pin_name in self.pins:
                return pin_name

        # Check alternate names
        for pin_id, pin_info in self.pins.items():
            if pin_info.alternate_names and pin_name in pin_info.alternate_names:
                return pin_id

        # Unknown format
        raise ValueError(f"Cannot normalize STM32G0 pin name: {pin_name}")

    def validate_pin_assignment(self, pin_name: str, role: str) -> list[str]:
        """
        STM32G0-specific pin assignment validation.
        
        Args:
            pin_name: Normalized pin name  
            role: Assigned role/function
            
        Returns:
            List of validation warnings
        """
        warnings = super().validate_pin_assignment(pin_name, role)

        # STM32G0-specific validation
        if pin_name in ["PA13", "PA14"] and role != "debug":
            warnings.append(f"Pin {pin_name} is SWD debug pin - may conflict with debugging")

        if pin_name == "PB2" and role != "boot":
            warnings.append("PB2 is Boot1 pin - state affects boot mode selection")

        if pin_name in ["PC14", "PC15"] and role not in ["gpio", "crystal"]:
            warnings.append(f"Pin {pin_name} is LSE crystal pin - may conflict with RTC")

        if pin_name in ["PF0", "PF1"] and role not in ["gpio", "crystal"]:
            warnings.append(f"Pin {pin_name} is HSE crystal pin - may conflict with system clock")

        return warnings
