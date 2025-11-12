"""
Integration tests for DAG execution

Tests end-to-end execution of the DAG
"""

import pytest
import sys
import os
from unittest.mock import patch, Mock
from datetime import datetime

# Add dags directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../dags'))

from airflow.models import DagBag
from airflow.utils.state import State


@pytest.mark.integration
class TestDAGExecution:
    """Test DAG execution flow"""
    
    @pytest.fixture(scope='class')
    def dagbag(self):
        """Load DAG"""
        return DagBag(dag_folder='dags/', include_examples=False)
    
    @pytest.fixture
    def mock_api_response(self):
        """Mock successful API response"""
        return {
            'chart': {
                'result': [{
                    'meta': {
                        'currency': 'USD',
                        'symbol': 'AAPL',
                        'exchangeName': 'NMS',
                        'instrumentType': 'EQUITY',
                        'regularMarketPrice': 182.41,
                        'regularMarketTime': 1699549200,
                        'fiftyTwoWeekHigh': 184.95,
                        'fiftyTwoWeekLow': 124.17,
                        'longName': 'Apple Inc.',
                        'shortName': 'Apple Inc.'
                    },
                    'indicators': {
                        'quote': [{
                            'open': [182.96],
                            'high': [184.12],
                            'low': [181.81],
                            'close': [182.41],
                            'volume': [53763500]
                        }]
                    }
                }],
                'error': None
            }
        }
    
    def test_validate_ticker_task(self, dagbag):
        """Test validate_ticker task execution"""
        dag = dagbag.get_dag('get_market_data')
        task = dag.get_task('validate_ticker')
        
        # Create mock context
        mock_context = {
            'dag_run': Mock(conf={'ticker': 'AAPL'}),
            'task_instance': Mock()
        }
        
        # Execute task
        result = task.python_callable(**mock_context)
        
        # Verify result
        assert result == 'AAPL'
    
    def test_validate_ticker_lowercase(self, dagbag):
        """Test validate_ticker converts to uppercase"""
        dag = dagbag.get_dag('get_market_data')
        task = dag.get_task('validate_ticker')
        
        mock_context = {
            'dag_run': Mock(conf={'ticker': 'aapl'}),
            'task_instance': Mock()
        }
        
        result = task.python_callable(**mock_context)
        
        assert result == 'AAPL'
    
    @patch('market_data.utils.api_client.requests.get')
    def test_check_api_availability_task(self, mock_get, dagbag, mock_api_response):
        """Test check_api_availability sensor"""
        dag = dagbag.get_dag('get_market_data')
        task = dag.get_task('check_api_availability')
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_get.return_value = mock_response
        
        # Execute sensor
        result = task.python_callable(ticker='AAPL')
        
        assert result is True
    
    @patch('market_data.utils.api_client.requests.get')
    def test_fetch_market_data_task(self, mock_get, dagbag, mock_api_response):
        """Test fetch_market_data task execution"""
        dag = dagbag.get_dag('get_market_data')
        task = dag.get_task('fetch_market_data')
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        mock_get.return_value = mock_response
        
        # Create mock context
        mock_ti = Mock()
        mock_context = {
            'task_instance': mock_ti
        }
        
        # Execute task
        result = task.python_callable(
            ticker='AAPL',
            date='2023-11-09',
            **mock_context
        )
        
        # Verify result structure
        assert result['ticker'] == 'AAPL'
        assert result['date'] == '2023-11-09'
        assert 'quote' in result
        assert 'metadata' in result
        
        # Verify XCom push was called
        mock_ti.xcom_push.assert_called_once()
    
    def test_process_market_data_task(self, dagbag):
        """Test process_market_data task execution"""
        dag = dagbag.get_dag('get_market_data')
        task = dag.get_task('process_market_data')
        
        # Mock market data from XCom
        mock_data = {
            'ticker': 'AAPL',
            'date': '2023-11-09',
            'currency': 'USD',
            'exchange': 'NMS',
            'quote': {
                'open': 182.96,
                'high': 184.12,
                'low': 181.81,
                'close': 182.41,
                'volume': 53763500
            },
            'metadata': {
                'long_name': 'Apple Inc.',
                'fifty_two_week_high': 184.95,
                'fifty_two_week_low': 124.17
            }
        }
        
        # Create mock context
        mock_ti = Mock()
        mock_ti.xcom_pull.return_value = mock_data
        mock_context = {
            'task_instance': mock_ti
        }
        
        # Execute task
        result = task.python_callable(**mock_context)
        
        # Verify result
        assert result == mock_data
        
        # Verify XCom pull was called
        mock_ti.xcom_pull.assert_called_once_with(
            task_ids='fetch_market_data',
            key='market_data'
        )

