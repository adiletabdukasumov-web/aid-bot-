"""Хранилище: PostgreSQL (если задан DATABASE_URL) или файл SQLite (по умолчанию).

SQLite не требует отдельного сервера: база лежит одним файлом data/bot.db рядом с ботом.
Запросы пишутся с плейсхолдерами $1, $2... строго по порядку; для SQLite они превращаются в «?».
Время хранится как число секунд (time.time()), поэтому SQL одинаковый для обеих баз.
"""
import asyncio
import re
import sqlite3
import threading
from pathlib import Path

_PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS rb_messages(
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    ts DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS rb_messages_chat_idx ON rb_messages(chat_id, id);
CREATE TABLE IF NOT EXISTS rb_chat_state(
    chat_id BIGINT PRIMARY KEY,
    paused_until DOUBLE PRECISION,
    client_name TEXT
);
CREATE TABLE IF NOT EXISTS rb_settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rb_drafts(
    id BIGSERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    connection_id TEXT NOT NULL,
    text TEXT NOT NULL,
    notify_msg_id BIGINT,
    created DOUBLE PRECISION NOT NULL
);
"""

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS rb_messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS rb_messages_chat_idx ON rb_messages(chat_id, id);
CREATE TABLE IF NOT EXISTS rb_chat_state(
    chat_id INTEGER PRIMARY KEY,
    paused_until REAL,
    client_name TEXT
);
CREATE TABLE IF NOT EXISTS rb_settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS rb_drafts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER NOT NULL,
    connection_id TEXT NOT NULL,
    text TEXT NOT NULL,
    notify_msg_id INTEGER,
    created REAL NOT NULL
);
"""

_PLACEHOLDER = re.compile(r"\$\d+")


class SqliteDB:
    kind = "sqlite"

    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")

    def _run(self, q: str, args, mode: str):
        q = _PLACEHOLDER.sub("?", q)
        with self._lock:
            cur = self._conn.execute(q, args)
            if mode == "all":
                return [dict(r) for r in cur.fetchall()]
            if mode == "row":
                r = cur.fetchone()
                cur.fetchall()
                return dict(r) if r is not None else None
            if mode == "val":
                r = cur.fetchone()
                cur.fetchall()
                return r[0] if r is not None else None
            return None

    async def init(self):
        with self._lock:
            self._conn.executescript(_SQLITE_SCHEMA)

    async def execute(self, q, *args):
        await asyncio.to_thread(self._run, q, args, "none")

    async def fetch(self, q, *args):
        return await asyncio.to_thread(self._run, q, args, "all")

    async def fetchrow(self, q, *args):
        return await asyncio.to_thread(self._run, q, args, "row")

    async def fetchval(self, q, *args):
        return await asyncio.to_thread(self._run, q, args, "val")

    async def close(self):
        with self._lock:
            self._conn.close()


class PostgresDB:
    kind = "postgres"

    def __init__(self, url: str):
        self.url = url
        self.pool = None

    async def init(self):
        import asyncpg  # нужен только для PostgreSQL

        self.pool = await asyncpg.create_pool(self.url)
        async with self.pool.acquire() as conn:
            await conn.execute(_PG_SCHEMA)

    async def execute(self, q, *args):
        await self.pool.execute(q, *args)

    async def fetch(self, q, *args):
        return [dict(r) for r in await self.pool.fetch(q, *args)]

    async def fetchrow(self, q, *args):
        r = await self.pool.fetchrow(q, *args)
        return dict(r) if r is not None else None

    async def fetchval(self, q, *args):
        return await self.pool.fetchval(q, *args)

    async def close(self):
        await self.pool.close()


def open_db(database_url: str, sqlite_path: str):
    if database_url:
        return PostgresDB(database_url)
    return SqliteDB(sqlite_path)
