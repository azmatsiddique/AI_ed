# src/agents/templates.py
from datetime import datetime
from ..core.market import get_share_price

# Note for traders: explain market data availability (Groww)
note = "You have access to market data via the Groww adapter; prices are reported in INR (₹). Use your get_share_price tool to retrieve the latest price."

def researcher_instructions():
    return f"""You are a financial researcher for Indian markets. Use online searches and Groww market data
to find opportunities. Save and recall company information when useful. Summarize findings clearly.
The current datetime is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

def research_tool():
    return "This tool researches online for news and opportunities or analyzes a company/symbol on request."

import os

def trader_instructions(name: str):
    use_groww = os.getenv("USE_GROWW", "true").lower() in ("true", "1", "yes")
    use_indmoney = os.getenv("USE_INDMONEY", "true").lower() in ("true", "1", "yes")

    tools_list = [
        "1. Account & Portfolio Management (`get_account`, `buy_shares`, `sell_shares`).",
        "2. High-Performance Web Research via PinchTab (`pinchtab_browse_url`, `pinchtab_search_financial_news`, `pinchtab_get_status`)."
    ]
    if use_groww:
        tools_list.append(f"3. Live Market Data via Groww (`get_share_price`). {note}")
    if use_indmoney:
        tools_list.append("4. INDmoney / INDstocks Integration (`indmoney_get_chart_data`, `indmoney_get_wallet_balance`, `indmoney_get_stock_summary`).")

    formatted_tools = "\n".join(tools_list)
    return f"""
You are {name}, an autonomous AI trader operating in the Indian stock market. Your account name is {name}.
You have access to:
{formatted_tools}

Use these tools to analyze market opportunities, verify company news, inspect charts, and make informed trading decisions.
"""

def trade_message(name, strategy, account):
    return f"""Based on your investment strategy, find opportunities consistent with your strategy.
Use research and market tools (priced in INR) and then execute trades.
Strategy:
{strategy}
Account:
{account}
Current datetime: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

def rebalance_message(name, strategy, account):
    return f"""Examine and rebalance the portfolio using INR market data and your strategy.
Strategy:
{strategy}
Account:
{account}
Current datetime: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
