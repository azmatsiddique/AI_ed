"""
indmoney_server.py
MCP server providing INDmoney / INDstocks chart data and wallet balance tools.
"""

from mcp.server.fastmcp import FastMCP
from src.utils.indmoney_client import INDmoneyClient

# Initialize INDmoney MCP server
mcp = FastMCP("indmoney")
client = INDmoneyClient()


@mcp.tool()
def indmoney_get_wallet_balance() -> dict:
    """
    Retrieve wallet balance, margin, available cash, and total portfolio valuation from INDmoney / INDstocks.
    """
    return client.get_wallet_balance()


@mcp.tool()
def indmoney_get_chart_data(symbol: str, period: str = "1d") -> dict:
    """
    Retrieve stock chart data, OHLC price performance, and price trends for a symbol from INDmoney.
    
    Args:
        symbol: Stock symbol or company name (e.g. "RELIANCE", "TCS", "INFY", "TATAMOTORS")
        period: Time period for chart ("1d", "1w", "1m", "1y")
    """
    return client.get_stock_chart_data(symbol, period=period)


@mcp.tool()
def indmoney_get_stock_summary(symbol: str) -> dict:
    """
    Fetch comprehensive company overview, valuation metrics, and technical chart details from INDmoney.
    """
    return client.get_stock_summary(symbol)


if __name__ == "__main__":
    mcp.run()
