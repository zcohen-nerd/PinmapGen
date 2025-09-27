"""
Test cases for pin name normalization functionality.
"""

import unittest

from tools.pinmapgen.rp2040_profile import RP2040Profile


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
            "I2C_SCL": ["GP1"]
        }

        canonical = self.rp2040_profile.create_canonical_pinmap(nets)
        diff_pairs = canonical.get("differential_pairs", [])

        # Should detect USB differential pair
        self.assertEqual(len(diff_pairs), 1)
        pair = diff_pairs[0]
        self.assertIn(pair["positive"], ["USB_DP", "USB_DM"])
        self.assertIn(pair["negative"], ["USB_DP", "USB_DM"])


if __name__ == "__main__":
    unittest.main()
