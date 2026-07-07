"""Regression tests for issues #56-#60."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.pinmapgen.bom_csv import get_mcu_nets, parse_netlist_tuples
from tools.pinmapgen.emit_markdown import generate_differential_pairs_table
from tools.pinmapgen.emit_micropython import generate_micropython_with_roles
from tools.pinmapgen.profile_registry import ProfileRegistry
from tools.pinmapgen.watch import watch_and_regenerate

_registry = ProfileRegistry()


def RP2040Profile():  # noqa: N802 — keeps historical test call sites readable
    return _registry.get_profile("rp2040")


class TestIssue56MicroPythonImports(unittest.TestCase):
    """#56 — Numbered bus groups must still import required machine classes."""

    def test_i2c_numbered_group_imports_i2c(self):
        canonical = {
            "mcu": "rp2040",
            "pins": {
                "I2C0_SDA": ["GP0"],
                "I2C0_SCL": ["GP1"],
            },
            "differential_pairs": [],
            "metadata": {},
        }

        code = generate_micropython_with_roles(canonical)

        self.assertIn("from machine import Pin, I2C", code)
        self.assertIn("def setup_i2c0", code)


class TestIssue57MarkdownDiffSafety(unittest.TestCase):
    """#57 — Differential pair table generation must tolerate empty pin lists."""

    def test_empty_diff_pin_list_does_not_crash(self):
        canonical = {
            "mcu": "rp2040",
            "pins": {
                "USB_DP": [],
                "USB_DN": ["GP24"],
            },
            "differential_pairs": [{"positive": "USB_DP", "negative": "USB_DN"}],
            "metadata": {},
        }

        table = generate_differential_pairs_table(canonical)

        self.assertIn("| Signal | Positive Pin | Negative Pin | Function | Notes |", table)
        self.assertIn("USB", table)
        self.assertIn("GP24", table)


class TestIssue58RefDesMatching(unittest.TestCase):
    """#58 — MCU ref matching should be case-insensitive and fail fast when absent."""

    def test_case_insensitive_refdes_matching(self):
        csv_content = """Net,Pin,Component,RefDes
LED,GP15,RP2040,U1
I2C_SDA,GP0,RP2040,U1
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "netlist.csv"
            csv_path.write_text(csv_content, encoding="utf-8")

            tuples = parse_netlist_tuples(csv_path, "u1")
            nets = get_mcu_nets(csv_path, "u1")

            self.assertEqual(len(tuples), 2)
            self.assertEqual(len(nets), 2)
            self.assertIn("LED", nets)

    def test_get_mcu_nets_raises_when_ref_missing(self):
        csv_content = """Net,Pin,Component,RefDes
LED,GP15,RP2040,U2
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "netlist.csv"
            csv_path.write_text(csv_content, encoding="utf-8")

            with self.assertRaises(ValueError):
                get_mcu_nets(csv_path, "U1")


class TestIssue59DiffPairCaseSensitivity(unittest.TestCase):
    """#59 — Differential pair detection should work regardless of net-name casing."""

    def test_lowercase_usb_diff_pair_detected(self):
        profile = RP2040Profile()
        pairs = profile.detect_differential_pairs(
            {
                "usb_dp": ["GP25"],
                "usb_dm": ["GP24"],
            }
        )

        self.assertEqual(pairs, [("usb_dp", "usb_dm")])


class TestIssue60WatchRecursiveStartup(unittest.TestCase):
    """#60 — Watch startup file discovery must match recursive runtime behavior."""

    def test_nested_csv_detected_on_startup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "nested"
            nested.mkdir(parents=True, exist_ok=True)
            (nested / "board.csv").write_text(
                "Net,Pin,Component,RefDes\nLED,GP4,RP2040,U1\n",
                encoding="utf-8",
            )

            with patch("tools.pinmapgen.watch.SimpleFileWatcher.start") as start_mock:
                watch_and_regenerate(tmpdir, poll_interval=0.01)

            start_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
