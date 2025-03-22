import abc


class BusDriver(abc.ABC):
    def __init__(self, name: str):
        self.name = name

    @abc.abstractmethod
    def send(self, messages: list[dict]) -> None:
        pass

    @abc.abstractmethod
    def receive(self) -> list[dict] | None:
        pass


class BusDriverFactory:

    registry = {}

    @classmethod
    def register(cls, name: str, driver_cls):
        cls.registry[name] = driver_cls

    @classmethod
    def create(cls, name: str, *args, **kwargs):
        if name not in cls.registry:
            raise ValueError(f"Bus driver '{name}' not registered.")
        return cls.registry[name](*args, **kwargs)
