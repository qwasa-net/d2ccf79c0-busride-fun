import argparse
import json
import os
import socket

from . import service
from .logger import configure_logging, log


def read_args() -> argparse.Namespace:
    """…"""

    parser = argparse.ArgumentParser(
        description="BusRide Service",
    )
    parser.add_argument(
        "--service-id",
        type=str,
        default=os.environ.get("SERVICE_ID", None),
    )
    parser.add_argument(
        "--services-list",
        type=str,
        default=os.environ.get("SERVICES_LIST", None),
    )
    parser.add_argument(
        "--service-type",
        type=str,
        default=os.environ.get("SERVICE_TYPE", "worker"),
        choices=["kicker", "worker", "catcher"],
    )
    parser.add_argument(
        "--work-hard-time",
        type=float,
        default=float(os.environ.get("WORK_HARD_TIME", "0.05")),
    )
    parser.add_argument(
        "--kick-count",
        type=int,
        default=int(os.environ.get("KICK_COUNT", "100")),
    )
    parser.add_argument(
        "--catch-count",
        type=int,
        default=int(os.environ.get("CATCH_COUNT", "100")),
    )
    parser.add_argument(
        "--exit",
        action="store_true",
        default=bool(os.environ.get("EXIT", "")),
    )
    parser.add_argument(
        "--bus-type",
        type=str,
        default=os.environ.get("BUS_TYPE", "redis"),
        choices=["redis", "dummy"],
    )
    parser.add_argument(
        "--bus-connection",
        type=str,
        default=os.environ.get(
            "BUS_CONNECTION",
            '{"host": "localhost", "port": 6379, "db": 0}',
        ),
    )
    args, _ = parser.parse_known_args()

    if args.bus_connection:
        try:
            args.bus_connection = json.loads(args.bus_connection)
        except Exception as e:
            raise ValueError(f"Invalid bus connection string: {e}") from e

    if args.services_list:
        args.services_list = args.services_list.split(" ")
    else:
        args.services_list = []

    if args.service_id is None:
        args.service_id = os.environ.get("HOSTNAME", socket.gethostname())

    return args


def main() -> None:
    config = read_args()
    configure_logging(config)
    log.info("Starting service with args: %s", config)
    srv = service.ServiceFactory.create(config)
    srv.run()


if __name__ == "__main__":
    main()
