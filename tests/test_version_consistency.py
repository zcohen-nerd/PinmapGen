"""Every place PinmapGen reports or stamps a version must agree with the one
authoritative source: ``tools.pinmapgen.__version__`` (which resolves from the
installed package metadata, falling back to ``_FALLBACK_VERSION`` for a plain
source checkout). The release workflow enforces the same invariant against the
Git tag before it builds any release asset.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestVersionConsistency(unittest.TestCase):
    def test_pyproject_matches_package_version(self):
        from tools.pinmapgen import __version__

        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(
            pyproject["project"]["version"],
            __version__,
            "pyproject.toml [project] version must match tools.pinmapgen.__version__ "
            "(update _FALLBACK_VERSION in tools/pinmapgen/__init__.py).",
        )

    def test_cli_version_flag_reports_package_version(self):
        from tools.pinmapgen import __version__

        result = subprocess.run(
            [sys.executable, "-m", "tools.pinmapgen.cli", "--version"],
            capture_output=True,
            text=True,
            check=False,
            cwd=REPO_ROOT,
        )
        self.assertIn(__version__, result.stdout)

    def test_emitters_do_not_hardcode_a_second_version(self):
        from tools.pinmapgen import __version__

        for name in ("emit_json.py", "emit_markdown.py", "cli.py"):
            src = (REPO_ROOT / "tools" / "pinmapgen" / name).read_text(encoding="utf-8")
            # No bare version literal like "0.5.0" / v0.5.0 in the emitters —
            # they must read __version__.
            self.assertNotRegex(
                src,
                r'v?\d+\.\d+\.\d+',
                f"{name} contains a hard-coded version string; use __version__.",
            )
        # sanity: __version__ is a real semver
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")

    def test_generated_pinmap_json_stamps_the_package_version(self):
        """emit_json writes the package version into generated pinmap.json."""
        from tools.pinmapgen import __version__
        from tools.pinmapgen.emit_json import emit_json

        pinmap = {
            "mcu": "rp2040",
            "mcu_ref": "U1",
            "nets": {"LED": ["GP25"]},
            "differential_pairs": {},
            "warnings": [],
        }
        out = REPO_ROOT / "tests" / "_tmp_version_pinmap.json"
        try:
            emit_json(pinmap, out)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["generated"]["version"], __version__)
        finally:
            out.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
