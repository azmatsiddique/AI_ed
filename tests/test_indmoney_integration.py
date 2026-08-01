"""
test_indmoney_integration.py
Test INDmoney / INDstocks chart data and wallet balance integration.
"""

import sys
from src.utils.indmoney_client import INDmoneyClient
from src.mcp_servers.indmoney_server import indmoney_get_wallet_balance, indmoney_get_chart_data, indmoney_get_stock_summary


def test_indmoney_client():
    print("--- 1. Testing INDmoneyClient Wallet & Balance ---")
    client = INDmoneyClient()
    wallet = client.get_wallet_balance()
    print(f"Wallet Status: {wallet.get('status')}, Source: {wallet.get('source')}, Cash: ₹{wallet.get('available_cash'):,.2f}")
    assert wallet.get("status") == "success", "Failed to retrieve INDmoney wallet balance!"


def test_indmoney_chart_data():
    print("\n--- 2. Testing INDmoney Stock Chart Data ---")
    client = INDmoneyClient()
    chart_reliance = client.get_stock_chart_data("RELIANCE", period="1d")
    print(f"Symbol: {chart_reliance.get('symbol')}, Source: {chart_reliance.get('source')}")
    print(f"Chart Summary: {chart_reliance.get('chart_summary')}")
    assert chart_reliance.get("status") == "success", "Failed to retrieve stock chart data!"


def test_indmoney_mcp_tools():
    print("\n--- 3. Testing INDmoney MCP Server Tools ---")
    wallet_mcp = indmoney_get_wallet_balance()
    print(f"MCP Wallet Result: {wallet_mcp.get('status')} (Available: ₹{wallet_mcp.get('available_cash'):,.2f})")
    assert wallet_mcp.get("status") == "success", "MCP tool indmoney_get_wallet_balance failed!"

    chart_mcp = indmoney_get_chart_data("INFY")
    print(f"MCP Chart Result for INFY: {chart_mcp.get('symbol')}")
    assert chart_mcp.get("status") == "success", "MCP tool indmoney_get_chart_data failed!"


if __name__ == "__main__":
    try:
        test_indmoney_client()
        test_indmoney_chart_data()
        test_indmoney_mcp_tools()
        print("\n✅ All INDmoney Integration Tests Passed Successfully!")
    except Exception as e:
        print(f"\n❌ INDmoney Integration Test Failed: {e}")
        sys.exit(1)
