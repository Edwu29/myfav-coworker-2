"""Tests for pull request models."""

import pytest
from datetime import datetime
from pydantic import ValidationError
from src.models.pull_request import PullRequestModel, PullRequestSubmission, PullRequestResponse


class TestPullRequestModel:
    """Test cases for PullRequestModel."""
    
    def test_valid_pull_request_model(self):
        """Test creating valid PullRequestModel."""
        pr_data = {
            "owner": "test-owner",
            "repo": "test-repo",
            "pull_number": 123,
            "title": "Test PR",
            "head_sha": "abc123",
            "base_sha": "def456",
            "head_ref": "feature-branch",
            "base_ref": "main",
            "diff_url": "https://github.com/test-owner/test-repo/pull/123.diff",
            "patch_url": "https://github.com/test-owner/test-repo/pull/123.patch",
            "state": "open",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        pr = PullRequestModel(**pr_data)
        
        assert pr.owner == "test-owner"
        assert pr.repo == "test-repo"
        assert pr.pull_number == 123
        assert pr.title == "Test PR"
        assert pr.head_sha == "abc123"
        assert pr.base_sha == "def456"
        assert pr.head_ref == "feature-branch"
        assert pr.base_ref == "main"
        assert pr.state == "open"
    
    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            PullRequestModel()
    
    def test_invalid_pull_number_type(self):
        """Test that invalid pull_number type raises ValidationError."""
        pr_data = {
            "owner": "test-owner",
            "repo": "test-repo",
            "pull_number": "not-a-number",  # Invalid type
            "title": "Test PR",
            "head_sha": "abc123",
            "base_sha": "def456",
            "head_ref": "feature-branch",
            "base_ref": "main",
            "diff_url": "https://github.com/test-owner/test-repo/pull/123.diff",
            "patch_url": "https://github.com/test-owner/test-repo/pull/123.patch",
            "state": "open",
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        with pytest.raises(ValidationError):
            PullRequestModel(**pr_data)


class TestPullRequestSubmission:
    """Test cases for PullRequestSubmission."""
    
    def test_valid_pr_submission(self):
        """Test creating valid PullRequestSubmission."""
        submission = PullRequestSubmission(
            pr_url="https://github.com/owner/repo/pull/123"
        )
        
        assert str(submission.pr_url) == "https://github.com/owner/repo/pull/123"
    
    def test_invalid_url_format(self):
        """Test that invalid URL format raises ValidationError."""
        with pytest.raises(ValidationError):
            PullRequestSubmission(pr_url="not-a-url")
    
    def test_missing_pr_url(self):
        """Test that missing pr_url raises ValidationError."""
        with pytest.raises(ValidationError):
            PullRequestSubmission()


class TestPullRequestResponse:
    """Test cases for PullRequestResponse."""
    
    def test_valid_pr_response(self):
        """Test creating valid PullRequestResponse."""
        response = PullRequestResponse(
            job_id="test-job-id-123",
            status="pending"
        )
        
        assert response.job_id == "test-job-id-123"
        assert response.status == "pending"
    
    def test_default_status(self):
        """Test that status defaults to 'pending'."""
        response = PullRequestResponse(job_id="test-job-id")
        
        assert response.status == "pending"
    
    def test_missing_job_id(self):
        """Test that missing job_id raises ValidationError."""
        with pytest.raises(ValidationError):
            PullRequestResponse()
    
    def test_json_serialization(self):
        """Test JSON serialization works correctly."""
        response = PullRequestResponse(
            job_id="test-job-id-123",
            status="running"
        )
        
        json_data = response.model_dump_json()
        assert "test-job-id-123" in json_data
        assert "running" in json_data
