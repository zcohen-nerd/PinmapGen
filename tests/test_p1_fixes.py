"""Regression tests for the P1 audit fixes.

Covers:
- emit_json no longer mutates the caller's canonical dict (emitter output
  must not depend on emitter order).
- CLI --strict exits non-zero on validation errors / dropped pins.
- watch.py accepts all registry profiles, not a hardcoded subset.
- Multi-pin nets are flagged in MicroPython/Arduino constant comments.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.pinmapgen import emit_json
from tools.pinmapgen.emit_arduino import generate_arduino_with_roles
from tools.pinmapgen.emit_micropython import generate_micropython_with_roles
from tools.pinmapgen.profile_registry import ProfileRegistry


class TestEmitJsonDoesNotMutate(unittest.TestCase):
    """emit_json must not append role-derived pairs to the shared dict."""

    def test_canonical_dict_unchanged_after_emit(self):
        profile = ProfileRegistry().get_profile("rp2040")
        # "USB_D+"/"USB_D-" is missed by the canonical regex patterns but
        # found by role analysis, so emit_json wants to add a pair.
        nets = {"USB_D+": ["GP25"], "USB_D-": ["GP24"], "LED": ["GP5"]}
        canonical = profile.create_canonical_pinmap(nets)
        pairs_before = [dict(p) for p in canonical["differential_pairs"]]

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "pinmap.json"
            emit_json.emit_json(canonical, out_path)
            written = json.loads(out_path.read_text(encoding="utf-8"))

        # The caller's dict is untouched…
        self.assertEqual(canonical["differential_pairs"], pairs_before)
        # …while the JSON output still contains the role-derived pair.
        written_pairs = {
            (p["positive"], p["negative"])
            for p in written["differential_pairs"]
        }
        self.assertIn(("USB_D+", "USB_D-"), written_pairs)


class TestStrictExitCode(unittest.TestCase):
    """--strict must fail the CLI on validation errors or dropped pins."""

    def _run_cli(self, csv_content, *extra_args):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "netlist.csv"
            csv_path.write_text(csv_content, encoding="utf-8")
            out_root = Path(tmpdir) / "out"
            result = subprocess.run(
                [
                    sys.executable, "-m", "tools.pinmapgen.cli",
                    "--csv", str(csv_path),
                    "--mcu", "rp2040",
                    "--mcu-ref", "U1",
                    "--out-root", str(out_root),
                    *extra_args,
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            json_written = (out_root / "pinmaps" / "pinmap.json").exists()
        return result, json_written

    def test_duplicate_pin_fails_strict(self):
        csv = (
            "Component,RefDes,Pin,Net\n"
            "RP2040,U1,GP4,SIG_A\n"
            "RP2040,U1,GP4,SIG_B\n"
        )
        result, json_written = self._run_cli(csv, "--strict")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Strict mode", result.stderr)
        self.assertFalse(json_written, "no output should be written")

    def test_dropped_pin_fails_strict(self):
        csv = (
            "Component,RefDes,Pin,Net\n"
            "RP2040,U1,NOT_A_PIN_99,MYSTERY\n"
            "RP2040,U1,GP4,LED\n"
        )
        result, json_written = self._run_cli(csv, "--strict")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(json_written)

    def test_duplicate_pin_passes_without_strict(self):
        csv = (
            "Component,RefDes,Pin,Net\n"
            "RP2040,U1,GP4,SIG_A\n"
            "RP2040,U1,GP4,SIG_B\n"
        )
        result, json_written = self._run_cli(csv)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json_written)

    def test_clean_netlist_passes_strict(self):
        csv = (
            "Component,RefDes,Pin,Net\n"
            "RP2040,U1,GP4,LED\n"
            "RP2040,U1,GP5,BUTTON\n"
        )
        result, json_written = self._run_cli(csv, "--strict")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json_written)


class TestWatchRegistryMcus(unittest.TestCase):
    """watch.py must accept every registered profile."""

    def test_help_lists_registry_profiles(self):
        result = subprocess.run(
            [sys.executable, "-m", "tools.pinmapgen.watch", "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        # Profiles beyond the old hardcoded trio must be usable.
        for mcu in ("esp32s3", "nrf52840", "atsamd21"):
            self.assertIn(mcu, result.stdout)
        self.assertIn("--profile-dir", result.stdout)


class TestMultiPinAnnotations(unittest.TestCase):
    """Multi-pin nets must be flagged in generated code comments."""

    @staticmethod
    def _canonical(mcu, pins):
        return {
            "mcu": mcu,
            "pins": pins,
            "differential_pairs": [],
            "metadata": {
                "total_nets": len(pins),
                "total_pins": sum(len(v) for v in pins.values()),
                "differential_pairs_count": 0,
                "special_pins_used": [],
                "validation_warnings": [],
                "validation_errors": [],
            },
        }

    def test_micropython_flags_multi_pin_net(self):
        cd = self._canonical(
            "esp32", {"I2C_SDA": ["GPIO4", "GPIO21"], "LED": ["GPIO5"]}
        )
        code = generate_micropython_with_roles(cd)
        self.assertIn("net also connects to GPIO21", code)
        # Single-pin nets are not flagged.
        for line in code.splitlines():
            if line.startswith("LED ="):
                self.assertNotIn("also connects", line)

    def test_arduino_flags_multi_pin_net(self):
        cd = self._canonical(
            "esp32", {"I2C_SDA": ["GPIO4", "GPIO21"], "LED": ["GPIO5"]}
        )
        header = generate_arduino_with_roles(cd)
        self.assertIn("net also connects to GPIO21", header)


if __name__ == "__main__":
    unittest.main()
