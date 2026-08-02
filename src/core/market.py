# src/core/market.py
"""
Market data adapter with pluggable Provider Registry.
Zero special-case if-statements in core price lookups.
"""

from dataclasses import dataclass
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from functools import lru_cache
import logging
import os
import random
import requests
from typing import Dict, List, Optional, Union

import json
import pathlib

logger = logging.getLogger("market")

_price_cache: Dict[str, float] = {}
_CACHE_TTL_SECONDS = int(os.getenv("GROWW_CACHE_TTL_SECONDS", "5"))


def _load_instrument_config() -> Dict[str, Dict[str, str]]:
    """Load optional instrument exchange/asset_class mapping from configuration file."""
    config_paths = [
        pathlib.Path("config/instruments.json"),
        pathlib.Path(__file__).parent.parent.parent / "config" / "instruments.json",
    ]
    for p in config_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as exc:
                logger.warning(f"Failed to load instrument config from {p}: {exc}")
    return {}


_INSTRUMENT_CONFIG_MAPPING = _load_instrument_config()


@dataclass
class Instrument:
    """Structured financial instrument model specifying symbol, exchange, and asset class."""
    symbol: str
    exchange: str = "NSE"        # NSE, BSE, NASDAQ, NYSE, HKEX
    asset_class: str = "EQUITY"   # EQUITY, ETF, CRYPTO_ETF

    @classmethod
    def parse(cls, raw: Union[str, "Instrument"]) -> "Instrument":
        """Generic rule-based symbol parser with configurable mapping overrides."""
        if isinstance(raw, Instrument):
            return raw

        clean = raw.upper().strip()

        # 1. Configured mapping lookup
        if clean in _INSTRUMENT_CONFIG_MAPPING:
            cfg = _INSTRUMENT_CONFIG_MAPPING[clean]
            return cls(
                symbol=cfg.get("symbol", clean),
                exchange=cfg.get("exchange", "NSE"),
                asset_class=cfg.get("asset_class", "EQUITY"),
            )

        # 2. Explicit prefix rule: EXCHANGE:SYMBOL (e.g. NASDAQ:AAPL, HKEX:9988)
        if ":" in clean:
            prefix, sym = clean.split(":", 1)
            return cls(symbol=sym, exchange=prefix, asset_class="EQUITY")

        # 3. Market prefix rules (US. / HK.)
        if clean.startswith("US."):
            return cls(symbol=clean.replace("US.", ""), exchange="NASDAQ", asset_class="EQUITY")
        if clean.startswith("HK."):
            return cls(symbol=clean.replace("HK.", ""), exchange="HKEX", asset_class="EQUITY")

        # 4. Market suffix rules (.NS / .BO)
        if clean.endswith(".NS"):
            return cls(symbol=clean[:-3], exchange="NSE", asset_class="EQUITY")
        if clean.endswith(".BO"):
            return cls(symbol=clean[:-3], exchange="BSE", asset_class="EQUITY")

        # 5. Default generic rule
        return cls(symbol=clean, exchange="NSE", asset_class="EQUITY")


# Abstract Provider Interface
class MarketProvider(ABC):
    """Abstract interface for pluggable market data providers."""

    @abstractmethod
    def supports_instrument(self, inst: Instrument) -> bool:
        """Return True if this provider supports quote lookups for the given instrument."""
        pass

    @abstractmethod
    def get_price(self, inst: Instrument) -> Optional[float]:
        """Fetch current share price or return None if lookup fails/unconfigured."""
        pass


class INDmoneyProvider(MarketProvider):
    """INDmoney / INDstocks provider for US and Indian stock chart data."""

    def supports_instrument(self, inst: Instrument) -> bool:
        return True

    def get_price(self, inst: Instrument) -> Optional[float]:
        try:
            from src.utils.indmoney_client import INDmoneyClient
            ind_data = INDmoneyClient().get_stock_chart_data(inst.symbol)
            if ind_data.get("current_price") is not None:
                return float(ind_data["current_price"])
        except Exception as exc:
            logger.warning(f"INDmoney provider lookup failed for '{inst.symbol}': {exc}", exc_info=True)
        return None


class MoomooProvider(MarketProvider):
    """Moomoo OpenD API provider for US & Global stock quotes."""

    def supports_instrument(self, inst: Instrument) -> bool:
        return inst.exchange in {"NASDAQ", "NYSE", "HKEX"}

    def get_price(self, inst: Instrument) -> Optional[float]:
        try:
            from src.utils.moomoo_client import MoomooClient
            moo_symbol = f"US.{inst.symbol}" if inst.exchange in {"NASDAQ", "NYSE"} else f"HK.{inst.symbol}"
            moo_data = MoomooClient().get_stock_quote(moo_symbol)
            if moo_data.get("last_price") is not None and moo_data.get("last_price") > 0:
                return float(moo_data["last_price"])
        except Exception as exc:
            logger.warning(f"Moomoo provider lookup failed for '{inst.symbol}': {exc}", exc_info=True)
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

    def supports_instrument(self, inst: Instrument) -> bool:
        return inst.exchange in {"NSE", "BSE"}

    def get_price(self, inst: Instrument) -> Optional[float]:
        if not (self.api_key or self.token):
            return None
        try:
            url = f"{self.base_url}/market/v1/quotes"
            resp = requests.get(url, headers=self._headers(), params={"symbol": inst.symbol}, timeout=4)
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
            logger.warning(f"Groww provider lookup failed for '{inst.symbol}': {exc}", exc_info=True)
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


def get_share_price(symbol_or_inst: Union[str, Instrument]) -> float:
    """
    Zero-special-case market price resolver over active Provider Registry and Instrument model.
    Fails loudly with RuntimeError if live market data is unavailable.
    """
    inst = Instrument.parse(symbol_or_inst)
    cache_key = inst.symbol.upper().strip()
    now_ts = int(datetime.now(tz=timezone.utc).timestamp())

    cached = _price_cache.get(cache_key)
    if cached:
        ts, price = cached
        if now_ts - ts <= _CACHE_TTL_SECONDS:
            return price

    for provider in _PROVIDERS:
        if provider.supports_instrument(inst):
            price = provider.get_price(inst)
            if price is not None:
                _price_cache[cache_key] = (now_ts, price)
                return price

    logger.error(f"HARD MARKET FAILURE: All registered providers failed/unconfigured for '{cache_key}' (Exchange: {inst.exchange}).")
    raise RuntimeError(f"Live market quote unavailable for '{cache_key}'. Halting execution to prevent trading on unverified data.")


@lru_cache(maxsize=256)
def get_historical_close(symbol: str, date_iso: str) -> float:
    """
    Get historical close for symbol at date (YYYY-MM-DD).
    Fails loudly if provider history is unavailable.
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

    raise RuntimeError(f"Historical close price unavailable for '{symbol}' ({date_iso}).")


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
