"""
Test cases for pin name normalization functionality.
"""

import unittest

from tools.pinmapgen.profile_registry import ProfileRegistry

_registry = ProfileRegistry()


def RP2040Profile():  # noqa: N802 — keeps historical test call sites readable
    return _registry.get_profile("rp2040")


def STM32G0Profile():  # noqa: N802
    return _registry.get_profile("stm32g0")


def ESP32Profile():  # noqa: N802
    return _registry.get_profile("esp32")


class TestNormalize(unittest.TestCase):
    """Test pin name normalization for different MCUs."""

    def setUp(self):
        """Set up test fixtures."""
        self.rp2040_profile = RP2040Profile()

    def test_rp2040_pin_normalization(self):
        """Test RP2040 pin name normalization."""
        # Standard GPIO pin normalization
        self.assertEqual(self.rp2040_profile.normalize_pin_name("GPIO0"), "GP0")
        self.assertEqual(self.rp2040_profile.normalize_pin_name("GPIO1"), "GP1")
        self.assertEqual(self.rp2040_profile.normalize_pin_name("GPIO15"), "GP15")

        # Already normalized pins should remain unchanged
        self.assertEqual(self.rp2040_profile.normalize_pin_name("GP0"), "GP0")
        self.assertEqual(self.rp2040_profile.normalize_pin_name("GP28"), "GP28")

        # Alternative formats
        self.assertEqual(self.rp2040_profile.normalize_pin_name("0"), "GP0")
        self.assertEqual(self.rp2040_profile.normalize_pin_name("IO5"), "GP5")

    def test_rp2040_special_pins(self):
        """Test normalization of special function pins."""
        # USB pins (note: GP24=USB_DM, GP25=USB_DP per RP2040 datasheet)
        self.assertEqual(self.rp2040_profile.normalize_pin_name("USB_DP"), "GP25")
        self.assertEqual(self.rp2040_profile.normalize_pin_name("USB_DM"), "GP24")
        self.assertEqual(self.rp2040_profile.normalize_pin_name("USB_DN"), "GP24")

        # Alternative USB naming
        self.assertEqual(self.rp2040_profile.normalize_pin_name("USBDP"), "GP25")
        self.assertEqual(self.rp2040_profile.normalize_pin_name("USBDM"), "GP24")

    def test_rp2040_case_insensitive(self):
        """Test that normalization is case insensitive."""
        self.assertEqual(self.rp2040_profile.normalize_pin_name("gpio0"), "GP0")
        self.assertEqual(self.rp2040_profile.normalize_pin_name("Gpio15"), "GP15")
        self.assertEqual(self.rp2040_profile.normalize_pin_name("usb_dp"), "GP25")

    def test_rp2040_invalid_pins(self):
        """Test handling of invalid pin names."""
        # Non-existent pins should raise ValueError
        with self.assertRaises(ValueError):
            self.rp2040_profile.normalize_pin_name("GP99")
        with self.assertRaises(ValueError):
            self.rp2040_profile.normalize_pin_name("INVALID")
        with self.assertRaises(ValueError):
            self.rp2040_profile.normalize_pin_name("")

    def test_edge_cases(self):
        """Test edge cases and malformed input."""
        # Whitespace handling
        self.assertEqual(self.rp2040_profile.normalize_pin_name(" GPIO0 "), "GP0")
        self.assertEqual(self.rp2040_profile.normalize_pin_name("\tGP5\n"), "GP5")

        # Invalid patterns should raise ValueError
        with self.assertRaises(ValueError):
            self.rp2040_profile.normalize_pin_name("GPIO")

    def test_differential_pair_detection(self):
        """Test differential pair detection."""
        nets = {
            "USB_DP": ["GP25"],
            "USB_DM": ["GP24"],
            "I2C_SDA": ["GP0"],
            "I2C_SCL": ["GP1"],
        }

        canonical = self.rp2040_profile.create_canonical_pinmap(nets)
        diff_pairs = canonical.get("differential_pairs", [])

        # Should detect USB differential pair
        self.assertEqual(len(diff_pairs), 1)
        pair = diff_pairs[0]
        self.assertIn(pair["positive"], ["USB_DP", "USB_DM"])
        self.assertIn(pair["negative"], ["USB_DP", "USB_DM"])


class TestSTM32G0Normalize(unittest.TestCase):
    """Test pin name normalization for STM32G0."""

    def setUp(self):
        self.profile = STM32G0Profile()

    def test_stm32g0_pin_normalization(self):
        """Test STM32G0 pin name normalization formats."""
        self.assertEqual(self.profile.normalize_pin_name("PA0"), "PA0")
        self.assertEqual(self.profile.normalize_pin_name("PB6"), "PB6")
        # GPIOA5 -> PA5
        self.assertEqual(self.profile.normalize_pin_name("GPIOA5"), "PA5")
        # A5 -> PA5
        self.assertEqual(self.profile.normalize_pin_name("A5"), "PA5")

    def test_stm32g0_case_insensitive(self):
        """Test that normalization is case insensitive."""
        self.assertEqual(self.profile.normalize_pin_name("pa0"), "PA0")
        self.assertEqual(self.profile.normalize_pin_name("gpiob6"), "PB6")

    def test_stm32g0_special_pins(self):
        """Test special function pin detection."""
        # SWD pins should be recognized
        pin_info = self.profile.pins.get("PA13")
        self.assertIsNotNone(pin_info)
        self.assertIsNotNone(pin_info.special_function)

    def test_stm32g0_invalid_pins(self):
        """Test handling of invalid pin names."""
        with self.assertRaises(ValueError):
            self.profile.normalize_pin_name("")
        with self.assertRaises(ValueError):
            self.profile.normalize_pin_name("INVALID")
        with self.assertRaises(ValueError):
            self.profile.normalize_pin_name("PG0")  # Port G doesn't exist

    def test_stm32g0_canonical_pinmap(self):
        """Test canonical pinmap generation."""
        nets = {
            "I2C_SDA": ["PA10"],
            "I2C_SCL": ["PA9"],
            "LED": ["PB0"],
        }
        canonical = self.profile.create_canonical_pinmap(nets)
        self.assertEqual(canonical["mcu"], "stm32g0")
        self.assertEqual(len(canonical["pins"]), 3)
        self.assertIn("I2C_SDA", canonical["pins"])


class TestESP32Normalize(unittest.TestCase):
    """Test pin name normalization for ESP32."""

    def setUp(self):
        self.profile = ESP32Profile()

    def test_esp32_pin_normalization(self):
        """Test ESP32 pin name normalization formats."""
        self.assertEqual(self.profile.normalize_pin_name("GPIO0"), "GPIO0")
        self.assertEqual(self.profile.normalize_pin_name("GPIO25"), "GPIO25")
        # IO4 -> GPIO4
        self.assertEqual(self.profile.normalize_pin_name("IO4"), "GPIO4")
        # Numeric -> GPIOnn
        self.assertEqual(self.profile.normalize_pin_name("4"), "GPIO4")

    def test_esp32_case_insensitive(self):
        """Test that normalization is case insensitive."""
        self.assertEqual(self.profile.normalize_pin_name("gpio0"), "GPIO0")
        self.assertEqual(self.profile.normalize_pin_name("io4"), "GPIO4")

    def test_esp32_special_pins(self):
        """Test strapping pin detection."""
        pin_info = self.profile.pins.get("GPIO0")
        self.assertIsNotNone(pin_info)
        # GPIO0 is a strapping pin — should have warnings
        self.assertTrue(len(pin_info.warnings) > 0)

    def test_esp32_invalid_pins(self):
        """Test handling of invalid pin names."""
        with self.assertRaises(ValueError):
            self.profile.normalize_pin_name("")
        with self.assertRaises(ValueError):
            self.profile.normalize_pin_name("INVALID")
        with self.assertRaises(ValueError):
            self.profile.normalize_pin_name("GPIO99")

    def test_esp32_canonical_pinmap(self):
        """Test canonical pinmap generation."""
        nets = {
            "LED": ["GPIO2"],
            "SENSOR": ["GPIO4"],
            "DAC_OUT": ["GPIO25"],
        }
        canonical = self.profile.create_canonical_pinmap(nets)
        self.assertEqual(canonical["mcu"], "esp32")
        self.assertEqual(len(canonical["pins"]), 3)
        self.assertIn("LED", canonical["pins"])


if __name__ == "__main__":
    unittest.main()
