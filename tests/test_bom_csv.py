"""
Test cases for CSV parsing functionality.
"""

import os
import shutil
import tempfile
import unittest

from tools.pinmapgen.bom_csv import get_mcu_nets


class TestBomCsv(unittest.TestCase):
    """Test CSV netlist parsing."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp files
        shutil.rmtree(self.temp_dir)

    def create_test_csv(self, content: str) -> str:
        """Create a temporary CSV file with given content."""
        csv_path = os.path.join(self.temp_dir, "test.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(content)
        return csv_path

    def test_parse_valid_csv(self):
        """Test parsing a valid CSV netlist."""
        csv_content = """Net,Pin,Component,RefDes
LED_STATUS,GP15,RP2040,U1
LED_ERROR,GP16,RP2040,U1
I2C_SDA,GP4,RP2040,U1"""

        csv_path = self.create_test_csv(csv_content)
        result = get_mcu_nets(csv_path, "U1")

        self.assertEqual(
            result,
            {
                "LED_STATUS": ["GP15"],
                "LED_ERROR": ["GP16"],
                "I2C_SDA": ["GP4"],
            },
        )

    def test_parse_empty_csv(self):
        """Test parsing an empty CSV file."""
        csv_content = "Net,Pin,Component,RefDes\n"
        csv_path = self.create_test_csv(csv_content)

        # Empty CSV should raise an error
        with self.assertRaises(ValueError):
            get_mcu_nets(csv_path, "U1")

    def test_parse_no_matching_ref(self):
        """Test parsing CSV with no matching MCU reference."""
        csv_content = """Net,Pin,Component,RefDes
LED_STATUS,GP15,RP2040,U2
LED_ERROR,GP16,RP2040,U2"""

        csv_path = self.create_test_csv(csv_content)

        # Should raise error when no matching reference found
        with self.assertRaises(ValueError):
            get_mcu_nets(csv_path, "U1")  # Look for U1 not U2

    def test_parse_invalid_csv_format(self):
        """Test parsing CSV with wrong column headers."""
        csv_content = """Wrong,Headers,Here
RP2040,U1,20"""

        csv_path = self.create_test_csv(csv_content)
        with self.assertRaises(ValueError):
            get_mcu_nets(csv_path, "U1")

    def test_parse_missing_file(self):
        """Test parsing nonexistent file."""
        with self.assertRaises(FileNotFoundError):
            get_mcu_nets("/nonexistent/file.csv", "U1")


if __name__ == "__main__":
    unittest.main()
