"""Simulation runner service for executing browser automation tests."""

import os
import logging
import asyncio
import subprocess
from typing import Optional, Dict, Any, List
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page
from models.simulation_job import SimulationJobModel, JobStatus

logger = logging.getLogger(__name__)


class SimulationService:
    """Service for running browser automation simulations on PR code."""
    
    def __init__(self):
        """Initialize simulation service."""
        self.browser_timeout = int(os.getenv('SIMULATION_BROWSER_TIMEOUT', '30000'))  # 30 seconds
        self.script_timeout = int(os.getenv('SIMULATION_SCRIPT_TIMEOUT', '300000'))  # 5 minutes
        self.headless = os.getenv('SIMULATION_HEADLESS', 'true').lower() == 'true'
        
    async def run_simulation(self, job: SimulationJobModel, repo_path: str) -> Dict[str, Any]:
        """
        Run browser automation simulation for a PR.
        
        Args:
            job: Simulation job with PR details
            repo_path: Path to local repository clone
            
        Returns:
            Simulation report with results
        """
        logger.info(f"Starting simulation for job {job.job_id} in {repo_path}")
        
        try:
            # Generate test script based on PR diff
            test_script = await self._generate_test_script(job, repo_path)
            
            # Launch browser and execute test
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    headless=self.headless,
                    timeout=self.browser_timeout
                )
                
                try:
                    page = await browser.new_page()
                    result = await self._execute_test_script(page, test_script, repo_path)
                    
                    logger.info(f"Simulation completed for job {job.job_id}")
                    return {
                        "result": "pass" if result["success"] else "fail",
                        "summary": result["summary"],
                        "execution_logs": result["logs"],
                        "test_script": test_script,
                        "timestamp": result["timestamp"]
                    }
                    
                finally:
                    await browser.close()
                    
        except Exception as e:
            logger.error(f"Simulation failed for job {job.job_id}: {str(e)}")
            return {
                "result": "fail",
                "summary": f"Simulation failed: {str(e)}",
                "execution_logs": [f"ERROR: {str(e)}"],
                "test_script": None,
                "timestamp": None
            }
    
    async def _generate_test_script(self, job: SimulationJobModel, repo_path: str) -> Dict[str, Any]:
        """
        Generate test script by analyzing PR diff.
        
        Args:
            job: Simulation job with PR details
            repo_path: Path to repository
            
        Returns:
            Test script configuration
        """
        logger.info(f"Generating test script for PR {job.pr_url}")
        
        try:
            # Get PR diff using git
            diff_output = await self._get_pr_diff(repo_path, job.pr_base_sha, job.pr_head_sha)
            
            # For now, create a basic test script
            # TODO: In Story 1.5, this will use AI agent for diff analysis
            test_script = {
                "type": "basic_health_check",
                "description": "Basic application health check simulation",
                "steps": [
                    {
                        "action": "navigate",
                        "url": "http://localhost:3000",
                        "description": "Navigate to application root"
                    },
                    {
                        "action": "wait_for_selector",
                        "selector": "body",
                        "timeout": 5000,
                        "description": "Wait for page to load"
                    },
                    {
                        "action": "check_title",
                        "expected": ".*",
                        "description": "Verify page has a title"
                    }
                ],
                "diff_summary": self._summarize_diff(diff_output)
            }
            
            logger.info(f"Generated test script with {len(test_script['steps'])} steps")
            return test_script
            
        except Exception as e:
            logger.error(f"Failed to generate test script: {str(e)}")
            # Return minimal fallback script
            return {
                "type": "fallback",
                "description": "Fallback test script due to diff analysis failure",
                "steps": [
                    {
                        "action": "navigate",
                        "url": "http://localhost:3000",
                        "description": "Basic navigation test"
                    }
                ],
                "error": str(e)
            }
    
    async def _get_pr_diff(self, repo_path: str, base_sha: str, head_sha: str) -> str:
        """Get PR diff using git command."""
        try:
            cmd = ["git", "diff", f"{base_sha}..{head_sha}"]
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                logger.warning(f"Git diff failed: {result.stderr}")
                return ""
                
        except subprocess.TimeoutExpired:
            logger.error("Git diff command timed out")
            return ""
        except Exception as e:
            logger.error(f"Failed to get PR diff: {str(e)}")
            return ""
    
    def _summarize_diff(self, diff_output: str) -> Dict[str, Any]:
        """Create basic summary of diff output."""
        if not diff_output:
            return {"files_changed": 0, "lines_added": 0, "lines_removed": 0}
        
        lines = diff_output.split('\n')
        files_changed = len([line for line in lines if line.startswith('diff --git')])
        lines_added = len([line for line in lines if line.startswith('+')])
        lines_removed = len([line for line in lines if line.startswith('-')])
        
        return {
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "has_diff": len(diff_output.strip()) > 0
        }
    
    async def _execute_test_script(self, page: Page, test_script: Dict[str, Any], repo_path: str) -> Dict[str, Any]:
        """
        Execute test script using Playwright.
        
        Args:
            page: Playwright page instance
            test_script: Test script to execute
            repo_path: Repository path for context
            
        Returns:
            Execution results
        """
        from datetime import datetime, timezone
        
        start_time = datetime.now(timezone.utc)
        logs = []
        success = True
        
        try:
            logs.append(f"Starting test execution: {test_script['description']}")
            
            for i, step in enumerate(test_script.get('steps', [])):
                step_num = i + 1
                action = step.get('action')
                logs.append(f"Step {step_num}: {step.get('description', action)}")
                
                try:
                    if action == "navigate":
                        await page.goto(step['url'], timeout=self.browser_timeout)
                        logs.append(f"  ✓ Navigated to {step['url']}")
                        
                    elif action == "wait_for_selector":
                        await page.wait_for_selector(
                            step['selector'], 
                            timeout=step.get('timeout', 5000)
                        )
                        logs.append(f"  ✓ Found selector: {step['selector']}")
                        
                    elif action == "check_title":
                        title = await page.title()
                        import re
                        if re.match(step['expected'], title):
                            logs.append(f"  ✓ Title matches pattern: {title}")
                        else:
                            logs.append(f"  ✗ Title mismatch. Expected pattern: {step['expected']}, Got: {title}")
                            success = False
                            
                    else:
                        logs.append(f"  ⚠ Unknown action: {action}")
                        
                except Exception as step_error:
                    logs.append(f"  ✗ Step failed: {str(step_error)}")
                    success = False
                    
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            summary = f"Test {'PASSED' if success else 'FAILED'} in {duration:.2f}s"
            logs.append(summary)
            
            return {
                "success": success,
                "summary": summary,
                "logs": logs,
                "timestamp": end_time.isoformat(),
                "duration_seconds": duration
            }
            
        except Exception as e:
            logs.append(f"Test execution failed: {str(e)}")
            return {
                "success": False,
                "summary": f"Test execution failed: {str(e)}",
                "logs": logs,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": 0
            }
    
    def validate_environment(self) -> bool:
        """Validate that simulation environment is properly configured."""
        try:
            # Check if Playwright is available
            import playwright
            logger.info("Playwright is available")
            return True
        except ImportError:
            logger.error("Playwright is not installed")
            return False
