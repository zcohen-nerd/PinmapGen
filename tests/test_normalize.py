"""
Test cases for pin name normalization functionality.
"""

import unittest
from tools.pinmapgen.normalize import RP2040PinNormalizer


class TestNormalize(unittest.TestCase):
    """Test pin name normalization for different MCUs."""
    
    def test_rp2040_pin_normalization(self):
        """Test RP2040 pin name normalization."""
        # Standard GPIO pin normalization
        self.assertEqual(normalize_pin_name("GPIO0", "rp2040"), "GP0")
        self.assertEqual(normalize_pin_name("GPIO1", "rp2040"), "GP1")
        self.assertEqual(normalize_pin_name("GPIO15", "rp2040"), "GP15")
        
        # Already normalized pins should remain unchanged
        self.assertEqual(normalize_pin_name("GP0", "rp2040"), "GP0")
        self.assertEqual(normalize_pin_name("GP28", "rp2040"), "GP28")
        
        # Alternative formats
        self.assertEqual(normalize_pin_name("Pin0", "rp2040"), "GP0")
        self.assertEqual(normalize_pin_name("IO5", "rp2040"), "GP5")
        
    def test_rp2040_special_pins(self):
        """Test normalization of special function pins."""
        # USB pins
        self.assertEqual(normalize_pin_name("USB_DP", "rp2040"), "GP24")
        self.assertEqual(normalize_pin_name("USB_DM", "rp2040"), "GP25") 
        self.assertEqual(normalize_pin_name("USB_DN", "rp2040"), "GP25")
        
        # Alternative USB naming
        self.assertEqual(normalize_pin_name("USBDP", "rp2040"), "GP24")
        self.assertEqual(normalize_pin_name("USBDM", "rp2040"), "GP25")
        
    def test_rp2040_case_insensitive(self):
        """Test that normalization is case insensitive."""
        self.assertEqual(normalize_pin_name("gpio0", "rp2040"), "GP0")
        self.assertEqual(normalize_pin_name("Gpio15", "rp2040"), "GP15")
        self.assertEqual(normalize_pin_name("usb_dp", "rp2040"), "GP24")
        
    def test_rp2040_invalid_pins(self):
        """Test handling of invalid pin names."""
        # Non-existent pins should return as-is
        self.assertEqual(normalize_pin_name("GP99", "rp2040"), "GP99")
        self.assertEqual(normalize_pin_name("INVALID", "rp2040"), "INVALID")
        self.assertEqual(normalize_pin_name("", "rp2040"), "")
        
    def test_unknown_mcu(self):
        """Test normalization with unknown MCU returns pin as-is."""
        self.assertEqual(normalize_pin_name("GPIO0", "unknown"), "GPIO0")
        self.assertEqual(normalize_pin_name("PA5", "stm32"), "PA5")
        
    def test_edge_cases(self):
        """Test edge cases and malformed input."""
        # None input
        self.assertEqual(normalize_pin_name(None, "rp2040"), None)
        
        # Empty strings
        self.assertEqual(normalize_pin_name("", "rp2040"), "")
        self.assertEqual(normalize_pin_name("GPIO", "rp2040"), "GPIO")
        
        # Whitespace handling
        self.assertEqual(normalize_pin_name(" GPIO0 ", "rp2040"), "GP0")
        self.assertEqual(normalize_pin_name("\tGP5\n", "rp2040"), "GP5")


if __name__ == '__main__':
    unittest.main()