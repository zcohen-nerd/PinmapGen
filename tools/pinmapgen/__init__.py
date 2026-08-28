# PinmapGen Core Package

import os
import sys
from datetime import UTC, datetime


def get_build_datetime() -> datetime:
    """Return build timestamp, respecting SOURCE_DATE_EPOCH for reproducible builds.

    When the ``SOURCE_DATE_EPOCH`` environment variable is set (integer seconds
    since the Unix epoch), the returned datetime is derived from that value,
    guaranteeing deterministic output.  Otherwise ``datetime.now(UTC)`` is used.

    A value that is not a valid integer (empty string, garbage left over
    from another tool) is ignored with a warning rather than crashing the
    run - the variable is a build-metadata convention, not user input we
    control.
    """
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch is not None:
        try:
            return datetime.fromtimestamp(int(epoch), tz=UTC)
        except (ValueError, OverflowError, OSError):
            print(
                f"Warning: ignoring invalid SOURCE_DATE_EPOCH value "
                f"{epoch!r} (expected integer seconds since the epoch)",
                file=sys.stderr,
            )
    return datetime.now(UTC)


def get_build_timestamp() -> str:
    """Return the shared human-readable timestamp for generated file headers.

    Every text emitter uses this one format so the same run stamps every
    output identically (pinmap.json keeps machine-readable ISO-8601).
    """
    return get_build_datetime().strftime("%Y-%m-%d %H:%M:%S UTC")
