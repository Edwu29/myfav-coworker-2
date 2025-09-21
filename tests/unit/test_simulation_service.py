"""Unit tests for simulation service."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone

from services.simulation_service import SimulationService
from models.simulation_job import SimulationJobModel, JobStatus


class TestSimulationService:
    """Test cases for SimulationService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = SimulationService()
        self.sample_job = SimulationJobModel(
            user_id="test-user-123",
            pr_url="https://github.com/owner/repo/pull/123",
            pr_owner="owner",
            pr_repo="repo",
            pr_number=123,
            pr_head_sha="abc123",
            pr_base_sha="def456"
        )
        self.repo_path = "/tmp/test-repo"
    
    @pytest.mark.asyncio
    async def test_run_simulation_success(self):
        """Test successful simulation run."""
        with patch('services.simulation_service.async_playwright') as mock_playwright:
            # Mock playwright context manager
            mock_context = AsyncMock()
            mock_browser = AsyncMock()
            mock_page = AsyncMock()
            
            mock_playwright.return_value.__aenter__.return_value = mock_context
            mock_context.chromium.launch.return_value = mock_browser
            mock_browser.__aenter__.return_value = mock_browser
            mock_browser.__aexit__.return_value = None
            mock_browser.new_page.return_value = mock_page
            
            # Mock page interactions
            mock_page.goto = AsyncMock()
            mock_page.wait_for_selector = AsyncMock()
            mock_page.title.return_value = "Test Page"
            
            # Mock diff generation
            with patch.object(self.service, '_generate_test_script') as mock_gen_script:
                mock_gen_script.return_value = {
                    "type": "basic_health_check",
                    "description": "Test script",
                    "steps": [
                        {
                            "action": "navigate",
                            "url": "http://localhost:3000",
                            "description": "Navigate to app"
                        },
                        {
                            "action": "check_title",
                            "expected": ".*",
                            "description": "Check title"
                        }
                    ]
                }
                
                result = await self.service.run_simulation(self.sample_job, self.repo_path)
                
                assert result["result"] == "pass"
                assert "summary" in result
                assert "execution_logs" in result
                assert "test_script" in result
                assert "timestamp" in result
                
                # Verify browser was launched
                mock_context.chromium.launch.assert_called_once()
                mock_browser.new_page.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_simulation_browser_failure(self):
        """Test simulation with browser launch failure."""
        with patch('services.simulation_service.async_playwright') as mock_playwright:
            mock_context = AsyncMock()
            mock_playwright.return_value.__aenter__.return_value = mock_context
            mock_context.chromium.launch.side_effect = Exception("Browser launch failed")
            
            result = await self.service.run_simulation(self.sample_job, self.repo_path)
            
            assert result["result"] == "fail"
            assert "Browser launch failed" in result["summary"]
            assert result["test_script"] is None
    
    @pytest.mark.asyncio
    async def test_generate_test_script_success(self):
        """Test successful test script generation."""
        with patch.object(self.service, '_get_pr_diff') as mock_get_diff:
            mock_get_diff.return_value = "diff --git a/file.js b/file.js\n+added line"
            
            script = await self.service._generate_test_script(self.sample_job, self.repo_path)
            
            assert script["type"] == "basic_health_check"
            assert "steps" in script
            assert len(script["steps"]) > 0
            assert "diff_summary" in script
            assert script["diff_summary"]["has_diff"] is True
    
    @pytest.mark.asyncio
    async def test_generate_test_script_diff_failure(self):
        """Test test script generation with diff failure."""
        with patch.object(self.service, '_get_pr_diff') as mock_get_diff:
            mock_get_diff.side_effect = Exception("Git diff failed")
            
            script = await self.service._generate_test_script(self.sample_job, self.repo_path)
            
            assert script["type"] == "fallback"
            assert "error" in script
            assert "Git diff failed" in script["error"]
    
    @pytest.mark.asyncio
    async def test_get_pr_diff_success(self):
        """Test successful PR diff retrieval."""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "diff --git a/test.js b/test.js\n+new line"
            mock_run.return_value = mock_result
            
            diff = await self.service._get_pr_diff(self.repo_path, "base123", "head456")
            
            assert "diff --git" in diff
            assert "+new line" in diff
            mock_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_pr_diff_command_failure(self):
        """Test PR diff retrieval with command failure."""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "fatal: bad revision"
            mock_run.return_value = mock_result
            
            diff = await self.service._get_pr_diff(self.repo_path, "bad123", "head456")
            
            assert diff == ""
    
    @pytest.mark.asyncio
    async def test_get_pr_diff_timeout(self):
        """Test PR diff retrieval with timeout."""
        with patch('subprocess.run') as mock_run:
            from subprocess import TimeoutExpired
            mock_run.side_effect = TimeoutExpired("git", 30)
            
            diff = await self.service._get_pr_diff(self.repo_path, "base123", "head456")
            
            assert diff == ""
    
    def test_summarize_diff_with_content(self):
        """Test diff summarization with content."""
        diff_content = """diff --git a/file1.js b/file1.js
index 123..456 100644
--- a/file1.js
+++ b/file1.js
@@ -1,3 +1,4 @@
 existing line
+added line
-removed line
 another line
diff --git a/file2.py b/file2.py
new file mode 100644"""
        
        summary = self.service._summarize_diff(diff_content)
        
        assert summary["files_changed"] == 2
        assert summary["lines_added"] > 0
        assert summary["lines_removed"] > 0
        assert summary["has_diff"] is True
    
    def test_summarize_diff_empty(self):
        """Test diff summarization with empty content."""
        summary = self.service._summarize_diff("")
        
        assert summary["files_changed"] == 0
        assert summary["lines_added"] == 0
        assert summary["lines_removed"] == 0
        assert summary["has_diff"] is False
    
    @pytest.mark.asyncio
    async def test_execute_test_script_navigate_success(self):
        """Test successful test script execution with navigation."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.title.return_value = "Test Page"
        
        test_script = {
            "description": "Navigation test",
            "steps": [
                {
                    "action": "navigate",
                    "url": "http://localhost:3000",
                    "description": "Navigate to app"
                },
                {
                    "action": "check_title",
                    "expected": "Test.*",
                    "description": "Check title matches"
                }
            ]
        }
        
        result = await self.service._execute_test_script(mock_page, test_script, self.repo_path)
        
        assert result["success"] is True
        assert "PASSED" in result["summary"]
        assert len(result["logs"]) > 0
        mock_page.goto.assert_called_once_with("http://localhost:3000", timeout=30000)
    
    @pytest.mark.asyncio
    async def test_execute_test_script_step_failure(self):
        """Test test script execution with step failure."""
        mock_page = AsyncMock()
        mock_page.goto.side_effect = Exception("Navigation failed")
        
        test_script = {
            "description": "Failing test",
            "steps": [
                {
                    "action": "navigate",
                    "url": "http://localhost:3000",
                    "description": "Navigate to app"
                }
            ]
        }
        
        result = await self.service._execute_test_script(mock_page, test_script, self.repo_path)
        
        assert result["success"] is False
        assert "FAILED" in result["summary"]
        assert any("Navigation failed" in log for log in result["logs"])
    
    @pytest.mark.asyncio
    async def test_execute_test_script_wait_for_selector(self):
        """Test test script execution with selector waiting."""
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        
        test_script = {
            "description": "Selector test",
            "steps": [
                {
                    "action": "wait_for_selector",
                    "selector": "body",
                    "timeout": 5000,
                    "description": "Wait for body"
                }
            ]
        }
        
        result = await self.service._execute_test_script(mock_page, test_script, self.repo_path)
        
        assert result["success"] is True
        mock_page.wait_for_selector.assert_called_once_with("body", timeout=5000)
    
    @pytest.mark.asyncio
    async def test_execute_test_script_title_mismatch(self):
        """Test test script execution with title mismatch."""
        mock_page = AsyncMock()
        mock_page.title.return_value = "Wrong Title"
        
        test_script = {
            "description": "Title check test",
            "steps": [
                {
                    "action": "check_title",
                    "expected": "Expected Title",
                    "description": "Check specific title"
                }
            ]
        }
        
        result = await self.service._execute_test_script(mock_page, test_script, self.repo_path)
        
        assert result["success"] is False
        assert any("Title mismatch" in log for log in result["logs"])
    
    @pytest.mark.asyncio
    async def test_execute_test_script_unknown_action(self):
        """Test test script execution with unknown action."""
        mock_page = AsyncMock()
        
        test_script = {
            "description": "Unknown action test",
            "steps": [
                {
                    "action": "unknown_action",
                    "description": "Unknown action"
                }
            ]
        }
        
        result = await self.service._execute_test_script(mock_page, test_script, self.repo_path)
        
        assert result["success"] is True  # Unknown actions are warnings, not failures
        assert any("Unknown action" in log for log in result["logs"])
    
    def test_validate_environment_success(self):
        """Test environment validation success."""
        with patch('services.simulation_service.playwright'):
            result = self.service.validate_environment()
            assert result is True
    
    def test_validate_environment_failure(self):
        """Test environment validation failure."""
        with patch('services.simulation_service.playwright', side_effect=ImportError):
            result = self.service.validate_environment()
            assert result is False
