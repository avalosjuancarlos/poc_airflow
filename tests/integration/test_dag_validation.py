"""
Integration tests for DAG validation

Tests that the DAG structure and configuration are valid
"""

import os
import sys
from datetime import datetime, timedelta

import pytest

# Add dags directory to path
DAGS_DIR = os.path.join(os.path.dirname(__file__), "../../dags")
if DAGS_DIR not in sys.path:
    sys.path.insert(0, DAGS_DIR)

from airflow.models import DagBag


class TestDAGValidation:
    """Test DAG validation and structure"""

    @pytest.fixture(scope="class")
    def dagbag(self):
        """Load all DAGs"""
        return DagBag(dag_folder="dags/", include_examples=False)

    def test_dag_loaded(self, dagbag):
        """Test that the DAG is loaded without errors"""
        # Check for import errors first
        if dagbag.import_errors:
            for filename, error in dagbag.import_errors.items():
                print(f"Import error in {filename}:")
                print(error)

        assert (
            len(dagbag.import_errors) == 0
        ), f"DAG import errors: {dagbag.import_errors}"
        assert (
            "get_market_data" in dagbag.dags
        ), f"Available DAGs: {list(dagbag.dags.keys())}"

    def test_dag_structure(self, dagbag):
        """Test DAG has correct structure"""
        dag = dagbag.get_dag("get_market_data")

        # Check DAG exists
        assert dag is not None

        # Check DAG properties
        assert dag.dag_id == "get_market_data"
        assert dag.schedule_interval is None
        assert dag.catchup is False

        # Check tags
        assert "finance" in dag.tags
        assert "market-data" in dag.tags
        assert "yahoo-finance" in dag.tags
        assert "api" in dag.tags

    def test_dag_tasks(self, dagbag):
        """Test DAG has all required tasks"""
        dag = dagbag.get_dag("get_market_data")

        # Expected tasks
        expected_tasks = [
            "validate_ticker",
            "check_api_availability",
            "fetch_market_data",
            "process_market_data",
        ]

        # Check all tasks exist
        task_ids = [task.task_id for task in dag.tasks]
        for expected_task in expected_tasks:
            assert expected_task in task_ids, f"Missing task: {expected_task}"

        # Check exact count
        assert len(dag.tasks) == 4

    def test_task_dependencies(self, dagbag):
        """Test tasks have correct dependencies"""
        dag = dagbag.get_dag("get_market_data")

        # Get tasks
        validate_task = dag.get_task("validate_ticker")
        sensor_task = dag.get_task("check_api_availability")
        fetch_task = dag.get_task("fetch_market_data")
        process_task = dag.get_task("process_market_data")

        # Check dependencies
        # validate_ticker >> check_api_availability
        assert sensor_task in validate_task.downstream_list

        # check_api_availability >> fetch_market_data
        assert fetch_task in sensor_task.downstream_list

        # fetch_market_data >> process_market_data
        assert process_task in fetch_task.downstream_list

    def test_task_retries(self, dagbag):
        """Test tasks have retry configuration"""
        dag = dagbag.get_dag("get_market_data")

        for task in dag.tasks:
            assert task.retries == 2
            assert task.retry_delay == timedelta(minutes=2)
            assert task.execution_timeout == timedelta(minutes=10)

    def test_sensor_configuration(self, dagbag):
        """Test sensor has correct configuration"""
        dag = dagbag.get_dag("get_market_data")
        sensor_task = dag.get_task("check_api_availability")

        # Check sensor-specific attributes
        assert sensor_task.poke_interval >= 30
        assert sensor_task.timeout >= 600
        assert sensor_task.mode == "poke"

    def test_dag_params(self, dagbag):
        """Test DAG has correct parameters"""
        dag = dagbag.get_dag("get_market_data")

        # Check params exist
        assert "ticker" in dag.params
        assert "date" in dag.params

        # Check default ticker is set
        assert dag.params["ticker"] is not None

    def test_dag_owner(self, dagbag):
        """Test DAG has correct owner"""
        dag = dagbag.get_dag("get_market_data")

        assert dag.default_args.get("owner") == "airflow"

    def test_dag_start_date(self, dagbag):
        """Test DAG has valid start date"""
        dag = dagbag.get_dag("get_market_data")

        assert dag.default_args.get("start_date") is not None
        assert isinstance(dag.default_args.get("start_date"), datetime)
