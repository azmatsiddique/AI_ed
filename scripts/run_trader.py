# scripts/run_trader.py
"""Standalone script for testing individual traders"""

import asyncio
from src.agents.trader import Trader


async def main():
    """Run a single trader for testing"""
    trader = Trader("Warren", "Patience", "gpt-4o-mini")
    await trader.run()


if __name__ == "__main__":
    print("Running individual trader test...")
    asyncio.run(main())
