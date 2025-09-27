# Test suite for PinmapGen

This directory contains unit tests for the PinmapGen toolchain.

## Running Tests

### Using Python's unittest module:
```bash
# Run all tests
python -m unittest discover tests

# Run specific test file  
python -m unittest tests.test_normalize

# Run specific test case
python -m unittest tests.test_normalize.TestNormalize.test_rp2040_pin_normalization
```

### Using pytest (if installed):
```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest -v tests/

# Run specific test
pytest tests/test_normalize.py::TestNormalize::test_rp2040_pin_normalization
```

## Test Structure

- `test_normalize.py` - Tests for pin name normalization
- `test_roles.py` - Tests for role inference
- `test_bom_csv.py` - Tests for CSV parsing
- `test_emitters.py` - Tests for output generation
- `fixtures/` - Test data files

## Test Data

Test cases use sample data in the `fixtures/` directory:
- Minimal CSV files for edge case testing
- Sample schematic data
- Expected output files for comparison

## Writing Tests

When adding new tests:

1. **Follow the naming convention:** `test_module_name.py`
2. **Use descriptive test names:** `test_function_with_specific_condition`
3. **Include docstrings:** Explain what the test validates
4. **Test edge cases:** Empty inputs, malformed data, etc.
5. **Use fixtures:** Keep test data in `fixtures/` directory

Example test structure:
```python
import unittest
from pathlib import Path
from tools.pinmapgen.normalize import normalize_pin_name

class TestNormalize(unittest.TestCase):
    def test_rp2040_pin_normalization(self):
        """Test that RP2040 pins are normalized correctly."""
        self.assertEqual(normalize_pin_name("GPIO0", "rp2040"), "GP0")
        self.assertEqual(normalize_pin_name("GP1", "rp2040"), "GP1")
```