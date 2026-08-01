# src/mcp_servers/accounts_server.py
"""FastMCP accounts server using pure async Account models."""

from mcp.server.fastmcp import FastMCP
from src.core.models import Account

mcp = FastMCP("accounts_server")


@mcp.tool()
async def get_balance(name: str) -> float:
    account = await Account.get(name)
    return float(account.balance)


@mcp.tool()
async def get_holdings(name: str) -> dict:
    account = await Account.get(name)
    return account.holdings


@mcp.tool()
async def buy_shares(name: str, symbol: str, quantity: int, rationale: str) -> str:
    account = await Account.get(name)
    return await account.buy_shares(symbol, quantity, rationale)


@mcp.tool()
async def sell_shares(name: str, symbol: str, quantity: int, rationale: str) -> str:
    account = await Account.get(name)
    return await account.sell_shares(symbol, quantity, rationale)


@mcp.tool()
async def change_strategy(name: str, strategy: str) -> str:
    account = await Account.get(name)
    return await account.change_strategy(strategy)


@mcp.resource("accounts://accounts_server/{name}")
async def read_account_resource(name: str) -> str:
    account = await Account.get(name.lower())
    return await account.report()


@mcp.resource("accounts://strategy/{name}")
async def read_strategy_resource(name: str) -> str:
    account = await Account.get(name.lower())
    return await account.get_strategy()


if __name__ == "__main__":
    mcp.run(transport='stdio')
