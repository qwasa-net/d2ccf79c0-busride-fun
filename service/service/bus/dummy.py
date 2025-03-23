from .bus import BusDriver, BusDriverFactory


class DummyBusDriver(BusDriver):
    """
    Dummy bus driver.

    This driver does not send or receive messages.
    """

    def __init__(self, *args: tuple, **kwargs: dict) -> None:
        pass

    def send(self, messages: list[dict]) -> None:
        pass

    def receive(self, stream_id: str | None = None) -> list[dict] | None:
        return []


BusDriverFactory.register("dummy", DummyBusDriver)
