import json
import time

import nats

from ..helpers import async_try_ignore
from ..logger import log
from .bus import BusDriver, BusDriverFactory, BusMessage


class NatsBusDriver(BusDriver):
    """
    NATS bus driver.

    This driver uses NATS to send and receive messages.
    """

    STREAM_NAME = "bus"
    MESSAGE_SUBJECT_PREFIX = "s"

    def __init__(
        self,
        host: str = "localhost",
        port: int = 4222,
        *args: tuple,
        **kwargs: dict,
    ) -> None:
        self.servers = f"nats://{host}:{port}"
        self.nc = None
        self._subscribed_to = None
        self._sub = None

    async def start(self) -> None:
        await self._connect()

    async def stop(self) -> None:
        if self.nc is not None and not self.nc.is_closed:
            await self.nc.close()
            self.nc = None
        self._subscribed_to = None
        self._sub = None

    async def _connect(self) -> None:
        if self.nc is None or self.nc.is_closed:
            self.nc = await nats.connect(servers=self.servers)

    @async_try_ignore(fb=None)
    async def send(self, messages: list[BusMessage]) -> None:
        for message in messages:
            log.debug("sending message: %s", message)
            subject = f"{self.MESSAGE_SUBJECT_PREFIX}{message.rcpt}"
            await self.nc.publish(
                subject=subject,
                payload=json.dumps(message.data).encode("utf-8"),
            )

    @async_try_ignore(fb=None)
    async def _subscribe(self, name: str) -> None:
        subject = f"{self.MESSAGE_SUBJECT_PREFIX}{name!s}"
        if self._subscribed_to != subject:
            self._sub = await self.nc.subscribe(subject)
            self._subscribed_to = subject
        return self._sub

    @async_try_ignore(fb=None)
    async def receive(
        self,
        name: str,
        count: int = 100,
        timeout: int = 0.025 * 1000,
        *args: tuple,
        **kwargs: dict,
    ) -> list[BusMessage] | None:

        messages = []

        sub = await self._subscribe(name)
        start = time.time()

        while True:
            try:
                msg = await sub.next_msg(timeout=min(timeout / 1000, 1))
                if msg:
                    data = json.loads(msg.data.decode("utf-8"))
                    bmsg = BusMessage(data=data, rcpt=name, msg_id=msg.sid)
                    messages.append(bmsg)
            except TimeoutError:
                break
            except Exception as e:
                log.error("nats error while receiving messages: %s", e)
            if len(messages) >= count:
                break
            if time.time() - start > timeout / 1000:
                break

        return messages


BusDriverFactory.register("nats", NatsBusDriver)
