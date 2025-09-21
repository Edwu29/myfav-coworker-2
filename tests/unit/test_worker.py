"""Unit tests for worker Lambda handler."""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from src.worker import lambda_handler, process_simulation_job, validate_worker_environment
from models.simulation_job import SimulationJobModel, JobStatus


class TestWorkerLambdaHandler:
    """Test cases for worker lambda_handler."""
    
    @patch('src.worker.process_simulation_job')
    def test_lambda_handler_success(self, mock_process_job):
        """Test successful SQS message processing."""
        mock_process_job.return_value = {"status": "completed", "job_id": "job123"}
        
        event = {
            'Records': [
                {
                    'body': json.dumps({
                        'job_id': 'job123',
                        'action': 'start_simulation',
                        'user_id': 'user123'
                    })
                }
            ]
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        assert response['processed'] == 1
        assert len(response['results']) == 1
        mock_process_job.assert_called_once()
    
    @patch('src.worker.process_simulation_job')
    def test_lambda_handler_multiple_records(self, mock_process_job):
        """Test processing multiple SQS records."""
        mock_process_job.side_effect = [
            {"status": "completed", "job_id": "job123"},
            {"status": "completed", "job_id": "job456"}
        ]
        
        event = {
            'Records': [
                {
                    'body': json.dumps({
                        'job_id': 'job123',
                        'action': 'start_simulation'
                    })
                },
                {
                    'body': json.dumps({
                        'job_id': 'job456',
                        'action': 'start_simulation'
                    })
                }
            ]
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        assert response['processed'] == 2
        assert mock_process_job.call_count == 2
    
    def test_lambda_handler_unknown_action(self):
        """Test handling unknown action."""
        event = {
            'Records': [
                {
                    'body': json.dumps({
                        'job_id': 'job123',
                        'action': 'unknown_action'
                    })
                }
            ]
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        assert response['results'][0]['status'] == 'skipped'
        assert 'Unknown action' in response['results'][0]['reason']
    
    def test_lambda_handler_invalid_json(self):
        """Test handling invalid JSON in SQS message."""
        event = {
            'Records': [
                {
                    'body': 'invalid json'
                }
            ]
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 200
        assert response['results'][0]['status'] == 'error'
    
    def test_lambda_handler_exception(self):
        """Test handling unexpected exception."""
        event = {
            'Records': 'invalid_structure'  # This will cause an exception
        }
        
        response = lambda_handler(event, {})
        
        assert response['statusCode'] == 500
        assert 'error' in response


class TestProcessSimulationJob:
    """Test cases for process_simulation_job."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sample_message = {
            'job_id': 'job123',
            'action': 'start_simulation',
            'user_id': 'user123',
            'pr_url': 'https://github.com/owner/repo/pull/123',
            'pr_owner': 'owner',
            'pr_repo': 'repo',
            'pr_number': 123,
            'pr_head_sha': 'abc123',
            'pr_base_sha': 'def456'
        }
        
        self.sample_job_item = {
            'job_id': 'job123',
            'user_id': 'user123',
            'pr_url': 'https://github.com/owner/repo/pull/123',
            'status': 'simulation_running',
            'created_at': '2023-01-01T00:00:00+00:00',
            'pr_owner': 'owner',
            'pr_repo': 'repo',
            'pr_number': 123,
            'pr_head_sha': 'abc123',
            'pr_base_sha': 'def456'
        }
    
    @patch('src.worker.UserService')
    @patch('src.worker.RepositoryService')
    @patch('src.worker.SimulationService')
    @patch('os.path.exists')
    def test_process_simulation_job_success(self, mock_exists, mock_sim_service, 
                                          mock_repo_service, mock_user_service):
        """Test successful simulation job processing."""
        # Mock services
        mock_user_instance = Mock()
        mock_table = Mock()
        mock_user_instance.table = mock_table
        mock_user_service.return_value = mock_user_instance
        
        mock_repo_instance = Mock()
        mock_repo_instance.get_repository_path.return_value = '/tmp/repo'
        mock_repo_service.return_value = mock_repo_instance
        
        mock_sim_instance = Mock()
        mock_sim_service.return_value = mock_sim_instance
        
        # Mock DynamoDB response
        mock_table.get_item.return_value = {'Item': self.sample_job_item}
        
        # Mock repository exists
        mock_exists.return_value = True
        
        # Mock simulation result
        simulation_report = {
            "result": "pass",
            "summary": "Test passed",
            "execution_logs": ["Step 1: Success"],
            "timestamp": "2023-01-01T00:00:00Z"
        }
        
        # Mock asyncio.run_until_complete
        with patch('asyncio.new_event_loop') as mock_loop_new, \
             patch('asyncio.set_event_loop') as mock_set_loop:
            
            mock_loop = Mock()
            mock_loop_new.return_value = mock_loop
            mock_loop.run_until_complete.return_value = simulation_report
            
            result = process_simulation_job(self.sample_message)
            
            assert result['status'] == 'completed'
            assert result['job_id'] == 'job123'
            assert result['final_status'] == 'simulation_completed'
            assert result['result'] == 'pass'
            
            # Verify services were called
            mock_repo_instance.checkout_pr_branch.assert_called_once()
            mock_loop.run_until_complete.assert_called_once()
            mock_table.put_item.assert_called()
    
    @patch('src.worker.UserService')
    def test_process_simulation_job_not_found(self, mock_user_service):
        """Test processing job that doesn't exist."""
        mock_user_instance = Mock()
        mock_table = Mock()
        mock_user_instance.table = mock_table
        mock_user_service.return_value = mock_user_instance
        
        # Mock job not found
        mock_table.get_item.return_value = {}
        
        result = process_simulation_job(self.sample_message)
        
        assert result['status'] == 'error'
        assert result['job_id'] == 'job123'
        assert 'Job not found' in result['error']
    
    @patch('src.worker.UserService')
    def test_process_simulation_job_wrong_status(self, mock_user_service):
        """Test processing job in wrong status."""
        mock_user_instance = Mock()
        mock_table = Mock()
        mock_user_instance.table = mock_table
        mock_user_service.return_value = mock_user_instance
        
        # Mock job in wrong status
        wrong_status_item = self.sample_job_item.copy()
        wrong_status_item['status'] = 'pending'
        mock_table.get_item.return_value = {'Item': wrong_status_item}
        
        result = process_simulation_job(self.sample_message)
        
        assert result['status'] == 'skipped'
        assert result['job_id'] == 'job123'
        assert 'Job state is pending' in result['reason']
    
    @patch('src.worker.UserService')
    @patch('src.worker.RepositoryService')
    @patch('os.path.exists')
    def test_process_simulation_job_repo_not_found(self, mock_exists, mock_repo_service, 
                                                  mock_user_service):
        """Test processing job with missing repository."""
        # Mock services
        mock_user_instance = Mock()
        mock_table = Mock()
        mock_user_instance.table = mock_table
        mock_user_service.return_value = mock_user_instance
        
        mock_repo_instance = Mock()
        mock_repo_instance.get_repository_path.return_value = '/tmp/nonexistent'
        mock_repo_service.return_value = mock_repo_instance
        
        # Mock DynamoDB response
        mock_table.get_item.return_value = {'Item': self.sample_job_item}
        
        # Mock repository doesn't exist
        mock_exists.return_value = False
        
        result = process_simulation_job(self.sample_message)
        
        assert result['status'] == 'error'
        assert result['job_id'] == 'job123'
        assert 'Repository not found' in result['error']
        
        # Verify job was marked as failed
        mock_table.put_item.assert_called()
    
    @patch('src.worker.UserService')
    @patch('src.worker.RepositoryService')
    @patch('os.path.exists')
    def test_process_simulation_job_checkout_failure(self, mock_exists, mock_repo_service, 
                                                   mock_user_service):
        """Test processing job with checkout failure."""
        # Mock services
        mock_user_instance = Mock()
        mock_table = Mock()
        mock_user_instance.table = mock_table
        mock_user_service.return_value = mock_user_instance
        
        mock_repo_instance = Mock()
        mock_repo_instance.get_repository_path.return_value = '/tmp/repo'
        mock_repo_instance.checkout_pr_branch.side_effect = Exception("Checkout failed")
        mock_repo_service.return_value = mock_repo_instance
        
        # Mock DynamoDB response
        mock_table.get_item.return_value = {'Item': self.sample_job_item}
        
        # Mock repository exists
        mock_exists.return_value = True
        
        result = process_simulation_job(self.sample_message)
        
        assert result['status'] == 'error'
        assert result['job_id'] == 'job123'
        assert 'Checkout failed' in result['error']
    
    @patch('src.worker.UserService')
    @patch('src.worker.RepositoryService')
    @patch('src.worker.SimulationService')
    @patch('os.path.exists')
    def test_process_simulation_job_simulation_failure(self, mock_exists, mock_sim_service, 
                                                     mock_repo_service, mock_user_service):
        """Test processing job with simulation failure."""
        # Mock services
        mock_user_instance = Mock()
        mock_table = Mock()
        mock_user_instance.table = mock_table
        mock_user_service.return_value = mock_user_instance
        
        mock_repo_instance = Mock()
        mock_repo_instance.get_repository_path.return_value = '/tmp/repo'
        mock_repo_service.return_value = mock_repo_instance
        
        mock_sim_instance = Mock()
        mock_sim_service.return_value = mock_sim_instance
        
        # Mock DynamoDB response
        mock_table.get_item.return_value = {'Item': self.sample_job_item}
        
        # Mock repository exists
        mock_exists.return_value = True
        
        # Mock simulation failure
        with patch('asyncio.new_event_loop') as mock_loop_new:
            mock_loop = Mock()
            mock_loop_new.return_value = mock_loop
            mock_loop.run_until_complete.side_effect = Exception("Simulation failed")
            
            result = process_simulation_job(self.sample_message)
            
            assert result['status'] == 'completed'  # Still completed, but job marked as failed
            assert result['job_id'] == 'job123'
            assert result['final_status'] == 'failed'
            
            # Verify job was updated with failure
            mock_table.put_item.assert_called()
    
    @patch('src.worker.UserService')
    def test_process_simulation_job_database_error(self, mock_user_service):
        """Test processing job with database error."""
        mock_user_instance = Mock()
        mock_table = Mock()
        mock_user_instance.table = mock_table
        mock_user_service.return_value = mock_user_instance
        
        # Mock database error
        mock_table.get_item.side_effect = Exception("Database error")
        
        result = process_simulation_job(self.sample_message)
        
        assert result['status'] == 'error'
        assert result['job_id'] == 'job123'
        assert 'Database error' in result['error']


class TestValidateWorkerEnvironment:
    """Test cases for validate_worker_environment."""
    
    @patch('src.worker.SimulationService')
    @patch('src.worker.RepositoryService')
    def test_validate_worker_environment_success(self, mock_repo_service, mock_sim_service):
        """Test successful environment validation."""
        mock_sim_instance = Mock()
        mock_sim_instance.validate_environment.return_value = True
        mock_sim_service.return_value = mock_sim_instance
        
        result = validate_worker_environment()
        
        assert result is True
        mock_sim_instance.validate_environment.assert_called_once()
    
    @patch('src.worker.SimulationService')
    @patch('src.worker.RepositoryService')
    def test_validate_worker_environment_sim_failure(self, mock_repo_service, mock_sim_service):
        """Test environment validation with simulation service failure."""
        mock_sim_instance = Mock()
        mock_sim_instance.validate_environment.return_value = False
        mock_sim_service.return_value = mock_sim_instance
        
        result = validate_worker_environment()
        
        assert result is False
    
    @patch('src.worker.SimulationService')
    def test_validate_worker_environment_import_error(self, mock_sim_service):
        """Test environment validation with import error."""
        mock_sim_service.side_effect = ImportError("Module not found")
        
        result = validate_worker_environment()
        
        assert result is False
