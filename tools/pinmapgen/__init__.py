# PinmapGen Core Package

import os
from datetime import UTC, datetime


def get_build_datetime() -> datetime:
    """Return build timestamp, respecting SOURCE_DATE_EPOCH for reproducible builds.

    When the ``SOURCE_DATE_EPOCH`` environment variable is set (integer seconds
    since the Unix epoch), the returned datetime is derived from that value,
    guaranteeing deterministic output.  Otherwise ``datetime.now(UTC)`` is used.
    """
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch is not None:
        return datetime.fromtimestamp(int(epoch), tz=UTC)
    return datetime.now(UTC)
