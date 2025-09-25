"""Repository management service for local git operations."""

import os
import shutil
import subprocess
import tempfile
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path


logger = logging.getLogger(__name__)


class RepositoryError(Exception):
    """Exception raised for repository operation errors."""
    pass


class RepositoryService:
    """Service for managing local git repository operations."""
    
    def __init__(self, base_path: str = "/tmp"):
        """
        Initialize repository service.
        
        Args:
            base_path: Base directory for repository storage (Lambda /tmp)
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        
    def clone_repository(self, repo_url: str, access_token: str, target_dir: Optional[str] = None) -> str:
        """
        Clone a GitHub repository to local storage.
        
        Args:
            repo_url: GitHub repository URL (https://github.com/owner/repo.git)
            access_token: GitHub access token for authentication
            target_dir: Optional target directory name
            
        Returns:
            Path to cloned repository
            
        Raises:
            RepositoryError: If clone operation fails
        """
        try:
            # Generate unique directory name if not provided
            if not target_dir:
                target_dir = f"repo_{os.urandom(8).hex()}"
            
            repo_path = self.base_path / target_dir
            
            # Remove existing directory if it exists
            if repo_path.exists():
                shutil.rmtree(repo_path)
            
            # Construct authenticated clone URL
            if repo_url.startswith('https://github.com/'):
                # Convert to authenticated URL
                repo_part = repo_url.replace('https://github.com/', '')
                auth_url = f"https://{access_token}@github.com/{repo_part}"
            else:
                raise RepositoryError(f"Unsupported repository URL format: {repo_url}")
            
            # Execute git clone
            cmd = ['git', 'clone', auth_url, str(repo_path)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Git clone failed: {result.stderr}")
                raise RepositoryError(f"Failed to clone repository: {result.stderr}")
            
            logger.info(f"Successfully cloned repository to: {repo_path}")
            return str(repo_path)
            
        except subprocess.TimeoutExpired:
            logger.error("Git clone operation timed out")
            raise RepositoryError("Repository clone operation timed out")
        except Exception as e:
            logger.error(f"Failed to clone repository: {e}")
            raise RepositoryError(f"Repository clone failed: {e}")
    
    def checkout_branch(self, repo_path: str, branch_name: str) -> bool:
        """
        Checkout a specific branch in the repository.
        
        Args:
            repo_path: Path to local repository
            branch_name: Branch name to checkout
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            RepositoryError: If checkout operation fails
        """
        try:
            if not os.path.exists(repo_path):
                raise RepositoryError(f"Repository path does not exist: {repo_path}")
            
            # First, fetch all branches
            fetch_cmd = ['git', 'fetch', 'origin']
            fetch_result = subprocess.run(
                fetch_cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if fetch_result.returncode != 0:
                logger.warning(f"Git fetch warning: {fetch_result.stderr}")
            
            # Checkout the branch
            checkout_cmd = ['git', 'checkout', branch_name]
            result = subprocess.run(
                checkout_cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                # Try checking out as remote branch
                remote_checkout_cmd = ['git', 'checkout', '-b', branch_name, f'origin/{branch_name}']
                remote_result = subprocess.run(
                    remote_checkout_cmd,
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if remote_result.returncode != 0:
                    logger.error(f"Git checkout failed: {result.stderr}")
                    raise RepositoryError(f"Failed to checkout branch {branch_name}: {result.stderr}")
            
            logger.info(f"Successfully checked out branch: {branch_name}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Git checkout operation timed out")
            raise RepositoryError("Branch checkout operation timed out")
        except Exception as e:
            logger.error(f"Failed to checkout branch {branch_name}: {e}")
            raise RepositoryError(f"Branch checkout failed: {e}")
    
    def get_current_branch(self, repo_path: str) -> str:
        """
        Get the currently checked out branch name.
        
        Args:
            repo_path: Path to local repository
            
        Returns:
            Current branch name
            
        Raises:
            RepositoryError: If operation fails
        """
        try:
            cmd = ['git', 'rev-parse', '--abbrev-ref', 'HEAD']
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                raise RepositoryError(f"Failed to get current branch: {result.stderr}")
            
            branch_name = result.stdout.strip()
            logger.info(f"Current branch: {branch_name}")
            return branch_name
            
        except subprocess.TimeoutExpired:
            raise RepositoryError("Get current branch operation timed out")
        except Exception as e:
            logger.error(f"Failed to get current branch: {e}")
            raise RepositoryError(f"Get current branch failed: {e}")
    
    def get_commit_sha(self, repo_path: str, ref: str = "HEAD") -> str:
        """
        Get commit SHA for a given reference.
        
        Args:
            repo_path: Path to local repository
            ref: Git reference (default: HEAD)
            
        Returns:
            Commit SHA
            
        Raises:
            RepositoryError: If operation fails
        """
        try:
            cmd = ['git', 'rev-parse', ref]
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                raise RepositoryError(f"Failed to get commit SHA: {result.stderr}")
            
            commit_sha = result.stdout.strip()
            logger.info(f"Commit SHA for {ref}: {commit_sha}")
            return commit_sha
            
        except subprocess.TimeoutExpired:
            raise RepositoryError("Get commit SHA operation timed out")
        except Exception as e:
            logger.error(f"Failed to get commit SHA: {e}")
            raise RepositoryError(f"Get commit SHA failed: {e}")
    
    def cleanup_repository(self, repo_path: str) -> bool:
        """
        Clean up repository directory.
        
        Args:
            repo_path: Path to repository to clean up
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path)
                logger.info(f"Successfully cleaned up repository: {repo_path}")
                return True
            else:
                logger.warning(f"Repository path does not exist: {repo_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to cleanup repository {repo_path}: {e}")
            return False
    
    def get_repository_size(self, repo_path: str) -> int:
        """
        Get repository size in bytes.
        
        Args:
            repo_path: Path to repository
            
        Returns:
            Repository size in bytes
        """
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(repo_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
            
            logger.info(f"Repository size: {total_size} bytes")
            return total_size
            
        except Exception as e:
            logger.error(f"Failed to calculate repository size: {e}")
            return 0
    
    def validate_repository_constraints(self, repo_path: str, max_size_mb: int = 400) -> Dict[str, Any]:
        """
        Validate that a repository's total size is within a given maximum size.
        
        Parameters:
            repo_path (str): Path to the repository directory to measure.
            max_size_mb (int): Maximum allowed repository size in megabytes (default 400).
        
        Returns:
            dict: Validation result containing:
                - 'valid' (bool): True if repository size is less than or equal to max_size_mb, False otherwise.
                - 'size_bytes' (int): Total size in bytes.
                - 'size_mb' (float): Total size in megabytes (rounded to 2 decimals).
                - 'max_size_mb' (int): The provided maximum size in megabytes.
                - 'warnings' (List[str]): Warning messages for nearing or exceeding the limit.
        """
        try:
            size_bytes = self.get_repository_size(repo_path)
            size_mb = size_bytes / (1024 * 1024)
            
            validation_result = {
                'valid': size_mb <= max_size_mb,
                'size_bytes': size_bytes,
                'size_mb': round(size_mb, 2),
                'max_size_mb': max_size_mb,
                'warnings': []
            }
            
            if size_mb > max_size_mb:
                validation_result['warnings'].append(
                    f"Repository size ({size_mb:.2f}MB) exceeds limit ({max_size_mb}MB)"
                )
            
            if size_mb > max_size_mb * 0.8:  # Warning at 80% of limit
                validation_result['warnings'].append(
                    f"Repository size ({size_mb:.2f}MB) is approaching limit ({max_size_mb}MB)"
                )
            
            logger.info(f"Repository validation: {validation_result}")
            return validation_result
            
        except Exception as e:
            logger.error(f"Repository validation failed: {e}")
            return {
                'valid': False,
                'error': str(e),
                'warnings': ['Repository validation failed']
            }
    
    def calculate_diff(self, repo_path: str, base_branch: str = "main", target_branch: str = "HEAD") -> Dict[str, Any]:
        """
        Compute a structured diff between two branches in a local repository.
        
        Parameters:
            repo_path (str): Path to the local git repository to inspect.
            base_branch (str): Base branch to compare against (default "main").
            target_branch (str): Target branch or ref to compare (default "HEAD").
        
        Returns:
            dict: A dictionary containing diff data and metadata with the following keys:
                - base_branch (str): The base branch used for the comparison.
                - target_branch (str): The target branch/ref used for the comparison.
                - diff_content (str): Full git diff output between the branches.
                - changed_files (List[Dict[str, str]]): Parsed list of changed files with keys
                  like `status`, `filename`, and `change_type`.
                - relevant_files (List[Dict[str, str]]): Subset of `changed_files` considered
                  relevant by repository heuristics (source/config files).
                - total_files_changed (int): Number of entries in `changed_files`.
                - relevant_files_changed (int): Number of entries in `relevant_files`.
                - has_changes (bool): `true` if any files changed, `false` otherwise.
        
        Raises:
            RepositoryError: If the repository path does not exist, git commands fail, or the
            diff operation times out.
        """
        try:
            if not os.path.exists(repo_path):
                raise RepositoryError(f"Repository path does not exist: {repo_path}")
            
            # Get diff with file names and stats
            diff_cmd = ['git', 'diff', '--name-status', f'{base_branch}...{target_branch}']
            diff_result = subprocess.run(
                diff_cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if diff_result.returncode != 0:
                logger.error(f"Git diff failed: {diff_result.stderr}")
                raise RepositoryError(f"Failed to calculate diff: {diff_result.stderr}")
            
            # Get full diff content
            full_diff_cmd = ['git', 'diff', f'{base_branch}...{target_branch}']
            full_diff_result = subprocess.run(
                full_diff_cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if full_diff_result.returncode != 0:
                logger.error(f"Git full diff failed: {full_diff_result.stderr}")
                raise RepositoryError(f"Failed to get full diff: {full_diff_result.stderr}")
            
            # Parse changed files
            changed_files = self._parse_diff_files(diff_result.stdout)
            
            # Filter relevant files (exclude binary, config files)
            relevant_files = self._filter_relevant_files(changed_files)
            
            diff_data = {
                'base_branch': base_branch,
                'target_branch': target_branch,
                'diff_content': full_diff_result.stdout,
                'changed_files': changed_files,
                'relevant_files': relevant_files,
                'total_files_changed': len(changed_files),
                'relevant_files_changed': len(relevant_files),
                'has_changes': len(changed_files) > 0
            }
            
            logger.info(f"Calculated diff: {len(changed_files)} files changed, {len(relevant_files)} relevant")
            return diff_data
            
        except subprocess.TimeoutExpired:
            logger.error("Git diff operation timed out")
            raise RepositoryError("Diff calculation operation timed out")
        except Exception as e:
            logger.error(f"Failed to calculate diff: {e}")
            raise RepositoryError(f"Diff calculation failed: {e}")
    
    def _parse_diff_files(self, diff_output: str) -> List[Dict[str, str]]:
        """
        Parse the output of `git diff --name-status` into a list of structured file-change records.
        
        Parameters:
            diff_output (str): Raw stdout from `git diff --name-status`.
        
        Returns:
            List[Dict[str, str]]: A list of dictionaries, each with keys:
                - 'status': the raw git status code (e.g., 'A', 'M', 'D', 'R', ...),
                - 'filename': the affected path as reported by git,
                - 'change_type': a human-readable change type derived from the status.
        
        Notes:
            - Empty lines in the input are ignored.
            - Lines are expected to be tab-separated; only lines with at least two tab-separated fields are included.
        """
        files = []
        for line in diff_output.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split('\t')
            if len(parts) >= 2:
                status = parts[0]
                filename = parts[1]
                
                files.append({
                    'status': status,
                    'filename': filename,
                    'change_type': self._get_change_type(status)
                })
        
        return files
    
    def _get_change_type(self, status: str) -> str:
        """
        Map a git --name-status status code to a human-readable change type.
        
        Parameters:
            status (str): Git status code string (e.g., 'A', 'M', 'D', 'R', 'C', 'T').
        
        Returns:
            str: One of 'added', 'modified', 'deleted', 'renamed', 'copied', 'type_changed', or 'unknown'.
        """
        status_map = {
            'A': 'added',
            'M': 'modified',
            'D': 'deleted',
            'R': 'renamed',
            'C': 'copied',
            'T': 'type_changed'
        }
        return status_map.get(status[0], 'unknown')
    
    def _filter_relevant_files(self, changed_files: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Filter a list of changed file records to those considered relevant source or configuration files.
        
        Parameters:
            changed_files (List[Dict[str, str]]): List of change records where each dict contains at least a 'filename' key.
        
        Returns:
            List[Dict[str, str]]: Subset of the input list containing only entries whose filenames are considered relevant source files or common configuration files.
        """
        # File extensions to include (source code)
        relevant_extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
            '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
            '.html', '.css', '.scss', '.sass', '.less', '.vue', '.svelte'
        }
        
        # File patterns to exclude
        exclude_patterns = {
            '.git', '.gitignore', '.gitmodules',
            'package-lock.json', 'yarn.lock', 'Pipfile.lock',
            '.env', '.env.local', '.env.production',
            'node_modules', '__pycache__', '.pytest_cache',
            '.DS_Store', 'Thumbs.db',
            '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico',
            '.pdf', '.doc', '.docx', '.zip', '.tar', '.gz'
        }
        
        relevant_files = []
        for file_info in changed_files:
            filename = file_info['filename']
            file_path = Path(filename)
            
            # Check if file should be excluded
            should_exclude = False
            for pattern in exclude_patterns:
                if pattern in filename.lower() or filename.lower().endswith(pattern):
                    should_exclude = True
                    break
            
            if should_exclude:
                continue
            
            # Include if it has a relevant extension or is a common config file
            if (file_path.suffix.lower() in relevant_extensions or
                filename in ['Dockerfile', 'Makefile', 'requirements.txt', 'setup.py', 'pyproject.toml']):
                relevant_files.append(file_info)
        
        return relevant_files
    
    def get_repository_path(self, owner: str, repo: str) -> str:
        """
        Compute the local filesystem path for a repository under the service's base_path using the pattern "{owner}_{repo}".
        
        Returns:
            repo_path (str): String path to the repository directory (base_path/{owner}_{repo}).
        """
        # Create a consistent directory name based on owner/repo
        repo_dir = f"{owner}_{repo}"
        repo_path = self.base_path / repo_dir
        return str(repo_path)
    
    def checkout_pr_branch(self, repo_path: str, pr_head_sha: str) -> bool:
        """
        Check out the repository at repo_path to the specified commit SHA (PR head).
        
        Parameters:
            repo_path (str): Path to the local Git repository.
            pr_head_sha (str): Commit SHA to check out.
        
        Returns:
            True if the commit was successfully checked out.
        
        Raises:
            RepositoryError: If the repository path does not exist, the checkout fails, or the operation times out.
        """
        try:
            if not os.path.exists(repo_path):
                raise RepositoryError(f"Repository path does not exist: {repo_path}")
            
            # First, fetch all refs to ensure we have the latest commits
            fetch_cmd = ['git', 'fetch', 'origin', '+refs/*:refs/*']
            fetch_result = subprocess.run(
                fetch_cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if fetch_result.returncode != 0:
                logger.warning(f"Git fetch warning: {fetch_result.stderr}")
            
            # Checkout the specific commit SHA
            checkout_cmd = ['git', 'checkout', pr_head_sha]
            result = subprocess.run(
                checkout_cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"Git checkout SHA failed: {result.stderr}")
                raise RepositoryError(f"Failed to checkout SHA {pr_head_sha}: {result.stderr}")
            
            logger.info(f"Successfully checked out commit SHA: {pr_head_sha}")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("Git checkout SHA operation timed out")
            raise RepositoryError("SHA checkout operation timed out")
        except Exception as e:
            logger.error(f"Failed to checkout SHA {pr_head_sha}: {e}")
            raise RepositoryError(f"SHA checkout failed: {e}")
