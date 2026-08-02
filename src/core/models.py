# src/core/models.py
"""Core data models for the trading system with pure async database persistence."""

import sys
import pathlib
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Union, Dict, List, Tuple
from decimal import Decimal, ROUND_HALF_UP

from .database import async_write_account, async_read_account, async_write_log
from .market import get_share_price
from ..utils.formatting import fmt_inr

root_dir = str(pathlib.Path(__file__).parent.parent.parent.resolve())
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    from groww_client import client as groww_client
except ModuleNotFoundError:
    groww_client = None

INITIAL_BALANCE = Decimal("100000.00")  # starting balance (₹100,000)
SPREAD = Decimal("0.002")  # 0.2% spread


def quantize_money(val: Union[Decimal, float, str, int]) -> Decimal:
    """Quantize financial values to 2 decimal places using standard ROUND_HALF_UP rounding."""
    if not isinstance(val, Decimal):
        val = Decimal(str(val))
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Transaction(BaseModel):
    """Represents a single trading transaction"""
    symbol: str
    quantity: int
    price: Decimal
    timestamp: str
    rationale: str

    def total(self) -> Decimal:
        """Calculate total transaction value"""
        return quantize_money(Decimal(self.quantity) * self.price)
    
    def __repr__(self):
        return f"{abs(self.quantity)} shares of {self.symbol} at {fmt_inr(self.price)} each."


class Account(BaseModel):
    """Represents a trader's account with holdings and transaction history"""
    name: str
    balance: Decimal
    strategy: str
    holdings: Dict[str, int]
    transactions: List[Transaction]
    portfolio_value_time_series: List[Tuple[str, float]]
    live_balance: Optional[Decimal] = None

    @classmethod
    async def get(cls, name: str) -> "Account":
        """Get or create an account asynchronously by name."""
        fields = await async_read_account(name.lower())
        if not fields:
            fields = {
                "name": name.lower(),
                "balance": INITIAL_BALANCE,
                "strategy": "",
                "holdings": {},
                "transactions": [],
                "portfolio_value_time_series": []
            }
            await async_write_account(name, fields)
        
        # Populate real Groww wallet balance separately if available without overwriting DB balance
        if groww_client and groww_client.available():
            fields["live_balance"] = Decimal(str(groww_client.get_wallet_balance()))
            
        return cls(**fields)
    
    async def save(self) -> None:
        """Persist account asynchronously to database."""
        await async_write_account(self.name.lower(), self.model_dump(mode="json"))

    async def reset(self, strategy: str) -> None:
        """Reset account asynchronously to initial state with new strategy."""
        self.balance = INITIAL_BALANCE
        self.strategy = strategy
        self.holdings = {}
        self.transactions = []
        self.portfolio_value_time_series = []
        await self.save()

    async def deposit(self, amount: Union[Decimal, float, str, int]) -> None:
        """Deposit funds into the account asynchronously."""
        dec_amount = quantize_money(amount)
        if dec_amount <= Decimal("0"):
            raise ValueError("Deposit amount must be positive.")
        self.balance = quantize_money(self.balance + dec_amount)
        msg = f"Deposited {fmt_inr(dec_amount)}. New balance: {fmt_inr(self.balance)}"
        print(msg)
        await async_write_log(self.name, "account", msg)
        await self.save()

    async def withdraw(self, amount: Union[Decimal, float, str, int]) -> None:
        """Withdraw funds asynchronously from the account."""
        dec_amount = quantize_money(amount)
        if dec_amount > self.balance:
            raise ValueError("Insufficient funds for withdrawal.")
        self.balance = quantize_money(self.balance - dec_amount)
        msg = f"Withdrew {fmt_inr(dec_amount)}. New balance: {fmt_inr(self.balance)}"
        print(msg)
        await async_write_log(self.name, "account", msg)
        await self.save()

    async def buy_shares(self, symbol: str, quantity: int, rationale: str) -> str:
        """Buy shares of a stock asynchronously if sufficient funds are available."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        raw_price = get_share_price(symbol)
        if raw_price == 0:
            raise ValueError(f"Unrecognized symbol {symbol}")
        price = quantize_money(raw_price)
        buy_price = quantize_money(price * (Decimal("1") + SPREAD))
        total_cost = quantize_money(buy_price * Decimal(quantity))
        
        if total_cost > self.balance:
            raise ValueError("Insufficient funds to buy shares.")
        
        self.holdings[symbol] = self.holdings.get(symbol, 0) + quantity
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        transaction = Transaction(
            symbol=symbol, 
            quantity=quantity, 
            price=buy_price, 
            timestamp=timestamp, 
            rationale=rationale
        )
        self.transactions.append(transaction)
        self.balance = quantize_money(self.balance - total_cost)
        await self.save()
        await async_write_log(self.name, "account", f"Bought {quantity} of {symbol} @ {fmt_inr(buy_price)} for {fmt_inr(total_cost)}")
        return "Completed. Latest details:\n" + await self.report()

    async def sell_shares(self, symbol: str, quantity: int, rationale: str) -> str:
        """Sell shares of a stock asynchronously if enough shares are held."""
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        holding_qty = self.holdings.get(symbol, 0)
        if holding_qty < quantity:
            raise ValueError(f"Cannot sell {quantity} shares of {symbol}. Not enough shares held.")
        
        raw_price = get_share_price(symbol)
        price = quantize_money(raw_price)
        sell_price = quantize_money(price * (Decimal("1") - SPREAD))
        total_proceeds = quantize_money(sell_price * Decimal(quantity))
        
        self.holdings[symbol] = holding_qty - quantity
        if self.holdings[symbol] == 0:
            del self.holdings[symbol]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        transaction = Transaction(
            symbol=symbol, 
            quantity=-quantity, 
            price=sell_price, 
            timestamp=timestamp, 
            rationale=rationale
        )
        self.transactions.append(transaction)

        self.balance = quantize_money(self.balance + total_proceeds)
        await self.save()
        await async_write_log(self.name, "account", f"Sold {quantity} of {symbol} @ {fmt_inr(sell_price)} for {fmt_inr(total_proceeds)}")
        return "Completed. Latest details:\n" + await self.report()

    def calculate_portfolio_value(self) -> Decimal:
        """Calculate the total value of the user's portfolio."""
        total_value = self.balance
        for symbol, quantity in self.holdings.items():
            stock_price = quantize_money(get_share_price(symbol))
            total_value += stock_price * Decimal(quantity)
        return quantize_money(total_value)

    def calculate_profit_loss(self, portfolio_value: Decimal) -> Decimal:
        """Calculate profit or loss from the initial spend."""
        initial_spend = sum((t.price * Decimal(t.quantity)) for t in self.transactions if t.quantity > 0)
        sales_proceeds = sum((-t.price * Decimal(t.quantity)) for t in self.transactions if t.quantity < 0)
        net_spent = initial_spend - sales_proceeds
        return quantize_money(portfolio_value - net_spent)

    def get_holdings(self) -> dict[str, int]:
        """Report current holdings."""
        return self.holdings

    def get_profit_loss(self) -> float:
        """Report current profit/loss as float."""
        pv = self.calculate_portfolio_value()
        return float(self.calculate_profit_loss(pv))

    def list_transactions(self) -> list[dict]:
        """List all transactions as dicts."""
        return [transaction.model_dump(mode="json") for transaction in self.transactions]
    
    async def report(self) -> str:
        """Return a json string representing the account asynchronously."""
        import json
        portfolio_value = self.calculate_portfolio_value()
        pv_float = float(portfolio_value)
        self.portfolio_value_time_series.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pv_float))
        await self.save()
        pnl = self.calculate_profit_loss(portfolio_value)
        data = self.model_dump(mode="json")
        data["total_portfolio_value"] = pv_float
        data["total_profit_loss"] = float(pnl)
        await async_write_log(self.name, "account", f"Retrieved account details: {fmt_inr(portfolio_value)} / P&L {fmt_inr(pnl)}")
        return json.dumps(data)
    
    async def get_strategy(self) -> str:
        """Return account strategy asynchronously."""
        await async_write_log(self.name, "account", "Retrieved strategy")
        return self.strategy
    
    async def change_strategy(self, strategy: str) -> str:
        """Change investment strategy asynchronously."""
        self.strategy = strategy
        await self.save()
        await async_write_log(self.name, "account", "Changed strategy")
        return "Changed strategy"
