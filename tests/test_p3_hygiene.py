"""
Tests for the P3 hygiene batch: output determinism, Mermaid robustness,
Arduino header details, watcher hardening, registry edges, and the
SOURCE_DATE_EPOCH guard.

Covers audit items P3.9 (determinism), P3.10 (Mermaid), P3.11 (Arduino
guard/pair types), P3.12 (watch.py), P3.13 (profile registry), and
P3.14 (environment guard).
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from tools.pinmapgen.emit_arduino import generate_arduino_with_roles
from tools.pinmapgen.emit_mermaid import generate_mermaid_graph
from tools.pinmapgen.emit_micropython import emit_micropython
from tools.pinmapgen.profile_registry import ProfileRegistry, registry
from tools.pinmapgen.watch import SimpleFileWatcher


class TestDeterminism(unittest.TestCase):
    """P3.9 - same input data, same bytes, whatever the row order."""

    def test_special_pins_sorted_and_stable(self):
        profile = registry.get_profile("esp32")
        forward = profile.create_canonical_pinmap(
            {"BOOT": ["GPIO0"], "SENSE": ["GPIO34"], "STRAP": ["GPIO12"]}
        )
        backward = profile.create_canonical_pinmap(
            {"STRAP": ["GPIO12"], "SENSE": ["GPIO34"], "BOOT": ["GPIO0"]}
        )
        self.assertEqual(
            forward["metadata"]["special_pins_used"],
            backward["metadata"]["special_pins_used"],
        )
        self.assertEqual(
            forward["metadata"]["special_pins_used"],
            ["GPIO0", "GPIO12", "GPIO34"],
        )

    def test_emitted_file_has_unix_newlines(self):
        """Emitters write LF regardless of platform (newline="\\n")."""
        canonical = {
            "mcu": "rp2040",
            "pins": {"LED": ["GP5"]},
            "differential_pairs": [],
            "metadata": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pinmap_micropython.py"
            emit_micropython(canonical, out)
            raw = out.read_bytes()
        self.assertNotIn(b"\r", raw)

    def test_text_outputs_share_one_timestamp_format(self):
        """All text headers carry the same 'YYYY-... UTC' stamp."""
        os.environ["SOURCE_DATE_EPOCH"] = "0"
        try:
            canonical = {
                "mcu": "rp2040",
                "pins": {"LED": ["GP5"]},
                "differential_pairs": [],
                "metadata": {},
            }
            from tools.pinmapgen.emit_markdown import (
                generate_pinout_documentation,
            )
            from tools.pinmapgen.emit_micropython import (
                generate_micropython_with_roles,
            )

            stamp = "1970-01-01 00:00:00 UTC"
            self.assertIn(stamp, generate_micropython_with_roles(canonical))
            self.assertIn(stamp, generate_arduino_with_roles(canonical))
            self.assertIn(stamp, generate_pinout_documentation(canonical))
            self.assertIn(stamp, generate_mermaid_graph(canonical))
        finally:
            del os.environ["SOURCE_DATE_EPOCH"]


class TestSourceDateEpochGuard(unittest.TestCase):
    """P3.14 - a garbage SOURCE_DATE_EPOCH must not crash the run."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        csv_path = Path(self.temp_dir) / "netlist.csv"
        csv_path.write_text(
            "Net,Pin,Component,RefDes\nLED,GP5,RP2040,U1\n",
            encoding="utf-8",
        )
        self.csv_path = csv_path

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _run(self, *extra: str) -> subprocess.CompletedProcess:
        env = dict(os.environ, SOURCE_DATE_EPOCH="not-a-number")
        return subprocess.run(
            [
                sys.executable, "-m", "tools.pinmapgen.cli",
                "--csv", str(self.csv_path), "--mcu", "rp2040",
                "--mcu-ref", "U1", "--out-root", self.temp_dir, *extra,
            ],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_garbage_value_warns_and_continues(self):
        result = self._run()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("invalid SOURCE_DATE_EPOCH", result.stderr)

    def test_reproducible_repairs_garbage_value(self):
        result = self._run("--reproducible")
        self.assertEqual(result.returncode, 0, result.stderr)
        # The value was replaced with 0, so nothing needed a warning and
        # the output carries the epoch timestamp.
        self.assertNotIn("invalid SOURCE_DATE_EPOCH", result.stderr)
        content = (
            Path(self.temp_dir)
            / "firmware" / "micropython" / "pinmap_micropython.py"
        ).read_text(encoding="utf-8")
        self.assertIn("1970-01-01 00:00:00 UTC", content)


class TestMermaidRobustness(unittest.TestCase):
    """P3.10 - hostile net names and honest multi-pin styling."""

    def _canonical(self, pins, pairs=None):
        return {
            "mcu": "rp2040",
            "pins": pins,
            "differential_pairs": pairs or [],
            "metadata": {},
        }

    def test_quote_in_net_name_is_escaped(self):
        diagram = generate_mermaid_graph(
            self._canonical({'SENSE"A': ["GP5"]})
        )
        self.assertIn("#quot;", diagram)
        self.assertNotIn('["SENSE"A', diagram)

    def test_angle_brackets_escaped(self):
        diagram = generate_mermaid_graph(
            self._canonical({"NET<1>": ["GP5"]})
        )
        self.assertIn("#lt;1#gt;", diagram)

    def test_multi_pin_sensor_bus_is_not_styled_power(self):
        diagram = generate_mermaid_graph(
            self._canonical({"SENSOR_BUS": ["GP8", "GP9"]})
        )
        row = next(
            line for line in diagram.splitlines()
            if line.strip().startswith("class SENSOR_BUS")
        )
        self.assertNotIn("power", row)

    def test_multi_pin_rail_keeps_power_style(self):
        diagram = generate_mermaid_graph(
            self._canonical({"VCC_3V3": ["GP8", "GP9"]})
        )
        self.assertIn("class VCC_3V3 power", diagram)

    def test_polarity_pairs_get_distinct_readable_ids(self):
        diagram = generate_mermaid_graph(
            self._canonical(
                {"USB_D+": ["GP15"], "USB_D-": ["GP16"]},
                pairs=[{"positive": "USB_D+", "negative": "USB_D-"}],
            )
        )
        self.assertIn("USB_D_P", diagram)
        self.assertIn("USB_D_N", diagram)


class TestArduinoHeaderDetails(unittest.TestCase):
    """P3.11 - include guards and pair member types."""

    def _canonical(self, mcu="rp2040", ref="U1", pins=None, pairs=None):
        return {
            "mcu": mcu,
            "mcu_ref": ref,
            "pins": pins or {"LED": ["GP5"]},
            "differential_pairs": pairs or [],
            "metadata": {},
        }

    def test_guard_embeds_mcu_and_ref(self):
        header = generate_arduino_with_roles(self._canonical())
        self.assertIn("#ifndef PINMAP_ARDUINO_RP2040_U1_H", header)

    def test_two_pinmaps_get_distinct_guards(self):
        a = generate_arduino_with_roles(self._canonical(ref="U1"))
        b = generate_arduino_with_roles(self._canonical(ref="U2"))
        guard_a = next(line for line in a.splitlines() if "#ifndef" in line)
        guard_b = next(line for line in b.splitlines() if "#ifndef" in line)
        self.assertNotEqual(guard_a, guard_b)

    def test_pair_members_use_constexpr_auto(self):
        header = generate_arduino_with_roles(
            self._canonical(
                pins={"USB_DP": ["GP15"], "USB_DN": ["GP16"]},
                pairs=[{"positive": "USB_DP", "negative": "USB_DN"}],
            )
        )
        self.assertIn("static constexpr auto DP", header)
        self.assertNotIn("constexpr uint8_t", header)


class TestWatcherHardening(unittest.TestCase):
    """P3.12 - interval validation and write debounce."""

    def test_zero_or_negative_interval_rejected(self):
        with self.assertRaises(ValueError):
            SimpleFileWatcher(set(), lambda p: None, poll_interval=0)
        with self.assertRaises(ValueError):
            SimpleFileWatcher(set(), lambda p: None, poll_interval=-1)

    def test_change_reported_only_after_settling(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "netlist.csv"
            target.write_text("a\n", encoding="utf-8")
            watcher = SimpleFileWatcher(
                {target}, lambda p: None, poll_interval=0.05
            )

            # Modify the file: the first poll must hold it back...
            time.sleep(0.02)
            target.write_text("b\n", encoding="utf-8")
            self.assertEqual(watcher._check_for_changes(), set())
            # ...and the next poll (mtime unchanged) reports it.
            self.assertEqual(watcher._check_for_changes(), {target})
            # Once reported, quiet polls stay quiet.
            self.assertEqual(watcher._check_for_changes(), set())

    def test_file_still_being_written_stays_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "netlist.csv"
            target.write_text("a\n", encoding="utf-8")
            watcher = SimpleFileWatcher(
                {target}, lambda p: None, poll_interval=0.05
            )

            time.sleep(0.02)
            target.write_text("b\n", encoding="utf-8")
            self.assertEqual(watcher._check_for_changes(), set())
            # Another write before the settle poll: still pending.
            time.sleep(0.02)
            target.write_text("c\n", encoding="utf-8")
            self.assertEqual(watcher._check_for_changes(), set())
            self.assertEqual(watcher._check_for_changes(), {target})


class TestRegistryEdges(unittest.TestCase):
    """P3.13 - malformed TOML errors name the file; instances cached."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.bad = Path(self.temp_dir) / "broken.toml"
        self.bad.write_text("[profile\nname = oops", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_malformed_toml_error_names_the_file(self):
        reg = ProfileRegistry(discover_builtins=False)
        reg.add_profile_dir(self.temp_dir)
        with self.assertRaises(ValueError) as ctx:
            reg.get_profile("broken")
        self.assertIn("broken.toml", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx2:
            reg.get_profile_info("broken")
        self.assertIn("broken.toml", str(ctx2.exception))

    def test_list_mcus_survives_broken_profile(self):
        result = subprocess.run(
            [
                sys.executable, "-m", "tools.pinmapgen.cli",
                "--list-mcus", "--profile-dir", self.temp_dir,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("[BROKEN]", result.stdout)
        self.assertIn("broken.toml", result.stdout)
        # The healthy built-ins are still listed.
        self.assertIn("rp2040", result.stdout)
        self.assertIn("atsamd51", result.stdout)

    def test_profiles_are_cached(self):
        reg = ProfileRegistry()
        self.assertIs(reg.get_profile("rp2040"), reg.get_profile("rp2040"))

    def test_profile_dir_accepted_after_subcommand(self):
        """`profiles check <name> --profile-dir DIR` (documented order)."""
        result = subprocess.run(
            [
                sys.executable, "-m", "tools.pinmapgen.cli",
                "profiles", "check", "rp2040",
                "--profile-dir", self.temp_dir,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
