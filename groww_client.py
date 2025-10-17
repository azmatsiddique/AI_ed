"""
groww_client.py
Wrapper around the Groww Python SDK for Groww (growwapi).
This file provides safe fallbacks if the SDK is not installed, so the project
can still run in a dev environment without live Groww credentials.
Environment variables:
- GROWW_API_TOKEN : the Groww access token (preferred)
- GROWW_API_KEY / GROWW_API_SECRET / GROWW_TOTP_SECRET : for alternative auth flows
"""

import os
import time
from typing import Any, Dict, List, Optional

GROWW_TOKEN = os.environ.get("GROWW_API_TOKEN")

try:
    from growwapi import GrowwAPI, GrowwFeed
    SDK_AVAILABLE = True
except Exception as e:
    GrowwAPI = None  # type: ignore
    GrowwFeed = None  # type: ignore
    SDK_AVAILABLE = False

class GrowwClientWrapper:
    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or GROWW_TOKEN
        self.groww = None
        if SDK_AVAILABLE and self.access_token:
            try:
                self.groww = GrowwAPI(self.access_token)
            except Exception as e:
                # SDK failed to initialize in current environment
                self.groww = None

    def available(self) -> bool:
        return SDK_AVAILABLE and self.groww is not None

    def get_quote(self, exchange: str, segment: str, trading_symbol: str) -> Dict[str, Any]:
        """Get a live quote for a single instrument. Returns Groww SDK dict or
        a simple fallback structure when the SDK is not present."""
        if self.available():
            return self.groww.get_quote(exchange=self.groww.__dict__.get('EXCHANGE_'+exchange, exchange),
                                       segment=self.groww.__dict__.get('SEGMENT_'+segment, segment),
                                       trading_symbol=trading_symbol)
        # fallback (mock)
        ts = int(time.time() * 1000)
        return {
            "last_price": 100.0,
            "day_change_perc": 0.0,
            "ltp": 100.0,
            "last_trade_time": ts
        }

    def get_ltp(self, segment: str, exchange_trading_symbols) -> Dict[str, float]:
        if self.available():
            return self.groww.get_ltp(segment=segment, exchange_trading_symbols=exchange_trading_symbols)
        # fallback
        if isinstance(exchange_trading_symbols, (list, tuple)):
            return {s: 100.0 for s in exchange_trading_symbols}
        return {exchange_trading_symbols: 100.0}

    def get_holdings_for_user(self, timeout: int = 5) -> Dict[str, Any]:
        if self.available():
            return self.groww.get_holdings_for_user(timeout=timeout)
        return {"holdings": []}

    def get_positions_for_user(self):
        if self.available():
            return self.groww.get_positions_for_user()
        return {"positions": []}

    def get_historical_candles(self, exchange: str, segment: str, groww_symbol: str,
                              start_time: str, end_time: str, candle_interval: Any):
        if self.available():
            return self.groww.get_historical_candles(exchange=exchange, segment=segment,
                                                    groww_symbol=groww_symbol, start_time=start_time,
                                                    end_time=end_time, candle_interval=candle_interval)
        return {"candles": []}

    def feed_subscribe_ltp(self, instruments_list, on_data_received=None):
        if not SDK_AVAILABLE or not self.groww:
            raise RuntimeError("Groww SDK not available in this environment.")
        feed = GrowwFeed(self.groww)
        feed.subscribe_ltp(instruments_list, on_data_received=on_data_received)
        return feed

# Export a singleton client
client = GrowwClientWrapper()
