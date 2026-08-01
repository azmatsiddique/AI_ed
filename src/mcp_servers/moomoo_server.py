"""
moomoo_server.py
MCP server providing Moomoo API Skills tools for AI trading agents.
"""

from mcp.server.fastmcp import FastMCP
from src.utils.moomoo_client import MoomooClient

# Initialize Moomoo MCP server
mcp = FastMCP("moomoo")
client = MoomooClient()


@mcp.tool()
def moomoo_get_stock_quote(symbol: str) -> dict:
    """
    Retrieve real-time market snapshot, last price, and 52-week range for US or Global stocks from Moomoo.
    
    Args:
        symbol: Stock ticker symbol (e.g. "US.AAPL", "AAPL", "US.TSLA", "US.NVDA")
    """
    return client.get_stock_quote(symbol)


@mcp.tool()
def moomoo_get_account_positions() -> dict:
    """
    Retrieve Moomoo trading account assets, cash balance, and portfolio positions.
    """
    return client.get_account_positions()


@mcp.tool()
def moomoo_place_order(symbol: str, qty: int, side: str = "BUY") -> dict:
    """
    Place a paper trading or live trade order on Moomoo platform.
    
    Args:
        symbol: Ticker symbol (e.g. "US.AAPL", "US.TSLA")
        qty: Order quantity (number of shares)
        side: Order side ("BUY" or "SELL")
    """
    return client.place_order(symbol, qty=qty, side=side)


if __name__ == "__main__":
    mcp.run()
