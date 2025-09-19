import json
import logging
import secrets
from typing import Dict, Any
from services.github_service import GitHubService
from services.user_service import UserService
from utils.jwt_auth import create_jwt_manager
from models.user import AuthTokenResponse


logger = logging.getLogger(__name__)


def github_login(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Initiate GitHub OAuth flow."""
    try:
        # Generate secure random state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Get GitHub authorization URL
        github_service = GitHubService()
        auth_url = github_service.get_authorization_url(state)
        
        logger.info(f"Generated GitHub OAuth URL with state: {state}")
        
        return {
            'statusCode': 302,
            'headers': {
                'Location': auth_url,
                'Access-Control-Allow-Origin': '*'
            },
            'body': ''
        }
        
    except Exception as e:
        logger.error(f"Failed to initiate GitHub OAuth: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Failed to initiate authentication'})
        }


def github_callback(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle GitHub OAuth callback and complete authentication."""
    try:
        # Extract query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        code = query_params.get('code')
        state = query_params.get('state')
        error = query_params.get('error')
        
        # Handle OAuth errors
        if error:
            logger.warning(f"GitHub OAuth error: {error}")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': f'GitHub OAuth error: {error}'})
            }
        
        # Validate required parameters
        if not code or not state:
            logger.warning("Missing code or state parameter in OAuth callback")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Missing required parameters'})
            }
        
        # Exchange code for access token
        github_service = GitHubService()
        access_token = github_service.exchange_code_for_token(code, state)
        
        if not access_token:
            logger.error("Failed to exchange code for access token")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Failed to exchange authorization code'})
            }
        
        # Get user profile from GitHub
        github_profile = github_service.get_user_profile(access_token)
        
        if not github_profile:
            logger.error("Failed to retrieve user profile from GitHub")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Failed to retrieve user profile'})
            }
        
        # Create or update user in database
        user_service = UserService()
        user = user_service.get_user_by_github_id(str(github_profile.id))
        
        if user:
            # Update existing user's token and last login
            user_service.update_github_token(str(github_profile.id), access_token)
            user_service.update_last_login(str(github_profile.id))
            logger.info(f"Updated existing user: {github_profile.login}")
        else:
            # Create new user
            user = user_service.create_user(github_profile, access_token)
            logger.info(f"Created new user: {github_profile.login}")
        
        # Generate JWT session token
        jwt_manager = create_jwt_manager()
        session_token = jwt_manager.generate_token(user.user_id, user.github_id)
        
        # Return authentication response
        auth_response = AuthTokenResponse(
            access_token=session_token,
            token_type="Bearer",
            expires_in=3600
        )
        
        logger.info(f"Successfully authenticated user: {github_profile.login}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': auth_response.model_dump_json()
        }
        
    except Exception as e:
        logger.error(f"Failed to handle GitHub callback: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Authentication failed'})
        }
