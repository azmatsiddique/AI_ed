"""
researcher_server.py
MCP server providing research and data intelligence tools.

This connects to the BRAVE Search API (via BRAVE_API_KEY) to help
agents or the UI perform enhanced data lookups, sentiment gathering,
and quick financial insights.

Each tool returns structured responses that can be used by AI agents
(e.g., traders, researchers) for decision support.
"""

import os
import requests
from mcp.server.fastmcp import FastMCP, Tool

BRAVE_API_KEY = os.environ.get("BRAVE_API_KEY", "")
BRAVE_URL = "https://api.search.brave.com/res/v1/web/search"

# Initialize MCP server
mcp = FastMCP("researcher")

@mcp.tool()
def web_search(query: str, count: int = 5) -> dict:
    """
    Perform a web search using the BRAVE API.
    Returns top search results with title, link, and snippet.
    """
    if not BRAVE_API_KEY:
        return {"error": "Missing BRAVE_API_KEY. Please set it in environment variables."}

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY,
    }
    params = {"q": query, "count": count}
    try:
        resp = requests.get(BRAVE_URL, headers=headers, params=params, timeout=10)
        data = resp.json()
        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "description": item.get("description"),
            })
        return {"query": query, "results": results}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def quick_insight(ticker: str) -> dict:
    """
    Quickly fetch recent web results about a stock or company to gauge sentiment.
    Example: quick_insight("RELIANCE")
    """
    q = f"{ticker} stock performance site:moneycontrol.com OR site:economictimes.indiatimes.com"
    return web_search(q, count=3)

if __name__ == "__main__":
    mcp.run()
