"""Regression tests for the P2 audit fixes.

Covers:
- normalize.get_mcu_profile routes through the TOML profile registry
  (the divergent Python profile classes were removed).
- pin_metadata derives special-function tables from profiles instead of
  hardcoded 3-MCU dicts.
- profile_schema rejects invalid normalization regexes and out-of-range
  output placeholders with clear errors instead of raw tracebacks.
- bom_csv skips rows with missing required fields instead of aborting
  the whole file.
"""

import os
import tempfile
import unittest
from pathlib import Path

from tools.pinmapgen import normalize
from tools.pinmapgen.bom_csv import get_mcu_nets, parse_csv
from tools.pinmapgen.pin_metadata import (
    get_pin_comment,
    get_special_function,
    get_special_functions_short,
)
from tools.pinmapgen.profile_schema import (
    ProfileValidationError,
    validate_profile_toml,
)


class TestNormalizeUsesRegistry(unittest.TestCase):
    """normalize.get_mcu_profile must serve every registered profile."""

    def test_all_builtin_profiles_resolve(self):
        for mcu in ("rp2040", "esp32", "stm32g0", "nrf52840", "atsamd21"):
            profile = normalize.get_mcu_profile(mcu)
            self.assertTrue(profile.pins, f"{mcu} has no pins")

    def test_unknown_mcu_raises_value_error(self):
        with self.assertRaises(ValueError):
            normalize.get_mcu_profile("not_a_real_mcu")

    def test_legacy_rp2040_shim_delegates_to_toml(self):
        legacy = normalize.RP2040Profile()
        self.assertEqual(legacy.normalize_pin_name("GPIO5"), "GP5")
        self.assertIn(25, legacy.valid_gpio_pins)
        self.assertIn("GP24", legacy.special_pins)


class TestPinMetadataFromProfiles(unittest.TestCase):
    """Special-function tables must come from profile data."""

    def test_rp2040_short_table(self):
        table = get_special_functions_short("rp2040")
        self.assertEqual(table.get("GP25"), "USB D+")
        self.assertEqual(table.get("GP26"), "ADC0")

    def test_covers_profiles_beyond_original_three(self):
        # The old hardcoded dicts only knew rp2040/stm32g0/esp32.
        table = get_special_functions_short("nrf52840")
        self.assertEqual(table.get("P0_09"), "NFC1")

    def test_unknown_mcu_yields_empty_table(self):
        self.assertEqual(get_special_functions_short("no_such_mcu"), {})

    def test_get_pin_comment_without_canonical_dict(self):
        self.assertEqual(get_pin_comment("GP24", "rp2040"), "GP24 - USB D-")

    def test_get_special_function_without_canonical_dict(self):
        self.assertEqual(
            get_special_function("PA13", "stm32g0"),
            "SWD Debug IO (SWDIO)",
        )
        self.assertEqual(
            get_special_function("GP0", "rp2040"), "General Purpose I/O"
        )


class TestSchemaRegexValidation(unittest.TestCase):
    """Bad regexes/placeholders must fail schema validation cleanly."""

    @staticmethod
    def _profile(patterns):
        return {
            "profile": {"schema_version": 1, "name": "testmcu"},
            "normalization": {"patterns": patterns},
            "pins": {"groups": [{"names": ["X1"], "capabilities": ["gpio"]}]},
        }

    def _errors_for(self, patterns):
        with self.assertRaises(ProfileValidationError) as ctx:
            validate_profile_toml(self._profile(patterns), "testmcu.toml")
        return "\n".join(ctx.exception.errors)

    def test_invalid_regex_reports_error(self):
        errors = self._errors_for([{"regex": "GPIO(\\d+", "output": "X{0}"}])
        self.assertIn("invalid regular expression", errors)

    def test_out_of_range_placeholder_reports_error(self):
        errors = self._errors_for([{"regex": "GPIO(\\d+)", "output": "X{1}"}])
        self.assertIn("capture group 1", errors)
        self.assertIn("1 group(s)", errors)

    def test_valid_padded_placeholder_passes(self):
        warnings = validate_profile_toml(
            self._profile([{"regex": "P(\\d+)\\.(\\d+)", "output": "P{0}_{1:02}"}]),
            "testmcu.toml",
        )
        self.assertEqual(warnings, [])


class TestCsvRowTolerance(unittest.TestCase):
    """Rows with missing required fields are skipped, not fatal."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    def _write_csv(self, content):
        path = os.path.join(self.temp_dir, "netlist.csv")
        Path(path).write_text(content, encoding="utf-8")
        return path

    def test_row_with_empty_net_is_skipped(self):
        # A no-connect row (empty Net) elsewhere in the export must not
        # prevent parsing the MCU rows.
        csv_path = self._write_csv(
            "Net,Pin,Component,RefDes\n"
            "LED,GP4,RP2040,U1\n"
            ",7,CONN,J1\n"
            "BUTTON,GP5,RP2040,U1\n"
        )
        nets = get_mcu_nets(csv_path, "U1")
        self.assertEqual(set(nets), {"LED", "BUTTON"})

    def test_all_rows_invalid_still_raises(self):
        csv_path = self._write_csv(
            "Net,Pin,Component,RefDes\n"
            ",GP4,RP2040,U1\n"
            "LED,,RP2040,U1\n"
        )
        with self.assertRaises(ValueError):
            parse_csv(csv_path)


if __name__ == "__main__":
    unittest.main()
