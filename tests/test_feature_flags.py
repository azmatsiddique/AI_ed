"""
test_feature_flags.py
Test USE_GROWW and USE_INDMONEY feature flag behavior across market routing and MCP server loading.
"""

import os
import sys

def test_feature_flags():
    print("--- 1. Testing Feature Flag MCP Server Registration ---")
    
    # Test both enabled
    os.environ["USE_GROWW"] = "true"
    os.environ["USE_INDMONEY"] = "true"
    
    import importlib
    import src.trading_agents.mcp_config as mcp_config
    importlib.reload(mcp_config)
    
    server_commands = [item.get("args", [])[-1] for item in mcp_config.get_trader_mcp_server_params() if "args" in item]
    print(f"Active MCP Servers (Both Enabled): {server_commands}")
    assert "src.mcp_servers.indmoney_server" in server_commands, "indmoney_server missing when USE_INDMONEY=true!"
    assert "src.mcp_servers.market_server" in server_commands, "market_server missing when USE_GROWW=true!"

    # Test Groww disabled
    os.environ["USE_GROWW"] = "false"
    os.environ["USE_INDMONEY"] = "true"
    importlib.reload(mcp_config)
    
    server_commands_no_groww = [item.get("args", [])[-1] for item in mcp_config.get_trader_mcp_server_params() if "args" in item]
    print(f"Active MCP Servers (Groww Disabled): {server_commands_no_groww}")
    assert "src.mcp_servers.market_server" not in server_commands_no_groww, "market_server present when USE_GROWW=false!"

    # Test INDmoney disabled
    os.environ["USE_GROWW"] = "true"
    os.environ["USE_INDMONEY"] = "false"
    importlib.reload(mcp_config)
    
    server_commands_no_ind = [item.get("args", [])[-1] for item in mcp_config.get_trader_mcp_server_params() if "args" in item]
    print(f"Active MCP Servers (INDmoney Disabled): {server_commands_no_ind}")
    assert "src.mcp_servers.indmoney_server" not in server_commands_no_ind, "indmoney_server present when USE_INDMONEY=false!"

    # Reset both to true
    os.environ["USE_GROWW"] = "true"
    os.environ["USE_INDMONEY"] = "true"
    importlib.reload(mcp_config)

def test_price_routing():
    print("\n--- 2. Testing Market Share Price Routing ---")
    import src.core.market as market
    import importlib
    importlib.reload(market)
    
    price = market.get_share_price("RELIANCE")
    print(f"Price for RELIANCE with feature flags enabled: ₹{price:,.2f}")
    assert price > 0, "Failed to calculate share price!"

if __name__ == "__main__":
    try:
        test_feature_flags()
        test_price_routing()
        print("\n✅ All Feature Flag Tests Passed Successfully!")
    except Exception as e:
        print(f"\n❌ Feature Flag Test Failed: {e}")
        sys.exit(1)
