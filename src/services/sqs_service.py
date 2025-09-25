"""
SQS service for managing simulation job queues.
"""

import os
import logging
import boto3
from typing import Dict, Any, List
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class SQSService:
    """Service for managing SQS operations for simulation jobs."""
    
    def __init__(self):
        """Initialize SQS service with configuration."""
        # Use us-east-1 region where your queue exists
        self.sqs_client = boto3.client('sqs', region_name='us-east-1')
        self.queue_name = os.getenv('SIMULATION_QUEUE_NAME', 'myfav-coworker-simulation-queue')
        self._queue_url = os.getenv('SQS_QUEUE_URL', None)
        
    def get_queue_url(self) -> str:
        """
        Get SQS queue URL for simulation jobs.
        
        Returns:
            Queue URL string
            
        Raises:
            Exception: If queue URL cannot be retrieved
        """
        if self._queue_url:
            return self._queue_url
            
        try:
            response = self.sqs_client.get_queue_url(QueueName=self.queue_name)
            self._queue_url = response['QueueUrl']
            logger.info(f"Retrieved SQS queue URL: {self._queue_url}")
            return self._queue_url
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AWS.SimpleQueueService.NonExistentQueue':
                logger.error(f"SQS queue '{self.queue_name}' does not exist")
                raise Exception(f"SQS queue '{self.queue_name}' not found")
            else:
                logger.error(f"Failed to get SQS queue URL: {e}")
                raise Exception(f"Failed to retrieve SQS queue URL: {str(e)}")
                
        except Exception as e:
            logger.error(f"Unexpected error getting SQS queue URL: {e}")
            raise Exception(f"Failed to get SQS queue URL: {str(e)}")
    
    def send_message(self, message_body: Dict[str, Any]) -> str:
        """
        Send message to simulation queue.
        
        Args:
            message_body: Message data to send
            
        Returns:
            Message ID
            
        Raises:
            Exception: If message cannot be sent
        """
        try:
            import json
            logging.info(f"Sending SQS message: {message_body}")
            queue_url = self.get_queue_url()
            logging.info(f"Sending SQS message to queue: {queue_url}")
            
            response = self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message_body)
            )
            logging.info(f"SQS message sent: {response}")
            
            message_id = response['MessageId']
            logger.info(f"Sent SQS message: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to send SQS message: {e}")
            raise Exception(f"Failed to send message to queue: {str(e)}")
    
    def receive_message(self, max_messages: int = 1, wait_time: int = 5) -> List[Dict[str, Any]]:
        """
        Receive messages from simulation queue.
        
        Args:
            max_messages: Maximum number of messages to receive (1-10)
            wait_time: Long polling wait time in seconds (0-20)
            
        Returns:
            List of message dictionaries
            
        Raises:
            Exception: If messages cannot be received
        """
        try:
            queue_url = self.get_queue_url()
            
            response = self.sqs_client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=min(max_messages, 10),
                WaitTimeSeconds=min(wait_time, 20),
                VisibilityTimeout=300  # 5 minutes
            )
            
            messages = response.get('Messages', [])
            logger.info(f"Received {len(messages)} messages from SQS queue")
            return messages
            
        except Exception as e:
            logger.error(f"Failed to receive SQS messages: {e}")
            raise Exception(f"Failed to receive messages from queue: {str(e)}")
    
    def delete_message(self, receipt_handle: str) -> bool:
        """
        Delete a processed message from the queue.
        
        Args:
            receipt_handle: Receipt handle from received message
            
        Returns:
            True if message was deleted successfully
            
        Raises:
            Exception: If message cannot be deleted
        """
        try:
            queue_url = self.get_queue_url()
            
            self.sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
            
            logger.info("Successfully deleted message from SQS queue")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete SQS message: {e}")
            raise Exception(f"Failed to delete message from queue: {str(e)}")

    def validate_environment(self) -> bool:
        """
        Validate SQS service environment configuration.
        
        Returns:
            True if environment is valid
        """
        try:
            # Test queue URL retrieval
            self.get_queue_url()
            logger.info("SQS service environment validation passed")
            return True
            
        except Exception as e:
            logger.error(f"SQS service environment validation failed: {e}")
            return False
