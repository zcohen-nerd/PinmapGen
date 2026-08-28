"""
Tests for the P0.1 / P1.1 audit fixes.

P0.1 — bare-number pins are ambiguous (logical GPIO number vs physical
package pad number). The profiles interpret them as GPIO numbers, and a
summary warning must say so. The ULP now also exports symbol pin names
plus an extra Pad column, which the CSV parser must tolerate.

P1.1 — profile data corrections: RP2040 USB is on dedicated pins (never
GP24/GP25), the STM32G071 has no FDCAN, and ESP32 GPIO37/38 are not
bonded on WROOM-32 modules.
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from tools.pinmapgen import bom_csv
from tools.pinmapgen.mcu_profiles import PinCapability
from tools.pinmapgen.profile_registry import registry


class TestBareNumberInterpretationWarning(unittest.TestCase):
    """P0.1: interpreting '2' as GP2 must be announced, once per run."""

    def test_bare_numbers_warn_and_still_normalize(self):
        profile = registry.get_profile("rp2040")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = profile.create_canonical_pinmap(
                {"LED": ["2"], "BUTTON": ["5"]}
            )

        # Interpretation is unchanged: bare numbers become GP names.
        self.assertEqual(result["pins"]["LED"], ["GP2"])
        self.assertEqual(result["pins"]["BUTTON"], ["GP5"])

        # One summary warning names the assumption and shows examples.
        warnings = result["metadata"]["validation_warnings"]
        numeric_warnings = [w for w in warnings if "bare numbers" in w]
        self.assertEqual(len(numeric_warnings), 1)
        self.assertIn("2 pin(s)", numeric_warnings[0])
        self.assertIn("'2' -> GP2", numeric_warnings[0])
        self.assertIn("pad numbers", numeric_warnings[0])
        self.assertIn("bare numbers", stderr.getvalue())

    def test_named_pins_do_not_warn(self):
        profile = registry.get_profile("rp2040")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = profile.create_canonical_pinmap(
                {"LED": ["GP2"], "SENSOR": ["GPIO5"]}
            )

        warnings = result["metadata"]["validation_warnings"]
        self.assertFalse([w for w in warnings if "bare numbers" in w])
        self.assertNotIn("bare numbers", stderr.getvalue())

    def test_pad_column_from_ulp_is_tolerated(self):
        """The ULP now exports an extra Pad column; the parser ignores it."""
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "netlist.csv"
            csv_path.write_text(
                '"RefDes","Pin","Component","Net","Pad"\n'
                '"U1","GP4","U1","LED","6"\n',
                encoding="utf-8",
            )
            nets = bom_csv.get_mcu_nets(csv_path, "U1")
        self.assertEqual(nets, {"LED": ["GP4"]})


class TestRP2040USBPinData(unittest.TestCase):
    """P1.1: RP2040 USB D+/D- are dedicated pins, not GP24/GP25."""

    def setUp(self):
        self.profile = registry.get_profile("rp2040")

    def test_usb_nets_drop_instead_of_mapping_to_gpio(self):
        """A schematic's USB_DP/USB_DM pins must never become GP25/GP24."""
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = self.profile.create_canonical_pinmap(
                {"USB_DP": ["USB_DP"], "USB_DM": ["USB_DM"], "LED": ["GP5"]}
            )

        self.assertEqual(result["pins"].get("LED"), ["GP5"])
        self.assertNotIn("USB_DP", result["pins"])
        self.assertNotIn("USB_DM", result["pins"])
        dropped = {d["pin"] for d in result["metadata"]["dropped_pins"]}
        self.assertEqual(dropped, {"USB_DP", "USB_DM"})

    def test_gp24_gp25_have_full_mux(self):
        """As plain chip GPIOs, GP24/GP25 keep the full capability set."""
        for name in ("GP23", "GP24", "GP25"):
            pin = self.profile.pins[name]
            self.assertIn(PinCapability.GPIO, pin.capabilities)
            self.assertIn(PinCapability.PWM, pin.capabilities)
            self.assertIn(PinCapability.UART_TX, pin.capabilities)


class TestSTM32G0CANRemoval(unittest.TestCase):
    """P1.1: the STM32G071 has no FDCAN peripheral."""

    def setUp(self):
        self.profile = registry.get_profile("stm32g0")

    def test_no_can_peripheral(self):
        names = [p.name for p in self.profile.peripherals]
        self.assertNotIn("CAN", names)

    def test_pb8_pb9_have_no_can_capabilities(self):
        for name in ("PB8", "PB9"):
            caps = self.profile.pins[name].capabilities
            self.assertNotIn(PinCapability.CAN_RX, caps)
            self.assertNotIn(PinCapability.CAN_TX, caps)

    def test_description_names_the_64_pin_part(self):
        """The pin list is the LQFP-64 set, so the description must match."""
        self.assertIn("LQFP-64", self.profile.description)


class TestESP32ModulePinData(unittest.TestCase):
    """P1.1: GPIO37/38 are not bonded out on ESP32-WROOM-32 modules."""

    def setUp(self):
        self.profile = registry.get_profile("esp32")

    def test_gpio37_gpio38_warn_on_use(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = self.profile.create_canonical_pinmap(
                {"SENSE_A": ["GPIO37"], "SENSE_B": ["GPIO38"]}
            )

        warnings = result["metadata"]["validation_warnings"]
        self.assertTrue(
            [w for w in warnings if "GPIO37" in w and "not bonded" in w]
        )
        self.assertTrue(
            [w for w in warnings if "GPIO38" in w and "not bonded" in w]
        )
        self.assertIn("not bonded", stderr.getvalue())

    def test_gpio34_gpio35_labeled_input_only_without_warning(self):
        """Input-only pins carry a label but no warning.

        Using GPIO34 as an input is perfectly legitimate; a warning on
        every use would be a false positive.
        """
        for name in ("GPIO34", "GPIO35"):
            pin = self.profile.pins[name]
            self.assertIn("Input Only", pin.special_function)
            self.assertFalse(pin.warnings)

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = self.profile.create_canonical_pinmap(
                {"BUTTON_IN": ["GPIO34"]}
            )
        self.assertFalse(result["metadata"]["validation_warnings"])


if __name__ == "__main__":
    unittest.main()
