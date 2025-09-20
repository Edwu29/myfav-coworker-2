import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from src.utils.jwt_auth import JWTManager, get_jwt_secret, create_jwt_manager


class TestJWTManager:
    """Test cases for JWTManager class."""
    
    def test_generate_token(self):
        """Test JWT token generation."""
        secret = "test_secret_key"
        manager = JWTManager(secret)
        
        user_id = "user-123"
        github_id = "github-456"
        
        token = manager.generate_token(user_id, github_id)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify payload
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert payload["user_id"] == user_id
        assert payload["github_id"] == github_id
        assert payload["iss"] == "myfav-coworker"
        assert "iat" in payload
        assert "exp" in payload
    
    def test_generate_token_custom_expiry(self):
        """Test JWT token generation with custom expiry."""
        secret = "test_secret_key"
        manager = JWTManager(secret)
        
        user_id = "user-123"
        github_id = "github-456"
        expires_in = 7200  # 2 hours
        
        token = manager.generate_token(user_id, github_id, expires_in)
        
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        
        # Check expiry time
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        iat_time = datetime.utcfromtimestamp(payload["iat"])
        time_diff = exp_time - iat_time
        
        assert abs(time_diff.total_seconds() - expires_in) < 1  # Allow 1 second tolerance
    
    def test_validate_token_valid(self):
        """Test validation of valid JWT token."""
        secret = "test_secret_key"
        manager = JWTManager(secret)
        
        user_id = "user-123"
        github_id = "github-456"
        
        token = manager.generate_token(user_id, github_id)
        payload = manager.validate_token(token)
        
        assert payload is not None
        assert payload["user_id"] == user_id
        assert payload["github_id"] == github_id
        assert payload["iss"] == "myfav-coworker"
    
    def test_validate_token_expired(self):
        """Test validation of expired JWT token."""
        secret = "test_secret_key"
        manager = JWTManager(secret)
        
        # Create token that expires immediately
        user_id = "user-123"
        github_id = "github-456"
        expires_in = -1  # Already expired
        
        token = manager.generate_token(user_id, github_id, expires_in)
        payload = manager.validate_token(token)
        
        assert payload is None
    
    def test_validate_token_invalid_signature(self):
        """Test validation of token with invalid signature."""
        secret1 = "test_secret_key_1"
        secret2 = "test_secret_key_2"
        
        manager1 = JWTManager(secret1)
        manager2 = JWTManager(secret2)
        
        user_id = "user-123"
        github_id = "github-456"
        
        token = manager1.generate_token(user_id, github_id)
        payload = manager2.validate_token(token)  # Different secret
        
        assert payload is None
    
    def test_validate_token_malformed(self):
        """Test validation of malformed JWT token."""
        secret = "test_secret_key"
        manager = JWTManager(secret)
        
        malformed_token = "not.a.valid.jwt.token"
        payload = manager.validate_token(malformed_token)
        
        assert payload is None
    
    def test_refresh_token_valid(self):
        """Test refreshing a valid JWT token."""
        import time
        secret = "test_secret_key"
        manager = JWTManager(secret)
        
        user_id = "user-123"
        github_id = "github-456"
        
        original_token = manager.generate_token(user_id, github_id)
        time.sleep(1)  # Ensure different timestamp
        refreshed_token = manager.refresh_token(original_token)
        
        assert refreshed_token is not None
        assert refreshed_token != original_token
        
        # Verify refreshed token is valid
        payload = manager.validate_token(refreshed_token)
        assert payload["user_id"] == user_id
        assert payload["github_id"] == github_id
    
    def test_refresh_token_invalid(self):
        """Test refreshing an invalid JWT token."""
        secret = "test_secret_key"
        manager = JWTManager(secret)
        
        invalid_token = "invalid.jwt.token"
        refreshed_token = manager.refresh_token(invalid_token)
        
        assert refreshed_token is None
    
    def test_custom_algorithm(self):
        """Test JWT manager with custom algorithm."""
        secret = "test_secret_key"
        algorithm = "HS512"
        manager = JWTManager(secret, algorithm)
        
        user_id = "user-123"
        github_id = "github-456"
        
        token = manager.generate_token(user_id, github_id)
        payload = manager.validate_token(token)
        
        assert payload is not None
        assert payload["user_id"] == user_id
        
        # Verify algorithm by decoding manually
        header = jwt.get_unverified_header(token)
        assert header["alg"] == algorithm


class TestGetJWTSecret:
    """Test cases for get_jwt_secret function."""
    
    @patch.dict('os.environ', {'JWT_SECRET_KEY': 'env_secret_123'})
    def test_get_secret_from_environment(self):
        """Test getting JWT secret from environment variable."""
        secret = get_jwt_secret()
        assert secret == 'env_secret_123'
    
    @patch.dict('os.environ', {}, clear=True)
    @patch('boto3.client')
    def test_get_secret_from_parameter_store(self, mock_boto_client):
        """Test getting JWT secret from AWS Parameter Store."""
        mock_ssm = MagicMock()
        mock_boto_client.return_value = mock_ssm
        mock_ssm.get_parameter.return_value = {
            'Parameter': {'Value': 'parameter_store_secret_456'}
        }
        
        secret = get_jwt_secret()
        
        assert secret == 'parameter_store_secret_456'
        mock_ssm.get_parameter.assert_called_once_with(
            Name='/myfav-coworker/jwt-secret-key',
            WithDecryption=True
        )
    
    @patch.dict('os.environ', {}, clear=True)
    @patch('boto3.client')
    def test_get_secret_parameter_store_failure(self, mock_boto_client):
        """Test handling of Parameter Store failure."""
        mock_ssm = MagicMock()
        mock_boto_client.return_value = mock_ssm
        mock_ssm.get_parameter.side_effect = Exception("Parameter not found")
        
        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY environment variable not set and AWS Parameter Store unavailable"):
            get_jwt_secret()


class TestCreateJWTManager:
    """Test cases for create_jwt_manager function."""
    
    @patch('src.utils.jwt_auth.get_jwt_secret')
    def test_create_jwt_manager(self, mock_get_secret):
        """Test creating JWTManager instance."""
        mock_get_secret.return_value = "test_secret_789"
        
        manager = create_jwt_manager()
        
        assert isinstance(manager, JWTManager)
        assert manager.secret_key == "test_secret_789"
        assert manager.algorithm == "HS256"
        mock_get_secret.assert_called_once()
    
    @patch('src.utils.jwt_auth.get_jwt_secret')
    def test_create_jwt_manager_secret_failure(self, mock_get_secret):
        """Test handling of secret retrieval failure."""
        mock_get_secret.side_effect = RuntimeError("Secret retrieval failed")
        
        with pytest.raises(RuntimeError, match="Secret retrieval failed"):
            create_jwt_manager()
