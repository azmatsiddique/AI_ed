# src/core/database.py
import sqlite3
import aiosqlite
import asyncio
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List

load_dotenv(override=True)

DB = "accounts.db"
logger = logging.getLogger("database")


def _init_db_sync():
    """Ensure database tables exist and set WAL mode for high performance & concurrency."""
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("CREATE TABLE IF NOT EXISTS accounts (name TEXT PRIMARY KEY, account TEXT)")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                datetime TEXT,
                type TEXT,
                message TEXT
            )
        """)
        cursor.execute("CREATE TABLE IF NOT EXISTS market (date TEXT PRIMARY KEY, data TEXT)")
        conn.commit()


_init_db_sync()


# Async Database API (aiosqlite)
async def async_write_account(name: str, account_dict: Dict[str, Any]) -> None:
    json_data = json.dumps(account_dict)
    async with aiosqlite.connect(DB) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("""
            INSERT INTO accounts (name, account)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET account=excluded.account
        """, (name.lower(), json_data))
        await db.commit()


async def async_read_account(name: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT account FROM accounts WHERE name = ?", (name.lower(),)) as cursor:
            row = await cursor.fetchone()
            return json.loads(row[0]) if row else None


async def async_write_log(name: str, log_type: str, message: str) -> None:
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("""
            INSERT INTO logs (name, datetime, type, message)
            VALUES (?, ?, ?, ?)
        """, (name.lower(), now, log_type, message))
        await db.commit()


async def async_read_log(name: str, last_n: int = 10) -> List[tuple]:
    async with aiosqlite.connect(DB) as db:
        async with db.execute("""
            SELECT datetime, type, message FROM logs 
            WHERE name = ? 
            ORDER BY datetime DESC
            LIMIT ?
        """, (name.lower(), last_n)) as cursor:
            rows = await cursor.fetchall()
            return list(reversed(rows))


async def async_write_market(date: str, data: Dict[str, Any]) -> None:
    data_json = json.dumps(data)
    async with aiosqlite.connect(DB) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("""
            INSERT INTO market (date, data)
            VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET data=excluded.data
        """, (date, data_json))
        await db.commit()


async def async_read_market(date: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT data FROM market WHERE date = ?", (date,)) as cursor:
            row = await cursor.fetchone()
            return json.loads(row[0]) if row else None


# Synchronous Helper API (for backward compatibility & sync contexts)
def write_account(name: str, account_dict: Dict[str, Any]) -> None:
    json_data = json.dumps(account_dict)
    with sqlite3.connect(DB) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            INSERT INTO accounts (name, account)
            VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET account=excluded.account
        """, (name.lower(), json_data))
        conn.commit()


def read_account(name: str) -> Optional[Dict[str, Any]]:
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT account FROM accounts WHERE name = ?", (name.lower(),))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None


def write_log(name: str, log_type: str, message: str) -> None:
    now = datetime.now().isoformat()
    with sqlite3.connect(DB) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            INSERT INTO logs (name, datetime, type, message)
            VALUES (?, ?, ?, ?)
        """, (name.lower(), now, log_type, message))
        conn.commit()


def read_log(name: str, last_n: int = 10) -> List[tuple]:
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT datetime, type, message FROM logs 
            WHERE name = ? 
            ORDER BY datetime DESC
            LIMIT ?
        """, (name.lower(), last_n))
        return list(reversed(cursor.fetchall()))


def write_market(date: str, data: Dict[str, Any]) -> None:
    data_json = json.dumps(data)
    with sqlite3.connect(DB) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            INSERT INTO market (date, data)
            VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET data=excluded.data
        """, (date, data_json))
        conn.commit()


def read_market(date: str) -> Optional[Dict[str, Any]]:
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM market WHERE date = ?", (date,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row else None
