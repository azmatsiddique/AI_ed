"""
pinchtab_server.py
MCP server providing token-efficient browser automation and live web research capabilities
via PinchTab daemon.

This server enables AI agents (Warren, George, Ray, Cathie) to navigate financial news sites,
extract live article text, and analyze real-time market sentiment directly from the web.
"""

import urllib.parse
from mcp.server.fastmcp import FastMCP
from src.utils.pinchtab_client import PinchtabClient

# Initialize PinchTab MCP server
mcp = FastMCP("pinchtab")
client = PinchtabClient()


@mcp.tool()
def pinchtab_get_status() -> dict:
    """
    Check PinchTab browser daemon health and status.
    Returns status, version, profiles, and active Chrome instances.
    """
    return client.get_status()


@mcp.tool()
def pinchtab_browse_url(url: str) -> dict:
    """
    Navigate Chrome to a web page and extract token-efficient text content.
    Use this to read live news articles, financial reports, or stock commentary.
    
    Example URLs:
      - https://www.moneycontrol.com
      - https://economictimes.indiatimes.com/markets
      - https://www.livemint.com/market
    """
    if not client.is_healthy():
        return {"error": "PinchTab browser daemon is not running or unreachable on http://127.0.0.1:9867"}

    return client.browse_and_extract(url)


@mcp.tool()
def pinchtab_search_financial_news(ticker_or_topic: str, site: str = "moneycontrol.com") -> dict:
    """
    Perform targeted financial news research by navigating directly to stock/market pages on top Indian financial portals.
    
    Args:
        ticker_or_topic: Company ticker or market topic (e.g. "RELIANCE", "INFY", "RBI Repo Rate")
        site: Preferred news portal ("moneycontrol.com", "economictimes.indiatimes.com", "livemint.com")
    """
    if not client.is_healthy():
        return {"error": "PinchTab browser daemon is not running or unreachable"}

    search_url = f"https://www.google.com/search?q={urllib.parse.quote(ticker_or_topic + ' site:' + site)}"
    return client.browse_and_extract(search_url)


if __name__ == "__main__":
    mcp.run()
