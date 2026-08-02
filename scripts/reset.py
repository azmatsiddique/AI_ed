# scripts/reset.py
"""Reset trader accounts using TRADER_CONFIGS and pure async Account methods."""

import asyncio
from src.core.database import setup_database
from src.core.models import Account
from src.utils.config import TRADER_CONFIGS


async def reset_traders():
    """Reset all registered trader accounts asynchronously."""
    await setup_database()
    for cfg in TRADER_CONFIGS:
        acc = await Account.get(cfg.name)
        await acc.reset(cfg.strategy)
        print(f"Reset account '{cfg.name}' successfully.")


if __name__ == "__main__":
    asyncio.run(reset_traders())
