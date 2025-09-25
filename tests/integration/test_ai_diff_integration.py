"""Integration tests for AI agent diff-based test execution."""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import os
import shutil
from pathlib import Path

from src.services.repository_service import RepositoryService
from src.services.ai_agent_service import AIAgentService
from src.services.simulation_service import SimulationService
from models.simulation_job import SimulationJobModel, JobStatus


class TestAIDiffIntegration(unittest.TestCase):
    """Integration tests for AI diff-based test execution workflow."""
    
    def setUp(self):
        """
        Prepare integration test fixtures and initial state for each test.
        
        Creates a temporary directory and a minimal Git repository, instantiates RepositoryService, AIAgentService, and SimulationService, and constructs a SimulationJobModel representing a pending pull-request job.
        
        Attributes:
            temp_dir (str): Path to the temporary directory for the test repository.
            test_repo_path (str): Path to the created test Git repository.
            repo_service (RepositoryService): Repository service instance used to calculate diffs.
            ai_service (AIAgentService): AI agent service instance used to generate test plans.
            simulation_service (SimulationService): Simulation service instance used to run simulations.
            test_job (SimulationJobModel): Preconfigured simulation job model with PR metadata and pending status.
        """
        self.temp_dir = tempfile.mkdtemp()
        self.test_repo_path = os.path.join(self.temp_dir, "test_repo")
        os.makedirs(self.test_repo_path)
        
        # Create test git repository structure
        self._create_test_git_repo()
        
        self.repo_service = RepositoryService()
        self.ai_service = AIAgentService()
        self.simulation_service = SimulationService()
        
        self.test_job = SimulationJobModel(
            job_id="integration_test_123",
            pr_url="https://github.com/test/repo/pull/1",
            pr_base_sha="main",
            pr_head_sha="feature-branch",
            status=JobStatus.PENDING
        )
    
    def tearDown(self):
        """
        Remove the temporary directory created for the test and its contents.
        
        This deletes the filesystem directory used during setUp for repository and file fixtures. Any errors raised while removing the directory are ignored.
        """
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_git_repo(self):
        """
        Set up a temporary Git repository at self.test_repo_path with an initial commit and a feature branch containing simple code changes.
        
        Creates a repository, configures a test user, adds initial project files (src/api/auth.py and README.md) and commits them to a created `main` branch. Then creates a `feature-branch` that updates src/api/auth.py and adds src/api/new_service.py, commits those changes, and checks out `main`.
        """
        # Initialize git repo
        os.system(f"cd {self.test_repo_path} && git init")
        os.system(f"cd {self.test_repo_path} && git config user.email 'test@example.com'")
        os.system(f"cd {self.test_repo_path} && git config user.name 'Test User'")
        
        # Create initial files
        src_dir = os.path.join(self.test_repo_path, "src", "api")
        os.makedirs(src_dir, exist_ok=True)
        
        with open(os.path.join(src_dir, "auth.py"), "w") as f:
            f.write("def authenticate(user):\n    return True\n")
        
        with open(os.path.join(self.test_repo_path, "README.md"), "w") as f:
            f.write("# Test Repository\n")
        
        # Initial commit
        os.system(f"cd {self.test_repo_path} && git add .")
        os.system(f"cd {self.test_repo_path} && git commit -m 'Initial commit'")
        os.system(f"cd {self.test_repo_path} && git branch main")
        
        # Create feature branch with changes
        os.system(f"cd {self.test_repo_path} && git checkout -b feature-branch")
        
        # Modify auth.py
        with open(os.path.join(src_dir, "auth.py"), "w") as f:
            f.write("def authenticate(user):\n    # Added validation\n    if not user:\n        return False\n    return True\n")
        
        # Add new service file
        with open(os.path.join(src_dir, "new_service.py"), "w") as f:
            f.write("def new_function():\n    return 'new feature'\n")
        
        os.system(f"cd {self.test_repo_path} && git add .")
        os.system(f"cd {self.test_repo_path} && git commit -m 'Add authentication validation'")
        
        # Switch back to main
        os.system(f"cd {self.test_repo_path} && git checkout main")
    
    @patch('subprocess.run')
    def test_repository_diff_calculation_integration(self, mock_run):
        """Test repository service diff calculation with real-like data."""
        # Mock git diff --name-status
        mock_name_status = Mock()
        mock_name_status.returncode = 0
        mock_name_status.stdout = "M\tsrc/api/auth.py\nA\tsrc/api/new_service.py"
        
        # Mock git diff full content
        mock_full_diff = Mock()
        mock_full_diff.returncode = 0
        mock_full_diff.stdout = """diff --git a/src/api/auth.py b/src/api/auth.py
index abc123..def456 100644
--- a/src/api/auth.py
+++ b/src/api/auth.py
@@ -1,2 +1,5 @@
 def authenticate(user):
+    # Added validation
+    if not user:
+        return False
     return True"""
        
        mock_run.side_effect = [mock_name_status, mock_full_diff]
        
        diff_data = self.repo_service.calculate_diff(
            self.test_repo_path, "main", "feature-branch"
        )
        
        # Verify diff data structure
        self.assertTrue(diff_data['has_changes'])
        self.assertEqual(len(diff_data['changed_files']), 2)
        self.assertEqual(len(diff_data['relevant_files']), 2)
        
        # Verify file details
        changed_files = {f['filename']: f for f in diff_data['changed_files']}
        self.assertIn('src/api/auth.py', changed_files)
        self.assertIn('src/api/new_service.py', changed_files)
        self.assertEqual(changed_files['src/api/auth.py']['change_type'], 'modified')
        self.assertEqual(changed_files['src/api/new_service.py']['change_type'], 'added')
    
    @patch('src.services.ai_agent_service.diff_agent')
    async def test_ai_agent_test_plan_generation_integration(self, mock_agent):
        """Test AI agent service integration with repository diff data."""
        # Sample diff data from repository service
        diff_data = {
            'diff_content': 'diff --git a/src/api/auth.py b/src/api/auth.py\n+validation added',
            'changed_files': [
                {'status': 'M', 'filename': 'src/api/auth.py', 'change_type': 'modified'},
                {'status': 'A', 'filename': 'src/api/new_service.py', 'change_type': 'added'}
            ],
            'relevant_files': [
                {'status': 'M', 'filename': 'src/api/auth.py', 'change_type': 'modified'},
                {'status': 'A', 'filename': 'src/api/new_service.py', 'change_type': 'added'}
            ],
            'base_branch': 'main',
            'target_branch': 'feature-branch',
            'total_files_changed': 2,
            'relevant_files_changed': 2,
            'has_changes': True
        }
        
        # Mock AI agent response
        from src.services.ai_agent_service import TestPlan, TestCase
        mock_result = Mock()
        mock_result.output = TestPlan(**{
            'test_cases': [
                TestCase(**{
                    'id': 'auth_test_001',
                    'description': 'Test authentication with null user',
                    'test_type': 'api',
                    'target_element': '/api/auth',
                    'action': 'post_request',
                    'expected_outcome': 'Returns 400 for null user',
                    'priority': 'high'
                }),
                TestCase(**{
                    'id': 'auth_test_002',
                    'description': 'Test authentication with valid user',
                    'test_type': 'api',
                    'target_element': '/api/auth',
                    'action': 'post_request',
                    'expected_outcome': 'Returns 200 for valid user',
                    'priority': 'high'
                }),
                TestCase(**{
                    'id': 'service_test_001',
                    'description': 'Test new service endpoint',
                    'test_type': 'api',
                    'target_element': '/api/new_service',
                    'action': 'get_request',
                    'expected_outcome': 'Returns new feature response',
                    'priority': 'medium'
                })
            ],
            'execution_strategy': 'sequential',
            'estimated_duration_minutes': 8,
            'risk_level': 'medium',
            'summary': 'Test plan for authentication and new service changes',
            'reasoning': 'Authentication logic was modified and new service was added'
        })
        
        mock_agent.run = AsyncMock(return_value=mock_result)
        
        test_plan = await self.ai_service.generate_test_plan(diff_data)
        
        # Verify test plan structure
        self.assertEqual(len(test_plan['test_cases']), 3)
        self.assertEqual(test_plan['risk_level'], 'medium')
        self.assertEqual(test_plan['execution_strategy'], 'sequential')
        
        # Verify test cases focus on changed areas
        test_case_descriptions = [tc['description'] for tc in test_plan['test_cases']]
        self.assertTrue(any('authentication' in desc.lower() for desc in test_case_descriptions))
        self.assertTrue(any('new service' in desc.lower() for desc in test_case_descriptions))
        
        # Verify AI agent was called with correct data
        mock_agent.run.assert_called_once()
        call_args = mock_agent.run.call_args
        self.assertIn('authentication', call_args[0][0].lower())
        self.assertIn('new service', call_args[0][0].lower())
    
    @patch('src.services.simulation_service.async_playwright')
    async def test_full_simulation_workflow_integration(self, mock_playwright):
        """Test complete simulation workflow from diff to result determination."""
        # Mock repository service
        diff_data = {
            'diff_content': 'test diff content',
            'changed_files': [
                {'status': 'M', 'filename': 'src/api/auth.py', 'change_type': 'modified'}
            ],
            'relevant_files': [
                {'status': 'M', 'filename': 'src/api/auth.py', 'change_type': 'modified'}
            ],
            'base_branch': 'main',
            'target_branch': 'feature-branch',
            'total_files_changed': 1,
            'relevant_files_changed': 1,
            'has_changes': True
        }
        
        self.simulation_service.repository_service.calculate_diff = Mock(
            return_value=diff_data
        )
        
        # Mock AI agent service
        test_plan = {
            'test_cases': [
                {
                    'id': 'integration_test_001',
                    'description': 'Test authentication flow',
                    'test_type': 'ui',
                    'target_element': 'body',
                    'action': 'navigate_and_verify',
                    'expected_outcome': 'Application loads',
                    'priority': 'high'
                },
                {
                    'id': 'integration_test_002',
                    'description': 'Test login form',
                    'test_type': 'ui',
                    'target_element': '#login-form',
                    'action': 'verify_text',
                    'expected_outcome': 'Login',
                    'priority': 'medium'
                }
            ],
            'execution_strategy': 'sequential',
            'estimated_duration_minutes': 5,
            'risk_level': 'medium',
            'summary': 'Integration test plan',
            'reasoning': 'Authentication changes detected',
            'generated_by': 'ai_agent',
            'agent_model': 'openai:gpt-4o'
        }
        
        self.simulation_service.ai_agent_service.generate_test_plan = AsyncMock(
            return_value=test_plan
        )
        
        # Mock Playwright
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser
        
        # Mock successful page interactions
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.title.return_value = "Test Application"
        mock_page.text_content.return_value = "Login Form"
        
        # Run full simulation
        result = await self.simulation_service.run_simulation(self.test_job, self.test_repo_path)
        
        # Verify complete workflow
        self.assertIn('result', result)
        self.assertIn('test_plan', result)
        self.assertIn('test_results', result)
        self.assertIn('result_determination', result)
        
        # Verify services were integrated correctly
        self.simulation_service.repository_service.calculate_diff.assert_called_once()
        self.simulation_service.ai_agent_service.generate_test_plan.assert_called_once_with(diff_data)
        
        # Verify test execution
        self.assertEqual(len(result['test_results']), 2)
        
        # Verify result determination
        result_determination = result['result_determination']
        self.assertIn('overall_result', result_determination)
        self.assertIn('confidence', result_determination)
        self.assertIn('risk_assessment', result_determination)
        self.assertIn('recommendation', result_determination)
    
    @patch('src.services.simulation_service.async_playwright')
    async def test_error_handling_integration(self, mock_playwright):
        """Test error handling across the integrated workflow."""
        # Mock repository service failure
        self.simulation_service.repository_service.calculate_diff = Mock(
            side_effect=Exception("Git repository not found")
        )
        
        # Mock Playwright for fallback execution
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value = mock_browser
        
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.title.return_value = "Fallback Test"
        
        # Run simulation with error
        result = await self.simulation_service.run_simulation(self.test_job, self.test_repo_path)
        
        # Should complete with fallback test plan
        self.assertIn('result', result)
        self.assertIn('test_plan', result)
        
        # Verify fallback was used
        test_plan = result['test_plan']
        self.assertEqual(test_plan['generated_by'], 'fallback')
        self.assertIn('Git repository not found', test_plan['reasoning'])
        
        # Should still have result determination
        self.assertIn('result_determination', result)
    
    def test_validate_test_plan_integration(self):
        """Test test plan validation integration."""
        # Valid test plan
        valid_plan = {
            'test_cases': [
                {
                    'id': 'valid_001',
                    'description': 'Valid test case',
                    'test_type': 'ui',
                    'target_element': 'body',
                    'action': 'click',
                    'expected_outcome': 'Success',
                    'priority': 'high'
                }
            ],
            'execution_strategy': 'sequential',
            'estimated_duration_minutes': 3,
            'risk_level': 'low',
            'summary': 'Valid test plan',
            'reasoning': 'Test validation'
        }
        
        self.assertTrue(self.ai_service.validate_test_plan(valid_plan))
        
        # Invalid test plan (missing required field)
        invalid_plan = valid_plan.copy()
        del invalid_plan['execution_strategy']
        
        self.assertFalse(self.ai_service.validate_test_plan(invalid_plan))
    
    def test_result_determination_integration(self):
        """Test result determination logic integration."""
        # Test various scenarios
        scenarios = [
            {
                'name': 'all_pass_low_risk',
                'test_results': [
                    {'case_id': 'test_001', 'success': True, 'error': None},
                    {'case_id': 'test_002', 'success': True, 'error': None}
                ],
                'risk_level': 'low',
                'expected_result': 'pass'
            },
            {
                'name': 'mixed_high_risk',
                'test_results': [
                    {'case_id': 'test_001', 'success': True, 'error': None},
                    {'case_id': 'test_002', 'success': False, 'error': 'Failed'}
                ],
                'risk_level': 'high',
                'expected_result': 'fail'
            },
            {
                'name': 'mostly_pass_medium_risk',
                'test_results': [
                    {'case_id': 'test_001', 'success': True, 'error': None},
                    {'case_id': 'test_002', 'success': True, 'error': None},
                    {'case_id': 'test_003', 'success': True, 'error': None},
                    {'case_id': 'test_004', 'success': False, 'error': 'Minor issue'}
                ],
                'risk_level': 'medium',
                'expected_result': 'conditional_pass'
            }
        ]
        
        for scenario in scenarios:
            test_plan = {'risk_level': scenario['risk_level']}
            result = self.simulation_service.determine_simulation_result(
                scenario['test_results'], test_plan
            )
            
            self.assertEqual(
                result['overall_result'], 
                scenario['expected_result'],
                f"Scenario {scenario['name']} failed"
            )


class TestAIDiffIntegrationAsync(unittest.IsolatedAsyncioTestCase):
    """Async integration tests for AI diff workflow."""
    
    async def test_async_workflow_integration(self):
        """
        Verify that the AI agent produces an appropriate test plan for an async code change.
        
        Creates mock diff data representing an asynchronous change, patches the AI agent to return a single test case with a `parallel` execution strategy, and asserts the generated test plan contains one test case, uses the `parallel` strategy, and that the test case description references "async".
        """
        repo_service = RepositoryService()
        ai_service = AIAgentService()
        
        # Mock diff data
        diff_data = {
            'diff_content': 'async test diff',
            'changed_files': [
                {'status': 'M', 'filename': 'src/async_service.py', 'change_type': 'modified'}
            ],
            'relevant_files': [
                {'status': 'M', 'filename': 'src/async_service.py', 'change_type': 'modified'}
            ],
            'base_branch': 'main',
            'target_branch': 'async-feature',
            'total_files_changed': 1,
            'relevant_files_changed': 1,
            'has_changes': True
        }
        
        # Test async AI agent call
        with patch('src.services.ai_agent_service.diff_agent') as mock_agent:
            from src.services.ai_agent_service import TestPlan, TestCase
            mock_result = Mock()
            mock_result.output = TestPlan(**{
                'test_cases': [TestCase(**{
                    'id': 'async_test_001',
                    'description': 'Test async functionality',
                    'test_type': 'api',
                    'target_element': '/api/async',
                    'action': 'async_request',
                    'expected_outcome': 'Async response received',
                    'priority': 'high'
                })],
                'execution_strategy': 'parallel',
                'estimated_duration_minutes': 3,
                'risk_level': 'low',
                'summary': 'Async test plan',
                'reasoning': 'Async service modified'
            })
            
            mock_agent.run = AsyncMock(return_value=mock_result)
            
            test_plan = await ai_service.generate_test_plan(diff_data)
            
            self.assertEqual(len(test_plan['test_cases']), 1)
            self.assertEqual(test_plan['execution_strategy'], 'parallel')
            self.assertIn('async', test_plan['test_cases'][0]['description'].lower())


if __name__ == '__main__':
    unittest.main()
