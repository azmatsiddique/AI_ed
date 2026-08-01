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

GROWW_TOKEN = os.environ.get("GROWW_API_TOKEN") or os.environ.get("GROWW_TOKEN")

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
        self._cached_balance = None
        self._last_balance_fetch_time = 0.0
        if SDK_AVAILABLE and self.access_token:
            try:
                self.groww = GrowwAPI(self.access_token)
            except Exception as e:
                # SDK failed to initialize in current environment
                self.groww = None

    def available(self) -> bool:
        return SDK_AVAILABLE and self.groww is not None

    def get_wallet_balance(self) -> float:
        """Fetch available clear cash from Groww margin details with caching."""
        current_time = time.time()
        # Cache for 30 seconds to avoid hitting rate limits and slowing down queries
        if self._cached_balance is not None and (current_time - self._last_balance_fetch_time < 30.0):
            return self._cached_balance

        if self.available():
            try:
                details = self.groww.get_available_margin_details()
                if isinstance(details, dict):
                    # Keys can vary; common ones are 'clear_cash', 'available_balance', 'cash', 'margin'
                    cash = (
                        details.get("clear_cash") or
                        details.get("available_balance") or
                        details.get("cash") or
                        details.get("margin") or
                        0.0
                    )
                    self._cached_balance = float(cash)
                    self._last_balance_fetch_time = current_time
                    return self._cached_balance
            except Exception as e:
                print(f"Error fetching Groww wallet balance: {e}")
                # Cache the error/fallback for 10 seconds so sequential reloads for other traders
                # do not trigger immediate failing network calls
                self._last_balance_fetch_time = current_time - 20.0
                if self._cached_balance is not None:
                    return self._cached_balance
        # fallback
        self._cached_balance = 100000.0
        self._last_balance_fetch_time = current_time
        return self._cached_balance


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
