"""
File Watcher for PinmapGen.

Simple polling-based file watcher for automatic pinmap regeneration.
No external dependencies - uses stdlib only.
"""

import signal
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path


class SimpleFileWatcher:
    """Simple polling-based file watcher."""

    def __init__(
        self,
        watch_paths: set[Path],
        callback: Callable[[Path], None],
        poll_interval: float = 1.0,
    ):
        """
        Initialize file watcher.

        Args:
            watch_paths: Set of paths to watch for changes
            callback: Function to call when files change
            poll_interval: Polling interval in seconds
        """
        if poll_interval <= 0:
            msg = f"poll_interval must be positive, got {poll_interval}"
            raise ValueError(msg)

        self.watch_paths = watch_paths
        self.callback = callback
        self.poll_interval = poll_interval
        self.file_times = {}  # Path -> last modified time
        self._pending = {}  # Path -> mtime awaiting one settle poll
        self.running = False

        # Initialize file modification times
        self._update_file_times()

    # File extensions relevant for pinmap generation
    _WATCH_EXTENSIONS = ("*.csv", "*.sch")

    def _update_file_times(self) -> None:
        """Update stored file modification times."""
        for watch_path in self.watch_paths:
            if watch_path.exists():
                if watch_path.is_file():
                    self.file_times[watch_path] = watch_path.stat().st_mtime
                elif watch_path.is_dir():
                    # Watch only relevant file types in directory
                    for ext in self._WATCH_EXTENSIONS:
                        for file_path in watch_path.rglob(ext):
                            self.file_times[file_path] = (
                                file_path.stat().st_mtime
                            )

    def _check_for_changes(self) -> set[Path]:
        """Check for file changes and return set of settled changed files.

        A change is only reported once the file's mtime has been stable
        for one full poll interval (debounce): editors and Excel write
        exports in several chunks, and regenerating from a half-written
        CSV produces garbage or a parse error.
        """
        candidates: dict[Path, float] = {}

        for watch_path in self.watch_paths:
            if not watch_path.exists():
                continue

            if watch_path.is_file():
                candidates[watch_path] = watch_path.stat().st_mtime
            elif watch_path.is_dir():
                # Check only relevant file types in directory
                for ext in self._WATCH_EXTENSIONS:
                    for file_path in watch_path.rglob(ext):
                        candidates[file_path] = file_path.stat().st_mtime

        changed_files = set()
        for file_path, current_time in candidates.items():
            known_time = self.file_times.get(file_path)
            if known_time == current_time:
                self._pending.pop(file_path, None)
                continue

            pending_time = self._pending.get(file_path)
            if pending_time == current_time:
                # Unchanged since last poll: the write has settled.
                self.file_times[file_path] = current_time
                del self._pending[file_path]
                changed_files.add(file_path)
            else:
                # New or still being written - wait one more poll.
                self._pending[file_path] = current_time

        return changed_files

    def start(self) -> None:
        """Start watching for file changes."""
        self.running = True
        print(f"Watching {len(self.watch_paths)} paths for changes...")
        print("Press Ctrl+C to stop watching")

        try:
            while self.running:
                changed_files = self._check_for_changes()

                if changed_files:
                    for changed_file in changed_files:
                        print(f"Detected change: {changed_file}")
                        try:
                            self.callback(changed_file)
                        except Exception as e:
                            print(f"ERROR: Callback failed for {changed_file}: {e}")

                time.sleep(self.poll_interval)

        except (KeyboardInterrupt, SystemExit):
            print("\nStopping file watcher...")
            self.stop()

    def stop(self) -> None:
        """Stop watching for file changes."""
        self.running = False


def watch_and_regenerate(
    watch_dir: Path | str,
    mcu: str = "rp2040",
    mcu_ref: str = "U1",
    out_root: Path | str = ".",
    mermaid: bool = False,
    poll_interval: float = 1.0,
    profile_dir: Path | str | None = None,
) -> None:
    """
    Watch directory for changes and regenerate pinmaps automatically.

    Args:
        watch_dir: Directory (or single .csv/.sch file) to watch
        mcu: MCU profile to use
        mcu_ref: MCU reference designator
        out_root: Output root directory
        mermaid: Whether to generate Mermaid diagrams
        poll_interval: Polling interval in seconds
        profile_dir: Optional directory with custom TOML MCU profiles,
            passed through to the CLI
    """
    # Ensure we have Path objects
    if isinstance(watch_dir, str):
        watch_dir = Path(watch_dir)
    if isinstance(out_root, str):
        out_root = Path(out_root)

    if not watch_dir.exists():
        print(f"ERROR: Watch path does not exist: {watch_dir}")
        return

    # A single .csv/.sch file may be watched instead of a directory —
    # useful when a directory holds netlists for several different MCUs.
    if watch_dir.is_file():
        if watch_dir.suffix.lower() not in (".csv", ".sch"):
            print(f"ERROR: Unsupported file type: {watch_dir.suffix}")
            return
        initial_files = {watch_dir}
    else:
        # Verify the directory has watchable files at startup
        initial_files = set()
        for pattern in ["*.csv", "*.sch"]:
            initial_files.update(watch_dir.rglob(pattern))

        if not initial_files:
            print(f"ERROR: No .csv or .sch files found in {watch_dir}")
            return

    print(f"Found {len(initial_files)} files to watch:")
    for file_path in sorted(initial_files):
        print(f"  - {file_path.name}")
    if watch_dir.is_dir():
        print("(New files added to the directory will also be detected)")
    if len(initial_files) > 1:
        print(
            "NOTE: every watched file regenerates into the same "
            f"--out-root ({out_root}) - last write wins. Watch a single "
            "file, or run one watcher per netlist with separate "
            "--out-root folders, if these are different boards."
        )

    # The subprocess imports tools.pinmapgen.cli, which only works from
    # the repository root (unless pinmapgen is pip-installed). Run it
    # there explicitly so `cd hardware/exports && watch .` works too -
    # with every path made absolute first, since they were given
    # relative to the user's directory, not the repo root.
    repo_root = Path(__file__).resolve().parents[2]

    def regenerate_callback(changed_file: Path) -> None:
        """Callback to regenerate pinmaps when files change."""
        print(f"Regenerating pinmaps for {changed_file.name}...")

        # Determine input type and build command
        cmd = [sys.executable, "-m", "tools.pinmapgen.cli"]

        if changed_file.suffix.lower() == ".csv":
            cmd.extend(["--csv", str(changed_file.resolve())])
        elif changed_file.suffix.lower() == ".sch":
            cmd.extend(["--sch", str(changed_file.resolve())])
        else:
            print(f"ERROR: Unsupported file type: {changed_file.suffix}")
            return

        cmd.extend(
            [
                "--mcu", mcu,
                "--mcu-ref", mcu_ref,
                "--out-root", str(out_root.resolve()),
            ]
        )

        if profile_dir:
            cmd.extend(["--profile-dir", str(Path(profile_dir).resolve())])

        if mermaid:
            cmd.append("--mermaid")

        try:
            # Run the pinmap generator
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                cwd=repo_root,
            )

            if result.returncode == 0:
                print("Generated OK")
                if result.stdout and result.stdout.strip():
                    print(f"Output: {result.stdout.strip()}")
                # Validation warnings/errors go to stderr even on success —
                # surface them so watch mode doesn't hide a broken pinmap.
                if result.stderr and result.stderr.strip():
                    print(f"Warnings:\n{result.stderr.strip()}")
            else:
                error_msg = "Generation failed"
                if result.stderr:
                    error_msg = result.stderr.strip()
                elif result.stdout:
                    error_msg = result.stdout.strip()
                print(f"ERROR: {error_msg}")

        except subprocess.TimeoutExpired:
            print("ERROR: Generation timed out after 30 seconds")
        except Exception as e:
            print(f"ERROR: {e!s}")

    # Create and start watcher — pass directory so new files are detected
    watcher = SimpleFileWatcher(
        watch_paths={watch_dir},
        callback=regenerate_callback,
        poll_interval=poll_interval,
    )

    watcher.start()


def main() -> None:
    """Main entry point for watch command."""
    import argparse

    from .profile_registry import registry

    parser = argparse.ArgumentParser(
        description="Watch for changes to .sch/.csv files and regenerate pinmaps automatically"
    )
    parser.add_argument(
        "watch_dir",
        type=Path,
        help="Directory (or single .csv/.sch file) to watch",
    )
    parser.add_argument(
        "--mcu",
        default=None,
        help=(
            "MCU profile (default: rp2040). Available: "
            + ", ".join(registry.list_profiles())
        ),
    )
    parser.add_argument(
        "--mcu-ref",
        default=None,
        help="MCU reference designator (default: U1)",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path(),
        help="Output root directory (default: current directory)",
    )
    parser.add_argument(
        "--profile-dir",
        type=Path,
        help="Additional directory containing custom TOML MCU profiles",
    )
    parser.add_argument(
        "--mermaid", action="store_true", help="Generate Mermaid diagrams"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Polling interval in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    if args.interval <= 0:
        parser.error(
            f"--interval must be a positive number of seconds, "
            f"got {args.interval}"
        )

    # Defaults are convenient for the common Pico case, but silently
    # generating rp2040 output for someone watching an STM32 netlist is
    # a trap - say loudly which profile is in play when it was assumed.
    defaulted = []
    if args.mcu is None:
        args.mcu = "rp2040"
        defaulted.append("--mcu rp2040")
    if args.mcu_ref is None:
        args.mcu_ref = "U1"
        defaulted.append("--mcu-ref U1")
    if defaulted:
        print(
            f"NOTE: using default {' '.join(defaulted)} - pass these "
            "explicitly if your netlist targets a different chip or "
            "reference designator."
        )

    # Validate the MCU name against the registry (including any custom
    # profile directory) instead of a hardcoded subset.
    if args.profile_dir:
        try:
            registry.add_profile_dir(args.profile_dir)
        except FileNotFoundError as exc:
            parser.error(str(exc))
    if args.mcu.lower() not in registry:
        parser.error(
            f"Unknown MCU profile '{args.mcu}'. "
            f"Available: {', '.join(registry.list_profiles())}"
        )

    # Setup signal handler for graceful shutdown
    def signal_handler(signum, frame):
        print("\nReceived interrupt signal, stopping...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, signal_handler)

    # Start watching
    watch_and_regenerate(
        watch_dir=args.watch_dir,
        mcu=args.mcu,
        mcu_ref=args.mcu_ref,
        out_root=args.out_root,
        mermaid=args.mermaid,
        poll_interval=args.interval,
        profile_dir=args.profile_dir,
    )


if __name__ == "__main__":
    main()
