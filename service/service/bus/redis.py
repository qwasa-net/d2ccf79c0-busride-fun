import redis

from ..helpers import try_ignore
from ..logger import log
from .bus import BusDriver, BusDriverFactory, BusMessage


class RedisBusDriver(BusDriver):
    """
    Redis bus driver.

    This driver uses Redis to send and receive messages.
    """

    STREAM_MAXLEN = 1000

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        *args: tuple,
        **kwargs: dict,
    ) -> None:
        self.redis = redis.Redis(host=host, port=port, db=db)

    @try_ignore(fb=None)
    def send(self, messages: list[BusMessage]) -> None:
        for message in messages:
            log.debug("sending message: %s", message)
            self.redis.xadd(
                message.rcpt,
                message.data,
                maxlen=self.STREAM_MAXLEN,
                approximate=True,
            )

    @try_ignore(fb=None)
    def receive(
        self,
        stream_name: str,
        count: int = 100,
        block: int = 1 * 1000,
    ) -> list[BusMessage] | None:

        data = self.redis.xread({stream_name: 0}, count=count, block=block)

        messages = []
        ids_to_delete = []

        for stream_data in data or []:
            for msg in stream_data[1]:
                msg_id, msg_data = msg
                log.debug("msg: %s %s", msg_id, msg_data)
                bmsg = BusMessage(data=msg_data, msg_id=msg_id)
                messages.append(bmsg)
                ids_to_delete.append(msg_id)

        if ids_to_delete:
            self.redis.xdel(stream_name, *ids_to_delete)

        return messages


BusDriverFactory.register("redis", RedisBusDriver)
