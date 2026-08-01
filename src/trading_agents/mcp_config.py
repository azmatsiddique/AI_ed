# src/agents/mcp_config.py
import os
from dotenv import load_dotenv

load_dotenv(override=False)

GROWW_API_KEY = os.getenv("GROWW_API_KEY")

# If you have a Groww MCP package (unlikely public), you could switch to uvx similar to polygon.
# Otherwise we use the local Python market_server (uv run src/mcp_servers/market_server.py)
market_mcp = {"command": "uv", "args": ["run", "-m", "src.mcp_servers.market_server"]}

def get_trader_mcp_server_params():
    use_groww = os.getenv("USE_GROWW", "true").lower() in ("true", "1", "yes")
    use_indmoney = os.getenv("USE_INDMONEY", "true").lower() in ("true", "1", "yes")
    use_moomoo = os.getenv("USE_MOOMOO", "true").lower() in ("true", "1", "yes")

    params = [
        {"command": "uv", "args": ["run", "-m", "src.mcp_servers.accounts_server"]},
        {"command": "uv", "args": ["run", "-m", "src.mcp_servers.push_server"]},
        {"command": "uv", "args": ["run", "-m", "src.mcp_servers.pinchtab_server"]},
    ]

    if use_indmoney:
        params.append({"command": "uv", "args": ["run", "-m", "src.mcp_servers.indmoney_server"]})

    if use_moomoo:
        params.append({"command": "uv", "args": ["run", "-m", "src.mcp_servers.moomoo_server"]})

    if use_groww:
        params.append(market_mcp)

    return params

# For backward compatibility
trader_mcp_server_params = get_trader_mcp_server_params()

# Researcher MCP server params using PinchTab browser automation (no API key required)
def researcher_mcp_server_params(name: str):
    return [
        {"command": "uv", "args": ["run", "-m", "src.mcp_servers.researcher_server"]},
        {"command": "uvx", "args": ["mcp-server-fetch"]},
        {
            "command": "npx",
            "args": ["-y", "mcp-memory-libsql"],
            "env": {"LIBSQL_URL": f"file:./memory/{name}.db"},
        },
    ]
