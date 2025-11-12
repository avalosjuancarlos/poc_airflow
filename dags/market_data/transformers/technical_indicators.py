"""
Technical Indicators Calculator

Calculates various technical indicators for financial data analysis:
- Moving Averages (SMA, EMA)
- RSI (Relative Strength Index)
- Bollinger Bands
- MACD (Moving Average Convergence Divergence)
"""

from typing import Dict, List

import pandas as pd
from market_data.utils import get_logger

logger = get_logger(__name__)


def calculate_moving_averages(
    df: pd.DataFrame, periods: List[int] = [7, 14, 20]
) -> pd.DataFrame:
    """
    Calculate Simple Moving Averages (SMA)

    Args:
        df: DataFrame with 'close' column
        periods: List of periods for moving averages

    Returns:
        DataFrame with additional SMA columns
    """
    logger.info(f"Calculating moving averages for periods: {periods}")

    df_result = df.copy()

    for period in periods:
        column_name = f"sma_{period}"
        df_result[column_name] = df_result["close"].rolling(window=period).mean()
        logger.debug(f"Calculated {column_name}")

    logger.audit(
        "moving_averages_calculated",
        {"periods": periods, "rows": len(df_result)},
    )

    return df_result


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate Relative Strength Index (RSI)

    Args:
        df: DataFrame with 'close' column
        period: Period for RSI calculation (default: 14)

    Returns:
        DataFrame with 'rsi' column added
    """
    logger.info(f"Calculating RSI with period {period}")

    df_result = df.copy()

    # Calculate price changes
    delta = df_result["close"].diff()

    # Separate gains and losses
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

    # Calculate RS and RSI
    rs = gain / loss
    df_result["rsi"] = 100 - (100 / (1 + rs))

    logger.debug(
        f"RSI calculation complete. Non-null values: {df_result['rsi'].notna().sum()}"
    )
    logger.audit("rsi_calculated", {"period": period, "rows": len(df_result)})

    return df_result


def calculate_ema(df: pd.DataFrame, period: int = 12) -> pd.Series:
    """
    Calculate Exponential Moving Average (EMA)

    Args:
        df: DataFrame with 'close' column
        period: Period for EMA

    Returns:
        Series with EMA values
    """
    return df["close"].ewm(span=period, adjust=False).mean()


def calculate_macd(
    df: pd.DataFrame,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> pd.DataFrame:
    """
    Calculate MACD (Moving Average Convergence Divergence)

    Args:
        df: DataFrame with 'close' column
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line period (default: 9)

    Returns:
        DataFrame with 'macd', 'macd_signal', 'macd_histogram' columns
    """
    logger.info(f"Calculating MACD ({fast_period}, {slow_period}, {signal_period})")

    df_result = df.copy()

    # Calculate MACD line
    ema_fast = calculate_ema(df_result, fast_period)
    ema_slow = calculate_ema(df_result, slow_period)
    df_result["macd"] = ema_fast - ema_slow

    # Calculate signal line
    df_result["macd_signal"] = (
        df_result["macd"].ewm(span=signal_period, adjust=False).mean()
    )

    # Calculate histogram
    df_result["macd_histogram"] = df_result["macd"] - df_result["macd_signal"]

    logger.audit(
        "macd_calculated",
        {
            "fast": fast_period,
            "slow": slow_period,
            "signal": signal_period,
            "rows": len(df_result),
        },
    )

    return df_result


def calculate_bollinger_bands(
    df: pd.DataFrame, period: int = 20, num_std: float = 2.0
) -> pd.DataFrame:
    """
    Calculate Bollinger Bands

    Args:
        df: DataFrame with 'close' column
        period: Period for SMA (default: 20)
        num_std: Number of standard deviations (default: 2.0)

    Returns:
        DataFrame with 'bb_upper', 'bb_middle', 'bb_lower' columns
    """
    logger.info(f"Calculating Bollinger Bands (period={period}, std={num_std})")

    df_result = df.copy()

    # Middle band (SMA)
    df_result["bb_middle"] = df_result["close"].rolling(window=period).mean()

    # Standard deviation
    std = df_result["close"].rolling(window=period).std()

    # Upper and lower bands
    df_result["bb_upper"] = df_result["bb_middle"] + (std * num_std)
    df_result["bb_lower"] = df_result["bb_middle"] - (std * num_std)

    logger.audit(
        "bollinger_bands_calculated",
        {"period": period, "std_dev": num_std, "rows": len(df_result)},
    )

    return df_result


def calculate_technical_indicators(
    market_data_list: List[Dict], ticker: str
) -> pd.DataFrame:
    """
    Calculate comprehensive technical indicators from market data

    Args:
        market_data_list: List of market data dictionaries
        ticker: Stock ticker symbol

    Returns:
        DataFrame with all technical indicators calculated
    """
    logger.info(f"Starting technical indicators calculation for {ticker}")
    logger.set_context(ticker=ticker, records=len(market_data_list))

    # Convert to DataFrame
    df = pd.DataFrame(market_data_list)

    # Sort by date
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    logger.info(
        f"Processing {len(df)} records from {df['date'].min()} to {df['date'].max()}"
    )

    # Extract OHLCV data
    if "quote" in df.columns:
        df["open"] = df["quote"].apply(
            lambda x: x.get("open") if isinstance(x, dict) else None
        )
        df["high"] = df["quote"].apply(
            lambda x: x.get("high") if isinstance(x, dict) else None
        )
        df["low"] = df["quote"].apply(
            lambda x: x.get("low") if isinstance(x, dict) else None
        )
        df["close"] = df["quote"].apply(
            lambda x: x.get("close") if isinstance(x, dict) else None
        )
        df["volume"] = df["quote"].apply(
            lambda x: x.get("volume") if isinstance(x, dict) else None
        )

    # Convert OHLCV columns to numeric (handle None/invalid values)
    numeric_columns = ["open", "high", "low", "close", "volume"]
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Basic data validation
    required_columns = ["date", "close"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # Check for valid close prices
    valid_close_count = df["close"].notna().sum()
    if valid_close_count == 0:
        raise ValueError("No valid 'close' prices found in data")

    logger.info(
        f"Data validation: {valid_close_count}/{len(df)} records with valid close prices"
    )

    # Calculate indicators
    logger.info("Calculating moving averages...")
    df = calculate_moving_averages(df, periods=[7, 14, 20])

    logger.info("Calculating RSI...")
    df = calculate_rsi(df, period=14)

    logger.info("Calculating MACD...")
    df = calculate_macd(df)

    logger.info("Calculating Bollinger Bands...")
    df = calculate_bollinger_bands(df)

    # Add derived metrics
    logger.info("Calculating daily returns...")
    df["daily_return"] = df["close"].pct_change()
    df["daily_return_pct"] = df["daily_return"] * 100

    # Calculate volatility (20-day rolling)
    df["volatility_20d"] = df["daily_return"].rolling(window=20).std() * 100

    # Log summary statistics
    logger.info(
        "Technical indicators calculated successfully",
        extra={
            "ticker": ticker,
            "total_rows": len(df),
            "date_range": f"{df['date'].min()} to {df['date'].max()}",
            "indicators": [
                "sma_7",
                "sma_14",
                "sma_20",
                "rsi",
                "macd",
                "bollinger_bands",
                "daily_return",
                "volatility",
            ],
        },
    )

    # Log metrics
    latest_close = df["close"].iloc[-1] if len(df) > 0 else None
    latest_rsi = df["rsi"].iloc[-1] if len(df) > 0 else None

    if latest_close:
        logger.metric("indicators.close_price", latest_close, {"ticker": ticker})
    if latest_rsi:
        logger.metric("indicators.rsi", latest_rsi, {"ticker": ticker})

    logger.audit(
        "technical_indicators_completed",
        {
            "ticker": ticker,
            "rows_processed": len(df),
            "columns_added": 12,
            "date_range_days": (df["date"].max() - df["date"].min()).days,
        },
    )

    logger.clear_context()

    return df
