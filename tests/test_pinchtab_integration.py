"""
test_pinchtab_integration.py
Test PinchTab integration with AI Trading Floor.
"""

import sys
from src.utils.pinchtab_client import PinchtabClient
from src.mcp_servers.pinchtab_server import pinchtab_get_status, pinchtab_browse_url

def test_pinchtab_client():
    print("--- 1. Testing PinchtabClient ---")
    client = PinchtabClient()
    healthy = client.is_healthy()
    print(f"PinchTab Health: {healthy}")
    assert healthy, "PinchTab daemon is not healthy!"

    status = client.get_status()
    print(f"PinchTab Status Version: {status.get('version')}, Security Level: {status.get('security', {}).get('level')}")

def test_pinchtab_navigation():
    print("\n--- 2. Testing PinchTab Web Navigation & Extraction ---")
    client = PinchtabClient()
    res = client.browse_and_extract("https://moneycontrol.com")
    print(f"Navigated URL: {res.get('url')}")
    print(f"Title: {res.get('title')}")
    print(f"Extracted Text Snippet:\n{res.get('text', '')[:200]}...")
    assert "status" in res and res["status"] == "success", "Failed to browse URL!"

def test_mcp_tools():
    print("\n--- 3. Testing PinchTab MCP Tools ---")
    status_mcp = pinchtab_get_status()
    print(f"MCP Status Output: {status_mcp.get('status')}")
    assert status_mcp.get("status") == "ok", "MCP tool pinchtab_get_status failed!"

if __name__ == "__main__":
    try:
        test_pinchtab_client()
        test_pinchtab_navigation()
        test_mcp_tools()
        print("\n✅ All PinchTab Integration Tests Passed Successfully!")
    except Exception as e:
        print(f"\n❌ Integration Test Failed: {e}")
        sys.exit(1)
