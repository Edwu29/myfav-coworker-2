import os
import uuid
import logging
from datetime import datetime
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from models.user import User, GitHubUserProfile
from utils.encryption import create_token_encryptor


logger = logging.getLogger(__name__)


class UserService:
    """Service for user data management in DynamoDB."""
    
    def __init__(self):
        """
        Initialize the UserService by configuring the DynamoDB resource, selecting the DynamoDB table, creating the table resource, and initializing the token encryptor.
        
        If the environment variable DYNAMODB_ENDPOINT_URL is set, use that endpoint and the local table name "myfav-coworker-main-local" with dummy credentials; otherwise create a DynamoDB resource in "us-east-1" and determine the table name from DYNAMODB_TABLE_NAME (treating "MainTable" as "myfav-coworker-main"). The method sets self.dynamodb, self.table_name, self.table, and self.encryptor, and logs the initialization details.
        """
        # Check if explicitly using local DynamoDB endpoint
        local_endpoint = os.getenv('DYNAMODB_ENDPOINT_URL', None)
        
        if local_endpoint:
            # Use local DynamoDB with explicit endpoint
            self.dynamodb = boto3.resource(
                'dynamodb',
                endpoint_url=local_endpoint,
                region_name='us-east-1',
                aws_access_key_id='dummy',
                aws_secret_access_key='dummy'
            )
            self.table_name = 'myfav-coworker-main-local'
        else:
            # Use AWS DynamoDB (default for both local SAM and deployed Lambda)
            self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
            table_name_env = os.getenv('DYNAMODB_TABLE_NAME', 'myfav-coworker-main')
            # SAM local doesn't resolve CloudFormation references properly
            if table_name_env == 'MainTable':
                self.table_name = 'myfav-coworker-main'
            else:
                self.table_name = table_name_env
        
        self.table = self.dynamodb.Table(self.table_name)
        self.encryptor = create_token_encryptor()
        
        # Debug logging
        logger.info(f"UserService initialized with table: {self.table_name}, endpoint: {local_endpoint if local_endpoint else 'AWS'}")
    
    def create_user(self, github_profile: GitHubUserProfile, github_token: str) -> User:
        """
        Create and persist a new User record from a GitHub profile and token.
        
        Parameters:
            github_profile (GitHubUserProfile): GitHub profile containing `id` and `login` used to populate the user record.
            github_token (str): Plaintext GitHub access token to be encrypted and stored on the user record.
        
        Returns:
            User: The created User with an assigned `user_id`, encrypted token, and `created_at`/`last_login_at` timestamps.
        
        Raises:
            RuntimeError: If writing the user record to DynamoDB fails.
        """
        user_id = str(uuid.uuid4())
        encrypted_token = self.encryptor.encrypt_token(github_token)
        
        user = User(
            user_id=user_id,
            github_id=str(github_profile.id),
            github_username=github_profile.login,
            encrypted_github_token=encrypted_token,
            created_at=datetime.utcnow(),
            last_login_at=datetime.utcnow()
        )
        
        try:
            self.table.put_item(Item=user.to_dynamodb_item())
            logger.info(f"Created new user: {user.github_username}")
            return user
        except ClientError as e:
            logger.error(f"Failed to create user: {e}")
            raise RuntimeError(f"Failed to create user: {e}")
    
    def get_user_by_github_id(self, github_id: str) -> Optional[User]:
        """Retrieve user by GitHub ID."""
        try:
            response = self.table.get_item(
                Key={
                    'PK': f'USER#{github_id}',
                    'SK': 'METADATA'
                }
            )
            
            if 'Item' in response:
                user = User.from_dynamodb_item(response['Item'])
                logger.info(f"Retrieved user: {user.github_username}")
                return user
            
            return None
            
        except ClientError as e:
            logger.error(f"Failed to retrieve user by GitHub ID {github_id}: {e}")
            return None
    
    def get_user_by_user_id(self, user_id: str) -> Optional[User]:
        """Retrieve user by user ID (requires scan - use sparingly)."""
        try:
            response = self.table.scan(
                FilterExpression='user_id = :user_id',
                ExpressionAttributeValues={':user_id': user_id}
            )
            
            if response['Items']:
                user = User.from_dynamodb_item(response['Items'][0])
                logger.info(f"Retrieved user by user_id: {user.github_username}")
                return user
            
            return None
            
        except ClientError as e:
            logger.error(f"Failed to retrieve user by user ID {user_id}: {e}")
            return None
    
    def update_last_login(self, github_id: str) -> bool:
        """Update user's last login timestamp."""
        try:
            self.table.update_item(
                Key={
                    'PK': f'USER#{github_id}',
                    'SK': 'METADATA'
                },
                UpdateExpression='SET last_login_at = :timestamp',
                ExpressionAttributeValues={
                    ':timestamp': datetime.utcnow().isoformat()
                }
            )
            logger.info(f"Updated last login for GitHub ID: {github_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to update last login for GitHub ID {github_id}: {e}")
            return False
    
    def update_user(self, user: User) -> User:
        """Update user information in DynamoDB."""
        try:
            item = user.to_dynamodb_item()
            self.table.put_item(Item=item)
            logger.info(f"Updated user: {user.user_id}")
            return user
        except ClientError as e:
            logger.error(f"Failed to update user {user.user_id}: {e}")
            raise RuntimeError(f"Failed to update user: {e}")
    
    def get_decrypted_github_token(self, github_id: str) -> str:
        """
        Retrieve and decrypt a user's GitHub access token using their GitHub ID.
        
        Parameters:
            github_id (str): The GitHub account ID used to look up the user.
        
        Returns:
            str: The decrypted GitHub access token.
        
        Raises:
            RuntimeError: If the user is not found or if decryption fails.
        """
        try:
            user = self.get_user_by_github_id(github_id)
            if not user:
                raise RuntimeError("User not found")
            return self.encryptor.decrypt_token(user.encrypted_github_token)
        except Exception as e:
            logger.error(f"Failed to decrypt GitHub token for GitHub ID {github_id}: {e}")
            raise RuntimeError("Failed to decrypt GitHub token")
    
    def get_decrypted_github_token_by_user_id(self, user_id: str) -> str:
        """
        Retrieve and decrypt a user's GitHub access token by user ID.
        
        Parameters:
            user_id (str): The user's identifier (UUID).
        
        Returns:
            str: The decrypted GitHub access token.
        
        Raises:
            RuntimeError: If no user exists for the given user_id or if decryption/retrieval fails.
        """
        try:
            user = self.get_user_by_user_id(user_id)
            if not user:
                raise RuntimeError("User not found")
            return self.encryptor.decrypt_token(user.encrypted_github_token)
        except Exception as e:
            logger.error(f"Failed to decrypt GitHub token for user ID {user_id}: {e}")
            raise RuntimeError("Failed to decrypt GitHub token")
    
    def update_github_token(self, github_id: str, new_token: str) -> bool:
        """
        Update the stored GitHub access token for a user by replacing it with an encrypted value.
        
        Parameters:
            github_id (str): The GitHub identifier for the user whose token will be updated.
            new_token (str): The plaintext GitHub access token to encrypt and store.
        
        Returns:
            bool: `True` if the token was successfully updated in the database, `False` otherwise.
        """
        try:
            encrypted_token = self.encryptor.encrypt_token(new_token)
            
            self.table.update_item(
                Key={
                    'PK': f'USER#{github_id}',
                    'SK': 'METADATA'
                },
                UpdateExpression='SET encrypted_github_token = :token',
                ExpressionAttributeValues={
                    ':token': encrypted_token
                }
            )
            logger.info(f"Updated GitHub token for GitHub ID: {github_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to update GitHub token for GitHub ID {github_id}: {e}")
            return False
