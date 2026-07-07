"""Regression tests for the post-audit code-review fixes.

Covers:
- nRF52840 MicroPython literals are flat Nordic pin numbers (the nrf port
  rejects dotted strings like "P0.13").
- Generated Arduino headers are pure ASCII, and nRF headers carry the raw
  Nordic numbering note.
- bom_csv caps per-row skip warnings instead of flooding stderr.
- The file watcher accepts a single file path.
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from tools.pinmapgen.bom_csv import parse_csv
from tools.pinmapgen.emit_arduino import generate_arduino_with_roles
from tools.pinmapgen.emit_micropython import (
    _micropython_pin_literal,
    generate_micropython_with_roles,
)
from tools.pinmapgen.watch import watch_and_regenerate


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


class TestNrfMicropythonLiterals(unittest.TestCase):
    """nrf port machine.Pin() accepts ints / "P13"-style names only."""

    def test_port0_flat_number(self):
        self.assertEqual(_micropython_pin_literal("P0_13"), "13")

    def test_port1_flat_number(self):
        self.assertEqual(_micropython_pin_literal("P1_02"), "34")

    def test_generated_module_uses_ints(self):
        cd = _canonical("nrf52840", {"LED": ["P0_13"], "SDA_PIN": ["P1_02"]})
        code = generate_micropython_with_roles(cd)
        self.assertIn("LED = 13", code)
        self.assertIn("SDA_PIN = 34", code)
        self.assertNotIn('"P0.13"', code)


class TestArduinoHeaderAscii(unittest.TestCase):
    """Generated C code must be pure ASCII."""

    def test_unmapped_pin_comment_is_ascii(self):
        cd = _canonical("atmega328p", {"XTAL_NET": ["PB6"], "LED": ["PB5"]})
        header = generate_arduino_with_roles(cd)
        self.assertTrue(header.isascii(), "non-ASCII character in header")
        self.assertIn("no Arduino pin mapping - replace manually", header)

    def test_nrf_header_notes_raw_nordic_numbering(self):
        cd = _canonical("nrf52840", {"LED": ["P0_13"]})
        header = generate_arduino_with_roles(cd)
        self.assertTrue(header.isascii())
        self.assertIn("raw Nordic pin numbers", header)

    def test_non_nrf_header_has_no_nordic_note(self):
        cd = _canonical("rp2040", {"LED": ["GP4"]})
        header = generate_arduino_with_roles(cd)
        self.assertNotIn("Nordic", header)


class TestCsvSkipWarningCap(unittest.TestCase):
    """Per-row skip warnings are capped with a summary line."""

    def test_warning_flood_is_capped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "netlist.csv"
            lines = ["Net,Pin,Component,RefDes", "LED,GP4,RP2040,U1"]
            lines += [f",{n},CONN,J1" for n in range(15)]  # 15 bad rows
            csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                rows = parse_csv(csv_path)

        self.assertEqual(len(rows), 1)
        warnings = stderr.getvalue().splitlines()
        per_row = [w for w in warnings if w.startswith("Warning: Skipping")]
        self.assertEqual(len(per_row), 10)
        self.assertTrue(
            any("5 more rows skipped (15 total)" in w for w in warnings),
            warnings,
        )


class TestWatchSingleFile(unittest.TestCase):
    """The watcher validates single-file paths."""

    def test_unsupported_file_type_returns_early(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            txt = Path(tmpdir) / "notes.txt"
            txt.write_text("not a netlist", encoding="utf-8")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                # Returns immediately instead of starting the polling loop.
                watch_and_regenerate(txt)

        self.assertIn("Unsupported file type", stdout.getvalue())

    def test_missing_path_returns_early(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            watch_and_regenerate(
                Path(tempfile.gettempdir()) / "does_not_exist_xyz"
            )
        self.assertIn("does not exist", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
