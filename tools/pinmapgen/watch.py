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

    def __init__(self, watch_paths: set[Path], callback: Callable[[Path], None], poll_interval: float = 1.0):
        """
        Initialize file watcher.
        
        Args:
            watch_paths: Set of paths to watch for changes
            callback: Function to call when files change
            poll_interval: Polling interval in seconds
        """
        self.watch_paths = watch_paths
        self.callback = callback
        self.poll_interval = poll_interval
        self.file_times = {}  # Path -> last modified time
        self.running = False

        # Initialize file modification times
        self._update_file_times()

    def _update_file_times(self) -> None:
        """Update stored file modification times."""
        for watch_path in self.watch_paths:
            if watch_path.exists():
                if watch_path.is_file():
                    self.file_times[watch_path] = watch_path.stat().st_mtime
                elif watch_path.is_dir():
                    # Watch all files in directory
                    for file_path in watch_path.rglob("*"):
                        if file_path.is_file():
                            self.file_times[file_path] = file_path.stat().st_mtime

    def _check_for_changes(self) -> set[Path]:
        """Check for file changes and return set of changed files."""
        changed_files = set()

        for watch_path in self.watch_paths:
            if not watch_path.exists():
                continue

            if watch_path.is_file():
                current_time = watch_path.stat().st_mtime
                if watch_path not in self.file_times or self.file_times[watch_path] != current_time:
                    self.file_times[watch_path] = current_time
                    changed_files.add(watch_path)

            elif watch_path.is_dir():
                # Check all files in directory
                for file_path in watch_path.rglob("*"):
                    if file_path.is_file():
                        current_time = file_path.stat().st_mtime
                        if file_path not in self.file_times or self.file_times[file_path] != current_time:
                            self.file_times[file_path] = current_time
                            changed_files.add(file_path)

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

        except KeyboardInterrupt:
            print("\nStopping file watcher...")
            self.stop()

    def stop(self) -> None:
        """Stop watching for file changes."""
        self.running = False


def watch_and_regenerate(watch_dir: Path | str,
                        mcu: str = "rp2040",
                        mcu_ref: str = "U1",
                        out_root: Path | str = ".",
                        mermaid: bool = False,
                        poll_interval: float = 1.0) -> None:
    """
    Watch directory for changes and regenerate pinmaps automatically.
    
    Args:
        watch_dir: Directory to watch for .sch/.csv files
        mcu: MCU profile to use
        mcu_ref: MCU reference designator
        out_root: Output root directory
        mermaid: Whether to generate Mermaid diagrams
        poll_interval: Polling interval in seconds
    """
    # Ensure we have Path objects
    if isinstance(watch_dir, str):
        watch_dir = Path(watch_dir)
    if isinstance(out_root, str):
        out_root = Path(out_root)

    if not watch_dir.exists():
        print(f"ERROR: Watch directory does not exist: {watch_dir}")
        return

    # Find watchable files
    watch_files = set()
    for pattern in ["*.csv", "*.sch"]:
        watch_files.update(watch_dir.glob(pattern))

    if not watch_files:
        print(f"ERROR: No .csv or .sch files found in {watch_dir}")
        return

    print(f"Found {len(watch_files)} files to watch:")
    for file_path in sorted(watch_files):
        print(f"  - {file_path.name}")

    def regenerate_callback(changed_file: Path) -> None:
        """Callback to regenerate pinmaps when files change."""
        print(f"Regenerating pinmaps for {changed_file.name}...")

        # Determine input type and build command
        cmd = [sys.executable, "-m", "tools.pinmapgen.cli"]

        if changed_file.suffix.lower() == ".csv":
            cmd.extend(["--csv", str(changed_file)])
        elif changed_file.suffix.lower() == ".sch":
            cmd.extend(["--sch", str(changed_file)])
        else:
            print(f"ERROR: Unsupported file type: {changed_file.suffix}")
            return

        cmd.extend([
            "--mcu", mcu,
            "--mcu-ref", mcu_ref,
            "--out-root", str(out_root)
        ])

        if mermaid:
            cmd.append("--mermaid")

        try:
            # Run the pinmap generator
            result = subprocess.run(
                cmd,
                check=False, capture_output=True,
                text=True,
                timeout=30  # 30 second timeout
            )

            if result.returncode == 0:
                print("Generated OK")
                if result.stdout and result.stdout.strip():
                    print(f"Output: {result.stdout.strip()}")
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

    # Create and start watcher
    watcher = SimpleFileWatcher(
        watch_paths=watch_files,
        callback=regenerate_callback,
        poll_interval=poll_interval
    )

    watcher.start()


def main() -> None:
    """Main entry point for watch command."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Watch for changes to .sch/.csv files and regenerate pinmaps automatically"
    )
    parser.add_argument(
        "watch_dir",
        type=Path,
        help="Directory to watch for .sch/.csv files"
    )
    parser.add_argument(
        "--mcu",
        default="rp2040",
        choices=["rp2040"],
        help="MCU profile (default: rp2040)"
    )
    parser.add_argument(
        "--mcu-ref",
        default="U1",
        help="MCU reference designator (default: U1)"
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path(),
        help="Output root directory (default: current directory)"
    )
    parser.add_argument(
        "--mermaid",
        action="store_true",
        help="Generate Mermaid diagrams"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Polling interval in seconds (default: 1.0)"
    )

    args = parser.parse_args()

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
        poll_interval=args.interval
    )


if __name__ == "__main__":
    main()
