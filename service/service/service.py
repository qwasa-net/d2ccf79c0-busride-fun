import random
import time
from argparse import Namespace
from collections import Counter

from .bus import BusDriver, BusMessage, dummy, get_bus_driver, kafka, pg_table, redis  # noqa
from .helpers import asleeq, rndstr
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

    async def run(self) -> None:
        await self.driver.start()
        while True:
            await self.work()
        await self.driver.stop()  # noqa

    async def work(self) -> None:
        # read
        log.debug("reading for service_id=`%s` ...", self.id)
        inbox = await self.driver.receive(self.id)
        if not inbox:
            return

        # process
        output = await self.process(inbox)

        # write
        await self.driver.send(output)

    async def process(self, messages: list[BusMessage]) -> list[BusMessage]:
        output = []
        for msg in messages or []:
            datas = msg.datas()
            log.debug("processing: id=%s log=%.80s", datas["id"], datas["log"])

            # hard work simulation
            await asleeq(self.config.work_hard_time)
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

    async def idle(self, ts: float = 1.0) -> None:
        await asleeq(ts)


class ServiceKicker(Service):

    def __init__(self, config: Namespace) -> None:
        super().__init__(config)
        self.kick_count = config.kick_count
        self.work_hard_time = config.work_hard_time

    async def run(self) -> None:
        await self.driver.start()
        await self.kick()
        log.info("kicker is done")
        while self.config.exit is False:
            await self.idle(999)
        log.info("kicker exiting")
        await self.driver.stop()

    async def kick(self) -> None:
        messages = []
        for i in range(1, int(self.kick_count) + 1):
            await asleeq(self.work_hard_time)
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
        await self.driver.send(messages)


class ServiceCatcher(Service):

    def __init__(self, config: Namespace) -> None:
        self.caught_ids = set()
        self.caught_stops = Counter()
        self.caught_legs = Counter()
        self.travel_times = []
        self.catch_count = config.catch_count
        super().__init__(config)

    async def run(self) -> None:
        await self.driver.start()
        while self.catch_count is None or len(self.caught_ids) < self.catch_count:
            await self.work()

        log.info("catcher finished, counter=%s", len(self.caught_ids))
        self.show_stats()

        if self.config.draw_stats:
            self.draw_stats()

        while not self.config.exit:
            await self.idle(999)

        await self.driver.stop()
        log.info("catcher exiting")

    async def process(self, messages: list[BusMessage]) -> list[BusMessage]:
        for message in messages:
            message_data = message.datas()
            self.process_message(message_data)
        return []

    def process_message(self, msg: dict) -> None:

        # keep message ids
        if msg["id"] in self.caught_ids:
            log.warning("already catched: #%s", msg["id"])
        self.caught_ids.add(msg["id"])

        # count all ride stops and legs
        logs = msg.get("log", "").split(";")
        logs.append("X")  # we are right here, at the end
        self.caught_stops.update(logs)
        for i in range(len(logs) - 1):
            leg = (logs[i], logs[i + 1])
            self.caught_legs.update([leg])

        # save travel time
        travel_time = int(time.time()) - int(msg.get("ts", 0))
        self.travel_times.append((travel_time, len(logs)))

        # log the message
        log.info(
            "catched (%s): #%s payload=%.10s tt=%s log=|%s/%s|=%.80s",
            len(self.caught_ids),
            msg["id"],
            msg["payload"],
            f"{travel_time // 60}:{travel_time % 60:02d}",
            len(logs),
            len(set(logs)),
            msg["log"],
        )

    def show_stats(self) -> None:
        log.info("catcher stats:")
        log.info("  caught messages: %s", len(self.caught_ids))
        log.info("  stops: %s", len(self.caught_stops))
        log.info("  legs: %s", len(self.caught_legs))
        log.info(
            "  min travel time/legs: %.0d/%.0d",
            min([tt[0] for tt in self.travel_times]),
            min([tt[1] for tt in self.travel_times]),
        )
        log.info(
            "  max travel time/legs: %.0d/%.0d",
            max([tt[0] for tt in self.travel_times]),
            max([tt[1] for tt in self.travel_times]),
        )
        log.info(
            "  avg travel time/legs: %.2f/%.2f",
            sum([tt[0] for tt in self.travel_times]) / len(self.travel_times),
            sum([tt[1] for tt in self.travel_times]) / len(self.travel_times),
        )
        log.info(
            "  most common stops: %s",
            "; ".join([f"{k}×{v}" for k, v in self.caught_stops.most_common(10)]),
        )
        log.info(
            "  most common legs: %s",
            "; ".join([f"{k[0]}→{k[1]}×{v}" for k, v in self.caught_legs.most_common(10)]),
        )

    def draw_stats(self) -> None:
        plantuml = [""]
        plantuml.append("@startuml")
        plantuml.append("scale 4096 width")
        plantuml.append(
            f"""title Fun Ride: {self.config.bus_type} bus, """
            f"""{len(self.caught_ids)} passengers, """
            f"""{len(self.caught_stops)} stops"""
        )
        stop_styles = {"0": "<<choice>>", "X": "<<end>>", None: "<<choice>>"}
        for stop in self.caught_stops:
            style = stop_styles.get(stop, "")
            cnt = self.caught_stops[stop]
            plantuml.append(f"""state "s{stop}" as s{stop} {style}: ×{cnt}""")
        leg_styles = {"0": "down", "X": "down", None: ""}
        for leg in self.caught_legs:
            cnt = self.caught_legs[leg]
            style = leg_styles.get(leg[0], "")
            plantuml.append(f"s{leg[0]} -{style}-> s{leg[1]}: ×{cnt}")
        plantuml.append("@enduml")
        plantuml.append("")

        log.info("########## ✂")
        log.info("\n".join(plantuml))
        log.info("########## ✂")


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
