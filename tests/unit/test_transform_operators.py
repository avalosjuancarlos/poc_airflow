"""
Unit tests for transform operators
"""

import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from dags.market_data.operators.transform_operators import (
    check_and_determine_dates,
    fetch_multiple_dates,
    transform_and_save,
)


class TestCheckAndDetermineDates:
    """Test check_and_determine_dates operator"""

    def test_no_parquet_returns_backfill(self, mock_context):
        """Test returns 20 days when parquet doesn't exist"""
        mock_context["task_instance"].xcom_pull.return_value = "AAPL"
        mock_context["execution_date"] = datetime(2023, 11, 20)

        with patch(
            "dags.market_data.operators.transform_operators.check_parquet_exists",
            return_value=False,
        ):
            result = check_and_determine_dates(**mock_context)

        assert result["is_backfill"] is True
        assert len(result["dates"]) == 20
        assert result["ticker"] == "AAPL"
        # Should start 19 days before execution_date
        assert result["dates"][0] == "2023-11-01"
        assert result["dates"][-1] == "2023-11-20"

    def test_existing_parquet_returns_single_date(self, mock_context):
        """Test returns single date when parquet exists"""
        mock_context["task_instance"].xcom_pull.return_value = "AAPL"
        mock_context["execution_date"] = datetime(2023, 11, 20)

        with patch(
            "dags.market_data.operators.transform_operators.check_parquet_exists",
            return_value=True,
        ):
            result = check_and_determine_dates(**mock_context)

        assert result["is_backfill"] is False
        assert len(result["dates"]) == 1
        assert result["dates"][0] == "2023-11-20"
        assert result["ticker"] == "AAPL"

    def test_pushes_to_xcom(self, mock_context):
        """Test that result is pushed to XCom"""
        mock_context["task_instance"].xcom_pull.return_value = "AAPL"
        mock_context["execution_date"] = datetime(2023, 11, 20)

        with patch(
            "dags.market_data.operators.transform_operators.check_parquet_exists",
            return_value=False,
        ):
            result = check_and_determine_dates(**mock_context)

        # Verify xcom_push was called
        mock_context["task_instance"].xcom_push.assert_called_once()
        call_args = mock_context["task_instance"].xcom_push.call_args
        assert call_args[1]["key"] == "dates_to_process"
        assert call_args[1]["value"] == result


class TestFetchMultipleDates:
    """Test fetch_multiple_dates operator"""

    def test_fetch_multiple_dates_success(self, mock_context):
        """Test fetching multiple dates successfully"""
        dates_info = {
            "dates": ["2023-11-01", "2023-11-02", "2023-11-03"],
            "ticker": "AAPL",
            "is_backfill": True,
        }

        mock_context["task_instance"].xcom_pull.return_value = dates_info

        mock_client = MagicMock()
        mock_client.fetch_market_data.return_value = {
            "date": "2023-11-01",
            "ticker": "AAPL",
            "close": 100.0,
        }

        # Patch where it's used, not where it's defined
        with patch("market_data.operators.transform_operators.YahooFinanceClient", return_value=mock_client):
            result = fetch_multiple_dates(**mock_context)

        assert len(result) == 3
        assert mock_client.fetch_market_data.call_count == 3

    def test_fetch_continues_on_error(self, mock_context):
        """Test continues fetching even if some dates fail"""
        dates_info = {
            "dates": ["2023-11-01", "2023-11-02", "2023-11-03"],
            "ticker": "AAPL",
            "is_backfill": False,
        }

        mock_context["task_instance"].xcom_pull.return_value = dates_info

        mock_client = MagicMock()
        # First call fails, others succeed
        mock_client.fetch_market_data.side_effect = [
            Exception("API Error"),
            {"date": "2023-11-02", "close": 101.0},
            {"date": "2023-11-03", "close": 102.0},
        ]

        with patch("market_data.operators.transform_operators.YahooFinanceClient", return_value=mock_client):
            result = fetch_multiple_dates(**mock_context)

        # Should have 2 successful results (1 failed)
        assert len(result) == 2

    def test_fetch_all_fail_raises_error(self, mock_context):
        """Test raises error if all dates fail"""
        dates_info = {
            "dates": ["2023-11-01", "2023-11-02"],
            "ticker": "AAPL",
            "is_backfill": False,
        }

        mock_context["task_instance"].xcom_pull.return_value = dates_info

        mock_client = MagicMock()
        mock_client.fetch_market_data.side_effect = Exception("API Error")

        with patch("market_data.operators.transform_operators.YahooFinanceClient", return_value=mock_client):
            with pytest.raises(ValueError, match="Failed to fetch data for all"):
                fetch_multiple_dates(**mock_context)


class TestTransformAndSave:
    """Test transform_and_save operator"""

    def test_transform_and_save_success(self, mock_context):
        """Test successful transformation and save"""
        # Mock data
        market_data_list = []
        for i in range(30):
            market_data_list.append(
                {
                    "date": f"2023-11-{i+1:02d}",
                    "ticker": "AAPL",
                    "quote": {"close": 100.0 + i, "volume": 1000000},
                }
            )

        dates_info = {"ticker": "AAPL", "is_backfill": True}

        mock_context["task_instance"].xcom_pull.side_effect = [
            market_data_list,
            dates_info,
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch(
                "dags.market_data.operators.transform_operators.save_to_parquet"
            ) as mock_save:
                mock_save.return_value = f"{tmpdir}/AAPL_market_data.parquet"

                result = transform_and_save(**mock_context)

                assert result["ticker"] == "AAPL"
                assert result["rows_processed"] == 30
                assert "latest_indicators" in result
                mock_save.assert_called_once()

    def test_transform_calculates_indicators(self, mock_context):
        """Test that indicators are calculated"""
        market_data_list = []
        for i in range(30):
            market_data_list.append(
                {
                    "date": f"2023-11-{i+1:02d}",
                    "ticker": "AAPL",
                    "quote": {"close": 100.0 + i},
                }
            )

        dates_info = {"ticker": "AAPL", "is_backfill": True}
        mock_context["task_instance"].xcom_pull.side_effect = [
            market_data_list,
            dates_info,
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"MARKET_DATA_STORAGE_DIR": tmpdir}):
                result = transform_and_save(**mock_context)

                # Check that file was created
                file_path = result["file_path"]
                assert os.path.exists(file_path)

                # Load and verify indicators
                df = pd.read_parquet(file_path)
                assert "sma_7" in df.columns
                assert "sma_14" in df.columns
                assert "rsi" in df.columns
                assert "macd" in df.columns

    def test_transform_pushes_summary_to_xcom(self, mock_context):
        """Test that summary is pushed to XCom"""
        market_data_list = [
            {"date": "2023-11-01", "ticker": "AAPL", "quote": {"close": 100.0}},
            {"date": "2023-11-02", "ticker": "AAPL", "quote": {"close": 101.0}},
        ]

        dates_info = {"ticker": "AAPL", "is_backfill": False}
        mock_context["task_instance"].xcom_pull.side_effect = [
            market_data_list,
            dates_info,
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.dict(os.environ, {"MARKET_DATA_STORAGE_DIR": tmpdir}):
                transform_and_save(**mock_context)

                # Check xcom_push was called with summary
                push_calls = [
                    call
                    for call in mock_context["task_instance"].xcom_push.call_args_list
                    if call[1].get("key") == "transformation_summary"
                ]
                assert len(push_calls) == 1

