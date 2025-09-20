"""Pull Request URL validation and parsing utilities."""

import re
from typing import Tuple, Optional
from urllib.parse import urlparse


class PRValidationError(Exception):
    """Exception raised for PR URL validation errors."""
    pass


def parse_github_pr_url(pr_url: str) -> Tuple[str, str, int]:
    """
    Parse GitHub PR URL to extract owner, repo, and pull number.
    
    Args:
        pr_url: GitHub pull request URL
        
    Returns:
        Tuple of (owner, repo, pull_number)
        
    Raises:
        PRValidationError: If URL is invalid or not a GitHub PR URL
    """
    if not pr_url:
        raise PRValidationError("PR URL cannot be empty")
    
    # Parse URL
    try:
        parsed = urlparse(pr_url)
    except Exception as e:
        raise PRValidationError(f"Invalid URL format: {e}")
    
    # Validate GitHub domain
    if parsed.netloc.lower() not in ['github.com', 'www.github.com']:
        raise PRValidationError("URL must be from github.com")
    
    # Extract path components using regex
    # Expected format: /owner/repo/pull/123
    pattern = r'^/([^/]+)/([^/]+)/pull/(\d+)/?$'
    match = re.match(pattern, parsed.path)
    
    if not match:
        raise PRValidationError(
            "Invalid GitHub PR URL format. Expected: https://github.com/owner/repo/pull/123"
        )
    
    owner, repo, pull_number_str = match.groups()
    
    # Validate components
    if not owner or not repo:
        raise PRValidationError("Owner and repository name cannot be empty")
    
    try:
        pull_number = int(pull_number_str)
        if pull_number <= 0:
            raise ValueError("Pull request number must be positive")
    except ValueError as e:
        raise PRValidationError(f"Invalid pull request number: {e}")
    
    return owner, repo, pull_number


def validate_pr_url(pr_url: str) -> bool:
    """
    Validate GitHub PR URL format.
    
    Args:
        pr_url: GitHub pull request URL
        
    Returns:
        True if valid, False otherwise
    """
    try:
        parse_github_pr_url(pr_url)
        return True
    except PRValidationError:
        return False
