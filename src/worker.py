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
from services.sqs_service import SQSService

# Configure structured logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda entry point that polls SQS and processes simulation job messages.
    
    Polls the configured SQS queue (up to one message per invocation), parses each message body, dispatches messages with action "start_simulation" to process_simulation_job, and aggregates per-message results.
    
    Parameters:
        event (Dict[str, Any]): Incoming Lambda event payload (not used for message retrieval; SQS is polled via SQSService).
        context (Any): Lambda runtime context (unused).
    
    Returns:
        Dict[str, Any]: A result dictionary containing:
            - statusCode (int): HTTP-style status code (200 on success, 500 on handler error).
            - processed (int): Number of messages processed.
            - results (List[Dict[str, Any]]): Per-message outcome objects, or an "error" key when the handler fails.
    """
    try:
        sqs_service = SQSService()
        
        # Receive messages from SQS
        messages = sqs_service.receive_message(max_messages=1, wait_time=5)
        
        if not messages:
            logger.info("No messages found in SQS queue")
            return {"statusCode": 200, "processed": 0, "results": []}
        
        logger.info(f"Processing {len(messages)} SQS messages")
        
        results = []
        
        for message in messages:
            try:
                # Parse SQS message
                message_body = json.loads(message['Body'])
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
    Process a single simulation job described by an SQS message and persist its final state.
    
    This function locates the job by its `job_id` from the provided SQS message, validates and updates the job lifecycle state, ensures repository availability and branch checkout, executes the simulation, and writes the final job record back to the datastore. On success the job is marked complete with the simulation report; on failure the job is marked failed with an error message and partial report where appropriate.
    
    Parameters:
        message_data (Dict[str, Any]): Parsed SQS message body containing at minimum the `job_id` key.
    
    Returns:
        Dict[str, Any]: A summary of processing outcome with at least:
            - `status`: One of `"completed"`, `"skipped"`, or `"error"`.
            - `job_id`: The processed job identifier.
            - `final_status`: Final job status value when available (string).
            - `result`: Simulation result summary when present (may be `None`).
            - `error` (optional): Error message when `status` is `"error"`.
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
        
        # Validate job is in correct state - accept PENDING jobs for processing
        if job.status not in [JobStatus.PENDING, JobStatus.SIMULATION_RUNNING]:
            logger.warning(f"Job {job_id} cannot be processed in current state: {job.status}")
            return {"status": "skipped", "job_id": job_id, "reason": f"Job state is {job.status}"}
        
        # Update job status to SIMULATION_RUNNING
        job.status = JobStatus.SIMULATION_RUNNING
        try:
            table.put_item(Item=job.to_dynamodb_item())
            logger.info(f"Updated job {job_id} status to SIMULATION_RUNNING")
        except Exception as e:
            logger.error(f"Failed to update job status to SIMULATION_RUNNING: {e}")
            return {"status": "error", "job_id": job_id, "error": f"Failed to update job status: {str(e)}"}
        
        # Get repository path and clone if needed
        repo_path = repo_service.get_repository_path(job.pr_owner, job.pr_repo)
        
        if not os.path.exists(repo_path):
            logger.info(f"Repository not found, cloning: {repo_path}")
            try:
                # Get user's GitHub token for cloning
                github_token = user_service.get_decrypted_github_token_by_user_id(job.user_id)
                
                # Construct repository URL
                repo_url = f"https://github.com/{job.pr_owner}/{job.pr_repo}.git"
                target_dir = f"{job.pr_owner}_{job.pr_repo}"
                
                # Clone the repository
                cloned_path = repo_service.clone_repository(
                    repo_url=repo_url,
                    access_token=github_token,
                    target_dir=target_dir
                )
                
                logger.info(f"Successfully cloned repository to: {cloned_path}")
                
            except Exception as e:
                logger.error(f"Failed to clone repository {job.pr_owner}/{job.pr_repo}: {e}")
                # Update job status to failed
                job.status = JobStatus.FAILED
                job.error_message = f"Failed to clone repository: {str(e)}"
                job.completed_at = datetime.now(timezone.utc)
                table.put_item(Item=job.to_dynamodb_item())
                return {"status": "error", "job_id": job_id, "error": f"Repository clone failed: {str(e)}"}
        
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


def process_sqs_messages() -> Dict[str, Any]:
    """
    Poll the configured SQS queue, process up to one message, and return per-message results for local (non-Lambda) usage.
    
    Receives messages from SQS, processes messages with action "start_simulation" by delegating to process_simulation_job, deletes handled or unknown messages when appropriate, and accumulates per-message results.
    
    Returns:
        result (Dict[str, Any]): A dictionary with keys:
            - statusCode (int): HTTP-like status code (200 on success, 500 on failure).
            - processed (int): Number of messages processed (length of "results").
            - results (List[Dict[str, Any]]): Per-message result objects (e.g., {"status": "completed", ...}, {"status": "skipped", ...}, {"status": "error", ...}).
            - error (str, optional): Error string present when statusCode is 500.
    """
    try:
        sqs_service = SQSService()
        
        # Receive messages from SQS
        messages = sqs_service.receive_message(max_messages=1, wait_time=5)
        
        if not messages:
            logger.info("No messages found in SQS queue")
            return {"statusCode": 200, "processed": 0, "results": []}
        
        logger.info(f"Processing {len(messages)} SQS messages")
        
        results = []
        
        for message in messages:
            try:
                # Parse message body
                message_body = json.loads(message['Body'])
                action = message_body.get('action')
                
                logger.info(f"Processing SQS message with action: {action}")
                
                if action == 'start_simulation':
                    # Process the simulation job
                    result = process_simulation_job(message_body)
                    results.append(result)
                    
                    # Delete message if processing was successful
                    if result.get('status') in ['completed', 'skipped']:
                        try:
                            sqs_service.delete_message(message['ReceiptHandle'])
                            logger.info("Successfully deleted processed message from SQS")
                        except Exception as e:
                            logger.error(f"Failed to delete message from SQS: {e}")
                    
                else:
                    logger.warning(f"Unknown action in SQS message: {action}")
                    results.append({"status": "skipped", "reason": f"Unknown action: {action}"})
                    
                    # Delete unknown messages to prevent infinite processing
                    try:
                        sqs_service.delete_message(message['ReceiptHandle'])
                    except Exception as e:
                        logger.error(f"Failed to delete unknown message: {e}")
                        
            except Exception as e:
                logger.error(f"Failed to process SQS message: {e}")
                results.append({"status": "error", "error": str(e)})
        
        return {
            "statusCode": 200,
            "processed": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"SQS message processing failed: {e}")
        return {"statusCode": 500, "error": str(e)}


def validate_worker_environment() -> bool:
    """
    Check that the worker runtime and required services are available and operational.
    
    Returns:
        bool: `True` if environment validation passed, `False` otherwise.
    """
    try:
        # Check required services can be imported
        from services.simulation_service import SimulationService
        
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
