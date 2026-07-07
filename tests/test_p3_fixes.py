"""Regression tests for the P3 polish fixes.

Covers:
- Shared net-name sanitizer preserves differential polarity markers
  (USB_D+/USB_D- become USB_D_P/USB_D_N instead of USB_D/USB_D_2).
- The MCU reference designator is recorded in pinmap.json.
- --list-mcus and 'profiles list' share one table printer.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.pinmapgen.emit_arduino import (
    _sanitize_net_name as arduino_sanitize,
)
from tools.pinmapgen.emit_micropython import (
    _sanitize_net_name as micropython_sanitize,
)
from tools.pinmapgen.emit_micropython import (
    generate_micropython_with_roles,
)
from tools.pinmapgen.naming import sanitize_net_name


class TestPolaritySuffixes(unittest.TestCase):
    """Trailing +/- must become _P/_N instead of vanishing."""

    def test_plus_becomes_p(self):
        self.assertEqual(sanitize_net_name("USB_D+"), "USB_D_P")

    def test_minus_becomes_n(self):
        self.assertEqual(sanitize_net_name("USB_D-"), "USB_D_N")

    def test_pair_no_longer_collides(self):
        seen: dict[str, int] = {}
        pos = sanitize_net_name("USB_D+", seen)
        neg = sanitize_net_name("USB_D-", seen)
        self.assertEqual(pos, "USB_D_P")
        self.assertEqual(neg, "USB_D_N")
        self.assertNotIn("_2", neg)

    def test_emitters_share_the_implementation(self):
        self.assertEqual(arduino_sanitize("VBUS-"), "VBUS_N")
        self.assertEqual(micropython_sanitize("VBUS+"), "VBUS_P")

    def test_interior_minus_still_underscore(self):
        # '-' mid-name is a separator, not polarity.
        self.assertEqual(sanitize_net_name("LED-RED"), "LED_RED")

    def test_generated_module_uses_polarity_names(self):
        cd = {
            "mcu": "rp2040",
            "pins": {"USB_D+": ["GP25"], "USB_D-": ["GP24"]},
            "differential_pairs": [],
            "metadata": {},
        }
        code = generate_micropython_with_roles(cd)
        self.assertIn("USB_D_P = 25", code)
        self.assertIn("USB_D_N = 24", code)


class TestMcuRefRecorded(unittest.TestCase):
    """pinmap.json must carry the MCU reference designator."""

    def test_json_contains_mcu_ref(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "netlist.csv"
            csv_path.write_text(
                "Net,Pin,Component,RefDes\nLED,GP4,RP2040,U7\n",
                encoding="utf-8",
            )
            out_root = Path(tmpdir) / "out"
            result = subprocess.run(
                [
                    sys.executable, "-m", "tools.pinmapgen.cli",
                    "--csv", str(csv_path),
                    "--mcu", "rp2040",
                    "--mcu-ref", "U7",
                    "--out-root", str(out_root),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(
                (out_root / "pinmaps" / "pinmap.json").read_text(
                    encoding="utf-8"
                )
            )
        self.assertEqual(data.get("mcu_ref"), "U7")


class TestUnifiedProfileList(unittest.TestCase):
    """--list-mcus and 'profiles list' print the same table."""

    def _run(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "tools.pinmapgen.cli", *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_both_commands_show_schema_column(self):
        for args in (["--list-mcus"], ["profiles", "list"]):
            result = self._run(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Schema", result.stdout)
            self.assertIn("rp2040", result.stdout)


if __name__ == "__main__":
    unittest.main()
