"""Regression tests for issues #61-#64."""

import subprocess
import sys
import unittest

from tools.pinmapgen.emit_markdown import (
    generate_pinout_documentation,
    generate_single_ended_table,
)
from tools.pinmapgen.emit_mermaid import (
    _get_node_style,
    _group_pins_by_function,
    generate_mermaid_graph,
)


class TestIssue61MarkdownSpecialFunctionsFromCanonical(unittest.TestCase):
    """#61 — Markdown emitter must use canonical_dict special functions."""

    def _make_canonical(self):
        return {
            "mcu": "custom_mcu",
            "pins": {
                "NET_A": ["XPIN1"],
            },
            "differential_pairs": [],
            "metadata": {
                "total_nets": 1,
                "total_pins": 1,
                "differential_pairs_count": 0,
                "special_pins_used": ["XPIN1"],
                "special_functions_long": {
                    "XPIN1": "Custom Special Function",
                },
                "special_functions_short": {
                    "XPIN1": "CUSTOM",
                },
            },
        }

    def test_special_pins_section_uses_canonical_metadata(self):
        """Special pins section should use special_functions_long from metadata."""
        canonical = self._make_canonical()
        doc = generate_pinout_documentation(canonical)
        self.assertIn("Custom Special Function", doc)

    def test_single_ended_table_uses_canonical_metadata(self):
        """Single-ended table should use special_functions_long from metadata."""
        canonical = self._make_canonical()
        table = generate_single_ended_table(canonical)
        self.assertIn("Custom Special Function", table)


class TestIssue62PinsWithoutNumbers(unittest.TestCase):
    """#62 — Pins without numeric characters must not be silently dropped."""

    def test_markdown_includes_non_numeric_pins(self):
        canonical = {
            "mcu": "test",
            "pins": {
                "NET_ALPHA": ["XYZPIN"],
            },
            "differential_pairs": [],
            "metadata": {},
        }
        table = generate_single_ended_table(canonical)
        self.assertIn("XYZPIN", table)
        self.assertIn("NET_ALPHA", table)

    def test_mermaid_includes_non_numeric_pins(self):
        canonical = {
            "mcu": "test",
            "pins": {
                "NET_ALPHA": ["XYZPIN"],
            },
            "differential_pairs": [],
            "metadata": {},
        }
        diagram = generate_mermaid_graph(canonical)
        self.assertIn("NET_ALPHA", diagram)
        self.assertIn("XYZPIN", diagram)


class TestIssue63MermaidCommunicationKeywords(unittest.TestCase):
    """#63 — SCK, TX, RX, CS, SS nets must be classified as communication."""

    def test_sck_classified_as_communication(self):
        pin_data = [(0, "SCK", "GP0")]
        canonical = {"differential_pairs": []}
        groups = _group_pins_by_function(pin_data, canonical)
        self.assertIn("Communication", groups)
        self.assertEqual(len(groups["Communication"]), 1)

    def test_tx_classified_as_communication(self):
        pin_data = [(1, "TX", "GP1")]
        canonical = {"differential_pairs": []}
        groups = _group_pins_by_function(pin_data, canonical)
        self.assertIn("Communication", groups)

    def test_rx_classified_as_communication(self):
        pin_data = [(2, "RX", "GP2")]
        canonical = {"differential_pairs": []}
        groups = _group_pins_by_function(pin_data, canonical)
        self.assertIn("Communication", groups)

    def test_cs_classified_as_communication(self):
        pin_data = [(3, "CS", "GP3")]
        canonical = {"differential_pairs": []}
        groups = _group_pins_by_function(pin_data, canonical)
        self.assertIn("Communication", groups)

    def test_ss_classified_as_communication(self):
        pin_data = [(4, "SS", "GP4")]
        canonical = {"differential_pairs": []}
        groups = _group_pins_by_function(pin_data, canonical)
        self.assertIn("Communication", groups)

    def test_sck_node_style_is_communication(self):
        style = _get_node_style("SCK", "GP0", {"differential_pairs": []})
        self.assertEqual(style, "communication")

    def test_tx_node_style_is_communication(self):
        style = _get_node_style("TX", "GP1", {"differential_pairs": []})
        self.assertEqual(style, "communication")


class TestIssue64CLIVersion(unittest.TestCase):
    """#64 — CLI should support --version flag."""

    def test_version_flag(self):
        result = subprocess.run(
            [sys.executable, "-m", "tools.pinmapgen.cli", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertIn("0.1.0", result.stdout)


if __name__ == "__main__":
    unittest.main()
