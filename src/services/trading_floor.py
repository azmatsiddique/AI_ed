# src/services/trading_floor.py
"""Scheduler and runner for trading floor agents driven by TRADER_CONFIGS."""

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*HTTP_422_UNPROCESSABLE_ENTITY.*")

import asyncio
import logging
from typing import List

from ..trading_agents.trader import Trader
from ..utils.tracers import LogTracer
from ..utils.config import settings, TRADER_CONFIGS
from agents import add_trace_processor

try:
    from ..core.market import is_market_open as _is_market_open
except Exception:
    def _is_market_open() -> bool:
        return True

logger = logging.getLogger("trading_floor")

RUN_EVERY_N_MINUTES = settings.run_every_n_minutes
RUN_EVEN_WHEN_MARKET_IS_CLOSED = settings.run_even_when_market_is_closed


def create_traders() -> List[Trader]:
    """Create trader instances from central TRADER_CONFIGS registry."""
    return [Trader(cfg) for cfg in TRADER_CONFIGS]


async def run_every_n_minutes():
    """Run active traders on schedule with failure isolation."""
    add_trace_processor(LogTracer())
    traders = create_traders()
    while True:
        if RUN_EVEN_WHEN_MARKET_IS_CLOSED or _is_market_open():
            results = await asyncio.gather(*[trader.run() for trader in traders], return_exceptions=True)
            for trader, res in zip(traders, results):
                if isinstance(res, Exception):
                    logger.error(f"Trader '{trader.name}' encountered an isolated execution error: {res}", exc_info=res)
        else:
            print("Market is closed, skipping run")
        await asyncio.sleep(RUN_EVERY_N_MINUTES * 60)


if __name__ == "__main__":
    print(f"Starting scheduler to run every {RUN_EVERY_N_MINUTES} minutes")
    asyncio.run(run_every_n_minutes())
