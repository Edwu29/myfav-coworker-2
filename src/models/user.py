from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class User(BaseModel):
    """User model for storing GitHub authenticated user information."""
    
    user_id: str = Field(..., description="Unique user identifier")
    github_id: str = Field(..., description="GitHub user ID")
    github_username: str = Field(..., description="GitHub username")
    encrypted_github_token: str = Field(..., description="Encrypted GitHub access token")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="User creation timestamp")
    last_login_at: Optional[datetime] = Field(None, description="Last login timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_dynamodb_item(self) -> dict:
        """Convert user model to DynamoDB item format."""
        return {
            "PK": f"USER#{self.github_id}",
            "SK": "METADATA",
            "user_id": self.user_id,
            "github_id": self.github_id,
            "github_username": self.github_username,
            "encrypted_github_token": self.encrypted_github_token,
            "created_at": self.created_at.isoformat(),
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
    
    @classmethod
    def from_dynamodb_item(cls, item: dict) -> "User":
        """Create User instance from DynamoDB item."""
        return cls(
            user_id=item["user_id"],
            github_id=item["github_id"],
            github_username=item["github_username"],
            encrypted_github_token=item["encrypted_github_token"],
            created_at=datetime.fromisoformat(item["created_at"]),
            last_login_at=datetime.fromisoformat(item["last_login_at"]) if item.get("last_login_at") else None,
        )


class GitHubUserProfile(BaseModel):
    """GitHub user profile data from GitHub API."""
    
    id: int = Field(..., description="GitHub user ID")
    login: str = Field(..., description="GitHub username")
    name: Optional[str] = Field(None, description="User's full name")
    email: Optional[str] = Field(None, description="User's email")
    avatar_url: str = Field(..., description="User's avatar URL")


class AuthTokenResponse(BaseModel):
    """Response model for successful authentication."""
    
    access_token: str = Field(..., description="JWT session token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(default=3600, description="Token expiration in seconds")
