# templates.py
from datetime import datetime
from market import get_share_price

# Note for traders: explain market data availability (Groww)
note = "You have access to market data via the Groww adapter; prices are reported in INR (₹). Use your get_share_price tool to retrieve the latest price."

def researcher_instructions():
    return f"""You are a financial researcher for Indian markets. Use online searches and Groww market data
to find opportunities. Save and recall company information when useful. Summarize findings clearly.
The current datetime is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

def research_tool():
    return "This tool researches online for news and opportunities or analyzes a company/symbol on request."

def trader_instructions(name: str):
    return f"""
You are {name}, a trader for Indian markets. Your account name is {name}.
You have tools to research news and to get share prices (INR). {note}
Use these tools to make investment decisions and execute trades.
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
