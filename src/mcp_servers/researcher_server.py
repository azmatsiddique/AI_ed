"""
researcher_server.py
MCP server providing research and data intelligence tools via PinchTab browser automation.
No third-party search API keys (like Brave) required!
"""

from mcp.server.fastmcp import FastMCP
from src.utils.pinchtab_client import PinchtabClient

# Initialize MCP server
mcp = FastMCP("researcher")
pinchtab = PinchtabClient()


@mcp.tool()
def web_search(query: str, count: int = 5) -> dict:
    """
    Perform live web research and data extraction via PinchTab browser automation.
    No BRAVE_API_KEY required.
    """
    formatted_query = query.replace(" ", "+")
    search_url = f"https://www.google.com/search?q={formatted_query}"
    res = pinchtab.browse_and_extract(search_url)
    return {
        "query": query,
        "status": res.get("status", "success"),
        "source": "pinchtab_browser_daemon",
        "title": res.get("title", f"Web Search - {query}"),
        "content": res.get("text", "")[:1200]
    }


@mcp.tool()
def quick_insight(ticker: str) -> dict:
    """
    Quickly fetch recent market news and sentiment for a stock via PinchTab.
    """
    ticker_clean = ticker.upper().strip()
    news_url = f"https://www.moneycontrol.com/india/stockpricequote/{ticker_clean.lower()}"
    res = pinchtab.browse_and_extract(news_url)
    return {
        "ticker": ticker_clean,
        "status": res.get("status", "success"),
        "source": "pinchtab_moneycontrol",
        "title": res.get("title", f"Market Insight - {ticker_clean}"),
        "extracted_news": res.get("text", "")[:1200]
    }


if __name__ == "__main__":
    mcp.run()
