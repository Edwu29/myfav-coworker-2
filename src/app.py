"""
Main Lambda handler for myfav-coworker API Gateway integration.
"""

import json
import logging
import re
from typing import Dict, Any
from api.auth import github_login, github_callback
from api.simulations import submit_simulation_handler, get_simulation_status_handler

# Configure structured logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for API Gateway events.

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response format
    """
    try:
        # Extract path and method from event
        path = event.get("path", "")
        method = event.get("httpMethod", "")

        logger.info(f"Processing {method} request to {path}")

        # Route to appropriate handler
        if path == "/health" and method == "GET":
            return handle_health_check()
        
        # Authentication routes
        elif path == "/auth/github" and method == "GET":
            return github_login(event, context)
        elif path == "/auth/github/callback" and method == "GET":
            return github_callback(event, context)
        
        # Simulation routes
        elif path == "/simulations" and method == "POST":
            return submit_simulation_handler(event, context)
        elif re.match(r"^/simulations/[^/]+$", path) and method == "GET":
            return get_simulation_status_handler(event, context)

        # Default 404 response
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {"error": "Not Found", "message": f"Path {path} not found"}
            ),
        }

    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                }
            ),
        }


def handle_health_check() -> Dict[str, Any]:
    """
    Handle health check endpoint.

    Returns:
        200 OK response with JSON health status
    """
    logger.info("Health check requested")

    response_body = {
        "status": "healthy",
        "service": "myfav-coworker",
        "version": "1.0.0",
    }

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(response_body),
    }
