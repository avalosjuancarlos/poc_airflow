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


def _extract_ohlcv_from_quotes(df: pd.DataFrame) -> pd.DataFrame:
    """Expand OHLCV values from the nested quote payload."""
    logger.info(f"DataFrame columns before extraction: {list(df.columns)}")
    logger.debug(
        f"Sample quote data: {df['quote'].iloc[0] if 'quote' in df.columns and len(df) > 0 else 'No quote column'}"
    )

    if "quote" not in df.columns:
        logger.warning("'quote' column not found in DataFrame")
        return df

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

    logger.debug(f"Extracted close values (first 3): {df['close'].head(3).tolist()}")
    return df


def _flatten_metadata_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten metadata dict into explicit columns if present."""
    if "metadata" not in df.columns:
        return df

    logger.info("Flattening metadata fields into top-level columns")

    def safe_meta_value(meta_obj, key):
        if isinstance(meta_obj, dict):
            return meta_obj.get(key)
        return None

    df["fifty_two_week_high"] = df["metadata"].apply(
        lambda meta: safe_meta_value(meta, "fifty_two_week_high")
    )
    df["fifty_two_week_low"] = df["metadata"].apply(
        lambda meta: safe_meta_value(meta, "fifty_two_week_low")
    )
    df["long_name"] = df["metadata"].apply(
        lambda meta: safe_meta_value(meta, "long_name")
    )
    df["short_name"] = df["metadata"].apply(
        lambda meta: safe_meta_value(meta, "short_name")
    )

    logger.debug(
        "Flattened metadata added",
        extra={
            "long_name_sample": df["long_name"].dropna().head(1).tolist(),
            "short_name_sample": df["short_name"].dropna().head(1).tolist(),
        },
    )
    return df


def _convert_numeric_columns(df: pd.DataFrame, columns: List[str]) -> None:
    """Convert selected columns to numeric, logging before/after counts."""
    for col in columns:
        if col in df.columns:
            before_count = df[col].notna().sum()
            df[col] = pd.to_numeric(df[col], errors="coerce")
            after_count = df[col].notna().sum()
            logger.debug(
                f"Column '{col}': {before_count} → {after_count} non-null values after conversion"
            )


def _validate_required_columns(df: pd.DataFrame, required: List[str]) -> None:
    """Ensure required columns are present."""
    missing_columns = [col for col in required if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")


def _ensure_close_prices_exist(df: pd.DataFrame) -> None:
    """Ensure there are valid close prices."""
    valid_close_count = df["close"].notna().sum()
    if valid_close_count == 0:
        raise ValueError("No valid 'close' prices found in data")

    logger.info(
        f"Data validation: {valid_close_count}/{len(df)} records with valid close prices"
    )


def _filter_valid_closes(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows without close price and log how many were removed."""
    records_before_filter = len(df)
    df = df[df["close"].notna()].copy().reset_index(drop=True)
    records_after_filter = len(df)

    if records_before_filter > records_after_filter:
        logger.info(
            f"Filtered out {records_before_filter - records_after_filter} records with NaN close prices (weekends/holidays)"
        )

    return df


def _merge_with_historical_data(
    df: pd.DataFrame, historical_df: pd.DataFrame | None
) -> pd.DataFrame:
    """Merge fresh data with historical Parquet if provided."""
    if historical_df is None or len(historical_df) == 0:
        return df

    logger.info(
        f"Merging {len(df)} new records with {len(historical_df)} historical records"
    )

    historical_df = historical_df.copy()
    historical_df["date"] = pd.to_datetime(historical_df["date"])
    new_dates = df["date"].values
    historical_df = historical_df[~historical_df["date"].isin(new_dates)]

    df = pd.concat([historical_df, df], ignore_index=True)
    df = df.sort_values("date").reset_index(drop=True)

    logger.info(
        f"Combined dataset: {len(df)} total records from {df['date'].min()} to {df['date'].max()}"
    )
    return df


def _calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Run the full indicator pipeline and derived metrics."""
    logger.info("Calculating moving averages...")
    df = calculate_moving_averages(df, periods=[7, 14, 20])

    logger.info("Calculating EMA (12)...")
    df["ema_12"] = calculate_ema(df, period=12)

    logger.info("Calculating RSI...")
    df = calculate_rsi(df, period=14)

    logger.info("Calculating MACD...")
    df = calculate_macd(df)

    logger.info("Calculating Bollinger Bands...")
    df = calculate_bollinger_bands(df)

    logger.info("Calculating daily returns...")
    df["daily_return"] = df["close"].pct_change()
    df["daily_return_pct"] = df["daily_return"] * 100
    df["volatility_20d"] = df["daily_return"].rolling(window=20).std() * 100

    return df


def _log_indicator_summary(df: pd.DataFrame, ticker: str) -> None:
    """Emit summary logs and metrics after indicator calculation."""
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
                "ema_12",
                "rsi",
                "macd",
                "bollinger_bands",
                "daily_return",
                "volatility",
            ],
        },
    )

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
    market_data_list: List[Dict], ticker: str, historical_df: pd.DataFrame = None
) -> pd.DataFrame:
    """
    Calculate comprehensive technical indicators from market data

    This function can work in two modes:
    1. Backfill mode (historical_df=None): Calculate indicators on new data only
    2. Incremental mode (historical_df provided): Merge with historical data and
       recalculate ALL indicators on complete dataset for accuracy

    Args:
        market_data_list: List of market data dictionaries (new data)
        ticker: Stock ticker symbol
        historical_df: Optional existing historical data to merge with

    Returns:
        DataFrame with all technical indicators calculated on complete dataset
    """
    logger.info(f"Starting technical indicators calculation for {ticker}")
    logger.set_context(ticker=ticker, records=len(market_data_list))

    df = pd.DataFrame(market_data_list)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    logger.info(
        f"Processing {len(df)} records from {df['date'].min()} to {df['date'].max()}"
    )

    df = _extract_ohlcv_from_quotes(df)
    df = _flatten_metadata_columns(df)
    _convert_numeric_columns(df, ["open", "high", "low", "close", "volume"])
    _validate_required_columns(df, ["date", "close"])
    _ensure_close_prices_exist(df)
    df = _filter_valid_closes(df)
    df = _merge_with_historical_data(df, historical_df)
    df = _calculate_all_indicators(df)
    _log_indicator_summary(df, ticker)

    logger.clear_context()

    return df
