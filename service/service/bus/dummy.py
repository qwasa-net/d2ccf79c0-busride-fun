from .bus import BusDriver, BusDriverFactory


class DummyBusDriver(BusDriver):
    """
    Dummy bus driver.

    This driver does not send or receive messages.
    """

    def __init__(self, name: str):
        super().__init__(name)

    def send(self, messages: list[dict]) -> None:
        pass

    def receive(self) -> list[dict] | None:
        return []


BusDriverFactory.register("dummy", DummyBusDriver)
