import pytest
from unittest.mock import patch, MagicMock
from src.utils.auth_middleware import require_auth, get_current_user
from src.models.user import User


class TestRequireAuth:
    """Test cases for require_auth decorator."""
    
    @patch('src.utils.auth_middleware.create_jwt_manager')
    @patch('src.utils.auth_middleware.UserService')
    def test_require_auth_valid_token(self, mock_user_service_class, mock_create_jwt_manager):
        """Test authentication with valid JWT token."""
        # Mock JWT manager
        mock_jwt_manager = MagicMock()
        mock_create_jwt_manager.return_value = mock_jwt_manager
        mock_jwt_manager.validate_token.return_value = {
            'user_id': 'user-123',
            'github_id': 'github-456',
            'iss': 'myfav-coworker'
        }
        
        # Mock user service
        mock_user_service = MagicMock()
        mock_user_service_class.return_value = mock_user_service
        mock_user = User(
            user_id='user-123',
            github_id='github-456',
            github_username='testuser',
            encrypted_github_token='encrypted_token'
        )
        mock_user_service.get_user_by_github_id.return_value = mock_user
        
        # Mock endpoint function
        @require_auth
        def mock_endpoint(event, context):
            return {'statusCode': 200, 'body': 'success'}
        
        # Test event with valid Authorization header
        event = {
            'headers': {
                'Authorization': 'Bearer valid_jwt_token'
            }
        }
        context = {}
        
        result = mock_endpoint(event, context)
        
        assert result['statusCode'] == 200
        assert result['body'] == 'success'
        assert 'user' in event
        assert event['user']['user_id'] == 'user-123'
        assert event['user']['github_id'] == 'github-456'
        assert event['user']['github_username'] == 'testuser'
        
        mock_jwt_manager.validate_token.assert_called_once_with('valid_jwt_token')
        mock_user_service.get_user_by_github_id.assert_called_once_with('github-456')
    
    def test_require_auth_missing_header(self):
        """Test authentication with missing Authorization header."""
        @require_auth
        def mock_endpoint(event, context):
            return {'statusCode': 200, 'body': 'success'}
        
        event = {'headers': {}}
        context = {}
        
        result = mock_endpoint(event, context)
        
        assert result['statusCode'] == 401
        assert 'Missing Authorization header' in result['body']
        assert result['headers']['Content-Type'] == 'application/json'
    
    def test_require_auth_invalid_header_format(self):
        """Test authentication with invalid Authorization header format."""
        @require_auth
        def mock_endpoint(event, context):
            return {'statusCode': 200, 'body': 'success'}
        
        event = {
            'headers': {
                'Authorization': 'InvalidFormat token_here'
            }
        }
        context = {}
        
        result = mock_endpoint(event, context)
        
        assert result['statusCode'] == 401
        assert 'Invalid Authorization header format' in result['body']
    
    @patch('src.utils.auth_middleware.create_jwt_manager')
    def test_require_auth_invalid_token(self, mock_create_jwt_manager):
        """Test authentication with invalid JWT token."""
        # Mock JWT manager to return None for invalid token
        mock_jwt_manager = MagicMock()
        mock_create_jwt_manager.return_value = mock_jwt_manager
        mock_jwt_manager.validate_token.return_value = None
        
        @require_auth
        def mock_endpoint(event, context):
            return {'statusCode': 200, 'body': 'success'}
        
        event = {
            'headers': {
                'Authorization': 'Bearer invalid_jwt_token'
            }
        }
        context = {}
        
        result = mock_endpoint(event, context)
        
        assert result['statusCode'] == 401
        assert 'Invalid or expired token' in result['body']
        mock_jwt_manager.validate_token.assert_called_once_with('invalid_jwt_token')
    
    @patch('src.utils.auth_middleware.create_jwt_manager')
    @patch('src.utils.auth_middleware.UserService')
    def test_require_auth_user_not_found(self, mock_user_service_class, mock_create_jwt_manager):
        """Test authentication when user is not found in database."""
        # Mock JWT manager
        mock_jwt_manager = MagicMock()
        mock_create_jwt_manager.return_value = mock_jwt_manager
        mock_jwt_manager.validate_token.return_value = {
            'user_id': 'user-123',
            'github_id': 'github-456',
            'iss': 'myfav-coworker'
        }
        
        # Mock user service to return None (user not found)
        mock_user_service = MagicMock()
        mock_user_service_class.return_value = mock_user_service
        mock_user_service.get_user_by_github_id.return_value = None
        
        @require_auth
        def mock_endpoint(event, context):
            return {'statusCode': 200, 'body': 'success'}
        
        event = {
            'headers': {
                'Authorization': 'Bearer valid_jwt_token'
            }
        }
        context = {}
        
        result = mock_endpoint(event, context)
        
        assert result['statusCode'] == 401
        assert 'User not found' in result['body']
        mock_user_service.get_user_by_github_id.assert_called_once_with('github-456')
    
    @patch('src.utils.auth_middleware.create_jwt_manager')
    def test_require_auth_case_insensitive_header(self, mock_create_jwt_manager):
        """Test authentication with lowercase authorization header."""
        # Mock JWT manager to return None for invalid token
        mock_jwt_manager = MagicMock()
        mock_create_jwt_manager.return_value = mock_jwt_manager
        mock_jwt_manager.validate_token.return_value = None
        
        @require_auth
        def mock_endpoint(event, context):
            return {'statusCode': 200, 'body': 'success'}
        
        event = {
            'headers': {
                'authorization': 'Bearer token_here'  # lowercase
            }
        }
        context = {}
        
        # Should still detect missing token (since we're not mocking JWT validation)
        result = mock_endpoint(event, context)
        
        # The function should handle case-insensitive headers
        assert result['statusCode'] == 401
        # Should get to token validation, not header format error
        assert 'Invalid or expired token' in result['body']


class TestGetCurrentUser:
    """Test cases for get_current_user function."""
    
    def test_get_current_user_with_user_data(self):
        """Test extracting user data from authenticated event."""
        event = {
            'user': {
                'user_id': 'user-123',
                'github_id': 'github-456',
                'github_username': 'testuser'
            }
        }
        
        user_data = get_current_user(event)
        
        assert user_data['user_id'] == 'user-123'
        assert user_data['github_id'] == 'github-456'
        assert user_data['github_username'] == 'testuser'
    
    def test_get_current_user_no_user_data(self):
        """Test extracting user data from event without user data."""
        event = {}
        
        user_data = get_current_user(event)
        
        assert user_data == {}
    
    def test_get_current_user_partial_data(self):
        """Test extracting partial user data from event."""
        event = {
            'user': {
                'user_id': 'user-123'
                # Missing other fields
            }
        }
        
        user_data = get_current_user(event)
        
        assert user_data['user_id'] == 'user-123'
        assert len(user_data) == 1
