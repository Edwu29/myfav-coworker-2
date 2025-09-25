"""Tests for repository service."""

import pytest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from src.services.repository_service import RepositoryService, RepositoryError


class TestRepositoryService:
    """Test cases for RepositoryService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_service = RepositoryService(base_path=self.temp_dir)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init_creates_base_path(self):
        """Test that initialization creates base path."""
        new_temp_dir = os.path.join(self.temp_dir, "new_base")
        service = RepositoryService(base_path=new_temp_dir)
        
        assert os.path.exists(new_temp_dir)
        assert service.base_path == Path(new_temp_dir)
    
    @patch('src.services.repository_service.subprocess.run')
    def test_clone_repository_success(self, mock_run):
        """Test successful repository cloning."""
        # Mock successful git clone and create directory to simulate git clone behavior
        def mock_git_clone(*args, **kwargs):
            # Extract the target path from the command
            cmd = args[0]
            if len(cmd) >= 4 and cmd[0] == 'git' and cmd[1] == 'clone':
                target_path = cmd[3]
                os.makedirs(target_path, exist_ok=True)
            
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stderr = ""
            return mock_result
        
        mock_run.side_effect = mock_git_clone
        
        repo_url = "https://github.com/owner/repo.git"
        access_token = "token123"
        
        result_path = self.repo_service.clone_repository(repo_url, access_token)
        
        # Verify the path is returned and exists
        assert result_path.startswith(self.temp_dir)
        assert os.path.exists(result_path)
        
        # Verify git clone was called with authenticated URL
        expected_auth_url = f"https://{access_token}@github.com/owner/repo.git"
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == 'git'
        assert call_args[1] == 'clone'
        assert call_args[2] == expected_auth_url
    
    @patch('src.services.repository_service.subprocess.run')
    def test_clone_repository_with_target_dir(self, mock_run):
        """Test repository cloning with specific target directory."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        repo_url = "https://github.com/owner/repo.git"
        access_token = "token123"
        target_dir = "custom_repo_dir"
        
        result_path = self.repo_service.clone_repository(repo_url, access_token, target_dir)
        
        expected_path = os.path.join(self.temp_dir, target_dir)
        assert result_path == expected_path
    
    @patch('src.services.repository_service.subprocess.run')
    def test_clone_repository_failure(self, mock_run):
        """Test repository cloning failure."""
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "fatal: repository not found"
        mock_run.return_value = mock_result
        
        repo_url = "https://github.com/owner/nonexistent.git"
        access_token = "token123"
        
        with pytest.raises(RepositoryError, match="Failed to clone repository"):
            self.repo_service.clone_repository(repo_url, access_token)
    
    @patch('src.services.repository_service.subprocess.run')
    def test_clone_repository_timeout(self, mock_run):
        """Test repository cloning timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=['git'], timeout=300)
        
        repo_url = "https://github.com/owner/repo.git"
        access_token = "token123"
        
        with pytest.raises(RepositoryError, match="Repository clone operation timed out"):
            self.repo_service.clone_repository(repo_url, access_token)
    
    def test_clone_repository_invalid_url(self):
        """Test repository cloning with invalid URL."""
        repo_url = "https://gitlab.com/owner/repo.git"
        access_token = "token123"
        
        with pytest.raises(RepositoryError, match="Unsupported repository URL format"):
            self.repo_service.clone_repository(repo_url, access_token)
    
    @patch('src.services.repository_service.subprocess.run')
    def test_checkout_branch_success(self, mock_run):
        """Test successful branch checkout."""
        # Create a mock repository directory
        repo_path = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(repo_path)
        
        # Mock successful git commands
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = self.repo_service.checkout_branch(repo_path, "feature-branch")
        
        assert result is True
        
        # Verify git fetch and checkout were called
        assert mock_run.call_count == 2
        
        # First call should be git fetch
        first_call = mock_run.call_args_list[0]
        assert first_call[0][0] == ['git', 'fetch', 'origin']
        assert first_call[1]['cwd'] == repo_path
        
        # Second call should be git checkout
        second_call = mock_run.call_args_list[1]
        assert second_call[0][0] == ['git', 'checkout', 'feature-branch']
        assert second_call[1]['cwd'] == repo_path
    
    @patch('src.services.repository_service.subprocess.run')
    def test_checkout_branch_remote_fallback(self, mock_run):
        """Test branch checkout with remote fallback."""
        repo_path = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(repo_path)
        
        # Mock fetch success, checkout failure, remote checkout success
        fetch_result = Mock()
        fetch_result.returncode = 0
        
        checkout_result = Mock()
        checkout_result.returncode = 1
        checkout_result.stderr = "error: pathspec 'feature-branch' did not match"
        
        remote_checkout_result = Mock()
        remote_checkout_result.returncode = 0
        
        mock_run.side_effect = [fetch_result, checkout_result, remote_checkout_result]
        
        result = self.repo_service.checkout_branch(repo_path, "feature-branch")
        
        assert result is True
        assert mock_run.call_count == 3
        
        # Third call should be remote checkout
        third_call = mock_run.call_args_list[2]
        expected_cmd = ['git', 'checkout', '-b', 'feature-branch', 'origin/feature-branch']
        assert third_call[0][0] == expected_cmd
    
    def test_checkout_branch_nonexistent_repo(self):
        """Test branch checkout with nonexistent repository."""
        repo_path = "/nonexistent/path"
        
        with pytest.raises(RepositoryError, match="Repository path does not exist"):
            self.repo_service.checkout_branch(repo_path, "feature-branch")
    
    @patch('src.services.repository_service.subprocess.run')
    def test_get_current_branch_success(self, mock_run):
        """Test getting current branch name."""
        repo_path = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(repo_path)
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "main\n"
        mock_run.return_value = mock_result
        
        branch = self.repo_service.get_current_branch(repo_path)
        
        assert branch == "main"
        
        # Verify git command
        mock_run.assert_called_once_with(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
    
    @patch('src.services.repository_service.subprocess.run')
    def test_get_commit_sha_success(self, mock_run):
        """Test getting commit SHA."""
        repo_path = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(repo_path)
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "abc123def456\n"
        mock_run.return_value = mock_result
        
        sha = self.repo_service.get_commit_sha(repo_path)
        
        assert sha == "abc123def456"
        
        # Verify git command with default HEAD
        mock_run.assert_called_once_with(
            ['git', 'rev-parse', 'HEAD'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
    
    @patch('src.services.repository_service.subprocess.run')
    def test_get_commit_sha_custom_ref(self, mock_run):
        """Test getting commit SHA for custom reference."""
        repo_path = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(repo_path)
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "def456abc789\n"
        mock_run.return_value = mock_result
        
        sha = self.repo_service.get_commit_sha(repo_path, "origin/main")
        
        assert sha == "def456abc789"
        
        # Verify git command with custom ref
        mock_run.assert_called_once_with(
            ['git', 'rev-parse', 'origin/main'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
    
    def test_cleanup_repository_success(self):
        """Test successful repository cleanup."""
        # Create a test repository directory
        repo_path = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(repo_path)
        
        # Create some files
        test_file = os.path.join(repo_path, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        assert os.path.exists(repo_path)
        
        result = self.repo_service.cleanup_repository(repo_path)
        
        assert result is True
        assert not os.path.exists(repo_path)
    
    def test_cleanup_repository_nonexistent(self):
        """Test cleanup of nonexistent repository."""
        repo_path = "/nonexistent/path"
        
        result = self.repo_service.cleanup_repository(repo_path)
        
        assert result is True  # Should return True even if path doesn't exist
    
    def test_get_repository_size(self):
        """Test getting repository size."""
        # Create a test repository with files
        repo_path = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(repo_path)
        
        # Create test files with known sizes
        file1 = os.path.join(repo_path, "file1.txt")
        file2 = os.path.join(repo_path, "file2.txt")
        
        with open(file1, 'w') as f:
            f.write("a" * 100)  # 100 bytes
        
        with open(file2, 'w') as f:
            f.write("b" * 200)  # 200 bytes
        
        size = self.repo_service.get_repository_size(repo_path)
        
        assert size == 300  # 100 + 200 bytes
    
    def test_validate_repository_constraints_valid(self):
        """Test repository validation with valid size."""
        # Create a small test repository
        repo_path = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(repo_path)
        
        test_file = os.path.join(repo_path, "test.txt")
        with open(test_file, 'w') as f:
            f.write("small file")
        
        result = self.repo_service.validate_repository_constraints(repo_path, max_size_mb=1)
        
        assert result['valid'] is True
        assert result['size_mb'] < 1
        assert len(result['warnings']) == 0
    
    def test_validate_repository_constraints_too_large(self):
        """Test repository validation with oversized repository."""
        # Create a test repository that exceeds size limit
        repo_path = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(repo_path)
        
        # Create a 2MB file (exceeds 1MB limit)
        test_file = os.path.join(repo_path, "large_file.txt")
        with open(test_file, 'w') as f:
            f.write("a" * (2 * 1024 * 1024))  # 2MB
        
        result = self.repo_service.validate_repository_constraints(repo_path, max_size_mb=1)
        
        assert result['valid'] is False
        assert result['size_mb'] > 1
        assert any("exceeds limit" in warning for warning in result['warnings'])
    
    def test_validate_repository_constraints_approaching_limit(self):
        """Test repository validation approaching size limit."""
        repo_path = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(repo_path)
        
        # Create a file that's 90% of the limit (0.9MB out of 1MB)
        test_file = os.path.join(repo_path, "large_file.txt")
        with open(test_file, 'w') as f:
            f.write("a" * int(0.9 * 1024 * 1024))  # 0.9MB
        
        result = self.repo_service.validate_repository_constraints(repo_path, max_size_mb=1)
        
        assert result['valid'] is True
        assert any("approaching limit" in warning for warning in result['warnings'])
    
    def test_get_repository_path(self):
        """Test getting repository path from owner and repo name."""
        owner = "testowner"
        repo = "testrepo"
        
        expected_path = os.path.join(self.temp_dir, f"{owner}_{repo}")
        actual_path = self.repo_service.get_repository_path(owner, repo)
        
        assert actual_path == expected_path
    
    @patch('src.services.repository_service.subprocess.run')
    def test_checkout_pr_branch_success(self, mock_run):
        """Test successful PR branch checkout."""
        # Create test repository directory
        repo_path = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(repo_path)
        
        # Mock git fetch and checkout commands
        mock_run.return_value = Mock(returncode=0, stderr="")
        
        pr_head_sha = "abc123def456"
        result = self.repo_service.checkout_pr_branch(repo_path, pr_head_sha)
        
        assert result is True
        
        # Verify git commands were called
        assert mock_run.call_count == 2
        calls = mock_run.call_args_list
        
        # First call should be fetch
        fetch_call = calls[0][0][0]  # First positional arg of first call
        assert fetch_call[0:3] == ['git', 'fetch', 'origin']
        
        # Second call should be checkout
        checkout_call = calls[1][0][0]  # First positional arg of second call
        assert checkout_call == ['git', 'checkout', pr_head_sha]
    
    @patch('src.services.repository_service.subprocess.run')
    def test_checkout_pr_branch_repo_not_found(self, mock_run):
        """Test PR branch checkout with nonexistent repository."""
        nonexistent_path = os.path.join(self.temp_dir, "nonexistent")
        pr_head_sha = "abc123def456"
        
        with pytest.raises(RepositoryError) as exc_info:
            self.repo_service.checkout_pr_branch(nonexistent_path, pr_head_sha)
        
        assert "does not exist" in str(exc_info.value)
        # Git commands should not be called
        mock_run.assert_not_called()
    
    @patch('src.services.repository_service.subprocess.run')
    def test_checkout_pr_branch_checkout_failure(self, mock_run):
        """Test PR branch checkout failure."""
        # Create test repository directory
        repo_path = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(repo_path)
        
        # Mock git fetch success, checkout failure
        def mock_git_commands(*args, **kwargs):
            cmd = args[0]
            if cmd[1] == 'fetch':
                return Mock(returncode=0, stderr="")
            elif cmd[1] == 'checkout':
                return Mock(returncode=1, stderr="fatal: reference is not a tree: abc123")
            
        mock_run.side_effect = mock_git_commands
        
        pr_head_sha = "abc123def456"
        
        with pytest.raises(RepositoryError) as exc_info:
            self.repo_service.checkout_pr_branch(repo_path, pr_head_sha)
        
        assert "Failed to checkout SHA" in str(exc_info.value)
        assert pr_head_sha in str(exc_info.value)


# Import subprocess for the timeout test
import subprocess
