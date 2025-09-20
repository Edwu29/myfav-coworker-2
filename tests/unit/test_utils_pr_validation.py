"""Tests for PR validation utilities."""

import pytest
from src.utils.pr_validation import parse_github_pr_url, validate_pr_url, PRValidationError


class TestParseGitHubPRURL:
    """Test cases for parse_github_pr_url function."""
    
    def test_valid_pr_url(self):
        """Test parsing valid GitHub PR URL."""
        url = "https://github.com/owner/repo/pull/123"
        owner, repo, pull_number = parse_github_pr_url(url)
        
        assert owner == "owner"
        assert repo == "repo"
        assert pull_number == 123
    
    def test_valid_pr_url_with_trailing_slash(self):
        """Test parsing valid GitHub PR URL with trailing slash."""
        url = "https://github.com/owner/repo/pull/456/"
        owner, repo, pull_number = parse_github_pr_url(url)
        
        assert owner == "owner"
        assert repo == "repo"
        assert pull_number == 456
    
    def test_valid_pr_url_with_www(self):
        """Test parsing valid GitHub PR URL with www prefix."""
        url = "https://www.github.com/owner/repo/pull/789"
        owner, repo, pull_number = parse_github_pr_url(url)
        
        assert owner == "owner"
        assert repo == "repo"
        assert pull_number == 789
    
    def test_valid_pr_url_complex_names(self):
        """Test parsing PR URL with complex owner/repo names."""
        url = "https://github.com/my-org/my-repo-name/pull/1"
        owner, repo, pull_number = parse_github_pr_url(url)
        
        assert owner == "my-org"
        assert repo == "my-repo-name"
        assert pull_number == 1
    
    def test_empty_url(self):
        """Test parsing empty URL raises error."""
        with pytest.raises(PRValidationError, match="PR URL cannot be empty"):
            parse_github_pr_url("")
    
    def test_none_url(self):
        """Test parsing None URL raises error."""
        with pytest.raises(PRValidationError, match="PR URL cannot be empty"):
            parse_github_pr_url(None)
    
    def test_invalid_domain(self):
        """Test parsing URL with invalid domain raises error."""
        url = "https://gitlab.com/owner/repo/pull/123"
        with pytest.raises(PRValidationError, match="URL must be from github.com"):
            parse_github_pr_url(url)
    
    def test_invalid_path_format(self):
        """Test parsing URL with invalid path format raises error."""
        url = "https://github.com/owner/repo/issues/123"
        with pytest.raises(PRValidationError, match="Invalid GitHub PR URL format"):
            parse_github_pr_url(url)
    
    def test_missing_pull_number(self):
        """Test parsing URL without pull number raises error."""
        url = "https://github.com/owner/repo/pull/"
        with pytest.raises(PRValidationError, match="Invalid GitHub PR URL format"):
            parse_github_pr_url(url)
    
    def test_invalid_pull_number(self):
        """Test parsing URL with invalid pull number raises error."""
        url = "https://github.com/owner/repo/pull/abc"
        with pytest.raises(PRValidationError, match="Invalid GitHub PR URL format"):
            parse_github_pr_url(url)
    
    def test_zero_pull_number(self):
        """Test parsing URL with zero pull number raises error."""
        url = "https://github.com/owner/repo/pull/0"
        with pytest.raises(PRValidationError, match="Pull request number must be positive"):
            parse_github_pr_url(url)
    
    def test_negative_pull_number(self):
        """Test parsing URL with negative pull number raises error."""
        url = "https://github.com/owner/repo/pull/-1"
        with pytest.raises(PRValidationError, match="Invalid GitHub PR URL format"):
            parse_github_pr_url(url)
    
    def test_empty_owner(self):
        """Test parsing URL with empty owner raises error."""
        url = "https://github.com//repo/pull/123"
        with pytest.raises(PRValidationError, match="Invalid GitHub PR URL format"):
            parse_github_pr_url(url)
    
    def test_empty_repo(self):
        """Test parsing URL with empty repo raises error."""
        url = "https://github.com/owner//pull/123"
        with pytest.raises(PRValidationError, match="Invalid GitHub PR URL format"):
            parse_github_pr_url(url)
    
    def test_malformed_url(self):
        """Test parsing malformed URL raises error."""
        url = "not-a-url"
        with pytest.raises(PRValidationError, match="URL must be from github.com"):
            parse_github_pr_url(url)


class TestValidatePRURL:
    """Test cases for validate_pr_url function."""
    
    def test_valid_url_returns_true(self):
        """Test that valid URL returns True."""
        url = "https://github.com/owner/repo/pull/123"
        assert validate_pr_url(url) is True
    
    def test_invalid_url_returns_false(self):
        """Test that invalid URL returns False."""
        url = "https://gitlab.com/owner/repo/pull/123"
        assert validate_pr_url(url) is False
    
    def test_empty_url_returns_false(self):
        """Test that empty URL returns False."""
        assert validate_pr_url("") is False
    
    def test_malformed_url_returns_false(self):
        """Test that malformed URL returns False."""
        assert validate_pr_url("not-a-url") is False
