# src/utils/formatting.py
"""Formatting utilities for display"""


from decimal import Decimal
from typing import Union


def fmt_inr(amount: Union[float, Decimal, int, str]) -> str:
    """Format amount in INR with rupee symbol and thousands separators."""
    val = float(amount) if isinstance(amount, (Decimal, int, float, str)) else 0.0
    return f"₹{val:,.2f}"

