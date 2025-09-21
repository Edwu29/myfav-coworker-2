"""
SQS worker Lambda handler for background simulation processing.
"""

import json
import logging
import os
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timezone

from models.simulation_job import SimulationJobModel, JobStatus
from services.user_service import UserService
from services.repository_service import RepositoryService
from services.simulation_service import SimulationService

# Configure structured logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for SQS events - processes simulation jobs.
    
    Args:
        event: SQS event with message records
        context: Lambda context
        
    Returns:
        Processing results
    """
    try:
        records = event.get('Records', [])
        logger.info(f"Processing {len(records)} SQS messages")
        
        results = []
        
        for record in records:
            try:
                # Parse SQS message
                message_body = json.loads(record['body'])
                action = message_body.get('action')
                
                logger.info(f"Processing message with action: {action}")
                
                if action == 'start_simulation':
                    result = process_simulation_job(message_body)
                    results.append(result)
                else:
                    logger.warning(f"Unknown action: {action}")
                    results.append({"status": "skipped", "reason": f"Unknown action: {action}"})
                    
            except Exception as e:
                logger.error(f"Failed to process SQS record: {e}")
                results.append({"status": "error", "error": str(e)})
        
        return {
            "statusCode": 200,
            "processed": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Worker lambda handler failed: {e}")
        return {
            "statusCode": 500,
            "error": str(e)
        }


def process_simulation_job(message_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a simulation job from SQS message.
    
    Args:
        message_data: SQS message body with job details
        
    Returns:
        Processing result
    """
    job_id = message_data.get('job_id')
    
    try:
        logger.info(f"Starting simulation processing for job {job_id}")
        
        # Initialize services
        user_service = UserService()
        repo_service = RepositoryService()
        simulation_service = SimulationService()
        
        # Fetch job from DynamoDB
        table = user_service.table
        response = table.get_item(
            Key={
                'PK': f'JOB#{job_id}',
                'SK': 'METADATA'
            }
        )
        
        if 'Item' not in response:
            logger.error(f"Job {job_id} not found in database")
            return {"status": "error", "job_id": job_id, "error": "Job not found"}
        
        job = SimulationJobModel.from_dynamodb_item(response['Item'])
        
        # Validate job is in correct state
        if job.status != JobStatus.SIMULATION_RUNNING:
            logger.warning(f"Job {job_id} is not in simulation_running state: {job.status}")
            return {"status": "skipped", "job_id": job_id, "reason": f"Job state is {job.status}"}
        
        # Get repository path from previous processing
        repo_path = repo_service.get_repository_path(job.pr_owner, job.pr_repo)
        
        if not os.path.exists(repo_path):
            logger.error(f"Repository path does not exist: {repo_path}")
            # Update job status to failed
            job.status = JobStatus.FAILED
            job.error_message = f"Repository not found: {repo_path}"
            job.completed_at = datetime.now(timezone.utc)
            table.put_item(Item=job.to_dynamodb_item())
            return {"status": "error", "job_id": job_id, "error": "Repository not found"}
        
        # Ensure correct branch is checked out
        try:
            repo_service.checkout_pr_branch(repo_path, job.pr_head_sha)
            logger.info(f"Checked out PR branch for job {job_id}")
        except Exception as e:
            logger.error(f"Failed to checkout PR branch: {e}")
            job.status = JobStatus.FAILED
            job.error_message = f"Failed to checkout PR branch: {str(e)}"
            job.completed_at = datetime.now(timezone.utc)
            table.put_item(Item=job.to_dynamodb_item())
            return {"status": "error", "job_id": job_id, "error": str(e)}
        
        # Run simulation asynchronously
        try:
            # Use asyncio to run the async simulation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                simulation_report = loop.run_until_complete(
                    simulation_service.run_simulation(job, repo_path)
                )
            finally:
                loop.close()
            
            # Update job with simulation results
            job.status = JobStatus.SIMULATION_COMPLETED
            job.report = simulation_report
            job.completed_at = datetime.now(timezone.utc)
            
            # Clear any previous error message
            job.error_message = None
            
            logger.info(f"Simulation completed for job {job_id}: {simulation_report.get('result', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Simulation failed for job {job_id}: {e}")
            job.status = JobStatus.FAILED
            job.error_message = f"Simulation execution failed: {str(e)}"
            job.completed_at = datetime.now(timezone.utc)
            
            # Store partial report if available
            job.report = {
                "result": "fail",
                "summary": f"Simulation failed: {str(e)}",
                "execution_logs": [f"ERROR: {str(e)}"],
                "error": str(e)
            }
        
        # Update job in DynamoDB
        try:
            table.put_item(Item=job.to_dynamodb_item())
            logger.info(f"Updated job {job_id} status to {job.status}")
        except Exception as e:
            logger.error(f"Failed to update job {job_id} in database: {e}")
            return {"status": "error", "job_id": job_id, "error": f"Database update failed: {str(e)}"}
        
        return {
            "status": "completed",
            "job_id": job_id,
            "final_status": job.status.value if hasattr(job.status, 'value') else str(job.status),
            "result": job.report.get('result') if job.report else None
        }
        
    except Exception as e:
        logger.error(f"Unexpected error processing job {job_id}: {e}")
        
        # Try to update job status to failed if possible
        try:
            user_service = UserService()
            table = user_service.table
            
            # Fetch current job state
            response = table.get_item(
                Key={
                    'PK': f'JOB#{job_id}',
                    'SK': 'METADATA'
                }
            )
            
            if 'Item' in response:
                job = SimulationJobModel.from_dynamodb_item(response['Item'])
                job.status = JobStatus.FAILED
                job.error_message = f"Worker processing failed: {str(e)}"
                job.completed_at = datetime.now(timezone.utc)
                table.put_item(Item=job.to_dynamodb_item())
                
        except Exception as update_error:
            logger.error(f"Failed to update job {job_id} after processing error: {update_error}")
        
        return {"status": "error", "job_id": job_id, "error": str(e)}


def validate_worker_environment() -> bool:
    """Validate that worker environment is properly configured."""
    try:
        # Check required services can be imported
        from services.simulation_service import SimulationService
        from services.repository_service import RepositoryService
        
        # Validate simulation service
        sim_service = SimulationService()
        if not sim_service.validate_environment():
            logger.error("Simulation service environment validation failed")
            return False
        
        logger.info("Worker environment validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Worker environment validation failed: {e}")
        return False
