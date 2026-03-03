import logging
import sys

def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())

    if root.handlers:
        for h in list(root.handlers):
            root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
