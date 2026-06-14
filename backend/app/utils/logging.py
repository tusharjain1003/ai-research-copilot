import logging
import sys


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)-20s  %(message)s",
    ))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
