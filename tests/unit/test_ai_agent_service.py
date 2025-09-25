"""Unit tests for AI agent service."""

import unittest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from src.services.ai_agent_service import (
    AIAgentService, DiffData, TestPlan, TestCase, AIAgentError,
    _matches_file_type
)


class TestAIAgentService(unittest.TestCase):
    """Test cases for AI agent service."""
    
    def setUp(self):
        """
        Initialize common test fixtures and sample data used by the test cases.
        
        Creates:
        - self.ai_service: an AIAgentService instance used to exercise service methods.
        - self.sample_diff_data: a dict representing a repository diff and metadata with keys such as
          'diff_content', 'changed_files', 'relevant_files', 'base_branch', 'target_branch',
          'total_files_changed', 'relevant_files_changed', and 'has_changes'.
        - self.sample_test_plan: a dict representing a generated test plan containing 'test_cases'
          (list of test case dicts including 'id', 'description', 'test_type', 'target_element',
          'action', 'expected_outcome', and 'priority'), plus plan-level metadata
          ('execution_strategy', 'estimated_duration_minutes', 'risk_level', 'summary',
          'reasoning', 'generated_by', 'agent_model').
        """
        self.ai_service = AIAgentService()
        self.sample_diff_data = {
            'diff_content': 'diff --git a/src/api/auth.py b/src/api/auth.py\n+new line',
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
        
        self.sample_test_plan = {
            'test_cases': [
                {
                    'id': 'test_001',
                    'description': 'Test authentication endpoint',
                    'test_type': 'api',
                    'target_element': '/api/auth',
                    'action': 'post_request',
                    'expected_outcome': 'Returns 200 status',
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
    
    def test_diff_data_model_validation(self):
        """Test DiffData Pydantic model validation."""
        # Valid data should work
        diff_data = DiffData(**self.sample_diff_data)
        self.assertEqual(diff_data.base_branch, 'main')
        self.assertEqual(diff_data.target_branch, 'feature-branch')
        self.assertTrue(diff_data.has_changes)
        
        # Invalid data should raise validation error
        invalid_data = self.sample_diff_data.copy()
        del invalid_data['base_branch']
        
        with self.assertRaises(Exception):  # Pydantic validation error
            DiffData(**invalid_data)
    
    def test_test_case_model_validation(self):
        """Test TestCase Pydantic model validation."""
        test_case_data = {
            'id': 'test_001',
            'description': 'Test case description',
            'test_type': 'ui',
            'target_element': 'button#submit',
            'action': 'click',
            'expected_outcome': 'Form submits successfully',
            'priority': 'high'
        }
        
        test_case = TestCase(**test_case_data)
        self.assertEqual(test_case.id, 'test_001')
        self.assertEqual(test_case.test_type, 'ui')
        self.assertEqual(test_case.priority, 'high')
    
    def test_test_plan_model_validation(self):
        """Test TestPlan Pydantic model validation."""
        test_cases = [TestCase(**{
            'id': 'test_001',
            'description': 'Test case',
            'test_type': 'ui',
            'target_element': 'body',
            'action': 'click',
            'expected_outcome': 'Success',
            'priority': 'medium'
        })]
        
        test_plan_data = {
            'test_cases': test_cases,
            'execution_strategy': 'parallel',
            'estimated_duration_minutes': 10,
            'risk_level': 'low',
            'summary': 'Test plan summary',
            'reasoning': 'Test reasoning'
        }
        
        test_plan = TestPlan(**test_plan_data)
        self.assertEqual(len(test_plan.test_cases), 1)
        self.assertEqual(test_plan.execution_strategy, 'parallel')
        self.assertEqual(test_plan.risk_level, 'low')
    
    @patch('src.services.ai_agent_service.diff_agent')
    async def test_generate_test_plan_success(self, mock_agent):
        """Test successful test plan generation."""
        # Mock AI agent response
        mock_result = Mock()
        mock_result.output = TestPlan(**{
            'test_cases': [TestCase(**{
                'id': 'test_001',
                'description': 'Test authentication',
                'test_type': 'api',
                'target_element': '/api/auth',
                'action': 'post_request',
                'expected_outcome': 'Returns 200',
                'priority': 'high'
            })],
            'execution_strategy': 'sequential',
            'estimated_duration_minutes': 5,
            'risk_level': 'medium',
            'summary': 'Auth test plan',
            'reasoning': 'Auth code changed'
        })
        
        mock_agent.run = AsyncMock(return_value=mock_result)
        
        result = await self.ai_service.generate_test_plan(self.sample_diff_data)
        
        # Verify result structure
        self.assertIn('test_cases', result)
        self.assertIn('execution_strategy', result)
        self.assertIn('generated_by', result)
        self.assertEqual(result['generated_by'], 'ai_agent')
        self.assertEqual(len(result['test_cases']), 1)
        
        # Verify AI agent was called
        mock_agent.run.assert_called_once()
    
    @patch('src.services.ai_agent_service.diff_agent')
    def test_generate_test_plan_sync_success(self, mock_agent):
        """Test successful synchronous test plan generation."""
        # Mock AI agent response
        mock_result = Mock()
        mock_result.output = TestPlan(**{
            'test_cases': [TestCase(**{
                'id': 'test_001',
                'description': 'Test sync',
                'test_type': 'ui',
                'target_element': 'body',
                'action': 'click',
                'expected_outcome': 'Success',
                'priority': 'medium'
            })],
            'execution_strategy': 'sequential',
            'estimated_duration_minutes': 3,
            'risk_level': 'low',
            'summary': 'Sync test plan',
            'reasoning': 'Sync test'
        })
        
        mock_agent.run_sync = Mock(return_value=mock_result)
        
        result = self.ai_service.generate_test_plan_sync(self.sample_diff_data)
        
        # Verify result
        self.assertIn('test_cases', result)
        self.assertEqual(result['generated_by'], 'ai_agent')
        
        # Verify sync method was called
        mock_agent.run_sync.assert_called_once()
    
    async def test_generate_test_plan_no_changes(self):
        """Test test plan generation with no changes."""
        no_changes_data = self.sample_diff_data.copy()
        no_changes_data['has_changes'] = False
        
        result = await self.ai_service.generate_test_plan(no_changes_data)
        
        # Should return empty test plan
        self.assertEqual(len(result['test_cases']), 0)
        self.assertEqual(result['execution_strategy'], 'skip')
        self.assertEqual(result['risk_level'], 'low')
        self.assertIn('No code changes detected', result['summary'])
    
    def test_generate_test_plan_sync_no_changes(self):
        """Test synchronous test plan generation with no changes."""
        no_changes_data = self.sample_diff_data.copy()
        no_changes_data['has_changes'] = False
        
        result = self.ai_service.generate_test_plan_sync(no_changes_data)
        
        # Should return empty test plan
        self.assertEqual(len(result['test_cases']), 0)
        self.assertEqual(result['execution_strategy'], 'skip')
    
    @patch('src.services.ai_agent_service.diff_agent')
    async def test_generate_test_plan_ai_failure(self, mock_agent):
        """Test test plan generation when AI agent fails."""
        mock_agent.run = AsyncMock(side_effect=Exception("AI service unavailable"))
        
        with self.assertRaises(AIAgentError) as context:
            await self.ai_service.generate_test_plan(self.sample_diff_data)
        
        self.assertIn("Test plan generation failed", str(context.exception))
    
    @patch('src.services.ai_agent_service.diff_agent')
    def test_generate_test_plan_sync_ai_failure(self, mock_agent):
        """Test synchronous test plan generation when AI agent fails."""
        mock_agent.run_sync = Mock(side_effect=Exception("AI service unavailable"))
        
        with self.assertRaises(AIAgentError) as context:
            self.ai_service.generate_test_plan_sync(self.sample_diff_data)
        
        self.assertIn("Test plan generation failed", str(context.exception))
    
    def test_create_empty_test_plan(self):
        """Test creation of empty test plan."""
        reason = "No changes detected"
        result = self.ai_service._create_empty_test_plan(reason)
        
        self.assertEqual(len(result['test_cases']), 0)
        self.assertEqual(result['execution_strategy'], 'skip')
        self.assertEqual(result['estimated_duration_minutes'], 0)
        self.assertEqual(result['risk_level'], 'low')
        self.assertIn(reason, result['summary'])
        self.assertEqual(result['reasoning'], reason)
    
    def test_validate_test_plan_valid(self):
        """Test validation of valid test plan."""
        result = self.ai_service.validate_test_plan(self.sample_test_plan)
        self.assertTrue(result)
    
    def test_validate_test_plan_missing_fields(self):
        """Test validation of test plan with missing required fields."""
        invalid_plan = self.sample_test_plan.copy()
        del invalid_plan['execution_strategy']
        
        result = self.ai_service.validate_test_plan(invalid_plan)
        self.assertFalse(result)
    
    def test_validate_test_plan_invalid_test_cases(self):
        """Test validation of test plan with invalid test cases."""
        invalid_plan = self.sample_test_plan.copy()
        invalid_plan['test_cases'] = "not a list"
        
        result = self.ai_service.validate_test_plan(invalid_plan)
        self.assertFalse(result)
    
    def test_validate_test_plan_missing_test_case_fields(self):
        """
        Checks that validate_test_plan rejects a plan whose test cases lack required fields.
        
        Constructs a test plan containing a single incomplete test case (missing required fields)
        and asserts that validate_test_plan returns a falsy value.
        """
        invalid_plan = self.sample_test_plan.copy()
        invalid_plan['test_cases'] = [
            {
                'id': 'test_001',
                'description': 'Test case',
                # Missing required fields
            }
        ]
        
        result = self.ai_service.validate_test_plan(invalid_plan)
        self.assertFalse(result)
    
    def test_matches_file_type_python(self):
        """Test file type matching for Python files."""
        self.assertTrue(_matches_file_type('src/api/auth.py', 'python'))
        self.assertTrue(_matches_file_type('tests/test_auth.py', 'python'))
        self.assertFalse(_matches_file_type('src/api/auth.js', 'python'))
    
    def test_matches_file_type_javascript(self):
        """Test file type matching for JavaScript files."""
        self.assertTrue(_matches_file_type('src/component.js', 'javascript'))
        self.assertTrue(_matches_file_type('src/component.ts', 'javascript'))
        self.assertTrue(_matches_file_type('src/component.jsx', 'javascript'))
        self.assertTrue(_matches_file_type('src/component.tsx', 'javascript'))
        self.assertFalse(_matches_file_type('src/component.py', 'javascript'))
    
    def test_matches_file_type_api(self):
        """Test file type matching for API files."""
        self.assertTrue(_matches_file_type('src/api/auth.py', 'api'))
        self.assertTrue(_matches_file_type('src/api/auth.js', 'api'))
        self.assertTrue(_matches_file_type('src/api/auth.ts', 'api'))
        self.assertFalse(_matches_file_type('src/api/auth.css', 'api'))
    
    def test_matches_file_type_config(self):
        """Test file type matching for config files."""
        self.assertTrue(_matches_file_type('config.json', 'config'))
        self.assertTrue(_matches_file_type('settings.yaml', 'config'))
        self.assertTrue(_matches_file_type('app.toml', 'config'))
        self.assertTrue(_matches_file_type('.env', 'config'))
        self.assertFalse(_matches_file_type('src/app.py', 'config'))
    
    def test_matches_file_type_unknown(self):
        """Test file type matching for unknown file types."""
        self.assertFalse(_matches_file_type('test.py', 'unknown_type'))


class TestAIAgentServiceAsync(unittest.IsolatedAsyncioTestCase):
    """Async test cases for AI agent service."""
    
    async def test_analyze_file_changes_tool(self):
        """Test the analyze_file_changes tool function."""
        from src.services.ai_agent_service import analyze_file_changes
        from pydantic_ai import RunContext
        
        # Create mock context with diff data
        diff_data = DiffData(**{
            'diff_content': 'test diff',
            'changed_files': [
                {'status': 'M', 'filename': 'src/api/auth.py', 'change_type': 'modified'},
                {'status': 'A', 'filename': 'src/component.js', 'change_type': 'added'}
            ],
            'relevant_files': [
                {'status': 'M', 'filename': 'src/api/auth.py', 'change_type': 'modified'},
                {'status': 'A', 'filename': 'src/component.js', 'change_type': 'added'}
            ],
            'base_branch': 'main',
            'target_branch': 'feature',
            'total_files_changed': 2,
            'relevant_files_changed': 2,
            'has_changes': True
        })
        
        mock_context = Mock()
        mock_context.deps = diff_data
        
        # Test Python file analysis
        result = await analyze_file_changes(mock_context, 'python')
        self.assertIn('Found 1 python files changed', result)
        self.assertIn('src/api/auth.py (modified)', result)
        
        # Test JavaScript file analysis
        result = await analyze_file_changes(mock_context, 'javascript')
        self.assertIn('Found 1 javascript files changed', result)
        self.assertIn('src/component.js (added)', result)
        
        # Test no matching files
        result = await analyze_file_changes(mock_context, 'config')
        self.assertIn('No config files changed', result)


if __name__ == '__main__':
    unittest.main()
