"""
Unit tests for validators module
"""

import pytest
import sys
import os

# Add dags directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../dags'))

from market_data.utils.validators import validate_ticker_format, validate_date_format


class TestValidateTickerFormat:
    """Tests for ticker validation"""
    
    def test_valid_ticker_uppercase(self):
        """Test valid uppercase ticker"""
        result = validate_ticker_format('AAPL')
        assert result == 'AAPL'
    
    def test_valid_ticker_lowercase(self):
        """Test lowercase ticker gets converted to uppercase"""
        result = validate_ticker_format('aapl')
        assert result == 'AAPL'
    
    def test_valid_ticker_mixed_case(self):
        """Test mixed case ticker gets converted to uppercase"""
        result = validate_ticker_format('AaPl')
        assert result == 'AAPL'
    
    def test_valid_ticker_with_dot(self):
        """Test ticker with dot (e.g., BRK.B)"""
        result = validate_ticker_format('BRK.B')
        assert result == 'BRK.B'
    
    def test_valid_ticker_with_dash(self):
        """Test ticker with dash"""
        result = validate_ticker_format('CL-Q')
        assert result == 'CL-Q'
    
    def test_valid_ticker_with_caret(self):
        """Test ticker with caret (e.g., ^GSPC for S&P 500)"""
        result = validate_ticker_format('^GSPC')
        assert result == '^GSPC'
    
    def test_empty_ticker(self):
        """Test empty ticker raises error"""
        with pytest.raises(ValueError, match="Ticker cannot be empty"):
            validate_ticker_format('')
    
    def test_none_ticker(self):
        """Test None ticker raises error"""
        with pytest.raises(ValueError, match="Ticker must be a valid string"):
            validate_ticker_format(None)
    
    def test_numeric_ticker(self):
        """Test numeric ticker raises error"""
        with pytest.raises(ValueError, match="Ticker must be a valid string"):
            validate_ticker_format(123)
    
    def test_ticker_too_long(self):
        """Test ticker longer than 10 characters raises error"""
        with pytest.raises(ValueError, match="Ticker too long"):
            validate_ticker_format('VERYLONGTICKER123')
    
    def test_ticker_with_spaces(self):
        """Test ticker with spaces gets trimmed"""
        result = validate_ticker_format('  AAPL  ')
        assert result == 'AAPL'
    
    def test_ticker_with_invalid_chars(self):
        """Test ticker with invalid characters raises error"""
        with pytest.raises(ValueError, match="Invalid characters"):
            validate_ticker_format('AAPL@#$')


class TestValidateDateFormat:
    """Tests for date validation"""
    
    def test_valid_date(self):
        """Test valid date format"""
        result = validate_date_format('2023-11-09')
        assert result == '2023-11-09'
    
    def test_valid_date_different(self):
        """Test different valid date"""
        result = validate_date_format('2024-01-15')
        assert result == '2024-01-15'
    
    def test_invalid_date_format_slash(self):
        """Test invalid date format with slashes"""
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date_format('11/09/2023')
    
    def test_invalid_date_format_dots(self):
        """Test invalid date format with dots"""
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date_format('09.11.2023')
    
    def test_invalid_date_format_reversed(self):
        """Test invalid date format (DD-MM-YYYY)"""
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date_format('09-11-2023')
    
    def test_invalid_date_value(self):
        """Test invalid date value"""
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date_format('2023-13-45')
    
    def test_invalid_month(self):
        """Test invalid month"""
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date_format('2023-13-01')
    
    def test_invalid_day(self):
        """Test invalid day"""
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date_format('2023-02-30')

