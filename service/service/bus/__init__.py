from .bus import BusDriver, BusDriverFactory, BusMessage  # noqa


def get_bus_driver(
    bus_type: str,
    *args: tuple,
    **kwargs: dict,
) -> BusDriver:
    return BusDriverFactory.create(bus_type, *args, **kwargs)
