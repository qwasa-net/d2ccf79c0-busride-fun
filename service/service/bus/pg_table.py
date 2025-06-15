import asyncio
import json
import time

import asyncpg

from ..helpers import async_try_ignore
from ..logger import log
from .bus import BusDriver, BusDriverFactory, BusMessage


class PostgresTablePollBusDriver(BusDriver):
    """
    Postgres bus driver:
    - table-based storage
    - reads messages by polling the table
    - marks messages as read immediately after reading
    - uses JSONB for message data storage
    - 🤯
    """

    def __init__(
        self,
        table: str = "messages",
        host: str = "localhost",
        port: int = 5432,
        user: str = "user",
        pswd: str = "password",
        db: str = "busride",
        *args: tuple,
        **kwargs: dict,
    ) -> None:
        self.dsn = f"postgresql://{user}:{pswd}@{host}:{port}/{db}"
        self.table = table
        self.conn: asyncpg.Connection | None = None

    async def start(self) -> None:
        self.conn = await asyncpg.connect(self.dsn)
        await self.conn.execute(
            f"""
            CREATE UNLOGGED TABLE IF NOT EXISTS {self.table} (
            id SERIAL PRIMARY KEY,
            rcpt VARCHAR(32),
            sender VARCHAR(32),
            data JSONB,
            read BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS idx_{self.table}_rcpt ON {self.table} (rcpt);
            """
        )

    async def stop(self) -> None:
        if self.conn:
            await self.conn.close()
            self.conn = None

    @async_try_ignore(fb=None)
    async def send(self, messages: list[BusMessage]) -> None:
        if not self.conn:
            await self.start()
        insert_rows = []
        for message in messages:
            log.debug("sending message: %s", message)
            insert_rows.append(
                (
                    str(message.rcpt) if message.rcpt else None,
                    str(message.sender) if message.sender else None,
                    json.dumps(message.data),
                )
            )

        await self.conn.executemany(
            f"""
            INSERT INTO {self.table}
            (rcpt, sender, data)
            VALUES ($1, $2, $3::jsonb)
            """,
            insert_rows,
        )

    @async_try_ignore(fb=None)
    async def receive(
        self,
        stream_name: str,
        limit: int = 1024,
        timeout: float = 10.0,
        poll_iterval: float = 1.0,
        *args: tuple,
        **kwargs: dict,
    ) -> list[BusMessage] | None:
        if not self.conn:
            await self.start()

        start_time = time.time()
        ids, messages = [], []

        while True:

            async with self.conn.transaction():
                await self._fetch_unread_messages(stream_name, limit, ids, messages)
                await self._mark_as_read(ids)

            if len(messages) > 0:
                log.debug("got %s messages from `%s`", len(messages), stream_name)
                break
            if time.time() - start_time > timeout:
                break
            await asyncio.sleep(poll_iterval)

        return messages

    async def _fetch_unread_messages(
        self,
        stream_name: str,
        limit: int,
        ids: list[int],
        messages: list[BusMessage],
    ) -> None:
        rows = await self.conn.fetch(
            f"""
                SELECT id, data, rcpt, sender
                FROM {self.table}
                WHERE rcpt = $1 AND read = FALSE
                LIMIT $2
                FOR UPDATE SKIP LOCKED
            """,
            stream_name,
            limit,
        )
        for row in rows:
            ids.append(row["id"])
            data = row["data"]
            if isinstance(data, str | bytes):
                data = json.loads(data)
            msq = BusMessage(data=data, msg_id=data.get("id"), rcpt=row["rcpt"], sender=row["sender"])
            messages.append(msq)

    async def _mark_as_read(self, ids: list[int]) -> None:
        if not ids:
            return
        await self.conn.execute(
            f"""
                UPDATE {self.table}
                SET read = TRUE
                WHERE id = ANY($1::int[])
             """,
            ids,
        )


BusDriverFactory.register("pg_table", PostgresTablePollBusDriver)
