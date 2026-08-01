# src/core/database.py
"""
Persistent Async Database Connection Manager with Safe SQL Migration & Pure Async API.
Backed by aiosqlite with WAL mode and foreign key constraints.
"""

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
    """
    Ensure normalized relational tables exist with WAL mode and foreign key constraints.
    Safe Migration: If legacy JSON schema exists, migrate data safely without data loss before cleanup.
    """
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")

        # Safe Migration Check
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'")
        table_exists = cursor.fetchone()
        if table_exists:
            cursor.execute("PRAGMA table_info(accounts)")
            columns = [row[1] for row in cursor.fetchall()]
            if "account" in columns and "balance" not in columns:
                logger.info("Safe SQL Migration: Migrating legacy JSON accounts table to normalized relational schema...")
                cursor.execute("ALTER TABLE accounts RENAME TO accounts_legacy")

        # 1. Relational Accounts Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                name TEXT PRIMARY KEY,
                balance TEXT NOT NULL,
                strategy TEXT
            )
        """)

        # 2. Relational Holdings Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS holdings (
                account_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                PRIMARY KEY (account_name, symbol),
                FOREIGN KEY (account_name) REFERENCES accounts(name) ON DELETE CASCADE
            )
        """)

        # 3. Relational Transactions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                rationale TEXT,
                FOREIGN KEY (account_name) REFERENCES accounts(name) ON DELETE CASCADE
            )
        """)

        # 4. Portfolio History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                portfolio_value TEXT NOT NULL,
                FOREIGN KEY (account_name) REFERENCES accounts(name) ON DELETE CASCADE
            )
        """)

        # 5. Logs Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                datetime TEXT,
                type TEXT,
                message TEXT
            )
        """)

        # 6. Market Cache Table
        cursor.execute("CREATE TABLE IF NOT EXISTS market (date TEXT PRIMARY KEY, data TEXT)")

        # Execute Safe Legacy Data Population if accounts_legacy exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts_legacy'")
        if cursor.fetchone():
            try:
                cursor.execute("SELECT name, account FROM accounts_legacy")
                legacy_rows = cursor.fetchall()
                for acc_name, json_str in legacy_rows:
                    if not json_str:
                        continue
                    data = json.loads(json_str)
                    clean_name = acc_name.lower().strip()
                    balance_str = str(data.get("balance", "100000.00"))
                    strategy = data.get("strategy", "")
                    
                    cursor.execute("""
                        INSERT INTO accounts (name, balance, strategy)
                        VALUES (?, ?, ?)
                        ON CONFLICT(name) DO UPDATE SET balance=excluded.balance, strategy=excluded.strategy
                    """, (clean_name, balance_str, strategy))

                    for sym, qty in data.get("holdings", {}).items():
                        if qty > 0:
                            cursor.execute("""
                                INSERT INTO holdings (account_name, symbol, quantity)
                                VALUES (?, ?, ?)
                                ON CONFLICT(account_name, symbol) DO UPDATE SET quantity=excluded.quantity
                            """, (clean_name, sym.upper(), qty))

                    for t in data.get("transactions", []):
                        cursor.execute("""
                            INSERT INTO transactions (account_name, symbol, quantity, price, timestamp, rationale)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            clean_name,
                            t.get("symbol", "").upper(),
                            t.get("quantity", 0),
                            str(t.get("price", "0.0")),
                            t.get("timestamp", ""),
                            t.get("rationale", "")
                        ))

                    for ts_entry in data.get("portfolio_value_time_series", []):
                        if isinstance(ts_entry, (list, tuple)) and len(ts_entry) == 2:
                            cursor.execute("""
                                INSERT INTO portfolio_history (account_name, timestamp, portfolio_value)
                                VALUES (?, ?, ?)
                            """, (clean_name, str(ts_entry[0]), str(ts_entry[1])))

                cursor.execute("DROP TABLE accounts_legacy")
                logger.info("Safe SQL Migration completed successfully. Legacy table removed.")
            except Exception as exc:
                logger.error(f"Migration error: {exc}. Retaining accounts_legacy table for safety.", exc_info=True)

        conn.commit()


_init_db_sync()


# -------------------------------------------------------------
# Module-Level Persistent Connection Pool / Manager
# -------------------------------------------------------------

class AsyncDatabaseManager:
    """Module-level persistent connection pool manager for aiosqlite."""

    def __init__(self, db_path: str = DB):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def get_connection(self) -> aiosqlite.Connection:
        async with self._lock:
            if self._conn is None or not self._conn._running:
                self._conn = await aiosqlite.connect(self.db_path)
                await self._conn.execute("PRAGMA journal_mode=WAL;")
                await self._conn.execute("PRAGMA synchronous=NORMAL;")
                await self._conn.execute("PRAGMA foreign_keys=ON;")
            return self._conn

    async def close(self) -> None:
        async with self._lock:
            if self._conn:
                await self._conn.close()
                self._conn = None


db_manager = AsyncDatabaseManager()


# -------------------------------------------------------------
# Pure Async Database API
# -------------------------------------------------------------

async def async_write_account(name: str, account_dict: Dict[str, Any]) -> None:
    """Save account state atomically into normalized relational tables."""
    acc_name = name.lower().strip()
    balance_str = str(account_dict.get("balance", "100000.00"))
    strategy = account_dict.get("strategy", "")
    holdings = account_dict.get("holdings", {})
    transactions = account_dict.get("transactions", [])
    history = account_dict.get("portfolio_value_time_series", [])

    db = await db_manager.get_connection()
    try:
        await db.execute("BEGIN TRANSACTION;")
        await db.execute("""
            INSERT INTO accounts (name, balance, strategy)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                balance=excluded.balance,
                strategy=excluded.strategy
        """, (acc_name, balance_str, strategy))

        await db.execute("DELETE FROM holdings WHERE account_name = ?", (acc_name,))
        for sym, qty in holdings.items():
            if qty > 0:
                await db.execute("""
                    INSERT INTO holdings (account_name, symbol, quantity)
                    VALUES (?, ?, ?)
                """, (acc_name, sym.upper(), qty))

        await db.execute("DELETE FROM transactions WHERE account_name = ?", (acc_name,))
        for t in transactions:
            await db.execute("""
                INSERT INTO transactions (account_name, symbol, quantity, price, timestamp, rationale)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                acc_name, 
                t.get("symbol", "").upper(), 
                t.get("quantity", 0), 
                str(t.get("price", "0.0")), 
                t.get("timestamp", ""), 
                t.get("rationale", "")
            ))

        await db.execute("DELETE FROM portfolio_history WHERE account_name = ?", (acc_name,))
        for ts_entry in history:
            if isinstance(ts_entry, (list, tuple)) and len(ts_entry) == 2:
                await db.execute("""
                    INSERT INTO portfolio_history (account_name, timestamp, portfolio_value)
                    VALUES (?, ?, ?)
                """, (acc_name, str(ts_entry[0]), str(ts_entry[1])))

        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.error(f"Failed atomic account write for '{acc_name}': {exc}", exc_info=True)
        raise exc


async def async_read_account(name: str) -> Optional[Dict[str, Any]]:
    """Query normalized relational tables to reconstruct account payload asynchronously."""
    acc_name = name.lower().strip()
    db = await db_manager.get_connection()
    async with db.execute("SELECT balance, strategy FROM accounts WHERE name = ?", (acc_name,)) as cursor:
        row = await cursor.fetchone()
        if not row:
            return None
        balance_str, strategy = row

    holdings = {}
    async with db.execute("SELECT symbol, quantity FROM holdings WHERE account_name = ?", (acc_name,)) as cursor:
        async for sym, qty in cursor:
            holdings[sym] = qty

    transactions = []
    async with db.execute("""
        SELECT symbol, quantity, price, timestamp, rationale 
        FROM transactions 
        WHERE account_name = ? 
        ORDER BY id ASC
    """, (acc_name,)) as cursor:
        async for sym, qty, price_str, ts, rationale in cursor:
            transactions.append({
                "symbol": sym,
                "quantity": qty,
                "price": price_str,
                "timestamp": ts,
                "rationale": rationale
            })

    history = []
    async with db.execute("""
        SELECT timestamp, portfolio_value 
        FROM portfolio_history 
        WHERE account_name = ? 
        ORDER BY id ASC
    """, (acc_name,)) as cursor:
        async for ts, val_str in cursor:
            try:
                history.append((ts, float(val_str)))
            except ValueError:
                pass

    return {
        "name": acc_name,
        "balance": balance_str,
        "strategy": strategy,
        "holdings": holdings,
        "transactions": transactions,
        "portfolio_value_time_series": history
    }


async def async_write_log(name: str, log_type: str, message: str) -> None:
    now = datetime.now().isoformat()
    db = await db_manager.get_connection()
    await db.execute("""
        INSERT INTO logs (name, datetime, type, message)
        VALUES (?, ?, ?, ?)
    """, (name.lower(), now, log_type, message))
    await db.commit()


async def async_read_log(name: str, last_n: int = 10) -> List[tuple]:
    db = await db_manager.get_connection()
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
    db = await db_manager.get_connection()
    await db.execute("""
        INSERT INTO market (date, data)
        VALUES (?, ?)
        ON CONFLICT(date) DO UPDATE SET data=excluded.data
    """, (date, data_json))
    await db.commit()


async def async_read_market(date: str) -> Optional[Dict[str, Any]]:
    db = await db_manager.get_connection()
    async with db.execute("SELECT data FROM market WHERE date = ?", (date,)) as cursor:
        row = await cursor.fetchone()
        return json.loads(row[0]) if row else None
