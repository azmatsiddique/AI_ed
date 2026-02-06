# src/services/account_service.py
"""Service layer for account management operations"""

from typing import Optional
from ..core.models import Account


class AccountService:
    """Service layer for managing trader accounts"""
    
    @staticmethod
    def get_account(name: str) -> Account:
        """Get an account by name"""
        return Account.get(name)
    
    @staticmethod
    def create_account(name: str, strategy: str) -> Account:
        """Create a new account with initial strategy"""
        account = Account.get(name)
        account.reset(strategy)
        return account
    
    @staticmethod
    def execute_buy(name: str, symbol: str, quantity: int, rationale: str) -> str:
        """Execute a buy order for an account"""
        account = Account.get(name)
        return account.buy_shares(symbol, quantity, rationale)
    
    @staticmethod
    def execute_sell(name: str, symbol: str, quantity: int, rationale: str) -> str:
        """Execute a sell order for an account"""
        account = Account.get(name)
        return account.sell_shares(symbol, quantity, rationale)
    
    @staticmethod
    def get_portfolio_value(name: str) -> float:
        """Get the current portfolio value for an account"""
        account = Account.get(name)
        return account.calculate_portfolio_value()
    
    @staticmethod
    def get_profit_loss(name: str) -> float:
        """Get the profit/loss for an account"""
        account = Account.get(name)
        return account.get_profit_loss()
