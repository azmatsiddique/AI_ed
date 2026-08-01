# src/trading_agents/mcp_config.py
"""MCP server registration configuration for trading agents."""

from src.utils.config import settings

# Base market MCP server runner
market_mcp = {"command": "uv", "args": ["run", "-m", "src.mcp_servers.market_server"]}


def get_trader_mcp_server_params():
    """Build list of active MCP server configurations based on centralized settings."""
    params = [
        {"command": "uv", "args": ["run", "-m", "src.mcp_servers.accounts_server"]},
        {"command": "uv", "args": ["run", "-m", "src.mcp_servers.push_server"]},
        {"command": "uv", "args": ["run", "-m", "src.mcp_servers.pinchtab_server"]},
    ]

    # Dynamically register optional market integration servers
    params.append({"command": "uv", "args": ["run", "-m", "src.mcp_servers.indmoney_server"]})
    params.append({"command": "uv", "args": ["run", "-m", "src.mcp_servers.moomoo_server"]})
    params.append(market_mcp)

    return params


# Backward compatibility binding
trader_mcp_server_params = get_trader_mcp_server_params()


def researcher_mcp_server_params(name: str):
    """Researcher MCP server parameters backed by PinchTab browser automation."""
    return [
        {"command": "uv", "args": ["run", "-m", "src.mcp_servers.researcher_server"]},
        {"command": "uvx", "args": ["mcp-server-fetch"]},
        {
            "command": "npx",
            "args": ["-y", "mcp-memory-libsql"],
            "env": {"LIBSQL_URL": f"file:./memory/{name}.db"},
        },
    ]
