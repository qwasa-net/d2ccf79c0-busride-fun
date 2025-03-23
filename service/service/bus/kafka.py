import json

from confluent_kafka import Consumer, KafkaException, Producer

from ..helpers import try_ignore
from ..logger import log
from .bus import BusDriver, BusDriverFactory, BusMessage


class KafkaBusDriver(BusDriver):
    """
    Kafka bus driver.

    This driver uses Kafka to send and receive messages.
    """

    TOPIC_PREFIX = "t."

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
    def producer(self) -> Producer:
        if not self._producer:
            self._producer = Producer(
                {
                    "bootstrap.servers": self.bootstrap_servers,
                    "client.id": "bus-driver",
                    "linger.ms": 5,
                    "acks": "0",
                }
            )
        return self._producer

    @property
    def consumer(self) -> Consumer:
        if not self._consumer:
            self._consumer = Consumer(
                {
                    "bootstrap.servers": self.bootstrap_servers,
                    "group.id": self.group_id,
                    "client.id": "bus-driver",
                    "auto.offset.reset": "earliest",
                    "enable.partition.eof": False,
                    "enable.auto.commit": False,
                }
            )
        return self._consumer

    @try_ignore(fb=None)
    def send(self, messages: list[BusMessage]) -> None:
        for msg in messages:
            log.debug("sending message: %s", msg)
            topic = f"{self.TOPIC_PREFIX}{msg.rcpt}"
            try:
                data = json.dumps(msg.data).encode("utf-8")
                self.producer.produce(
                    topic=topic,
                    value=data,
                    key=msg.msg_id,
                )
            except KafkaException as e:
                log.error("kafka produce: %s", e)
        self.producer.flush()

    @try_ignore(fb=None)
    def receive(
        self,
        stream_name: str,
        count: int = 1024,
        timeout: float = 0.25,
    ) -> list[BusMessage] | None:

        self.consumer_subscribe(stream_name)

        messages = []

        try:
            msgs = self.consumer.consume(num_messages=count, timeout=timeout)
            if not msgs:
                return messages
            for msg in msgs:
                if msg is None:
                    continue
                if msg.error():
                    log.error("kafka msg: %s", msg.error())
                    continue
                log.debug("msg: %s %s", msg.key(), msg.value())
                data = json.loads(msg.value().decode("utf-8"))
                bmsg = BusMessage(data=data, msg_id=msg.key())
                messages.append(bmsg)
                self.consumer.commit(msg)
        except KafkaException as e:
            log.error("kafka consume: %s", e)

        return messages

    def consumer_subscribe(self, stream_name: str) -> None:
        topic = f"{self.TOPIC_PREFIX}{stream_name}"
        if self._subscribed_to != topic:
            self.consumer.subscribe([topic])
            self._subscribed_to = topic


BusDriverFactory.register("kafka", KafkaBusDriver)
