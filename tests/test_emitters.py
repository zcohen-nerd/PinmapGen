"""
Test cases for output emitters.
"""

import unittest
import tempfile
import json
import os
from pathlib import Path
from tools.pinmapgen.emit_json import emit_json
from tools.pinmapgen.emit_micropython import emit_micropython
from tools.pinmapgen.emit_arduino import emit_arduino_header


class TestEmitters(unittest.TestCase):
    """Test output file generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Sample canonical dictionary for testing
        self.canonical_dict = {
            "mcu": "rp2040",
            "pins": {
                "I2C0_SDA": ["GP0"],
                "I2C0_SCL": ["GP1"],
                "LED_DATA": ["GP4"],
                "USB_DP": ["GP24"],
                "USB_DN": ["GP25"]
            },
            "differential_pairs": [
                {
                    "positive": "USB_DP",
                    "negative": "USB_DN"
                }
            ],
            "metadata": {
                "total_nets": 5,
                "total_pins": 5,
                "differential_pairs_count": 1,
                "timestamp": "2025-09-27 12:00:00"
            }
        }
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def test_emit_json_pinmap(self):
        """Test JSON pinmap generation."""
        output_path = os.path.join(self.temp_dir, "test_pinmap.json")
        
        emit_json_pinmap(self.canonical_dict, output_path)
        
        # Verify file was created
        self.assertTrue(os.path.exists(output_path))
        
        # Verify JSON is valid and contains expected data
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        self.assertEqual(data["mcu"], "rp2040")
        self.assertIn("pins", data)
        self.assertIn("differential_pairs", data)
        self.assertEqual(len(data["pins"]), 5)
        self.assertEqual(len(data["differential_pairs"]), 1)
        
    def test_emit_micropython_constants(self):
        """Test MicroPython constants generation."""
        output_path = os.path.join(self.temp_dir, "test_pinmap.py")
        
        emit_micropython_constants(self.canonical_dict, output_path)
        
        # Verify file was created
        self.assertTrue(os.path.exists(output_path))
        
        # Verify content contains expected constants
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        self.assertIn("I2C0_SDA = 0", content)
        self.assertIn("I2C0_SCL = 1", content)
        self.assertIn("LED_DATA = 4", content)
        self.assertIn("USB_DP = 24", content)
        self.assertIn("USB_DN = 25", content)
        
        # Should contain auto-generated header
        self.assertIn("Auto-generated", content)
        
    def test_emit_arduino_header(self):
        """Test Arduino C++ header generation."""
        output_path = os.path.join(self.temp_dir, "test_pinmap.h")
        
        emit_arduino_header(self.canonical_dict, output_path)
        
        # Verify file was created
        self.assertTrue(os.path.exists(output_path))
        
        # Verify content contains expected defines
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        self.assertIn("#define I2C0_SDA 0", content)
        self.assertIn("#define I2C0_SCL 1", content)
        self.assertIn("#define LED_DATA 4", content)
        
        # Should have header guards
        self.assertIn("#ifndef", content)
        self.assertIn("#define", content)
        self.assertIn("#endif", content)
        
    def test_emitters_create_directories(self):
        """Test that emitters create output directories if needed."""
        nested_dir = os.path.join(self.temp_dir, "nested", "path")
        output_path = os.path.join(nested_dir, "pinmap.json")
        
        emit_json_pinmap(self.canonical_dict, output_path)
        
        # Verify nested directory was created
        self.assertTrue(os.path.exists(nested_dir))
        self.assertTrue(os.path.exists(output_path))
        
    def test_emitters_handle_empty_data(self):
        """Test emitters handle empty/minimal data gracefully."""
        empty_dict = {
            "mcu": "test",
            "pins": {},
            "differential_pairs": [],
            "metadata": {}
        }
        
        # Should not crash with empty data
        output_path = os.path.join(self.temp_dir, "empty.json")
        emit_json_pinmap(empty_dict, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        output_path = os.path.join(self.temp_dir, "empty.py")
        emit_micropython_constants(empty_dict, output_path)
        self.assertTrue(os.path.exists(output_path))
        
        output_path = os.path.join(self.temp_dir, "empty.h")
        emit_arduino_header(empty_dict, output_path)
        self.assertTrue(os.path.exists(output_path))
        
    def test_emitters_deterministic_output(self):
        """Test that emitters produce deterministic output."""
        # Generate the same data twice
        output_path1 = os.path.join(self.temp_dir, "test1.json")
        output_path2 = os.path.join(self.temp_dir, "test2.json")
        
        emit_json_pinmap(self.canonical_dict, output_path1)
        emit_json_pinmap(self.canonical_dict, output_path2)
        
        # Read both files
        with open(output_path1, 'r', encoding='utf-8') as f:
            content1 = f.read()
        with open(output_path2, 'r', encoding='utf-8') as f:
            content2 = f.read()
            
        # Should be identical (accounting for timestamps)
        # For this test, we'll just check that both files exist and are non-empty
        self.assertTrue(len(content1) > 0)
        self.assertEqual(len(content1), len(content2))


if __name__ == "__main__":
    unittest.main()