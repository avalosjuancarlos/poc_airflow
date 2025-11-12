"""
Yahoo Finance API Client

Handles all interactions with Yahoo Finance API including
error handling, retries, and rate limiting.
"""

import time
from datetime import datetime, timedelta
from typing import Any, Dict

import requests

from .logger import get_logger, log_execution

logger = get_logger(__name__)


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

    @log_execution()
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
        # Set time to 6PM (18:00) to ensure market has closed for the day
        target_date = datetime.strptime(date, "%Y-%m-%d")
        target_date = target_date.replace(hour=18, minute=0, second=0, microsecond=0)
        timestamp = int(target_date.timestamp())

        # Build URL and params
        url = f"{self.base_url}/{ticker}"
        params = {"period1": timestamp, "period2": timestamp, "interval": "1d"}

        # Build full URL for logging
        full_url = f"{url}?period1={timestamp}&period2={timestamp}&interval=1d"

        logger.info(
            f"Fetching market data for {ticker} on {date}",
            extra={"ticker": ticker, "date": date, "url": url, "timestamp": timestamp},
        )
        logger.info(f"API URL: {full_url}")

        # Retry logic with exponential backoff
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = retry_delay * (2**attempt)
                    logger.info(
                        f"Waiting {wait_time}s before retry attempt {attempt + 1}",
                        extra={"wait_time": wait_time, "attempt": attempt + 1},
                    )
                    time.sleep(wait_time)

                logger.debug(
                    f"API request attempt {attempt + 1}/{max_retries}",
                    extra={"attempt": attempt + 1, "max_retries": max_retries},
                )

                with logger.execution_timer(f"api_request_{ticker}"):
                    response = requests.get(
                        url,
                        params=params,
                        headers=self.headers,
                        timeout=self.timeout,
                    )

                # Handle rate limiting
                if response.status_code == 429:
                    logger.metric(
                        "api.rate_limit",
                        1,
                        {"ticker": ticker, "attempt": attempt + 1},
                    )
                    if attempt < max_retries - 1:
                        retry_after = int(
                            response.headers.get("Retry-After", retry_delay)
                        )
                        logger.warning(
                            f"Rate limit (429). Waiting {retry_after}s...",
                            extra={"retry_after": retry_after},
                        )
                        time.sleep(retry_after)
                        continue
                    else:
                        logger.error(
                            "Rate limit reached after all retries",
                            extra={"ticker": ticker, "max_retries": max_retries},
                        )
                        response.raise_for_status()

                response.raise_for_status()
                logger.metric("api.request.success", 1, {"ticker": ticker})
                break  # Success, exit retry loop

            except requests.exceptions.HTTPError as e:
                logger.metric(
                    "api.request.http_error",
                    1,
                    {"ticker": ticker, "status_code": e.response.status_code},
                )
                if attempt == max_retries - 1:
                    logger.error(
                        f"HTTP error after all retries: {e}",
                        extra={"ticker": ticker, "error": str(e)},
                        exc_info=True,
                    )
                    raise
                logger.warning(
                    f"HTTP error on attempt {attempt + 1}: {e}",
                    extra={"attempt": attempt + 1, "error": str(e)},
                )
            except requests.exceptions.RequestException as e:
                logger.metric(
                    "api.request.network_error",
                    1,
                    {"ticker": ticker, "error": type(e).__name__},
                )
                if attempt == max_retries - 1:
                    logger.error(
                        f"Network error after all retries: {e}",
                        extra={"ticker": ticker, "error": str(e)},
                        exc_info=True,
                    )
                    raise
                logger.warning(
                    f"Network error on attempt {attempt + 1}: {e}",
                    extra={"attempt": attempt + 1, "error": str(e)},
                )

        # Parse response
        data = response.json()

        # Validate response
        if data.get("chart", {}).get("error"):
            error_msg = data["chart"]["error"]
            logger.error(
                f"API error: {error_msg}",
                extra={"ticker": ticker, "api_error": error_msg},
            )
            logger.metric("api.response.error", 1, {"ticker": ticker})
            raise ValueError(f"API error: {error_msg}")

        # Debug: Log response structure
        if data.get("chart", {}).get("result"):
            result = data["chart"]["result"][0]
            indicators = result.get("indicators", {})
            quote_list = indicators.get("quote", [])

            logger.info(
                f"API response structure for {ticker} on {date}: "
                f"has_indicators={bool(indicators)}, "
                f"quote_list_length={len(quote_list)}"
            )

            if quote_list and len(quote_list) > 0:
                quote = quote_list[0]
                logger.info(
                    f"Quote data arrays for {ticker} on {date}: "
                    f"open_len={len(quote.get('open', []))}, "
                    f"high_len={len(quote.get('high', []))}, "
                    f"low_len={len(quote.get('low', []))}, "
                    f"close_len={len(quote.get('close', []))}, "
                    f"volume_len={len(quote.get('volume', []))}"
                )

                # Log actual values if arrays are not empty
                if quote.get("close") and len(quote.get("close", [])) > 0:
                    logger.info(
                        f"First close value for {ticker} on {date}: {quote['close'][0]}"
                    )
                else:
                    logger.warning(
                        f"Empty close array for {ticker} on {date}. Full quote: {quote}"
                    )
            else:
                logger.warning(
                    f"No quote data in response for {ticker} on {date}. Indicators: {indicators}"
                )

        # Extract market data
        return self._parse_market_data(data, ticker, date, timestamp)

    @log_execution()
    def check_availability(self, ticker: str) -> bool:
        """
        Check if Yahoo Finance API is available and responding

        Args:
            ticker: Ticker symbol to test

        Returns:
            True if API is available, False to retry
        """
        try:
            # Use recent date for testing (7 days ago at 6PM)
            test_date = datetime.now() - timedelta(days=7)
            test_date = test_date.replace(hour=18, minute=0, second=0, microsecond=0)
            timestamp = int(test_date.timestamp())

            url = f"{self.base_url}/{ticker}"
            params = {"period1": timestamp, "period2": timestamp, "interval": "1d"}

            logger.info(
                f"Checking API availability for {ticker}",
                extra={"ticker": ticker, "url": url},
            )

            with logger.execution_timer(f"api_availability_check_{ticker}"):
                response = requests.get(
                    url, params=params, headers=self.headers, timeout=self.timeout
                )

            # Handle different response codes
            if response.status_code == 429:
                logger.warning(
                    "API returned 429 (Rate Limit)",
                    extra={"ticker": ticker, "status_code": 429},
                )
                logger.metric("api.availability.rate_limit", 1, {"ticker": ticker})
                return False

            if 500 <= response.status_code < 600:
                logger.warning(
                    f"API returned server error: {response.status_code}",
                    extra={"ticker": ticker, "status_code": response.status_code},
                )
                logger.metric(
                    "api.availability.server_error",
                    1,
                    {"ticker": ticker, "status_code": response.status_code},
                )
                return False

            response.raise_for_status()

            # Validate response structure
            data = response.json()

            if not data.get("chart"):
                logger.error("Invalid API response format", extra={"ticker": ticker})
                logger.metric("api.availability.invalid_format", 1, {"ticker": ticker})
                return False

            if data.get("chart", {}).get("error"):
                error = data["chart"]["error"]
                logger.error(
                    f"API error: {error}", extra={"ticker": ticker, "error": error}
                )
                # Fail immediately for invalid ticker
                if "not found" in str(error).lower() or "invalid" in str(error).lower():
                    logger.metric(
                        "api.availability.invalid_ticker", 1, {"ticker": ticker}
                    )
                    raise ValueError(f"Invalid ticker '{ticker}': {error}")
                return False

            if not data.get("chart", {}).get("result"):
                logger.warning("API returned no results", extra={"ticker": ticker})
                logger.metric("api.availability.no_results", 1, {"ticker": ticker})
                return False

            logger.info(f"✅ API is available for {ticker}", extra={"ticker": ticker})
            logger.metric("api.availability.success", 1, {"ticker": ticker})
            return True

        except requests.exceptions.Timeout:
            logger.warning("Timeout connecting to API", extra={"ticker": ticker})
            logger.metric("api.availability.timeout", 1, {"ticker": ticker})
            return False
        except requests.exceptions.ConnectionError:
            logger.warning("Connection error to API", extra={"ticker": ticker})
            logger.metric("api.availability.connection_error", 1, {"ticker": ticker})
            return False
        except requests.exceptions.RequestException as e:
            logger.error(
                f"Request error: {str(e)}", extra={"ticker": ticker, "error": str(e)}
            )
            logger.metric("api.availability.request_error", 1, {"ticker": ticker})
            return False
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.exception(
                f"Unexpected error during availability check: {str(e)}",
                extra={"ticker": ticker, "error": str(e)},
            )
            logger.metric("api.availability.unexpected_error", 1, {"ticker": ticker})
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

            # Helper function to safely extract first element from array
            def safe_get_first(arr):
                """Safely get first element from array, handling empty arrays"""
                if arr and len(arr) > 0:
                    return arr[0]
                return None

            quote_data = {
                "open": safe_get_first(quote.get("open", [])),
                "high": safe_get_first(quote.get("high", [])),
                "low": safe_get_first(quote.get("low", [])),
                "close": safe_get_first(quote.get("close", [])),
                "volume": safe_get_first(quote.get("volume", [])),
            }

            logger.debug(
                f"Extracted quote data for {ticker}: close={quote_data.get('close')}, "
                f"volume={quote_data.get('volume')}"
            )

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

        close_price = quote_data.get("close")
        volume = quote_data.get("volume")

        logger.info(
            f"Successfully parsed market data for {ticker}",
            extra={
                "ticker": ticker,
                "date": date,
                "close_price": close_price,
                "volume": volume,
                "currency": meta.get("currency"),
                "exchange": meta.get("exchangeName"),
            },
        )

        # Log metrics for monitoring
        if close_price is not None:
            logger.metric(
                "market.close_price", close_price, {"ticker": ticker, "date": date}
            )
        if volume is not None:
            logger.metric("market.volume", volume, {"ticker": ticker, "date": date})

        logger.audit(
            "market_data_fetched",
            {
                "ticker": ticker,
                "date": date,
                "has_price": close_price is not None,
                "has_volume": volume is not None,
            },
        )

        return market_data
