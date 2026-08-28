"""
Tests for the P2 audit batch: the error/warning taxonomy, unified
differential-pair detection, input-only and power-rail validation, the
--no-* output-selection flags, and the PINOUT Function column.

Covers audit items P2.1/P2.2 (advisories must not fail --strict),
P2.4 (one pair detector feeding every emitter), P2.5 (power/ground
roles), P2.6 (Function column shows the net's role), P2.7 (input-only
pins), and P2.8 (output format selection).
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.pinmapgen.emit_arduino import generate_arduino_with_roles
from tools.pinmapgen.emit_markdown import generate_single_ended_table
from tools.pinmapgen.emit_micropython import generate_micropython_with_roles
from tools.pinmapgen.profile_registry import registry
from tools.pinmapgen.roles import PinRole, RoleInferencer


class TestValidationTaxonomy(unittest.TestCase):
    """Errors are conflicts only; heuristics are advisories (P2.1/P2.2)."""

    def setUp(self):
        self.profile = registry.get_profile("rp2040")

    def test_pin_conflict_is_an_error(self):
        errors = self.profile.validate_pinmap(
            {"NET_A": ["GP5"], "NET_B": ["GP5"]}
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("used by multiple nets", errors[0])

    def test_multi_pin_net_is_not_an_error(self):
        """A net fanning out to several pins must not fail --strict."""
        errors = self.profile.validate_pinmap(
            {"SENSOR_BUS": ["GP8", "GP9"]}
        )
        self.assertEqual(errors, [])

    def test_multi_pin_net_is_an_advisory(self):
        warnings = self.profile.validate_pinmap_advisories(
            {"SENSOR_BUS": ["GP8", "GP9"]}
        )
        self.assertEqual(len(warnings), 1)
        self.assertIn("fine for a shared bus", warnings[0])

    def test_power_rail_multi_pin_not_flagged(self):
        """VIN across pins is normal wiring, not even an advisory."""
        warnings = self.profile.validate_pinmap_advisories(
            {"VIN": ["GP8", "GP9"], "VSYS": ["GP10", "GP11"]}
        )
        self.assertEqual(warnings, [])

    def test_active_low_names_are_not_lonely_pairs(self):
        """RESET_N / CS_N are active-low signals, not pair halves."""
        warnings = self.profile.validate_pinmap_advisories(
            {"RESET_N": ["GP5"], "CS_N": ["GP6"], "IRQ_N": ["GP7"]}
        )
        self.assertEqual(warnings, [])

    def test_lonely_positive_half_is_flagged(self):
        warnings = self.profile.validate_pinmap_advisories(
            {"USB_DP": ["GP15"]}
        )
        self.assertEqual(len(warnings), 1)
        self.assertIn("lonely differential pair", warnings[0])

    def test_lonely_can_h_is_flagged(self):
        warnings = self.profile.validate_pinmap_advisories(
            {"CAN_H": ["GP4"]}
        )
        self.assertTrue(
            any("lonely differential pair" in w for w in warnings)
        )


class TestStrictExitCodes(unittest.TestCase):
    """--strict fails on errors only, never on advisories (P2.2)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _run_strict(self, body: str) -> subprocess.CompletedProcess:
        csv_path = Path(self.temp_dir) / "netlist.csv"
        csv_path.write_text(
            "Net,Pin,Component,RefDes\n" + body, encoding="utf-8"
        )
        return subprocess.run(
            [
                sys.executable, "-m", "tools.pinmapgen.cli",
                "--csv", str(csv_path), "--mcu", "rp2040",
                "--mcu-ref", "U1", "--out-root", self.temp_dir,
                "--strict",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_advisories_pass_strict(self):
        """Active-low names, fanned-out nets, and rails exit 0."""
        result = self._run_strict(
            "RESET_N,GP5,RP2040,U1\n"
            "SENSOR_BUS,GP8,RP2040,U1\n"
            "SENSOR_BUS,GP9,RP2040,U1\n"
            "VIN,GP10,RP2040,U1\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # The fanned-out net is still surfaced as a warning.
        self.assertIn("fine for a shared bus", result.stderr)

    def test_conflict_fails_strict(self):
        result = self._run_strict(
            "NET_A,GP5,RP2040,U1\n"
            "NET_B,GP5,RP2040,U1\n"
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("used by multiple nets", result.stderr)


class TestUnifiedDifferentialPairs(unittest.TestCase):
    """One canonical detector feeds every output format (P2.4)."""

    def setUp(self):
        self.profile = registry.get_profile("rp2040")

    def test_usb_plus_minus_detected(self):
        """USB_D+ / USB_D- (schematic-style names) pair up."""
        pairs = self.profile.detect_differential_pairs(
            {"USB_D+": ["GP15"], "USB_D-": ["GP16"]}
        )
        self.assertIn(("USB_D+", "USB_D-"), pairs)

    def test_can_h_l_detected(self):
        pairs = self.profile.detect_differential_pairs(
            {"CAN_H": ["GP4"], "CAN_L": ["GP5"]}
        )
        self.assertIn(("CAN_H", "CAN_L"), pairs)

    def test_pairs_reach_all_emitters(self):
        """The canonical pair shows up in every generated format."""
        canonical = self.profile.create_canonical_pinmap(
            {"USB_D+": ["GP15"], "USB_D-": ["GP16"]}
        )
        pair_lists = canonical["differential_pairs"]
        self.assertEqual(len(pair_lists), 1)
        self.assertEqual(pair_lists[0]["positive"], "USB_D+")
        self.assertEqual(pair_lists[0]["negative"], "USB_D-")

        micropython = generate_micropython_with_roles(canonical)
        self.assertIn("Differential Pair", micropython)

        arduino = generate_arduino_with_roles(canonical)
        self.assertIn("Differential Pair", arduino)

        table = generate_single_ended_table(canonical)
        # Both halves live in the pairs table, not the single-ended one.
        self.assertNotIn("USB_D+", table)


class TestInputOnlyValidation(unittest.TestCase):
    """ESP32 GPIO34-39 warn when an output-role net lands there (P2.7)."""

    def setUp(self):
        self.profile = registry.get_profile("esp32")

    def test_output_role_on_input_only_pin_warns(self):
        warnings = self.profile.validate_pin_assignment("GPIO34", "led")
        self.assertTrue(
            any("input-only" in w for w in warnings), warnings
        )

    def test_input_role_on_input_only_pin_is_fine(self):
        warnings = self.profile.validate_pin_assignment("GPIO34", "adc")
        self.assertFalse(
            any("input-only" in w for w in warnings), warnings
        )

    def test_end_to_end_warning_in_metadata(self):
        canonical = self.profile.create_canonical_pinmap(
            {"LED_STATUS": ["GPIO34"]}
        )
        self.assertTrue(
            any(
                "input-only" in w
                for w in canonical["metadata"]["validation_warnings"]
            )
        )


class TestPowerRailValidation(unittest.TestCase):
    """Power/ground roles exist and rails on GPIOs warn (P2.5)."""

    def test_power_and_ground_roles_inferred(self):
        inferencer = RoleInferencer()
        self.assertEqual(inferencer.infer_role("3V3"), PinRole.POWER)
        self.assertEqual(inferencer.infer_role("VBAT"), PinRole.POWER)
        self.assertEqual(inferencer.infer_role("AGND"), PinRole.GROUND)
        self.assertEqual(inferencer.infer_role("GND"), PinRole.GROUND)

    def test_rail_on_gpio_warns(self):
        profile = registry.get_profile("rp2040")
        canonical = profile.create_canonical_pinmap({"3V3": ["GP5"]})
        self.assertTrue(
            any(
                "power/ground rail" in w
                for w in canonical["metadata"]["validation_warnings"]
            )
        )

    def test_signal_net_does_not_warn_about_rails(self):
        profile = registry.get_profile("rp2040")
        canonical = profile.create_canonical_pinmap({"LED_DATA": ["GP5"]})
        self.assertFalse(
            any(
                "power/ground rail" in w
                for w in canonical["metadata"]["validation_warnings"]
            )
        )


class TestOutputSelectionFlags(unittest.TestCase):
    """--no-micropython / --no-arduino / --no-markdown skip files (P2.8)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _run_cli(self, *extra_args: str) -> subprocess.CompletedProcess:
        csv_path = Path(self.temp_dir) / "netlist.csv"
        csv_path.write_text(
            "Net,Pin,Component,RefDes\nLED,GP5,RP2040,U1\n",
            encoding="utf-8",
        )
        return subprocess.run(
            [
                sys.executable, "-m", "tools.pinmapgen.cli",
                "--csv", str(csv_path), "--mcu", "rp2040",
                "--mcu-ref", "U1", "--out-root", self.temp_dir,
                *extra_args,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def _out(self, rel: str) -> Path:
        return Path(self.temp_dir) / rel

    def test_default_run_writes_all_formats(self):
        result = self._run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self._out("pinmaps/pinmap.json").exists())
        self.assertTrue(
            self._out("firmware/micropython/pinmap_micropython.py").exists()
        )
        self.assertTrue(
            self._out("firmware/include/pinmap_arduino.h").exists()
        )
        self.assertTrue(self._out("firmware/docs/PINOUT.md").exists())

    def test_no_flags_skip_their_formats(self):
        result = self._run_cli(
            "--no-micropython", "--no-arduino", "--no-markdown"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # JSON is the canonical output and is always written.
        self.assertTrue(self._out("pinmaps/pinmap.json").exists())
        self.assertFalse(
            self._out("firmware/micropython/pinmap_micropython.py").exists()
        )
        self.assertFalse(
            self._out("firmware/include/pinmap_arduino.h").exists()
        )
        self.assertFalse(self._out("firmware/docs/PINOUT.md").exists())

    def test_single_skip_leaves_the_rest(self):
        result = self._run_cli("--no-markdown")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            self._out("firmware/micropython/pinmap_micropython.py").exists()
        )
        self.assertTrue(
            self._out("firmware/include/pinmap_arduino.h").exists()
        )
        self.assertFalse(self._out("firmware/docs/PINOUT.md").exists())


class TestMarkdownFunctionColumn(unittest.TestCase):
    """PINOUT's Function column describes the net's role (P2.6)."""

    def test_function_column_uses_role_description(self):
        canonical = {
            "mcu": "rp2040",
            "pins": {"I2C0_SDA": ["GP4"]},
            "differential_pairs": [],
            "metadata": {},
        }
        table = generate_single_ended_table(canonical)
        self.assertIn("I2C Serial Data", table)

    def test_special_function_moves_to_notes(self):
        """The pin's own quirk stays visible, now in the Notes column."""
        profile = registry.get_profile("esp32")
        canonical = profile.create_canonical_pinmap(
            {"PHOTO_SENSE": ["GPIO34"]}
        )
        table = generate_single_ended_table(canonical)
        row = next(
            line for line in table.splitlines() if "PHOTO_SENSE" in line
        )
        self.assertIn("Input Only", row)


if __name__ == "__main__":
    unittest.main()
