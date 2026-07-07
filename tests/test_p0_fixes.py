"""Regression tests for the P0 audit fixes.

Covers:
- Zero-padded pin normalization for nRF52840 and ATSAMD profiles
  (pattern template ``{n:0W}`` support in profile_loader).
- Removal of the incorrect USB D+/D- mapping on nRF52840 P0_13/P0_14.
- Integer pin literals in ESP32-family MicroPython output (the esp32
  MicroPython port rejects string pin ids).
- MCU-family-aware Arduino pin literals and setup macros.
"""

import unittest

from tools.pinmapgen.emit_arduino import (
    _NO_ARDUINO_PIN,
    _arduino_pin_literal,
    generate_arduino_with_roles,
)
from tools.pinmapgen.emit_micropython import (
    _micropython_pin_literal,
    generate_micropython_with_roles,
)
from tools.pinmapgen.profile_registry import ProfileRegistry


def _canonical(mcu, pins):
    return {
        "mcu": mcu,
        "pins": pins,
        "differential_pairs": [],
        "metadata": {
            "total_nets": len(pins),
            "total_pins": sum(len(v) for v in pins.values()),
            "differential_pairs_count": 0,
            "special_pins_used": [],
            "validation_warnings": [],
            "validation_errors": [],
        },
    }


class TestZeroPaddedNormalization(unittest.TestCase):
    """Single-digit pin references must resolve to zero-padded names."""

    @classmethod
    def setUpClass(cls):
        cls.registry = ProfileRegistry()
        cls.nrf = cls.registry.get_profile("nrf52840")
        cls.samd21 = cls.registry.get_profile("atsamd21")
        cls.samd51 = cls.registry.get_profile("atsamd51")
        cls.stm32 = cls.registry.get_profile("stm32g0")

    def test_nrf_dot_notation_single_digit(self):
        self.assertEqual(self.nrf.normalize_pin_name("P0.5"), "P0_05")

    def test_nrf_dot_notation_two_digit(self):
        self.assertEqual(self.nrf.normalize_pin_name("P0.13"), "P0_13")

    def test_nrf_port1_single_digit(self):
        self.assertEqual(self.nrf.normalize_pin_name("P1.2"), "P1_02")

    def test_nrf_underscore_single_digit(self):
        self.assertEqual(self.nrf.normalize_pin_name("P0_5"), "P0_05")

    def test_nrf_gpio_number(self):
        self.assertEqual(self.nrf.normalize_pin_name("GPIO5"), "P0_05")

    def test_samd21_unpadded_with_p(self):
        self.assertEqual(self.samd21.normalize_pin_name("PA2"), "PA02")

    def test_samd21_unpadded_bare_port(self):
        self.assertEqual(self.samd21.normalize_pin_name("B8"), "PB08")

    def test_samd51_unpadded_with_p(self):
        self.assertEqual(self.samd51.normalize_pin_name("PA4"), "PA04")

    def test_stm32_stays_unpadded(self):
        # STM32 canonical names are NOT padded; ensure no regression.
        self.assertEqual(self.stm32.normalize_pin_name("A5"), "PA5")
        self.assertEqual(self.stm32.normalize_pin_name("PA5"), "PA5")


class TestNrfUsbPinData(unittest.TestCase):
    """nRF52840 USB D+/D- are dedicated pads, not GPIOs P0.13/P0.14."""

    @classmethod
    def setUpClass(cls):
        cls.nrf = ProfileRegistry().get_profile("nrf52840")

    def test_p0_13_has_no_usb_capability(self):
        caps = {c.value for c in self.nrf.pins["P0_13"].capabilities}
        self.assertNotIn("usb_dm", caps)
        self.assertNotIn("usb_dp", caps)

    def test_p0_14_has_no_usb_capability(self):
        caps = {c.value for c in self.nrf.pins["P0_14"].capabilities}
        self.assertNotIn("usb_dm", caps)
        self.assertNotIn("usb_dp", caps)

    def test_no_gpio_usb_peripheral_mapping(self):
        for peri in self.nrf.peripherals:
            if peri.name == "USB":
                self.assertNotIn("P0_13", peri.pins.values())
                self.assertNotIn("P0_14", peri.pins.values())


class TestEsp32MicropythonLiterals(unittest.TestCase):
    """MicroPython esp32 port only accepts integer pin ids."""

    def test_gpio_literal_is_int(self):
        self.assertEqual(_micropython_pin_literal("GPIO21"), "21")

    def test_rp2040_literal_unchanged(self):
        self.assertEqual(_micropython_pin_literal("GP4"), "4")

    def test_generated_module_uses_ints(self):
        cd = _canonical("esp32", {"I2C_SDA": ["GPIO21"], "I2C_SCL": ["GPIO22"]})
        code = generate_micropython_with_roles(cd)
        self.assertIn("I2C_SDA = 21", code)
        self.assertIn("I2C_SCL = 22", code)
        self.assertNotIn('"GPIO21"', code)


class TestArduinoFamilyLiterals(unittest.TestCase):
    """Arduino #define values must be valid for each family's core."""

    def test_avr_uno_digital(self):
        self.assertEqual(_arduino_pin_literal("PD3", "atmega328p"), "3")

    def test_avr_uno_analog(self):
        self.assertEqual(_arduino_pin_literal("PC4", "atmega328p"), "A4")

    def test_avr_uno_unmapped_crystal(self):
        self.assertEqual(
            _arduino_pin_literal("PB6", "atmega328p"), _NO_ARDUINO_PIN
        )

    def test_avr_mega_digital(self):
        self.assertEqual(_arduino_pin_literal("PB7", "atmega2560"), "13")

    def test_avr_mega_analog(self):
        self.assertEqual(_arduino_pin_literal("PK0", "atmega2560"), "A8")

    def test_samd21_zero_map(self):
        self.assertEqual(_arduino_pin_literal("PA17", "atsamd21"), "13")

    def test_samd51_unmapped(self):
        # No universal SAMD51 board mapping — sentinel, not a fake pin.
        self.assertEqual(
            _arduino_pin_literal("PA16", "atsamd51"), _NO_ARDUINO_PIN
        )

    def test_stm32_pin_name_passthrough(self):
        self.assertEqual(_arduino_pin_literal("PA10", "stm32f411"), "PA10")

    def test_nrf_flat_number(self):
        self.assertEqual(_arduino_pin_literal("P1_00", "nrf52840"), "32")


class TestArduinoFamilyMacros(unittest.TestCase):
    """Bus setup macros must use APIs that exist on each family's core."""

    def _header(self, mcu, pins):
        return generate_arduino_with_roles(_canonical(mcu, pins))

    def test_rp2040_uses_setsda(self):
        header = self._header(
            "rp2040", {"I2C0_SDA": ["GP0"], "I2C0_SCL": ["GP1"]}
        )
        self.assertIn("Wire.setSDA(I2C0_SDA)", header)

    def test_esp32_uses_begin_with_pins(self):
        header = self._header(
            "esp32", {"I2C0_SDA": ["GPIO21"], "I2C0_SCL": ["GPIO22"]}
        )
        self.assertIn("Wire.begin(I2C0_SDA, I2C0_SCL, freq)", header)
        self.assertNotIn("Wire.setSDA", header)

    def test_avr_uses_plain_begin(self):
        header = self._header(
            "atmega328p", {"I2C0_SDA": ["PC4"], "I2C0_SCL": ["PC5"]}
        )
        self.assertIn("Wire.begin()", header)
        self.assertNotIn("Wire.setSDA", header)

    def test_stm32_spi_uses_setsclk(self):
        header = self._header(
            "stm32g0",
            {
                "SPI1_MOSI": ["PA7"],
                "SPI1_MISO": ["PA6"],
                "SPI1_SCK": ["PA5"],
            },
        )
        self.assertIn("SPI.setSCLK(SPI1_SCK)", header)
        self.assertNotIn("SPI.setSCK(", header)

    def test_esp32_spi_begin_signature(self):
        header = self._header(
            "esp32",
            {
                "SPI_MOSI": ["GPIO23"],
                "SPI_MISO": ["GPIO19"],
                "SPI_SCK": ["GPIO18"],
            },
        )
        self.assertIn("SPI.begin(SPI_SCK, SPI_MISO, SPI_MOSI)", header)

    def test_macros_wrapped_in_do_while(self):
        header = self._header(
            "rp2040", {"I2C0_SDA": ["GP0"], "I2C0_SCL": ["GP1"]}
        )
        self.assertIn("do { \\", header)
        self.assertIn("} while (0)", header)

    def test_no_deprecated_clock_divider(self):
        header = self._header(
            "rp2040",
            {"SPI_MOSI": ["GP3"], "SPI_MISO": ["GP4"], "SPI_SCK": ["GP2"]},
        )
        self.assertNotIn("setClockDivider", header)

    def test_unmapped_pin_flagged_in_comment(self):
        header = self._header("atmega328p", {"XTAL_NET": ["PB6"]})
        self.assertIn("no Arduino pin mapping", header)


if __name__ == "__main__":
    unittest.main()
