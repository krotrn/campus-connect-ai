"""Central logging configuration.

Replaces ad-hoc ``print()`` calls with the stdlib logger so that output is
levelled, timestamped, and capturable by the container runtime.
"""

import logging
import sys

_CONFIGURED = False


def configure_logging(level: str | None = None) -> None:
    """Configure root logging once, idempotently."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    from src.config import settings

    resolved = (level or settings.log_level).upper()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(getattr(logging, resolved, logging.INFO))
    root.addHandler(handler)

    # Third-party libraries are chatty at INFO; keep them at WARNING.
    for noisy in ("httpx", "httpcore", "urllib3", "qdrant_client"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True
