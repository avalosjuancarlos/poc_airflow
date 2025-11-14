"""
Unit tests for technical indicators
"""

import pandas as pd
import pytest

from dags.market_data.transformers.technical_indicators import (
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_moving_averages,
    calculate_rsi,
    calculate_technical_indicators,
)


class TestCalculateMovingAverages:
    """Test calculate_moving_averages function"""

    def test_moving_averages_basic(self):
        """Test basic moving average calculation"""
        df = pd.DataFrame(
            {
                "date": pd.date_range("2023-11-01", periods=30),
                "close": range(100, 130),
            }
        )

        result = calculate_moving_averages(df, periods=[7, 14, 20])

        assert "sma_7" in result.columns
        assert "sma_14" in result.columns
        assert "sma_20" in result.columns

        # SMA_7 should have 6 NaN values at start
        assert result["sma_7"].isna().sum() == 6

    def test_moving_averages_custom_periods(self):
        """Test with custom periods"""
        df = pd.DataFrame(
            {"date": pd.date_range("2023-11-01", periods=50), "close": range(100, 150)}
        )

        result = calculate_moving_averages(df, periods=[5, 10])

        assert "sma_5" in result.columns
        assert "sma_10" in result.columns
        assert "sma_7" not in result.columns

    def test_moving_averages_values(self):
        """Test moving average calculated values"""
        # Simple case: constant values
        df = pd.DataFrame({"close": [10] * 20})

        result = calculate_moving_averages(df, periods=[5])

        # SMA of constant values should equal the value
        assert result["sma_5"].iloc[-1] == 10.0


class TestCalculateRSI:
    """Test calculate_rsi function"""

    def test_rsi_basic(self):
        """Test basic RSI calculation"""
        df = pd.DataFrame(
            {"date": pd.date_range("2023-11-01", periods=30), "close": range(100, 130)}
        )

        result = calculate_rsi(df, period=14)

        assert "rsi" in result.columns
        # RSI should be between 0 and 100
        valid_rsi = result["rsi"].dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_rsi_uptrend(self):
        """Test RSI in uptrend (should be > 50)"""
        # Consistent uptrend
        df = pd.DataFrame({"close": range(100, 150)})

        result = calculate_rsi(df, period=14)

        # In uptrend, RSI should be above 50
        assert result["rsi"].iloc[-1] > 50

    def test_rsi_period(self):
        """Test RSI with different periods"""
        df = pd.DataFrame({"close": range(100, 150)})

        result = calculate_rsi(df, period=10)

        assert "rsi" in result.columns
        # With period=10, should have 9 NaN values at start
        assert result["rsi"].isna().sum() >= 9


class TestCalculateEMA:
    """Test calculate_ema function"""

    def test_ema_basic(self):
        """Test basic EMA calculation"""
        df = pd.DataFrame({"close": range(100, 120)})

        result = calculate_ema(df, period=12)

        assert isinstance(result, pd.Series)
        assert len(result) == len(df)

    def test_ema_values(self):
        """Test EMA values are reasonable"""
        df = pd.DataFrame({"close": [100] * 20})

        result = calculate_ema(df, period=10)

        # EMA of constant values should converge to the value
        assert abs(result.iloc[-1] - 100.0) < 0.01


class TestCalculateMACD:
    """Test calculate_macd function"""

    def test_macd_basic(self):
        """Test basic MACD calculation"""
        df = pd.DataFrame(
            {"date": pd.date_range("2023-11-01", periods=50), "close": range(100, 150)}
        )

        result = calculate_macd(df)

        assert "macd" in result.columns
        assert "macd_signal" in result.columns
        assert "macd_histogram" in result.columns

    def test_macd_histogram(self):
        """Test MACD histogram calculation"""
        df = pd.DataFrame({"close": range(100, 150)})

        result = calculate_macd(df)

        # Histogram should be MACD - Signal
        calculated_histogram = result["macd"] - result["macd_signal"]
        pd.testing.assert_series_equal(
            result["macd_histogram"], calculated_histogram, check_names=False
        )

    def test_macd_custom_periods(self):
        """Test MACD with custom periods"""
        df = pd.DataFrame({"close": range(100, 150)})

        result = calculate_macd(df, fast_period=10, slow_period=20, signal_period=5)

        assert "macd" in result.columns
        # Should have values
        assert result["macd"].notna().sum() > 0


class TestCalculateBollingerBands:
    """Test calculate_bollinger_bands function"""

    def test_bollinger_bands_basic(self):
        """Test basic Bollinger Bands calculation"""
        df = pd.DataFrame(
            {"date": pd.date_range("2023-11-01", periods=30), "close": range(100, 130)}
        )

        result = calculate_bollinger_bands(df, period=20)

        assert "bb_upper" in result.columns
        assert "bb_middle" in result.columns
        assert "bb_lower" in result.columns

    def test_bollinger_bands_relationship(self):
        """Test Bollinger Bands upper > middle > lower"""
        df = pd.DataFrame({"close": range(100, 150)})

        result = calculate_bollinger_bands(df, period=20, num_std=2.0)

        # Drop NaN values
        valid_data = result.dropna(subset=["bb_upper", "bb_middle", "bb_lower"])

        # Upper should be > middle > lower
        assert (valid_data["bb_upper"] >= valid_data["bb_middle"]).all()
        assert (valid_data["bb_middle"] >= valid_data["bb_lower"]).all()

    def test_bollinger_bands_width(self):
        """Test Bollinger Bands width with different std"""
        df = pd.DataFrame({"close": range(100, 150)})

        result1 = calculate_bollinger_bands(df, period=20, num_std=1.0)
        result2 = calculate_bollinger_bands(df, period=20, num_std=2.0)

        # With 2 std, bands should be wider
        width1 = (result1["bb_upper"] - result1["bb_lower"]).iloc[-1]
        width2 = (result2["bb_upper"] - result2["bb_lower"]).iloc[-1]

        assert width2 > width1


class TestCalculateTechnicalIndicators:
    """Test calculate_technical_indicators main function"""

    def test_full_calculation(self):
        """Test complete indicator calculation"""
        metadata = {
            "long_name": "Apple Inc.",
            "short_name": "Apple",
            "fifty_two_week_high": 200.0,
            "fifty_two_week_low": 120.0,
        }

        market_data_list = [
            {
                "date": "2023-11-01",
                "ticker": "AAPL",
                "quote": {
                    "open": 100.0,
                    "high": 102.0,
                    "low": 99.0,
                    "close": 101.0,
                    "volume": 1000000,
                },
                "metadata": metadata,
            },
            {
                "date": "2023-11-02",
                "ticker": "AAPL",
                "quote": {
                    "open": 101.0,
                    "high": 103.0,
                    "low": 100.0,
                    "close": 102.0,
                    "volume": 1100000,
                },
                "metadata": metadata,
            },
        ]

        # Need more data for meaningful indicators
        for i in range(2, 30):
            market_data_list.append(
                {
                    "date": f"2023-11-{i+1:02d}",
                    "ticker": "AAPL",
                    "quote": {
                        "open": 100.0 + i,
                        "high": 102.0 + i,
                        "low": 99.0 + i,
                        "close": 101.0 + i,
                        "volume": 1000000 + i * 10000,
                    },
                    "metadata": metadata,
                }
            )

        result = calculate_technical_indicators(market_data_list, "AAPL")

        # Check all expected columns exist
        expected_cols = [
            "date",
            "ticker",
            "close",
            "sma_7",
            "sma_14",
            "sma_20",
            "ema_12",
            "rsi",
            "macd",
            "macd_signal",
            "macd_histogram",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "daily_return",
            "daily_return_pct",
            "volatility_20d",
            "long_name",
            "short_name",
            "fifty_two_week_high",
            "fifty_two_week_low",
        ]

        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

        # Check data integrity
        assert len(result) == 30
        assert result["ticker"].iloc[0] == "AAPL"

        # EMA 12 should have numeric values (allow NaNs for initial rows)
        assert result["ema_12"].notna().sum() > 0

        # Metadata columns should be populated
        assert result["long_name"].iloc[-1] == metadata["long_name"]
        assert result["short_name"].iloc[-1] == metadata["short_name"]

    def test_sorted_by_date(self):
        """Test that result is sorted by date"""
        market_data_list = [
            {"date": "2023-11-05", "ticker": "AAPL", "quote": {"close": 105.0}},
            {"date": "2023-11-03", "ticker": "AAPL", "quote": {"close": 103.0}},
            {"date": "2023-11-04", "ticker": "AAPL", "quote": {"close": 104.0}},
        ]

        result = calculate_technical_indicators(market_data_list, "AAPL")

        # Should be sorted
        assert result["date"].iloc[0] == pd.Timestamp("2023-11-03")
        assert result["date"].iloc[1] == pd.Timestamp("2023-11-04")
        assert result["date"].iloc[2] == pd.Timestamp("2023-11-05")

    def test_missing_required_column(self):
        """Test error handling for missing columns"""
        market_data_list = [{"date": "2023-11-01", "ticker": "AAPL"}]  # No close price

        with pytest.raises(ValueError, match="Missing required columns"):
            calculate_technical_indicators(market_data_list, "AAPL")
