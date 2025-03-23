import redis

from ..helpers import try_except
from ..logger import log
from .bus import BusDriver, BusDriverFactory, BusMessage


class RedisBusDriver(BusDriver):
    """
    Redis bus driver.

    This driver uses Redis to send and receive messages.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        *args: tuple,
        **kwargs: dict,
    ) -> None:
        self.redis = redis.Redis(host=host, port=port, db=db)

    @try_except(fallback=None)
    def send(self, messages: list[BusMessage]) -> None:
        for message in messages:
            log.debug("sending message: %s", message)
            self.redis.xadd(message.rcpt, message.data)

    @try_except(fallback=None)
    def receive(
        self,
        stream_name: str,
        count: int = 100,
        block: int = 25 * 1000,
    ) -> list[BusMessage] | None:

        data = self.redis.xread({stream_name: 0}, count=count, block=block)

        messages = []
        for stream_data in data or []:
            for msg in stream_data[1]:
                msg_id, msg_data = msg
                log.debug("msg: %s %s", msg_id, msg_data)
                bmsg = BusMessage(data=msg_data, msg_id=msg_id)
                messages.append(bmsg)

                self.redis.xdel(stream_name, msg_id)

        return messages


BusDriverFactory.register("redis", RedisBusDriver)
