"""
MCU Profile Registry with auto-discovery for PinmapGen.

Discovers built-in TOML profiles from ``tools/pinmapgen/profiles/``,
user-supplied TOML profiles via ``--profile-dir``, and programmatically
registered Python ``MCUProfile`` subclasses.

Discovery order (later wins on name collision unless both are TOML
within the *same* directory scan, which triggers an error):

1. Built-in TOML files in ``<package>/profiles/*.toml``.
2. User-supplied TOML directories added via :meth:`add_profile_dir`.
   (overrides built-in TOMLs with the same name — logged as info)
3. Python profile classes registered via :meth:`register`.
   (always override TOML — logged as info)

Usage::

    from tools.pinmapgen.profile_registry import registry

    # List available profiles
    print(registry.list_profiles())

    # Get (instantiate) a profile
    profile = registry.get_profile("rp2040")

    # Add a user directory at runtime
    registry.add_profile_dir(Path("~/my_profiles"))
"""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path
from typing import Any

from .mcu_profiles import MCUProfile  # noqa: TC001 — used at runtime
from .profile_loader import TOMLProfile

_logger = logging.getLogger(__name__)


class ProfileCollisionError(Exception):
    """Raised when two TOML files in the same directory claim the same name."""


class ProfileRegistry:
    """Central registry for MCU profiles.

    Resolution priority (highest → lowest):

    1. Python profile classes registered via :meth:`register`.
    2. User-supplied TOML directories added via :meth:`add_profile_dir`.
    3. Built-in TOML files in ``<package>/profiles/*.toml``.
    """

    def __init__(self, *, discover_builtins: bool = True) -> None:
        # Maps lowercase profile name → TOML path *or* Python class.
        self._entries: dict[str, Path | type[MCUProfile]] = {}

        if discover_builtins:
            builtin_dir = Path(__file__).resolve().parent / "profiles"
            if builtin_dir.is_dir():
                self._scan_directory(builtin_dir)

    # -- Public API ---------------------------------------------------------

    def add_profile_dir(self, directory: Path | str) -> None:
        """Scan *directory* for ``*.toml`` profile files and add them.

        TOML files whose ``profile.name`` collides with an existing TOML
        override it.  An info-level log message records the override.
        """
        directory = Path(directory)
        if not directory.is_dir():
            msg = f"Profile directory does not exist: {directory}"
            raise FileNotFoundError(msg)
        self._scan_directory(directory)

    def register(self, name: str, profile_class: type[MCUProfile]) -> None:
        """Programmatically register a Python profile class.

        This always overrides any TOML file with the same *name*.
        """
        key = name.lower()
        existing = self._entries.get(key)
        if isinstance(existing, Path):
            _logger.info(
                "Python profile '%s' (%s) overrides TOML profile at %s",
                key,
                profile_class.__qualname__,
                existing,
            )
        self._entries[key] = profile_class

    def get_profile(self, name: str) -> MCUProfile:
        """Instantiate and return the profile identified by *name*.

        Raises:
            KeyError: If no profile with *name* is registered.
        """
        key = name.lower()
        if key not in self._entries:
            available = ", ".join(self.list_profiles()) or "(none)"
            msg = (
                f"Unknown MCU profile '{name}'. "
                f"Available profiles: {available}"
            )
            raise KeyError(msg)

        entry = self._entries[key]
        if isinstance(entry, Path):
            return TOMLProfile(entry)
        # Python class - instantiate it.
        return entry()

    def list_profiles(self) -> list[str]:
        """Return sorted list of registered profile names."""
        return sorted(self._entries)

    def get_profile_info(self, name: str) -> dict[str, Any]:
        """Return metadata dict for a profile without fully instantiating it.

        For TOML profiles this reads only the ``[profile]`` table.  For
        Python profiles a minimal dict with the class name is returned.
        """
        key = name.lower()
        entry = self._entries.get(key)
        if entry is None:
            msg = f"Unknown profile: {name}"
            raise KeyError(msg)

        if isinstance(entry, Path):
            with entry.open("rb") as fh:
                cfg = tomllib.load(fh)
            meta = cfg.get("profile", {})
            return {
                "name": meta.get("name", key),
                "display_name": meta.get("display_name", key.upper()),
                "description": meta.get("description", ""),
                "family": meta.get("family", ""),
                "schema_version": meta.get("schema_version"),
                "source": "toml",
                "path": str(entry),
            }

        return {
            "name": key,
            "display_name": key.upper(),
            "description": entry.__doc__ or "",
            "family": "",
            "schema_version": None,
            "source": "python",
            "class": entry.__qualname__,
        }

    def __contains__(self, name: str) -> bool:
        return name.lower() in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    # -- Internals ----------------------------------------------------------

    def _scan_directory(self, directory: Path) -> None:
        """Discover TOML profiles in *directory*.

        Files are processed in sorted order (deterministic).  Within a
        single directory, two files that declare the same ``profile.name``
        raise :class:`ProfileCollisionError`.  Across directories, a later
        scan overrides earlier entries with an info log.
        """
        # Collect all entries from this single directory first so that we
        # can detect intra-directory collisions before merging.
        new_entries: dict[str, Path] = {}

        for toml_file in sorted(directory.glob("*.toml")):
            resolved = toml_file.resolve()

            # Read profile.name from the TOML (lightweight parse).
            try:
                with toml_file.open("rb") as fh:
                    cfg = tomllib.load(fh)
                name = (
                    cfg.get("profile", {})
                    .get("name", toml_file.stem)
                    .lower()
                )
            except Exception:  # noqa: BLE001
                # If the TOML can't even be parsed, fall back to stem.
                # Full validation happens later in TOMLProfile.__init__.
                name = toml_file.stem.lower()

            # Intra-directory collision check.
            if name in new_entries:
                msg = (
                    f"Profile name '{name}' is claimed by multiple files "
                    f"in {directory}:\n"
                    f"  - {new_entries[name]}\n"
                    f"  - {resolved}\n"
                    f"Ensure each profile has a unique [profile] name."
                )
                raise ProfileCollisionError(msg)

            new_entries[name] = resolved

        # Merge into main registry (cross-directory overrides are logged).
        for name in sorted(new_entries):
            path = new_entries[name]
            existing = self._entries.get(name)
            if isinstance(existing, Path) and existing != path:
                _logger.info(
                    "Profile '%s' from %s overrides %s",
                    name,
                    path,
                    existing,
                )
            self._entries[name] = path


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

registry = ProfileRegistry()
