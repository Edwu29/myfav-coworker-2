"""Unit tests for repository service diff calculation functionality."""

import unittest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import tempfile
import os
from pathlib import Path

from src.services.repository_service import RepositoryService, RepositoryError


class TestRepositoryServiceDiff(unittest.TestCase):
    """Test cases for repository service diff calculation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.repo_service = RepositoryService()
        self.test_repo_path = "/tmp/test_repo"
        
    @patch('subprocess.run')
    def test_calculate_diff_success(self, mock_run):
        """Test successful diff calculation."""
        # Mock git diff --name-status output
        mock_name_status = Mock()
        mock_name_status.returncode = 0
        mock_name_status.stdout = "M\tsrc/api/auth.py\nA\tsrc/services/new_service.py\nD\tREADME.old"
        
        # Mock git diff full output
        mock_full_diff = Mock()
        mock_full_diff.returncode = 0
        mock_full_diff.stdout = "diff --git a/src/api/auth.py b/src/api/auth.py\n+new line"
        
        mock_run.side_effect = [mock_name_status, mock_full_diff]
        
        with patch('os.path.exists', return_value=True):
            result = self.repo_service.calculate_diff(
                self.test_repo_path, 
                "main", 
                "feature-branch"
            )
        
        # Verify result structure
        self.assertIn('base_branch', result)
        self.assertIn('target_branch', result)
        self.assertIn('diff_content', result)
        self.assertIn('changed_files', result)
        self.assertIn('relevant_files', result)
        self.assertIn('has_changes', result)
        
        # Verify values
        self.assertEqual(result['base_branch'], 'main')
        self.assertEqual(result['target_branch'], 'feature-branch')
        self.assertTrue(result['has_changes'])
        self.assertEqual(len(result['changed_files']), 3)
        
        # Verify git commands were called correctly
        expected_calls = [
            unittest.mock.call(
                ['git', 'diff', '--name-status', 'main...feature-branch'],
                cwd=self.test_repo_path,
                capture_output=True,
                text=True,
                timeout=30
            ),
            unittest.mock.call(
                ['git', 'diff', 'main...feature-branch'],
                cwd=self.test_repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
        ]
        mock_run.assert_has_calls(expected_calls)
    
    @patch('subprocess.run')
    def test_calculate_diff_no_repo_path(self, mock_run):
        """Test diff calculation with non-existent repository path."""
        with patch('os.path.exists', return_value=False):
            with self.assertRaises(RepositoryError) as context:
                self.repo_service.calculate_diff(self.test_repo_path)
            
            self.assertIn("Repository path does not exist", str(context.exception))
    
    @patch('subprocess.run')
    def test_calculate_diff_git_command_failure(self, mock_run):
        """Test diff calculation when git command fails."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "fatal: bad revision"
        
        with patch('os.path.exists', return_value=True):
            with self.assertRaises(RepositoryError) as context:
                self.repo_service.calculate_diff(self.test_repo_path)
            
            self.assertIn("Failed to calculate diff", str(context.exception))
    
    @patch('subprocess.run')
    def test_calculate_diff_timeout(self, mock_run):
        """Test diff calculation timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired(['git', 'diff'], 30)
        
        with patch('os.path.exists', return_value=True):
            with self.assertRaises(RepositoryError) as context:
                self.repo_service.calculate_diff(self.test_repo_path)
            
            self.assertIn("Diff calculation operation timed out", str(context.exception))
    
    def test_parse_diff_files_success(self):
        """Test parsing git diff --name-status output."""
        diff_output = "M\tsrc/api/auth.py\nA\tsrc/services/new_service.py\nD\tREADME.old\nR\told_file.py\tnew_file.py"
        
        result = self.repo_service._parse_diff_files(diff_output)
        
        self.assertEqual(len(result), 4)
        
        # Check first file (modified)
        self.assertEqual(result[0]['status'], 'M')
        self.assertEqual(result[0]['filename'], 'src/api/auth.py')
        self.assertEqual(result[0]['change_type'], 'modified')
        
        # Check second file (added)
        self.assertEqual(result[1]['status'], 'A')
        self.assertEqual(result[1]['filename'], 'src/services/new_service.py')
        self.assertEqual(result[1]['change_type'], 'added')
        
        # Check third file (deleted)
        self.assertEqual(result[2]['status'], 'D')
        self.assertEqual(result[2]['filename'], 'README.old')
        self.assertEqual(result[2]['change_type'], 'deleted')
        
        # Check fourth file (renamed)
        self.assertEqual(result[3]['status'], 'R')
        self.assertEqual(result[3]['filename'], 'old_file.py')
        self.assertEqual(result[3]['change_type'], 'renamed')
    
    def test_parse_diff_files_empty_output(self):
        """Test parsing empty diff output."""
        result = self.repo_service._parse_diff_files("")
        self.assertEqual(len(result), 0)
    
    def test_get_change_type_mapping(self):
        """Test change type mapping from git status codes."""
        test_cases = [
            ('A', 'added'),
            ('M', 'modified'),
            ('D', 'deleted'),
            ('R', 'renamed'),
            ('C', 'copied'),
            ('T', 'type_changed'),
            ('X', 'unknown')  # Unknown status
        ]
        
        for status, expected_type in test_cases:
            result = self.repo_service._get_change_type(status)
            self.assertEqual(result, expected_type)
    
    def test_filter_relevant_files_source_code(self):
        """Test filtering to include relevant source code files."""
        changed_files = [
            {'status': 'M', 'filename': 'src/api/auth.py', 'change_type': 'modified'},
            {'status': 'A', 'filename': 'src/services/new_service.js', 'change_type': 'added'},
            {'status': 'M', 'filename': 'frontend/component.tsx', 'change_type': 'modified'},
            {'status': 'A', 'filename': 'styles/main.css', 'change_type': 'added'},
            {'status': 'M', 'filename': 'requirements.txt', 'change_type': 'modified'},
            {'status': 'A', 'filename': 'Dockerfile', 'change_type': 'added'}
        ]
        
        result = self.repo_service._filter_relevant_files(changed_files)
        
        # Should include all files as they are relevant
        self.assertEqual(len(result), 6)
        
        # Verify all files are included
        filenames = [f['filename'] for f in result]
        expected_files = [
            'src/api/auth.py', 'src/services/new_service.js', 
            'frontend/component.tsx', 'styles/main.css',
            'requirements.txt', 'Dockerfile'
        ]
        for expected_file in expected_files:
            self.assertIn(expected_file, filenames)
    
    def test_filter_relevant_files_exclude_binary_and_config(self):
        """Test filtering to exclude binary and irrelevant files."""
        changed_files = [
            {'status': 'M', 'filename': 'src/api/auth.py', 'change_type': 'modified'},
            {'status': 'A', 'filename': 'image.jpg', 'change_type': 'added'},
            {'status': 'M', 'filename': 'package-lock.json', 'change_type': 'modified'},
            {'status': 'A', 'filename': '.env.local', 'change_type': 'added'},
            {'status': 'M', 'filename': '.DS_Store', 'change_type': 'modified'},
            {'status': 'A', 'filename': 'node_modules/package/index.js', 'change_type': 'added'},
            {'status': 'M', 'filename': 'document.pdf', 'change_type': 'modified'}
        ]
        
        result = self.repo_service._filter_relevant_files(changed_files)
        
        # Should only include the Python file
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['filename'], 'src/api/auth.py')
    
    def test_filter_relevant_files_empty_list(self):
        """Test filtering with empty file list."""
        result = self.repo_service._filter_relevant_files([])
        self.assertEqual(len(result), 0)
    
    @patch('subprocess.run')
    def test_calculate_diff_no_changes(self, mock_run):
        """Test diff calculation when there are no changes."""
        # Mock empty git diff output
        mock_name_status = Mock()
        mock_name_status.returncode = 0
        mock_name_status.stdout = ""
        
        mock_full_diff = Mock()
        mock_full_diff.returncode = 0
        mock_full_diff.stdout = ""
        
        mock_run.side_effect = [mock_name_status, mock_full_diff]
        
        with patch('os.path.exists', return_value=True):
            result = self.repo_service.calculate_diff(self.test_repo_path)
        
        self.assertFalse(result['has_changes'])
        self.assertEqual(len(result['changed_files']), 0)
        self.assertEqual(len(result['relevant_files']), 0)
        self.assertEqual(result['total_files_changed'], 0)
        self.assertEqual(result['relevant_files_changed'], 0)
    
    @patch('subprocess.run')
    def test_calculate_diff_default_branches(self, mock_run):
        """Test diff calculation with default branch parameters."""
        mock_name_status = Mock()
        mock_name_status.returncode = 0
        mock_name_status.stdout = "M\ttest.py"
        
        mock_full_diff = Mock()
        mock_full_diff.returncode = 0
        mock_full_diff.stdout = "diff content"
        
        mock_run.side_effect = [mock_name_status, mock_full_diff]
        
        with patch('os.path.exists', return_value=True):
            result = self.repo_service.calculate_diff(self.test_repo_path)
        
        # Should use default values
        self.assertEqual(result['base_branch'], 'main')
        self.assertEqual(result['target_branch'], 'HEAD')
        
        # Verify git command used default branches
        mock_run.assert_any_call(
            ['git', 'diff', '--name-status', 'main...HEAD'],
            cwd=self.test_repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )


if __name__ == '__main__':
    unittest.main()
