# src/core/database.py
"""
Normalized relational SQLite database layer backed by aiosqlite with WAL mode.
Replaces JSON-blob storage with relational accounts, holdings, and transactions tables.
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
    """Ensure normalized relational tables exist with WAL mode and foreign key constraints."""
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")

        # Migrate legacy accounts table if it has old JSON 'account' column
        cursor.execute("PRAGMA table_info(accounts)")
        columns = [row[1] for row in cursor.fetchall()]
        if columns and "account" in columns and "balance" not in columns:
            logger.info("Migrating legacy accounts table to normalized relational schema...")
            cursor.execute("DROP TABLE accounts")

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
        conn.commit()


_init_db_sync()


# -------------------------------------------------------------
# Relational Async Database API
# -------------------------------------------------------------

async def async_write_account(name: str, account_dict: Dict[str, Any]) -> None:
    """Save account balance, strategy, holdings, and transactions into normalized relational tables."""
    acc_name = name.lower().strip()
    balance_str = str(account_dict.get("balance", "100000.00"))
    strategy = account_dict.get("strategy", "")
    holdings = account_dict.get("holdings", {})
    transactions = account_dict.get("transactions", [])
    history = account_dict.get("portfolio_value_time_series", [])

    async with aiosqlite.connect(DB) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")

        # Upsert account row
        await db.execute("""
            INSERT INTO accounts (name, balance, strategy)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                balance=excluded.balance,
                strategy=excluded.strategy
        """, (acc_name, balance_str, strategy))

        # Replace holdings
        await db.execute("DELETE FROM holdings WHERE account_name = ?", (acc_name,))
        for sym, qty in holdings.items():
            if qty > 0:
                await db.execute("""
                    INSERT INTO holdings (account_name, symbol, quantity)
                    VALUES (?, ?, ?)
                """, (acc_name, sym.upper(), qty))

        # Replace transactions
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

        # Replace portfolio history
        await db.execute("DELETE FROM portfolio_history WHERE account_name = ?", (acc_name,))
        for ts_entry in history:
            if isinstance(ts_entry, (list, tuple)) and len(ts_entry) == 2:
                await db.execute("""
                    INSERT INTO portfolio_history (account_name, timestamp, portfolio_value)
                    VALUES (?, ?, ?)
                """, (acc_name, str(ts_entry[0]), str(ts_entry[1])))

        await db.commit()


async def async_read_account(name: str) -> Optional[Dict[str, Any]]:
    """Query normalized relational tables to reconstruct account payload."""
    acc_name = name.lower().strip()
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT balance, strategy FROM accounts WHERE name = ?", (acc_name,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            balance_str, strategy = row

        # Fetch holdings
        holdings = {}
        async with db.execute("SELECT symbol, quantity FROM holdings WHERE account_name = ?", (acc_name,)) as cursor:
            async for sym, qty in cursor:
                holdings[sym] = qty

        # Fetch transactions
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

        # Fetch portfolio history
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


# -------------------------------------------------------------
# Synchronous Helper API (Relational DB)
# -------------------------------------------------------------

def write_account(name: str, account_dict: Dict[str, Any]) -> None:
    acc_name = name.lower().strip()
    balance_str = str(account_dict.get("balance", "100000.00"))
    strategy = account_dict.get("strategy", "")
    holdings = account_dict.get("holdings", {})
    transactions = account_dict.get("transactions", [])
    history = account_dict.get("portfolio_value_time_series", [])

    with sqlite3.connect(DB) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")

        conn.execute("""
            INSERT INTO accounts (name, balance, strategy)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                balance=excluded.balance,
                strategy=excluded.strategy
        """, (acc_name, balance_str, strategy))

        conn.execute("DELETE FROM holdings WHERE account_name = ?", (acc_name,))
        for sym, qty in holdings.items():
            if qty > 0:
                conn.execute("""
                    INSERT INTO holdings (account_name, symbol, quantity)
                    VALUES (?, ?, ?)
                """, (acc_name, sym.upper(), qty))

        conn.execute("DELETE FROM transactions WHERE account_name = ?", (acc_name,))
        for t in transactions:
            conn.execute("""
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

        conn.execute("DELETE FROM portfolio_history WHERE account_name = ?", (acc_name,))
        for ts_entry in history:
            if isinstance(ts_entry, (list, tuple)) and len(ts_entry) == 2:
                conn.execute("""
                    INSERT INTO portfolio_history (account_name, timestamp, portfolio_value)
                    VALUES (?, ?, ?)
                """, (acc_name, str(ts_entry[0]), str(ts_entry[1])))

        conn.commit()


def read_account(name: str) -> Optional[Dict[str, Any]]:
    acc_name = name.lower().strip()
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT balance, strategy FROM accounts WHERE name = ?", (acc_name,))
        row = cursor.fetchone()
        if not row:
            return None
        balance_str, strategy = row

        cursor.execute("SELECT symbol, quantity FROM holdings WHERE account_name = ?", (acc_name,))
        holdings = {sym: qty for sym, qty in cursor.fetchall()}

        cursor.execute("""
            SELECT symbol, quantity, price, timestamp, rationale 
            FROM transactions 
            WHERE account_name = ? 
            ORDER BY id ASC
        """, (acc_name,))
        transactions = [{
            "symbol": sym,
            "quantity": qty,
            "price": price_str,
            "timestamp": ts,
            "rationale": rationale
        } for sym, qty, price_str, ts, rationale in cursor.fetchall()]

        cursor.execute("""
            SELECT timestamp, portfolio_value 
            FROM portfolio_history 
            WHERE account_name = ? 
            ORDER BY id ASC
        """, (acc_name,))
        history = [(ts, float(val_str)) for ts, val_str in cursor.fetchall()]

        return {
            "name": acc_name,
            "balance": balance_str,
            "strategy": strategy,
            "holdings": holdings,
            "transactions": transactions,
            "portfolio_value_time_series": history
        }


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
