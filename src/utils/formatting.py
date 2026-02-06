# src/utils/formatting.py
"""Formatting utilities for display"""


def fmt_inr(amount: float) -> str:
    """Format amount in INR with rupee symbol and thousands separators."""
    return f"₹{amount:,.2f}"
