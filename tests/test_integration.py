"""
Simple integration test to verify the basic functionality works.

This test runs the CLI and checks that files are generated without errors.
"""

import unittest
import tempfile
import os
import subprocess
import sys
from pathlib import Path


class TestIntegration(unittest.TestCase):
    """Integration tests for the PinmapGen toolchain."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def test_cli_help_works(self):
        """Test that CLI help command works."""
        result = subprocess.run([
            sys.executable, "-m", "tools.pinmapgen.cli", "--help"
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Generate pinmaps from Fusion Electronics", result.stdout)
        
    def test_cli_generates_files(self):
        """Test that CLI generates expected output files."""
        # Use the existing sample netlist
        sample_csv = "hardware/exports/sample_netlist.csv"
        
        # Run the CLI to generate files in temp directory
        result = subprocess.run([
            sys.executable, "-m", "tools.pinmapgen.cli",
            "--csv", sample_csv,
            "--mcu", "rp2040", 
            "--mcu-ref", "U1",
            "--out-root", self.temp_dir,
            "--mermaid"
        ], capture_output=True, text=True)
        
        # Should complete successfully
        self.assertEqual(result.returncode, 0, f"CLI failed: {result.stderr}")
        
        # Check that expected files were created
        expected_files = [
            "pinmaps/pinmap.json",
            "firmware/micropython/pinmap_micropython.py",
            "firmware/include/pinmap_arduino.h", 
            "firmware/docs/PINOUT.md",
            "firmware/docs/pinout.mmd"
        ]
        
        for file_path in expected_files:
            full_path = os.path.join(self.temp_dir, file_path)
            self.assertTrue(os.path.exists(full_path), f"Missing file: {file_path}")
            
            # Check that file has content
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertGreater(len(content), 0, f"Empty file: {file_path}")
        
    def test_modules_can_be_imported(self):
        """Test that all modules can be imported without errors."""
        modules_to_test = [
            "tools.pinmapgen.cli",
            "tools.pinmapgen.bom_csv", 
            "tools.pinmapgen.eagle_sch",
            "tools.pinmapgen.normalize",
            "tools.pinmapgen.roles",
            "tools.pinmapgen.emit_json",
            "tools.pinmapgen.emit_micropython",
            "tools.pinmapgen.emit_arduino",
            "tools.pinmapgen.emit_markdown",
            "tools.pinmapgen.emit_mermaid",
            "tools.pinmapgen.watch"
        ]
        
        for module_name in modules_to_test:
            try:
                __import__(module_name)
            except ImportError as e:
                self.fail(f"Failed to import {module_name}: {e}")


if __name__ == "__main__":
    unittest.main()