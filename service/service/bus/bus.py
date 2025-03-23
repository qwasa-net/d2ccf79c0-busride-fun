import abc
import dataclasses
from collections import defaultdict


@dataclasses.dataclass
class BusMessage:
    data: dict
    rcpt: str | int | None = None
    sender: str | int | None = None
    msg_id: str | int | None = None

    def datas(self) -> dict:
        datas = defaultdict(str)
        for key, value in self.data.items():
            if isinstance(key, bytes):
                key = key.decode("utf-8")
            if isinstance(value, bytes):
                datas[key] = value.decode("utf-8")
            elif not isinstance(value, str):
                datas[key] = str(value)
            else:
                datas[key] = value
        return datas


class BusDriver(abc.ABC):

    @abc.abstractmethod
    def __init__(self, *args: tuple, **kwargs: dict) -> None:
        pass

    @abc.abstractmethod
    def send(self, messages: list[BusMessage], *args: tuple, **kwargs: dict) -> None:
        pass

    @abc.abstractmethod
    def receive(self, *args: tuple, **kwargs: dict) -> list[BusMessage] | None:
        pass


class BusDriverFactory:

    registry: dict[str, BusDriver] = {}

    @classmethod
    def register(cls, bus_type: str, driver_cls: BusDriver) -> None:
        cls.registry[bus_type] = driver_cls

    @classmethod
    def create(cls, bus_type: str, *args: tuple, **kwargs: dict) -> BusDriver:
        if bus_type not in cls.registry:
            raise ValueError(f"Bus driver '{bus_type}' not registered.")
        return cls.registry[bus_type](*args, **kwargs)
