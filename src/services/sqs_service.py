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
        """
        Set up the SQS client and default queue configuration for the service.
        
        Reads SIMULATION_QUEUE_NAME (default 'myfav-coworker-simulation-queue') to determine the queue name, reads SQS_QUEUE_URL to initialize a cached queue URL if present, and creates a boto3 SQS client configured for region 'us-east-1'.
        """
        # Use us-east-1 region where your queue exists
        self.sqs_client = boto3.client('sqs', region_name='us-east-1')
        self.queue_name = os.getenv('SIMULATION_QUEUE_NAME', 'myfav-coworker-simulation-queue')
        self._queue_url = os.getenv('SQS_QUEUE_URL', None)
        
    def get_queue_url(self) -> str:
        """
        Retrieve and cache the SQS queue URL for the configured simulation queue.
        
        If the URL is already cached, the cached value is returned. Otherwise the method queries AWS SQS for the queue URL, caches it, and returns it.
        
        Returns:
            str: The SQS queue URL.
        
        Raises:
            Exception: If the configured queue does not exist.
            Exception: If the queue URL cannot be retrieved for any other reason.
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
        Send a JSON-serializable dictionary as a message to the configured simulation SQS queue.
        
        Args:
            message_body (Dict[str, Any]): The message payload; will be serialized to JSON and sent as the SQS MessageBody.
        
        Returns:
            str: The SQS MessageId assigned to the sent message.
        
        Raises:
            Exception: If the message cannot be sent; rethrows a descriptive exception on failure.
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
        Retrieve a batch of messages from the simulation SQS queue.
        
        Parameters:
            max_messages (int): Requested maximum number of messages; value will be capped at 10.
            wait_time (int): Long-poll wait time in seconds; value will be capped at 20.
        
        Returns:
            List[Dict[str, Any]]: A list of message dictionaries as returned by boto3 SQS (each typically contains keys such as `MessageId`, `ReceiptHandle`, `Body`, and `Attributes`). Returns an empty list if no messages are available.
        
        Raises:
            Exception: If messages cannot be retrieved from the queue.
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
        Delete a processed message from the configured SQS queue.
        
        Parameters:
            receipt_handle (str): The SQS receipt handle obtained from a received message.
        
        Returns:
            bool: `True` if the message was deleted successfully.
        
        Raises:
            Exception: If the message could not be deleted.
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
        Check that the SQS service is properly configured by attempting to retrieve the queue URL.
        
        Returns:
            bool: `True` if the queue URL could be retrieved and configuration appears valid, `False` otherwise.
        """
        try:
            # Test queue URL retrieval
            self.get_queue_url()
            logger.info("SQS service environment validation passed")
            return True
            
        except Exception as e:
            logger.error(f"SQS service environment validation failed: {e}")
            return False
