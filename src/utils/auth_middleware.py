import logging
from functools import wraps
from typing import Dict, Any, Callable
from src.utils.jwt_auth import create_jwt_manager
from src.services.user_service import UserService


logger = logging.getLogger(__name__)


def require_auth(f: Callable) -> Callable:
    """Decorator to require JWT authentication for API endpoints."""
    
    @wraps(f)
    def decorated_function(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Wrapper function that validates JWT token before calling the endpoint."""
        
        # Extract Authorization header
        headers = event.get('headers', {})
        auth_header = headers.get('Authorization') or headers.get('authorization')
        
        if not auth_header:
            logger.warning("Missing Authorization header")
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': '{"error": "Missing Authorization header"}'
            }
        
        # Extract token from Bearer format
        if not auth_header.startswith('Bearer '):
            logger.warning("Invalid Authorization header format")
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': '{"error": "Invalid Authorization header format"}'
            }
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Validate JWT token
        jwt_manager = create_jwt_manager()
        payload = jwt_manager.validate_token(token)
        
        if not payload:
            logger.warning("Invalid or expired JWT token")
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': '{"error": "Invalid or expired token"}'
            }
        
        # Verify user exists in database
        user_service = UserService()
        user = user_service.get_user_by_github_id(payload['github_id'])
        
        if not user:
            logger.warning(f"User not found for GitHub ID: {payload['github_id']}")
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': '{"error": "User not found"}'
            }
        
        # Add user information to event for use in the endpoint
        event['user'] = {
            'user_id': user.user_id,
            'github_id': user.github_id,
            'github_username': user.github_username
        }
        
        logger.info(f"Authenticated user: {user.github_username}")
        
        # Call the original function
        return f(event, context)
    
    return decorated_function


def get_current_user(event: Dict[str, Any]) -> Dict[str, str]:
    """Extract current user information from authenticated event."""
    return event.get('user', {})
