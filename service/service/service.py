import random
import sys
from argparse import Namespace

from .bus import BusDriver, BusMessage, dummy, get_bus_driver, redis  # noqa
from .helpers import sleeq
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
        for msg in messages:
            datas = msg.datas()

            log.debug(
                "processing: id=%s log=%s",
                datas["id"],
                datas["log"][-40:],
            )
            sleeq(self.config.work_hard_time)

            datas["log"] = str(datas.get("log") or "") + ";" + str(self.id)
            datas["value"] = float(datas["value"]) + random.random()

            out_msg = BusMessage(
                data=datas,
                rcpt=self.choose_rcpt(msg),
                sender=self.id,
            )
            log.debug("sending [%s] to: %s", datas["id"], out_msg.rcpt)
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
        for i in range(int(self.kick_count)):
            sleeq(self.work_hard_time)
            message = BusMessage(
                data={"log": str(self.id), "id": str(i), "value": 0},
                rcpt=self.choose_rcpt(None),
                sender=self.id,
            )
            log.info("kicking the bus: #[%s], [%s]→[%s]", i, self.id, message.rcpt)
            self.driver.send([message])


class ServiceCatcher(Service):

    def __init__(self, config: Namespace) -> None:
        self.counter = 0
        self.catch_count = config.catch_count
        super().__init__(config)

    def work(self) -> None:
        super().work()
        if self.catch_count is not None and self.counter >= self.catch_count:
            log.info("catcher finished, counter=%s", self.counter)
            if self.config.exit:
                log.info("catcher exiting")
                sys.exit(0)

    def process(self, messages: list[BusMessage]) -> list[BusMessage]:
        for message in messages:
            datas = message.datas()
            self.counter += 1
            logg = datas.get("log", "").split(";")
            log.info(
                "catched: |%s| id=%s value=%.2f log=|%s/%s|=%.80s",
                self.counter,
                datas["id"],
                float(datas["value"]),
                len(logg),
                len(set(logg)),
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
