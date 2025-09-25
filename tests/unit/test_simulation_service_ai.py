"""Unit tests for simulation service AI integration."""

import unittest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import asyncio
from datetime import datetime, timezone

from src.services.simulation_service import SimulationService
from models.simulation_job import SimulationJobModel, JobStatus


class TestSimulationServiceAI(unittest.TestCase):
    """Test cases for simulation service AI integration."""
    
    def setUp(self):
        """
        Initialize fixtures used by TestSimulationServiceAI.
        
        Sets up a SimulationService instance, a sample SimulationJobModel (with identifiers, PR URLs/SHAs, and PENDING status), a test repository path, sample diff metadata describing changed and relevant files, and a sample AI-generated UI test plan containing one high-priority test case along with execution strategy, estimated duration, risk level, summary, reasoning, and agent model.
        """
        self.simulation_service = SimulationService()
        self.test_job = SimulationJobModel(
            job_id="test_job_123",
            pr_url="https://github.com/test/repo/pull/1",
            pr_base_sha="abc123",
            pr_head_sha="def456",
            status=JobStatus.PENDING
        )
        self.test_repo_path = "/tmp/test_repo"
        
        self.sample_diff_data = {
            'diff_content': 'diff --git a/src/api/auth.py b/src/api/auth.py\n+new line',
            'changed_files': [
                {'status': 'M', 'filename': 'src/api/auth.py', 'change_type': 'modified'}
            ],
            'relevant_files': [
                {'status': 'M', 'filename': 'src/api/auth.py', 'change_type': 'modified'}
            ],
            'base_branch': 'abc123',
            'target_branch': 'def456',
            'total_files_changed': 1,
            'relevant_files_changed': 1,
            'has_changes': True
        }
        
        self.sample_test_plan = {
            'test_cases': [
                {
                    'id': 'test_001',
                    'description': 'Test authentication endpoint',
                    'test_type': 'ui',
                    'target_element': 'body',
                    'action': 'navigate_and_verify',
                    'expected_outcome': 'Application loads successfully',
                    'priority': 'high'
                }
            ],
            'execution_strategy': 'sequential',
            'estimated_duration_minutes': 5,
            'risk_level': 'medium',
            'summary': 'Test plan for authentication changes',
            'reasoning': 'Authentication code was modified',
            'generated_by': 'ai_agent',
            'agent_model': 'openai:gpt-4o'
        }
    
    @patch('src.services.simulation_service.async_playwright')
    async def test_run_simulation_success(self, mock_playwright):
        """Test successful simulation run with AI integration."""
        # Mock repository service
        self.simulation_service.repository_service.calculate_diff = Mock(
            return_value=self.sample_diff_data
        )
        
        # Mock AI agent service
        self.simulation_service.ai_agent_service.generate_test_plan = AsyncMock(
            return_value=self.sample_test_plan
        )
        
        # Mock Playwright
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser
        
        # Mock page interactions
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.title.return_value = "Test App"
        
        result = await self.simulation_service.run_simulation(self.test_job, self.test_repo_path)
        
        # Verify result structure
        self.assertIn('result', result)
        self.assertIn('summary', result)
        self.assertIn('test_plan', result)
        self.assertIn('test_results', result)
        self.assertIn('result_determination', result)
        
        # Verify services were called
        self.simulation_service.repository_service.calculate_diff.assert_called_once_with(
            repo_path=self.test_repo_path,
            base_branch='abc123',
            target_branch='def456'
        )
        self.simulation_service.ai_agent_service.generate_test_plan.assert_called_once_with(
            self.sample_diff_data
        )
    
    @patch('src.services.simulation_service.async_playwright')
    async def test_run_simulation_ai_failure_fallback(self, mock_playwright):
        """Test simulation with AI failure using fallback test plan."""
        # Mock repository service success
        self.simulation_service.repository_service.calculate_diff = Mock(
            return_value=self.sample_diff_data
        )
        
        # Mock AI agent service failure
        self.simulation_service.ai_agent_service.generate_test_plan = AsyncMock(
            side_effect=Exception("AI service unavailable")
        )
        
        # Mock Playwright
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser
        
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.title.return_value = "Test App"
        
        result = await self.simulation_service.run_simulation(self.test_job, self.test_repo_path)
        
        # Should still complete with fallback test plan
        self.assertIn('result', result)
        self.assertIn('test_plan', result)
        
        # Test plan should be fallback
        test_plan = result['test_plan']
        self.assertEqual(test_plan['generated_by'], 'fallback')
        self.assertIn('AI test plan generation failed', test_plan['reasoning'])
    
    async def test_generate_ai_test_plan_success(self):
        """Test successful AI test plan generation."""
        # Mock repository service
        self.simulation_service.repository_service.calculate_diff = Mock(
            return_value=self.sample_diff_data
        )
        
        # Mock AI agent service
        self.simulation_service.ai_agent_service.generate_test_plan = AsyncMock(
            return_value=self.sample_test_plan
        )
        
        result = await self.simulation_service._generate_ai_test_plan(
            self.test_job, self.test_repo_path
        )
        
        self.assertEqual(result, self.sample_test_plan)
        self.simulation_service.repository_service.calculate_diff.assert_called_once()
        self.simulation_service.ai_agent_service.generate_test_plan.assert_called_once()
    
    async def test_generate_ai_test_plan_failure(self):
        """Test AI test plan generation failure with fallback."""
        # Mock repository service failure
        self.simulation_service.repository_service.calculate_diff = Mock(
            side_effect=Exception("Git diff failed")
        )
        
        result = await self.simulation_service._generate_ai_test_plan(
            self.test_job, self.test_repo_path
        )
        
        # Should return fallback test plan
        self.assertEqual(result['generated_by'], 'fallback')
        self.assertIn('Git diff failed', result['reasoning'])
    
    def test_create_fallback_test_plan(self):
        """Test creation of fallback test plan."""
        error_reason = "AI service unavailable"
        result = self.simulation_service._create_fallback_test_plan(error_reason)
        
        # Verify fallback structure
        self.assertEqual(result['generated_by'], 'fallback')
        self.assertEqual(result['agent_model'], 'none')
        self.assertEqual(len(result['test_cases']), 1)
        self.assertIn(error_reason, result['reasoning'])
        
        # Verify fallback test case
        test_case = result['test_cases'][0]
        self.assertEqual(test_case['id'], 'fallback_001')
        self.assertEqual(test_case['action'], 'navigate_and_verify')
        self.assertEqual(test_case['priority'], 'high')
    
    async def test_execute_test_plan_success(self):
        """Test successful test plan execution."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.title.return_value = "Test Application"
        
        result = await self.simulation_service._execute_test_plan(
            mock_page, self.sample_test_plan, self.test_repo_path
        )
        
        # Verify execution result
        self.assertTrue(result['success'])
        self.assertIn('test_results', result)
        self.assertEqual(len(result['test_results']), 1)
        self.assertEqual(result['passed_count'], 1)
        self.assertEqual(result['failed_count'], 0)
        
        # Verify page interactions
        mock_page.goto.assert_called_once()
        mock_page.wait_for_selector.assert_called_once_with('body', timeout=5000)
    
    async def test_execute_test_plan_mixed_results(self):
        """Test test plan execution with mixed pass/fail results."""
        test_plan_with_failures = {
            'test_cases': [
                {
                    'id': 'test_001',
                    'description': 'Successful test',
                    'test_type': 'ui',
                    'target_element': 'body',
                    'action': 'navigate_and_verify',
                    'expected_outcome': 'Success',
                    'priority': 'high'
                },
                {
                    'id': 'test_002',
                    'description': 'Failing test',
                    'test_type': 'ui',
                    'target_element': '#nonexistent',
                    'action': 'click',
                    'expected_outcome': 'Click succeeds',
                    'priority': 'medium'
                }
            ],
            'execution_strategy': 'sequential',
            'estimated_duration_minutes': 5,
            'risk_level': 'medium',
            'summary': 'Mixed test plan',
            'reasoning': 'Test mixed results'
        }
        
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.title.return_value = "Test App"
        mock_page.click = AsyncMock(side_effect=Exception("Element not found"))
        
        result = await self.simulation_service._execute_test_plan(
            mock_page, test_plan_with_failures, self.test_repo_path
        )
        
        # Should have mixed results
        self.assertFalse(result['success'])  # Overall failure due to one failed test
        self.assertEqual(len(result['test_results']), 2)
        self.assertEqual(result['passed_count'], 1)
        self.assertEqual(result['failed_count'], 1)
        
        # Check individual test results
        test_results = result['test_results']
        self.assertTrue(test_results[0]['success'])  # First test passed
        self.assertFalse(test_results[1]['success'])  # Second test failed
        self.assertIn('error', test_results[1])
    
    async def test_execute_test_case_navigate_and_verify(self):
        """Test execute_test_case with navigate_and_verify action."""
        test_case = {
            'id': 'test_001',
            'description': 'Navigation test',
            'test_type': 'ui',
            'target_element': 'body',
            'action': 'navigate_and_verify',
            'expected_outcome': 'Page loads',
            'priority': 'high'
        }
        
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.title.return_value = "Test Page"
        
        logs = []
        result = await self.simulation_service._execute_test_case(mock_page, test_case, logs)
        
        self.assertTrue(result['success'])
        self.assertIn('duration_seconds', result)
        
        # Verify logs were updated
        self.assertTrue(any('Navigated to application' in log for log in logs))
        self.assertTrue(any('Found target element: body' in log for log in logs))
        self.assertTrue(any('Page loaded with title: Test Page' in log for log in logs))
    
    async def test_execute_test_case_click_action(self):
        """Test execute_test_case with click action."""
        test_case = {
            'id': 'test_002',
            'description': 'Click test',
            'test_type': 'ui',
            'target_element': 'button#submit',
            'action': 'click',
            'expected_outcome': 'Button clicked',
            'priority': 'medium'
        }
        
        mock_page = AsyncMock()
        mock_page.click = AsyncMock()
        
        logs = []
        result = await self.simulation_service._execute_test_case(mock_page, test_case, logs)
        
        self.assertTrue(result['success'])
        mock_page.click.assert_called_once_with('button#submit', timeout=5000)
        self.assertTrue(any('Clicked element: button#submit' in log for log in logs))
    
    async def test_execute_test_case_type_action(self):
        """Test execute_test_case with type action."""
        test_case = {
            'id': 'test_003',
            'description': 'Type test',
            'test_type': 'ui',
            'target_element': 'input#username',
            'action': 'type',
            'input_text': 'testuser',
            'expected_outcome': 'Text entered',
            'priority': 'medium'
        }
        
        mock_page = AsyncMock()
        mock_page.fill = AsyncMock()
        
        logs = []
        result = await self.simulation_service._execute_test_case(mock_page, test_case, logs)
        
        self.assertTrue(result['success'])
        mock_page.fill.assert_called_once_with('input#username', 'testuser')
        self.assertTrue(any('Typed text into: input#username' in log for log in logs))
    
    async def test_execute_test_case_verify_text_action(self):
        """Test execute_test_case with verify_text action."""
        test_case = {
            'id': 'test_004',
            'description': 'Text verification test',
            'test_type': 'ui',
            'target_element': 'h1',
            'action': 'verify_text',
            'expected_outcome': 'Welcome',
            'priority': 'high'
        }
        
        mock_page = AsyncMock()
        mock_page.text_content.return_value = "Welcome to our application"
        
        logs = []
        result = await self.simulation_service._execute_test_case(mock_page, test_case, logs)
        
        self.assertTrue(result['success'])
        mock_page.text_content.assert_called_once_with('h1')
        self.assertTrue(any('Text verification passed: Welcome' in log for log in logs))
    
    async def test_execute_test_case_verify_text_failure(self):
        """Test execute_test_case with verify_text action failure."""
        test_case = {
            'id': 'test_005',
            'description': 'Text verification failure test',
            'test_type': 'ui',
            'target_element': 'h1',
            'action': 'verify_text',
            'expected_outcome': 'Expected Text',
            'priority': 'high'
        }
        
        mock_page = AsyncMock()
        mock_page.text_content.return_value = "Different Text"
        
        logs = []
        result = await self.simulation_service._execute_test_case(mock_page, test_case, logs)
        
        self.assertFalse(result['success'])
        self.assertIn('error', result)
        self.assertTrue(any('Test case failed:' in log for log in logs))
    
    async def test_execute_test_case_unknown_action(self):
        """Test execute_test_case with unknown action."""
        test_case = {
            'id': 'test_006',
            'description': 'Unknown action test',
            'test_type': 'ui',
            'target_element': 'body',
            'action': 'unknown_action',
            'expected_outcome': 'Should skip',
            'priority': 'low'
        }
        
        mock_page = AsyncMock()
        
        logs = []
        result = await self.simulation_service._execute_test_case(mock_page, test_case, logs)
        
        # Should succeed but log warning
        self.assertTrue(result['success'])
        self.assertTrue(any("Unknown action 'unknown_action' - skipping" in log for log in logs))
    
    def test_determine_simulation_result_all_pass(self):
        """Test result determination with all tests passing."""
        test_results = [
            {'case_id': 'test_001', 'success': True, 'error': None},
            {'case_id': 'test_002', 'success': True, 'error': None}
        ]
        
        result = self.simulation_service.determine_simulation_result(
            test_results, self.sample_test_plan
        )
        
        self.assertEqual(result['overall_result'], 'pass')
        self.assertEqual(result['confidence'], 'high')
        self.assertEqual(result['pass_rate'], 1.0)
        self.assertEqual(result['passed_tests'], 2)
        self.assertEqual(result['failed_tests'], 0)
        self.assertIn('All 2 test cases passed', result['reasoning'])
    
    def test_determine_simulation_result_mixed_high_risk(self):
        """Test result determination with mixed results and high risk."""
        test_results = [
            {'case_id': 'test_001', 'success': True, 'error': None},
            {'case_id': 'test_002', 'success': False, 'error': 'Test failed'}
        ]
        
        high_risk_plan = self.sample_test_plan.copy()
        high_risk_plan['risk_level'] = 'high'
        
        result = self.simulation_service.determine_simulation_result(
            test_results, high_risk_plan
        )
        
        self.assertEqual(result['overall_result'], 'fail')
        self.assertEqual(result['pass_rate'], 0.5)
        self.assertEqual(result['risk_assessment'], 'high')
        self.assertEqual(result['ai_risk_level'], 'high')
    
    def test_determine_simulation_result_no_tests(self):
        """Test result determination with no test results."""
        result = self.simulation_service.determine_simulation_result([], self.sample_test_plan)
        
        self.assertEqual(result['overall_result'], 'fail')
        self.assertEqual(result['confidence'], 'high')
        self.assertEqual(result['risk_assessment'], 'high')
        self.assertIn('No test cases were executed', result['reasoning'])
    
    def test_determine_simulation_result_conditional_pass(self):
        """Test result determination with conditional pass scenario."""
        test_results = [
            {'case_id': 'test_001', 'success': True, 'error': None},
            {'case_id': 'test_002', 'success': True, 'error': None},
            {'case_id': 'test_003', 'success': True, 'error': None},
            {'case_id': 'test_004', 'success': False, 'error': 'Minor failure'}
        ]
        
        low_risk_plan = self.sample_test_plan.copy()
        low_risk_plan['risk_level'] = 'low'
        
        result = self.simulation_service.determine_simulation_result(
            test_results, low_risk_plan
        )
        
        # 75% pass rate with low risk should be conditional pass
        self.assertEqual(result['overall_result'], 'conditional_pass')
        self.assertEqual(result['pass_rate'], 0.75)
        self.assertEqual(result['passed_tests'], 3)
        self.assertEqual(result['failed_tests'], 1)


if __name__ == '__main__':
    unittest.main()
