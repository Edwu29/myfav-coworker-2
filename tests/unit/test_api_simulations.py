"""Tests for simulation API handlers."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from src.api.simulations import submit_simulation_handler, get_simulation_status_handler


class TestSubmitSimulationHandler:
    """Test cases for submit_simulation_handler."""
    
    @patch('src.api.simulations.get_user_from_token')
    @patch('src.api.simulations.parse_github_pr_url')
    @patch('src.api.simulations.UserService')
    @patch('src.api.simulations.GitHubService')
    def test_submit_simulation_success(self, mock_github_service, 
                                     mock_user_service, mock_parse_url, mock_get_user):
        """Test successful simulation submission."""
        # Mock user authentication
        mock_get_user.return_value = {
            'user_id': 'user123',
            'github_id': 'github123'
        }
        
        # Mock PR URL parsing
        mock_parse_url.return_value = ('owner', 'repo', 123)
        
        # Mock user service
        mock_user_instance = Mock()
        mock_user_instance.get_decrypted_github_token.return_value = 'token123'
        mock_table = Mock()
        mock_user_instance.table = mock_table
        mock_user_service.return_value = mock_user_instance
        
        # Mock GitHub service
        mock_github_instance = Mock()
        mock_github_instance.get_pull_request.return_value = {
            'number': 123,
            'title': 'Test PR',
            'head': {'sha': 'abc123', 'ref': 'feature'},
            'base': {'sha': 'def456', 'ref': 'main'},
            'state': 'open',
            'diff_url': 'https://github.com/owner/repo/pull/123.diff',
            'patch_url': 'https://github.com/owner/repo/pull/123.patch',
            'created_at': '2023-01-01T00:00:00Z',
            'updated_at': '2023-01-01T12:00:00Z'
        }
        mock_github_service.return_value = mock_github_instance
        
        # Create test event
        event = {
            'body': json.dumps({
                'pr_url': 'https://github.com/owner/repo/pull/123'
            }),
            'headers': {
                'Authorization': 'Bearer valid_token'
            }
        }
        
        response = submit_simulation_handler(event, {})
        
        # Verify response
        assert response['statusCode'] == 202
        assert 'application/json' in response['headers']['Content-Type']
        
        response_body = json.loads(response['body'])
        assert 'job_id' in response_body
        assert response_body['status'] == 'pending'
        
        # Verify DynamoDB put_item was called
        mock_table.put_item.assert_called_once()
    
    @patch('src.api.simulations.get_user_from_token')
    def test_submit_simulation_invalid_token(self, mock_get_user):
        """Test submission with invalid authentication token."""
        mock_get_user.side_effect = Exception("Invalid token")
        
        event = {
            'body': json.dumps({
                'pr_url': 'https://github.com/owner/repo/pull/123'
            }),
            'headers': {
                'Authorization': 'Bearer invalid_token'
            }
        }
        
        response = submit_simulation_handler(event, {})
        
        assert response['statusCode'] == 401
        response_body = json.loads(response['body'])
        assert 'error' in response_body
    
    @patch('src.api.simulations.get_user_from_token')
    def test_submit_simulation_missing_body(self, mock_get_user):
        """Test submission with missing request body."""
        mock_get_user.return_value = {'user_id': 'user123', 'github_id': 'github123'}
        
        event = {
            'headers': {
                'Authorization': 'Bearer valid_token'
            }
        }
        
        response = submit_simulation_handler(event, {})
        
        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'error' in response_body
    
    @patch('src.api.simulations.get_user_from_token')
    def test_submit_simulation_invalid_json(self, mock_get_user):
        """Test submission with invalid JSON body."""
        mock_get_user.return_value = {'user_id': 'user123', 'github_id': 'github123'}
        
        event = {
            'body': 'invalid json',
            'headers': {
                'Authorization': 'Bearer valid_token'
            }
        }
        
        response = submit_simulation_handler(event, {})
        
        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'error' in response_body
    
    @patch('src.api.simulations.get_user_from_token')
    @patch('src.api.simulations.parse_github_pr_url')
    def test_submit_simulation_invalid_pr_url(self, mock_parse_url, mock_get_user):
        """Test submission with invalid PR URL."""
        mock_get_user.return_value = {'user_id': 'user123', 'github_id': 'github123'}
        mock_parse_url.side_effect = Exception("Invalid PR URL")
        
        event = {
            'body': json.dumps({
                'pr_url': 'invalid-url'
            }),
            'headers': {
                'Authorization': 'Bearer valid_token'
            }
        }
        
        response = submit_simulation_handler(event, {})
        
        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'error' in response_body


class TestGetSimulationStatusHandler:
    """Test cases for get_simulation_status_handler."""
    
    @patch('src.api.simulations.get_user_from_token')
    @patch('src.api.simulations.boto3.resource')
    def test_get_simulation_status_success(self, mock_boto3, mock_get_user):
        """Test successful simulation status retrieval."""
        # Mock user authentication
        mock_get_user.return_value = {'user_id': 'user123', 'github_id': 'github123'}
        
        # Mock DynamoDB response
        mock_table = Mock()
        mock_table.get_item.return_value = {
            'Item': {
                'job_id': 'job123',
                'user_id': 'user123',
                'pr_url': 'https://github.com/owner/repo/pull/123',
                'status': 'completed',
                'created_at': '2023-01-01T00:00:00Z',
                'completed_at': '2023-01-01T12:00:00Z',
                'report': {'result': 'pass'}
            }
        }
        mock_resource = Mock()
        mock_resource.Table.return_value = mock_table
        mock_boto3.return_value = mock_resource
        
        # Create test event
        event = {
            'pathParameters': {'job_id': 'job123'},
            'headers': {
                'Authorization': 'Bearer valid_token'
            }
        }
        
        response = get_simulation_status_handler(event, {})
        
        # Verify response
        assert response['statusCode'] == 200
        
        response_body = json.loads(response['body'])
        assert response_body['job_id'] == 'job123'
        assert response_body['status'] == 'completed'
        assert response_body['report'] == {'result': 'pass'}
    
    @patch('src.api.simulations.get_user_from_token')
    def test_get_simulation_status_invalid_token(self, mock_get_user):
        """Test status retrieval with invalid token."""
        mock_get_user.side_effect = Exception("Invalid token")
        
        event = {
            'pathParameters': {'job_id': 'job123'},
            'headers': {
                'Authorization': 'Bearer invalid_token'
            }
        }
        
        response = get_simulation_status_handler(event, {})
        
        assert response['statusCode'] == 401
        response_body = json.loads(response['body'])
        assert 'error' in response_body
    
    @patch('src.api.simulations.get_user_from_token')
    @patch('src.api.simulations.boto3.resource')
    def test_get_simulation_status_not_found(self, mock_boto3, mock_get_user):
        """Test status retrieval for non-existent job."""
        mock_get_user.return_value = {'user_id': 'user123', 'github_id': 'github123'}
        
        # Mock DynamoDB response with no item
        mock_table = Mock()
        mock_table.get_item.return_value = {}
        mock_resource = Mock()
        mock_resource.Table.return_value = mock_table
        mock_boto3.return_value = mock_resource
        
        event = {
            'pathParameters': {'job_id': 'nonexistent'},
            'headers': {
                'Authorization': 'Bearer valid_token'
            }
        }
        
        response = get_simulation_status_handler(event, {})
        
        assert response['statusCode'] == 404
        response_body = json.loads(response['body'])
        assert 'error' in response_body
    
    @patch('src.api.simulations.get_user_from_token')
    @patch('src.api.simulations.boto3.resource')
    def test_get_simulation_status_access_denied(self, mock_boto3, mock_get_user):
        """Test status retrieval for job owned by different user."""
        mock_get_user.return_value = {'user_id': 'user123', 'github_id': 'github123'}
        
        # Mock DynamoDB response with job owned by different user
        mock_table = Mock()
        mock_table.get_item.return_value = {
            'Item': {
                'job_id': 'job123',
                'user_id': 'different_user',  # Different user
                'pr_url': 'https://github.com/owner/repo/pull/123',
                'status': 'completed',
                'created_at': '2023-01-01T00:00:00Z',
                'pr_owner': 'owner',
                'pr_repo': 'repo',
                'pr_number': 123
            }
        }
        mock_resource = Mock()
        mock_resource.Table.return_value = mock_table
        mock_boto3.return_value = mock_resource
        
        event = {
            'pathParameters': {'job_id': 'job123'},
            'headers': {
                'Authorization': 'Bearer valid_token'
            }
        }
        
        response = get_simulation_status_handler(event, {})
        
        assert response['statusCode'] == 403
        response_body = json.loads(response['body'])
        assert 'Access denied' in response_body['error']
    
    @patch('src.api.simulations.get_user_from_token')
    def test_get_simulation_status_missing_job_id(self, mock_get_user):
        """Test status retrieval with missing job_id parameter."""
        mock_get_user.return_value = {'user_id': 'user123', 'github_id': 'github123'}
        
        event = {
            'headers': {
                'Authorization': 'Bearer valid_token'
            }
        }
        
        response = get_simulation_status_handler(event, {})
        
        assert response['statusCode'] == 400
        response_body = json.loads(response['body'])
        assert 'error' in response_body
    
    @patch('src.api.simulations.get_user_from_token')
    @patch('src.api.simulations.boto3.resource')
    def test_get_simulation_status_dynamodb_error(self, mock_boto3, mock_get_user):
        """Test status retrieval with DynamoDB error."""
        mock_get_user.return_value = {'user_id': 'user123', 'github_id': 'github123'}
        
        # Mock DynamoDB error
        mock_table = Mock()
        mock_table.get_item.side_effect = Exception("DynamoDB error")
        mock_resource = Mock()
        mock_resource.Table.return_value = mock_table
        mock_boto3.return_value = mock_resource
        
        event = {
            'pathParameters': {'job_id': 'job123'},
            'headers': {
                'Authorization': 'Bearer valid_token'
            }
        }
        
        response = get_simulation_status_handler(event, {})
        
        assert response['statusCode'] == 500
        response_body = json.loads(response['body'])
        assert 'error' in response_body
