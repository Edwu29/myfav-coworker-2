"""Simulation API endpoints for PR submission and tracking."""

import json
import logging
import re
import boto3
from typing import Dict, Any
from pydantic import ValidationError
from datetime import datetime, timezone

from src.models.pull_request import PullRequestSubmission, PullRequestResponse
from src.models.simulation_job import SimulationJobModel, JobStatus
from src.services.user_service import UserService
from src.services.github_service import GitHubService
from src.utils.auth_middleware import get_user_from_token
from src.utils.pr_validation import parse_github_pr_url, PRValidationError

logger = logging.getLogger(__name__)


def submit_simulation_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for POST /simulations - Submit a new simulation job.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response format
    """
    try:
        # Extract and validate authentication
        try:
            user_data = get_user_from_token(event)
        except Exception as e:
            logger.warning(f"Authentication failed: {e}")
            return {
                "statusCode": 401,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Authentication required"})
            }
        
        user_id = user_data.get('user_id')
        github_id = user_data.get('github_id')
        
        if not user_id or not github_id:
            logger.error("Missing user information in authentication data")
            return {
                "statusCode": 401,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Invalid authentication data"})
            }
        
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
            request = PullRequestSubmission(**body)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Invalid request body: {e}")
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Invalid request format"})
            }
        
        # Validate and parse PR URL
        pr_url_str = str(request.pr_url)
        try:
            owner, repo, pull_number = parse_github_pr_url(pr_url_str)
            logger.info(f"Parsed PR URL: {owner}/{repo}/pull/{pull_number}")
        except PRValidationError as e:
            logger.warning(f"Invalid PR URL format: {pr_url_str} - {e}")
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"Invalid GitHub PR URL: {e}"})
            }
        
        # Create simulation job record
        job = SimulationJobModel(
            user_id=user_id,
            pr_url=pr_url_str,
            status=JobStatus.PENDING,
            pr_owner=owner,
            pr_repo=repo,
            pr_number=pull_number
        )
        
        # Initialize services
        user_service = UserService()
        github_service = GitHubService()
        
        # Get user's GitHub token for API access
        try:
            github_token = user_service.get_decrypted_github_token(github_id)
        except Exception as e:
            logger.error(f"Failed to get GitHub token for user {github_id}: {e}")
            return {
                "statusCode": 401,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "GitHub authentication required"})
            }
        
        # Validate PR exists and is accessible
        try:
            pr_data = github_service.get_pull_request(
                owner, repo, pull_number, github_token
            )
            
            # Update job with PR metadata
            job.pr_title = pr_data.get('title')
            job.pr_head_sha = pr_data.get('head', {}).get('sha')
            job.pr_base_sha = pr_data.get('base', {}).get('sha')
            
            logger.info(f"Successfully validated PR: {owner}/{repo}/pull/{pull_number}")
            
        except Exception as e:
            logger.error(f"Failed to fetch PR data: {e}")
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "error": "Unable to access the specified pull request. Please check the URL and your permissions."
                })
            }
        
        # Store job in DynamoDB
        try:
            table = user_service.table
            table.put_item(Item=job.to_dynamodb_item())
            
            logger.info(f"Created simulation job: {job.job_id}")
            
        except Exception as e:
            logger.error(f"Failed to store simulation job: {e}")
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Failed to create simulation job"})
            }
        
        # Auto-start simulation by sending to SQS queue
        try:
            sqs = boto3.client('sqs')
            queue_url = user_service._get_sqs_queue_url()
            
            message_body = {
                "job_id": job.job_id,
                "action": "start_simulation",
                "user_id": user_id,
                "pr_url": job.pr_url,
                "pr_owner": job.pr_owner,
                "pr_repo": job.pr_repo,
                "pr_number": job.pr_number,
                "pr_head_sha": job.pr_head_sha,
                "pr_base_sha": job.pr_base_sha
            }
            
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(message_body),
                MessageAttributes={
                    'action': {
                        'StringValue': 'start_simulation',
                        'DataType': 'String'
                    }
                }
            )
            
            logger.info(f"Queued simulation job {job.job_id} for processing")
            
        except Exception as e:
            logger.warning(f"Failed to queue simulation job {job.job_id}: {e}")
            # Don't fail the request if queueing fails - job is still created
        
        # Return success response with job_id only (per API spec)
        return {
            "statusCode": 202,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"job_id": job.job_id})
        }
        
    except Exception as e:
        logger.error(f"Unexpected error in submit_simulation: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal server error"})
        }


def get_simulation_status_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for GET /simulations/{job_id} - Get simulation job status.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        API Gateway response format
    """
    try:
        # Extract and validate authentication
        try:
            user_data = get_user_from_token(event)
        except Exception as e:
            logger.warning(f"Authentication failed: {e}")
            return {
                "statusCode": 401,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Authentication required"})
            }
        
        user_id = user_data.get('user_id')
        
        if not user_id:
            return {
                "statusCode": 401,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Invalid authentication data"})
            }
        
        # Extract job_id from path parameters
        path_parameters = event.get('pathParameters', {})
        job_id = path_parameters.get('job_id')
        
        if not job_id:
            # Fallback to path parsing if pathParameters not available
            path = event.get("path", "")
            match = re.match(r"^/simulations/([^/]+)$", path)
            if not match:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Missing job ID"})
                }
            job_id = match.group(1)
        
        # Initialize user service to access DynamoDB
        user_service = UserService()
        table = user_service.table
        
        # Fetch job from DynamoDB
        try:
            response = table.get_item(
                Key={
                    'PK': f'JOB#{job_id}',
                    'SK': 'METADATA'
                }
            )
            
            if 'Item' not in response:
                return {
                    "statusCode": 404,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Simulation job not found"})
                }
            
            job_item = response['Item']
            job = SimulationJobModel.from_dynamodb_item(job_item)
            
            # Verify user owns this job
            if job.user_id != user_id:
                return {
                    "statusCode": 403,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Access denied to this simulation job"})
                }
            
            # Return job data
            status_value = job.status.value if hasattr(job.status, 'value') else str(job.status)
            created_at_str = job.created_at.isoformat() if hasattr(job.created_at, 'isoformat') else str(job.created_at)
            completed_at_str = job.completed_at.isoformat() if job.completed_at and hasattr(job.completed_at, 'isoformat') else str(job.completed_at) if job.completed_at else None
            
            job_data = {
                "job_id": job.job_id,
                "status": status_value,
                "pr_url": job.pr_url,
                "created_at": created_at_str,
                "completed_at": completed_at_str,
                "report": job.report,
                "error_message": job.error_message,
                "pr_title": job.pr_title,
                "pr_owner": job.pr_owner,
                "pr_repo": job.pr_repo,
                "pr_number": job.pr_number
            }
            
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(job_data)
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch job {job_id}: {e}")
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Failed to fetch simulation job"})
            }
            
    except Exception as e:
        logger.error(f"Unexpected error in get_simulation_status: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal server error"})
        }


