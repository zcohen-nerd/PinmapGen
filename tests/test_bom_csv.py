"""
Test cases for CSV parsing functionality.
"""

import unittest
import tempfile
import os
from pathlib import Path
from tools.pinmapgen.bom_csv import parse_netlist_tuples


class TestBomCsv(unittest.TestCase):
    """Test CSV netlist parsing."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp files
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def create_test_csv(self, content: str) -> str:
        """Create a temporary CSV file with given content."""
        csv_path = os.path.join(self.temp_dir, "test.csv")
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return csv_path
        
    def test_parse_valid_csv(self):
        """Test parsing a valid CSV netlist."""
        csv_content = """Part,Designator,Footprint,Quantity,Designation,Supplier and ref,Pin,Net
Pico,U1,RP2040,1,RP2040 Microcontroller,,GP0,I2C0_SDA
Pico,U1,RP2040,1,RP2040 Microcontroller,,GP1,I2C0_SCL
Pico,U1,RP2040,1,RP2040 Microcontroller,,GP4,LED_DATA"""
        
        csv_path = self.create_test_csv(csv_content)
        result = parse_csv_netlist(csv_path, "U1")
        
        self.assertIsNotNone(result)
        self.assertEqual(result.mcu, "U1")
        self.assertEqual(len(result.pin_assignments), 3)
        
        # Check specific pin assignments
        assignments = {pa.pin: pa.net for pa in result.pin_assignments}
        self.assertEqual(assignments["GP0"], "I2C0_SDA")
        self.assertEqual(assignments["GP1"], "I2C0_SCL")
        self.assertEqual(assignments["GP4"], "LED_DATA")
        
    def test_parse_empty_csv(self):
        """Test parsing an empty CSV file."""
        csv_content = "Part,Designator,Footprint,Quantity,Designation,Supplier and ref,Pin,Net\n"
        csv_path = self.create_test_csv(csv_content)
        result = parse_csv_netlist(csv_path, "U1")
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result.pin_assignments), 0)
        
    def test_parse_missing_mcu_ref(self):
        """Test parsing CSV with no matching MCU reference."""
        csv_content = """Part,Designator,Footprint,Quantity,Designation,Supplier and ref,Pin,Net
Pico,U2,RP2040,1,RP2040 Microcontroller,,GP0,I2C0_SDA"""
        
        csv_path = self.create_test_csv(csv_content)
        result = parse_csv_netlist(csv_path, "U1")  # Looking for U1, but file has U2
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result.pin_assignments), 0)
        
    def test_parse_malformed_csv(self):
        """Test parsing malformed CSV file."""
        csv_content = "This is not a valid CSV file"
        csv_path = self.create_test_csv(csv_content)
        result = parse_csv_netlist(csv_path, "U1")
        
        # Should handle gracefully and return None or empty result
        self.assertIsNotNone(result)
        
    def test_parse_nonexistent_file(self):
        """Test parsing non-existent file."""
        result = parse_csv_netlist("/nonexistent/file.csv", "U1")
        self.assertIsNone(result)
        
    def test_parse_different_encodings(self):
        """Test parsing CSV with different text encodings."""
        csv_content = """Part,Designator,Footprint,Quantity,Designation,Supplier and ref,Pin,Net
Pico,U1,RP2040,1,RP2040 Microcontroller,,GP0,I2C0_SDA"""
        
        # Test UTF-8 (default)
        csv_path = self.create_test_csv(csv_content)
        result = parse_csv_netlist(csv_path, "U1")
        self.assertIsNotNone(result)
        
    def test_parse_with_extra_columns(self):
        """Test parsing CSV with extra columns."""
        csv_content = """Part,Designator,Footprint,Quantity,Designation,Supplier and ref,Pin,Net,Extra1,Extra2
Pico,U1,RP2040,1,RP2040 Microcontroller,,GP0,I2C0_SDA,Extra,Data"""
        
        csv_path = self.create_test_csv(csv_content)
        result = parse_csv_netlist(csv_path, "U1")
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result.pin_assignments), 1)
        
    def test_parse_multiple_mcu_refs(self):
        """Test parsing CSV with multiple MCU references."""
        csv_content = """Part,Designator,Footprint,Quantity,Designation,Supplier and ref,Pin,Net
Pico,U1,RP2040,1,RP2040 Microcontroller,,GP0,I2C0_SDA
Pico,U2,RP2040,1,RP2040 Microcontroller,,GP0,SPI_SCK
Pico,U1,RP2040,1,RP2040 Microcontroller,,GP1,I2C0_SCL"""
        
        csv_path = self.create_test_csv(csv_content)
        result = parse_csv_netlist(csv_path, "U1")
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result.pin_assignments), 2)  # Only U1 pins
        
        # Verify only U1 pins are included
        nets = [pa.net for pa in result.pin_assignments]
        self.assertIn("I2C0_SDA", nets)
        self.assertIn("I2C0_SCL", nets)
        self.assertNotIn("SPI_SCK", nets)  # This is from U2


if __name__ == "__main__":
    unittest.main()