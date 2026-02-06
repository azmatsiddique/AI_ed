# market.py
"""
Market data adapter for Groww (replaces Polygon).
- Uses GROWW_API_KEY (or GROWW_CLIENT_ID/GROWW_CLIENT_SECRET) via env.
- You must fill in actual Groww API endpoints / auth flow below.
- Falls back to a deterministic pseudo-random price if Groww isn't configured.
"""

from functools import lru_cache
from datetime import datetime, timezone, timedelta
import os
import random
import requests
from typing import Dict, Optional

GROWW_API_KEY = os.getenv("GROWW_API_KEY")  # primary key (if Groww provides one)
GROWW_BASE_URL = os.getenv("GROWW_BASE_URL", "https://api.groww.in")  # placeholder
GROWW_TOKEN = os.getenv("GROWW_TOKEN")  # if you have an oauth token

# small in-memory cache for realtime calls (non-persistent)
_price_cache: Dict[str, float] = {}
_CACHE_TTL_SECONDS = int(os.getenv("GROWW_CACHE_TTL_SECONDS", "5"))


def _format_fallback(symbol: str) -> float:
    """Deterministic fallback so test runs are repeatable across runs."""
    random.seed(symbol)
    return float(round(random.uniform(10.0, 1000.0), 2))


def _groww_headers() -> Dict[str, str]:
    """
    Return headers for Groww API calls. Adjust if Groww requires OAuth bearer token,
    client id + secret, or custom headers.
    """
    headers = {"Accept": "application/json", "User-Agent": "azmat-trading/1.0"}
    if GROWW_API_KEY:
        headers["x-api-key"] = GROWW_API_KEY
    if GROWW_TOKEN:
        headers["Authorization"] = f"Bearer {GROWW_TOKEN}"
    return headers


def _call_groww_quote_endpoint(symbol: str) -> Optional[float]:
    """
    Placeholder function to call Groww EOD or realtime quote endpoint.
    Replace the path with the correct Groww endpoint and query params.

    Example (fake):
        GET https://api.groww.in/market/v1/quotes?symbol={symbol}
        headers: x-api-key or Authorization
    """
    if not (GROWW_API_KEY or GROWW_TOKEN):
        return None

    try:
        url = f"{GROWW_BASE_URL}/market/v1/quotes"
        params = {"symbol": symbol}  # adjust param name if Groww uses different query key
        resp = requests.get(url, headers=_groww_headers(), params=params, timeout=4)
        resp.raise_for_status()
        data = resp.json()
        # === IMPORTANT: adapt these access paths to Groww's actual JSON ===
        # below is an example conversion that expects something like:
        # {"data": {"symbol": "RELIANCE", "last_price": 3540.25}}
        price = None
        if isinstance(data, dict):
            if "last_price" in data:
                price = float(data["last_price"])
            elif "data" in data and isinstance(data["data"], dict) and "last_price" in data["data"]:
                price = float(data["data"]["last_price"])
            # else try some other likely keys
            elif "last" in data:
                price = float(data["last"])
        return price
    except Exception:
        # don't raise in production — log externally if you have a logger
        return None


def get_share_price(symbol: str) -> float:
    """
    Returns current share price for symbol in INR.
    Attempts Groww realtime endpoint, falls back to cached EOD, then deterministic random.
    """
    # quick cache hit to avoid spamming provider
    cache_key = symbol.upper()
    now_ts = int(datetime.now(tz=timezone.utc).timestamp())

    # simple TTL cache using dict storing (timestamp, price)
    cached = _price_cache.get(cache_key)
    if cached:
        ts, price = cached
        if now_ts - ts <= _CACHE_TTL_SECONDS:
            return price

    # Try Groww realtime quote
    price = _call_groww_quote_endpoint(cache_key)
    if price is not None:
        _price_cache[cache_key] = (now_ts, price)
        return price

    # No Groww key or endpoint mismatch — fallback to deterministic pseudo-random
    price = _format_fallback(cache_key)
    _price_cache[cache_key] = (now_ts, price)
    return price


@lru_cache(maxsize=256)
def get_historical_close(symbol: str, date_iso: str) -> float:
    """
    Get historical close for symbol at date (YYYY-MM-DD). This will try a Groww EOD endpoint
    if available; otherwise returns fallback.
    """
    # In production replace with Groww's /history or /eod endpoint
    # Example placeholder: GET /market/v1/history?symbol={symbol}&date={date_iso}
    try:
        if not (GROWW_API_KEY or GROWW_TOKEN):
            raise RuntimeError("No Groww key present")

        url = f"{GROWW_BASE_URL}/market/v1/history"
        params = {"symbol": symbol, "date": date_iso}
        resp = requests.get(url, headers=_groww_headers(), params=params, timeout=6)
        resp.raise_for_status()
        payload = resp.json()
        # adapt to actual Groww payload:
        if isinstance(payload, dict):
            if "close" in payload:
                return float(payload["close"])
            if "data" in payload and isinstance(payload["data"], dict) and "close" in payload["data"]:
                return float(payload["data"]["close"])
    except Exception:
        # fallback deterministic
        pass
    return _format_fallback(symbol)


def is_market_open(now_utc: Optional[datetime] = None) -> bool:
    """
    Return True if Indian equities market is open now.

    Simplified rules:
    - Monday to Friday only
    - 09:15 to 15:30 India Standard Time (IST, UTC+5:30)
    - Does not account for exchange holidays or special sessions
    """
    if now_utc is None:
        now_utc = datetime.now(tz=timezone.utc)

    ist = now_utc.astimezone(timezone(timedelta(hours=5, minutes=30)))

    # 0=Mon, 6=Sun
    if ist.weekday() >= 5:
        return False

    market_open = ist.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = ist.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= ist <= market_close
