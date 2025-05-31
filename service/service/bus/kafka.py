import json

import aiokafka
import aiokafka.errors

from ..helpers import async_try_ignore
from ..logger import log
from .bus import BusDriver, BusDriverFactory, BusMessage


class KafkaBusDriver(BusDriver):
    """
    Kafka bus driver.

    This driver uses Kafka to send and receive messages.
    """

    TOPIC_PREFIX = "t."
    AUTO_COMMIT_INTERVAL = 5000  # ms

    def __init__(
        self,
        bootstrap_servers: str = "kafka:9092",
        group_id: str = "default-group",
        *args: tuple,
        **kwargs: dict,
    ) -> None:
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self._producer = None
        self._consumer = None
        self._subscribed_to = None

    @property
    def producer(self) -> aiokafka.AIOKafkaProducer:
        if not self._producer:
            self._producer = aiokafka.AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                client_id="bus-driver",
                linger_ms=10,
                acks=0,
            )
        return self._producer

    @property
    def consumer(self) -> aiokafka.AIOKafkaConsumer:
        if not self._consumer:
            self._consumer = aiokafka.AIOKafkaConsumer(
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                client_id="bus-driver",
                auto_offset_reset="earliest",
                enable_auto_commit=self.AUTO_COMMIT_INTERVAL > 0,
                auto_commit_interval_ms=self.AUTO_COMMIT_INTERVAL,
                session_timeout_ms=90000,  # here goes some magic numbers
                consumer_timeout_ms=100,
                max_poll_records=1024,
                retry_backoff_ms=1000,
            )
        return self._consumer

    async def start(self) -> None:
        await self.producer.start()
        await self.consumer.start()

    async def stop(self) -> None:
        await self.producer.stop()
        await self.consumer.stop()

    @async_try_ignore(fb=None)
    async def send(self, messages: list[BusMessage]) -> None:
        for msg in messages:
            log.debug("sending message: %s", msg)
            topic = f"{self.TOPIC_PREFIX}{msg.rcpt}"
            try:
                data = json.dumps(msg.data).encode("utf-8")
                rc = await self.producer.send_and_wait(
                    topic=topic,
                    value=data,
                    key=str(msg.msg_id).encode("utf-8") if msg.msg_id else None,
                )
                log.debug("kafka produce result: %s", rc)
            except aiokafka.errors.KafkaError as e:
                log.error("kafka produce: %s", e)

    @async_try_ignore(fb=None)
    async def receive(
        self,
        stream_name: str,
        count: int = 1024,
        timeout: float = 0.25,
        *args: tuple,
        **kwargs: dict,
    ) -> list[BusMessage] | None:

        await self.consumer_subscribe(stream_name)

        messages = []
        topic_part = aiokafka.TopicPartition(f"{self.TOPIC_PREFIX}{stream_name}", 0)
        try:
            result = await self.consumer.getmany(timeout_ms=int(timeout * 1000), max_records=count)
            for topic_part, top_messages in result.items():
                log.debug("got %s messages from `%s`", len(top_messages), topic_part)
                for msg in top_messages:
                    if msg is None:
                        continue
                    log.debug("msg: %s %s", msg.key, msg.value)
                    data = json.loads(msg.value.decode("utf-8"))
                    bmsg = BusMessage(data=data, msg_id=msg.key.decode("utf-8") if msg.key else None)
                    messages.append(bmsg)
                    if not self.AUTO_COMMIT_INTERVAL:
                        await self.consumer.commit()
                    if len(messages) >= count:
                        break
        except aiokafka.errors.KafkaError as e:
            log.error("kafka consume: %s", e)
        except TimeoutError:
            pass

        return messages

    async def consumer_subscribe(self, stream_name: str) -> None:
        topic = f"{self.TOPIC_PREFIX}{stream_name}"
        if self._subscribed_to != topic:
            log.info("subscribing to topic: %s", topic)
            self.consumer.subscribe([topic])
            self._subscribed_to = topic


BusDriverFactory.register("kafka", KafkaBusDriver)
