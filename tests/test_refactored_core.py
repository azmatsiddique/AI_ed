import unittest
import asyncio
from decimal import Decimal
from src.core.database import setup_database, async_write_account, async_read_account
from src.core.models import Account
from src.core.market import Instrument
from src.trading_agents.trader import get_balance, get_holdings, buy_shares, sell_shares, change_strategy


class TestRefactoredCore(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        await setup_database()

    async def test_database_setup_and_account_upsert(self):
        account_name = "test_trader"
        account_data = {
            "name": account_name,
            "balance": "100000.00",
            "strategy": "Value Investing",
            "holdings": {"AAPL": 10, "TSLA": 5},
            "transactions": [
                {
                    "symbol": "AAPL",
                    "quantity": 10,
                    "price": "150.00",
                    "timestamp": "2026-08-02 12:00:00",
                    "rationale": "Initial purchase"
                }
            ],
            "portfolio_value_time_series": [("2026-08-02 12:00:00", 100000.0)]
        }
        await async_write_account(account_name, account_data)

        # Re-read account
        read_data = await async_read_account(account_name)
        self.assertIsNotNone(read_data)
        self.assertEqual(read_data["name"], account_name)
        self.assertEqual(read_data["holdings"].get("AAPL"), 10)

        # Upsert account update without table wipes
        account_data["holdings"]["AAPL"] = 15
        await async_write_account(account_name, account_data)

        read_data_updated = await async_read_account(account_name)
        self.assertEqual(read_data_updated["holdings"].get("AAPL"), 15)

    async def test_account_model_isolation(self):
        acc = await Account.get("warren")
        self.assertEqual(acc.name, "warren")
        self.assertTrue(isinstance(acc.balance, Decimal))

    def test_instrument_parse_rules(self):
        # Config lookup / Prefix rules
        inst1 = Instrument.parse("US.AAPL")
        self.assertEqual(inst1.symbol, "AAPL")
        self.assertEqual(inst1.exchange, "NASDAQ")

        inst2 = Instrument.parse("HK.9988")
        self.assertEqual(inst2.symbol, "9988")
        self.assertEqual(inst2.exchange, "HKEX")

        inst3 = Instrument.parse("NASDAQ:TSLA")
        self.assertEqual(inst3.symbol, "TSLA")
        self.assertEqual(inst3.exchange, "NASDAQ")

        inst4 = Instrument.parse("RELIANCE.NS")
        self.assertEqual(inst4.symbol, "RELIANCE")
        self.assertEqual(inst4.exchange, "NSE")

        inst5 = Instrument.parse("CUSTOMSTOCK")
        self.assertEqual(inst5.symbol, "CUSTOMSTOCK")
        self.assertEqual(inst5.exchange, "NSE")

    async def test_native_account_tools(self):
        from agents.tool_context import ToolContext
        acc = await Account.get("tool_test_user")
        await acc.reset("Test Strategy")

        ctx_bal = ToolContext(None, tool_name="get_balance", tool_call_id="call_1", tool_arguments='{"name": "tool_test_user"}')
        bal = await get_balance.on_invoke_tool(ctx_bal, '{"name": "tool_test_user"}')
        self.assertEqual(bal, 100000.0)

        ctx_strat = ToolContext(None, tool_name="change_strategy", tool_call_id="call_2", tool_arguments='{"name": "tool_test_user", "strategy": "Growth"}')
        strat_res = await change_strategy.on_invoke_tool(ctx_strat, '{"name": "tool_test_user", "strategy": "Growth"}')
        self.assertEqual(strat_res, "Changed strategy")


if __name__ == "__main__":
    unittest.main()
