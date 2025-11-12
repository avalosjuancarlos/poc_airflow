"""
Validation utilities for Market Data
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def validate_ticker_format(ticker: Any) -> str:
    """
    Validate and normalize ticker symbol
    
    Args:
        ticker: Ticker symbol to validate
        
    Returns:
        Normalized ticker symbol (uppercase)
        
    Raises:
        ValueError: If ticker is invalid
        
    Example:
        >>> validate_ticker_format('aapl')
        'AAPL'
        >>> validate_ticker_format('GOOGL')
        'GOOGL'
    """
    if not isinstance(ticker, str):
        raise ValueError("Ticker must be a valid string")
    
    # Convert to uppercase
    ticker = ticker.strip().upper()
    
    # Basic validation
    if not ticker or len(ticker) == 0:
        raise ValueError("Ticker cannot be empty")
    
    if len(ticker) > 10:
        raise ValueError(f"Ticker too long: {ticker} (max 10 characters)")
    
    # Check for valid characters (alphanumeric and some special chars)
    if not all(c.isalnum() or c in ['.', '-', '^'] for c in ticker):
        raise ValueError(f"Invalid characters in ticker: {ticker}")
    
    logger.info(f"Ticker validated: {ticker}")
    return ticker


def validate_date_format(date_str: str) -> str:
    """
    Validate date format (YYYY-MM-DD)
    
    Args:
        date_str: Date string to validate
        
    Returns:
        Validated date string
        
    Raises:
        ValueError: If date format is invalid
        
    Example:
        >>> validate_date_format('2023-11-09')
        '2023-11-09'
    """
    from datetime import datetime
    
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str
    except ValueError as e:
        raise ValueError(f"Invalid date format '{date_str}'. Use YYYY-MM-DD format") from e

