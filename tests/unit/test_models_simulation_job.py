"""Tests for simulation job models."""

import pytest
from datetime import datetime, timezone
from src.models.simulation_job import SimulationJobModel, JobStatus


class TestSimulationJobModel:
    """Test cases for SimulationJobModel."""
    
    def test_create_job_with_defaults(self):
        """Test creating job with default values."""
        job = SimulationJobModel(
            user_id="user123",
            pr_url="https://github.com/owner/repo/pull/123"
        )
        
        assert job.user_id == "user123"
        assert job.pr_url == "https://github.com/owner/repo/pull/123"
        assert job.status == JobStatus.PENDING
        assert job.report is None
        assert job.error_message is None
        assert job.completed_at is None
        assert len(job.job_id) > 0  # UUID should be generated
        assert isinstance(job.created_at, datetime)
    
    def test_create_job_with_all_fields(self):
        """Test creating job with all fields specified."""
        created_at = datetime.now(timezone.utc)
        completed_at = datetime.now(timezone.utc)
        
        job = SimulationJobModel(
            job_id="custom-job-id",
            user_id="user123",
            pr_url="https://github.com/owner/repo/pull/123",
            status=JobStatus.COMPLETED,
            report={"result": "pass"},
            created_at=created_at,
            completed_at=completed_at,
            error_message="Test error",
            pr_owner="owner",
            pr_repo="repo",
            pr_number=123,
            pr_title="Test PR",
            pr_head_sha="abc123",
            pr_base_sha="def456"
        )
        
        assert job.job_id == "custom-job-id"
        assert job.status == JobStatus.COMPLETED
        assert job.report == {"result": "pass"}
        assert job.created_at == created_at
        assert job.completed_at == completed_at
        assert job.error_message == "Test error"
        assert job.pr_owner == "owner"
        assert job.pr_repo == "repo"
        assert job.pr_number == 123
        assert job.pr_title == "Test PR"
        assert job.pr_head_sha == "abc123"
        assert job.pr_base_sha == "def456"
    
    def test_to_dynamodb_item(self):
        """Test conversion to DynamoDB item format."""
        job = SimulationJobModel(
            job_id="test-job-123",
            user_id="user123",
            pr_url="https://github.com/owner/repo/pull/123",
            status=JobStatus.RUNNING,
            pr_owner="owner",
            pr_repo="repo",
            pr_number=123
        )
        
        item = job.to_dynamodb_item()
        
        assert item['PK'] == 'JOB#test-job-123'
        assert item['SK'] == 'METADATA'
        assert item['job_id'] == 'test-job-123'
        assert item['user_id'] == 'user123'
        assert item['pr_url'] == 'https://github.com/owner/repo/pull/123'
        assert item['status'] == 'running'
        assert item['pr_owner'] == 'owner'
        assert item['pr_repo'] == 'repo'
        assert item['pr_number'] == 123
        assert 'created_at' in item
        assert 'report' not in item  # Should not include None values
        assert 'completed_at' not in item
    
    def test_to_dynamodb_item_with_optional_fields(self):
        """Test DynamoDB conversion with optional fields."""
        completed_at = datetime.now(timezone.utc)
        
        job = SimulationJobModel(
            job_id="test-job-123",
            user_id="user123",
            pr_url="https://github.com/owner/repo/pull/123",
            status=JobStatus.COMPLETED,
            report={"result": "pass", "details": "All tests passed"},
            completed_at=completed_at,
            error_message="No errors",
            pr_title="Test PR Title"
        )
        
        item = job.to_dynamodb_item()
        
        assert item['report'] == {"result": "pass", "details": "All tests passed"}
        assert item['completed_at'] == completed_at.isoformat()
        assert item['error_message'] == "No errors"
        assert item['pr_title'] == "Test PR Title"
    
    def test_from_dynamodb_item(self):
        """Test creation from DynamoDB item."""
        created_at = datetime.now(timezone.utc)
        completed_at = datetime.now(timezone.utc)
        
        item = {
            'PK': 'JOB#test-job-123',
            'SK': 'METADATA',
            'job_id': 'test-job-123',
            'user_id': 'user123',
            'pr_url': 'https://github.com/owner/repo/pull/123',
            'status': 'completed',
            'created_at': created_at.isoformat(),
            'completed_at': completed_at.isoformat(),
            'report': {'result': 'pass'},
            'error_message': 'No errors',
            'pr_owner': 'owner',
            'pr_repo': 'repo',
            'pr_number': 123,
            'pr_title': 'Test PR',
            'pr_head_sha': 'abc123',
            'pr_base_sha': 'def456'
        }
        
        job = SimulationJobModel.from_dynamodb_item(item)
        
        assert job.job_id == 'test-job-123'
        assert job.user_id == 'user123'
        assert job.pr_url == 'https://github.com/owner/repo/pull/123'
        assert job.status == JobStatus.COMPLETED
        assert job.report == {'result': 'pass'}
        assert job.error_message == 'No errors'
        assert job.pr_owner == 'owner'
        assert job.pr_repo == 'repo'
        assert job.pr_number == 123
        assert job.pr_title == 'Test PR'
        assert job.pr_head_sha == 'abc123'
        assert job.pr_base_sha == 'def456'
        # Timestamps should be parsed correctly
        assert abs((job.created_at - created_at).total_seconds()) < 1
        assert abs((job.completed_at - completed_at).total_seconds()) < 1
    
    def test_from_dynamodb_item_minimal(self):
        """Test creation from minimal DynamoDB item."""
        created_at = datetime.now(timezone.utc)
        
        item = {
            'job_id': 'test-job-123',
            'user_id': 'user123',
            'pr_url': 'https://github.com/owner/repo/pull/123',
            'status': 'pending',
            'created_at': created_at.isoformat()
        }
        
        job = SimulationJobModel.from_dynamodb_item(item)
        
        assert job.job_id == 'test-job-123'
        assert job.user_id == 'user123'
        assert job.status == JobStatus.PENDING
        assert job.report is None
        assert job.completed_at is None
        assert job.error_message is None


class TestJobStatus:
    """Test cases for JobStatus enum."""
    
    def test_job_status_values(self):
        """Test JobStatus enum values."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
    
    def test_job_status_from_string(self):
        """Test creating JobStatus from string values."""
        assert JobStatus("pending") == JobStatus.PENDING
        assert JobStatus("running") == JobStatus.RUNNING
        assert JobStatus("completed") == JobStatus.COMPLETED
        assert JobStatus("failed") == JobStatus.FAILED
