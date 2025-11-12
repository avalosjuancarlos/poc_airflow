"""
Yahoo Finance API Client

Handles all interactions with Yahoo Finance API including
error handling, retries, and rate limiting.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)


class YahooFinanceClient:
    """Client for Yahoo Finance API with built-in retry logic and rate limiting handling"""

    def __init__(self, base_url: str, headers: Dict[str, str], timeout: int = 30):
        """
        Initialize Yahoo Finance API client

        Args:
            base_url: Base URL for Yahoo Finance API
            headers: HTTP headers to use in requests
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.headers = headers
        self.timeout = timeout

    def fetch_market_data(
        self, ticker: str, date: str, max_retries: int = 3, retry_delay: int = 5
    ) -> Dict[str, Any]:
        """
        Fetch market data for a specific ticker and date

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            date: Date in YYYY-MM-DD format
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds

        Returns:
            Dictionary with market data

        Raises:
            requests.exceptions.HTTPError: On HTTP errors after all retries
            requests.exceptions.RequestException: On connection errors
            ValueError: On invalid API response
        """
        # Convert date to Unix timestamp
        target_date = datetime.strptime(date, "%Y-%m-%d")
        timestamp = int(target_date.timestamp())

        # Build URL and params
        url = f"{self.base_url}/{ticker}"
        params = {"period1": timestamp, "period2": timestamp, "interval": "1d"}

        logger.info(f"Fetching market data for {ticker} on {date}")
        logger.info(f"URL: {url}")
        logger.info(f"Params: {params}")

        # Retry logic with exponential backoff
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = retry_delay * (2**attempt)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)

                logger.info(f"Attempt {attempt + 1}/{max_retries}")
                response = requests.get(
                    url, params=params, headers=self.headers, timeout=self.timeout
                )

                # Handle rate limiting
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        retry_after = int(
                            response.headers.get("Retry-After", retry_delay)
                        )
                        logger.warning(f"Rate limit (429). Waiting {retry_after}s...")
                        time.sleep(retry_after)
                        continue
                    else:
                        logger.error("Rate limit reached after all retries")
                        response.raise_for_status()

                response.raise_for_status()
                break  # Success, exit retry loop

            except requests.exceptions.HTTPError as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"HTTP error on attempt {attempt + 1}: {e}")
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Network error on attempt {attempt + 1}: {e}")

        # Parse response
        data = response.json()

        # Validate response
        if data.get("chart", {}).get("error"):
            error_msg = data["chart"]["error"]
            logger.error(f"API error: {error_msg}")
            raise ValueError(f"API error: {error_msg}")

        # Extract market data
        return self._parse_market_data(data, ticker, date, timestamp)

    def check_availability(self, ticker: str) -> bool:
        """
        Check if Yahoo Finance API is available and responding

        Args:
            ticker: Ticker symbol to test

        Returns:
            True if API is available, False to retry
        """
        try:
            # Use recent date for testing
            test_date = datetime.now() - timedelta(days=7)
            timestamp = int(test_date.timestamp())

            url = f"{self.base_url}/{ticker}"
            params = {"period1": timestamp, "period2": timestamp, "interval": "1d"}

            logger.info(f"Checking API availability for {ticker}...")
            response = requests.get(
                url, params=params, headers=self.headers, timeout=self.timeout
            )

            # Handle different response codes
            if response.status_code == 429:
                logger.warning("API returned 429 (Rate Limit)")
                return False

            if 500 <= response.status_code < 600:
                logger.warning(f"API returned server error: {response.status_code}")
                return False

            response.raise_for_status()

            # Validate response structure
            data = response.json()

            if not data.get("chart"):
                logger.error("Invalid API response format")
                return False

            if data.get("chart", {}).get("error"):
                error = data["chart"]["error"]
                logger.error(f"API error: {error}")
                # Fail immediately for invalid ticker
                if "not found" in str(error).lower() or "invalid" in str(error).lower():
                    raise ValueError(f"Invalid ticker '{ticker}': {error}")
                return False

            if not data.get("chart", {}).get("result"):
                logger.warning("API returned no results")
                return False

            logger.info(f"✅ API is available for {ticker}")
            return True

        except requests.exceptions.Timeout:
            logger.warning("Timeout connecting to API")
            return False
        except requests.exceptions.ConnectionError:
            logger.warning("Connection error to API")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            return False
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return False

    def _parse_market_data(
        self, data: Dict[str, Any], ticker: str, date: str, timestamp: int
    ) -> Dict[str, Any]:
        """
        Parse and structure market data from API response

        Args:
            data: Raw API response
            ticker: Ticker symbol
            date: Date string
            timestamp: Unix timestamp

        Returns:
            Structured market data dictionary
        """
        result = data["chart"]["result"][0]
        meta = result["meta"]

        # Extract quote data
        quote_data = {}
        if result.get("indicators", {}).get("quote") and result["indicators"]["quote"]:
            quote = result["indicators"]["quote"][0]
            quote_data = {
                "open": quote.get("open", [None])[0],
                "high": quote.get("high", [None])[0],
                "low": quote.get("low", [None])[0],
                "close": quote.get("close", [None])[0],
                "volume": quote.get("volume", [None])[0],
            }

        # Build structured response
        market_data = {
            "ticker": ticker,
            "date": date,
            "timestamp": timestamp,
            "currency": meta.get("currency"),
            "exchange": meta.get("exchangeName"),
            "instrument_type": meta.get("instrumentType"),
            "regular_market_price": meta.get("regularMarketPrice"),
            "regular_market_time": meta.get("regularMarketTime"),
            "quote": quote_data,
            "metadata": {
                "fifty_two_week_high": meta.get("fiftyTwoWeekHigh"),
                "fifty_two_week_low": meta.get("fiftyTwoWeekLow"),
                "long_name": meta.get("longName"),
                "short_name": meta.get("shortName"),
            },
        }

        logger.info(f"Successfully parsed market data for {ticker}")
        logger.info(f"Close price: {quote_data.get('close')}")
        logger.info(f"Volume: {quote_data.get('volume')}")

        return market_data
