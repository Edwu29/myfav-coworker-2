import os
import logging
from typing import Optional, Tuple
from authlib.integrations.requests_client import OAuth2Session
import requests
from models.user import GitHubUserProfile


logger = logging.getLogger(__name__)


class GitHubService:
    """Service for GitHub OAuth2 authentication and API interactions."""
    
    def __init__(self):
        """Initialize GitHub service with OAuth2 configuration."""
        self.client_id = self._get_github_client_id()
        self.client_secret = self._get_github_client_secret()
        self.redirect_uri = self._get_redirect_uri()
        self.scope = "repo"
        self.authorization_endpoint = "https://github.com/login/oauth/authorize"
        self.token_endpoint = "https://github.com/login/oauth/access_token"
        self.api_base_url = "https://api.github.com"
    
    def _get_github_client_id(self) -> str:
        """Get GitHub OAuth client ID from environment or Parameter Store."""
        client_id = os.getenv('GITHUB_CLIENT_ID')
        if client_id:
            return client_id
        
        import boto3
        ssm = boto3.client('ssm')
        try:
            response = ssm.get_parameter(Name='/myfav-coworker/github-client-id')
            return response['Parameter']['Value']
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve GitHub client ID: {e}")
    
    def _get_github_client_secret(self) -> str:
        """Get GitHub OAuth client secret from environment or Parameter Store."""
        client_secret = os.getenv('GITHUB_CLIENT_SECRET')
        if client_secret:
            return client_secret
        
        import boto3
        ssm = boto3.client('ssm')
        try:
            response = ssm.get_parameter(
                Name='/myfav-coworker/github-client-secret',
                WithDecryption=True
            )
            return response['Parameter']['Value']
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve GitHub client secret: {e}")
    
    def _get_redirect_uri(self) -> str:
        """Get OAuth redirect URI from environment."""
        return os.getenv('GITHUB_REDIRECT_URI', 'http://localhost:3000/auth/github/callback')
    
    def get_authorization_url(self, state: str) -> str:
        """Generate GitHub OAuth authorization URL."""
        oauth = OAuth2Session(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        authorization_url, _ = oauth.create_authorization_url(
            self.authorization_endpoint,
            state=state
        )
        logger.info(f"Generated authorization URL for state: {state}")
        return authorization_url
    
    def exchange_code_for_token(self, code: str, state: str) -> Optional[str]:
        """Exchange OAuth code for access token."""
        try:
            oauth = OAuth2Session(
                client_id=self.client_id,
                redirect_uri=self.redirect_uri
            )
            
            token = oauth.fetch_token(
                self.token_endpoint,
                code=code,
                client_secret=self.client_secret
            )
            
            access_token = token.get('access_token')
            logger.info(f"Successfully exchanged code for token for state: {state}")
            return access_token
            
        except Exception as e:
            logger.error(f"Failed to exchange code for token: {e}")
            return None
    
    def get_user_profile(self, access_token: str) -> Optional[GitHubUserProfile]:
        """Fetch user profile from GitHub API."""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'myfav-coworker/1.0'
            }
            
            response = requests.get(f"{self.api_base_url}/user", headers=headers)
            response.raise_for_status()
            
            user_data = response.json()
            profile = GitHubUserProfile(
                id=user_data['id'],
                login=user_data['login'],
                name=user_data.get('name'),
                email=user_data.get('email'),
                avatar_url=user_data['avatar_url']
            )
            
            logger.info(f"Retrieved user profile for GitHub user: {profile.login}")
            return profile
            
        except Exception as e:
            logger.error(f"Failed to fetch user profile: {e}")
            return None
    
    def validate_token(self, access_token: str) -> bool:
        """Validate GitHub access token by making a test API call."""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'myfav-coworker/1.0'
            }
            
            response = requests.get(f"{self.api_base_url}/user", headers=headers)
            return response.status_code == 200
            
        except Exception:
            return False
