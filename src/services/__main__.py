# src/services/__main__.py
"""Entry point for running the trading floor"""

import asyncio
from .trading_floor import run_every_n_minutes, RUN_EVERY_N_MINUTES

if __name__ == "__main__":
    print(f"Starting scheduler to run every {RUN_EVERY_N_MINUTES} minutes")
    asyncio.run(run_every_n_minutes())
