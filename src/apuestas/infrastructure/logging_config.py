import logging
import os
import sys


def setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    fmt = "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format=fmt,
        datefmt=date_fmt,
        stream=sys.stdout,
        force=True,
    )

    # Silenciar loggers ruidosos de terceros
    for noisy in ("urllib3", "httpx", "apscheduler.scheduler"):
        logging.getLogger(noisy).setLevel(logging.WARNING)