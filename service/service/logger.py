import logging
from argparse import Namespace

log = logging.getLogger()


def configure_logging(config: Namespace) -> None:
    """
    Configures the logging settings for the application.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler()],
    )
    log.setLevel(logging.INFO)
