"""Simulation runner service for executing browser automation tests."""

import os
import logging
import asyncio
import subprocess
from typing import Optional, Dict, Any, List
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page
from models.simulation_job import SimulationJobModel, JobStatus
from services.repository_service import RepositoryService
from services.ai_agent_service import AIAgentService

logger = logging.getLogger(__name__)


class SimulationService:
    """Service for running browser automation simulations on PR code."""
    
    def __init__(self):
        """Initialize simulation service."""
        self.browser_timeout = int(os.getenv('SIMULATION_BROWSER_TIMEOUT', '30000'))  # 30 seconds
        self.script_timeout = int(os.getenv('SIMULATION_SCRIPT_TIMEOUT', '300000'))  # 5 minutes
        self.headless = os.getenv('SIMULATION_HEADLESS', 'true').lower() == 'true'
        self.repository_service = RepositoryService()
        self.ai_agent_service = AIAgentService()
        
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
            # Generate AI-powered test plan based on PR diff
            test_plan = await self._generate_ai_test_plan(job, repo_path)
            
            # Launch browser and execute test plan
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    headless=self.headless,
                    timeout=self.browser_timeout
                )
                
                try:
                    page = await browser.new_page()
                    execution_result = await self._execute_test_plan(page, test_plan, repo_path)
                    
                    # Determine overall simulation result using AI analysis
                    result_determination = self.determine_simulation_result(
                        execution_result.get("test_results", []), 
                        test_plan
                    )
                    
                    logger.info(f"Simulation completed for job {job.job_id}: {result_determination['overall_result']}")
                    return {
                        "result": result_determination["overall_result"],
                        "summary": execution_result["summary"],
                        "execution_logs": execution_result["logs"],
                        "test_plan": test_plan,
                        "timestamp": execution_result["timestamp"],
                        "test_results": execution_result.get("test_results", []),
                        "result_determination": result_determination
                    }
                    
                finally:
                    await browser.close()
                    
        except Exception as e:
            logger.error(f"Simulation failed for job {job.job_id}: {str(e)}")
            return {
                "result": "fail",
                "summary": f"Simulation failed: {str(e)}",
                "execution_logs": [f"ERROR: {str(e)}"],
                "test_plan": None,
                "timestamp": None,
                "test_results": []
            }
    
    async def _generate_ai_test_plan(self, job: SimulationJobModel, repo_path: str) -> Dict[str, Any]:
        """
        Generate AI-powered test plan by analyzing PR diff.
        
        Args:
            job: Simulation job with PR details
            repo_path: Path to repository
            
        Returns:
            AI-generated test plan
        """
        logger.info(f"Generating AI test plan for PR {job.pr_url}")
        
        try:
            # Calculate diff using repository service
            diff_data = self.repository_service.calculate_diff(
                repo_path=repo_path,
                base_branch=job.pr_base_sha,
                target_branch=job.pr_head_sha
            )
            
            # Generate test plan using AI agent
            test_plan = await self.ai_agent_service.generate_test_plan(diff_data)
            
            logger.info(f"Generated AI test plan with {len(test_plan.get('test_cases', []))} test cases")
            return test_plan
            
        except Exception as e:
            logger.error(f"Failed to generate AI test plan: {str(e)}")
            # Return fallback test plan
            return self._create_fallback_test_plan(str(e))
    
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
            return {"files_changed": 0, "lines_added": 0, "lines_removed": 0, "has_diff": False}
        
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
    
    def _create_fallback_test_plan(self, error_reason: str) -> Dict[str, Any]:
        """
        Create a fallback test plan when AI generation fails.
        
        Args:
            error_reason: Reason for fallback
            
        Returns:
            Fallback test plan
        """
        return {
            'test_cases': [
                {
                    'id': 'fallback_001',
                    'description': 'Basic application health check',
                    'test_type': 'ui',
                    'target_element': 'body',
                    'action': 'navigate_and_verify',
                    'expected_outcome': 'Application loads successfully',
                    'priority': 'high'
                }
            ],
            'execution_strategy': 'sequential',
            'estimated_duration_minutes': 2,
            'risk_level': 'low',
            'summary': 'Fallback test plan due to AI generation failure',
            'reasoning': f'AI test plan generation failed: {error_reason}',
            'generated_by': 'fallback',
            'agent_model': 'none'
        }
    
    async def _execute_test_plan(self, page: Page, test_plan: Dict[str, Any], repo_path: str) -> Dict[str, Any]:
        """
        Execute AI-generated test plan using Playwright.
        
        Args:
            page: Playwright page instance
            test_plan: AI-generated test plan to execute
            repo_path: Repository path for context
            
        Returns:
            Execution results with individual test case results
        """
        from datetime import datetime, timezone
        
        start_time = datetime.now(timezone.utc)
        logs = []
        test_results = []
        overall_success = True
        
        try:
            test_cases = test_plan.get('test_cases', [])
            logs.append(f"Starting test plan execution: {test_plan.get('summary', 'AI-generated test plan')}")
            logs.append(f"Total test cases: {len(test_cases)}")
            
            for i, test_case in enumerate(test_cases):
                case_num = i + 1
                case_id = test_case.get('id', f'test_{case_num}')
                description = test_case.get('description', 'Unnamed test case')
                
                logs.append(f"\nTest Case {case_num} ({case_id}): {description}")
                
                case_result = await self._execute_test_case(page, test_case, logs)
                test_results.append({
                    'case_id': case_id,
                    'description': description,
                    'success': case_result['success'],
                    'error': case_result.get('error'),
                    'duration_seconds': case_result.get('duration_seconds', 0)
                })
                
                if not case_result['success']:
                    overall_success = False
                    
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            passed_count = sum(1 for result in test_results if result['success'])
            failed_count = len(test_results) - passed_count
            
            summary = f"Test plan {'PASSED' if overall_success else 'FAILED'}: {passed_count}/{len(test_results)} test cases passed in {duration:.2f}s"
            logs.append(f"\n{summary}")
            
            return {
                "success": overall_success,
                "summary": summary,
                "logs": logs,
                "test_results": test_results,
                "timestamp": end_time.isoformat(),
                "duration_seconds": duration,
                "passed_count": passed_count,
                "failed_count": failed_count
            }
            
        except Exception as e:
            logs.append(f"Test plan execution failed: {str(e)}")
            return {
                "success": False,
                "summary": f"Test plan execution failed: {str(e)}",
                "logs": logs,
                "test_results": test_results,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "duration_seconds": 0,
                "passed_count": 0,
                "failed_count": len(test_plan.get('test_cases', []))
            }
    
    async def _execute_test_case(self, page: Page, test_case: Dict[str, Any], logs: List[str]) -> Dict[str, Any]:
        """
        Execute a single test case.
        
        Args:
            page: Playwright page instance
            test_case: Individual test case to execute
            logs: Shared logs list to append to
            
        Returns:
            Test case execution result
        """
        from datetime import datetime, timezone
        
        start_time = datetime.now(timezone.utc)
        
        try:
            test_type = test_case.get('test_type', 'ui')
            action = test_case.get('action', 'unknown')
            target_element = test_case.get('target_element', '')
            expected_outcome = test_case.get('expected_outcome', '')
            
            if action == 'navigate_and_verify':
                # Basic navigation and verification
                await page.goto('http://localhost:3000', timeout=self.browser_timeout)
                logs.append(f"  ✓ Navigated to application")
                
                if target_element:
                    await page.wait_for_selector(target_element, timeout=5000)
                    logs.append(f"  ✓ Found target element: {target_element}")
                
                title = await page.title()
                if title:
                    logs.append(f"  ✓ Page loaded with title: {title}")
                else:
                    logs.append(f"  ⚠ Page loaded but no title found")
                    
            elif action == 'click':
                # Click action
                if target_element:
                    await page.click(target_element, timeout=5000)
                    logs.append(f"  ✓ Clicked element: {target_element}")
                else:
                    raise Exception("Click action requires target_element")
                    
            elif action == 'type':
                # Type action
                if target_element and 'input_text' in test_case:
                    await page.fill(target_element, test_case['input_text'])
                    logs.append(f"  ✓ Typed text into: {target_element}")
                else:
                    raise Exception("Type action requires target_element and input_text")
                    
            elif action == 'verify_text':
                # Text verification
                if target_element and expected_outcome:
                    element_text = await page.text_content(target_element)
                    if expected_outcome.lower() in element_text.lower():
                        logs.append(f"  ✓ Text verification passed: {expected_outcome}")
                    else:
                        raise Exception(f"Text verification failed. Expected: {expected_outcome}, Found: {element_text}")
                else:
                    raise Exception("Verify text action requires target_element and expected_outcome")
                    
            else:
                # Unknown action - log warning but don't fail
                logs.append(f"  ⚠ Unknown action '{action}' - skipping")
            
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            return {
                'success': True,
                'duration_seconds': duration
            }
            
        except Exception as e:
            logs.append(f"  ✗ Test case failed: {str(e)}")
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            
            return {
                'success': False,
                'error': str(e),
                'duration_seconds': duration
            }

    def determine_simulation_result(self, test_results: List[Dict[str, Any]], test_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Determine overall simulation result based on test case results and AI analysis.
        
        Args:
            test_results: List of individual test case results
            test_plan: Original AI-generated test plan
            
        Returns:
            Overall simulation result determination
        """
        if not test_results:
            return {
                'overall_result': 'fail',
                'confidence': 'high',
                'reasoning': 'No test cases were executed',
                'risk_assessment': 'high',
                'recommendation': 'Investigation required - no tests executed'
            }
        
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results if result['success'])
        failed_tests = total_tests - passed_tests
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        # Get risk level from AI test plan
        ai_risk_level = test_plan.get('risk_level', 'medium')
        
        # Determine overall result based on pass rate and AI risk assessment
        if pass_rate == 1.0:
            overall_result = 'pass'
            confidence = 'high'
            reasoning = f'All {total_tests} test cases passed successfully'
            recommendation = 'PR appears safe to merge'
        elif pass_rate >= 0.8:
            overall_result = 'pass' if ai_risk_level == 'low' else 'conditional_pass'
            confidence = 'medium'
            reasoning = f'{passed_tests}/{total_tests} test cases passed ({pass_rate:.1%} pass rate)'
            recommendation = 'PR likely safe, but monitor failed test areas'
        elif pass_rate >= 0.5:
            overall_result = 'conditional_pass' if ai_risk_level == 'low' else 'fail'
            confidence = 'medium'
            reasoning = f'Mixed results: {passed_tests}/{total_tests} test cases passed ({pass_rate:.1%} pass rate)'
            recommendation = 'Review failed tests before merging'
        else:
            overall_result = 'fail'
            confidence = 'high'
            reasoning = f'Majority of tests failed: {failed_tests}/{total_tests} failures ({pass_rate:.1%} pass rate)'
            recommendation = 'PR requires fixes before merging'
        
        # Adjust risk assessment based on AI analysis and results
        if ai_risk_level == 'high' and pass_rate < 1.0:
            risk_assessment = 'high'
        elif ai_risk_level == 'medium' and pass_rate < 0.8:
            risk_assessment = 'medium'
        elif pass_rate >= 0.9:
            risk_assessment = 'low'
        else:
            risk_assessment = 'medium'
        
        return {
            'overall_result': overall_result,
            'confidence': confidence,
            'reasoning': reasoning,
            'risk_assessment': risk_assessment,
            'recommendation': recommendation,
            'pass_rate': pass_rate,
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'ai_risk_level': ai_risk_level
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
