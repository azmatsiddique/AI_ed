# database.py
import sqlite3
import json
from datetime import datetime
from dotenv import load_dotenv
import threading

load_dotenv(override=True)

DB = "accounts.db"
_DB_LOCK = threading.Lock()

def _conn():
    # allow access from different threads/processes in simple deployments
    return sqlite3.connect(DB, check_same_thread=False)

with _conn() as conn:
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS accounts (name TEXT PRIMARY KEY, account TEXT)')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            datetime TEXT,
            type TEXT,
            message TEXT
        )
    ''')
    cursor.execute('CREATE TABLE IF NOT EXISTS market (date TEXT PRIMARY KEY, data TEXT)')
    conn.commit()

def write_account(name, account_dict):
    json_data = json.dumps(account_dict)
    with _DB_LOCK:
        with _conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO accounts (name, account)
                VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET account=excluded.account
            ''', (name.lower(), json_data))
            conn.commit()

def read_account(name):
    with _DB_LOCK:
        with _conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT account FROM accounts WHERE name = ?', (name.lower(),))
            row = cursor.fetchone()
            return json.loads(row[0]) if row else None
    
def write_log(name: str, type: str, message: str):
    now = datetime.now().isoformat()
    with _DB_LOCK:
        with _conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO logs (name, datetime, type, message)
                VALUES (?, ?, ?, ?)
            ''', (name.lower(), now, type, message))
            conn.commit()

def read_log(name: str, last_n=10):
    with _DB_LOCK:
        with _conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT datetime, type, message FROM logs 
                WHERE name = ? 
                ORDER BY datetime DESC
                LIMIT ?
            ''', (name.lower(), last_n))
            return reversed(cursor.fetchall())

def write_market(date: str, data: dict) -> None:
    data_json = json.dumps(data)
    with _DB_LOCK:
        with _conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO market (date, data)
                VALUES (?, ?)
                ON CONFLICT(date) DO UPDATE SET data=excluded.data
            ''', (date, data_json))
            conn.commit()

def read_market(date: str) -> dict | None:
    with _DB_LOCK:
        with _conn() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT data FROM market WHERE date = ?', (date,))
            row = cursor.fetchone()
            return json.loads(row[0]) if row else None
