"""
Tests for the P1.4 audit fix: forgiving, well-explained CSV parsing.

Headers match case-insensitively with common aliases, the delimiter is
sniffed, Component is optional, ragged rows are skipped with a warning
instead of crashing, and error messages say what was actually found.
"""

import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.pinmapgen.bom_csv import get_mcu_nets, parse_csv


class TestForgivingHeaders(unittest.TestCase):
    """Header matching: case, aliases, optional Component."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _write(self, content: str) -> Path:
        path = Path(self.temp_dir) / "netlist.csv"
        path.write_text(content, encoding="utf-8")
        return path

    def test_lowercase_headers(self):
        path = self._write("net,pin,component,refdes\nLED,GP5,RP2040,U1\n")
        self.assertEqual(get_mcu_nets(path, "U1"), {"LED": ["GP5"]})

    def test_designator_and_net_name_aliases(self):
        path = self._write(
            "Net Name,Pin Name,Part,Designator\nLED,GP5,RP2040,U1\n"
        )
        self.assertEqual(get_mcu_nets(path, "U1"), {"LED": ["GP5"]})

    def test_component_column_is_optional(self):
        path = self._write("Net,Pin,RefDes\nLED,GP5,U1\n")
        rows = parse_csv(path)
        self.assertEqual(rows[0]["Component"], "")
        self.assertEqual(get_mcu_nets(path, "U1"), {"LED": ["GP5"]})

    def test_empty_component_rows_are_kept(self):
        """Rows are no longer dropped just because Component is blank."""
        path = self._write(
            "Net,Pin,Component,RefDes\nLED,GP5,,U1\nBTN,GP6,RP2040,U1\n"
        )
        self.assertEqual(
            get_mcu_nets(path, "U1"), {"LED": ["GP5"], "BTN": ["GP6"]}
        )

    def test_missing_columns_message_lists_found_headers(self):
        path = self._write("Foo,Bar\n1,2\n")
        with self.assertRaises(ValueError) as ctx:
            parse_csv(path)
        message = str(ctx.exception)
        self.assertIn("missing required column(s)", message)
        self.assertIn("Found columns: Foo, Bar", message)
        self.assertIn("case-insensitively", message)


class TestDelimiterSniffing(unittest.TestCase):
    """Semicolon (European Excel) and tab delimiters are detected."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _write(self, content: str) -> Path:
        path = Path(self.temp_dir) / "netlist.csv"
        path.write_text(content, encoding="utf-8")
        return path

    def test_semicolon_delimited(self):
        path = self._write("Net;Pin;RefDes\nLED;GP5;U1\n")
        self.assertEqual(get_mcu_nets(path, "U1"), {"LED": ["GP5"]})

    def test_tab_delimited(self):
        path = self._write("Net\tPin\tRefDes\nLED\tGP5\tU1\n")
        self.assertEqual(get_mcu_nets(path, "U1"), {"LED": ["GP5"]})


class TestRaggedRows(unittest.TestCase):
    """Malformed rows are skipped with a pointer, never a stack trace."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _write(self, content: str) -> Path:
        path = Path(self.temp_dir) / "netlist.csv"
        path.write_text(content, encoding="utf-8")
        return path

    def test_row_with_unquoted_comma_is_skipped_not_fatal(self):
        path = self._write(
            "Net,Pin,Component,RefDes\n"
            "LED,GP5,RP2040,U1\n"
            "BAD,GP6,10k, 1%,U1\n"   # unquoted comma shifts the fields
            "BTN,GP7,RP2040,U1\n"
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            nets = get_mcu_nets(path, "U1")
        # The good rows survive; the bad row is named with its line number.
        self.assertEqual(nets, {"LED": ["GP5"], "BTN": ["GP7"]})
        self.assertIn("line 3", stderr.getvalue())
        self.assertIn("more fields than the header", stderr.getvalue())

    def test_trailing_comma_is_tolerated(self):
        """An empty overflow cell (plain trailing comma) is harmless."""
        path = self._write("Net,Pin,Component,RefDes\nLED,GP5,RP2040,U1,\n")
        self.assertEqual(get_mcu_nets(path, "U1"), {"LED": ["GP5"]})


class TestNotFoundMessages(unittest.TestCase):
    """A wrong --mcu-ref names the references that do exist."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_available_refs_are_listed(self):
        path = Path(self.temp_dir) / "netlist.csv"
        path.write_text(
            "Net,Pin,Component,RefDes\n"
            "LED,GP5,RP2040,U1\nBTN,1,SW,SW1\n",
            encoding="utf-8",
        )
        with self.assertRaises(ValueError) as ctx:
            get_mcu_nets(path, "U9")
        message = str(ctx.exception)
        self.assertIn("No entries found for MCU reference 'U9'", message)
        self.assertIn("SW1", message)
        self.assertIn("U1", message)

    def test_encoding_error_names_the_fix(self):
        path = Path(self.temp_dir) / "netlist.csv"
        path.write_bytes("Net,Pin,RefDes\nLED,GP5,U1\n".encode("utf-16"))
        with self.assertRaises(ValueError) as ctx:
            parse_csv(path)
        self.assertIn("UTF-8", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
