# src/core/market.py
"""
Market data adapter with pluggable Provider Registry.
Zero special-case if-statements in core price lookups.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from functools import lru_cache
import logging
import os
import random
import requests
from typing import Dict, List, Optional

logger = logging.getLogger("market")

_price_cache: Dict[str, float] = {}
_CACHE_TTL_SECONDS = int(os.getenv("GROWW_CACHE_TTL_SECONDS", "5"))


def _format_fallback(symbol: str) -> float:
    """Deterministic fallback so test runs are repeatable across runs."""
    random.seed(symbol)
    return float(round(random.uniform(10.0, 1000.0), 2))


# Abstract Provider Interface
class MarketProvider(ABC):
    """Abstract interface for pluggable market data providers."""

    @abstractmethod
    def supports_symbol(self, symbol: str) -> bool:
        """Return True if this provider supports quote lookups for the given symbol."""
        pass

    @abstractmethod
    def get_price(self, symbol: str) -> Optional[float]:
        """Fetch current share price or return None if lookup fails/unconfigured."""
        pass


class INDmoneyProvider(MarketProvider):
    """INDmoney / INDstocks provider for US and Indian stock chart data."""

    def supports_symbol(self, symbol: str) -> bool:
        return True

    def get_price(self, symbol: str) -> Optional[float]:
        try:
            from src.utils.indmoney_client import INDmoneyClient
            ind_data = INDmoneyClient().get_stock_chart_data(symbol)
            if ind_data.get("current_price") is not None:
                return float(ind_data["current_price"])
        except Exception as exc:
            logger.warning(f"INDmoney provider lookup failed for '{symbol}': {exc}", exc_info=True)
        return None


class MoomooProvider(MarketProvider):
    """Moomoo OpenD API provider for US & Global stock quotes."""

    def supports_symbol(self, symbol: str) -> bool:
        clean = symbol.upper().strip()
        return clean.startswith("US.") or clean.startswith("HK.")

    def get_price(self, symbol: str) -> Optional[float]:
        try:
            from src.utils.moomoo_client import MoomooClient
            moo_data = MoomooClient().get_stock_quote(symbol)
            if moo_data.get("last_price") is not None and moo_data.get("last_price") > 0:
                return float(moo_data["last_price"])
        except Exception as exc:
            logger.warning(f"Moomoo provider lookup failed for '{symbol}': {exc}", exc_info=True)
        return None


class GrowwProvider(MarketProvider):
    """Groww EOD and realtime quote provider for Indian equities (NSE/BSE)."""

    def __init__(self):
        self.api_key = os.getenv("GROWW_API_KEY")
        self.base_url = os.getenv("GROWW_BASE_URL", "https://api.groww.in")
        self.token = os.getenv("GROWW_TOKEN")

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "azmat-trading/1.0"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def supports_symbol(self, symbol: str) -> bool:
        clean = symbol.upper().strip()
        return not (clean.startswith("US.") or clean.startswith("HK."))

    def get_price(self, symbol: str) -> Optional[float]:
        if not (self.api_key or self.token):
            return None
        try:
            url = f"{self.base_url}/market/v1/quotes"
            resp = requests.get(url, headers=self._headers(), params={"symbol": symbol}, timeout=4)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict):
                if "last_price" in data:
                    return float(data["last_price"])
                if "data" in data and isinstance(data["data"], dict) and "last_price" in data["data"]:
                    return float(data["data"]["last_price"])
                if "last" in data:
                    return float(data["last"])
        except Exception as exc:
            logger.warning(f"Groww provider lookup failed for '{symbol}': {exc}", exc_info=True)
        return None


def _build_provider_registry() -> List[MarketProvider]:
    """Dynamically register market providers based on feature flags."""
    registry = []
    if os.getenv("USE_INDMONEY", "true").lower() in ("true", "1", "yes"):
        registry.append(INDmoneyProvider())
    if os.getenv("USE_MOOMOO", "true").lower() in ("true", "1", "yes"):
        registry.append(MoomooProvider())
    if os.getenv("USE_GROWW", "true").lower() in ("true", "1", "yes"):
        registry.append(GrowwProvider())
    return registry


_PROVIDERS = _build_provider_registry()


def get_share_price(symbol: str) -> float:
    """
    Zero-special-case market price resolver over active Provider Registry.
    """
    cache_key = symbol.upper().strip()
    now_ts = int(datetime.now(tz=timezone.utc).timestamp())

    cached = _price_cache.get(cache_key)
    if cached:
        ts, price = cached
        if now_ts - ts <= _CACHE_TTL_SECONDS:
            return price

    for provider in _PROVIDERS:
        if provider.supports_symbol(cache_key):
            price = provider.get_price(cache_key)
            if price is not None:
                _price_cache[cache_key] = (now_ts, price)
                return price

    price = _format_fallback(cache_key)
    logger.warning(
        f"[SYNTHETIC FALLBACK USED] All registered providers failed/unconfigured for '{cache_key}'. "
        f"Generated fallback price: ₹{price}"
    )
    _price_cache[cache_key] = (now_ts, price)
    return price


@lru_cache(maxsize=256)
def get_historical_close(symbol: str, date_iso: str) -> float:
    """
    Get historical close for symbol at date (YYYY-MM-DD).
    """
    groww = GrowwProvider()
    if groww.supports_symbol(symbol):
        try:
            url = f"{groww.base_url}/market/v1/history"
            resp = requests.get(url, headers=groww._headers(), params={"symbol": symbol, "date": date_iso}, timeout=6)
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
    Return True if Indian equities market is open now (Mon-Fri 09:15-15:30 IST).
    """
    if now_utc is None:
        now_utc = datetime.now(tz=timezone.utc)

    ist = now_utc.astimezone(timezone(timedelta(hours=5, minutes=30)))
    if ist.weekday() >= 5:
        return False

    market_open = ist.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = ist.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= ist <= market_close
