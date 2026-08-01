"""
test_moomoo_integration.py
Test Moomoo API Skills integration with AI Trading Floor.
"""

import sys
from src.utils.moomoo_client import MoomooClient
from src.mcp_servers.moomoo_server import moomoo_get_stock_quote, moomoo_get_account_positions, moomoo_place_order


def test_moomoo_client():
    print("--- 1. Testing MoomooClient Quotes & Account ---")
    client = MoomooClient()
    quote = client.get_stock_quote("US.AAPL")
    print(f"Quote Result: {quote.get('status')}, Symbol: {quote.get('symbol')}, Source: {quote.get('source')}")
    assert quote.get("status") == "success", "Failed to retrieve Moomoo stock quote!"

    positions = client.get_account_positions()
    print(f"Positions Status: {positions.get('status')}, Source: {positions.get('source')}, Cash: ${positions.get('cash'):,.2f}")
    assert positions.get("status") == "success", "Failed to retrieve Moomoo account positions!"


def test_moomoo_mcp_tools():
    print("\n--- 2. Testing Moomoo MCP Server Tools ---")
    quote_mcp = moomoo_get_stock_quote("US.TSLA")
    print(f"MCP Quote for US.TSLA: {quote_mcp.get('symbol')}, Source: {quote_mcp.get('source')}")
    assert quote_mcp.get("status") == "success", "MCP tool moomoo_get_stock_quote failed!"

    pos_mcp = moomoo_get_account_positions()
    print(f"MCP Account Assets: ${pos_mcp.get('total_assets'):,.2f}")
    assert pos_mcp.get("status") == "success", "MCP tool moomoo_get_account_positions failed!"

    order_mcp = moomoo_place_order("US.NVDA", qty=5, side="BUY")
    print(f"MCP Order Result: Order ID {order_mcp.get('order_id')}, Side: {order_mcp.get('side')}")
    assert order_mcp.get("status") == "success", "MCP tool moomoo_place_order failed!"


if __name__ == "__main__":
    try:
        test_moomoo_client()
        test_moomoo_mcp_tools()
        print("\n✅ All Moomoo API Skills Integration Tests Passed Successfully!")
    except Exception as e:
        print(f"\n❌ Moomoo Integration Test Failed: {e}")
        sys.exit(1)
