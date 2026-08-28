"""
Tests for result visibility: warning printing, the honest final status
line, and the --log-file mirror used by the Fusion ULP.

These cover the P0.2 audit fix: validation warnings used to be collected
into metadata but never printed, and the CLI reported bare success even
when the run had validation errors or dropped pins.
"""

import contextlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.pinmapgen.cli import _install_log_tee, _remove_log_tee
from tools.pinmapgen.profile_registry import registry


class TestWarningPrinting(unittest.TestCase):
    """Per-pin profile warnings must reach stderr, once each."""

    def test_special_pin_warnings_printed(self):
        """A net on a special pin prints that pin's advisory warning."""
        profile = registry.get_profile("esp32")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = profile.create_canonical_pinmap({"BOOT_BTN": ["GPIO0"]})

        output = stderr.getvalue()
        self.assertIn("Warning: GPIO0 is a boot strapping pin", output)
        self.assertIn(
            "GPIO0 is a boot strapping pin",
            result["metadata"]["validation_warnings"],
        )

    def test_duplicate_warnings_printed_once(self):
        """The same pin warning is not repeated for every net touching it."""
        profile = registry.get_profile("esp32")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = profile.create_canonical_pinmap(
                {"NET_A": ["GPIO0"], "NET_B": ["GPIO0"]}
            )

        output = stderr.getvalue()
        self.assertEqual(output.count("GPIO0 is a boot strapping pin"), 1)
        # Metadata is deduplicated too, so counts match what was printed.
        warnings = result["metadata"]["validation_warnings"]
        self.assertEqual(
            len([w for w in warnings if "boot strapping" in w]), 1
        )


class TestFinalStatusLine(unittest.TestCase):
    """The CLI's last line must reflect errors/warnings/dropped pins."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _write_csv(self, body: str) -> str:
        csv_path = Path(self.temp_dir) / "netlist.csv"
        csv_path.write_text("Net,Pin,Component,RefDes\n" + body, encoding="utf-8")
        return str(csv_path)

    def _run_cli(self, *extra_args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "tools.pinmapgen.cli", *extra_args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_clean_run_reports_success(self):
        """A run with no issues keeps the plain success message."""
        csv_path = self._write_csv("LED,GP5,RP2040,U1\n")
        result = self._run_cli(
            "--csv", csv_path, "--mcu", "rp2040", "--mcu-ref", "U1",
            "--out-root", self.temp_dir,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Pinmap files generated successfully", result.stdout)
        self.assertNotIn("review the messages above", result.stdout)

    def test_issues_change_the_status_line(self):
        """Errors, dropped pins, and warnings all appear in the summary."""
        csv_path = self._write_csv(
            "A,GP5,RP2040,U1\n"   # conflicts with B -> validation error
            "B,GP5,RP2040,U1\n"
            "C,GP99,RP2040,U1\n"  # out of range -> dropped pin
            "SENSE,7,RP2040,U1\n"  # bare number -> interpretation warning
        )
        result = self._run_cli(
            "--csv", csv_path, "--mcu", "rp2040", "--mcu-ref", "U1",
            "--out-root", self.temp_dir,
        )
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("generated successfully", result.stdout)
        self.assertIn("1 validation error(s)", result.stdout)
        self.assertIn("1 dropped pin(s)", result.stdout)
        self.assertIn("1 warning(s)", result.stdout)
        self.assertIn("review the messages above", result.stdout)


class TestLogFile(unittest.TestCase):
    """--log-file mirrors everything the run printed, for the ULP."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_path = Path(self.temp_dir) / "pinmapgen_log.txt"

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _write_csv(self, body: str) -> str:
        csv_path = Path(self.temp_dir) / "netlist.csv"
        csv_path.write_text("Net,Pin,Component,RefDes\n" + body, encoding="utf-8")
        return str(csv_path)

    def _run_cli(self, *extra_args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "tools.pinmapgen.cli", *extra_args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_log_mirrors_warnings_and_status(self):
        """Warnings and the final status line land in the log file."""
        csv_path = self._write_csv("BOOT_BTN,GPIO0,ESP32,U1\n")
        result = self._run_cli(
            "--csv", csv_path, "--mcu", "esp32", "--mcu-ref", "U1",
            "--out-root", self.temp_dir,
            "--log-file", str(self.log_path),
        )
        self.assertEqual(result.returncode, 0)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("Warning: GPIO0 is a boot strapping pin", log_text)
        self.assertIn("warning(s)", log_text)
        # Console output is unchanged by the tee.
        self.assertIn("Warning: GPIO0 is a boot strapping pin", result.stderr)

    def test_log_captures_argument_errors(self):
        """Even argparse usage errors reach the log (exit before parse)."""
        csv_path = self._write_csv("LED,GP5,RP2040,U1\n")
        result = self._run_cli(
            "--csv", csv_path,  # --mcu deliberately missing
            "--log-file", str(self.log_path),
        )
        self.assertEqual(result.returncode, 2)
        log_text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("--mcu is required", log_text)

    def test_log_parent_directory_is_created(self):
        """A log path in a directory that doesn't exist yet still works."""
        nested_log = Path(self.temp_dir) / "deep" / "nested" / "log.txt"
        csv_path = self._write_csv("LED,GP5,RP2040,U1\n")
        result = self._run_cli(
            "--csv", csv_path, "--mcu", "rp2040", "--mcu-ref", "U1",
            "--out-root", self.temp_dir,
            "--log-file", str(nested_log),
        )
        self.assertEqual(result.returncode, 0)
        self.assertTrue(nested_log.exists())

    def test_tee_restores_streams(self):
        """After teardown, sys.stdout/sys.stderr are the real streams."""
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        handle = _install_log_tee(
            ["prog", "--log-file", str(self.log_path)]
        )
        self.assertIsNotNone(handle)
        try:
            print("tee active")
        finally:
            _remove_log_tee(handle)
        self.assertIs(sys.stdout, original_stdout)
        self.assertIs(sys.stderr, original_stderr)
        self.assertIn(
            "tee active", self.log_path.read_text(encoding="utf-8")
        )


if __name__ == "__main__":
    unittest.main()
