import random
import time
from argparse import Namespace

from .bus import BusDriver, BusMessage, dummy, get_bus_driver, kafka, redis  # noqa
from .helpers import rndstr, sleeq
from .logger import log


class Service:

    def __init__(self, config: Namespace) -> None:
        self.config = config
        self._driver = None
        self.id = config.service_id
        self.services = config.services_list

    @property
    def driver(self) -> BusDriver:
        if not self._driver:
            self._driver = get_bus_driver(
                self.config.bus_type,
                **self.config.bus_connection,
            )
        return self._driver

    def run(self) -> None:
        while True:
            self.work()

    def work(self) -> None:
        # read
        log.debug("reading for service_id=`%s` ...", self.id)
        inbox = self.driver.receive(self.id)
        if not inbox:
            return

        # process
        output = self.process(inbox)

        # write
        self.driver.send(output)

    def process(self, messages: list[BusMessage]) -> list[BusMessage]:
        output = []
        for msg in messages or []:
            datas = msg.datas()
            log.debug("processing: id=%s log=%.80s", datas["id"], datas["log"])

            # hard work simulation
            sleeq(self.config.work_hard_time)
            datas["log"] = str(datas.get("log") or "") + ";" + str(self.id)
            datas["counter"] = int(datas.get("counter", 0)) + 1
            datas["payload"] = rndstr(256)

            out_msg = BusMessage(
                data=datas,
                rcpt=self.choose_rcpt(msg),
                sender=self.id,
            )

            log.debug("next hop: #%s [%s]->[%s]", datas["id"], self.id, out_msg.rcpt)
            if out_msg.rcpt is not None:
                output.append(out_msg)

        return output

    def choose_rcpt(self, message: BusMessage | None) -> str | None:
        if self.services:
            return random.choice(self.services)
        return None

    def idle(self, ts: float = 1.0) -> None:
        sleeq(ts)


class ServiceKicker(Service):

    def __init__(self, config: Namespace) -> None:
        super().__init__(config)
        self.kick_count = config.kick_count
        self.work_hard_time = config.work_hard_time

    def run(self) -> None:
        self.kick()
        log.info("kicker is done")
        while self.config.exit is False:
            self.idle(999)
        log.info("kicker exiting")

    def kick(self) -> None:
        messages = []
        for i in range(1, int(self.kick_count) + 1):
            sleeq(self.work_hard_time)
            message = BusMessage(
                data={
                    "id": str(i),
                    "ts": int(time.time()),
                    "counter": 1,
                    "log": str(self.id),
                    "payload": rndstr(256),
                },
                rcpt=self.choose_rcpt(None),
                sender=self.id,
            )
            log.info("kicking the bus: #%s ·→[%s]", i, message.rcpt)
            messages.append(message)
        self.driver.send(messages)


class ServiceCatcher(Service):

    def __init__(self, config: Namespace) -> None:
        self.catched = set()
        self.catch_count = config.catch_count
        super().__init__(config)

    def run(self) -> None:
        while self.catch_count is None or len(self.catched) < self.catch_count:
            self.work()

        log.info("catcher finished, counter=%s", len(self.catched))

        while not self.config.exit:
            self.idle(999)

        log.info("catcher exiting")

    def process(self, messages: list[BusMessage]) -> list[BusMessage]:
        for message in messages:
            datas = message.datas()
            self.catched.add(datas["id"])
            logs = datas.get("log", "").split(";")
            ride_time = int(time.time()) - int(datas.get("ts", 0))
            log.info(
                "catched (%s): #%s payload=%.10s tt=%s log=|%s/%s|=%.80s",
                len(self.catched),
                datas["id"],
                datas["payload"],
                f"{ride_time // 60}:{ride_time % 60:02d}",
                len(logs),
                len(set(logs)),
                datas["log"],
            )
        return []


class ServiceFactory:

    @classmethod
    def create(cls, config: Namespace) -> Service:
        if config.service_type == "kicker":
            return ServiceKicker(config)
        if config.service_type == "catcher":
            return ServiceCatcher(config)
        if config.service_type == "worker":
            return Service(config)
        raise ValueError(f"Unknown service type: {config.service_type}")
