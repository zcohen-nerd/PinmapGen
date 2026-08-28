# Test suite for PinmapGen

Unit and integration tests for the PinmapGen toolchain. The suite is
plain `unittest` — no dependencies to install.

## Running Tests

```bash
# Run everything (from the repo root)
python -m unittest discover -s tests -v

# Run one file
python -m unittest tests.test_roles

# Run one test case
python -m unittest tests.test_p2_validation_and_outputs.TestValidationTaxonomy
```

pytest also works if you have it (`pip install -e ".[dev]"`):

```bash
pytest tests/ -v
```

## What lives where

Rather than one file per module, the suite mixes module-focused files
with regression files named after the audit/fix round that produced
them (run `ls tests/` for the full current list):

- **Module-focused:** `test_normalize.py`, `test_roles.py`,
  `test_bom_csv.py`, `test_emitters.py`, `test_toml_profiles.py`,
  `test_profile_validation.py`, `test_csv_parsing.py`
- **Behavior/regression rounds:** `test_p0_fixes.py` … `test_p3_fixes.py`,
  `test_fixes_35_44.py` … `test_fixes_61_64.py`,
  `test_output_visibility.py`, `test_pin_data_fixes.py`,
  `test_reserved_names.py`, `test_p2_validation_and_outputs.py`
- **End-to-end:** `test_integration.py` (spawns the CLI as a subprocess)
- `fixtures/` — sample input data used by the tests

## Writing Tests

1. **Follow the naming convention:** `test_<topic>.py`
2. **Use descriptive test names:** `test_function_with_specific_condition`
3. **Include docstrings:** Explain what the test validates
4. **Test edge cases:** Empty inputs, malformed data, etc.
5. **Prefer real entry points:** go through `registry.get_profile(...)`
   and `create_canonical_pinmap(...)` rather than private helpers

Example (this runs as-is):

```python
import unittest

from tools.pinmapgen.profile_registry import registry


class TestNormalization(unittest.TestCase):
    def test_rp2040_pin_normalization(self):
        """RP2040 accepts GPIO/GP spellings and canonicalizes to GP<n>."""
        profile = registry.get_profile("rp2040")
        self.assertEqual(profile.normalize_pin_name("GPIO0"), "GP0")
        self.assertEqual(profile.normalize_pin_name("GP1"), "GP1")
```
