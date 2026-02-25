"""
Regression tests for bug fixes #35-#44.

Each test class targets a specific GitHub issue to prevent regressions.
"""

import io
import os
import shutil
import tempfile
import unittest

from tools.pinmapgen.bom_csv import extract_nets, parse_csv
from tools.pinmapgen.emit_arduino import _sanitize_net_name as arduino_sanitize
from tools.pinmapgen.emit_micropython import (
    _sanitize_net_name as micropython_sanitize,
)
from tools.pinmapgen.mcu_profiles import PinCapability
from tools.pinmapgen.roles import PinRole, RoleInferencer
from tools.pinmapgen.rp2040_profile import RP2040Profile


class TestIssue35BomEncoding(unittest.TestCase):
    """#35: UTF-8 BOM CSV files should parse without error."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_utf8_bom_csv(self):
        """CSV saved with UTF-8 BOM (\\xef\\xbb\\xbf) must parse correctly."""
        csv_path = os.path.join(self.temp_dir, "bom.csv")
        with open(csv_path, "wb") as f:
            # Write BOM then content
            f.write(b"\xef\xbb\xbf")
            f.write(b"Net,Pin,Component,RefDes\n")
            f.write(b"LED,GP15,RP2040,U1\n")

        csv_data = parse_csv(csv_path)
        result = extract_nets(csv_data, "U1")
        self.assertIn("LED", result)
        self.assertEqual(result["LED"], ["GP15"])

    def test_utf8_no_bom_still_works(self):
        """Regular UTF-8 CSV (no BOM) should still work."""
        csv_path = os.path.join(self.temp_dir, "plain.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("Net,Pin,Component,RefDes\nSDA,GP0,RP2040,U1\n")

        csv_data = parse_csv(csv_path)
        result = extract_nets(csv_data, "U1")
        self.assertIn("SDA", result)


class TestIssue36SanitizeLeadingDigits(unittest.TestCase):
    """#36: _sanitize_net_name must not strip leading digits from power nets."""

    def test_3v3_preserved_arduino(self):
        self.assertEqual(arduino_sanitize("3V3"), "_3V3")

    def test_5v_preserved_arduino(self):
        self.assertEqual(arduino_sanitize("5V"), "_5V")

    def test_3v3_preserved_micropython(self):
        self.assertEqual(micropython_sanitize("3V3"), "_3V3")

    def test_5v_preserved_micropython(self):
        self.assertEqual(micropython_sanitize("5V"), "_5V")

    def test_normal_name_unchanged(self):
        self.assertEqual(arduino_sanitize("LED_STATUS"), "LED_STATUS")
        self.assertEqual(micropython_sanitize("I2C_SDA"), "I2C_SDA")


class TestIssue37SpiTxClassification(unittest.TestCase):
    """#37: SPI_TX should be classified as SPI_MOSI, not UART_TX."""

    def setUp(self):
        self.inferencer = RoleInferencer()

    def test_spi_tx_is_spi_mosi(self):
        result = self.inferencer.infer_role("SPI_TX")
        self.assertEqual(result, PinRole.SPI_MOSI)

    def test_spi_rx_is_spi_miso(self):
        result = self.inferencer.infer_role("SPI_RX")
        self.assertEqual(result, PinRole.SPI_MISO)

    def test_plain_tx_still_uart(self):
        """Bare 'TX' without SPI prefix should still be UART."""
        result = self.inferencer.infer_role("TX")
        self.assertEqual(result, PinRole.UART_TX)

    def test_uart_tx_still_uart(self):
        result = self.inferencer.infer_role("UART_TX")
        self.assertEqual(result, PinRole.UART_TX)


class TestIssue38DiffPairPolarity(unittest.TestCase):
    """#38: USB_DP should be positive, USB_DM should be negative."""

    def setUp(self):
        self.profile = RP2040Profile()

    def test_usb_dp_is_positive(self):
        nets = {
            "USB_DP": ["GP25"],
            "USB_DM": ["GP24"],
        }
        diff_pairs = self.profile.detect_differential_pairs(nets)
        self.assertEqual(len(diff_pairs), 1)
        pos_net, neg_net = diff_pairs[0]
        self.assertEqual(pos_net, "USB_DP")
        self.assertEqual(neg_net, "USB_DM")


class TestIssue39RoleToCapability(unittest.TestCase):
    """#39: _role_to_capability must map usb.dn, can.h, can.l."""

    def setUp(self):
        self.profile = RP2040Profile()

    def test_usb_dn_maps(self):
        result = self.profile._role_to_capability("usb.dn")
        self.assertEqual(result, PinCapability.USB_DM)

    def test_can_h_maps(self):
        result = self.profile._role_to_capability("can.h")
        self.assertEqual(result, PinCapability.CAN_TX)

    def test_can_l_maps(self):
        result = self.profile._role_to_capability("can.l")
        self.assertEqual(result, PinCapability.CAN_RX)

    def test_existing_mappings_intact(self):
        self.assertEqual(
            self.profile._role_to_capability("usb.dp"), PinCapability.USB_DP
        )
        self.assertEqual(
            self.profile._role_to_capability("usb.dm"), PinCapability.USB_DM
        )


class TestIssue40CollisionDetection(unittest.TestCase):
    """#40: Duplicate sanitized names get _2, _3 suffixes."""

    def test_arduino_collision_tracking(self):
        seen: dict[str, int] = {}
        first = arduino_sanitize("MY_NET", seen)
        second = arduino_sanitize("MY.NET", seen)
        self.assertEqual(first, "MY_NET")
        self.assertEqual(second, "MY_NET_2")

    def test_micropython_collision_tracking(self):
        seen: dict[str, int] = {}
        first = micropython_sanitize("MY_NET", seen)
        second = micropython_sanitize("MY-NET", seen)
        third = micropython_sanitize("MY.NET", seen)
        self.assertEqual(first, "MY_NET")
        self.assertEqual(second, "MY_NET_2")
        self.assertEqual(third, "MY_NET_3")

    def test_no_collision_without_tracker(self):
        """Without seen_names, no suffix is appended (backward compat)."""
        first = arduino_sanitize("MY_NET")
        second = arduino_sanitize("MY_NET")
        self.assertEqual(first, "MY_NET")
        self.assertEqual(second, "MY_NET")


class TestIssue41NoDoublePrinting(unittest.TestCase):
    """#41: Validation errors should not be printed twice."""

    def test_normalize_delegate_no_extra_print(self):
        """normalize.RP2040Profile.create_canonical_pinmap should not
        re-print validation errors already printed by the delegate."""
        import sys

        from tools.pinmapgen.normalize import RP2040Profile as LegacyProfile

        profile = LegacyProfile()
        nets = {"NET_A": ["GP0", "GP1"], "NET_B": ["GP0"]}  # GP0 duplicate

        # Capture stderr
        old_stderr = sys.stderr
        sys.stderr = captured = io.StringIO()
        try:
            profile.create_canonical_pinmap(nets)
        finally:
            sys.stderr = old_stderr

        output = captured.getvalue()
        # Count occurrences of each error — each should appear exactly once
        lines = [ln for ln in output.strip().splitlines() if "Validation" in ln]
        # No duplicate lines
        self.assertEqual(len(lines), len(set(lines)))


class TestIssue43DroppedPinTracking(unittest.TestCase):
    """#43: Invalid pins should be logged and tracked in metadata."""

    def setUp(self):
        self.profile = RP2040Profile()

    def test_dropped_pin_in_metadata(self):
        nets = {"LED": ["GP15", "INVALID_PIN_XYZ"]}
        canonical = self.profile.create_canonical_pinmap(nets)
        dropped = canonical["metadata"].get("dropped_pins", [])
        self.assertTrue(len(dropped) > 0)
        self.assertEqual(dropped[0]["pin"], "INVALID_PIN_XYZ")
        self.assertEqual(dropped[0]["net"], "LED")

    def test_valid_pins_not_dropped(self):
        nets = {"LED": ["GP15"]}
        canonical = self.profile.create_canonical_pinmap(nets)
        dropped = canonical["metadata"].get("dropped_pins", [])
        self.assertEqual(len(dropped), 0)


class TestIssue44SampleNetlistUSBPins(unittest.TestCase):
    """#44: sample_netlist.csv should have USB_DP→GP25 and USB_DN→GP24."""

    def test_usb_pin_assignment(self):
        csv_path = os.path.join("hardware", "exports", "sample_netlist.csv")
        csv_data = parse_csv(csv_path)
        result = extract_nets(csv_data, "U1")
        # Per RP2040 datasheet: GP25=USB D+, GP24=USB D-
        self.assertIn("USB_DP", result)
        self.assertIn("USB_DN", result)
        self.assertIn("GP25", result["USB_DP"])
        self.assertIn("GP24", result["USB_DN"])


if __name__ == "__main__":
    unittest.main()
