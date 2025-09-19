import os
import uuid
import logging
from datetime import datetime
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from src.models.user import User, GitHubUserProfile
from src.utils.encryption import create_token_encryptor


logger = logging.getLogger(__name__)


class UserService:
    """Service for user data management in DynamoDB."""
    
    def __init__(self):
        """Initialize user service with DynamoDB client."""
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.getenv('DYNAMODB_TABLE_NAME', 'myfav-coworker-main')
        self.table = self.dynamodb.Table(self.table_name)
        self.encryptor = create_token_encryptor()
    
    def create_user(self, github_profile: GitHubUserProfile, github_token: str) -> User:
        """Create a new user from GitHub profile and token."""
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
    
    def get_decrypted_github_token(self, user: User) -> str:
        """Get decrypted GitHub token for a user."""
        try:
            return self.encryptor.decrypt_token(user.encrypted_github_token)
        except Exception as e:
            logger.error(f"Failed to decrypt GitHub token for user {user.user_id}: {e}")
            raise RuntimeError("Failed to decrypt GitHub token")
    
    def update_github_token(self, github_id: str, new_token: str) -> bool:
        """Update user's GitHub token."""
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
