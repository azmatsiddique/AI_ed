# src/mcp_servers/__main__.py
"""Entry point for running MCP servers (primarily for testing)"""

if __name__ == "__main__":
    print("MCP servers should be started via their individual modules:")
    print("  uv run -m src.mcp_servers.accounts_server")
    print("  uv run -m src.mcp_servers.market_server")
    print("  uv run -m src.mcp_servers.push_server")
