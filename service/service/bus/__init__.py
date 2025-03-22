from .bus import BusDriver, BusDriverFactory  # noqa


def get_bus_driver(name: str, *args, **kwargs) -> BusDriver:
    return BusDriverFactory.create(name, *args, **kwargs)
