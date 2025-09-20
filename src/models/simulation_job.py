"""Simulation job data models for tracking PR simulation requests."""

import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Simulation job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class SimulationJobModel(BaseModel):
    """Simulation job tracking model."""
    
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique job identifier")
    user_id: str = Field(..., description="User ID who submitted the job")
    pr_url: str = Field(..., description="GitHub pull request URL")
    status: JobStatus = Field(default=JobStatus.PENDING, description="Current job status")
    report: Optional[Dict[str, Any]] = Field(default=None, description="Simulation report data")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Job creation timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Job completion timestamp")
    error_message: Optional[str] = Field(default=None, description="Error message if job failed")
    
    # PR metadata (populated after GitHub API fetch)
    pr_owner: Optional[str] = Field(default=None, description="Repository owner")
    pr_repo: Optional[str] = Field(default=None, description="Repository name")
    pr_number: Optional[int] = Field(default=None, description="Pull request number")
    pr_title: Optional[str] = Field(default=None, description="Pull request title")
    pr_head_sha: Optional[str] = Field(default=None, description="Head commit SHA")
    pr_base_sha: Optional[str] = Field(default=None, description="Base commit SHA")
    
    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        item = {
            'PK': f'JOB#{self.job_id}',
            'SK': 'METADATA',
            'job_id': self.job_id,
            'user_id': self.user_id,
            'pr_url': self.pr_url,
            'status': self.status.value if isinstance(self.status, JobStatus) else self.status,
            'created_at': self.created_at.isoformat(),
        }
        
        # Add optional fields if present
        if self.report:
            item['report'] = self.report
        if self.completed_at:
            item['completed_at'] = self.completed_at.isoformat()
        if self.error_message:
            item['error_message'] = self.error_message
        if self.pr_owner:
            item['pr_owner'] = self.pr_owner
        if self.pr_repo:
            item['pr_repo'] = self.pr_repo
        if self.pr_number:
            item['pr_number'] = self.pr_number
        if self.pr_title:
            item['pr_title'] = self.pr_title
        if self.pr_head_sha:
            item['pr_head_sha'] = self.pr_head_sha
        if self.pr_base_sha:
            item['pr_base_sha'] = self.pr_base_sha
            
        return item
    
    @classmethod
    def from_dynamodb_item(cls, item: Dict[str, Any]) -> 'SimulationJobModel':
        """Create instance from DynamoDB item."""
        # Parse timestamps
        created_at = datetime.fromisoformat(item['created_at'])
        completed_at = None
        if 'completed_at' in item:
            completed_at = datetime.fromisoformat(item['completed_at'])
        
        return cls(
            job_id=item['job_id'],
            user_id=item['user_id'],
            pr_url=item['pr_url'],
            status=JobStatus(item['status']),
            report=item.get('report'),
            created_at=created_at,
            completed_at=completed_at,
            error_message=item.get('error_message'),
            pr_owner=item.get('pr_owner'),
            pr_repo=item.get('pr_repo'),
            pr_number=item.get('pr_number'),
            pr_title=item.get('pr_title'),
            pr_head_sha=item.get('pr_head_sha'),
            pr_base_sha=item.get('pr_base_sha'),
        )
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
