import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional


class JWTManager:
    """Handles JWT token generation and validation for user sessions."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """Initialize JWT manager with secret key and algorithm."""
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def generate_token(self, user_id: str, github_id: str, expires_in: int = 3600) -> str:
        """Generate a JWT token for authenticated user."""
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": user_id,
            "github_id": github_id,
            "iat": now,
            "exp": now + timedelta(seconds=expires_in),
            "iss": "myfav-coworker"
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """Validate JWT token and return payload if valid."""
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                issuer="myfav-coworker"
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def refresh_token(self, token: str, expires_in: int = 3600) -> Optional[str]:
        """Refresh an existing token if it's valid."""
        payload = self.validate_token(token)
        if not payload:
            return None
        
        return self.generate_token(
            payload["user_id"], 
            payload["github_id"], 
            expires_in
        )


def get_jwt_secret() -> str:
    """Get JWT secret from environment variable or AWS Parameter Store."""
    # First try environment variable (for local development)
    secret = os.getenv('JWT_SECRET_KEY')
    if secret:
        return secret
    
    # In production, get from AWS Parameter Store
    import boto3
    ssm = boto3.client('ssm')
    try:
        response = ssm.get_parameter(
            Name='/myfav-coworker/jwt-secret-key',
            WithDecryption=True
        )
        return response['Parameter']['Value']
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve JWT secret: {e}")


def create_jwt_manager() -> JWTManager:
    """Create a JWTManager instance with the appropriate secret."""
    jwt_secret = get_jwt_secret()
    return JWTManager(jwt_secret)
