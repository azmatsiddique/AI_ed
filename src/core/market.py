# market.py
"""
Market data adapter for Groww (replaces Polygon).
- Uses GROWW_API_KEY (or GROWW_CLIENT_ID/GROWW_CLIENT_SECRET) via env.
- You must fill in actual Groww API endpoints / auth flow below.
- Falls back to a deterministic pseudo-random price if Groww isn't configured.
"""

import logging
from functools import lru_cache
from datetime import datetime, timezone, timedelta
import os
import random
import requests
from typing import Dict, Optional

logger = logging.getLogger("market")

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
    Call Groww EOD or realtime quote endpoint.
    """
    if not (GROWW_API_KEY or GROWW_TOKEN):
        return None

    try:
        url = f"{GROWW_BASE_URL}/market/v1/quotes"
        params = {"symbol": symbol}
        resp = requests.get(url, headers=_groww_headers(), params=params, timeout=4)
        resp.raise_for_status()
        data = resp.json()
        price = None
        if isinstance(data, dict):
            if "last_price" in data:
                price = float(data["last_price"])
            elif "data" in data and isinstance(data["data"], dict) and "last_price" in data["data"]:
                price = float(data["data"]["last_price"])
            elif "last" in data:
                price = float(data["last"])
        return price
    except Exception as exc:
        logger.warning(f"Groww quote endpoint request failed for symbol '{symbol}': {exc}", exc_info=True)
        return None


USE_GROWW = os.getenv("USE_GROWW", "true").lower() in ("true", "1", "yes")
USE_INDMONEY = os.getenv("USE_INDMONEY", "true").lower() in ("true", "1", "yes")
USE_MOOMOO = os.getenv("USE_MOOMOO", "true").lower() in ("true", "1", "yes")


def get_share_price(symbol: str) -> float:
    """
    Returns current share price for symbol in INR.
    Respects USE_INDMONEY, USE_MOOMOO, and USE_GROWW feature flags.
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

    # 1. Try Moomoo quote if USE_MOOMOO is enabled and symbol is US/Global
    if USE_MOOMOO and (cache_key.startswith("US.") or cache_key.startswith("HK.")):
        try:
            from src.utils.moomoo_client import MoomooClient
            moo_data = MoomooClient().get_stock_quote(cache_key)
            if moo_data.get("last_price") is not None and moo_data.get("last_price") > 0:
                price = float(moo_data["last_price"])
                _price_cache[cache_key] = (now_ts, price)
                return price
        except Exception as exc:
            logger.warning(f"Moomoo quote lookup failed for '{cache_key}': {exc}", exc_info=True)

    # 2. Try INDmoney quote if USE_INDMONEY is enabled
    if USE_INDMONEY:
        try:
            from src.utils.indmoney_client import INDmoneyClient
            ind_data = INDmoneyClient().get_stock_chart_data(cache_key)
            if ind_data.get("current_price") is not None:
                price = float(ind_data["current_price"])
                _price_cache[cache_key] = (now_ts, price)
                return price
        except Exception as exc:
            logger.warning(f"INDmoney chart quote lookup failed for '{cache_key}': {exc}", exc_info=True)

    # 3. Try Groww realtime quote if USE_GROWW is enabled
    if USE_GROWW:
        price = _call_groww_quote_endpoint(cache_key)
        if price is not None:
            _price_cache[cache_key] = (now_ts, price)
            return price

    # 4. Fallback to deterministic pseudo-random
    price = _format_fallback(cache_key)
    logger.warning(
        f"[SYNTHETIC FALLBACK USED] All live market APIs failed/unconfigured for '{cache_key}'. "
        f"Generated fallback price: ₹{price}"
    )
    _price_cache[cache_key] = (now_ts, price)
    return price


@lru_cache(maxsize=256)
def get_historical_close(symbol: str, date_iso: str) -> float:
    """
    Get historical close for symbol at date (YYYY-MM-DD).
    """
    try:
        if not (GROWW_API_KEY or GROWW_TOKEN):
            raise RuntimeError("No Groww API credentials configured.")

        url = f"{GROWW_BASE_URL}/market/v1/history"
        params = {"symbol": symbol, "date": date_iso}
        resp = requests.get(url, headers=_groww_headers(), params=params, timeout=6)
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, dict):
            if "close" in payload:
                return float(payload["close"])
            if "data" in payload and isinstance(payload["data"], dict) and "close" in payload["data"]:
                return float(payload["data"]["close"])
    except Exception as exc:
        logger.warning(f"Historical close request failed for '{symbol}' ({date_iso}): {exc}", exc_info=True)

    fallback_p = _format_fallback(symbol)
    logger.warning(f"[SYNTHETIC FALLBACK USED] Historical close for '{symbol}' fallback: ₹{fallback_p}")
    return fallback_p


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
