import logging
from argparse import Namespace

log = logging.getLogger()


def configure_logging(config: Namespace) -> None:
    """
    Configures the logging settings for the application.
    """
    llevel = logging.DEBUG if config.debug else logging.INFO
    if llevel == logging.DEBUG:
        formats = "%(asctime)s [%(levelname)s] [%(module)s] %(message)s"
    else:
        formats = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(
        level=llevel,
        format=formats,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler()],
    )
    log.setLevel(llevel)
