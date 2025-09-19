import pytest
import sys
import os
from datetime import datetime

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from models.user import User, GitHubUserProfile, AuthTokenResponse


class TestUser:
    """Test cases for User model."""
    
    def test_user_creation(self):
        """Test User model creation with all fields."""
        now = datetime.utcnow()
        user = User(
            user_id="test-user-123",
            github_id="12345",
            github_username="testuser",
            encrypted_github_token="encrypted_token_data",
            created_at=now,
            last_login_at=now
        )
        
        assert user.user_id == "test-user-123"
        assert user.github_id == "12345"
        assert user.github_username == "testuser"
        assert user.encrypted_github_token == "encrypted_token_data"
        assert user.created_at == now
        assert user.last_login_at == now
    
    def test_user_creation_with_defaults(self):
        """Test User model creation with default values."""
        user = User(
            user_id="test-user-123",
            github_id="12345",
            github_username="testuser",
            encrypted_github_token="encrypted_token_data"
        )
        
        assert user.user_id == "test-user-123"
        assert user.github_id == "12345"
        assert user.github_username == "testuser"
        assert user.encrypted_github_token == "encrypted_token_data"
        assert isinstance(user.created_at, datetime)
        assert user.last_login_at is None
    
    def test_to_dynamodb_item(self):
        """Test conversion to DynamoDB item format."""
        now = datetime.utcnow()
        user = User(
            user_id="test-user-123",
            github_id="12345",
            github_username="testuser",
            encrypted_github_token="encrypted_token_data",
            created_at=now,
            last_login_at=now
        )
        
        item = user.to_dynamodb_item()
        
        assert item["PK"] == "USER#12345"
        assert item["SK"] == "METADATA"
        assert item["user_id"] == "test-user-123"
        assert item["github_id"] == "12345"
        assert item["github_username"] == "testuser"
        assert item["encrypted_github_token"] == "encrypted_token_data"
        assert item["created_at"] == now.isoformat()
        assert item["last_login_at"] == now.isoformat()
    
    def test_from_dynamodb_item(self):
        """Test creation from DynamoDB item."""
        now = datetime.utcnow()
        item = {
            "PK": "USER#12345",
            "SK": "METADATA",
            "user_id": "test-user-123",
            "github_id": "12345",
            "github_username": "testuser",
            "encrypted_github_token": "encrypted_token_data",
            "created_at": now.isoformat(),
            "last_login_at": now.isoformat()
        }
        
        user = User.from_dynamodb_item(item)
        
        assert user.user_id == "test-user-123"
        assert user.github_id == "12345"
        assert user.github_username == "testuser"
        assert user.encrypted_github_token == "encrypted_token_data"
        assert user.created_at == now
        assert user.last_login_at == now


class TestGitHubUserProfile:
    """Test cases for GitHubUserProfile model."""
    
    def test_github_profile_creation(self):
        """Test GitHubUserProfile creation with all fields."""
        profile = GitHubUserProfile(
            id=12345,
            login="testuser",
            name="Test User",
            email="test@example.com",
            avatar_url="https://github.com/avatar.jpg"
        )
        
        assert profile.id == 12345
        assert profile.login == "testuser"
        assert profile.name == "Test User"
        assert profile.email == "test@example.com"
        assert profile.avatar_url == "https://github.com/avatar.jpg"


class TestAuthTokenResponse:
    """Test cases for AuthTokenResponse model."""
    
    def test_auth_token_response_creation(self):
        """Test AuthTokenResponse creation with all fields."""
        response = AuthTokenResponse(
            access_token="jwt_token_here",
            token_type="Bearer",
            expires_in=3600
        )
        
        assert response.access_token == "jwt_token_here"
        assert response.token_type == "Bearer"
        assert response.expires_in == 3600
