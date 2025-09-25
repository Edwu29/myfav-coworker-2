"""AI agent service for generating test plans from code diffs."""

import logging
import os
import asyncio
from typing import Dict, Any, List
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

logger = logging.getLogger(__name__)


class DiffData(BaseModel):
    """Data model for Git diff information."""
    diff_content: str
    changed_files: List[Dict[str, str]]
    relevant_files: List[Dict[str, str]]
    base_branch: str
    target_branch: str
    total_files_changed: int
    relevant_files_changed: int
    has_changes: bool


class TestCase(BaseModel):
    """Individual test case within a test plan."""
    id: str
    description: str
    test_type: str  # 'ui', 'api', 'integration', 'unit'
    target_element: str
    action: str
    expected_outcome: str
    priority: str  # 'high', 'medium', 'low'


class TestPlan(BaseModel):
    """AI-generated test plan for code changes."""
    test_cases: List[TestCase]
    execution_strategy: str
    estimated_duration_minutes: int
    risk_level: str  # 'high', 'medium', 'low'
    summary: str
    reasoning: str


class AIAgentError(Exception):
    """Exception raised for AI agent operation errors."""
    pass


# Get AI configuration from environment
AI_TIMEOUT = int(os.getenv('AI_AGENT_TIMEOUT', '60'))
AI_MAX_RETRIES = int(os.getenv('AI_AGENT_MAX_RETRIES', '3'))
AI_TEMPERATURE = float(os.getenv('AI_AGENT_TEMPERATURE', '0.3'))
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Create Google provider and model
google_provider = GoogleProvider(api_key=GOOGLE_API_KEY)
google_model = GoogleModel('gemini-2.5-pro', provider=google_provider)

# Global AI agent instance for reuse (following Pydantic AI best practices)
diff_agent = Agent[DiffData, TestPlan](
    google_model,
    deps_type=DiffData,
    output_type=TestPlan,
    system_prompt=(
        'You are an expert test engineer analyzing code changes to generate targeted test plans. '
        'Analyze the provided Git diff and changed files to create comprehensive test cases that focus '
        'on the areas most likely to be affected by the changes. Generate test cases that can be '
        'executed using browser automation (Playwright). Focus on UI interactions, API endpoints, '
        'and integration points that may be impacted by the code changes. '
        'Prioritize test cases based on risk and impact of the changes.'
    )
)


@diff_agent.tool
async def analyze_file_changes(ctx: RunContext[DiffData], file_type: str) -> str:
    """
    Analyze specific file type changes for test planning.
    
    Args:
        ctx: Runtime context containing diff data
        file_type: Type of files to analyze ('python', 'javascript', 'api', 'config')
        
    Returns:
        Analysis summary for the file type
    """
    diff_data = ctx.deps
    
    relevant_files = [
        f for f in diff_data.relevant_files 
        if _matches_file_type(f['filename'], file_type)
    ]
    
    if not relevant_files:
        return f"No {file_type} files changed in this diff."
    
    analysis = f"Found {len(relevant_files)} {file_type} files changed:\n"
    for file_info in relevant_files:
        analysis += f"- {file_info['filename']} ({file_info['change_type']})\n"
    
    return analysis


def _matches_file_type(filename: str, file_type: str) -> bool:
    """Check if filename matches the specified file type."""
    type_extensions = {
        'python': ['.py'],
        'javascript': ['.js', '.ts', '.jsx', '.tsx'],
        'api': ['.py', '.js', '.ts'],  # API files could be in multiple languages
        'config': ['.json', '.yaml', '.yml', '.toml', '.ini', '.env']
    }
    
    extensions = type_extensions.get(file_type, [])
    return any(filename.lower().endswith(ext) for ext in extensions)


class AIAgentService:
    """Service for AI-powered test plan generation."""
    
    def __init__(self):
        """Initialize AI agent service."""
        self.agent = diff_agent
        
    async def generate_test_plan(self, diff_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a test plan from Git diff data using AI agent.
        
        Args:
            diff_data: Dictionary containing diff information
            
        Returns:
            Dictionary containing generated test plan
            
        Raises:
            AIAgentError: If test plan generation fails
        """
        try:
            # Convert diff data to Pydantic model
            diff_model = DiffData(**diff_data)
            
            # Validate that there are changes to analyze
            if not diff_model.has_changes:
                logger.warning("No changes detected in diff data")
                return self._create_empty_test_plan("No code changes detected")
            
            # Generate test plan using AI agent with timeout and retry logic
            logger.info(f"Generating test plan for {diff_model.relevant_files_changed} relevant file changes")
            
            for attempt in range(AI_MAX_RETRIES):
                try:
                    result = await self.agent.run(
                        f"Generate a comprehensive test plan for the following code changes:\n"
                        f"Base branch: {diff_model.base_branch}\n"
                        f"Target branch: {diff_model.target_branch}\n"
                        f"Files changed: {diff_model.total_files_changed}\n"
                        f"Relevant files: {diff_model.relevant_files_changed}\n\n"
                        f"Focus on creating test cases that validate the functionality "
                        f"affected by these changes and can be executed with browser automation.",
                        deps=diff_model
                    )
                    break
                except Exception as e:
                    logger.warning(f"AI agent attempt {attempt + 1} failed: {e}")
                    if attempt == AI_MAX_RETRIES - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
            # Convert result to dictionary
            test_plan = result.output
            test_plan_dict = {
                'test_cases': [case.model_dump() for case in test_plan.test_cases],
                'execution_strategy': test_plan.execution_strategy,
                'estimated_duration_minutes': test_plan.estimated_duration_minutes,
                'risk_level': test_plan.risk_level,
                'summary': test_plan.summary,
                'reasoning': test_plan.reasoning,
                'generated_by': 'ai_agent',
                'agent_model': 'gemini-2.5-pro'
            }
            
            logger.info(f"Generated test plan with {len(test_plan.test_cases)} test cases")
            return test_plan_dict
            
        except Exception as e:
            logger.error(f"Failed to generate test plan: {e}")
            raise AIAgentError(f"Test plan generation failed: {e}")
    
    def generate_test_plan_sync(self, diff_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous version of test plan generation.
        
        Args:
            diff_data: Dictionary containing diff information
            
        Returns:
            Dictionary containing generated test plan
            
        Raises:
            AIAgentError: If test plan generation fails
        """
        try:
            # Convert diff data to Pydantic model
            diff_model = DiffData(**diff_data)
            
            # Validate that there are changes to analyze
            if not diff_model.has_changes:
                logger.warning("No changes detected in diff data")
                return self._create_empty_test_plan("No code changes detected")
            
            # Generate test plan using AI agent (synchronous)
            logger.info(f"Generating test plan for {diff_model.relevant_files_changed} relevant file changes")
            
            result = self.agent.run_sync(
                f"Generate a comprehensive test plan for the following code changes:\n"
                f"Base branch: {diff_model.base_branch}\n"
                f"Target branch: {diff_model.target_branch}\n"
                f"Files changed: {diff_model.total_files_changed}\n"
                f"Relevant files: {diff_model.relevant_files_changed}\n\n"
                f"Focus on creating test cases that validate the functionality "
                f"affected by these changes and can be executed with browser automation.",
                deps=diff_model
            )
            
            # Convert result to dictionary
            test_plan = result.output
            test_plan_dict = {
                'test_cases': [case.model_dump() for case in test_plan.test_cases],
                'execution_strategy': test_plan.execution_strategy,
                'estimated_duration_minutes': test_plan.estimated_duration_minutes,
                'risk_level': test_plan.risk_level,
                'summary': test_plan.summary,
                'reasoning': test_plan.reasoning,
                'generated_by': 'ai_agent',
                'agent_model': 'gemini-2.5-pro'
            }
            
            logger.info(f"Generated test plan with {len(test_plan.test_cases)} test cases")
            return test_plan_dict
            
        except Exception as e:
            logger.error(f"Failed to generate test plan: {e}")
            raise AIAgentError(f"Test plan generation failed: {e}")
    
    def _create_empty_test_plan(self, reason: str) -> Dict[str, Any]:
        """
        Create an empty test plan when no changes are detected.
        
        Args:
            reason: Reason for empty test plan
            
        Returns:
            Empty test plan dictionary
        """
        return {
            'test_cases': [],
            'execution_strategy': 'skip',
            'estimated_duration_minutes': 0,
            'risk_level': 'low',
            'summary': f'No test plan generated: {reason}',
            'reasoning': reason,
            'generated_by': 'fallback',
            'agent_model': 'gemini-2.5-pro'
        }
    
    def validate_test_plan(self, test_plan: Dict[str, Any]) -> bool:
        """
        Validate that a test plan has the required structure.
        
        Args:
            test_plan: Test plan dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'test_cases', 'execution_strategy', 'estimated_duration_minutes',
            'risk_level', 'summary', 'reasoning'
        ]
        
        for field in required_fields:
            if field not in test_plan:
                logger.error(f"Test plan missing required field: {field}")
                return False
        
        # Validate test cases structure
        if not isinstance(test_plan['test_cases'], list):
            logger.error("Test cases must be a list")
            return False
        
        for i, test_case in enumerate(test_plan['test_cases']):
            required_case_fields = [
                'id', 'description', 'test_type', 'target_element',
                'action', 'expected_outcome', 'priority'
            ]
            for field in required_case_fields:
                if field not in test_case:
                    logger.error(f"Test case {i} missing required field: {field}")
                    return False
        
        logger.info("Test plan validation passed")
        return True
