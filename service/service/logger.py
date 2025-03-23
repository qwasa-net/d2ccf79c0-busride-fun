import logging
from argparse import Namespace

log = logging.getLogger()


def configure_logging(config: Namespace) -> None:
    """
    Configures the logging settings for the application.
    """
    llevel = logging.DEBUG if config.debug else logging.INFO
    logging.basicConfig(
        level=llevel,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler()],
    )
    log.setLevel(llevel)
