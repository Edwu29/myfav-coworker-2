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
        """
        Create and configure a SimulationService instance.
        
        Initializes runtime configuration from environment variables and constructs required service clients.
        Environment variables read:
          - SIMULATION_BROWSER_TIMEOUT: browser timeout in milliseconds (default 30000).
          - SIMULATION_SCRIPT_TIMEOUT: script timeout in milliseconds (default 300000).
          - SIMULATION_HEADLESS: "true" or "false" to control headless browser mode (default "true").
        
        Also instantiates:
          - repository_service: RepositoryService for repository/diff operations.
          - ai_agent_service: AIAgentService for AI-driven test plan generation.
        """
        self.browser_timeout = int(os.getenv('SIMULATION_BROWSER_TIMEOUT', '30000'))  # 30 seconds
        self.script_timeout = int(os.getenv('SIMULATION_SCRIPT_TIMEOUT', '300000'))  # 5 minutes
        self.headless = os.getenv('SIMULATION_HEADLESS', 'true').lower() == 'true'
        self.repository_service = RepositoryService()
        self.ai_agent_service = AIAgentService()
        
    async def run_simulation(self, job: SimulationJobModel, repo_path: str) -> Dict[str, Any]:
        """
        Run a browser-based simulation for a pull request using an AI-generated test plan.
        
        Generates a test plan from the PR diff, executes the plan in a headless Chromium browser, analyzes per-test outcomes to determine an overall result, and returns a consolidated simulation report.
        
        Parameters:
            job (SimulationJobModel): Simulation job containing PR details (e.g., base/head branches or SHAs and job_id).
            repo_path (str): Filesystem path to the local repository clone for the PR.
        
        Returns:
            Dict[str, Any]: A report dictionary with the following keys:
                - result (str): Overall simulation outcome (e.g., "pass", "fail", "conditional_pass").
                - summary (str): Human-readable summary of the execution.
                - execution_logs (List[str]): Collected logs from test execution.
                - test_plan (Dict[str, Any] | None): AI-generated test plan used for execution, or None on failure.
                - timestamp (str | None): ISO timestamp of execution start/completion, or None on failure.
                - test_results (List[Dict[str, Any]]): Per-test-case results produced during execution.
                - result_determination (Dict[str, Any]): Detailed determination including confidence, reasoning, risk assessment, and recommendations.
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
        Generate an AI-powered test plan for a pull request by analyzing the repository diff.
        
        Parameters:
            job (SimulationJobModel): Simulation job containing PR details (e.g., base/head SHAs and pr_url).
            repo_path (str): Filesystem path to the repository checkout to diff.
        
        Returns:
            Dict[str, Any]: A dictionary representing the test plan (including keys such as `test_cases` and metadata) to be executed by the simulation. If AI generation fails, returns a deterministic fallback test plan containing `generated_by: 'fallback'` and a `reason` explaining the failure.
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
        """
        Retrieve the git diff between two commits or refs for the repository at repo_path.
        
        Returns:
            diff_output (str): Unified git diff text for `base_sha..head_sha`. Returns an empty string if the git command fails, times out, or an error occurs.
        """
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
        """
        Produce a compact summary of a git diff output.
        
        Parameters:
            diff_output (str): Raw git diff text (as produced by `git diff`). May be empty.
        
        Returns:
            Dict[str, Any]: Summary with keys:
                - files_changed (int): Number of files modified (lines starting with 'diff --git').
                - lines_added (int): Count of lines starting with '+'.
                - lines_removed (int): Count of lines starting with '-'.
                - has_diff (bool): True if `diff_output` contains any non-whitespace content, False otherwise.
        """
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
        Return a deterministic fallback test plan used when AI test plan generation fails.
        
        The returned plan contains a single high-priority UI test case performing a basic application health check, an execution strategy, estimated duration, risk level, and metadata that records the fallback reason and generation source.
        
        Parameters:
            error_reason (str): Human-readable reason why AI generation failed; incorporated into the plan's `reasoning` field.
        
        Returns:
            Dict[str, Any]: A fallback test plan dictionary with keys including `test_cases`, `execution_strategy`, `estimated_duration_minutes`,
            `risk_level`, `summary`, `reasoning`, `generated_by`, and `agent_model`.
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
        Execute an AI-generated test plan in the provided Playwright page and aggregate per-case results.
        
        Parameters:
            page (Page): Playwright page instance used to run browser interactions.
            test_plan (Dict[str, Any]): Test plan containing a `test_cases` list and optional `summary` metadata.
            repo_path (str): Path to the repository used as contextual reference for tests.
        
        Returns:
            Dict[str, Any]: Aggregated execution result containing:
                - success (bool): `True` if all test cases passed, `False` otherwise.
                - summary (str): Human-readable summary of the execution outcome.
                - logs (List[str]): Ordered log entries produced during execution.
                - test_results (List[Dict[str, Any]]): Per-test-case results with keys `case_id`, `description`, `success`, `error` (optional), and `duration_seconds`.
                - timestamp (str): ISO-8601 timestamp when execution finished.
                - duration_seconds (float): Total execution duration in seconds.
                - passed_count (int): Number of passing test cases.
                - failed_count (int): Number of failing test cases.
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
        Execute a single test case defined by the test plan against the given Playwright page.
        
        The test_case dictionary must include an 'action' key indicating the operation to perform. Supported actions:
        - "navigate_and_verify": navigates to http://localhost:3000, optionally waits for `target_element`, and records the page title.
        - "click": clicks `target_element`.
        - "type": fills `target_element` with `input_text`.
        - "verify_text": checks that `expected_outcome` appears in the text content of `target_element`.
        Unknown actions are logged and skipped without causing a failure.
        
        Parameters:
            page (Page): Playwright page used to perform browser interactions.
            test_case (Dict[str, Any]): Test case specification. Common keys:
                - action (str): one of "navigate_and_verify", "click", "type", "verify_text".
                - target_element (str): selector for the target DOM element (when applicable).
                - input_text (str): text to type for "type" actions.
                - expected_outcome (str): text expected for "verify_text" actions.
            logs (List[str]): Mutable list to append human-readable execution logs.
        
        Returns:
            Dict[str, Any]: Result object with:
                - 'success' (bool): `true` when the action completed and checks passed, `false` otherwise.
                - 'duration_seconds' (float): elapsed time for the test case.
                - 'error' (str, optional): error message when 'success' is `false`.
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
        Assess overall simulation outcome from per-test results and the AI-provided test plan.
        
        Evaluates pass rate, incorporates the test plan's risk_level, and produces a summary decision with confidence, reasoning, risk assessment, and actionable recommendation.
        
        Parameters:
            test_results: List of per-test dictionaries; each entry must include a boolean `success` key indicating whether the test case passed.
            test_plan: AI-generated test plan dictionary; may include `risk_level` (expected values: "low", "medium", "high") used to bias the risk assessment.
        
        Returns:
            A dictionary with these keys:
            - overall_result: One of "pass", "conditional_pass", or "fail" describing the high-level outcome.
            - confidence: Confidence level for the determination ("low", "medium", or "high").
            - reasoning: Human-readable explanation of the decision and observed pass rate.
            - risk_assessment: Assessed risk to the codebase ("low", "medium", or "high").
            - recommendation: Suggested next step (e.g., merge, review, fix).
            - pass_rate: Fraction of tests that passed (0.0–1.0).
            - total_tests: Total number of executed tests.
            - passed_tests: Number of tests that passed.
            - failed_tests: Number of tests that failed.
            - ai_risk_level: The `risk_level` value taken from the provided test plan (defaults to "medium" if absent).
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
        """
        Check whether the runtime environment has the Playwright dependency available.
        
        Returns:
            True if Playwright is available, False otherwise.
        """
        try:
            # Check if Playwright is available
            import playwright
            logger.info("Playwright is available")
            return True
        except ImportError:
            logger.error("Playwright is not installed")
            return False
