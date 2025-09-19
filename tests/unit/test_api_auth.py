import pytest
import json
from unittest.mock import patch, MagicMock
from src.api.auth import github_login, github_callback
from src.models.user import User, GitHubUserProfile


class TestGitHubLogin:
    """Test cases for github_login endpoint."""
    
    @patch('src.api.auth.GitHubService')
    @patch('src.api.auth.secrets.token_urlsafe')
    def test_github_login_success(self, mock_token_urlsafe, mock_github_service_class):
        """Test successful GitHub OAuth initiation."""
        # Mock state generation
        mock_token_urlsafe.return_value = "secure_random_state_123"
        
        # Mock GitHub service
        mock_github_service = MagicMock()
        mock_github_service_class.return_value = mock_github_service
        mock_github_service.get_authorization_url.return_value = "https://github.com/login/oauth/authorize?client_id=123&state=secure_random_state_123"
        
        event = {}
        context = {}
        
        result = github_login(event, context)
        
        assert result['statusCode'] == 302
        assert result['headers']['Location'] == "https://github.com/login/oauth/authorize?client_id=123&state=secure_random_state_123"
        assert result['headers']['Access-Control-Allow-Origin'] == '*'
        assert result['body'] == ''
        
        mock_token_urlsafe.assert_called_once_with(32)
        mock_github_service.get_authorization_url.assert_called_once_with("secure_random_state_123")
    
    @patch('src.api.auth.GitHubService')
    def test_github_login_service_failure(self, mock_github_service_class):
        """Test GitHub OAuth initiation with service failure."""
        # Mock GitHub service to raise exception
        mock_github_service_class.side_effect = Exception("GitHub service error")
        
        event = {}
        context = {}
        
        result = github_login(event, context)
        
        assert result['statusCode'] == 500
        assert result['headers']['Content-Type'] == 'application/json'
        assert result['headers']['Access-Control-Allow-Origin'] == '*'
        
        response_body = json.loads(result['body'])
        assert response_body['error'] == 'Failed to initiate authentication'


class TestGitHubCallback:
    """Test cases for github_callback endpoint."""
    
    @patch('src.api.auth.GitHubService')
    @patch('src.api.auth.UserService')
    @patch('src.api.auth.create_jwt_manager')
    def test_github_callback_new_user_success(self, mock_create_jwt_manager, mock_user_service_class, mock_github_service_class):
        """Test successful GitHub OAuth callback for new user."""
        # Mock GitHub service
        mock_github_service = MagicMock()
        mock_github_service_class.return_value = mock_github_service
        mock_github_service.exchange_code_for_token.return_value = "github_access_token_123"
        
        mock_github_profile = GitHubUserProfile(
            id=12345,
            login="testuser",
            name="Test User",
            email="test@example.com",
            avatar_url="https://github.com/avatar.jpg"
        )
        mock_github_service.get_user_profile.return_value = mock_github_profile
        
        # Mock user service (new user)
        mock_user_service = MagicMock()
        mock_user_service_class.return_value = mock_user_service
        mock_user_service.get_user_by_github_id.return_value = None  # New user
        
        mock_user = User(
            user_id="user-123",
            github_id="12345",
            github_username="testuser",
            encrypted_github_token="encrypted_token"
        )
        mock_user_service.create_user.return_value = mock_user
        
        # Mock JWT manager
        mock_jwt_manager = MagicMock()
        mock_create_jwt_manager.return_value = mock_jwt_manager
        mock_jwt_manager.generate_token.return_value = "jwt_session_token_123"
        
        event = {
            'queryStringParameters': {
                'code': 'oauth_code_123',
                'state': 'oauth_state_456'
            }
        }
        context = {}
        
        result = github_callback(event, context)
        
        assert result['statusCode'] == 200
        assert result['headers']['Content-Type'] == 'application/json'
        assert result['headers']['Access-Control-Allow-Origin'] == '*'
        
        response_body = json.loads(result['body'])
        assert response_body['access_token'] == 'jwt_session_token_123'
        assert response_body['token_type'] == 'Bearer'
        assert response_body['expires_in'] == 3600
        
        # Verify service calls
        mock_github_service.exchange_code_for_token.assert_called_once_with('oauth_code_123', 'oauth_state_456')
        mock_github_service.get_user_profile.assert_called_once_with('github_access_token_123')
        mock_user_service.get_user_by_github_id.assert_called_once_with('12345')
        mock_user_service.create_user.assert_called_once_with(mock_github_profile, 'github_access_token_123')
        mock_jwt_manager.generate_token.assert_called_once_with(mock_user.user_id, mock_user.github_id)
    
    @patch('src.api.auth.GitHubService')
    @patch('src.api.auth.UserService')
    @patch('src.api.auth.create_jwt_manager')
    def test_github_callback_existing_user_success(self, mock_create_jwt_manager, mock_user_service_class, mock_github_service_class):
        """Test successful GitHub OAuth callback for existing user."""
        # Mock GitHub service
        mock_github_service = MagicMock()
        mock_github_service_class.return_value = mock_github_service
        mock_github_service.exchange_code_for_token.return_value = "github_access_token_123"
        
        mock_github_profile = GitHubUserProfile(
            id=12345,
            login="testuser",
            avatar_url="https://github.com/avatar.jpg"
        )
        mock_github_service.get_user_profile.return_value = mock_github_profile
        
        # Mock user service (existing user)
        mock_user_service = MagicMock()
        mock_user_service_class.return_value = mock_user_service
        
        mock_existing_user = User(
            user_id="user-123",
            github_id="12345",
            github_username="testuser",
            encrypted_github_token="old_encrypted_token"
        )
        mock_user_service.get_user_by_github_id.return_value = mock_existing_user
        mock_user_service.update_github_token.return_value = True
        mock_user_service.update_last_login.return_value = True
        
        # Mock JWT manager
        mock_jwt_manager = MagicMock()
        mock_create_jwt_manager.return_value = mock_jwt_manager
        mock_jwt_manager.generate_token.return_value = "jwt_session_token_456"
        
        event = {
            'queryStringParameters': {
                'code': 'oauth_code_123',
                'state': 'oauth_state_456'
            }
        }
        context = {}
        
        result = github_callback(event, context)
        
        assert result['statusCode'] == 200
        
        response_body = json.loads(result['body'])
        assert response_body['access_token'] == 'jwt_session_token_456'
        
        # Verify existing user update calls
        mock_user_service.update_github_token.assert_called_once_with('12345', 'github_access_token_123')
        mock_user_service.update_last_login.assert_called_once_with('12345')
        mock_user_service.create_user.assert_not_called()
    
    def test_github_callback_oauth_error(self):
        """Test GitHub OAuth callback with OAuth error."""
        event = {
            'queryStringParameters': {
                'error': 'access_denied',
                'error_description': 'User denied access'
            }
        }
        context = {}
        
        result = github_callback(event, context)
        
        assert result['statusCode'] == 400
        assert result['headers']['Content-Type'] == 'application/json'
        
        response_body = json.loads(result['body'])
        assert 'GitHub OAuth error: access_denied' in response_body['error']
    
    def test_github_callback_missing_parameters(self):
        """Test GitHub OAuth callback with missing parameters."""
        event = {
            'queryStringParameters': {
                'code': 'oauth_code_123'
                # Missing state parameter
            }
        }
        context = {}
        
        result = github_callback(event, context)
        
        assert result['statusCode'] == 400
        
        response_body = json.loads(result['body'])
        assert response_body['error'] == 'Missing required parameters'
    
    def test_github_callback_no_query_params(self):
        """Test GitHub OAuth callback with no query parameters."""
        event = {'queryStringParameters': None}
        context = {}
        
        result = github_callback(event, context)
        
        assert result['statusCode'] == 400
        
        response_body = json.loads(result['body'])
        assert response_body['error'] == 'Missing required parameters'
    
    @patch('src.api.auth.GitHubService')
    def test_github_callback_token_exchange_failure(self, mock_github_service_class):
        """Test GitHub OAuth callback with token exchange failure."""
        # Mock GitHub service to fail token exchange
        mock_github_service = MagicMock()
        mock_github_service_class.return_value = mock_github_service
        mock_github_service.exchange_code_for_token.return_value = None
        
        event = {
            'queryStringParameters': {
                'code': 'oauth_code_123',
                'state': 'oauth_state_456'
            }
        }
        context = {}
        
        result = github_callback(event, context)
        
        assert result['statusCode'] == 400
        
        response_body = json.loads(result['body'])
        assert response_body['error'] == 'Failed to exchange authorization code'
    
    @patch('src.api.auth.GitHubService')
    def test_github_callback_profile_fetch_failure(self, mock_github_service_class):
        """Test GitHub OAuth callback with profile fetch failure."""
        # Mock GitHub service
        mock_github_service = MagicMock()
        mock_github_service_class.return_value = mock_github_service
        mock_github_service.exchange_code_for_token.return_value = "github_access_token_123"
        mock_github_service.get_user_profile.return_value = None  # Profile fetch failure
        
        event = {
            'queryStringParameters': {
                'code': 'oauth_code_123',
                'state': 'oauth_state_456'
            }
        }
        context = {}
        
        result = github_callback(event, context)
        
        assert result['statusCode'] == 400
        
        response_body = json.loads(result['body'])
        assert response_body['error'] == 'Failed to retrieve user profile'
    
    @patch('src.api.auth.GitHubService')
    def test_github_callback_unexpected_error(self, mock_github_service_class):
        """Test GitHub OAuth callback with unexpected error."""
        # Mock GitHub service to raise unexpected exception
        mock_github_service_class.side_effect = Exception("Unexpected error")
        
        event = {
            'queryStringParameters': {
                'code': 'oauth_code_123',
                'state': 'oauth_state_456'
            }
        }
        context = {}
        
        result = github_callback(event, context)
        
        assert result['statusCode'] == 500
        
        response_body = json.loads(result['body'])
        assert response_body['error'] == 'Authentication failed'
