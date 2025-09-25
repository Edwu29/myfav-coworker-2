"""Tests for SQS service."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from src.services.sqs_service import SQSService


class TestSQSService:
    """Test cases for SQS service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sqs_service = SQSService()
    
    @patch('src.services.sqs_service.boto3.client')
    def test_get_queue_url_success(self, mock_boto3_client):
        """Test successful queue URL retrieval."""
        mock_sqs = Mock()
        mock_sqs.get_queue_url.return_value = {
            'QueueUrl': 'https://sqs.us-west-2.amazonaws.com/123456789/test-queue'
        }
        mock_boto3_client.return_value = mock_sqs
        
        service = SQSService()
        url = service.get_queue_url()
        
        assert url == 'https://sqs.us-west-2.amazonaws.com/123456789/test-queue'
        mock_sqs.get_queue_url.assert_called_once_with(QueueName='myfav-coworker-simulation-queue')
    
    @patch('src.services.sqs_service.boto3.client')
    def test_get_queue_url_cached(self, mock_boto3_client):
        """Test queue URL caching."""
        mock_sqs = Mock()
        mock_sqs.get_queue_url.return_value = {
            'QueueUrl': 'https://sqs.us-west-2.amazonaws.com/123456789/test-queue'
        }
        mock_boto3_client.return_value = mock_sqs
        
        service = SQSService()
        url1 = service.get_queue_url()
        url2 = service.get_queue_url()
        
        assert url1 == url2
        # Should only call AWS once due to caching
        mock_sqs.get_queue_url.assert_called_once()
    
    @patch('src.services.sqs_service.boto3.client')
    def test_get_queue_url_nonexistent_queue(self, mock_boto3_client):
        """Test queue URL retrieval with nonexistent queue."""
        mock_sqs = Mock()
        mock_sqs.get_queue_url.side_effect = ClientError(
            {'Error': {'Code': 'AWS.SimpleQueueService.NonExistentQueue'}},
            'GetQueueUrl'
        )
        mock_boto3_client.return_value = mock_sqs
        
        service = SQSService()
        
        with pytest.raises(Exception) as exc_info:
            service.get_queue_url()
        
        assert "not found" in str(exc_info.value)
    
    @patch('src.services.sqs_service.boto3.client')
    def test_get_queue_url_client_error(self, mock_boto3_client):
        """Test queue URL retrieval with client error."""
        mock_sqs = Mock()
        mock_sqs.get_queue_url.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied'}},
            'GetQueueUrl'
        )
        mock_boto3_client.return_value = mock_sqs
        
        service = SQSService()
        
        with pytest.raises(Exception) as exc_info:
            service.get_queue_url()
        
        assert "Failed to retrieve SQS queue URL" in str(exc_info.value)
    
    @patch('src.services.sqs_service.boto3.client')
    def test_send_message_success(self, mock_boto3_client):
        """Test successful message sending."""
        mock_sqs = Mock()
        mock_sqs.get_queue_url.return_value = {
            'QueueUrl': 'https://sqs.us-west-2.amazonaws.com/123456789/test-queue'
        }
        mock_sqs.send_message.return_value = {
            'MessageId': 'test-message-id-123'
        }
        mock_boto3_client.return_value = mock_sqs
        
        service = SQSService()
        message_body = {
            "job_id": "job123",
            "action": "start_simulation"
        }
        
        message_id = service.send_message(message_body)
        
        assert message_id == 'test-message-id-123'
        mock_sqs.send_message.assert_called_once_with(
            QueueUrl='https://sqs.us-west-2.amazonaws.com/123456789/test-queue',
            MessageBody=json.dumps(message_body)
        )
    
    @patch('src.services.sqs_service.boto3.client')
    def test_send_message_failure(self, mock_boto3_client):
        """Test message sending failure."""
        mock_sqs = Mock()
        mock_sqs.get_queue_url.return_value = {
            'QueueUrl': 'https://sqs.us-west-2.amazonaws.com/123456789/test-queue'
        }
        mock_sqs.send_message.side_effect = Exception("Network error")
        mock_boto3_client.return_value = mock_sqs
        
        service = SQSService()
        message_body = {"job_id": "job123"}
        
        with pytest.raises(Exception) as exc_info:
            service.send_message(message_body)
        
        assert "Failed to send message to queue" in str(exc_info.value)
    
    @patch('src.services.sqs_service.boto3.client')
    def test_validate_environment_success(self, mock_boto3_client):
        """Test successful environment validation."""
        mock_sqs = Mock()
        mock_sqs.get_queue_url.return_value = {
            'QueueUrl': 'https://sqs.us-west-2.amazonaws.com/123456789/test-queue'
        }
        mock_boto3_client.return_value = mock_sqs
        
        service = SQSService()
        result = service.validate_environment()
        
        assert result is True
    
    @patch('src.services.sqs_service.boto3.client')
    def test_validate_environment_failure(self, mock_boto3_client):
        """Test environment validation failure."""
        mock_sqs = Mock()
        mock_sqs.get_queue_url.side_effect = Exception("Connection failed")
        mock_boto3_client.return_value = mock_sqs
        
        service = SQSService()
        result = service.validate_environment()
        
        assert result is False
    
    @patch.dict('os.environ', {'SIMULATION_QUEUE_NAME': 'custom-queue-name'})
    @patch('src.services.sqs_service.boto3.client')
    def test_custom_queue_name(self, mock_boto3_client):
        """Test using custom queue name from environment."""
        mock_sqs = Mock()
        mock_sqs.get_queue_url.return_value = {
            'QueueUrl': 'https://sqs.us-west-2.amazonaws.com/123456789/custom-queue'
        }
        mock_boto3_client.return_value = mock_sqs
        
        service = SQSService()
        service.get_queue_url()
        
        mock_sqs.get_queue_url.assert_called_once_with(QueueName='custom-queue-name')
    
    @patch('src.services.sqs_service.boto3.client')
    def test_receive_message_success(self, mock_boto3_client):
        """Test successful message receiving."""
        mock_sqs = Mock()
        mock_sqs.get_queue_url.return_value = {
            'QueueUrl': 'https://sqs.us-west-2.amazonaws.com/123456789/test-queue'
        }
        mock_sqs.receive_message.return_value = {
            'Messages': [
                {
                    'Body': '{"action": "start_simulation", "job_id": "test123"}',
                    'ReceiptHandle': 'receipt-handle-123'
                }
            ]
        }
        mock_boto3_client.return_value = mock_sqs
        
        service = SQSService()
        messages = service.receive_message(max_messages=1, wait_time=5)
        
        assert len(messages) == 1
        assert 'Body' in messages[0]
        assert 'ReceiptHandle' in messages[0]
        mock_sqs.receive_message.assert_called_once_with(
            QueueUrl='https://sqs.us-west-2.amazonaws.com/123456789/test-queue',
            MaxNumberOfMessages=1,
            WaitTimeSeconds=5,
            VisibilityTimeout=300
        )
    
    @patch('src.services.sqs_service.boto3.client')
    def test_receive_message_empty_queue(self, mock_boto3_client):
        """Test receiving messages from empty queue."""
        mock_sqs = Mock()
        mock_sqs.get_queue_url.return_value = {
            'QueueUrl': 'https://sqs.us-west-2.amazonaws.com/123456789/test-queue'
        }
        mock_sqs.receive_message.return_value = {}  # No messages
        mock_boto3_client.return_value = mock_sqs
        
        service = SQSService()
        messages = service.receive_message()
        
        assert len(messages) == 0
    
    @patch('src.services.sqs_service.boto3.client')
    def test_receive_message_failure(self, mock_boto3_client):
        """Test message receiving failure."""
        mock_sqs = Mock()
        mock_sqs.get_queue_url.return_value = {
            'QueueUrl': 'https://sqs.us-west-2.amazonaws.com/123456789/test-queue'
        }
        mock_sqs.receive_message.side_effect = Exception("Network error")
        mock_boto3_client.return_value = mock_sqs
        
        service = SQSService()
        
        with pytest.raises(Exception) as exc_info:
            service.receive_message()
        
        assert "Failed to receive messages from queue" in str(exc_info.value)
    
    @patch('src.services.sqs_service.boto3.client')
    def test_delete_message_success(self, mock_boto3_client):
        """Test successful message deletion."""
        mock_sqs = Mock()
        mock_sqs.get_queue_url.return_value = {
            'QueueUrl': 'https://sqs.us-west-2.amazonaws.com/123456789/test-queue'
        }
        mock_boto3_client.return_value = mock_sqs
        
        service = SQSService()
        result = service.delete_message('receipt-handle-123')
        
        assert result is True
        mock_sqs.delete_message.assert_called_once_with(
            QueueUrl='https://sqs.us-west-2.amazonaws.com/123456789/test-queue',
            ReceiptHandle='receipt-handle-123'
        )
    
    @patch('src.services.sqs_service.boto3.client')
    def test_delete_message_failure(self, mock_boto3_client):
        """Test message deletion failure."""
        mock_sqs = Mock()
        mock_sqs.get_queue_url.return_value = {
            'QueueUrl': 'https://sqs.us-west-2.amazonaws.com/123456789/test-queue'
        }
        mock_sqs.delete_message.side_effect = Exception("Network error")
        mock_boto3_client.return_value = mock_sqs
        
        service = SQSService()
        
        with pytest.raises(Exception) as exc_info:
            service.delete_message('receipt-handle-123')
        
        assert "Failed to delete message from queue" in str(exc_info.value)
