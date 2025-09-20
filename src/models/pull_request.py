"""Pull Request data models for GitHub API integration."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field


class PullRequestModel(BaseModel):
    """GitHub Pull Request metadata model."""
    
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    pull_number: int = Field(..., description="Pull request number")
    title: str = Field(..., description="Pull request title")
    head_sha: str = Field(..., description="Head commit SHA")
    base_sha: str = Field(..., description="Base commit SHA")
    head_ref: str = Field(..., description="Head branch reference")
    base_ref: str = Field(..., description="Base branch reference")
    diff_url: str = Field(..., description="URL to fetch diff")
    patch_url: str = Field(..., description="URL to fetch patch")
    state: str = Field(..., description="Pull request state (open, closed, merged)")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PullRequestSubmission(BaseModel):
    """Model for PR URL submission requests."""
    
    pr_url: HttpUrl = Field(..., description="GitHub pull request URL")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "pr_url": "https://github.com/owner/repo/pull/123"
            }
        }


class PullRequestResponse(BaseModel):
    """Model for PR submission response."""
    
    job_id: str = Field(..., description="Simulation job ID")
    status: str = Field(default="pending", description="Initial job status")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "pending"
            }
        }
